#pragma once

#include <lvgl.h>

#include <string>

#include "wyss/application/panel_service.hpp"
#include "wyss/ports/ports.hpp"

namespace wyss::adapters {

class LvglPanelView final : public ports::ViewPort {
   public:
    void begin(application::PanelService& service, std::string primary_entity);

    void render_connection(domain::ConnectionState state) override;
    void render_devices(std::span<const domain::DeviceState> devices) override;
    void render_execution(const domain::ExecutionUpdate& update) override;
    void render_plan(const domain::Plan& plan) override;
    void render_toast(std::string_view message, bool error) override;

   private:
    static void on_power(lv_event_t* event);
    static void on_brightness(lv_event_t* event);
    static void on_brightness_release(lv_event_t* event);
    static void on_tab(lv_event_t* event);
    static void on_quick_intent(lv_event_t* event);
    static void on_submit(lv_event_t* event);
    static void on_plan_answer(lv_event_t* event);
    static void on_text_focus(lv_event_t* event);
    static lv_obj_t* label(lv_obj_t* parent, const char* text, const lv_font_t* font,
                           std::uint32_t color);
    static void style_button(lv_obj_t* object, std::uint32_t background);
    void show_page(unsigned page);
    void update_brightness_label(std::uint8_t value);

    application::PanelService* service_{nullptr};
    std::string primary_entity_;
    domain::DeviceState current_;
    bool has_device_{false};
    bool slider_active_{false};
    bool suppress_slider_{false};
    unsigned active_page_{0};

    lv_obj_t* pages_[2]{};
    lv_obj_t* tabs_[2]{};
    lv_obj_t* connection_{nullptr};
    lv_obj_t* clock_{nullptr};
    lv_obj_t* power_{nullptr};
    lv_obj_t* power_label_{nullptr};
    lv_obj_t* state_label_{nullptr};
    lv_obj_t* brightness_{nullptr};
    lv_obj_t* brightness_label_{nullptr};
    lv_obj_t* execution_{nullptr};
    lv_obj_t* composer_{nullptr};
    lv_obj_t* keyboard_{nullptr};
    lv_obj_t* modal_{nullptr};
    lv_obj_t* modal_title_{nullptr};
    lv_obj_t* modal_body_{nullptr};
    lv_obj_t* toast_{nullptr};
    char brightness_text_[12]{};
    char execution_text_[96]{};
};

}  // namespace wyss::adapters
