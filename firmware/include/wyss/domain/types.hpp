#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace wyss::domain {

enum class RiskLevel : std::uint8_t { A = 0, B = 1, C = 2, D = 3 };
enum class ConnectionState : std::uint8_t { Offline, Discovering, Pairing, Online, Degraded };
enum class HomeQuickAction : std::uint8_t { NightMode = 0, AllOff = 1, Leaving = 2 };

struct LocalDateTime {
    bool valid{false};
    std::uint32_t day_key{0};
    std::uint16_t minute_of_day{0};
};

struct DoorCheckState {
    bool closed{false};
    std::uint32_t confirmed_day{0};
    std::uint16_t confirmed_minute{0};
};
enum class ExecutionState : std::uint8_t {
    Idle,
    Optimistic,
    Planning,
    AwaitingConfirmation,
    Executing,
    Verified,
    Failed,
};

struct DeviceState {
    std::string entity_id;
    std::string friendly_name;
    bool available{false};
    bool on{false};
    std::uint8_t brightness{0};
    std::optional<std::uint32_t> rgb;
    std::uint64_t revision{0};

    [[nodiscard]] bool newer_than(const DeviceState& other) const noexcept {
        return revision > other.revision;
    }
};

struct FastCommand {
    std::string request_id;
    std::string entity_id;
    std::string action;
    std::optional<std::uint8_t> brightness;
    std::optional<std::uint32_t> rgb;
    std::uint64_t issued_at_ms{0};
};

struct MediaDevice {
    std::string id;
    std::string name;
    std::string type;
    bool active{false};
    bool restricted{false};
    bool supports_volume{false};
    std::optional<std::uint8_t> volume;
};

struct MediaTrack {
    std::string title;
    std::string artist;
};

struct MediaState {
    bool linked{false};
    bool available{false};
    bool playing{false};
    std::string track_uri;
    std::string title;
    std::string artist;
    std::uint32_t progress_ms{0};
    std::uint32_t duration_ms{0};
    bool favorite{false};
    std::optional<MediaDevice> device;
    std::string error_code;
    std::optional<std::uint32_t> retry_after;
    std::vector<MediaTrack> queue;
};

struct MediaCommand {
    std::string request_id;
    std::string action;
    std::optional<std::uint8_t> value;
    std::string device_id;
    std::uint64_t issued_at_ms{0};
};

struct WeatherDay {
    std::string date;
    std::string condition;
    float temperature_min{0};
    float temperature_max{0};
    std::optional<std::uint8_t> precipitation_probability;
};

struct WeatherState {
    std::string location;
    std::string timezone;
    std::string observed_at;
    std::uint32_t age_seconds{0};
    bool available{false};
    bool stale{false};
    std::optional<float> temperature;
    std::string condition;
    std::optional<float> wind_kmh;
    std::vector<WeatherDay> days;
    std::string error_code;
};

struct CalendarEvent {
    std::string event_id;
    std::string title;
    std::string start;
    std::string end;
    bool all_day{false};
    bool tentative{false};
};

struct AgendaState {
    std::string timezone;
    std::uint32_t age_seconds{0};
    bool available{false};
    bool stale{false};
    bool write_enabled{false};
    std::vector<CalendarEvent> events;
    std::string error_code;
};

struct ReminderItem {
    std::string reminder_id;
    std::string text;
    std::string due_at;
    std::string recurrence;
};

struct ReminderState {
    std::string timezone;
    std::uint32_t age_seconds{0};
    bool available{false};
    bool stale{false};
    bool notifications_enabled{false};
    std::vector<ReminderItem> items;
    std::string error_code;
};

struct TimerItem {
    std::string timer_id;
    std::string label;
    std::string status;
    std::uint32_t duration_seconds{0};
    std::uint32_t remaining_seconds{0};
    std::string deadline_at;
    std::string preset;
};

struct TimerState {
    std::uint32_t age_seconds{0};
    bool available{false};
    bool stale{false};
    std::vector<TimerItem> items;
    std::string error_code;
};

struct Intent {
    std::string request_id;
    std::string text;
    std::uint64_t issued_at_ms{0};
};

struct PlanStep {
    std::string description;
    std::string target;
};

struct Plan {
    std::string plan_id;
    std::string summary;
    RiskLevel risk{RiskLevel::A};
    std::vector<PlanStep> steps;
    std::uint64_t expires_at_ms{0};
    std::uint64_t revision{1};
};

struct ExecutionUpdate {
    std::string request_id;
    ExecutionState state{ExecutionState::Idle};
    std::string message;
    std::uint32_t round_trip_ms{0};
};

struct Telemetry {
    std::uint32_t uptime_s{0};
    std::uint32_t heap_free{0};
    std::uint32_t heap_min{0};
    std::uint16_t fps_x10{0};
    std::uint16_t touch_to_paint_ms{0};
    std::uint16_t command_rtt_ms{0};
    std::int8_t wifi_rssi{0};
};

}  // namespace wyss::domain
