#pragma once

#include <lvgl.h>

#include <string>

#include "wyss/application/panel_service.hpp"
#include "wyss/ports/ports.hpp"
#include "wyss/ui/design_tokens.hpp"

namespace wyss::adapters {

class LvglPanelView final : public ports::ViewPort {
   public:
    void begin(application::PanelService& service, std::string primary_entity);
    void set_mode(ui::ShellMode mode);
    void show_page(ui::ManualPage page);

    [[nodiscard]] ui::ShellMode mode() const noexcept { return mode_; }
    [[nodiscard]] ui::ManualPage page() const noexcept { return active_page_; }

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
    static void on_manual(lv_event_t* event);
    static void on_conversation_back(lv_event_t* event);
    static lv_obj_t* label(lv_obj_t* parent, const char* text, const lv_font_t* font,
                           std::uint32_t color);
    static void style_button(lv_obj_t* object, std::uint32_t background);
    void update_brightness_label(std::uint8_t value);

    application::PanelService* service_{nullptr};
    std::string primary_entity_;
    domain::DeviceState current_;
    bool has_device_{false};
    bool slider_active_{false};
    bool suppress_slider_{false};
    ui::ShellMode mode_{ui::ShellMode::Manual};
    ui::ManualPage active_page_{ui::ManualPage::Inicio};

    lv_obj_t* pages_[5]{};
    lv_obj_t* tabs_[5]{};
    lv_obj_t* manual_layer_{nullptr};
    lv_obj_t* sleeping_layer_{nullptr};
    lv_obj_t* conversation_layer_{nullptr};
    lv_obj_t* connection_{nullptr};
    lv_obj_t* sleeping_connection_{nullptr};
    lv_obj_t* system_connection_{nullptr};
    lv_obj_t* power_{nullptr};
    lv_obj_t* power_label_{nullptr};
    lv_obj_t* state_label_{nullptr};
    lv_obj_t* home_summary_{nullptr};
    lv_obj_t* brightness_{nullptr};
    lv_obj_t* brightness_label_{nullptr};
    lv_obj_t* conversation_state_{nullptr};
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
