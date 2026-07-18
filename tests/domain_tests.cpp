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
        fast_commands.push_back(command);
        return succeeds;
    }
    bool send_media(const wyss::domain::MediaCommand& command) override {
        last_media_action = command.action;
        return succeeds;
    }
    bool send_intent(const wyss::domain::Intent&) override {
        ++intents;
        return succeeds;
    }
    bool confirm(std::string_view, bool, wyss::domain::RiskLevel, std::uint64_t revision) override {
        ++confirmations;
        confirmed_revision = revision;
        return succeeds;
    }
    bool succeeds{true};
    std::string last_action;
    std::string last_media_action;
    std::vector<wyss::domain::FastCommand> fast_commands;
    unsigned intents{0};
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
    void render_media(const wyss::domain::MediaState& value) override { media = value; }
    void render_weather(const wyss::domain::WeatherState& value) override { weather = value; }
    void render_agenda(const wyss::domain::AgendaState& value) override { agenda = value; }
    void render_reminders(const wyss::domain::ReminderState& value) override {
        reminders = value;
    }
    void render_timers(const wyss::domain::TimerState& value) override { timers = value; }
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
    wyss::domain::MediaState media;
    wyss::domain::WeatherState weather;
    wyss::domain::AgendaState agenda;
    wyss::domain::ReminderState reminders;
    wyss::domain::TimerState timers;
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

void home_quick_actions_use_the_authorized_fast_light_path() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.replace_devices(
        {light(),
         {"light.desk", "Desk", true, true, 70, std::nullopt, 1},
         {"light.offline", "Offline", false, true, 90, std::nullopt, 1},
         {"scene.movie", "Movie", true, false, 0, std::nullopt, 1}});

    service.quick_action(wyss::domain::HomeQuickAction::NightMode);
    assert(commands.intents == 0);
    assert(commands.fast_commands.size() == 2);
    for (const auto& command : commands.fast_commands) {
        assert(command.action == "set_brightness");
        assert(command.brightness == 20);
        assert(command.entity_id.starts_with("light."));
    }

    commands.fast_commands.clear();
    service.quick_action(wyss::domain::HomeQuickAction::AllOff);
    assert(commands.fast_commands.size() == 2);
    for (const auto& command : commands.fast_commands) {
        assert(command.action == "turn_off");
        assert(!command.brightness);
    }

    commands.fast_commands.clear();
    service.quick_action(wyss::domain::HomeQuickAction::Leaving);
    assert(commands.fast_commands.size() == 2);
    for (const auto& command : commands.fast_commands) {
        assert(command.action == "turn_off");
    }
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

void media_controls_are_validated_and_forwarded_without_provider_details() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    service.set_connection(wyss::domain::ConnectionState::Online);
    service.receive_media(
        {true,
         true,
         true,
         "spotify:track:test",
         "Tema",
         "Artista",
         0,
         0,
         false,
         wyss::domain::MediaDevice{"desk", "Escritorio", "Computer", true, false, true, 25}});
    assert(view.media.playing);

    service.media_action("pause");
    assert(commands.last_media_action == "pause");
    service.media_action("set_volume", 101U);
    assert(view.toast_error);
    assert(commands.last_media_action == "pause");
}

void weather_projection_is_forwarded_without_local_freshness_invention() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    wyss::domain::WeatherState weather{"Resistencia",
                                       "America/Argentina/Cordoba",
                                       "2026-07-17T20:45",
                                       7'201,
                                       true,
                                       true,
                                       19.5F,
                                       "lluvia",
                                       8.0F,
                                       {{"2026-07-17", "lluvia", 15.0F, 22.0F, 80}},
                                       "provider_unavailable"};
    service.receive_weather(weather);
    assert(view.weather.stale);
    assert(view.weather.age_seconds == 7'201);
    assert(view.weather.days.size() == 1);
    assert(view.weather.error_code == "provider_unavailable");
}

void calendar_projection_is_forwarded_without_oauth_or_local_authority() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    wyss::domain::AgendaState agenda{
        "America/Argentina/Cordoba",
        90,
        true,
        true,
        false,
        {{"opaque-1", "Reunion", "2026-07-18T10:00:00-03:00",
          "2026-07-18T11:00:00-03:00", false, false}},
        "provider_unavailable"};
    service.receive_agenda(agenda);
    assert(view.agenda.stale);
    assert(!view.agenda.write_enabled);
    assert(view.agenda.events.size() == 1);
    assert(view.agenda.events.front().title == "Reunion");
}

void reminder_projection_is_forwarded_without_local_scheduler_authority() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    wyss::domain::ReminderState reminders{
        "America/Argentina/Cordoba",
        15,
        true,
        false,
        false,
        {{"reminder-1", "Tomar medicacion", "2026-07-18T10:00:00-03:00", "FREQ=DAILY"}},
        ""};
    service.receive_reminders(reminders);
    assert(view.reminders.available);
    assert(!view.reminders.notifications_enabled);
    assert(view.reminders.items.front().recurrence == "FREQ=DAILY");
}

void timer_projection_is_forwarded_without_local_deadline_authority() {
    Clock clock;
    Commands commands;
    View view;
    wyss::application::PanelService service(clock, commands, view);
    wyss::domain::TimerState timers{15,
                                    true,
                                    false,
                                    {{"timer-1", "Horno", "running", 600, 300,
                                      "2026-07-18T01:05:00Z", "horno"}},
                                    ""};
    service.receive_timers(timers);
    assert(view.timers.available);
    assert(view.timers.items.front().remaining_seconds == 300);
    assert(view.timers.items.front().deadline_at == "2026-07-18T01:05:00Z");
}
}  // namespace

int main() {
    optimistic_state_is_immediate_and_reconciled();
    failed_send_rolls_back_immediately();
    timeout_rolls_back_without_idle_redraws();
    policy_rejects_unknown_edge_actions();
    color_targets_only_the_selected_light();
    home_quick_actions_use_the_authorized_fast_light_path();
    policy_accepts_only_well_formed_scene_and_color_commands();
    shared_plan_resolution_clears_modal_authority_and_revision_is_forwarded();
    media_controls_are_validated_and_forwarded_without_provider_details();
    weather_projection_is_forwarded_without_local_freshness_invention();
    calendar_projection_is_forwarded_without_oauth_or_local_authority();
    reminder_projection_is_forwarded_without_local_scheduler_authority();
    timer_projection_is_forwarded_without_local_deadline_authority();
    return 0;
}
