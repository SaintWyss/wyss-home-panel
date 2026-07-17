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
