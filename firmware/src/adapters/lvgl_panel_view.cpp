#include "wyss/adapters/lvgl_panel_view.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>

namespace wyss::adapters {
namespace {
constexpr std::uint32_t kCanvas = 0x07101F;
constexpr std::uint32_t kSurface = 0x111D30;
constexpr std::uint32_t kSurfaceRaised = 0x18263C;
constexpr std::uint32_t kText = 0xF7FAFF;
constexpr std::uint32_t kMuted = 0x8EA2BF;
constexpr std::uint32_t kCyan = 0x2EE6D6;
constexpr std::uint32_t kBlue = 0x4F7CFF;
constexpr std::uint32_t kGreen = 0x45D483;
constexpr std::uint32_t kRed = 0xFF6B7A;
constexpr std::uint32_t kBorder = 0x263A56;

LvglPanelView* g_view = nullptr;

lv_color_t color(std::uint32_t value) { return lv_color_hex(value); }

void flat(lv_obj_t* object) {
    lv_obj_set_style_shadow_width(object, 0, 0);
    lv_obj_set_style_border_width(object, 1, 0);
    lv_obj_set_style_border_color(object, color(kBorder), 0);
    lv_obj_set_style_radius(object, 14, 0);
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
    lv_obj_set_style_bg_color(object, color(kBlue), LV_STATE_PRESSED);
    lv_obj_set_style_border_width(object, 0, 0);
}

void LvglPanelView::begin(application::PanelService& service, std::string primary_entity) {
    service_ = &service;
    primary_entity_ = std::move(primary_entity);
    g_view = this;

    lv_obj_t* screen = lv_scr_act();
    lv_obj_clean(screen);
    lv_obj_set_style_bg_color(screen, color(kCanvas), 0);
    lv_obj_set_style_pad_all(screen, 0, 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* brand = label(screen, "WYSS", &lv_font_montserrat_26, kText);
    lv_obj_set_pos(brand, 24, 17);
    lv_obj_t* subtitle = label(screen, "HOME PANEL", &lv_font_montserrat_12, kCyan);
    lv_obj_set_pos(subtitle, 105, 26);
    connection_ = label(screen, "SIN CONEXIÓN", &lv_font_montserrat_12, kMuted);
    lv_obj_align(connection_, LV_ALIGN_TOP_RIGHT, -24, 24);

    lv_obj_t* divider = lv_obj_create(screen);
    lv_obj_set_size(divider, 800, 1);
    lv_obj_set_pos(divider, 0, 63);
    lv_obj_set_style_bg_color(divider, color(kBorder), 0);
    lv_obj_set_style_border_width(divider, 0, 0);

    constexpr const char* tab_names[] = {"HOGAR", "WYSS"};
    for (unsigned index = 0; index < 2; ++index) {
        tabs_[index] = lv_btn_create(screen);
        lv_obj_set_size(tabs_[index], 92, 54);
        lv_obj_set_pos(tabs_[index], 12, 82 + static_cast<int>(index) * 66);
        style_button(tabs_[index], kCanvas);
        lv_obj_add_event_cb(tabs_[index], on_tab, LV_EVENT_PRESSED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        lv_obj_t* tab_label = label(tabs_[index], tab_names[index], &lv_font_montserrat_12, kMuted);
        lv_obj_center(tab_label);
    }

    pages_[0] = lv_obj_create(screen);
    lv_obj_set_size(pages_[0], 684, 416);
    lv_obj_set_pos(pages_[0], 116, 64);
    lv_obj_set_style_bg_opa(pages_[0], LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(pages_[0], 0, 0);
    lv_obj_set_style_pad_all(pages_[0], 0, 0);
    lv_obj_clear_flag(pages_[0], LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* card = lv_obj_create(pages_[0]);
    lv_obj_set_size(card, 648, 255);
    lv_obj_set_pos(card, 18, 16);
    flat(card);
    lv_obj_set_style_bg_color(card, color(kSurface), 0);
    lv_obj_set_style_pad_all(card, 20, 0);
    lv_obj_clear_flag(card, LV_OBJ_FLAG_SCROLLABLE);

    label(card, "LUZ PRINCIPAL", &lv_font_montserrat_12, kCyan);
    state_label_ = label(card, "Esperando estado…", &lv_font_montserrat_20, kText);
    lv_obj_set_pos(state_label_, 0, 34);
    lv_obj_t* response = label(card, "Respuesta local optimista", &lv_font_montserrat_12, kMuted);
    lv_obj_set_pos(response, 0, 70);

    power_ = lv_btn_create(card);
    lv_obj_set_size(power_, 150, 112);
    lv_obj_set_pos(power_, 0, 105);
    style_button(power_, kSurfaceRaised);
    lv_obj_add_event_cb(power_, on_power, LV_EVENT_PRESSED, this);
    power_label_ = label(power_, "ENCENDER", &lv_font_montserrat_16, kText);
    lv_obj_center(power_label_);

    lv_obj_t* brightness_title = label(card, "BRILLO", &lv_font_montserrat_12, kMuted);
    lv_obj_set_pos(brightness_title, 190, 110);
    brightness_label_ = label(card, "0 %", &lv_font_montserrat_20, kText);
    lv_obj_set_pos(brightness_label_, 530, 103);
    brightness_ = lv_slider_create(card);
    lv_obj_set_size(brightness_, 380, 48);
    lv_obj_set_pos(brightness_, 190, 150);
    lv_slider_set_range(brightness_, 0, 100);
    lv_obj_set_style_bg_color(brightness_, color(kBorder), LV_PART_MAIN);
    lv_obj_set_style_bg_color(brightness_, color(kCyan), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(brightness_, color(kText), LV_PART_KNOB);
    lv_obj_set_style_pad_all(brightness_, 8, LV_PART_KNOB);
    lv_obj_add_event_cb(brightness_, on_brightness, LV_EVENT_VALUE_CHANGED, this);
    lv_obj_add_event_cb(brightness_, on_brightness_release, LV_EVENT_RELEASED, this);
    lv_obj_add_event_cb(brightness_, on_brightness_release, LV_EVENT_PRESS_LOST, this);

    lv_obj_t* quick_title = label(pages_[0], "ACCIONES RÁPIDAS", &lv_font_montserrat_12, kMuted);
    lv_obj_set_pos(quick_title, 18, 292);
    constexpr const char* quick_labels[] = {"Modo noche", "Apagar todo", "Estoy saliendo"};
    constexpr const char* quick_intents[] = {
        "Activá el modo noche en casa", "Apagá todas las luces de la casa",
        "Prepará la casa porque estoy saliendo"};
    for (unsigned index = 0; index < 3; ++index) {
        lv_obj_t* button = lv_btn_create(pages_[0]);
        lv_obj_set_size(button, 198, 66);
        lv_obj_set_pos(button, 18 + static_cast<int>(index) * 216, 324);
        style_button(button, kSurface);
        lv_obj_add_event_cb(button, on_quick_intent, LV_EVENT_PRESSED,
                            const_cast<char*>(quick_intents[index]));
        lv_obj_t* button_label = label(button, quick_labels[index], &lv_font_montserrat_14, kText);
        lv_obj_center(button_label);
    }

    pages_[1] = lv_obj_create(screen);
    lv_obj_set_size(pages_[1], 684, 416);
    lv_obj_set_pos(pages_[1], 116, 64);
    lv_obj_set_style_bg_opa(pages_[1], LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(pages_[1], 0, 0);
    lv_obj_set_style_pad_all(pages_[1], 18, 0);
    lv_obj_clear_flag(pages_[1], LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(pages_[1], LV_OBJ_FLAG_HIDDEN);
    label(pages_[1], "¿Qué querés que haga?", &lv_font_montserrat_20, kText);
    lv_obj_t* hint = label(pages_[1], "Yo preparo un plan y te pido permiso cuando corresponde.",
                           &lv_font_montserrat_12, kMuted);
    lv_obj_set_pos(hint, 0, 38);
    composer_ = lv_textarea_create(pages_[1]);
    lv_obj_set_size(composer_, 510, 76);
    lv_obj_set_pos(composer_, 0, 78);
    lv_textarea_set_placeholder_text(composer_, "Ej.: dejá el living listo para ver una película");
    lv_textarea_set_one_line(composer_, true);
    lv_obj_set_style_bg_color(composer_, color(kSurface), 0);
    lv_obj_set_style_text_color(composer_, color(kText), 0);
    lv_obj_set_style_text_font(composer_, &lv_font_montserrat_14, 0);
    flat(composer_);
    lv_obj_add_event_cb(composer_, on_text_focus, LV_EVENT_FOCUSED, this);
    lv_obj_t* submit = lv_btn_create(pages_[1]);
    lv_obj_set_size(submit, 118, 76);
    lv_obj_set_pos(submit, 526, 78);
    style_button(submit, kBlue);
    lv_obj_add_event_cb(submit, on_submit, LV_EVENT_PRESSED, this);
    lv_obj_t* submit_label = label(submit, "ENVIAR", &lv_font_montserrat_14, kText);
    lv_obj_center(submit_label);
    execution_ = label(pages_[1], "Listo para orquestar.", &lv_font_montserrat_14, kMuted);
    lv_obj_set_pos(execution_, 0, 174);
    keyboard_ = lv_keyboard_create(pages_[1]);
    lv_obj_set_size(keyboard_, 644, 202);
    lv_obj_set_pos(keyboard_, 0, 214);
    lv_keyboard_set_textarea(keyboard_, composer_);
    lv_obj_set_style_bg_color(keyboard_, color(kSurface), 0);
    lv_obj_set_style_text_font(keyboard_, &lv_font_montserrat_12, 0);
    lv_obj_add_flag(keyboard_, LV_OBJ_FLAG_HIDDEN);

    modal_ = lv_obj_create(screen);
    lv_obj_set_size(modal_, 560, 330);
    lv_obj_align(modal_, LV_ALIGN_CENTER, 0, 10);
    lv_obj_set_style_bg_color(modal_, color(kSurfaceRaised), 0);
    lv_obj_set_style_pad_all(modal_, 24, 0);
    flat(modal_);
    lv_obj_add_flag(modal_, LV_OBJ_FLAG_HIDDEN);
    modal_title_ = label(modal_, "PLAN DE WYSS", &lv_font_montserrat_20, kText);
    modal_body_ = label(modal_, "", &lv_font_montserrat_14, kMuted);
    lv_obj_set_width(modal_body_, 510);
    lv_label_set_long_mode(modal_body_, LV_LABEL_LONG_WRAP);
    lv_obj_set_pos(modal_body_, 0, 52);
    constexpr const char* answers[] = {"CANCELAR", "CONFIRMAR"};
    for (unsigned index = 0; index < 2; ++index) {
        lv_obj_t* answer = lv_btn_create(modal_);
        lv_obj_set_size(answer, 180, 58);
        lv_obj_set_pos(answer, 80 + static_cast<int>(index) * 210, 236);
        style_button(answer, index == 0 ? kSurface : kBlue);
        lv_obj_add_event_cb(answer, on_plan_answer, LV_EVENT_PRESSED,
                            reinterpret_cast<void*>(static_cast<std::uintptr_t>(index)));
        lv_obj_t* answer_label = label(answer, answers[index], &lv_font_montserrat_14, kText);
        lv_obj_center(answer_label);
    }

    toast_ = label(screen, "", &lv_font_montserrat_12, kText);
    lv_obj_set_style_bg_color(toast_, color(kSurfaceRaised), 0);
    lv_obj_set_style_bg_opa(toast_, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_hor(toast_, 16, 0);
    lv_obj_set_style_pad_ver(toast_, 10, 0);
    lv_obj_align(toast_, LV_ALIGN_BOTTOM_MID, 0, -14);
    lv_obj_add_flag(toast_, LV_OBJ_FLAG_HIDDEN);
    show_page(0);
}

void LvglPanelView::show_page(unsigned page) {
    active_page_ = page < 2 ? page : 0;
    for (unsigned index = 0; index < 2; ++index) {
        if (index == active_page_) {
            lv_obj_clear_flag(pages_[index], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_color(tabs_[index], color(kSurfaceRaised), 0);
            lv_obj_set_style_text_color(lv_obj_get_child(tabs_[index], 0), color(kCyan), 0);
        } else {
            lv_obj_add_flag(pages_[index], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_color(tabs_[index], color(kCanvas), 0);
            lv_obj_set_style_text_color(lv_obj_get_child(tabs_[index], 0), color(kMuted), 0);
        }
    }
}

void LvglPanelView::render_connection(domain::ConnectionState state) {
    const char* text = "SIN CONEXIÓN";
    std::uint32_t text_color = kRed;
    if (state == domain::ConnectionState::Online) {
        text = "WYSS EN LÍNEA";
        text_color = kGreen;
    } else if (state == domain::ConnectionState::Discovering) {
        text = "CONECTANDO…";
        text_color = kCyan;
    } else if (state == domain::ConnectionState::Degraded) {
        text = "CONEXIÓN DEGRADADA";
    }
    lv_label_set_text(connection_, text);
    lv_obj_set_style_text_color(connection_, color(text_color), 0);
}

void LvglPanelView::render_devices(std::span<const domain::DeviceState> devices) {
    const auto found = std::find_if(devices.begin(), devices.end(), [&](const auto& device) {
        return device.entity_id == primary_entity_;
    });
    if (found == devices.end()) {
        return;
    }
    current_ = *found;
    has_device_ = true;
    lv_label_set_text(state_label_, current_.on ? "Encendida" : "Apagada");
    lv_label_set_text(power_label_, current_.on ? "APAGAR" : "ENCENDER");
    lv_obj_set_style_bg_color(power_, color(current_.on ? kCyan : kSurfaceRaised), 0);
    lv_obj_set_style_text_color(power_label_, color(current_.on ? kCanvas : kText), 0);
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
    std::snprintf(execution_text_, sizeof(execution_text_), "%s%s%lu ms",
                  update.message.c_str(), update.round_trip_ms > 0 ? " · " : "",
                  static_cast<unsigned long>(update.round_trip_ms));
    if (update.round_trip_ms == 0) {
        std::snprintf(execution_text_, sizeof(execution_text_), "%s", update.message.c_str());
    }
    lv_label_set_text_static(execution_, execution_text_);
    lv_obj_set_style_text_color(
        execution_, color(update.state == domain::ExecutionState::Failed ? kRed : kCyan), 0);
}

void LvglPanelView::render_plan(const domain::Plan& plan) {
    static char plan_text[620];
    std::size_t offset = static_cast<std::size_t>(std::snprintf(
        plan_text, sizeof(plan_text), "%s\n\nRIESGO %c\n", plan.summary.c_str(),
        static_cast<char>('A' + static_cast<unsigned>(plan.risk))));
    for (const auto& step : plan.steps) {
        if (offset >= sizeof(plan_text)) break;
        offset += static_cast<std::size_t>(std::snprintf(
            plan_text + offset, sizeof(plan_text) - offset, "• %s\n", step.description.c_str()));
    }
    lv_label_set_text(modal_body_, plan_text);
    lv_obj_clear_flag(modal_, LV_OBJ_FLAG_HIDDEN);
}

void LvglPanelView::render_toast(std::string_view message, bool error) {
    lv_label_set_text(toast_, std::string(message).c_str());
    lv_obj_set_style_text_color(toast_, color(error ? kRed : kText), 0);
    lv_obj_clear_flag(toast_, LV_OBJ_FLAG_HIDDEN);
}

void LvglPanelView::on_power(lv_event_t*) {
    if (g_view == nullptr || !g_view->has_device_) return;
    g_view->service_->fast_action(g_view->primary_entity_, g_view->current_.on ? "turn_off" : "turn_on");
}

void LvglPanelView::on_brightness(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    if (view->suppress_slider_) return;
    view->slider_active_ = true;
    view->update_brightness_label(static_cast<std::uint8_t>(lv_slider_get_value(view->brightness_)));
}

void LvglPanelView::on_brightness_release(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    view->slider_active_ = false;
    view->service_->fast_action(view->primary_entity_, "set_brightness",
                                static_cast<std::uint8_t>(lv_slider_get_value(view->brightness_)));
}

void LvglPanelView::on_tab(lv_event_t* event) {
    if (g_view != nullptr) {
        g_view->show_page(static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(
            lv_event_get_user_data(event))));
    }
}

void LvglPanelView::on_quick_intent(lv_event_t* event) {
    if (g_view != nullptr) {
        g_view->service_->submit_intent(static_cast<const char*>(lv_event_get_user_data(event)));
        g_view->show_page(1);
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

}  // namespace wyss::adapters
