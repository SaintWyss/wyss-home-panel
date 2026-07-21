#include "wyss/adapters/lvgl_panel_view.hpp"

#include "wyss/ui/spotify_logo.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <iterator>

namespace wyss::adapters {
namespace {
constexpr auto kCanvas = ui::tokens::canvas;
constexpr auto kSurface = ui::tokens::surface;
constexpr auto kSurfaceRaised = ui::tokens::surface_raised;
constexpr auto kText = ui::tokens::text;
constexpr auto kMuted = ui::tokens::muted;
constexpr auto kCyan = ui::tokens::cyan;
constexpr auto kBlue = ui::tokens::blue;
constexpr auto kGreen = ui::tokens::green;
constexpr auto kAmber = ui::tokens::amber;
constexpr auto kRed = ui::tokens::red;
constexpr auto kBorder = ui::tokens::border;
constexpr auto kSoft = ui::tokens::soft;
constexpr auto kCoral = ui::tokens::coral;
constexpr auto kCoralBg = ui::tokens::coral_bg;
constexpr auto kCoralInk = ui::tokens::coral_ink;
constexpr auto kAmbarBg = ui::tokens::ambar_bg;
constexpr auto kAmbarInk = ui::tokens::ambar_ink;
constexpr auto kCieloBg = ui::tokens::cielo_bg;
constexpr auto kCieloInk = ui::tokens::cielo_ink;
constexpr auto kSelvaBg = ui::tokens::selva_bg;
constexpr auto kSelvaInk = ui::tokens::selva_ink;
constexpr auto kLilaBg = ui::tokens::lila_bg;
constexpr auto kLilaInk = ui::tokens::lila_ink;
constexpr auto kNight = ui::tokens::night;
constexpr auto kNightInk = ui::tokens::night_ink;
constexpr auto kNightMuted = ui::tokens::night_muted;
constexpr auto kNightChip = ui::tokens::night_chip;

// Geometria del tile de clima (contenido util de 220x320 dentro del tile cielo).
constexpr int kWeatherContentWidth = 220;
constexpr int kWeatherColumnPitch = 31;
constexpr int kWeatherBarWidth = 14;
constexpr int kWeatherBarInset = (kWeatherColumnPitch - kWeatherBarWidth) / 2;
constexpr int kWeatherChartTop = 152;
constexpr int kWeatherChartHeight = 116;
constexpr int kWeatherMaxRow = kWeatherChartTop - 26;
constexpr int kWeatherDayRow = kWeatherChartTop + kWeatherChartHeight + 8;

LvglPanelView* g_view = nullptr;

lv_color_t color(std::uint32_t value) { return lv_color_hex(value); }

void flat(lv_obj_t* object) {
    lv_obj_set_style_shadow_width(object, 0, 0);
    lv_obj_set_style_border_width(object, 0, 0);
    lv_obj_set_style_radius(object, ui::tokens::radius, 0);
}

void prepare_layer(lv_obj_t* object) {
    lv_obj_set_size(object, ui::tokens::screen_width, ui::tokens::screen_height);
    lv_obj_set_pos(object, 0, 0);
    lv_obj_set_style_bg_opa(object, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(object, 0, 0);
    lv_obj_set_style_pad_all(object, 0, 0);
    lv_obj_clear_flag(object, LV_OBJ_FLAG_SCROLLABLE);
}

void disable_touch_scroll(lv_obj_t* object) {
    constexpr auto gesture_flags = static_cast<lv_obj_flag_t>(
        LV_OBJ_FLAG_SCROLL_ELASTIC | LV_OBJ_FLAG_SCROLL_MOMENTUM | LV_OBJ_FLAG_SCROLL_CHAIN |
        LV_OBJ_FLAG_SCROLL_ON_FOCUS | LV_OBJ_FLAG_SCROLL_WITH_ARROW);
    lv_obj_set_scroll_dir(object, LV_DIR_NONE);
    lv_obj_clear_flag(object, gesture_flags);
    lv_obj_scroll_to(object, 0, 0, LV_ANIM_OFF);
    const auto child_count = lv_obj_get_child_cnt(object);
    for (std::uint32_t index = 0; index < child_count; ++index) {
        disable_touch_scroll(lv_obj_get_child(object, static_cast<std::int32_t>(index)));
    }
}

lv_obj_t* panel(lv_obj_t* parent, int x, int y, int width, int height) {
    lv_obj_t* object = lv_obj_create(parent);
    lv_obj_set_size(object, width, height);
    lv_obj_set_pos(object, x, y);
    flat(object);
    lv_obj_set_style_bg_color(object, color(kSurface), 0);
    lv_obj_set_style_pad_all(object, 16, 0);
    lv_obj_clear_flag(object, LV_OBJ_FLAG_SCROLLABLE);
    return object;
}

// Tile de widget con familia de color propia.
lv_obj_t* tile(lv_obj_t* parent, int x, int y, int width, int height, std::uint32_t background) {
    lv_obj_t* object = panel(parent, x, y, width, height);
    lv_obj_set_style_bg_color(object, color(background), 0);
    return object;
}

// Pildora redondeada (accion rapida, escena, chip de preset).
lv_obj_t* pill(lv_obj_t* parent, const ui::Rect& bounds, std::uint32_t background) {
    lv_obj_t* object = lv_btn_create(parent);
    lv_obj_set_size(object, bounds.width, bounds.height);
    lv_obj_set_pos(object, bounds.x, bounds.y);
    lv_obj_set_style_shadow_width(object, 0, 0);
    lv_obj_set_style_border_width(object, 0, 0);
    lv_obj_set_style_bg_color(object, color(background), 0);
    lv_obj_set_style_radius(object, bounds.height / 2, 0);
    return object;
}

std::string ascii_safe(std::string_view text) {
    std::string output;
    output.reserve(text.size());
    for (std::size_t index = 0; index < text.size();) {
        const auto byte = static_cast<unsigned char>(text[index]);
        if (byte < 0x80U) {
            output.push_back(static_cast<char>(byte));
            ++index;
            continue;
        }
        if (byte == 0xC3U && index + 1 < text.size()) {
            const auto next = static_cast<unsigned char>(text[index + 1]);
            char replacement = '?';
            if (next == 0x81U || next == 0x89U || next == 0x8DU || next == 0x93U || next == 0x9AU ||
                next == 0x91U || next == 0x9CU) {
                constexpr char uppercase[] = {'A', 'E', 'I', 'O', 'U', 'N', 'U'};
                constexpr unsigned char codes[] = {0x81U, 0x89U, 0x8DU, 0x93U, 0x9AU, 0x91U, 0x9CU};
                for (std::size_t code = 0; code < std::size(codes); ++code) {
                    if (next == codes[code]) replacement = uppercase[code];
                }
            } else if (next == 0xA1U || next == 0xA9U || next == 0xADU || next == 0xB3U ||
                       next == 0xBAU || next == 0xB1U || next == 0xBCU) {
                constexpr char lowercase[] = {'a', 'e', 'i', 'o', 'u', 'n', 'u'};
                constexpr unsigned char codes[] = {0xA1U, 0xA9U, 0xADU, 0xB3U, 0xBAU, 0xB1U, 0xBCU};
                for (std::size_t code = 0; code < std::size(codes); ++code) {
                    if (next == codes[code]) replacement = lowercase[code];
                }
            }
            output.push_back(replacement);
            index += 2;
            continue;
        }
        if (byte == 0xC2U && index + 1 < text.size()) {
            const auto next = static_cast<unsigned char>(text[index + 1]);
            output.push_back(next == 0xBFU ? '?' : '-');
            index += 2;
            continue;
        }
        if (byte == 0xE2U && index + 2 < text.size()) {
            const auto second = static_cast<unsigned char>(text[index + 1]);
            const auto third = static_cast<unsigned char>(text[index + 2]);
            if (second == 0x80U && third == 0xA6U) {
                output.append("...");
            } else {
                output.push_back('-');
            }
            index += 3;
            continue;
        }
        output.push_back('?');
        ++index;
    }
    return output;
}

const char* weather_condition(std::string_view condition) {
    if (condition == "despejado") return "Despejado";
    if (condition == "parcialmente_nublado") return "Parcialmente nublado";
    if (condition == "nublado") return "Nublado";
    if (condition == "niebla") return "Niebla";
    if (condition == "llovizna") return "Llovizna";
    if (condition == "lluvia") return "Lluvia";
    if (condition == "nieve") return "Nieve";
    if (condition == "tormenta") return "Tormenta";
    return "Condicion desconocida";
}

const char* weather_error(std::string_view error) {
    if (error == "provider_unavailable") return "Proveedor fuera de linea";
    if (error == "cache_expired") return "Ultimo dato vencido";
    if (error == "invalid_forecast") return "Pronostico invalido";
    return "Sin datos validos";
}

const char* calendar_error(std::string_view error) {
    if (error == "reauthorization_required") return "Volve a vincular Calendar desde Wyss";
    if (error == "scope_required") return "Calendar no tiene el permiso requerido";
    if (error == "rate_limited") return "Calendar pidio esperar antes de reintentar";
    if (error == "provider_unavailable") return "Calendar temporalmente fuera de linea";
    if (error == "invalid_response") return "Calendar devolvio datos invalidos";
    return "Sin agenda sincronizada";
}

void format_age(char* output, std::size_t size, std::uint32_t age_seconds) {
    if (age_seconds < 60U) {
        std::snprintf(output, size, "menos de 1 min");
    } else if (age_seconds < 3'600U) {
        std::snprintf(output, size, "%lu min",
                      static_cast<unsigned long>(age_seconds / 60U));
    } else {
        std::snprintf(output, size, "%lu h",
                      static_cast<unsigned long>(age_seconds / 3'600U));
    }
}
}  // namespace

lv_obj_t* LvglPanelView::label(lv_obj_t* parent, const char* text, const lv_font_t* font,
                               std::uint32_t text_color) {
    lv_obj_t* object = lv_label_create(parent);
    lv_label_set_text(object, text);
    lv_obj_set_style_text_font(object, font, 0);
    lv_obj_set_style_text_color(object, color(text_color), 0);
    return object;
}

void LvglPanelView::style_button(lv_obj_t* object, std::uint32_t background) {
    flat(object);
    lv_obj_set_style_bg_color(object, color(background), 0);
    lv_obj_set_style_bg_color(object, color(kCoralInk), LV_STATE_PRESSED);
    lv_obj_set_style_border_width(object, 0, 0);
    lv_obj_set_style_border_width(object, 2, LV_STATE_FOCUSED);
    lv_obj_set_style_border_color(object, color(kCoral), LV_STATE_FOCUSED);
}

void LvglPanelView::begin(application::PanelService& service, std::string primary_entity) {
    service_ = &service;
    primary_entity_ = std::move(primary_entity);
    selected_entity_ = primary_entity_;
    g_view = this;

    lv_obj_t* screen = lv_scr_act();
    lv_obj_clean(screen);
    lv_obj_set_style_bg_color(screen, color(kCanvas), 0);
    lv_obj_set_style_pad_all(screen, 0, 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);

    manual_layer_ = lv_obj_create(screen);
    prepare_layer(manual_layer_);
    // Sidebar izquierda: marca, navegacion vertical y estado de conexion.
    lv_obj_t* sidebar = lv_obj_create(manual_layer_);
    lv_obj_set_size(sidebar, ui::tokens::sidebar_width, ui::tokens::screen_height);
    lv_obj_set_pos(sidebar, 0, 0);
    flat(sidebar);
    lv_obj_set_style_radius(sidebar, 0, 0);
    lv_obj_set_style_bg_color(sidebar, color(kSurface), 0);
    lv_obj_set_style_border_width(sidebar, 1, 0);
    lv_obj_set_style_border_side(sidebar, LV_BORDER_SIDE_RIGHT, 0);
    lv_obj_set_style_border_color(sidebar, color(kBorder), 0);
    lv_obj_clear_flag(sidebar, LV_OBJ_FLAG_SCROLLABLE);
    // Marca: circulo coral con la W.
    lv_obj_t* brand = lv_obj_create(manual_layer_);
    lv_obj_set_size(brand, 38, 38);
    lv_obj_set_pos(brand, 13, 12);
    flat(brand);
    lv_obj_set_style_radius(brand, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(brand, color(kCoral), 0);
    lv_obj_clear_flag(brand, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* brand_label = label(brand, "W", &lv_font_montserrat_16, kSurface);
    lv_obj_center(brand_label);
    // Conexion como punto de estado al pie del rail (el texto completo vive en Sistema).
    connection_ = label(manual_layer_, LV_SYMBOL_WIFI, &lv_font_montserrat_16, kRed);
    lv_obj_set_pos(connection_, 22, 446);

    constexpr const char* tab_names[] = {LV_SYMBOL_HOME, "", LV_SYMBOL_AUDIO,
                                         LV_SYMBOL_LIST, LV_SYMBOL_SETTINGS};
    for (unsigned index = 0; index < 5; ++index) {
        const auto bounds = ui::tokens::navigation[index];
        tabs_[index] = lv_btn_create(manual_layer_);
        lv_obj_set_size(tabs_[index], bounds.width, bounds.height);
        lv_obj_set_pos(tabs_[index], bounds.x, bounds.y);
        style_button(tabs_[index], kSurface);
        lv_obj_set_style_radius(tabs_[index], 16, 0);
        lv_obj_add_event_cb(tabs_[index], on_tab, LV_EVENT_CLICKED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        lv_obj_t* tab_label = label(tabs_[index], tab_names[index], &lv_font_montserrat_20, kMuted);
        lv_obj_center(tab_label);
    }
    // Hogar: Montserrat no tiene bombita, asi que la dibujamos (bulbo + casquillo).
    // El label vacio sigue siendo el hijo 0 para no romper el recoloreo de show_page.
    light_icon_glass_ = lv_obj_create(tabs_[1]);
    lv_obj_set_size(light_icon_glass_, 19, 19);
    lv_obj_align(light_icon_glass_, LV_ALIGN_CENTER, 0, -5);
    flat(light_icon_glass_);
    lv_obj_set_style_radius(light_icon_glass_, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(light_icon_glass_, color(kMuted), 0);
    lv_obj_clear_flag(light_icon_glass_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(light_icon_glass_, LV_OBJ_FLAG_CLICKABLE);
    light_icon_base_ = lv_obj_create(tabs_[1]);
    lv_obj_set_size(light_icon_base_, 9, 7);
    lv_obj_align(light_icon_base_, LV_ALIGN_CENTER, 0, 9);
    flat(light_icon_base_);
    lv_obj_set_style_radius(light_icon_base_, 2, 0);
    lv_obj_set_style_bg_color(light_icon_base_, color(kMuted), 0);
    lv_obj_clear_flag(light_icon_base_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(light_icon_base_, LV_OBJ_FLAG_CLICKABLE);

    // Hablar con Wyss: CTA coral, unica entrada manual a la conversacion.
    lv_obj_t* talk = lv_btn_create(manual_layer_);
    lv_obj_set_size(talk, ui::tokens::conversation_button.width,
                    ui::tokens::conversation_button.height);
    lv_obj_set_pos(talk, ui::tokens::conversation_button.x, ui::tokens::conversation_button.y);
    style_button(talk, kCoral);
    lv_obj_set_style_radius(talk, LV_RADIUS_CIRCLE, 0);
    lv_obj_add_event_cb(talk, on_conversation_open, LV_EVENT_CLICKED, this);
    lv_obj_t* talk_label = label(talk, LV_SYMBOL_EDIT, &lv_font_montserrat_20, kSurface);
    lv_obj_center(talk_label);

    for (auto*& page : pages_) {
        page = lv_obj_create(manual_layer_);
        lv_obj_set_size(page, ui::tokens::screen_width - ui::tokens::sidebar_width,
                        ui::tokens::screen_height);
        lv_obj_set_pos(page, ui::tokens::sidebar_width, 0);
        lv_obj_set_style_bg_opa(page, LV_OPA_TRANSP, 0);
        lv_obj_set_style_border_width(page, 0, 0);
        lv_obj_set_style_pad_all(page, 0, 0);
        lv_obj_clear_flag(page, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_flag(page, LV_OBJ_FLAG_HIDDEN);
    }

    // Tira superior sin tarjeta: el resumen del hogar vive directo sobre el canvas.
    home_summary_ = label(pages_[0], "Hogar esperando estado", &lv_font_montserrat_16, kText);
    lv_obj_set_width(home_summary_, 560);
    lv_obj_set_pos(home_summary_, 16, 22);
    lv_label_set_long_mode(home_summary_, LV_LABEL_LONG_DOT);

    // Clima: tile cielo relajado (temperatura, condicion, lluvia y la semana con maximas).
    lv_obj_t* status_card = tile(pages_[0], 16, 58, 252, 352, kCieloBg);
    weather_current_ = label(status_card, "--", &lv_font_montserrat_36, kText);
    lv_obj_set_pos(weather_current_, 0, 4);
    weather_unit_ = label(status_card, "\xC2\xB0" "C", &lv_font_montserrat_16, kCieloInk);
    lv_obj_align_to(weather_unit_, weather_current_, LV_ALIGN_OUT_RIGHT_TOP, 4, 6);
    weather_condition_ = label(status_card, "Sin sincronizar", &lv_font_montserrat_14, kCieloInk);
    lv_obj_set_width(weather_condition_, 130);
    lv_obj_set_pos(weather_condition_, 0, 56);
    lv_label_set_long_mode(weather_condition_, LV_LABEL_LONG_DOT);
    // La ubicacion queda para el modo durmiendo; el owner sabe donde vive.
    weather_location_ = label(status_card, "", &lv_font_montserrat_12, kMuted);
    lv_obj_add_flag(weather_location_, LV_OBJ_FLAG_HIDDEN);

    lv_obj_t* rain_chip = lv_obj_create(status_card);
    lv_obj_set_size(rain_chip, 84, 56);
    lv_obj_set_pos(rain_chip, 136, 0);
    flat(rain_chip);
    lv_obj_set_style_radius(rain_chip, 14, 0);
    lv_obj_set_style_bg_color(rain_chip, color(kSurface), 0);
    lv_obj_set_style_pad_all(rain_chip, 0, 0);
    lv_obj_clear_flag(rain_chip, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* rain_value = label(rain_chip, "--", &lv_font_montserrat_16, kText);
    lv_obj_align(rain_value, LV_ALIGN_TOP_MID, 0, 8);
    lv_obj_t* rain_title = label(rain_chip, "Lluvia", &lv_font_montserrat_12, kMuted);
    lv_obj_align(rain_title, LV_ALIGN_TOP_MID, 0, 32);
    weather_chip_values_[1] = rain_value;
    // Viento y antiguedad salen del tile; los buffers siguen vivos para el modo durmiendo.
    weather_chip_values_[0] = label(status_card, "", &lv_font_montserrat_12, kMuted);
    lv_obj_add_flag(weather_chip_values_[0], LV_OBJ_FLAG_HIDDEN);
    weather_meta_ = label(status_card, "", &lv_font_montserrat_12, kMuted);
    lv_obj_add_flag(weather_meta_, LV_OBJ_FLAG_HIDDEN);
    weather_range_ = label(status_card, "", &lv_font_montserrat_12, kMuted);
    lv_obj_add_flag(weather_range_, LV_OBJ_FLAG_HIDDEN);

    // Riel unico detras del grafico: una sola superficie en vez de siete (ahorra memoria LVGL).
    lv_obj_t* weather_rail = lv_obj_create(status_card);
    lv_obj_set_size(weather_rail, kWeatherContentWidth, kWeatherChartHeight + 8);
    lv_obj_set_pos(weather_rail, 0, kWeatherChartTop - 4);
    flat(weather_rail);
    lv_obj_set_style_pad_all(weather_rail, 0, 0);
    lv_obj_set_style_bg_color(weather_rail, color(kSurface), 0);
    lv_obj_set_style_radius(weather_rail, 10, 0);
    lv_obj_clear_flag(weather_rail, LV_OBJ_FLAG_SCROLLABLE);

    // Pronostico: maxima del dia arriba, barra de rango, dia abajo.
    for (unsigned index = 0; index < weather_days_.size(); ++index) {
        const int column = static_cast<int>(index) * kWeatherColumnPitch;
        weather_maxes_[index] = label(status_card, "", &lv_font_montserrat_12, kText);
        lv_obj_set_pos(weather_maxes_[index], column, kWeatherMaxRow);
        lv_obj_set_width(weather_maxes_[index], kWeatherColumnPitch);
        lv_obj_set_style_text_align(weather_maxes_[index], LV_TEXT_ALIGN_CENTER, 0);
        weather_bars_[index] = lv_obj_create(status_card);
        lv_obj_set_size(weather_bars_[index], kWeatherBarWidth, 0);
        lv_obj_set_pos(weather_bars_[index], column + kWeatherBarInset, kWeatherChartTop);
        flat(weather_bars_[index]);
        lv_obj_set_style_pad_all(weather_bars_[index], 0, 0);
        lv_obj_set_style_bg_color(weather_bars_[index], color(kCieloInk), 0);
        lv_obj_set_style_radius(weather_bars_[index], kWeatherBarWidth / 2, 0);
        lv_obj_clear_flag(weather_bars_[index], LV_OBJ_FLAG_SCROLLABLE);
        weather_days_[index] = label(status_card, "--", &lv_font_montserrat_12, kCieloInk);
        lv_obj_set_pos(weather_days_[index], column, kWeatherDayRow);
        lv_obj_set_width(weather_days_[index], kWeatherColumnPitch);
        lv_obj_set_style_text_align(weather_days_[index], LV_TEXT_ALIGN_CENTER, 0);
    }

    // Pendientes: tile ambar.
    lv_obj_t* todo_card = tile(pages_[0], 284, 58, 214, 352, kAmbarBg);
    label(todo_card, "PENDIENTES", &lv_font_montserrat_12, kAmbarInk);
    for (unsigned index = 0; index < inicio_todo_.size(); ++index) {
        inicio_todo_[index] = label(
            todo_card, index == 0 ? "Sin sincronizar" : "",
            &lv_font_montserrat_14, index == 0 ? kMuted : kText);
        lv_obj_set_pos(inicio_todo_[index], 0, 36 + static_cast<int>(index) * 48);
        lv_obj_set_width(inicio_todo_[index], 182);
        lv_label_set_long_mode(inicio_todo_[index], LV_LABEL_LONG_DOT);
    }

    // Proximo en agenda: tile lila.
    lv_obj_t* inicio_agenda_card = tile(pages_[0], 514, 58, 206, 352, kLilaBg);
    label(inicio_agenda_card, "PROXIMO EN AGENDA", &lv_font_montserrat_12, kLilaInk);
    for (unsigned index = 0; index < inicio_agenda_.size(); ++index) {
        inicio_agenda_[index] = label(
            inicio_agenda_card, index == 0 ? "Sin sincronizar" : "",
            &lv_font_montserrat_14, index == 0 ? kMuted : kText);
        lv_obj_set_pos(inicio_agenda_[index], 0, 36 + static_cast<int>(index) * 52);
        lv_obj_set_width(inicio_agenda_[index], 174);
        lv_label_set_long_mode(inicio_agenda_[index], LV_LABEL_LONG_WRAP);
        lv_obj_set_height(inicio_agenda_[index], 44);
    }

    constexpr const char* quick_labels[] = {"Modo noche", "Apagar todo", "Estoy saliendo"};
    constexpr std::uint32_t quick_bg[] = {kLilaBg, kCoralBg, kCieloBg};
    constexpr std::uint32_t quick_ink[] = {kLilaInk, kCoralInk, kCieloInk};
    for (unsigned index = 0; index < 3; ++index) {
        lv_obj_t* button = pill(pages_[0], ui::tokens::quick_actions[index], quick_bg[index]);
        lv_obj_set_style_bg_color(button, color(quick_ink[index]), LV_STATE_PRESSED);
        lv_obj_add_event_cb(button, on_quick_action, LV_EVENT_CLICKED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        lv_obj_t* button_label =
            label(button, quick_labels[index], &lv_font_montserrat_14, quick_ink[index]);
        lv_obj_center(button_label);
    }

    // Tarjetas de luz a la izquierda: cada una es un widget tocable.
    for (unsigned index = 0; index < device_buttons_.size(); ++index) {
        const auto bounds = ui::tokens::light_selectors[index];
        device_buttons_[index] = lv_btn_create(pages_[1]);
        lv_obj_set_size(device_buttons_[index], bounds.width, bounds.height);
        lv_obj_set_pos(device_buttons_[index], bounds.x, bounds.y);
        style_button(device_buttons_[index], kSurface);
        lv_obj_set_style_radius(device_buttons_[index], 20, 0);
        lv_obj_add_event_cb(device_buttons_[index], on_device, LV_EVENT_CLICKED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        device_labels_[index] =
            label(device_buttons_[index], "Sin luz", &lv_font_montserrat_14, kMuted);
        lv_obj_set_width(device_labels_[index], 178);
        lv_obj_set_style_text_align(device_labels_[index], LV_TEXT_ALIGN_LEFT, 0);
        lv_obj_align(device_labels_[index], LV_ALIGN_LEFT_MID, 8, 0);
        lv_obj_add_state(device_buttons_[index], LV_STATE_DISABLED);
    }

    // Control de la luz seleccionada: tile ambar con poder circular, brillo y color.
    lv_obj_t* card = tile(pages_[1], 242, 12, 478, 378, kAmbarBg);
    (void)card;
    selected_name_ = label(pages_[1], "Ninguna luz", &lv_font_montserrat_20, kText);
    lv_obj_set_pos(selected_name_, 264, 30);
    lv_obj_set_width(selected_name_, 300);
    lv_label_set_long_mode(selected_name_, LV_LABEL_LONG_DOT);
    availability_ = label(pages_[1], "No disponible", &lv_font_montserrat_12, kRed);
    lv_obj_set_pos(availability_, 588, 36);
    lv_obj_set_width(availability_, 116);
    lv_obj_set_style_text_align(availability_, LV_TEXT_ALIGN_RIGHT, 0);
    state_label_ = label(pages_[1], "Esperando estado...", &lv_font_montserrat_12, kAmbarInk);
    lv_obj_set_pos(state_label_, 264, 62);

    power_ = lv_btn_create(pages_[1]);
    lv_obj_set_size(power_, ui::tokens::power_button.width, ui::tokens::power_button.height);
    lv_obj_set_pos(power_, ui::tokens::power_button.x, ui::tokens::power_button.y);
    style_button(power_, kSurface);
    lv_obj_set_style_radius(power_, LV_RADIUS_CIRCLE, 0);
    lv_obj_add_event_cb(power_, on_power, LV_EVENT_CLICKED, this);
    power_label_ = label(power_, LV_SYMBOL_POWER, &lv_font_montserrat_26, kAmbarInk);
    lv_obj_center(power_label_);

    lv_obj_t* brightness_title = label(pages_[1], "Brillo", &lv_font_montserrat_12, kAmbarInk);
    lv_obj_set_pos(brightness_title, 346, 108);
    brightness_label_ = label(pages_[1], "0 %", &lv_font_montserrat_20, kText);
    lv_obj_set_width(brightness_label_, 90);
    lv_obj_set_pos(brightness_label_, 614, 100);
    lv_obj_set_style_text_align(brightness_label_, LV_TEXT_ALIGN_RIGHT, 0);
    brightness_ = lv_slider_create(pages_[1]);
    lv_obj_set_size(brightness_, ui::tokens::brightness_slider.width,
                    ui::tokens::brightness_slider.height);
    lv_obj_set_pos(brightness_, ui::tokens::brightness_slider.x, ui::tokens::brightness_slider.y);
    lv_slider_set_range(brightness_, 0, 100);
    lv_obj_set_style_radius(brightness_, ui::tokens::brightness_slider.height / 2, LV_PART_MAIN);
    lv_obj_set_style_radius(brightness_, ui::tokens::brightness_slider.height / 2,
                            LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(brightness_, color(kSurface), LV_PART_MAIN);
    lv_obj_set_style_bg_color(brightness_, color(kAmbarInk), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(brightness_, color(kSurface), LV_PART_KNOB);
    lv_obj_set_style_border_width(brightness_, 2, LV_PART_KNOB);
    lv_obj_set_style_border_color(brightness_, color(kAmbarInk), LV_PART_KNOB);
    lv_obj_set_style_pad_all(brightness_, -2, LV_PART_KNOB);
    lv_obj_add_event_cb(brightness_, on_brightness, LV_EVENT_VALUE_CHANGED, this);
    lv_obj_add_event_cb(brightness_, on_brightness_release, LV_EVENT_RELEASED, this);
    lv_obj_add_event_cb(brightness_, on_brightness_release, LV_EVENT_PRESS_LOST, this);

    // Color continuo: barra de matiz (6 segmentos con gradiente) + slider transparente encima.
    lv_obj_t* color_title = label(pages_[1], "Color", &lv_font_montserrat_12, kAmbarInk);
    lv_obj_set_width(color_title, ui::tokens::hue_slider.width);
    lv_obj_set_style_text_align(color_title, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_pos(color_title, ui::tokens::hue_slider.x, 200);
    constexpr std::array<std::uint32_t, 7> hue_stops = {0xFF4D4D, 0xFFC24D, 0xEDE04A, 0x4DD97A,
                                                        0x4DC3FF, 0x7A6CFF, 0xFF4D4D};
    const auto hue_bounds = ui::tokens::hue_slider;
    const int segment_width = hue_bounds.width / 6;
    for (unsigned index = 0; index < 6; ++index) {
        lv_obj_t* segment = lv_obj_create(pages_[1]);
        lv_obj_set_size(segment, segment_width, 30);
        lv_obj_set_pos(segment, hue_bounds.x + static_cast<int>(index) * segment_width,
                       hue_bounds.y + 7);
        flat(segment);
        lv_obj_set_style_pad_all(segment, 0, 0);
        lv_obj_set_style_radius(segment, index == 0 || index == 5 ? 15 : 0, 0);
        lv_obj_set_style_bg_color(segment, color(hue_stops[index]), 0);
        lv_obj_set_style_bg_grad_color(segment, color(hue_stops[index + 1]), 0);
        lv_obj_set_style_bg_grad_dir(segment, LV_GRAD_DIR_HOR, 0);
        lv_obj_clear_flag(segment, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_clear_flag(segment, LV_OBJ_FLAG_CLICKABLE);
    }
    hue_ = lv_slider_create(pages_[1]);
    lv_obj_set_size(hue_, hue_bounds.width, hue_bounds.height);
    lv_obj_set_pos(hue_, hue_bounds.x, hue_bounds.y);
    lv_slider_set_range(hue_, 0, 359);
    lv_obj_set_style_bg_opa(hue_, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(hue_, LV_OPA_TRANSP, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(hue_, color(kSurface), LV_PART_KNOB);
    lv_obj_set_style_border_width(hue_, 2, LV_PART_KNOB);
    lv_obj_set_style_border_color(hue_, color(kText), LV_PART_KNOB);
    lv_obj_set_style_pad_all(hue_, -8, LV_PART_KNOB);
    lv_obj_add_event_cb(hue_, on_hue_release, LV_EVENT_RELEASED, this);
    lv_obj_add_event_cb(hue_, on_hue_release, LV_EVENT_PRESS_LOST, this);

    // Presets: solo calido y frio (pedido del owner).
    constexpr std::array<std::uint32_t, 2> color_values = {0xFFB45C, 0xCFE4F2};
    constexpr const char* color_labels[] = {"Calido", "Frio"};
    for (unsigned index = 0; index < color_values.size(); ++index) {
        lv_obj_t* preset = pill(pages_[1], ui::tokens::color_presets[index], kSurface);
        color_buttons_[index] = preset;
        lv_obj_add_event_cb(preset, on_color, LV_EVENT_CLICKED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(color_values[index])));
        lv_obj_t* preset_label =
            label(preset, color_labels[index], &lv_font_montserrat_12,
                  index == 0 ? kAmbarInk : kCieloInk);
        lv_obj_center(preset_label);
    }

    for (unsigned index = 0; index < scene_buttons_.size(); ++index) {
        scene_buttons_[index] = pill(pages_[1], ui::tokens::scene_buttons[index], kSurface);
        lv_obj_add_event_cb(scene_buttons_[index], on_scene, LV_EVENT_CLICKED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        scene_labels_[index] =
            label(scene_buttons_[index], "Sin escena", &lv_font_montserrat_14, kMuted);
        lv_obj_center(scene_labels_[index]);
        lv_obj_add_state(scene_buttons_[index], LV_STATE_DISABLED);
    }

    lv_obj_t* media = tile(pages_[2], 16, 12, 452, 432, kSelvaBg);
    lv_obj_t* spotify_logo = lv_img_create(media);
    lv_img_set_src(spotify_logo, &wyss_spotify_logo);
    lv_obj_set_pos(spotify_logo, 0, 0);
    lv_obj_t* media_eyebrow = label(media, "SPOTIFY", &lv_font_montserrat_14, kSelvaInk);
    lv_obj_set_pos(media_eyebrow, 40, 0);
    media_device_ = label(media, "-", &lv_font_montserrat_12, kSelvaInk);
    lv_obj_set_width(media_device_, 200);
    lv_obj_set_pos(media_device_, 220, 2);
    lv_obj_set_style_text_align(media_device_, LV_TEXT_ALIGN_RIGHT, 0);
    lv_label_set_long_mode(media_device_, LV_LABEL_LONG_DOT);

    media_title_ = label(media, "Spotify no vinculado", &lv_font_montserrat_26, kText);
    lv_obj_set_pos(media_title_, 0, 64);
    lv_obj_set_width(media_title_, 420);
    lv_obj_set_style_text_align(media_title_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(media_title_, LV_LABEL_LONG_DOT);
    media_artist_ = label(media, "Vinculalo desde Wyss", &lv_font_montserrat_14, kSelvaInk);
    lv_obj_set_pos(media_artist_, 0, 104);
    lv_obj_set_width(media_artist_, 420);
    lv_obj_set_style_text_align(media_artist_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(media_artist_, LV_LABEL_LONG_DOT);

    // Transporte centrado: anterior / play selva relleno / siguiente.
    constexpr const char* media_symbols[] = {LV_SYMBOL_PREV, LV_SYMBOL_PLAY, LV_SYMBOL_NEXT};
    constexpr int media_sizes[] = {64, 92, 64};
    constexpr int media_xs[] = {64, 164, 292};
    constexpr int media_ys[] = {160, 146, 160};
    for (unsigned index = 0; index < 3; ++index) {
        media_buttons_[index] = lv_btn_create(media);
        lv_obj_set_size(media_buttons_[index], media_sizes[index], media_sizes[index]);
        lv_obj_set_pos(media_buttons_[index], media_xs[index], media_ys[index]);
        style_button(media_buttons_[index], index == 1 ? kSelvaInk : kSurface);
        lv_obj_set_style_radius(media_buttons_[index], LV_RADIUS_CIRCLE, 0);
        lv_obj_t* button_label = label(
            media_buttons_[index], media_symbols[index],
            index == 1 ? &lv_font_montserrat_30 : &lv_font_montserrat_20,
            index == 1 ? kSurface : kText);
        lv_obj_center(button_label);
        lv_obj_add_state(media_buttons_[index], LV_STATE_DISABLED);
    }
    media_play_label_ = lv_obj_get_child(media_buttons_[1], 0);

    media_buttons_[3] = lv_btn_create(media);
    lv_obj_set_size(media_buttons_[3], 130, 44);
    lv_obj_set_pos(media_buttons_[3], 145, 254);
    style_button(media_buttons_[3], kSurface);
    lv_obj_set_style_radius(media_buttons_[3], 22, 0);
    media_favorite_label_ =
        label(media_buttons_[3], "Favorito", &lv_font_montserrat_12, kSelvaInk);
    lv_obj_center(media_favorite_label_);
    lv_obj_add_state(media_buttons_[3], LV_STATE_DISABLED);

    media_time_now_ = label(media, "0:00", &lv_font_montserrat_12, kMuted);
    lv_obj_set_pos(media_time_now_, 0, 320);
    media_progress_ = lv_bar_create(media);
    lv_obj_set_size(media_progress_, 300, 8);
    lv_obj_set_pos(media_progress_, 48, 324);
    lv_bar_set_range(media_progress_, 0, 1000);
    lv_obj_set_style_radius(media_progress_, 4, LV_PART_MAIN);
    lv_obj_set_style_radius(media_progress_, 4, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(media_progress_, color(kSurface), LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_progress_, color(kSelvaInk), LV_PART_INDICATOR);
    media_progress_label_ = label(media, "0:00", &lv_font_montserrat_12, kMuted);
    lv_obj_set_width(media_progress_label_, 60);
    lv_obj_set_pos(media_progress_label_, 356, 320);
    lv_obj_set_style_text_align(media_progress_label_, LV_TEXT_ALIGN_RIGHT, 0);

    lv_obj_t* queue_card = panel(pages_[2], 484, 12, 236, 432);
    label(queue_card, "A CONTINUACION", &lv_font_montserrat_12, kSelvaInk);
    media_queue_empty_ = label(queue_card, "Sin cola", &lv_font_montserrat_14, kMuted);
    lv_obj_set_pos(media_queue_empty_, 0, 34);
    for (unsigned index = 0; index < media_queue_titles_.size(); ++index) {
        media_queue_titles_[index] =
            label(queue_card, "", &lv_font_montserrat_14, kText);
        lv_obj_set_pos(media_queue_titles_[index], 0, 34 + static_cast<int>(index) * 70);
        lv_obj_set_width(media_queue_titles_[index], 204);
        lv_label_set_long_mode(media_queue_titles_[index], LV_LABEL_LONG_DOT);
        media_queue_artists_[index] =
            label(queue_card, "", &lv_font_montserrat_12, kMuted);
        lv_obj_set_pos(media_queue_artists_[index], 0, 56 + static_cast<int>(index) * 70);
        lv_obj_set_width(media_queue_artists_[index], 204);
        lv_label_set_long_mode(media_queue_artists_[index], LV_LABEL_LONG_DOT);
    }

    lv_obj_add_event_cb(media_buttons_[0], on_media_previous, LV_EVENT_CLICKED, this);
    lv_obj_add_event_cb(media_buttons_[1], on_media_play, LV_EVENT_CLICKED, this);
    lv_obj_add_event_cb(media_buttons_[2], on_media_next, LV_EVENT_CLICKED, this);
    lv_obj_add_event_cb(media_buttons_[3], on_media_favorite, LV_EVENT_CLICKED, this);

    // Fila de volumen: existe solo cuando el dispositivo lo soporta (se muestra en render).
    media_volume_row_ = lv_obj_create(media);
    lv_obj_set_size(media_volume_row_, 420, 48);
    lv_obj_set_pos(media_volume_row_, 0, 348);
    lv_obj_set_style_bg_opa(media_volume_row_, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(media_volume_row_, 0, 0);
    lv_obj_set_style_pad_all(media_volume_row_, 0, 0);
    lv_obj_clear_flag(media_volume_row_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* volume_title =
        label(media_volume_row_, LV_SYMBOL_VOLUME_MAX, &lv_font_montserrat_16, kMuted);
    lv_obj_set_pos(volume_title, 0, 12);
    media_volume_ = lv_slider_create(media_volume_row_);
    lv_obj_set_size(media_volume_, 260, 40);
    lv_obj_set_pos(media_volume_, 36, 4);
    lv_slider_set_range(media_volume_, 0, 100);
    lv_obj_set_style_radius(media_volume_, 20, LV_PART_MAIN);
    lv_obj_set_style_radius(media_volume_, 20, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(media_volume_, color(kSurface), LV_PART_MAIN);
    lv_obj_set_style_bg_color(media_volume_, color(kSelvaInk), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(media_volume_, color(kSurface), LV_PART_KNOB);
    lv_obj_set_style_border_width(media_volume_, 2, LV_PART_KNOB);
    lv_obj_set_style_border_color(media_volume_, color(kSelvaInk), LV_PART_KNOB);
    lv_obj_set_style_pad_all(media_volume_, 6, LV_PART_KNOB);
    lv_obj_add_event_cb(media_volume_, on_media_volume, LV_EVENT_VALUE_CHANGED, this);
    lv_obj_add_event_cb(media_volume_, on_media_volume_release, LV_EVENT_RELEASED, this);
    lv_obj_add_event_cb(media_volume_, on_media_volume_release, LV_EVENT_PRESS_LOST, this);
    media_volume_label_ = label(media_volume_row_, "-- %", &lv_font_montserrat_20, kText);
    lv_obj_set_width(media_volume_label_, 100);
    lv_obj_set_pos(media_volume_label_, 316, 8);
    lv_obj_set_style_text_align(media_volume_label_, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_add_flag(media_volume_row_, LV_OBJ_FLAG_HIDDEN);

    lv_obj_t* agenda = tile(pages_[3], 16, 12, 452, 444, kLilaBg);
    label(agenda, "AGENDA", &lv_font_montserrat_12, kLilaInk);
    agenda_state_ = label(agenda, "Sin eventos proyectados", &lv_font_montserrat_20, kText);
    lv_obj_set_pos(agenda_state_, 0, 28);
    lv_obj_set_width(agenda_state_, 420);
    lv_label_set_long_mode(agenda_state_, LV_LABEL_LONG_DOT);
    agenda_meta_ = label(agenda, "Esperando Calendar", &lv_font_montserrat_12, kLilaInk);
    lv_obj_set_pos(agenda_meta_, 0, 62);
    for (unsigned index = 0; index < agenda_events_.size(); ++index) {
        agenda_events_[index] = label(agenda, "--", &lv_font_montserrat_14, kText);
        lv_obj_set_pos(agenda_events_[index], 0, 100 + static_cast<int>(index) * 46);
        lv_obj_set_width(agenda_events_[index], 420);
        lv_label_set_long_mode(agenda_events_[index], LV_LABEL_LONG_DOT);
    }

    lv_obj_t* reminder_card = tile(pages_[3], 484, 12, 236, 210, kAmbarBg);
    label(reminder_card, "RECORDATORIOS", &lv_font_montserrat_12, kAmbarInk);
    reminder_state_ = label(reminder_card, "Sin sincronizar", &lv_font_montserrat_14, kText);
    lv_obj_set_pos(reminder_state_, 0, 32);
    lv_obj_set_width(reminder_state_, 204);
    lv_label_set_long_mode(reminder_state_, LV_LABEL_LONG_WRAP);

    lv_obj_t* timer_card = tile(pages_[3], 484, 234, 236, 222, kCoralBg);
    label(timer_card, "TIMERS", &lv_font_montserrat_12, kCoralInk);
    timer_state_ = label(timer_card, "Sin sincronizar", &lv_font_montserrat_14, kText);
    lv_obj_set_pos(timer_state_, 0, 32);
    lv_obj_set_width(timer_state_, 204);
    lv_label_set_long_mode(timer_state_, LV_LABEL_LONG_WRAP);

    lv_obj_t* system_status = panel(pages_[4], 16, 12, 704, 92);
    lv_obj_t* system_dot = lv_obj_create(system_status);
    lv_obj_set_size(system_dot, 44, 44);
    lv_obj_set_pos(system_dot, 0, 8);
    flat(system_dot);
    lv_obj_set_style_radius(system_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(system_dot, color(kRed), 0);
    lv_obj_clear_flag(system_dot, LV_OBJ_FLAG_SCROLLABLE);
    system_connection_ = label(system_status, "Home Edge: sin conexion", &lv_font_montserrat_20,
                               kRed);
    lv_obj_set_pos(system_connection_, 60, 18);
    lv_obj_set_width(system_connection_, 600);
    lv_label_set_long_mode(system_connection_, LV_LABEL_LONG_DOT);

    lv_obj_t* protocol_card = panel(pages_[4], 16, 116, 346, 340);
    label(protocol_card, "PROTOCOLO", &lv_font_montserrat_12, kCieloInk);
    lv_obj_t* protocol =
        label(protocol_card, "v1 estable - v2 opt-in", &lv_font_montserrat_14, kText);
    lv_obj_set_pos(protocol, 0, 32);
    lv_obj_t* diagnostic_card = panel(pages_[4], 370, 116, 350, 340);
    label(diagnostic_card, "DIAGNOSTICO", &lv_font_montserrat_12, kCoralInk);
    lv_obj_t* diagnostic =
        label(diagnostic_card, "Sin datos de latencia todavia", &lv_font_montserrat_14, kText);
    lv_obj_set_pos(diagnostic, 0, 32);

    conversation_layer_ = lv_obj_create(screen);
    prepare_layer(conversation_layer_);
    lv_obj_set_style_bg_color(conversation_layer_, color(kCanvas), 0);
    lv_obj_set_style_bg_opa(conversation_layer_, LV_OPA_COVER, 0);
    lv_obj_t* back = lv_btn_create(conversation_layer_);
    lv_obj_set_size(back, 48, 48);
    lv_obj_set_pos(back, 16, 12);
    style_button(back, kSurface);
    lv_obj_set_style_radius(back, LV_RADIUS_CIRCLE, 0);
    lv_obj_add_event_cb(back, on_conversation_back, LV_EVENT_CLICKED, this);
    lv_obj_t* back_label = label(back, LV_SYMBOL_LEFT, &lv_font_montserrat_16, kText);
    lv_obj_center(back_label);
    lv_obj_t* conversation_title =
        label(conversation_layer_, "Conversacion con Wyss", &lv_font_montserrat_12, kCoralInk);
    lv_obj_set_pos(conversation_title, 80, 30);
    conversation_state_ =
        label(conversation_layer_, "Que queres que haga?", &lv_font_montserrat_20, kText);
    lv_obj_set_pos(conversation_state_, 36, 82);
    lv_obj_t* hint =
        label(conversation_layer_, "Yo preparo un plan y te pido permiso cuando corresponde.",
              &lv_font_montserrat_12, kMuted);
    lv_obj_set_pos(hint, 36, 118);
    composer_ = lv_textarea_create(conversation_layer_);
    lv_obj_set_size(composer_, 610, 68);
    lv_obj_set_pos(composer_, 36, 154);
    lv_textarea_set_placeholder_text(composer_, "Ej.: deja el living listo para ver una pelicula");
    lv_textarea_set_one_line(composer_, true);
    lv_obj_set_style_bg_color(composer_, color(kSurface), 0);
    lv_obj_set_style_text_color(composer_, color(kText), 0);
    lv_obj_set_style_text_font(composer_, &lv_font_montserrat_14, 0);
    flat(composer_);
    lv_obj_set_style_radius(composer_, 32, 0);
    lv_obj_add_event_cb(composer_, on_text_focus, LV_EVENT_FOCUSED, this);
    lv_obj_t* submit = lv_btn_create(conversation_layer_);
    lv_obj_set_size(submit, 100, 68);
    lv_obj_set_pos(submit, 664, 154);
    style_button(submit, kCoral);
    lv_obj_set_style_radius(submit, 34, 0);
    lv_obj_add_event_cb(submit, on_submit, LV_EVENT_CLICKED, this);
    lv_obj_t* submit_label = label(submit, LV_SYMBOL_RIGHT, &lv_font_montserrat_20, kSurface);
    lv_obj_center(submit_label);
    execution_ =
        label(conversation_layer_, "Listo para orquestar.", &lv_font_montserrat_14, kMuted);
    lv_obj_set_pos(execution_, 36, 240);
    lv_obj_set_size(execution_, 728, 58);
    lv_label_set_long_mode(execution_, LV_LABEL_LONG_WRAP);
    keyboard_ = lv_keyboard_create(conversation_layer_);
    lv_obj_set_size(keyboard_, 728, 190);
    lv_obj_set_pos(keyboard_, 36, 282);
    lv_keyboard_set_textarea(keyboard_, composer_);
    lv_obj_set_style_bg_color(keyboard_, color(kSurface), 0);
    lv_obj_set_style_text_font(keyboard_, &lv_font_montserrat_12, 0);
    lv_obj_add_flag(keyboard_, LV_OBJ_FLAG_HIDDEN);

    sleeping_layer_ = lv_obj_create(screen);
    prepare_layer(sleeping_layer_);
    lv_obj_set_style_bg_color(sleeping_layer_, color(kNight), 0);
    lv_obj_set_style_bg_opa(sleeping_layer_, LV_OPA_COVER, 0);
    lv_obj_t* sleeping_title = label(sleeping_layer_, "Wyss", &lv_font_montserrat_14, kNightMuted);
    lv_obj_set_pos(sleeping_title, 24, 22);
    sleeping_connection_ = label(sleeping_layer_, LV_SYMBOL_WIFI, &lv_font_montserrat_14, kRed);
    lv_obj_align(sleeping_connection_, LV_ALIGN_TOP_RIGHT, -24, 24);
    // Nucleo durmiente: anillo coral tenue sobre carbon, estilo velador.
    lv_obj_t* sleeping_core = lv_obj_create(sleeping_layer_);
    lv_obj_set_size(sleeping_core, 168, 168);
    lv_obj_set_pos(sleeping_core, 316, 92);
    lv_obj_set_style_radius(sleeping_core, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(sleeping_core, color(kNightChip), 0);
    lv_obj_set_style_border_width(sleeping_core, 3, 0);
    lv_obj_set_style_border_color(sleeping_core, color(kCoral), 0);
    lv_obj_set_style_shadow_width(sleeping_core, 0, 0);
    lv_obj_clear_flag(sleeping_core, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* sleeping_label =
        label(sleeping_core, "Wyss\ndurmiendo", &lv_font_montserrat_20, kNightInk);
    lv_obj_set_style_text_align(sleeping_label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_center(sleeping_label);
    sleeping_weather_ = label(
        sleeping_layer_, "Clima sin sincronizar   -   Agenda sin sincronizar   -   Sin timers",
        &lv_font_montserrat_14, kNightMuted);
    lv_obj_set_width(sleeping_weather_, 740);
    lv_obj_set_style_text_align(sleeping_weather_, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(sleeping_weather_, LV_ALIGN_BOTTOM_MID, 0, -104);
    lv_obj_t* manual = lv_btn_create(sleeping_layer_);
    lv_obj_set_size(manual, ui::tokens::manual_button.width, ui::tokens::manual_button.height);
    lv_obj_set_pos(manual, ui::tokens::manual_button.x, ui::tokens::manual_button.y);
    lv_obj_set_style_shadow_width(manual, 0, 0);
    lv_obj_set_style_border_width(manual, 0, 0);
    lv_obj_set_style_bg_color(manual, color(kNightChip), 0);
    lv_obj_set_style_bg_color(manual, color(kCoral), LV_STATE_PRESSED);
    lv_obj_set_style_radius(manual, ui::tokens::manual_button.height / 2, 0);
    lv_obj_add_event_cb(manual, on_manual, LV_EVENT_CLICKED, this);
    lv_obj_t* manual_label = label(manual, "Toca para despertar", &lv_font_montserrat_14,
                                   kNightInk);
    lv_obj_center(manual_label);

    modal_ = lv_obj_create(screen);
    lv_obj_set_size(modal_, 560, 330);
    lv_obj_align(modal_, LV_ALIGN_CENTER, 0, 10);
    lv_obj_set_style_bg_color(modal_, color(kSurfaceRaised), 0);
    lv_obj_set_style_pad_all(modal_, 24, 0);
    flat(modal_);
    lv_obj_add_flag(modal_, LV_OBJ_FLAG_HIDDEN);
    modal_title_ = label(modal_, "Plan de Wyss", &lv_font_montserrat_20, kText);
    modal_body_ = label(modal_, "", &lv_font_montserrat_14, kMuted);
    lv_obj_set_width(modal_body_, 510);
    lv_label_set_long_mode(modal_body_, LV_LABEL_LONG_WRAP);
    lv_obj_set_pos(modal_body_, 0, 52);
    constexpr const char* answers[] = {"Cancelar", "Confirmar"};
    for (unsigned index = 0; index < 2; ++index) {
        lv_obj_t* answer = lv_btn_create(modal_);
        lv_obj_set_size(answer, 180, 58);
        lv_obj_set_pos(answer, 80 + static_cast<int>(index) * 210, 236);
        style_button(answer, index == 0 ? kCanvas : kCoral);
        lv_obj_set_style_radius(answer, 29, 0);
        lv_obj_add_event_cb(answer, on_plan_answer, LV_EVENT_CLICKED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        lv_obj_t* answer_label = label(answer, answers[index], &lv_font_montserrat_14,
                                       index == 0 ? kText : kSurface);
        lv_obj_center(answer_label);
    }

    toast_ = label(screen, "", &lv_font_montserrat_12, kText);
    lv_obj_set_style_bg_color(toast_, color(kSurfaceRaised), 0);
    lv_obj_set_style_bg_opa(toast_, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_hor(toast_, 16, 0);
    lv_obj_set_style_pad_ver(toast_, 10, 0);
    lv_obj_align(toast_, LV_ALIGN_BOTTOM_MID, 0, -14);
    lv_obj_add_flag(toast_, LV_OBJ_FLAG_HIDDEN);
    disable_touch_scroll(screen);
    show_page(ui::ManualPage::Inicio);
    set_mode(ui::ShellMode::Manual);
}

void LvglPanelView::set_mode(ui::ShellMode mode) {
    mode_ = mode;
    lv_obj_add_flag(manual_layer_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(sleeping_layer_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(conversation_layer_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_t* active = manual_layer_;
    if (mode == ui::ShellMode::Sleeping) {
        active = sleeping_layer_;
    } else if (mode == ui::ShellMode::Conversation) {
        active = conversation_layer_;
    }
    lv_obj_clear_flag(active, LV_OBJ_FLAG_HIDDEN);
    lv_timer_set_period(_lv_disp_get_refr_timer(lv_disp_get_default()),
                        mode == ui::ShellMode::Sleeping ? ui::tokens::sleeping_refresh_ms
                                                        : ui::tokens::active_refresh_ms);
}

void LvglPanelView::show_page(ui::ManualPage page) {
    auto active_index = static_cast<unsigned>(page);
    if (active_index >= std::size(pages_)) {
        active_index = static_cast<unsigned>(ui::ManualPage::Inicio);
    }
    active_page_ = static_cast<ui::ManualPage>(active_index);
    for (unsigned index = 0; index < 5; ++index) {
        if (index == active_index) {
            lv_obj_clear_flag(pages_[index], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_color(tabs_[index], color(kCoralBg), 0);
            lv_obj_set_style_text_color(lv_obj_get_child(tabs_[index], 0), color(kCoralInk), 0);
        } else {
            lv_obj_add_flag(pages_[index], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_color(tabs_[index], color(kSurface), 0);
            lv_obj_set_style_text_color(lv_obj_get_child(tabs_[index], 0), color(kMuted), 0);
        }
    }
    // El foco dibujado no es texto: se recolorea por fondo.
    if (light_icon_glass_ != nullptr) {
        const auto ink = active_index == 1 ? kCoralInk : kMuted;
        lv_obj_set_style_bg_color(light_icon_glass_, color(ink), 0);
        lv_obj_set_style_bg_color(light_icon_base_, color(ink), 0);
    }
    set_mode(ui::ShellMode::Manual);
}

bool LvglPanelView::select_entity(std::string_view entity_id) {
    const auto found = std::find_if(devices_.begin(), devices_.end(), [&](const auto& device) {
        return device.entity_id == entity_id && device.entity_id.starts_with("light.");
    });
    if (found == devices_.end()) return false;
    selected_entity_ = found->entity_id;
    refresh_home_controls();
    return true;
}

void LvglPanelView::render_connection(domain::ConnectionState state) {
    const char* text = "sin conexion";
    std::uint32_t text_color = kRed;
    if (state == domain::ConnectionState::Online) {
        text = "Wyss en linea";
        text_color = kGreen;
    } else if (state == domain::ConnectionState::Discovering) {
        text = "conectando...";
        text_color = kAmber;
    } else if (state == domain::ConnectionState::Degraded) {
        text = "conexion degradada";
        text_color = kAmber;
    }
    // Rail y durmiendo muestran solo el punto de estado; el texto completo vive en Sistema.
    lv_obj_set_style_text_color(connection_, color(text_color), 0);
    lv_obj_set_style_text_color(sleeping_connection_, color(text_color), 0);
    std::snprintf(execution_text_, sizeof(execution_text_), "Home Edge: %s", text);
    lv_label_set_text(system_connection_, execution_text_);
    lv_obj_set_style_text_color(system_connection_, color(text_color), 0);
}

void LvglPanelView::render_devices(std::span<const domain::DeviceState> devices) {
    devices_.assign(devices.begin(), devices.end());
    refresh_home_controls();
}

void LvglPanelView::render_media(const domain::MediaState& state) {
    media_playing_ = state.playing;
    const bool controllable = state.linked && state.available && state.device &&
                              state.device->active && !state.device->restricted;
    const char* title = "Spotify no vinculado";
    const char* detail = "Habilitalo desde Wyss";
    if (state.linked && state.available) {
        title = state.title.empty() ? "Reproduccion sin titulo" : state.title.c_str();
        detail = state.artist.empty() ? "Artista no informado" : state.artist.c_str();
    } else if (state.linked) {
        title = "Sin reproduccion activa";
        if (state.error_code == "rate_limited") {
            detail = "Spotify pidio esperar antes de reintentar";
        } else if (state.error_code == "reauthorization_required") {
            detail = "Volve a vincular Spotify desde Wyss";
        } else if (state.error_code == "device_inactive") {
            detail = "Abri Spotify en un dispositivo";
        } else if (!state.error_code.empty()) {
            detail = "Spotify temporalmente no disponible";
        }
    }
    std::snprintf(media_title_text_, sizeof(media_title_text_), "%s", ascii_safe(title).c_str());
    std::snprintf(media_artist_text_, sizeof(media_artist_text_), "%s", ascii_safe(detail).c_str());
    lv_label_set_text_static(media_title_, media_title_text_);
    lv_label_set_text_static(media_artist_, media_artist_text_);

    const char* device_name = state.device ? state.device->name.c_str() : "-";
    std::snprintf(media_device_text_, sizeof(media_device_text_), "%s %s", LV_SYMBOL_AUDIO,
                  ascii_safe(device_name).c_str());
    lv_label_set_text_static(media_device_, media_device_text_);

    const std::uint32_t progress = std::min(state.progress_ms, state.duration_ms);
    const int ratio = state.duration_ms == 0
                          ? 0
                          : static_cast<int>((static_cast<std::uint64_t>(progress) * 1000U) /
                                             state.duration_ms);
    lv_bar_set_value(media_progress_, ratio, LV_ANIM_OFF);
    std::snprintf(media_time_now_text_, sizeof(media_time_now_text_), "%lu:%02lu",
                  static_cast<unsigned long>(progress / 60000U),
                  static_cast<unsigned long>((progress / 1000U) % 60U));
    lv_label_set_text_static(media_time_now_, media_time_now_text_);
    std::snprintf(media_progress_text_, sizeof(media_progress_text_), "%lu:%02lu",
                  static_cast<unsigned long>(state.duration_ms / 60000U),
                  static_cast<unsigned long>((state.duration_ms / 1000U) % 60U));
    lv_label_set_text_static(media_progress_label_, media_progress_text_);

    lv_label_set_text(media_play_label_, state.playing ? LV_SYMBOL_PAUSE : LV_SYMBOL_PLAY);
    lv_label_set_text(media_favorite_label_, state.favorite ? "Guardado" : "Favorito");
    lv_obj_set_style_bg_color(media_buttons_[3],
                              color(state.favorite ? kSelvaInk : kSurface), 0);
    lv_obj_set_style_text_color(media_favorite_label_,
                                color(state.favorite ? kSurface : kSelvaInk), 0);

    for (unsigned index = 0; index < media_queue_titles_.size(); ++index) {
        if (index < state.queue.size()) {
            lv_label_set_text(media_queue_titles_[index],
                              ascii_safe(state.queue[index].title).c_str());
            lv_label_set_text(media_queue_artists_[index],
                              ascii_safe(state.queue[index].artist).c_str());
        } else {
            lv_label_set_text(media_queue_titles_[index], "");
            lv_label_set_text(media_queue_artists_[index], "");
        }
    }
    if (state.queue.empty()) {
        lv_obj_clear_flag(media_queue_empty_, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(media_queue_empty_, LV_OBJ_FLAG_HIDDEN);
    }
    for (auto* button : media_buttons_) {
        if (controllable) {
            lv_obj_clear_state(button, LV_STATE_DISABLED);
        } else {
            lv_obj_add_state(button, LV_STATE_DISABLED);
        }
    }

    const bool volume_available = controllable && state.device &&
                                  state.device->supports_volume && state.device->volume;
    if (volume_available) {
        lv_obj_clear_flag(media_volume_row_, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_state(media_volume_, LV_STATE_DISABLED);
        if (!media_volume_active_ && lv_slider_get_value(media_volume_) != *state.device->volume) {
            suppress_media_volume_ = true;
            lv_slider_set_value(media_volume_, *state.device->volume, LV_ANIM_OFF);
            suppress_media_volume_ = false;
        }
        std::snprintf(media_volume_text_, sizeof(media_volume_text_), "%u %%",
                      *state.device->volume);
        lv_label_set_text_static(media_volume_label_, media_volume_text_);
    } else {
        // Sin soporte de volumen (p.ej. smartphone): la fila desaparece en vez
        // de quedar muerta en pantalla.
        lv_obj_add_flag(media_volume_row_, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_state(media_volume_, LV_STATE_DISABLED);
    }
}

void LvglPanelView::render_weather(const domain::WeatherState& state) {
    char age[24]{};
    format_age(age, sizeof(age), state.age_seconds);
    const std::uint32_t state_color = !state.available ? kRed : (state.stale ? kAmber : kText);

    std::uint8_t max_precipitation = 0;
    for (const auto& day : state.days) {
        if (day.precipitation_probability) {
            max_precipitation = std::max(max_precipitation, *day.precipitation_probability);
        }
    }

    if (!state.available || !state.temperature) {
        std::snprintf(weather_current_text_, sizeof(weather_current_text_), "--");
        std::snprintf(weather_condition_text_, sizeof(weather_condition_text_), "%s",
                      weather_error(state.error_code));
        std::snprintf(weather_chip_text_[0], sizeof(weather_chip_text_[0]), "--");
        std::snprintf(weather_chip_text_[1], sizeof(weather_chip_text_[1]), "--");
        std::snprintf(weather_meta_text_, sizeof(weather_meta_text_), "--");
        std::snprintf(sleeping_weather_part_, sizeof(sleeping_weather_part_),
                      "Resistencia - clima no disponible");
    } else {
        const char* condition = weather_condition(state.condition);
        std::snprintf(weather_current_text_, sizeof(weather_current_text_), "%.1f",
                      static_cast<double>(*state.temperature));
        std::snprintf(weather_condition_text_, sizeof(weather_condition_text_), "%s", condition);
        if (state.wind_kmh) {
            std::snprintf(weather_chip_text_[0], sizeof(weather_chip_text_[0]), "%.0f km/h",
                          static_cast<double>(*state.wind_kmh));
        } else {
            std::snprintf(weather_chip_text_[0], sizeof(weather_chip_text_[0]), "--");
        }
        std::snprintf(weather_chip_text_[1], sizeof(weather_chip_text_[1]), "%u%%",
                      static_cast<unsigned>(max_precipitation));
        std::snprintf(weather_meta_text_, sizeof(weather_meta_text_), "%s%s",
                      state.stale ? "CACHE " : "", age);
        std::snprintf(sleeping_weather_part_, sizeof(sleeping_weather_part_),
                      "Resistencia - %.0f C - %s - %s hace %s",
                      static_cast<double>(*state.temperature), condition,
                      state.stale ? "CACHE" : "actualizado", age);
    }
    const std::string location =
        ascii_safe(state.location.empty() ? std::string_view{"Sin ubicacion"} : state.location);
    std::snprintf(weather_location_text_, sizeof(weather_location_text_), "%s", location.c_str());

    lv_label_set_text_static(weather_current_, weather_current_text_);
    lv_obj_set_style_text_color(weather_current_, color(state_color), 0);
    lv_obj_align_to(weather_unit_, weather_current_, LV_ALIGN_OUT_RIGHT_TOP, 4, 10);
    lv_label_set_text_static(weather_condition_, weather_condition_text_);
    lv_obj_set_style_text_color(weather_condition_, color(state.available ? kCieloInk : kRed), 0);
    lv_label_set_text_static(weather_location_, weather_location_text_);
    lv_label_set_text_static(weather_chip_values_[0], weather_chip_text_[0]);
    lv_label_set_text_static(weather_chip_values_[1], weather_chip_text_[1]);
    lv_label_set_text_static(weather_meta_, weather_meta_text_);
    lv_obj_set_style_text_color(weather_meta_, color(state.stale ? kAmber : kText), 0);
    refresh_sleeping_summary();
    lv_obj_set_style_text_color(
        sleeping_weather_,
        color(!state.available ? kRed : (state.stale ? kAmber : kNightMuted)), 0);

    // Escala compartida por la semana: la barra de cada dia cubre su minima y maxima.
    const std::size_t forecast_days =
        state.available ? std::min(state.days.size(), weather_days_.size()) : 0U;
    float week_min = 0.0F;
    float week_max = 0.0F;
    if (forecast_days > 0U) {
        week_min = state.days[0].temperature_min;
        week_max = state.days[0].temperature_max;
        for (std::size_t index = 0; index < forecast_days; ++index) {
            week_min = std::min(week_min, state.days[index].temperature_min);
            week_max = std::max(week_max, state.days[index].temperature_max);
        }
        std::snprintf(weather_range_text_, sizeof(weather_range_text_), "min %.0f / max %.0f",
                      static_cast<double>(week_min), static_cast<double>(week_max));
    } else {
        std::snprintf(weather_range_text_, sizeof(weather_range_text_), "min -- / max --");
    }
    // Maxima del dia sobre cada barra (pedido del owner: la semana habla en temperaturas).
    for (unsigned index = 0; index < weather_maxes_.size(); ++index) {
        if (index < forecast_days) {
            std::snprintf(weather_max_text_[index], sizeof(weather_max_text_[index]), "%.0f",
                          static_cast<double>(state.days[index].temperature_max));
        } else {
            weather_max_text_[index][0] = '\0';
        }
        lv_label_set_text_static(weather_maxes_[index], weather_max_text_[index]);
        lv_obj_set_style_text_color(weather_maxes_[index],
                                    color(state.stale ? kAmber : kText), 0);
    }
    lv_label_set_text_static(weather_range_, weather_range_text_);
    const float span = std::max(1.0F, week_max - week_min);

    for (unsigned index = 0; index < weather_days_.size(); ++index) {
        if (index < forecast_days) {
            const auto& day = state.days[index];
            const std::string_view date = day.date;
            const std::string_view day_number = date.size() >= 10U ? date.substr(8U, 2U) : date;
            std::snprintf(weather_day_text_[index], sizeof(weather_day_text_[index]), "%.*s",
                          static_cast<int>(day_number.size()), day_number.data());

            const float top_ratio = (week_max - day.temperature_max) / span;
            const float height_ratio = (day.temperature_max - day.temperature_min) / span;
            const int height = std::max(
                4, static_cast<int>(height_ratio * static_cast<float>(kWeatherChartHeight)));
            const int top =
                std::min(kWeatherChartHeight - height,
                         static_cast<int>(top_ratio * static_cast<float>(kWeatherChartHeight)));
            lv_obj_set_size(weather_bars_[index], kWeatherBarWidth, height);
            lv_obj_set_pos(weather_bars_[index], static_cast<int>(index) * kWeatherColumnPitch +
                                                     kWeatherBarInset,
                           kWeatherChartTop + std::max(0, top));
            const bool rainy =
                day.precipitation_probability && *day.precipitation_probability >= 50U;
            lv_obj_set_style_bg_color(
                weather_bars_[index],
                color(state.stale ? kAmber : (rainy ? kText : kCieloInk)), 0);
            lv_obj_clear_flag(weather_bars_[index], LV_OBJ_FLAG_HIDDEN);
        } else {
            std::snprintf(weather_day_text_[index], sizeof(weather_day_text_[index]), "--");
            lv_obj_add_flag(weather_bars_[index], LV_OBJ_FLAG_HIDDEN);
        }
        lv_label_set_text_static(weather_days_[index], weather_day_text_[index]);
        lv_obj_set_style_text_color(weather_days_[index],
                                    color(state.stale ? kAmber : kCieloInk), 0);
    }
}

void LvglPanelView::render_agenda(const domain::AgendaState& state) {
    char age[24]{};
    format_age(age, sizeof(age), state.age_seconds);
    const std::uint32_t state_color = !state.available ? kRed : (state.stale ? kAmber : kText);

    if (!state.available) {
        std::snprintf(agenda_state_text_, sizeof(agenda_state_text_), "Calendar no disponible");
        std::snprintf(agenda_meta_text_, sizeof(agenda_meta_text_), "%s",
                      calendar_error(state.error_code));
        std::snprintf(sleeping_agenda_part_, sizeof(sleeping_agenda_part_),
                      "agenda no disponible");
    } else if (state.events.empty()) {
        std::snprintf(agenda_state_text_, sizeof(agenda_state_text_), "Sin eventos proximos");
        std::snprintf(agenda_meta_text_, sizeof(agenda_meta_text_), "%s hace %s - %s",
                      state.stale ? "CACHE" : "Actualizado", age,
                      state.write_enabled ? "edicion via Wyss" : "solo lectura");
        std::snprintf(sleeping_agenda_part_, sizeof(sleeping_agenda_part_),
                      "sin eventos proximos");
    } else {
        const auto title = ascii_safe(state.events.front().title);
        std::snprintf(agenda_state_text_, sizeof(agenda_state_text_), "Proximo: %s",
                      title.c_str());
        std::snprintf(agenda_meta_text_, sizeof(agenda_meta_text_), "%s hace %s - %s",
                      state.stale ? "CACHE" : "Actualizado", age,
                      state.write_enabled ? "edicion via Wyss" : "solo lectura");
        std::snprintf(sleeping_agenda_part_, sizeof(sleeping_agenda_part_), "proximo: %s",
                      title.c_str());
    }
    lv_label_set_text_static(agenda_state_, agenda_state_text_);
    lv_obj_set_style_text_color(agenda_state_, color(state_color), 0);
    lv_label_set_text_static(agenda_meta_, agenda_meta_text_);
    lv_obj_set_style_text_color(agenda_meta_, color(state.stale ? kAmber : kMuted), 0);

    for (unsigned index = 0; index < agenda_events_.size(); ++index) {
        if (state.available && index < state.events.size()) {
            const auto& event = state.events[index];
            const auto title = ascii_safe(event.title);
            const std::string_view start = event.start;
            const std::string_view day = start.size() >= 10U ? start.substr(8U, 2U) : start;
            const std::string_view month = start.size() >= 7U ? start.substr(5U, 2U) : "--";
            if (event.all_day) {
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
            }
        } else {
            std::snprintf(agenda_event_text_[index], sizeof(agenda_event_text_[index]), "--");
        }
        lv_label_set_text_static(agenda_events_[index], agenda_event_text_[index]);
        lv_obj_set_style_text_color(agenda_events_[index],
                                    color(state.stale ? kAmber : kMuted), 0);
    }
    // Tile "Proximo en agenda" del Inicio: hora + titulo por evento.
    for (unsigned index = 0; index < inicio_agenda_.size(); ++index) {
        if (state.available && index < state.events.size()) {
            const auto& event = state.events[index];
            const auto title = ascii_safe(event.title);
            const std::string_view start = event.start;
            const std::string_view time =
                event.all_day ? std::string_view{"Todo el dia"}
                              : (start.size() >= 16U ? start.substr(11U, 5U)
                                                     : std::string_view{"--:--"});
            std::snprintf(inicio_agenda_text_[index], sizeof(inicio_agenda_text_[index]),
                          "%.*s  %s", static_cast<int>(time.size()), time.data(), title.c_str());
            lv_label_set_text_static(inicio_agenda_[index], inicio_agenda_text_[index]);
            lv_obj_set_style_text_color(inicio_agenda_[index], color(kText), 0);
        } else if (index == 0) {
            lv_label_set_text(inicio_agenda_[0],
                              state.available ? "Sin eventos proximos" : "Sin sincronizar");
            lv_obj_set_style_text_color(inicio_agenda_[0], color(kMuted), 0);
        } else {
            lv_label_set_text(inicio_agenda_[index], "");
        }
    }
    refresh_sleeping_summary();
    lv_obj_set_style_text_color(
        sleeping_weather_,
        color(!state.available ? kRed : (state.stale ? kAmber : kNightMuted)), 0);
}

void LvglPanelView::render_reminders(const domain::ReminderState& state) {
    const std::uint32_t state_color = !state.available ? kRed : (state.stale ? kAmbarInk : kText);
    if (!state.available) {
        std::snprintf(reminder_state_text_, sizeof(reminder_state_text_),
                      "No disponibles");
        std::snprintf(sleeping_reminder_part_, sizeof(sleeping_reminder_part_),
                      "recordatorios no disponibles");
    } else if (state.items.empty()) {
        std::snprintf(reminder_state_text_, sizeof(reminder_state_text_),
                      "Sin pendientes");
        std::snprintf(sleeping_reminder_part_, sizeof(sleeping_reminder_part_),
                      "sin recordatorios pendientes");
    } else {
        const auto text = ascii_safe(state.items.front().text);
        std::snprintf(reminder_state_text_, sizeof(reminder_state_text_),
                      "%u pendientes\n\nProximo:\n%s",
                      static_cast<unsigned>(state.items.size()), text.c_str());
        std::snprintf(sleeping_reminder_part_, sizeof(sleeping_reminder_part_),
                      "%u recordatorios - %s", static_cast<unsigned>(state.items.size()),
                      text.c_str());
    }
    lv_label_set_text_static(reminder_state_, reminder_state_text_);
    lv_obj_set_style_text_color(reminder_state_, color(state_color), 0);

    // Lista de pendientes en INICIO: texto + hora (HH:MM del due_at ISO).
    for (unsigned index = 0; index < inicio_todo_.size(); ++index) {
        if (state.available && index < state.items.size()) {
            const auto& item = state.items[index];
            const std::string hora =
                item.due_at.size() >= 16 ? item.due_at.substr(11, 5) : "";
            std::string linea = ascii_safe(item.text);
            if (!hora.empty()) linea += "  -  " + hora;
            lv_label_set_text(inicio_todo_[index], linea.c_str());
            lv_obj_set_style_text_color(inicio_todo_[index], color(kText), 0);
        } else if (index == 0 && (!state.available || state.items.empty())) {
            lv_label_set_text(inicio_todo_[0],
                              state.available ? "Sin pendientes" : "Sin sincronizar");
            lv_obj_set_style_text_color(inicio_todo_[0], color(kMuted), 0);
        } else {
            lv_label_set_text(inicio_todo_[index], "");
        }
    }
    refresh_sleeping_summary();
}

void LvglPanelView::render_timers(const domain::TimerState& state) {
    const std::uint32_t state_color = !state.available ? kRed : (state.stale ? kCoralInk : kText);
    if (!state.available) {
        std::snprintf(timer_state_text_, sizeof(timer_state_text_), "No disponibles");
        std::snprintf(sleeping_timer_part_, sizeof(sleeping_timer_part_),
                      "timers no disponibles");
    } else if (state.items.empty()) {
        std::snprintf(timer_state_text_, sizeof(timer_state_text_), "Sin timers activos");
        std::snprintf(sleeping_timer_part_, sizeof(sleeping_timer_part_), "sin timers activos");
    } else {
        const auto label = ascii_safe(state.items.front().label);
        const auto remaining = state.items.front().remaining_seconds;
        std::snprintf(timer_state_text_, sizeof(timer_state_text_),
                      "%u activos\n\n%s\n%02u:%02u",
                      static_cast<unsigned>(state.items.size()), label.c_str(),
                      static_cast<unsigned>(remaining / 60U),
                      static_cast<unsigned>(remaining % 60U));
        std::snprintf(sleeping_timer_part_, sizeof(sleeping_timer_part_), "%s %02u:%02u",
                      label.c_str(), static_cast<unsigned>(remaining / 60U),
                      static_cast<unsigned>(remaining % 60U));
    }
    lv_label_set_text_static(timer_state_, timer_state_text_);
    lv_obj_set_style_text_color(timer_state_, color(state_color), 0);
    refresh_sleeping_summary();
}

void LvglPanelView::refresh_sleeping_summary() {
    std::snprintf(sleeping_summary_text_, sizeof(sleeping_summary_text_),
                  "%s   -   %s   -   %s   -   %s", sleeping_weather_part_,
                  sleeping_agenda_part_, sleeping_reminder_part_, sleeping_timer_part_);
    lv_label_set_text_static(sleeping_weather_, sleeping_summary_text_);
}

void LvglPanelView::refresh_home_controls() {
    unsigned light_count = 0;
    unsigned available_count = 0;
    unsigned on_count = 0;
    for (auto& entity : device_entities_) entity.clear();
    for (unsigned index = 0; index < device_buttons_.size(); ++index) {
        lv_label_set_text(device_labels_[index], "Sin luz");
        lv_obj_add_state(device_buttons_[index], LV_STATE_DISABLED);
        lv_obj_set_style_bg_color(device_buttons_[index], color(kSurface), 0);
        lv_obj_set_style_text_color(device_labels_[index], color(kMuted), 0);
    }
    for (const auto& device : devices_) {
        if (!device.entity_id.starts_with("light.")) continue;
        ++light_count;
        if (device.available) ++available_count;
        if (device.available && device.on) ++on_count;
        const unsigned slot = light_count - 1;
        if (slot >= device_buttons_.size()) continue;
        device_entities_[slot] = device.entity_id;
        const auto name = ascii_safe(device.friendly_name);
        std::snprintf(device_text_[slot], sizeof(device_text_[slot]), "%s\n%s", name.c_str(),
                      device.available ? (device.on ? "Encendida" : "Apagada")
                                       : "No disponible");
        lv_label_set_text_static(device_labels_[slot], device_text_[slot]);
        lv_obj_clear_state(device_buttons_[slot], LV_STATE_DISABLED);
    }

    const auto selected = std::find_if(devices_.begin(), devices_.end(), [&](const auto& device) {
        return device.entity_id == selected_entity_ && device.entity_id.starts_with("light.");
    });
    auto active = selected;
    if (active == devices_.end()) {
        active = std::find_if(devices_.begin(), devices_.end(), [](const auto& device) {
            return device.entity_id.starts_with("light.");
        });
    }
    has_device_ = active != devices_.end();
    if (has_device_) {
        current_ = *active;
        selected_entity_ = current_.entity_id;
    }

    // La tarjeta seleccionada se pinta con la familia ambar, como el control.
    for (unsigned index = 0; index < device_entities_.size(); ++index) {
        if (device_entities_[index] == selected_entity_) {
            lv_obj_set_style_bg_color(device_buttons_[index], color(kAmbarBg), 0);
            lv_obj_set_style_text_color(device_labels_[index], color(kText), 0);
        }
    }

    for (auto& entity : scene_entities_) entity.clear();
    for (unsigned index = 0; index < scene_buttons_.size(); ++index) {
        lv_label_set_text(scene_labels_[index], "Sin escena");
        lv_obj_add_state(scene_buttons_[index], LV_STATE_DISABLED);
    }
    unsigned scene_count = 0;
    for (const auto& device : devices_) {
        if (!device.entity_id.starts_with("scene.") || scene_count >= scene_buttons_.size()) {
            continue;
        }
        scene_entities_[scene_count] = device.entity_id;
        const auto name = ascii_safe(device.friendly_name);
        std::snprintf(scene_text_[scene_count], sizeof(scene_text_[scene_count]), "%s%s",
                      name.c_str(), device.available ? "" : " (no disp.)");
        lv_label_set_text_static(scene_labels_[scene_count], scene_text_[scene_count]);
        if (device.available) lv_obj_clear_state(scene_buttons_[scene_count], LV_STATE_DISABLED);
        ++scene_count;
    }

    std::snprintf(home_text_, sizeof(home_text_),
                  "Hogar: %u de %u luces encendidas - %u disponibles", on_count, light_count,
                  available_count);
    lv_label_set_text_static(home_summary_, home_text_);
    if (!has_device_) {
        lv_label_set_text(selected_name_, "Ninguna luz");
        lv_label_set_text(availability_, "No disponible");
        lv_label_set_text(state_label_, "Sin luces proyectadas");
        lv_obj_add_state(power_, LV_STATE_DISABLED);
        lv_obj_add_state(brightness_, LV_STATE_DISABLED);
        lv_obj_add_state(hue_, LV_STATE_DISABLED);
        for (auto* button : color_buttons_) lv_obj_add_state(button, LV_STATE_DISABLED);
        return;
    }

    const auto selected_name = ascii_safe(current_.friendly_name);
    std::snprintf(selected_text_, sizeof(selected_text_), "%s", selected_name.c_str());
    lv_label_set_text_static(selected_name_, selected_text_);
    lv_label_set_text(availability_, current_.available ? "Disponible" : "No disponible");
    lv_obj_set_style_text_color(availability_, color(current_.available ? kGreen : kRed), 0);
    lv_label_set_text(state_label_, current_.on ? "Encendida" : "Apagada");
    lv_obj_set_style_bg_color(power_, color(current_.on ? kAmbarInk : kSurface), 0);
    lv_obj_set_style_text_color(power_label_, color(current_.on ? kSurface : kAmbarInk), 0);
    if (current_.available) {
        lv_obj_clear_state(power_, LV_STATE_DISABLED);
        lv_obj_clear_state(brightness_, LV_STATE_DISABLED);
        lv_obj_clear_state(hue_, LV_STATE_DISABLED);
        for (auto* button : color_buttons_) lv_obj_clear_state(button, LV_STATE_DISABLED);
    } else {
        lv_obj_add_state(power_, LV_STATE_DISABLED);
        lv_obj_add_state(brightness_, LV_STATE_DISABLED);
        lv_obj_add_state(hue_, LV_STATE_DISABLED);
        for (auto* button : color_buttons_) lv_obj_add_state(button, LV_STATE_DISABLED);
    }
    if (!slider_active_ && lv_slider_get_value(brightness_) != current_.brightness) {
        suppress_slider_ = true;
        lv_slider_set_value(brightness_, current_.brightness, LV_ANIM_OFF);
        suppress_slider_ = false;
    }
    if (!slider_active_) update_brightness_label(current_.brightness);
}

void LvglPanelView::update_brightness_label(std::uint8_t value) {
    std::snprintf(brightness_text_, sizeof(brightness_text_), "%u %%", value);
    lv_label_set_text_static(brightness_label_, brightness_text_);
}

void LvglPanelView::render_execution(const domain::ExecutionUpdate& update) {
    if (update.state != domain::ExecutionState::AwaitingConfirmation) {
        lv_obj_add_flag(modal_, LV_OBJ_FLAG_HIDDEN);
    }
    auto message = ascii_safe(update.message);
    if (update.round_trip_ms > 0) {
        message.append(" - ");
        message.append(std::to_string(update.round_trip_ms));
        message.append(" ms");
    }
    lv_label_set_text(execution_, message.c_str());
    lv_obj_set_style_text_color(
        execution_, color(update.state == domain::ExecutionState::Failed ? kRed : kCoralInk), 0);
    const char* state = "Wyss esta listo";
    if (update.state == domain::ExecutionState::Planning) {
        state = "Wyss esta pensando";
    } else if (update.state == domain::ExecutionState::AwaitingConfirmation) {
        state = "Wyss espera tu confirmacion";
    } else if (update.state == domain::ExecutionState::Executing ||
               update.state == domain::ExecutionState::Optimistic) {
        state = "Wyss esta ejecutando";
    } else if (update.state == domain::ExecutionState::Verified) {
        state = "Accion verificada";
    } else if (update.state == domain::ExecutionState::Failed) {
        state = "La accion fallo";
    }
    lv_label_set_text(conversation_state_, state);
    lv_obj_set_style_text_color(
        conversation_state_, color(update.state == domain::ExecutionState::Failed ? kRed : kText),
        0);
    const bool starts_conversation = update.state == domain::ExecutionState::Planning ||
                                     update.state == domain::ExecutionState::AwaitingConfirmation ||
                                     update.state == domain::ExecutionState::Executing;
    if (mode_ != ui::ShellMode::Sleeping &&
        (mode_ == ui::ShellMode::Conversation || starts_conversation)) {
        set_mode(ui::ShellMode::Conversation);
    }
}

void LvglPanelView::render_plan(const domain::Plan& plan) {
    static char plan_text[620];
    std::size_t offset = static_cast<std::size_t>(std::snprintf(
        plan_text, sizeof(plan_text), "%s\n\nRiesgo %c\n", ascii_safe(plan.summary).c_str(),
        static_cast<char>('A' + static_cast<unsigned>(plan.risk))));
    for (const auto& step : plan.steps) {
        if (offset >= sizeof(plan_text)) break;
        offset +=
            static_cast<std::size_t>(std::snprintf(plan_text + offset, sizeof(plan_text) - offset,
                                                   "- %s\n", ascii_safe(step.description).c_str()));
    }
    lv_label_set_text(modal_body_, plan_text);
    lv_disp_trig_activity(nullptr);
    set_mode(ui::ShellMode::Conversation);
    lv_obj_clear_flag(modal_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(modal_);
}

void LvglPanelView::render_toast(std::string_view message, bool error) {
    lv_label_set_text(toast_, ascii_safe(message).c_str());
    lv_obj_set_style_text_color(toast_, color(error ? kRed : kText), 0);
    lv_obj_clear_flag(toast_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(toast_);
    if (error && mode_ == ui::ShellMode::Sleeping) {
        lv_disp_trig_activity(nullptr);
        set_mode(ui::ShellMode::Manual);
    }
}

void LvglPanelView::on_power(lv_event_t*) {
    if (g_view == nullptr || !g_view->has_device_) return;
    g_view->service_->fast_action(g_view->selected_entity_,
                                  g_view->current_.on ? "turn_off" : "turn_on");
}

void LvglPanelView::on_brightness(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    if (view->suppress_slider_) return;
    view->slider_active_ = true;
    view->update_brightness_label(
        static_cast<std::uint8_t>(lv_slider_get_value(view->brightness_)));
}

void LvglPanelView::on_brightness_release(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->slider_active_ = false;
    view->service_->fast_action(view->selected_entity_, "set_brightness",
                                static_cast<std::uint8_t>(lv_slider_get_value(view->brightness_)));
}

void LvglPanelView::on_device(lv_event_t* event) {
    if (g_view == nullptr) return;
    const auto index = reinterpret_cast<std::uintptr_t>(lv_event_get_user_data(event));
    if (index >= g_view->device_entities_.size() || g_view->device_entities_[index].empty()) return;
    g_view->select_entity(g_view->device_entities_[index]);
}

void LvglPanelView::on_hue_release(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    if (view == nullptr || !view->has_device_ || !view->current_.available) return;
    const auto hue = static_cast<std::uint16_t>(lv_slider_get_value(view->hue_));
    const lv_color32_t rgb{.full = lv_color_to32(lv_color_hsv_to_rgb(hue, 100, 100))};
    const std::uint32_t value = (static_cast<std::uint32_t>(rgb.ch.red) << 16) |
                                (static_cast<std::uint32_t>(rgb.ch.green) << 8) |
                                static_cast<std::uint32_t>(rgb.ch.blue);
    view->service_->fast_action(view->selected_entity_, "set_color", std::nullopt, value);
}

void LvglPanelView::on_color(lv_event_t* event) {
    if (g_view == nullptr || !g_view->has_device_ || !g_view->current_.available) return;
    const auto rgb = static_cast<std::uint32_t>(
        reinterpret_cast<std::uintptr_t>(lv_event_get_user_data(event)));
    g_view->service_->fast_action(g_view->selected_entity_, "set_color", std::nullopt, rgb);
}

void LvglPanelView::on_scene(lv_event_t* event) {
    if (g_view == nullptr) return;
    const auto index = reinterpret_cast<std::uintptr_t>(lv_event_get_user_data(event));
    if (index >= g_view->scene_entities_.size() || g_view->scene_entities_[index].empty()) return;
    g_view->service_->fast_action(g_view->scene_entities_[index], "activate_scene");
}

void LvglPanelView::on_media_previous(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->service_->media_action("previous");
}

void LvglPanelView::on_media_play(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->service_->media_action(view->media_playing_ ? "pause" : "play");
}

void LvglPanelView::on_media_next(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->service_->media_action("next");
}

void LvglPanelView::on_media_favorite(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->service_->media_action("toggle_favorite");
}

void LvglPanelView::on_media_volume(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    if (view->suppress_media_volume_) return;
    view->media_volume_active_ = true;
    std::snprintf(view->media_volume_text_, sizeof(view->media_volume_text_), "%d %%",
                  static_cast<int>(lv_slider_get_value(view->media_volume_)));
    lv_label_set_text_static(view->media_volume_label_, view->media_volume_text_);
}

void LvglPanelView::on_media_volume_release(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->media_volume_active_ = false;
    view->service_->media_action(
        "set_volume", static_cast<std::uint8_t>(lv_slider_get_value(view->media_volume_)));
}

void LvglPanelView::on_tab(lv_event_t* event) {
    if (g_view != nullptr) {
        g_view->show_page(static_cast<ui::ManualPage>(
            reinterpret_cast<std::uintptr_t>(lv_event_get_user_data(event))));
    }
}

void LvglPanelView::on_quick_action(lv_event_t* event) {
    if (g_view != nullptr) {
        const auto action = static_cast<domain::HomeQuickAction>(
            reinterpret_cast<std::uintptr_t>(lv_event_get_user_data(event)));
        g_view->service_->quick_action(action);
    }
}

void LvglPanelView::on_submit(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    const char* text = lv_textarea_get_text(view->composer_);
    if (text != nullptr && text[0] != '\0') {
        view->service_->submit_intent(text);
        lv_textarea_set_text(view->composer_, "");
        lv_obj_add_flag(view->keyboard_, LV_OBJ_FLAG_HIDDEN);
    }
}

void LvglPanelView::on_plan_answer(lv_event_t* event) {
    if (g_view == nullptr) return;
    const bool accepted = reinterpret_cast<std::uintptr_t>(lv_event_get_user_data(event)) != 0;
    g_view->service_->answer_plan(accepted);
    lv_obj_add_flag(g_view->modal_, LV_OBJ_FLAG_HIDDEN);
}

void LvglPanelView::on_text_focus(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    lv_obj_clear_flag(view->keyboard_, LV_OBJ_FLAG_HIDDEN);
}

void LvglPanelView::on_manual(lv_event_t*) {
    if (g_view != nullptr) {
        lv_disp_trig_activity(nullptr);
        g_view->set_mode(ui::ShellMode::Manual);
    }
}

void LvglPanelView::on_conversation_open(lv_event_t*) {
    if (g_view != nullptr) {
        lv_disp_trig_activity(nullptr);
        g_view->set_mode(ui::ShellMode::Conversation);
    }
}

void LvglPanelView::on_conversation_back(lv_event_t*) {
    if (g_view != nullptr) {
        lv_obj_add_flag(g_view->keyboard_, LV_OBJ_FLAG_HIDDEN);
        g_view->set_mode(ui::ShellMode::Manual);
    }
}

}  // namespace wyss::adapters
