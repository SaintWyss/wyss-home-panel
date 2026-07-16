#include <cassert>
#include <cstdint>
#include <string>
#include <vector>

#include "wyss/application/panel_service.hpp"

namespace {
class Clock final : public wyss::ports::Clock {
   public:
    [[nodiscard]] std::uint64_t now_ms() const noexcept override { return now; }
    std::uint64_t now{100};
};

class Commands final : public wyss::ports::CommandPort {
   public:
    bool send_fast(const wyss::domain::FastCommand& command) override {
        last_action = command.action;
        return succeeds;
    }
    bool send_intent(const wyss::domain::Intent&) override { return succeeds; }
    bool confirm(std::string_view, bool, wyss::domain::RiskLevel) override { return succeeds; }
    bool succeeds{true};
    std::string last_action;
};

class View final : public wyss::ports::ViewPort {
   public:
    void render_connection(wyss::domain::ConnectionState state) override { connection = state; }
    void render_devices(std::span<const wyss::domain::DeviceState> value) override {
        devices.assign(value.begin(), value.end());
        ++device_renders;
    }
    void render_execution(const wyss::domain::ExecutionUpdate& value) override {
        execution = value.state;
    }
    void render_plan(const wyss::domain::Plan&) override { ++plans; }
    void render_toast(std::string_view value, bool error) override {
        toast = value;
        toast_error = error;
    }
    wyss::domain::ConnectionState connection{wyss::domain::ConnectionState::Offline};
    wyss::domain::ExecutionState execution{wyss::domain::ExecutionState::Idle};
    std::vector<wyss::domain::DeviceState> devices;
    std::string toast;
    bool toast_error{false};
    unsigned device_renders{0};
    unsigned plans{0};
};

wyss::domain::DeviceState light(bool on = false, std::uint64_t revision = 1) {
    return {"light.living", "Living", true, on, 40, std::nullopt, revision};
}

void optimistic_state_is_immediate_and_reconciled() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.replace_devices({light()});
    service.fast_action("light.living", "turn_on");
    assert(view.devices.front().on);
    assert(view.execution == wyss::domain::ExecutionState::Optimistic);
    service.reconcile_device(light(true, 2));
    clock.now += 3'000;
    service.tick();
    assert(view.devices.front().on);
}

void failed_send_rolls_back_immediately() {
    Clock clock;
    Commands commands;
    commands.succeeds = false;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.replace_devices({light()});
    service.fast_action("light.living", "turn_on");
    assert(!view.devices.front().on);
    assert(view.toast_error);
}

void timeout_rolls_back_without_idle_redraws() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.replace_devices({light()});
    service.fast_action("light.living", "turn_on");
    const unsigned before_idle_tick = view.device_renders;
    service.tick();
    assert(view.device_renders == before_idle_tick);
    clock.now += 3'000;
    service.tick();
    assert(!view.devices.front().on);
}

void policy_rejects_unknown_edge_actions() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.replace_devices({light()});
    service.fast_action("lock.front_door", "unlock");
    assert(commands.last_action.empty());
    assert(view.toast_error);
}
}  // namespace

int main() {
    optimistic_state_is_immediate_and_reconciled();
    failed_send_rolls_back_immediately();
    timeout_rolls_back_without_idle_redraws();
    policy_rejects_unknown_edge_actions();
    return 0;
}

