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
inline constexpr std::int16_t media_button_height = 58;
inline constexpr std::int16_t media_slider_height = 48;
inline constexpr std::int16_t control_gap = 8;
inline constexpr std::int16_t radius = 10;
inline constexpr std::uint32_t active_refresh_ms = 33;
inline constexpr std::uint32_t sleeping_refresh_ms = 125;
inline constexpr std::uint32_t sleeping_after_ms = 300'000;
inline constexpr std::uint8_t active_brightness = 100;
inline constexpr std::uint8_t sleeping_brightness = 18;

inline constexpr std::uint32_t canvas = 0xF3EDE3;
inline constexpr std::uint32_t surface = 0xFAF6EE;
inline constexpr std::uint32_t surface_raised = 0xFFFFFF;
inline constexpr std::uint32_t text = 0x2E2521;
inline constexpr std::uint32_t muted = 0x96887B;
inline constexpr std::uint32_t cyan = 0xE2604B;
inline constexpr std::uint32_t blue = 0xC24E3B;
inline constexpr std::uint32_t green = 0x3E9B6C;
inline constexpr std::uint32_t amber = 0xC98A2B;
inline constexpr std::uint32_t red = 0xB84034;
inline constexpr std::uint32_t border = 0xE6DACA;
inline constexpr std::uint32_t soft = 0xF7DFD4;

inline constexpr std::array<Rect, 5> navigation = {
    Rect{12, 86, 148, 50},  Rect{12, 144, 148, 50}, Rect{12, 202, 148, 50},
    Rect{12, 260, 148, 50}, Rect{12, 318, 148, 50},
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
    Rect{16, 316, 180, 56}, Rect{212, 316, 180, 56}, Rect{408, 316, 180, 56},
};
}  // namespace tokens

enum class ShellMode : std::uint8_t { Sleeping, Manual, Conversation };
enum class ManualPage : std::uint8_t { Inicio, Hogar, Media, Agenda, Sistema };

}  // namespace wyss::ui
