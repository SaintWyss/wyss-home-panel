#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>

#include "wyss/ui/design_tokens.hpp"

namespace {
void require(bool condition) {
    if (!condition) std::abort();
}

double channel(std::uint8_t value) {
    const double normalized = static_cast<double>(value) / 255.0;
    return normalized <= 0.04045 ? normalized / 12.92
                                 : std::pow((normalized + 0.055) / 1.055, 2.4);
}

double luminance(std::uint32_t color) {
    return 0.2126 * channel(static_cast<std::uint8_t>(color >> 16)) +
           0.7152 * channel(static_cast<std::uint8_t>(color >> 8)) +
           0.0722 * channel(static_cast<std::uint8_t>(color));
}

double contrast(std::uint32_t first, std::uint32_t second) {
    const auto high = std::max(luminance(first), luminance(second));
    const auto low = std::min(luminance(first), luminance(second));
    return (high + 0.05) / (low + 0.05);
}

void palette_meets_wcag_aa() {
    using namespace wyss::ui::tokens;
    require(contrast(text, canvas) >= 4.5);
    require(contrast(muted, canvas) >= 4.5);
    require(contrast(text, surface) >= 4.5);
    require(contrast(cyan, canvas) >= 4.5);
    require(contrast(canvas, cyan) >= 4.5);
    require(contrast(red, canvas) >= 4.5);
}

void targets_are_large_and_inside_the_display() {
    using namespace wyss::ui::tokens;
    require(media_button_height >= min_touch_target);
    require(media_slider_height >= min_touch_target);
    constexpr std::array fixed_targets = {manual_button, power_button, brightness_slider};
    for (const auto& target : fixed_targets) {
        require(target.width >= min_touch_target);
        require(target.height >= min_touch_target);
        require(target.x >= 0 && target.y >= 0);
        require(target.x + target.width <= screen_width);
        require(target.y + target.height <= screen_height);
    }
    for (const auto& target : navigation) {
        require(target.width >= min_touch_target);
        require(target.height >= min_touch_target);
        require(target.x + target.width <= sidebar_width);
        require(target.y + target.height <= screen_height);
    }
    for (const auto& target : quick_actions) {
        require(target.width >= min_touch_target);
        require(target.height >= min_touch_target);
        require(target.x + target.width <= screen_width);
        require(target.y + target.height <= screen_height);
    }
    for (const auto& target : light_selectors) {
        require(target.width >= min_touch_target);
        require(target.height >= min_touch_target);
        require(target.x + target.width <= screen_width);
        require(target.y + target.height <= screen_height);
    }
    for (const auto& target : color_presets) {
        require(target.width >= min_touch_target);
        require(target.height >= min_touch_target);
        require(target.x + target.width <= screen_width);
        require(target.y + target.height <= screen_height);
    }
}

void refresh_and_brightness_budgets_are_explicit() {
    using namespace wyss::ui::tokens;
    require(active_refresh_ms <= 33);
    require(sleeping_refresh_ms >= 100 && sleeping_refresh_ms <= 200);
    require(sleeping_brightness > 0);
    require(sleeping_brightness < active_brightness);
}
}  // namespace

int main() {
    palette_meets_wcag_aa();
    targets_are_large_and_inside_the_display();
    refresh_and_brightness_budgets_are_explicit();
    return 0;
}
