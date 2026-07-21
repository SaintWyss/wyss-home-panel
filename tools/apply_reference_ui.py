from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "firmware/include/wyss/ui/design_tokens.hpp"
VIEW = ROOT / "firmware/src/adapters/lvgl_panel_view.cpp"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: se esperaba 1 coincidencia y hubo {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise RuntimeError(f"{label}: no se encontró el inicio")
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise RuntimeError(f"{label}: no se encontró el final")
    return text[:start_at] + replacement.rstrip() + "\n\n" + text[end_at:]


def update_tokens() -> None:
    text = TOKENS.read_text(encoding="utf-8")
    replacements = {
        "inline constexpr std::uint32_t canvas = 0xF4EFE6;":
            "inline constexpr std::uint32_t canvas = 0xF3F5F8;",
        "inline constexpr std::uint32_t text = 0x2A211C;":
            "inline constexpr std::uint32_t text = 0x10213B;",
        "inline constexpr std::uint32_t muted = 0x6E6154;":
            "inline constexpr std::uint32_t muted = 0x667085;",
        "inline constexpr std::uint32_t border = 0xE8DFD2;":
            "inline constexpr std::uint32_t border = 0xE3E7ED;",
        "inline constexpr std::uint32_t coral = 0xC2502F;":
            "inline constexpr std::uint32_t coral = 0xC94F32;",
        "inline constexpr std::uint32_t coral_bg = 0xF5D8CC;":
            "inline constexpr std::uint32_t coral_bg = 0xFFF3EA;",
        "inline constexpr std::uint32_t coral_ink = 0xA33F22;":
            "inline constexpr std::uint32_t coral_ink = 0x9D3D25;",
        "inline constexpr std::uint32_t ambar_bg = 0xFFE9C4;":
            "inline constexpr std::uint32_t ambar_bg = 0xFFF4CF;",
        "inline constexpr std::uint32_t ambar_ink = 0x8A5509;":
            "inline constexpr std::uint32_t ambar_ink = 0x875500;",
        "inline constexpr std::uint32_t cielo_bg = 0xD8ECF6;":
            "inline constexpr std::uint32_t cielo_bg = 0xE2EEFF;",
        "inline constexpr std::uint32_t cielo_ink = 0x1F6E93;":
            "inline constexpr std::uint32_t cielo_ink = 0x2457A7;",
        "inline constexpr std::uint32_t selva_bg = 0xD9F1DE;":
            "inline constexpr std::uint32_t selva_bg = 0xDDF3E5;",
        "inline constexpr std::uint32_t selva_ink = 0x196B3D;":
            "inline constexpr std::uint32_t selva_ink = 0x176A3B;",
        "inline constexpr std::uint32_t lila_bg = 0xE9E2F7;":
            "inline constexpr std::uint32_t lila_bg = 0xEEE7FF;",
        "inline constexpr std::uint32_t lila_ink = 0x6248AC;":
            "inline constexpr std::uint32_t lila_ink = 0x5C3BB2;",
        "inline constexpr std::uint32_t green = 0x3E9B6C;":
            "inline constexpr std::uint32_t green = 0x12A95B;",
        "inline constexpr std::uint32_t red = 0xB84034;":
            "inline constexpr std::uint32_t red = 0xB42332;",
        "inline constexpr std::uint32_t night = 0x221C18;":
            "inline constexpr std::uint32_t night = 0x151922;",
        "inline constexpr std::uint32_t night_ink = 0xEAE2D6;":
            "inline constexpr std::uint32_t night_ink = 0xF6F7F9;",
        "inline constexpr std::uint32_t night_muted = 0x9A8E82;":
            "inline constexpr std::uint32_t night_muted = 0xA6ADBA;",
        "inline constexpr std::uint32_t night_chip = 0x2E2620;":
            "inline constexpr std::uint32_t night_chip = 0x222938;",
    }
    for old, new in replacements.items():
        text = replace_once(text, old, new, old)
    TOKENS.write_text(text, encoding="utf-8")


MEDIA_BLOCK = r'''
    // ===== MEDIA: composición clara y suave del mockup del owner =====
    constexpr std::uint32_t kMediaAccent = 0x18B957;
    constexpr std::uint32_t kMediaTrack = 0xA7DFBC;
    constexpr std::uint32_t kMediaDeviceInk = 0x176A3B;
    lv_obj_t* media = tile(pages_[2], 16, 26, 452, 418, kSelvaBg);
    lv_obj_set_style_radius(media, 24, 0);

    lv_obj_t* spotify_logo = lv_img_create(media);
    lv_img_set_src(spotify_logo, &wyss_spotify_logo);
    lv_obj_set_pos(spotify_logo, 0, 0);
    lv_obj_set_style_img_recolor(spotify_logo, color(kMediaAccent), 0);
    lv_obj_set_style_img_recolor_opa(spotify_logo, LV_OPA_COVER, 0);
    lv_obj_t* media_eyebrow = label(media, "SPOTIFY", &lv_font_montserrat_14, kText);
    lv_obj_set_pos(media_eyebrow, 40, 2);

    media_device_ = label(media, "-", &lv_font_montserrat_12, kText);
    lv_obj_set_style_bg_color(media_device_, color(kSurface), 0);
    lv_obj_set_style_bg_opa(media_device_, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_hor(media_device_, 12, 0);
    lv_obj_set_style_pad_ver(media_device_, 7, 0);
    lv_obj_set_style_radius(media_device_, 16, 0);
    lv_obj_set_style_border_width(media_device_, 1, 0);
    lv_obj_set_style_border_color(media_device_, color(0xFFFFFF), 0);
    lv_obj_align(media_device_, LV_ALIGN_TOP_RIGHT, 0, -3);

    media_title_ = label(media, "Spotify no vinculado", &lv_font_montserrat_30, kText);
    lv_obj_set_pos(media_title_, 0, 82);
    lv_obj_set_width(media_title_, 420);
    lv_obj_set_style_text_align(media_title_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(media_title_, LV_LABEL_LONG_DOT);
    media_artist_ = label(media, "Vinculalo desde Wyss", &lv_font_montserrat_16, kMediaDeviceInk);
    lv_obj_set_pos(media_artist_, 0, 126);
    lv_obj_set_width(media_artist_, 420);
    lv_obj_set_style_text_align(media_artist_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(media_artist_, LV_LABEL_LONG_DOT);

    constexpr const char* media_symbols[] = {LV_SYMBOL_PREV, LV_SYMBOL_PLAY, LV_SYMBOL_NEXT};
    constexpr int media_sizes[] = {58, 84, 58};
    constexpr int media_xs[] = {76, 168, 286};
    constexpr int media_ys[] = {176, 162, 176};
    for (unsigned index = 0; index < 3; ++index) {
        media_buttons_[index] = lv_btn_create(media);
        lv_obj_set_size(media_buttons_[index], media_sizes[index], media_sizes[index]);
        lv_obj_set_pos(media_buttons_[index], media_xs[index], media_ys[index]);
        style_button(media_buttons_[index], index == 1 ? kMediaAccent : kSurface);
        lv_obj_set_style_bg_color(media_buttons_[index],
                                  color(index == 1 ? 0x109947 : 0xF4F7F5),
                                  LV_STATE_PRESSED);
        lv_obj_set_style_radius(media_buttons_[index], LV_RADIUS_CIRCLE, 0);
        if (index != 1) {
            lv_obj_set_style_shadow_width(media_buttons_[index], 8, 0);
            lv_obj_set_style_shadow_opa(media_buttons_[index], LV_OPA_10, 0);
            lv_obj_set_style_shadow_ofs_y(media_buttons_[index], 3, 0);
        }
        lv_obj_t* button_label = label(
            media_buttons_[index], media_symbols[index],
            index == 1 ? &lv_font_montserrat_30 : &lv_font_montserrat_20,
            index == 1 ? kSurface : kText);
        lv_obj_center(button_label);
        lv_obj_add_state(media_buttons_[index], LV_STATE_DISABLED);
    }
    media_play_label_ = lv_obj_get_child(media_buttons_[1], 0);

    media_buttons_[3] = lv_btn_create(media);
    lv_obj_set_size(media_buttons_[3], 128, 44);
    lv_obj_set_pos(media_buttons_[3], 146, 270);
    style_button(media_buttons_[3], 0xF2F7F4);
    lv_obj_set_style_bg_color(media_buttons_[3], color(0xE5F3EA), LV_STATE_PRESSED);
    lv_obj_set_style_radius(media_buttons_[3], 22, 0);
    media_favorite_label_ = label(media_buttons_[3], "Favorito", &lv_font_montserrat_14, kText);
    lv_obj_center(media_favorite_label_);
    lv_obj_add_state(media_buttons_[3], LV_STATE_DISABLED);

    // Volumen permanece funcional, pero ocupa una fila compacta que desaparece cuando no aplica.
    media_volume_row_ = lv_obj_create(media);
    lv_obj_set_size(media_volume_row_, 420, 42);
    lv_obj_set_pos(media_volume_row_, 0, 314);
    lv_obj_set_style_bg_opa(media_volume_row_, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(media_volume_row_, 0, 0);
    lv_obj_set_style_pad_all(media_volume_row_, 0, 0);
    lv_obj_clear_flag(media_volume_row_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* volume_title =
        label(media_volume_row_, LV_SYMBOL_VOLUME_MAX, &lv_font_montserrat_16, kMediaDeviceInk);
    lv_obj_set_pos(volume_title, 8, 10);
    media_volume_ = lv_slider_create(media_volume_row_);
    lv_obj_set_size(media_volume_, 280, 36);
    lv_obj_set_pos(media_volume_, 42, 3);
    lv_slider_set_range(media_volume_, 0, 100);
    lv_obj_set_style_radius(media_volume_, 18, LV_PART_MAIN);
    lv_obj_set_style_radius(media_volume_, 18, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(media_volume_, color(kMediaTrack), LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_volume_, color(kMediaAccent), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(media_volume_, color(kSurface), LV_PART_KNOB);
    lv_obj_set_style_border_width(media_volume_, 1, LV_PART_KNOB);
    lv_obj_set_style_border_color(media_volume_, color(kBorder), LV_PART_KNOB);
    lv_obj_set_style_pad_all(media_volume_, 5, LV_PART_KNOB);
    lv_obj_add_event_cb(media_volume_, on_media_volume, LV_EVENT_VALUE_CHANGED, this);
    lv_obj_add_event_cb(media_volume_, on_media_volume_release, LV_EVENT_RELEASED, this);
    lv_obj_add_event_cb(media_volume_, on_media_volume_release, LV_EVENT_PRESS_LOST, this);
    media_volume_label_ = label(media_volume_row_, "-- %", &lv_font_montserrat_14, kText);
    lv_obj_set_width(media_volume_label_, 84);
    lv_obj_set_pos(media_volume_label_, 330, 10);
    lv_obj_set_style_text_align(media_volume_label_, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_add_flag(media_volume_row_, LV_OBJ_FLAG_HIDDEN);

    media_time_now_ = label(media, "0:00", &lv_font_montserrat_12, kText);
    lv_obj_set_pos(media_time_now_, 0, 372);
    media_progress_ = lv_bar_create(media);
    lv_obj_set_size(media_progress_, 300, 8);
    lv_obj_set_pos(media_progress_, 52, 376);
    lv_bar_set_range(media_progress_, 0, 1000);
    lv_obj_set_style_radius(media_progress_, 4, LV_PART_MAIN);
    lv_obj_set_style_radius(media_progress_, 4, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(media_progress_, color(kMediaTrack), LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_progress_, color(kMediaAccent), LV_PART_INDICATOR);
    media_progress_label_ = label(media, "0:00", &lv_font_montserrat_12, kText);
    lv_obj_set_width(media_progress_label_, 60);
    lv_obj_set_pos(media_progress_label_, 360, 372);
    lv_obj_set_style_text_align(media_progress_label_, LV_TEXT_ALIGN_RIGHT, 0);

    lv_obj_t* queue_card = tile(pages_[2], 484, 26, 236, 418, kSurface);
    lv_obj_set_style_radius(queue_card, 24, 0);
    lv_obj_set_style_border_width(queue_card, 1, 0);
    lv_obj_set_style_border_color(queue_card, color(kBorder), 0);
    label(queue_card, "A CONTINUACION", &lv_font_montserrat_12, kMuted);
    media_queue_empty_ = label(queue_card, "Sin cola", &lv_font_montserrat_14, kMuted);
    lv_obj_set_pos(media_queue_empty_, 0, 42);
    for (unsigned index = 0; index < media_queue_titles_.size(); ++index) {
        const int row = 44 + static_cast<int>(index) * 68;
        media_queue_titles_[index] = label(queue_card, "", &lv_font_montserrat_14, kText);
        lv_obj_set_pos(media_queue_titles_[index], 0, row);
        lv_obj_set_width(media_queue_titles_[index], 166);
        lv_label_set_long_mode(media_queue_titles_[index], LV_LABEL_LONG_DOT);
        media_queue_artists_[index] = label(queue_card, "", &lv_font_montserrat_12, kMuted);
        lv_obj_set_pos(media_queue_artists_[index], 0, row + 24);
        lv_obj_set_width(media_queue_artists_[index], 166);
        lv_label_set_long_mode(media_queue_artists_[index], LV_LABEL_LONG_DOT);
        lv_obj_t* handle = label(queue_card, LV_SYMBOL_LIST, &lv_font_montserrat_12, kBorder);
        lv_obj_set_pos(handle, 184, row + 8);
    }

    lv_obj_add_event_cb(media_buttons_[0], on_media_previous, LV_EVENT_CLICKED, this);
    lv_obj_add_event_cb(media_buttons_[1], on_media_play, LV_EVENT_CLICKED, this);
    lv_obj_add_event_cb(media_buttons_[2], on_media_next, LV_EVENT_CLICKED, this);
    lv_obj_add_event_cb(media_buttons_[3], on_media_favorite, LV_EVENT_CLICKED, this);
'''

AGENDA_BLOCK = r'''
    // ===== AGENDA: timeline azul + recordatorios amarillos + timer coral =====
    lv_obj_t* agenda = tile(pages_[3], 16, 26, 452, 418, kCieloBg);
    lv_obj_set_style_radius(agenda, 24, 0);
    label(agenda, "AGENDA", &lv_font_montserrat_12, kCieloInk);
    agenda_state_ = label(agenda, "Sin eventos proyectados", &lv_font_montserrat_26, kText);
    lv_obj_set_pos(agenda_state_, 0, 30);
    lv_obj_set_width(agenda_state_, 420);
    lv_label_set_long_mode(agenda_state_, LV_LABEL_LONG_DOT);
    agenda_meta_ = label(agenda, "Esperando Calendar", &lv_font_montserrat_12, kCieloInk);
    lv_obj_set_pos(agenda_meta_, 0, 72);
    lv_obj_set_width(agenda_meta_, 420);
    lv_label_set_long_mode(agenda_meta_, LV_LABEL_LONG_DOT);

    lv_obj_t* timeline = lv_obj_create(agenda);
    lv_obj_set_size(timeline, 2, 210);
    lv_obj_set_pos(timeline, 86, 118);
    flat(timeline);
    lv_obj_set_style_radius(timeline, 1, 0);
    lv_obj_set_style_bg_color(timeline, color(0xB7D2FA), 0);
    lv_obj_clear_flag(timeline, LV_OBJ_FLAG_SCROLLABLE);
    for (unsigned index = 0; index < agenda_events_.size(); ++index) {
        const int row = 108 + static_cast<int>(index) * 64;
        lv_obj_t* dot = lv_obj_create(agenda);
        lv_obj_set_size(dot, index == 0 ? 14 : 12, index == 0 ? 14 : 12);
        lv_obj_set_pos(dot, index == 0 ? 80 : 81, row + 8);
        flat(dot);
        lv_obj_set_style_radius(dot, LV_RADIUS_CIRCLE, 0);
        lv_obj_set_style_bg_color(dot, color(index == 0 ? 0x1769E8 : 0x7DB1F5), 0);
        lv_obj_clear_flag(dot, LV_OBJ_FLAG_SCROLLABLE);
        agenda_events_[index] = label(agenda, "--", &lv_font_montserrat_14, kText);
        lv_obj_set_pos(agenda_events_[index], 104, row);
        lv_obj_set_width(agenda_events_[index], 300);
        lv_label_set_long_mode(agenda_events_[index], LV_LABEL_LONG_DOT);
    }
    lv_obj_t* agenda_divider = lv_obj_create(agenda);
    lv_obj_set_size(agenda_divider, 390, 1);
    lv_obj_set_pos(agenda_divider, 0, 344);
    flat(agenda_divider);
    lv_obj_set_style_bg_color(agenda_divider, color(0xBCD3F2), 0);
    lv_obj_clear_flag(agenda_divider, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* tomorrow = label(agenda, "MANANA   Sin eventos programados",
                               &lv_font_montserrat_12, kCieloInk);
    lv_obj_set_pos(tomorrow, 0, 362);

    lv_obj_t* reminder_card = tile(pages_[3], 484, 26, 236, 196, kAmbarBg);
    lv_obj_set_style_radius(reminder_card, 24, 0);
    label(reminder_card, "RECORDATORIOS", &lv_font_montserrat_12, kAmbarInk);
    reminder_state_ = label(reminder_card, "Sin sincronizar", &lv_font_montserrat_18, kText);
    lv_obj_set_pos(reminder_state_, 0, 42);
    lv_obj_set_width(reminder_state_, 204);
    lv_label_set_long_mode(reminder_state_, LV_LABEL_LONG_WRAP);
    lv_obj_set_style_text_line_space(reminder_state_, 8, 0);

    lv_obj_t* timer_card = tile(pages_[3], 484, 236, 236, 208, kCoralBg);
    lv_obj_set_style_radius(timer_card, 24, 0);
    label(timer_card, "TIMERS", &lv_font_montserrat_12, kCoralInk);
    lv_obj_t* timer_dot = lv_obj_create(timer_card);
    lv_obj_set_size(timer_dot, 7, 7);
    lv_obj_align(timer_dot, LV_ALIGN_TOP_RIGHT, 0, 0);
    flat(timer_dot);
    lv_obj_set_style_radius(timer_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(timer_dot, color(0xEF6670), 0);
    lv_obj_clear_flag(timer_dot, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* timer_ring = lv_obj_create(timer_card);
    lv_obj_set_size(timer_ring, 96, 96);
    lv_obj_set_pos(timer_ring, 54, 38);
    flat(timer_ring);
    lv_obj_set_style_radius(timer_ring, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(timer_ring, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(timer_ring, 8, 0);
    lv_obj_set_style_border_color(timer_ring, color(0xEF3D49), 0);
    lv_obj_clear_flag(timer_ring, LV_OBJ_FLAG_SCROLLABLE);
    timer_state_ = label(timer_card, "--:--\nSin timers activos", &lv_font_montserrat_18, kCoralInk);
    lv_obj_set_pos(timer_state_, 12, 70);
    lv_obj_set_width(timer_state_, 180);
    lv_obj_set_style_text_align(timer_state_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(timer_state_, LV_LABEL_LONG_WRAP);
    lv_obj_set_style_text_line_space(timer_state_, 44, 0);
'''


def update_view() -> None:
    text = VIEW.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "    lv_obj_set_style_bg_color(object, color(kSurface), 0);\n"
        "    lv_obj_set_style_pad_all(object, 16, 0);",
        "    lv_obj_set_style_bg_color(object, color(kSurface), 0);\n"
        "    lv_obj_set_style_shadow_width(object, 10, 0);\n"
        "    lv_obj_set_style_shadow_opa(object, LV_OPA_10, 0);\n"
        "    lv_obj_set_style_shadow_color(object, color(0x132238), 0);\n"
        "    lv_obj_set_style_shadow_ofs_y(object, 3, 0);\n"
        "    lv_obj_set_style_pad_all(object, 16, 0);",
        "sombras de tarjetas",
    )

    text = replace_between(
        text,
        "    constexpr std::uint32_t kMediaTop =",
        "    lv_obj_t* agenda = tile(pages_[3]",
        MEDIA_BLOCK,
        "bloque Media",
    )
    text = replace_between(
        text,
        "    lv_obj_t* agenda = tile(pages_[3]",
        "    lv_obj_t* system_status = panel(pages_[4]",
        AGENDA_BLOCK,
        "bloque Agenda",
    )

    text = replace_once(
        text,
        "    lv_obj_set_style_img_recolor(media_favorite_label_,\n"
        "                                 color(state.favorite ? kGreen : 0x8FD6AD), 0);",
        "    lv_obj_set_style_text_color(media_favorite_label_,\n"
        "                                color(state.favorite ? kGreen : kText), 0);",
        "estado de favorito",
    )

    old_agenda_meta = (
        '        std::snprintf(agenda_meta_text_, sizeof(agenda_meta_text_), "%s hace %s - %s",\n'
        '                      state.stale ? "CACHE" : "Actualizado", age,\n'
        '                      state.write_enabled ? "edicion via Wyss" : "solo lectura");'
    )
    new_agenda_meta = (
        '        std::snprintf(agenda_meta_text_, sizeof(agenda_meta_text_),\n'
        '                      "GOOGLE CALENDAR - %s HACE %s - %s",\n'
        '                      state.stale ? "CACHE" : "ACTUALIZADO", age,\n'
        '                      state.write_enabled ? "EDICION VIA WYSS" : "SOLO LECTURA");'
    )
    if text.count(old_agenda_meta) != 2:
        raise RuntimeError("metadatos de agenda: se esperaban 2 coincidencias")
    text = text.replace(old_agenda_meta, new_agenda_meta)

    old_event_block = r'''            if (event.all_day) {
                std::snprintf(agenda_event_text_[index], sizeof(agenda_event_text_[index]),
                              "%.*s/%.*s  TODO EL DIA  %s%s",
                              static_cast<int>(day.size()), day.data(),
                              static_cast<int>(month.size()), month.data(), title.c_str(),
                              event.tentative ? "  [TENTATIVO]" : "");
            } else {
                const std::string_view time =
                    start.size() >= 16U ? start.substr(11U, 5U) : std::string_view{"--:--"};
                std::snprintf(agenda_event_text_[index], sizeof(agenda_event_text_[index]),
                              "%.*s/%.*s  %.*s  %s%s", static_cast<int>(day.size()),
                              day.data(), static_cast<int>(month.size()), month.data(),
                              static_cast<int>(time.size()), time.data(), title.c_str(),
                              event.tentative ? "  [TENTATIVO]" : "");
            }'''
    new_event_block = r'''            if (event.all_day) {
                std::snprintf(agenda_event_text_[index], sizeof(agenda_event_text_[index]),
                              "TODO EL DIA   %s%s", title.c_str(),
                              event.tentative ? "  [TENTATIVO]" : "");
            } else {
                const std::string_view time =
                    start.size() >= 16U ? start.substr(11U, 5U) : std::string_view{"--:--"};
                std::snprintf(agenda_event_text_[index], sizeof(agenda_event_text_[index]),
                              "%.*s   %s%s", static_cast<int>(time.size()), time.data(),
                              title.c_str(), event.tentative ? "  [TENTATIVO]" : "");
            }'''
    text = replace_once(text, old_event_block, new_event_block, "filas de agenda")
    text = replace_once(
        text,
        "        lv_obj_set_style_text_color(agenda_events_[index],\n"
        "                                    color(state.stale ? kAmber : kMuted), 0);",
        "        lv_obj_set_style_text_color(agenda_events_[index],\n"
        "                                    color(state.stale ? kAmber : kText), 0);",
        "color de agenda",
    )

    text = replace_once(
        text,
        '        std::snprintf(reminder_state_text_, sizeof(reminder_state_text_),\n'
        '                      "%u pendientes\\n\\nProximo:\\n%s",\n'
        '                      static_cast<unsigned>(state.items.size()), text.c_str());',
        '        const auto count = static_cast<unsigned>(state.items.size());\n'
        '        std::snprintf(reminder_state_text_, sizeof(reminder_state_text_),\n'
        '                      "%u pendiente%s\\n\\nPROXIMO\\n%s", count,\n'
        '                      count == 1U ? "" : "s", text.c_str());',
        "resumen de recordatorios",
    )

    text = replace_once(
        text,
        '        std::snprintf(timer_state_text_, sizeof(timer_state_text_),\n'
        '                      "%u activos\\n\\n%s\\n%02u:%02u",\n'
        '                      static_cast<unsigned>(state.items.size()), label.c_str(),\n'
        '                      static_cast<unsigned>(remaining / 60U),\n'
        '                      static_cast<unsigned>(remaining % 60U));',
        '        std::snprintf(timer_state_text_, sizeof(timer_state_text_),\n'
        '                      "%02u:%02u\\n%s", static_cast<unsigned>(remaining / 60U),\n'
        '                      static_cast<unsigned>(remaining % 60U), label.c_str());',
        "resumen de timers",
    )
    text = replace_once(
        text,
        '        std::snprintf(timer_state_text_, sizeof(timer_state_text_), "Sin timers activos");',
        '        std::snprintf(timer_state_text_, sizeof(timer_state_text_), "--:--\\nSin timers activos");',
        "timer vacío",
    )
    text = replace_once(
        text,
        '        std::snprintf(timer_state_text_, sizeof(timer_state_text_), "No disponibles");',
        '        std::snprintf(timer_state_text_, sizeof(timer_state_text_), "--:--\\nNo disponibles");',
        "timer no disponible",
    )

    text = replace_once(
        text,
        "        lv_obj_set_style_bg_color(device_buttons_[index], color(kSurface), 0);\n"
        "        lv_obj_set_style_text_color(device_labels_[index], color(kMuted), 0);",
        "        lv_obj_set_style_bg_color(device_buttons_[index], color(kSurface), 0);\n"
        "        lv_obj_set_style_border_width(device_buttons_[index], 1, 0);\n"
        "        lv_obj_set_style_border_color(device_buttons_[index], color(kBorder), 0);\n"
        "        lv_obj_set_style_text_color(device_labels_[index], color(kMuted), 0);",
        "reset de tarjetas de luz",
    )
    text = replace_once(
        text,
        "            lv_obj_set_style_bg_color(device_buttons_[index], color(kAmbarBg), 0);\n"
        "            lv_obj_set_style_text_color(device_labels_[index], color(kText), 0);",
        "            lv_obj_set_style_bg_color(device_buttons_[index], color(kCoralBg), 0);\n"
        "            lv_obj_set_style_border_width(device_buttons_[index], 2, 0);\n"
        "            lv_obj_set_style_border_color(device_buttons_[index], color(kCoral), 0);\n"
        "            lv_obj_set_style_text_color(device_labels_[index], color(kText), 0);",
        "tarjeta de luz seleccionada",
    )
    text = replace_once(
        text,
        "    lv_obj_set_style_bg_color(power_, color(current_.on ? kCoral : kSurface), 0);",
        "    lv_obj_set_style_bg_color(power_, color(current_.on ? 0xC98A57 : kSurface), 0);",
        "botón de encendido",
    )

    VIEW.write_text(text, encoding="utf-8")


def main() -> None:
    update_tokens()
    update_view()


if __name__ == "__main__":
    main()
