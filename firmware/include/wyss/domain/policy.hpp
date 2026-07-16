#pragma once

#include <algorithm>
#include <array>
#include <string_view>

#include "wyss/domain/types.hpp"

namespace wyss::domain {

class EdgePolicy final {
   public:
    [[nodiscard]] static bool allows_fast_path(const FastCommand& command) noexcept {
        constexpr std::array<std::string_view, 5> kAllowed{
            "turn_on", "turn_off", "toggle", "set_brightness", "activate_scene"};
        const bool action_allowed =
            std::find(kAllowed.begin(), kAllowed.end(), command.action) != kAllowed.end();
        const bool target_allowed = command.entity_id.starts_with("light.") ||
                                    command.entity_id.starts_with("scene.");
        return action_allowed && target_allowed && !command.request_id.empty();
    }

    [[nodiscard]] static bool requires_confirmation(RiskLevel risk) noexcept {
        return risk == RiskLevel::B || risk == RiskLevel::C;
    }

    [[nodiscard]] static bool is_rejected(RiskLevel risk) noexcept {
        return risk == RiskLevel::D;
    }
};

}  // namespace wyss::domain

