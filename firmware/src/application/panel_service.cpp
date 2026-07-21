#include "wyss/application/panel_service.hpp"

#include <algorithm>
#include <cstdio>
#include <utility>

namespace wyss::application {
namespace {
constexpr std::uint64_t kOptimisticTimeoutMs = 2500;
constexpr std::uint64_t kQuickActionIntervalMs = 100;
}

PanelService::PanelService(ports::Clock& clock, ports::CommandPort& commands,
                           ports::ViewPort& view)
    : clock_(clock), commands_(commands), view_(view) {}

void PanelService::set_connection(domain::ConnectionState state) {
    connection_ = state;
    if (state != domain::ConnectionState::Online) {
        queued_quick_actions_.clear();
    }
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

void PanelService::receive_timers(domain::TimerState state) {
    view_.render_timers(state);
}

void PanelService::configure_door_check(ports::LocalTimePort& local_time,
                                        ports::DoorCheckStorePort& store) {
    local_time_ = &local_time;
    door_check_store_ = &store;
    door_check_ = store.load_door_check();
    next_door_check_refresh_ms_ = 0;
    refresh_door_check();
}

void PanelService::toggle_door_check() {
    if (local_time_ == nullptr || door_check_store_ == nullptr) {
        view_.render_toast("El check de puerta no esta disponible", true);
        return;
    }

    const auto before = door_check_;
    const auto now = local_time_->now_local();
    door_check_.closed = !door_check_.closed;
    if (door_check_.closed) {
        door_check_.confirmed_day = now.valid ? now.day_key : 0U;
        door_check_.confirmed_minute = now.valid ? now.minute_of_day : 0U;
    } else {
        door_check_.confirmed_day = 0U;
        door_check_.confirmed_minute = 0U;
    }

    if (!door_check_store_->save_door_check(door_check_)) {
        door_check_ = before;
        view_.render_toast("No pude guardar el check de la puerta", true);
        view_.render_door_check(door_check_);
        return;
    }
    view_.render_door_check(door_check_);
    view_.render_toast(door_check_.closed ? "Puerta marcada como cerrada"
                                         : "Check de puerta pendiente",
                       false);
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

void PanelService::quick_action(domain::HomeQuickAction action) {
    if (connection_ != domain::ConnectionState::Online) {
        view_.render_toast("Wyss está sin conexión", true);
        return;
    }
    std::vector<std::string> targets;
    targets.reserve(devices_.size());
    for (const auto& device : devices_) {
        if (device.available && device.entity_id.starts_with("light.")) {
            targets.push_back(device.entity_id);
        }
    }
    if (targets.empty()) {
        view_.render_toast("No hay luces disponibles para esa acción", true);
        return;
    }

    queued_quick_actions_.clear();
    for (auto& entity_id : targets) {
        if (action == domain::HomeQuickAction::NightMode) {
            queued_quick_actions_.push_back(
                {std::move(entity_id), "set_brightness", 20U});
        } else {
            queued_quick_actions_.push_back({std::move(entity_id), "turn_off", std::nullopt});
        }
    }
    next_quick_action_at_ms_ = clock_.now_ms();
    dispatch_quick_action();
}

void PanelService::resync() {
    view_.render_toast("Recargando estado…", false);
    commands_.request_resync();
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

void PanelService::tick() {
    rollback_expired();
    dispatch_quick_action();
    if (local_time_ != nullptr && door_check_store_ != nullptr &&
        clock_.now_ms() >= next_door_check_refresh_ms_) {
        refresh_door_check();
        next_door_check_refresh_ms_ = clock_.now_ms() + 1'000U;
    }
}

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

void PanelService::dispatch_quick_action() {
    if (queued_quick_actions_.empty() || clock_.now_ms() < next_quick_action_at_ms_) {
        return;
    }
    auto action = std::move(queued_quick_actions_.front());
    queued_quick_actions_.pop_front();
    fast_action(std::move(action.entity_id), std::move(action.action), action.brightness);
    next_quick_action_at_ms_ = clock_.now_ms() + kQuickActionIntervalMs;
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

void PanelService::refresh_door_check() {
    if (local_time_ == nullptr || door_check_store_ == nullptr) return;

    const auto now = local_time_->now_local();
    if (!now.valid || !door_check_.closed) {
        view_.render_door_check(door_check_);
        return;
    }

    const auto before = door_check_;
    if (door_check_.confirmed_day == 0U) {
        // El usuario confirmo antes de que NTP estuviera listo: adoptar el dia real sin perderlo.
        door_check_.confirmed_day = now.day_key;
        door_check_.confirmed_minute = now.minute_of_day;
    } else if (door_check_.confirmed_day != now.day_key) {
        // El check es deliberadamente diario; nunca arrastrar una confirmacion de ayer.
        door_check_ = {};
    }

    if (door_check_.closed != before.closed ||
        door_check_.confirmed_day != before.confirmed_day ||
        door_check_.confirmed_minute != before.confirmed_minute) {
        if (!door_check_store_->save_door_check(door_check_)) {
            door_check_ = before;
            view_.render_toast("No pude actualizar el check diario", true);
        }
    }
    view_.render_door_check(door_check_);
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
