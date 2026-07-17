#pragma once

#include <algorithm>
#include <array>
#include <string_view>

#include "wyss/domain/types.hpp"

namespace wyss::domain {

class EdgePolicy final {
   public:
    [[nodiscard]] static bool allows_fast_path(const FastCommand& command) noexcept {
        constexpr std::array<std::string_view, 6> kAllowed{
            "turn_on", "turn_off", "toggle", "set_brightness", "set_color",
            "activate_scene"};
        const bool action_allowed =
            std::find(kAllowed.begin(), kAllowed.end(), command.action) != kAllowed.end();
        const bool target_allowed = command.entity_id.starts_with("light.") ||
                                    command.entity_id.starts_with("scene.");
        if (!action_allowed || !target_allowed || command.request_id.empty()) return false;
        const bool scene = command.entity_id.starts_with("scene.");
        if (command.action == "activate_scene") {
            return scene && !command.brightness && !command.rgb;
        }
        if (scene) return false;
        if (command.action == "set_brightness") {
            return command.brightness.has_value() && !command.rgb;
        }
        if (command.action == "set_color") {
            return command.rgb.has_value() && *command.rgb <= 0xFFFFFFU && !command.brightness;
        }
        return !command.brightness && !command.rgb;
    }

    [[nodiscard]] static bool requires_confirmation(RiskLevel risk) noexcept {
        return risk == RiskLevel::B || risk == RiskLevel::C;
    }

    [[nodiscard]] static bool is_rejected(RiskLevel risk) noexcept {
        return risk == RiskLevel::D;
    }
};

}  // namespace wyss::domain
