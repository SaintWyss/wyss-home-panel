#pragma once

#include <array>
#include <cstdint>

namespace wyss::ui {

struct Rect {
    std::int16_t x;
    std::int16_t y;
    std::int16_t width;
    std::int16_t height;
};

namespace tokens {
inline constexpr std::int16_t screen_width = 800;
inline constexpr std::int16_t screen_height = 480;
inline constexpr std::int16_t header_height = 64;
inline constexpr std::int16_t min_touch_target = 44;
inline constexpr std::int16_t control_gap = 8;
inline constexpr std::int16_t radius = 10;
inline constexpr std::uint32_t active_refresh_ms = 33;
inline constexpr std::uint32_t sleeping_refresh_ms = 125;
inline constexpr std::uint32_t sleeping_after_ms = 300'000;
inline constexpr std::uint8_t active_brightness = 100;
inline constexpr std::uint8_t sleeping_brightness = 18;

inline constexpr std::uint32_t canvas = 0x07101F;
inline constexpr std::uint32_t surface = 0x111D30;
inline constexpr std::uint32_t surface_raised = 0x18263C;
inline constexpr std::uint32_t text = 0xF7FAFF;
inline constexpr std::uint32_t muted = 0xA9B9D0;
inline constexpr std::uint32_t cyan = 0x2EE6D6;
inline constexpr std::uint32_t blue = 0x4F7CFF;
inline constexpr std::uint32_t green = 0x45D483;
inline constexpr std::uint32_t amber = 0xFFC857;
inline constexpr std::uint32_t red = 0xFF6B7A;
inline constexpr std::uint32_t border = 0x314968;

inline constexpr std::array<Rect, 5> navigation = {
    Rect{142, 8, 86, 48}, Rect{234, 8, 86, 48}, Rect{326, 8, 86, 48},
    Rect{418, 8, 86, 48}, Rect{510, 8, 86, 48},
};
inline constexpr Rect manual_button{310, 382, 180, 58};
inline constexpr Rect power_button{20, 119, 150, 112};
inline constexpr Rect brightness_slider{210, 164, 380, 48};
inline constexpr std::array<Rect, 3> light_selectors = {
    Rect{40, 116, 210, 54}, Rect{40, 178, 210, 54}, Rect{40, 240, 210, 54},
};
inline constexpr std::array<Rect, 4> color_presets = {
    Rect{500, 222, 54, 48}, Rect{562, 222, 54, 48}, Rect{624, 222, 54, 48},
    Rect{686, 222, 54, 48},
};
inline constexpr std::array<Rect, 3> quick_actions = {
    Rect{20, 324, 232, 66}, Rect{284, 324, 232, 66}, Rect{548, 324, 232, 66},
};
}  // namespace tokens

enum class ShellMode : std::uint8_t { Sleeping, Manual, Conversation };
enum class ManualPage : std::uint8_t { Inicio, Hogar, Media, Agenda, Sistema };

}  // namespace wyss::ui
