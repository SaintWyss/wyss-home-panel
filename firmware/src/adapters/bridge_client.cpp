#include "wyss/adapters/bridge_client.hpp"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>

#include <algorithm>
#include <cstring>
#include <optional>
#include <string>
#include <vector>

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
    endpoint.path = slash == std::string_view::npos ? "/v1/panel" : String(remainder.substr(slash).data());
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
    if (std::strcmp(value, "planning") == 0) return domain::ExecutionState::Planning;
    if (std::strcmp(value, "awaiting_confirmation") == 0)
        return domain::ExecutionState::AwaitingConfirmation;
    if (std::strcmp(value, "executing") == 0) return domain::ExecutionState::Executing;
    if (std::strcmp(value, "verified") == 0) return domain::ExecutionState::Verified;
    if (std::strcmp(value, "failed") == 0) return domain::ExecutionState::Failed;
    return domain::ExecutionState::Idle;
}
}  // namespace

BridgeClient::BridgeClient(const ports::ConfigStorePort& config) : config_(config) {}

BridgeClient::~BridgeClient() {
    if (task_ != nullptr) {
        vTaskDelete(task_);
    }
    if (outbound_ != nullptr) vQueueDelete(outbound_);
    if (inbound_ != nullptr) vQueueDelete(inbound_);
}

bool BridgeClient::begin() {
    const auto endpoint = parse_endpoint(config_.bridge_url());
    if (!endpoint) {
        return false;
    }
    outbound_ = xQueueCreate(12, sizeof(Message));
    inbound_ = xQueueCreate(12, sizeof(Message));
    if (outbound_ == nullptr || inbound_ == nullptr) {
        return false;
    }

    auth_header_ = "Authorization: Bearer ";
    auth_header_ += config_.device_token().data();
    auth_header_ += "\r\nX-Wyss-Panel: ";
    auth_header_ += config_.panel_id().data();
    auth_header_ += "\r\n";
    socket_.setExtraHeaders(auth_header_.c_str());
    socket_.onEvent([this](WStype_t type, std::uint8_t* payload, std::size_t length) {
        handle_socket_event(type, payload, length);
    });
    socket_.setReconnectInterval(1000);
    socket_.enableHeartbeat(12000, 3000, 2);
    socket_.beginSslWithCA(endpoint->host.c_str(), endpoint->port, endpoint->path.c_str(),
                           config_.ca_certificate().data());
    state_.store(domain::ConnectionState::Discovering);
    return xTaskCreatePinnedToCore(task_entry, "wyss-network", 12288, this, 4, &task_, 0) == pdPASS;
}

void BridgeClient::task_entry(void* context) { static_cast<BridgeClient*>(context)->run(); }

void BridgeClient::run() {
    Message message{};
    for (;;) {
        socket_.loop();
        while (xQueueReceive(outbound_, &message, 0) == pdTRUE) {
            if (socket_.isConnected()) {
                socket_.sendTXT(message.text);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}

void BridgeClient::handle_socket_event(WStype_t type, std::uint8_t* payload, std::size_t length) {
    if (type == WStype_CONNECTED) {
        state_.store(domain::ConnectionState::Online);
        JsonDocument hello;
        hello["v"] = 1;
        hello["type"] = "hello";
        hello["panel_id"] = config_.panel_id();
        hello["firmware"] = "1.0.0";
        char json[256]{};
        const std::size_t written = serializeJson(hello, json, sizeof(json));
        enqueue_json(json, written);
    } else if (type == WStype_DISCONNECTED) {
        state_.store(domain::ConnectionState::Offline);
    } else if (type == WStype_TEXT && payload != nullptr && length < kMaxMessageBytes) {
        Message message{};
        std::memcpy(message.text, payload, length);
        message.text[length] = '\0';
        xQueueSend(inbound_, &message, 0);
    }
}

bool BridgeClient::enqueue_json(const char* json, std::size_t length) {
    if (outbound_ == nullptr || length == 0 || length >= kMaxMessageBytes) {
        return false;
    }
    Message message{};
    std::memcpy(message.text, json, length);
    message.text[length] = '\0';
    return xQueueSend(outbound_, &message, 0) == pdTRUE;
}

bool BridgeClient::send_fast(const domain::FastCommand& command) {
    JsonDocument document;
    document["v"] = 1;
    document["type"] = "command.fast";
    document["id"] = command.request_id;
    document["sent_at_ms"] = command.issued_at_ms;
    document["entity_id"] = command.entity_id;
    document["action"] = command.action;
    if (command.brightness) document["brightness"] = *command.brightness;
    if (command.rgb) document["rgb"] = *command.rgb;
    char json[512]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
}

bool BridgeClient::send_intent(const domain::Intent& intent) {
    JsonDocument document;
    document["v"] = 1;
    document["type"] = "intent.submit";
    document["id"] = intent.request_id;
    document["sent_at_ms"] = intent.issued_at_ms;
    document["text"] = intent.text;
    char json[1024]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
}

bool BridgeClient::confirm(std::string_view plan_id, bool accepted, domain::RiskLevel risk) {
    JsonDocument document;
    document["v"] = 1;
    document["type"] = "plan.answer";
    document["plan_id"] = plan_id;
    document["accepted"] = accepted;
    document["risk"] = static_cast<unsigned>(risk);
    char json[384]{};
    return enqueue_json(json, serializeJson(document, json, sizeof(json)));
}

void BridgeClient::poll(application::PanelService& service) {
    const auto state = state_.load();
    if (state != rendered_state_) {
        rendered_state_ = state;
        service.set_connection(state);
    }
    Message message{};
    for (unsigned count = 0; count < 6 && xQueueReceive(inbound_, &message, 0) == pdTRUE; ++count) {
        dispatch(service, message.text);
    }
}

void BridgeClient::dispatch(application::PanelService& service, const char* json) {
    JsonDocument document;
    if (deserializeJson(document, json) != DeserializationError::Ok) {
        return;
    }
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
}

}  // namespace wyss::adapters
