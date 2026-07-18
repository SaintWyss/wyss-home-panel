#include "wyss/adapters/bridge_client.hpp"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>

#include <algorithm>
#include <cstring>
#include <new>
#include <optional>
#include <string>
#include <vector>

#ifndef WYSS_PROTOCOL_V2_CLIENT
#define WYSS_PROTOCOL_V2_CLIENT 0
#endif

namespace wyss::adapters {
namespace {
constexpr std::uint16_t kDefaultPort = 443;

struct Endpoint {
    String host;
    String path;
    std::uint16_t port{kDefaultPort};
};

std::optional<Endpoint> parse_endpoint(std::string_view url) {
    constexpr std::string_view prefix = "wss://";
    if (!url.starts_with(prefix)) {
        return std::nullopt;
    }
    const std::string_view remainder = url.substr(prefix.size());
    const auto slash = remainder.find('/');
    const std::string_view authority = remainder.substr(0, slash);
    const auto colon = authority.rfind(':');
    Endpoint endpoint;
    endpoint.host = String(authority.substr(0, colon).data(),
                           static_cast<unsigned int>(colon == std::string_view::npos
                                                         ? authority.size()
                                                         : colon));
    endpoint.path =
        slash == std::string_view::npos ? "/v1/panel" : String(remainder.substr(slash).data());
#if WYSS_PROTOCOL_V2_CLIENT
    if (endpoint.path == "/" || endpoint.path == "/v1/panel") {
        endpoint.path = "/v2/client";
    }
#endif
    if (colon != std::string_view::npos) {
        const unsigned long parsed = String(authority.substr(colon + 1).data()).toInt();
        if (parsed == 0 || parsed > 65535) {
            return std::nullopt;
        }
        endpoint.port = static_cast<std::uint16_t>(parsed);
    }
    return endpoint;
}

domain::ExecutionState execution_state(const char* value) {
    if (std::strcmp(value, "planning") == 0 || std::strcmp(value, "thinking") == 0)
        return domain::ExecutionState::Planning;
    if (std::strcmp(value, "awaiting_confirmation") == 0)
        return domain::ExecutionState::AwaitingConfirmation;
    if (std::strcmp(value, "executing") == 0) return domain::ExecutionState::Executing;
    if (std::strcmp(value, "verified") == 0) return domain::ExecutionState::Verified;
    if (std::strcmp(value, "failed") == 0) return domain::ExecutionState::Failed;
    return domain::ExecutionState::Idle;
}

domain::RiskLevel risk_level(JsonVariantConst value) {
    if (value.is<const char*>()) {
        const char* risk = value.as<const char*>();
        if (std::strcmp(risk, "B") == 0) return domain::RiskLevel::B;
        if (std::strcmp(risk, "C") == 0) return domain::RiskLevel::C;
        if (std::strcmp(risk, "D") == 0) return domain::RiskLevel::D;
        return domain::RiskLevel::A;
    }
    return static_cast<domain::RiskLevel>(std::clamp(value.as<int>(), 0, 3));
}
}  // namespace

BridgeClient::BridgeClient(const ports::ConfigStorePort& config) : config_(config) {}

BridgeClient::~BridgeClient() {
    if (task_ != nullptr) {
        vTaskDelete(task_);
        task_ = nullptr;
    }
    auto release_queue = [](QueueHandle_t& queue) {
        if (queue == nullptr) return;
        Message* message = nullptr;
        while (xQueueReceive(queue, &message, 0) == pdTRUE) {
            delete message;
            message = nullptr;
        }
        vQueueDelete(queue);
        queue = nullptr;
    };
    release_queue(outbound_);
    release_queue(inbound_);
}

bool BridgeClient::begin() {
    if (task_ != nullptr) return true;
    if (WiFi.status() != WL_CONNECTED) return false;
    const auto endpoint = parse_endpoint(config_.bridge_url());
    if (!endpoint) {
        return false;
    }
    outbound_ = xQueueCreate(6, sizeof(Message*));
    inbound_ = xQueueCreate(6, sizeof(Message*));
    if (outbound_ == nullptr || inbound_ == nullptr) {
        if (outbound_ != nullptr) {
            vQueueDelete(outbound_);
            outbound_ = nullptr;
        }
        if (inbound_ != nullptr) {
            vQueueDelete(inbound_);
            inbound_ = nullptr;
        }
        return false;
    }

    auth_header_ = "Authorization: Bearer ";
    auth_header_ += config_.device_token().data();
    auth_header_ += "\r\nX-Wyss-";
#if WYSS_PROTOCOL_V2_CLIENT
    auth_header_ += "Client: ";
#else
    auth_header_ += "Panel: ";
#endif
    auth_header_ += config_.panel_id().data();
    auth_header_ += "\r\n";
    socket_.setExtraHeaders(auth_header_.c_str());
    socket_.onEvent([this](WStype_t type, std::uint8_t* payload, std::size_t length) {
        handle_socket_event(type, payload, length);
    });
    socket_.setReconnectInterval(1000);
    socket_.enableHeartbeat(12000, 3000, 2);
    socket_.beginSslWithCA(endpoint->host.c_str(), endpoint->port, endpoint->path.c_str(),
                           config_.ca_certificate().data(),
#if WYSS_PROTOCOL_V2_CLIENT
                           "wyss-v2"
#else
                           "arduino"
#endif
    );
    state_.store(domain::ConnectionState::Discovering);
    if (xTaskCreatePinnedToCore(task_entry, "wyss-network", kNetworkTaskStackBytes, this, 4,
                                &task_, 0) == pdPASS) {
        return true;
    }
    vQueueDelete(outbound_);
    vQueueDelete(inbound_);
    outbound_ = nullptr;
    inbound_ = nullptr;
    state_.store(domain::ConnectionState::Offline);
    return false;
}

void BridgeClient::task_entry(void* context) { static_cast<BridgeClient*>(context)->run(); }

void BridgeClient::run() {
    Message* message = nullptr;
    for (;;) {
        if (WiFi.status() != WL_CONNECTED) {
            state_.store(domain::ConnectionState::Offline);
            vTaskDelay(pdMS_TO_TICKS(250));
            continue;
        }
        socket_.loop();
        while (xQueueReceive(outbound_, &message, 0) == pdTRUE) {
            if (message != nullptr) {
                if (socket_.isConnected()) {
                    socket_.sendTXT(message->text);
                }
                delete message;
                message = nullptr;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}

void BridgeClient::handle_socket_event(WStype_t type, std::uint8_t* payload, std::size_t length) {
    if (type == WStype_CONNECTED) {
        state_.store(domain::ConnectionState::Online);
        JsonDocument hello;
#if WYSS_PROTOCOL_V2_CLIENT
        hello["v"] = 2;
        hello["type"] = "session.hello";
        hello["message_id"] = "panel:hello";
        hello["source"] = config_.panel_id();
        JsonObject payload = hello["payload"].to<JsonObject>();
        payload["firmware"] = "2.0.0";
        JsonArray capabilities = payload["capabilities"].to<JsonArray>();
        capabilities.add("ui.core");
        capabilities.add("light.fast");
        capabilities.add("assistant.text");
        capabilities.add("spotify.control");
        capabilities.add("calendar.read");
        payload["last_event_id"] = last_event_id_;
#else
        hello["v"] = 1;
        hello["type"] = "hello";
        hello["panel_id"] = config_.panel_id();
        hello["firmware"] = "2.0.0";
#endif
        char json[256]{};
        const std::size_t written = serializeJson(hello, json, sizeof(json));
        enqueue_json(json, written);
    } else if (type == WStype_DISCONNECTED) {
        state_.store(domain::ConnectionState::Offline);
    } else if (type == WStype_TEXT && payload != nullptr && length < kMaxMessageBytes) {
        auto* message = new (std::nothrow) Message{};
        if (message == nullptr) return;
        std::memcpy(message->text, payload, length);
        message->text[length] = '\0';
        if (xQueueSend(inbound_, &message, 0) != pdTRUE) delete message;
    }
}

bool BridgeClient::enqueue_json(const char* json, std::size_t length) {
    if (outbound_ == nullptr || length == 0 || length >= kMaxMessageBytes) {
        return false;
    }
    auto* message = new (std::nothrow) Message{};
    if (message == nullptr) return false;
    std::memcpy(message->text, json, length);
    message->text[length] = '\0';
    if (xQueueSend(outbound_, &message, 0) == pdTRUE) return true;
    delete message;
    return false;
}

bool BridgeClient::send_fast(const domain::FastCommand& command) {
    JsonDocument document;
#if WYSS_PROTOCOL_V2_CLIENT
    document["v"] = 2;
    document["type"] = "home.command";
    document["message_id"] = command.request_id;
    document["source"] = config_.panel_id();
    JsonObject payload = document["payload"].to<JsonObject>();
    payload["request_id"] = command.request_id;
    payload["idempotency_key"] = command.request_id;
    payload["entity_id"] = command.entity_id;
    payload["action"] = command.action;
    if (command.brightness) payload["value"] = *command.brightness;
    if (command.rgb) payload["rgb"] = *command.rgb;
#else
    document["v"] = 1;
    document["type"] = "command.fast";
    document["id"] = command.request_id;
    document["sent_at_ms"] = command.issued_at_ms;
    document["entity_id"] = command.entity_id;
    document["action"] = command.action;
    if (command.brightness) document["brightness"] = *command.brightness;
    if (command.rgb) document["rgb"] = *command.rgb;
#endif
    char json[512]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
}

bool BridgeClient::send_media(const domain::MediaCommand& command) {
#if WYSS_PROTOCOL_V2_CLIENT
    JsonDocument document;
    document["v"] = 2;
    document["type"] = "capability.command";
    document["message_id"] = command.request_id;
    document["source"] = config_.panel_id();
    JsonObject payload = document["payload"].to<JsonObject>();
    payload["capability"] = "spotify";
    payload["action"] = command.action;
    payload["idempotency_key"] = command.request_id;
    if (command.value) payload["value"] = *command.value;
    if (!command.device_id.empty()) payload["device_id"] = command.device_id;
    char json[512]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
#else
    (void)command;
    return false;
#endif
}

bool BridgeClient::send_intent(const domain::Intent& intent) {
    JsonDocument document;
#if WYSS_PROTOCOL_V2_CLIENT
    document["v"] = 2;
    document["type"] = "assistant.intent";
    document["message_id"] = intent.request_id;
    document["source"] = config_.panel_id();
    JsonObject payload = document["payload"].to<JsonObject>();
    payload["request_id"] = intent.request_id;
    payload["text"] = intent.text;
    payload["input"] = "text";
#else
    document["v"] = 1;
    document["type"] = "intent.submit";
    document["id"] = intent.request_id;
    document["sent_at_ms"] = intent.issued_at_ms;
    document["text"] = intent.text;
#endif
    char json[1024]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
}

bool BridgeClient::confirm(std::string_view plan_id, bool accepted, domain::RiskLevel risk,
                           std::uint64_t revision) {
    JsonDocument document;
#if WYSS_PROTOCOL_V2_CLIENT
    (void)risk;
    document["v"] = 2;
    document["type"] = "plan.answer";
    document["message_id"] = String("panel:answer:") + String(++sequence_);
    document["source"] = config_.panel_id();
    JsonObject payload = document["payload"].to<JsonObject>();
    payload["plan_id"] = plan_id;
    payload["decision"] = accepted ? "approve" : "reject";
    payload["confirmation"] = accepted ? "CONFIRMAR" : "";
    payload["expected_revision"] = revision;
#else
    document["v"] = 1;
    document["type"] = "plan.answer";
    document["plan_id"] = plan_id;
    document["accepted"] = accepted;
    document["risk"] = static_cast<unsigned>(risk);
#endif
    char json[384]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
}

void BridgeClient::poll(application::PanelService& service) {
    const auto state = state_.load();
    if (state != rendered_state_) {
        rendered_state_ = state;
        service.set_connection(state);
    }
    if (inbound_ == nullptr) return;
    Message* message = nullptr;
    for (unsigned count = 0; count < 6 && xQueueReceive(inbound_, &message, 0) == pdTRUE; ++count) {
        if (message != nullptr) {
            dispatch(service, message->text);
            delete message;
            message = nullptr;
        }
    }
}

void BridgeClient::dispatch(application::PanelService& service, const char* json) {
    JsonDocument document;
    if (deserializeJson(document, json) != DeserializationError::Ok) {
        return;
    }
#if WYSS_PROTOCOL_V2_CLIENT
    const char* type = document["type"] | "";
    auto replace_devices = [&](JsonArrayConst items) {
        std::vector<domain::DeviceState> devices;
        for (JsonObjectConst item : items) {
            domain::DeviceState device;
            device.entity_id = item["entity_id"] | "";
            device.friendly_name = item["friendly_name"] | device.entity_id.c_str();
            device.available = item["available"] | false;
            device.on = item["on"] | false;
            device.brightness =
                static_cast<std::uint8_t>(std::clamp(item["brightness"] | 0, 0, 100));
            if (item["rgb"].is<unsigned>()) device.rgb = item["rgb"].as<unsigned>();
            device.revision = item["revision"] | 0ULL;
            devices.push_back(std::move(device));
        }
        service.replace_devices(std::move(devices));
    };
    auto assistant = [&](JsonObjectConst value, const char* event_type) {
        const char* state_text = value["state"] | "";
        if (state_text[0] != '\0') {
            assistant_state_ = execution_state(state_text);
            if (assistant_state_ == domain::ExecutionState::Planning) response_buffer_.clear();
            service.receive_execution({value["request_id"] | "assistant", assistant_state_,
                                       value["message"] | "", 0});
        }
        if (std::strcmp(event_type, "assistant.response.delta") == 0) {
            response_buffer_.append(value["delta"] | "");
            service.receive_execution({value["request_id"] | "assistant", assistant_state_,
                                       response_buffer_, 0});
        } else if (std::strcmp(event_type, "assistant.response.completed") == 0) {
            response_buffer_ = value["message"] | "";
            service.receive_execution({value["request_id"] | "assistant", assistant_state_,
                                       response_buffer_, 0});
        } else if (std::strcmp(event_type, "plan.proposed") == 0 ||
                   (event_type[0] == '\0' &&
                    assistant_state_ == domain::ExecutionState::AwaitingConfirmation)) {
            domain::Plan plan;
            plan.plan_id = value["plan_id"] | "";
            plan.summary = value["summary"] | "";
            plan.risk = risk_level(value["risk"]);
            plan.revision = value["plan_revision"] | 1ULL;
            const std::uint64_t expires_in_ms =
                std::clamp<std::uint64_t>(value["expires_in_ms"] | 120000ULL, 0, 300000);
            plan.expires_at_ms = millis() + expires_in_ms;
            for (JsonObjectConst item : value["steps"].as<JsonArrayConst>()) {
                plan.steps.push_back({item["description"] | "", item["target"] | ""});
            }
            if (!plan.plan_id.empty()) service.receive_plan(std::move(plan));
        } else if (std::strcmp(event_type, "plan.resolved") == 0) {
            service.receive_plan_resolution(value["plan_id"] | "");
        }
    };
    auto spotify = [&](JsonObjectConst value) {
        domain::MediaState state;
        state.linked = value["linked"] | false;
        state.available = value["available"] | false;
        state.playing = value["playing"] | false;
        state.track_uri = value["track_uri"] | "";
        state.title = value["title"] | "";
        state.artist = value["artist"] | "";
        state.progress_ms = value["progress_ms"] | 0U;
        state.duration_ms = value["duration_ms"] | 0U;
        state.favorite = value["favorite"] | false;
        state.error_code = value["error_code"] | "";
        if (value["retry_after"].is<unsigned>()) {
            state.retry_after = value["retry_after"].as<unsigned>();
        }
        if (value["device"].is<JsonObjectConst>()) {
            JsonObjectConst item = value["device"];
            domain::MediaDevice device;
            device.id = item["id"] | "";
            device.name = item["name"] | "";
            device.type = item["type"] | "";
            device.active = item["active"] | false;
            device.restricted = item["restricted"] | false;
            device.supports_volume = item["supports_volume"] | false;
            if (item["volume"].is<unsigned>()) {
                device.volume = static_cast<std::uint8_t>(
                    std::clamp(item["volume"].as<int>(), 0, 100));
            }
            state.device = std::move(device);
        }
        service.receive_media(std::move(state));
    };
    auto weather = [&](JsonObjectConst value) {
        domain::WeatherState state;
        state.location = value["location"] | "";
        state.timezone = value["timezone"] | "";
        state.observed_at = value["observed_at"] | "";
        state.age_seconds = value["age_seconds"] | 0U;
        state.available = value["available"] | false;
        state.stale = value["stale"] | false;
        state.error_code = value["error_code"] | "";
        JsonObjectConst current = value["current"];
        if (current["temperature"].is<float>()) {
            state.temperature = current["temperature"].as<float>();
        }
        state.condition = current["condition"] | "";
        if (current["wind_kmh"].is<float>()) {
            state.wind_kmh = current["wind_kmh"].as<float>();
        }
        for (JsonObjectConst item : value["days"].as<JsonArrayConst>()) {
            if (state.days.size() >= 7U) break;
            domain::WeatherDay day;
            day.date = item["date"] | "";
            day.condition = item["condition"] | "";
            day.temperature_min = item["temperature_min"] | 0.0F;
            day.temperature_max = item["temperature_max"] | 0.0F;
            if (item["precipitation_probability"].is<unsigned>()) {
                day.precipitation_probability = static_cast<std::uint8_t>(
                    std::clamp(item["precipitation_probability"].as<int>(), 0, 100));
            }
            state.days.push_back(std::move(day));
        }
        service.receive_weather(std::move(state));
    };
    auto agenda = [&](JsonObjectConst value) {
        domain::AgendaState state;
        state.timezone = value["timezone"] | "";
        state.age_seconds = value["age_seconds"] | 0U;
        state.available = value["available"] | false;
        state.stale = value["stale"] | false;
        state.write_enabled = value["write_enabled"] | false;
        state.error_code = value["error_code"] | "";
        for (JsonObjectConst item : value["events"].as<JsonArrayConst>()) {
            if (state.events.size() >= 8U) break;
            const char* status = item["status"] | "confirmed";
            if (std::strcmp(status, "cancelled") == 0) continue;
            domain::CalendarEvent event;
            event.event_id = item["event_id"] | "";
            event.title = item["title"] | "";
            event.start = item["start"] | "";
            event.end = item["end"] | "";
            event.all_day = item["all_day"] | false;
            event.tentative = std::strcmp(status, "tentative") == 0;
            if (!event.event_id.empty() && !event.title.empty() && !event.start.empty()) {
                state.events.push_back(std::move(event));
            }
        }
        service.receive_agenda(std::move(state));
    };
    auto reminders = [&](JsonObjectConst value) {
        domain::ReminderState state;
        state.timezone = value["timezone"] | "";
        state.age_seconds = value["age_seconds"] | 0U;
        state.available = value["available"] | false;
        state.stale = value["stale"] | false;
        state.notifications_enabled = value["notifications_enabled"] | false;
        state.error_code = value["error_code"] | "";
        for (JsonObjectConst item : value["items"].as<JsonArrayConst>()) {
            if (state.items.size() >= 8U) break;
            const char* status = item["status"] | "active";
            if (std::strcmp(status, "active") != 0) continue;
            domain::ReminderItem reminder;
            reminder.reminder_id = item["reminder_id"] | "";
            reminder.text = item["text"] | "";
            reminder.due_at = item["due_at"] | "";
            reminder.recurrence = item["recurrence"] | "";
            if (!reminder.reminder_id.empty() && !reminder.text.empty() &&
                !reminder.due_at.empty()) {
                state.items.push_back(std::move(reminder));
            }
        }
        service.receive_reminders(std::move(state));
    };
    auto timers = [&](JsonObjectConst value) {
        domain::TimerState state;
        state.age_seconds = value["age_seconds"] | 0U;
        state.available = value["available"] | false;
        state.stale = value["stale"] | false;
        state.error_code = value["error_code"] | "";
        for (JsonObjectConst item : value["items"].as<JsonArrayConst>()) {
            if (state.items.size() >= 8U) break;
            const char* status = item["status"] | "";
            if (std::strcmp(status, "running") != 0 && std::strcmp(status, "paused") != 0) {
                continue;
            }
            domain::TimerItem timer;
            timer.timer_id = item["timer_id"] | "";
            timer.label = item["label"] | "";
            timer.status = status;
            timer.duration_seconds = item["duration_seconds"] | 0U;
            timer.remaining_seconds = item["remaining_seconds"] | 0U;
            timer.deadline_at = item["deadline_at"] | "";
            timer.preset = item["preset"] | "";
            if (!timer.timer_id.empty() && !timer.label.empty()) {
                state.items.push_back(std::move(timer));
            }
        }
        service.receive_timers(std::move(state));
    };

    if (std::strcmp(type, "projection.snapshot") == 0) {
        JsonObjectConst payload = document["payload"];
        replace_devices(payload["home"]["entities"].as<JsonArrayConst>());
        assistant(payload["assistant"].as<JsonObjectConst>(), "");
        spotify(payload["spotify"].as<JsonObjectConst>());
        weather(payload["weather"].as<JsonObjectConst>());
        agenda(payload["agenda"].as<JsonObjectConst>());
        reminders(payload["reminders"].as<JsonObjectConst>());
        timers(payload["timers"].as<JsonObjectConst>());
    } else if (std::strcmp(type, "projection.delta") == 0) {
        JsonObjectConst payload = document["payload"];
        last_event_id_ = payload["event_id"] | last_event_id_;
        JsonObjectConst changes = payload["changes"];
        const char* aggregate = payload["aggregate"] | "";
        if (std::strcmp(aggregate, "home") == 0 && changes["entities"].is<JsonArrayConst>()) {
            replace_devices(changes["entities"].as<JsonArrayConst>());
        } else if (std::strcmp(aggregate, "assistant") == 0) {
            assistant(changes, changes["event_type"] | "");
        } else if (std::strcmp(aggregate, "spotify") == 0) {
            spotify(changes);
        } else if (std::strcmp(aggregate, "weather") == 0) {
            weather(changes);
        } else if (std::strcmp(aggregate, "agenda") == 0) {
            agenda(changes);
        } else if (std::strcmp(aggregate, "reminders") == 0) {
            reminders(changes);
        } else if (std::strcmp(aggregate, "timers") == 0) {
            timers(changes);
        }
    } else if (std::strcmp(type, "execution.updated") == 0) {
        JsonObjectConst payload = document["payload"];
        service.receive_execution(
            {payload["request_id"] | "", execution_state(payload["state"] | ""),
             payload["state"] | "", 0});
    } else if (std::strcmp(type, "error") == 0) {
        service.receive_execution({"edge:error", domain::ExecutionState::Failed,
                                   document["payload"]["message"] | "Error de Wyss", 0});
    }
#else
    const char* type = document["type"] | "";
    if (std::strcmp(type, "state.snapshot") == 0) {
        std::vector<domain::DeviceState> devices;
        for (JsonObject item : document["devices"].as<JsonArray>()) {
            domain::DeviceState device;
            device.entity_id = item["entity_id"] | "";
            device.friendly_name = item["friendly_name"] | device.entity_id.c_str();
            device.available = item["available"] | false;
            device.on = item["on"] | false;
            device.brightness = static_cast<std::uint8_t>(std::clamp(item["brightness"] | 0, 0, 100));
            if (item["rgb"].is<unsigned>()) device.rgb = item["rgb"].as<unsigned>();
            device.revision = item["revision"] | 0ULL;
            devices.push_back(std::move(device));
        }
        service.replace_devices(std::move(devices));
    } else if (std::strcmp(type, "state.changed") == 0) {
        JsonObject item = document["device"];
        domain::DeviceState device;
        device.entity_id = item["entity_id"] | "";
        device.friendly_name = item["friendly_name"] | device.entity_id.c_str();
        device.available = item["available"] | false;
        device.on = item["on"] | false;
        device.brightness = static_cast<std::uint8_t>(std::clamp(item["brightness"] | 0, 0, 100));
        if (item["rgb"].is<unsigned>()) device.rgb = item["rgb"].as<unsigned>();
        device.revision = item["revision"] | 0ULL;
        service.reconcile_device(device);
    } else if (std::strcmp(type, "plan.proposed") == 0) {
        domain::Plan plan;
        plan.plan_id = document["plan_id"] | "";
        plan.summary = document["summary"] | "";
        plan.risk = static_cast<domain::RiskLevel>(std::clamp(document["risk"] | 0, 0, 3));
        const std::uint64_t expires_in_ms =
            std::clamp<std::uint64_t>(document["expires_in_ms"] | 120000ULL, 0, 300000);
        plan.expires_at_ms = millis() + expires_in_ms;
        for (JsonObject item : document["steps"].as<JsonArray>()) {
            plan.steps.push_back({item["description"] | "", item["target"] | ""});
        }
        service.receive_plan(std::move(plan));
    } else if (std::strcmp(type, "execution.update") == 0) {
        service.receive_execution({document["id"] | "", execution_state(document["state"] | ""),
                                   document["message"] | "", document["round_trip_ms"] | 0U});
    }
#endif
}

}  // namespace wyss::adapters
