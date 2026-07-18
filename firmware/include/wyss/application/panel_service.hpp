#pragma once

#include <deque>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "wyss/domain/policy.hpp"
#include "wyss/ports/ports.hpp"

namespace wyss::application {

class PanelService final {
   public:
    PanelService(ports::Clock& clock, ports::CommandPort& commands, ports::ViewPort& view);

    void set_connection(domain::ConnectionState state);
    void replace_devices(std::vector<domain::DeviceState> devices);
    void reconcile_device(const domain::DeviceState& state);
    void receive_media(domain::MediaState state);
    void receive_weather(domain::WeatherState state);
    void receive_agenda(domain::AgendaState state);
    void receive_reminders(domain::ReminderState state);
    void receive_timers(domain::TimerState state);
    void media_action(std::string action, std::optional<std::uint8_t> value = std::nullopt,
                      std::string device_id = {});
    void fast_action(std::string entity_id, std::string action,
                     std::optional<std::uint8_t> brightness = std::nullopt,
                     std::optional<std::uint32_t> rgb = std::nullopt);
    void quick_action(domain::HomeQuickAction action);
    void submit_intent(std::string text);
    void receive_plan(domain::Plan plan);
    void receive_plan_resolution(std::string_view plan_id);
    void answer_plan(bool accepted);
    void receive_execution(domain::ExecutionUpdate update);
    void tick();

    [[nodiscard]] const std::vector<domain::DeviceState>& devices() const noexcept;

   private:
    struct OptimisticState {
        domain::DeviceState before;
        std::uint64_t expires_at_ms;
    };

    struct QueuedQuickAction {
        std::string entity_id;
        std::string action;
        std::optional<std::uint8_t> brightness;
    };

    [[nodiscard]] std::string next_request_id();
    void apply_optimistic(const domain::FastCommand& command);
    void dispatch_quick_action();
    void rollback(std::string_view entity_id, std::string_view message);
    void rollback_expired();

    ports::Clock& clock_;
    ports::CommandPort& commands_;
    ports::ViewPort& view_;
    domain::ConnectionState connection_{domain::ConnectionState::Offline};
    std::vector<domain::DeviceState> devices_;
    std::unordered_map<std::string, OptimisticState> optimistic_;
    std::deque<QueuedQuickAction> queued_quick_actions_;
    std::uint64_t next_quick_action_at_ms_{0};
    std::optional<domain::Plan> pending_plan_;
    domain::MediaState media_;
    std::uint32_t sequence_{0};
};

}  // namespace wyss::application
