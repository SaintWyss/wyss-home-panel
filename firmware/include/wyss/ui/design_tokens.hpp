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
// Rail de iconos: reemplaza a la sidebar ancha y libera 108 px de contenido.
inline constexpr std::int16_t sidebar_width = 64;
inline constexpr std::int16_t min_touch_target = 44;
inline constexpr std::int16_t media_button_height = 58;
inline constexpr std::int16_t media_slider_height = 48;
inline constexpr std::int16_t control_gap = 8;
// Radio de tile: lenguaje de widgets redondeados.
inline constexpr std::int16_t radius = 22;
inline constexpr std::uint32_t active_refresh_ms = 33;
inline constexpr std::uint32_t sleeping_refresh_ms = 125;
inline constexpr std::uint32_t sleeping_after_ms = 300'000;
inline constexpr std::uint8_t active_brightness = 100;
inline constexpr std::uint8_t sleeping_brightness = 18;

// Base calida.
inline constexpr std::uint32_t canvas = 0xF4EFE6;
inline constexpr std::uint32_t surface = 0xFFFFFF;
inline constexpr std::uint32_t surface_raised = 0xFFFFFF;
inline constexpr std::uint32_t text = 0x2A211C;
inline constexpr std::uint32_t muted = 0x6E6154;
inline constexpr std::uint32_t border = 0xE8DFD2;

// Familias de color por funcion (fondo de tile + tinta AA sobre ese fondo).
inline constexpr std::uint32_t coral = 0xC2502F;      // marca / CTA (relleno, texto blanco)
inline constexpr std::uint32_t coral_bg = 0xF5D8CC;
inline constexpr std::uint32_t coral_ink = 0xA33F22;
inline constexpr std::uint32_t ambar_bg = 0xFFE9C4;   // luces / recordatorios
inline constexpr std::uint32_t ambar_ink = 0x8A5509;
inline constexpr std::uint32_t cielo_bg = 0xD8ECF6;   // clima
inline constexpr std::uint32_t cielo_ink = 0x1F6E93;
inline constexpr std::uint32_t selva_bg = 0xD9F1DE;   // media
inline constexpr std::uint32_t selva_ink = 0x196B3D;
inline constexpr std::uint32_t lila_bg = 0xE9E2F7;    // agenda
inline constexpr std::uint32_t lila_ink = 0x6248AC;

// Semanticos de estado.
inline constexpr std::uint32_t green = 0x3E9B6C;
inline constexpr std::uint32_t amber = 0xC98A2B;
inline constexpr std::uint32_t red = 0xB84034;

// Modo durmiendo: reloj de mesa de luz (fondo carbon calido).
inline constexpr std::uint32_t night = 0x221C18;
inline constexpr std::uint32_t night_ink = 0xEAE2D6;
inline constexpr std::uint32_t night_muted = 0x9A8E82;
inline constexpr std::uint32_t night_chip = 0x2E2620;

// Alias de compatibilidad con el shell previo.
inline constexpr std::uint32_t cyan = coral;
inline constexpr std::uint32_t blue = coral_ink;
inline constexpr std::uint32_t soft = coral_bg;

// Rail: 5 botones de icono de 48 px dentro de los 64 px del rail.
inline constexpr std::array<Rect, 5> navigation = {
    Rect{8, 64, 48, 48},  Rect{8, 120, 48, 48}, Rect{8, 176, 48, 48},
    Rect{8, 232, 48, 48}, Rect{8, 288, 48, 48},
};
// Reposo: despertar tocando el chip inferior.
inline constexpr Rect manual_button{300, 410, 200, 52};
// Hogar (coordenadas relativas a la pagina de 736 px).
inline constexpr Rect power_button{258, 118, 72, 72};
inline constexpr Rect brightness_slider{346, 132, 358, 44};
inline constexpr std::array<Rect, 3> light_selectors = {
    Rect{16, 12, 210, 118}, Rect{16, 142, 210, 118}, Rect{16, 272, 210, 118},
};
// Color: paleta centrada en la tarjeta (242..720, centro 481) y presets debajo.
inline constexpr Rect hue_slider{289, 224, 384, 44};
inline constexpr std::array<Rect, 2> color_presets = {
    Rect{349, 290, 124, 44}, Rect{489, 290, 124, 44},
};
inline constexpr std::array<Rect, 3> scene_buttons = {
    Rect{16, 402, 226, 56}, Rect{254, 402, 226, 56}, Rect{492, 402, 228, 56},
};
// Inicio: pildoras de accion rapida.
inline constexpr std::array<Rect, 3> quick_actions = {
    Rect{16, 420, 226, 48}, Rect{254, 420, 226, 48}, Rect{492, 420, 228, 48},
};
}  // namespace tokens

enum class ShellMode : std::uint8_t { Sleeping, Manual, Conversation };
enum class ManualPage : std::uint8_t { Inicio, Hogar, Media, Agenda, Sistema };

}  // namespace wyss::ui
