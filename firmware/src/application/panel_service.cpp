#include "wyss/application/panel_service.hpp"

#include <algorithm>
#include <cstdio>
#include <utility>

namespace wyss::application {
namespace {
constexpr std::uint64_t kOptimisticTimeoutMs = 2500;
}

PanelService::PanelService(ports::Clock& clock, ports::CommandPort& commands,
                           ports::ViewPort& view)
    : clock_(clock), commands_(commands), view_(view) {}

void PanelService::set_connection(domain::ConnectionState state) {
    connection_ = state;
    view_.render_connection(state);
}

void PanelService::replace_devices(std::vector<domain::DeviceState> devices) {
    devices_ = std::move(devices);
    optimistic_.clear();
    view_.render_devices(devices_);
}

void PanelService::reconcile_device(const domain::DeviceState& state) {
    const auto found = std::find_if(devices_.begin(), devices_.end(), [&](const auto& current) {
        return current.entity_id == state.entity_id;
    });
    if (found == devices_.end()) {
        devices_.push_back(state);
    } else if (state.newer_than(*found) || optimistic_.contains(state.entity_id)) {
        *found = state;
    }
    optimistic_.erase(state.entity_id);
    view_.render_devices(devices_);
}

void PanelService::receive_media(domain::MediaState state) {
    media_ = std::move(state);
    view_.render_media(media_);
}

void PanelService::receive_weather(domain::WeatherState state) {
    view_.render_weather(state);
}

void PanelService::receive_agenda(domain::AgendaState state) {
    view_.render_agenda(state);
}

void PanelService::receive_reminders(domain::ReminderState state) {
    view_.render_reminders(state);
}

void PanelService::media_action(std::string action, std::optional<std::uint8_t> value,
                                std::string device_id) {
    const bool plain = action == "play" || action == "pause" || action == "previous" ||
                       action == "next" || action == "toggle_favorite";
    const bool volume = action == "set_volume" && value.has_value() && *value <= 100U;
    const bool transfer = action == "transfer_device" && !device_id.empty();
    if ((!plain && !volume && !transfer) || (plain && (value || !device_id.empty())) ||
        (volume && !device_id.empty()) || (transfer && value)) {
        view_.render_toast("La política local bloqueó esa acción de media", true);
        return;
    }
    if (connection_ != domain::ConnectionState::Online) {
        view_.render_toast("Wyss está sin conexión", true);
        return;
    }
    if (!media_.linked ||
        (!transfer &&
         (!media_.available || !media_.device || !media_.device->active ||
          media_.device->restricted)) ||
        (volume && (!media_.device || !media_.device->supports_volume))) {
        view_.render_toast("Spotify no tiene un dispositivo controlable", true);
        return;
    }
    domain::MediaCommand command{next_request_id(), std::move(action), value,
                                 std::move(device_id), clock_.now_ms()};
    view_.render_execution({command.request_id, domain::ExecutionState::Optimistic,
                            "Aplicando en Spotify…", 0});
    if (!commands_.send_media(command)) {
        view_.render_toast("No pude enviar la acción de Spotify", true);
    }
}

void PanelService::fast_action(std::string entity_id, std::string action,
                               std::optional<std::uint8_t> brightness,
                               std::optional<std::uint32_t> rgb) {
    domain::FastCommand command{next_request_id(), std::move(entity_id), std::move(action),
                                brightness, rgb, clock_.now_ms()};
    if (!domain::EdgePolicy::allows_fast_path(command)) {
        view_.render_toast("La política local bloqueó esa acción", true);
        return;
    }
    if (connection_ != domain::ConnectionState::Online) {
        view_.render_toast("Wyss está sin conexión", true);
        return;
    }

    apply_optimistic(command);
    view_.render_devices(devices_);
    view_.render_execution({command.request_id, domain::ExecutionState::Optimistic,
                            "Aplicando…", 0});
    if (!commands_.send_fast(command)) {
        rollback(command.entity_id, "No pude enviar la acción");
    }
}

void PanelService::submit_intent(std::string text) {
    if (text.empty()) {
        return;
    }
    domain::Intent intent{next_request_id(), std::move(text), clock_.now_ms()};
    view_.render_execution(
        {intent.request_id, domain::ExecutionState::Planning, "Wyss está planificando…", 0});
    if (!commands_.send_intent(intent)) {
        view_.render_toast("No pude enviar la intención", true);
    }
}

void PanelService::receive_plan(domain::Plan plan) {
    if (domain::EdgePolicy::is_rejected(plan.risk)) {
        view_.render_execution(
            {plan.plan_id, domain::ExecutionState::Failed, "La política rechazó el plan", 0});
        return;
    }
    pending_plan_ = std::move(plan);
    view_.render_plan(*pending_plan_);
}

void PanelService::receive_plan_resolution(std::string_view plan_id) {
    if (pending_plan_ && pending_plan_->plan_id == plan_id) {
        pending_plan_.reset();
    }
}

void PanelService::answer_plan(bool accepted) {
    if (!pending_plan_) {
        return;
    }
    const auto plan = *pending_plan_;
    if (plan.expires_at_ms != 0 && plan.expires_at_ms <= clock_.now_ms()) {
        pending_plan_.reset();
        view_.render_toast("El plan venció; pedí uno nuevo", true);
        return;
    }
    if (!commands_.confirm(plan.plan_id, accepted, plan.risk, plan.revision)) {
        view_.render_toast("No pude responder la confirmación", true);
        return;
    }
    pending_plan_.reset();
    view_.render_execution({plan.plan_id,
                            accepted ? domain::ExecutionState::Executing
                                     : domain::ExecutionState::Failed,
                            accepted ? "Ejecutando el plan…" : "Plan cancelado", 0});
}

void PanelService::receive_execution(domain::ExecutionUpdate update) {
    view_.render_execution(update);
}

void PanelService::tick() { rollback_expired(); }

const std::vector<domain::DeviceState>& PanelService::devices() const noexcept { return devices_; }

std::string PanelService::next_request_id() {
    char buffer[48]{};
    std::snprintf(buffer, sizeof(buffer), "panel-%llu-%lu",
                  static_cast<unsigned long long>(clock_.now_ms()),
                  static_cast<unsigned long>(++sequence_));
    return buffer;
}

void PanelService::apply_optimistic(const domain::FastCommand& command) {
    const auto found = std::find_if(devices_.begin(), devices_.end(), [&](const auto& current) {
        return current.entity_id == command.entity_id;
    });
    if (found == devices_.end()) {
        return;
    }
    optimistic_[command.entity_id] = {*found, clock_.now_ms() + kOptimisticTimeoutMs};
    if (command.action == "turn_on") {
        found->on = true;
    } else if (command.action == "turn_off") {
        found->on = false;
    } else if (command.action == "toggle") {
        found->on = !found->on;
    } else if (command.action == "set_brightness" && command.brightness) {
        found->on = *command.brightness > 0;
        found->brightness = *command.brightness;
    } else if (command.action == "set_color" && command.rgb) {
        found->on = true;
        found->rgb = command.rgb;
    }
}

void PanelService::rollback_expired() {
    const auto now = clock_.now_ms();
    bool changed = false;
    for (auto it = optimistic_.begin(); it != optimistic_.end();) {
        if (it->second.expires_at_ms > now) {
            ++it;
            continue;
        }
        const auto found = std::find_if(devices_.begin(), devices_.end(), [&](const auto& current) {
            return current.entity_id == it->first;
        });
        if (found != devices_.end()) {
            *found = it->second.before;
        }
        it = optimistic_.erase(it);
        changed = true;
        view_.render_toast("No recibí confirmación; restauré el estado", true);
    }
    if (changed) {
        view_.render_devices(devices_);
    }
}

void PanelService::rollback(std::string_view entity_id, std::string_view message) {
    const auto optimistic = optimistic_.find(std::string(entity_id));
    if (optimistic != optimistic_.end()) {
        const auto device = std::find_if(devices_.begin(), devices_.end(), [&](const auto& current) {
            return current.entity_id == entity_id;
        });
        if (device != devices_.end()) {
            *device = optimistic->second.before;
        }
        optimistic_.erase(optimistic);
        view_.render_devices(devices_);
    }
    view_.render_toast(message, true);
}

}  // namespace wyss::application
