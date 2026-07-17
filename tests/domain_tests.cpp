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
    bool confirm(std::string_view, bool, wyss::domain::RiskLevel, std::uint64_t revision) override {
        ++confirmations;
        confirmed_revision = revision;
        return succeeds;
    }
    bool succeeds{true};
    std::string last_action;
    unsigned confirmations{0};
    std::uint64_t confirmed_revision{0};
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

void color_targets_only_the_selected_light() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.replace_devices(
        {light(), {"light.desk", "Desk", true, false, 30, std::nullopt, 1}});
    service.fast_action("light.desk", "set_color", std::nullopt, 0x3366CCU);
    assert(!view.devices.front().on);
    assert(view.devices[1].on);
    assert(view.devices[1].rgb == 0x3366CCU);
    assert(commands.last_action == "set_color");
}

void policy_accepts_only_well_formed_scene_and_color_commands() {
    using wyss::domain::EdgePolicy;
    using wyss::domain::FastCommand;
    assert(EdgePolicy::allows_fast_path(
        FastCommand{"one", "scene.movie", "activate_scene", std::nullopt, std::nullopt, 1}));
    assert(EdgePolicy::allows_fast_path(
        FastCommand{"two", "light.desk", "set_color", std::nullopt, 0x3366CCU, 1}));
    assert(!EdgePolicy::allows_fast_path(
        FastCommand{"three", "scene.movie", "toggle", std::nullopt, std::nullopt, 1}));
    assert(!EdgePolicy::allows_fast_path(
        FastCommand{"four", "light.desk", "turn_on", 20, std::nullopt, 1}));
}

void shared_plan_resolution_clears_modal_authority_and_revision_is_forwarded() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.receive_plan({"plan-shared", "Plan", wyss::domain::RiskLevel::B, {}, 5'000, 7});
    service.receive_plan_resolution("plan-shared");
    service.answer_plan(true);
    assert(commands.confirmations == 0);

    service.receive_plan({"plan-next", "Plan", wyss::domain::RiskLevel::C, {}, 5'000, 9});
    service.answer_plan(true);
    assert(commands.confirmations == 1);
    assert(commands.confirmed_revision == 9);
}
}  // namespace

int main() {
    optimistic_state_is_immediate_and_reconciled();
    failed_send_rolls_back_immediately();
    timeout_rolls_back_without_idle_redraws();
    policy_rejects_unknown_edge_actions();
    color_targets_only_the_selected_light();
    policy_accepts_only_well_formed_scene_and_color_commands();
    shared_plan_resolution_clears_modal_authority_and_revision_is_forwarded();
    return 0;
}
