#pragma once

#include <lvgl.h>

#include <array>
#include <string>
#include <string_view>
#include <vector>

#include "wyss/application/panel_service.hpp"
#include "wyss/ports/ports.hpp"
#include "wyss/ui/design_tokens.hpp"

namespace wyss::adapters {

class LvglPanelView final : public ports::ViewPort {
   public:
    void begin(application::PanelService& service, std::string primary_entity);
    void set_mode(ui::ShellMode mode);
    void show_page(ui::ManualPage page);
    bool select_entity(std::string_view entity_id);

    [[nodiscard]] ui::ShellMode mode() const noexcept { return mode_; }
    [[nodiscard]] ui::ManualPage page() const noexcept { return active_page_; }
    [[nodiscard]] const std::string& selected_entity() const noexcept { return selected_entity_; }

    void render_connection(domain::ConnectionState state) override;
    void render_devices(std::span<const domain::DeviceState> devices) override;
    void render_media(const domain::MediaState& state) override;
    void render_weather(const domain::WeatherState& state) override;
    void render_agenda(const domain::AgendaState& state) override;
    void render_reminders(const domain::ReminderState& state) override;
    void render_timers(const domain::TimerState& state) override;
    void render_execution(const domain::ExecutionUpdate& update) override;
    void render_plan(const domain::Plan& plan) override;
    void render_toast(std::string_view message, bool error) override;

   private:
    static void on_power(lv_event_t* event);
    static void on_brightness(lv_event_t* event);
    static void on_brightness_release(lv_event_t* event);
    static void on_device(lv_event_t* event);
    static void on_color(lv_event_t* event);
    static void on_scene(lv_event_t* event);
    static void on_media_previous(lv_event_t* event);
    static void on_media_play(lv_event_t* event);
    static void on_media_next(lv_event_t* event);
    static void on_media_favorite(lv_event_t* event);
    static void on_media_volume(lv_event_t* event);
    static void on_media_volume_release(lv_event_t* event);
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
    void refresh_home_controls();
    void refresh_sleeping_summary();

    application::PanelService* service_{nullptr};
    std::string primary_entity_;
    std::string selected_entity_;
    domain::DeviceState current_;
    std::vector<domain::DeviceState> devices_;
    bool has_device_{false};
    bool slider_active_{false};
    bool suppress_slider_{false};
    bool media_playing_{false};
    bool media_volume_active_{false};
    bool suppress_media_volume_{false};
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
    lv_obj_t* selected_name_{nullptr};
    lv_obj_t* availability_{nullptr};
    lv_obj_t* home_summary_{nullptr};
    lv_obj_t* weather_current_{nullptr};
    lv_obj_t* weather_meta_{nullptr};
    lv_obj_t* sleeping_weather_{nullptr};
    lv_obj_t* agenda_state_{nullptr};
    lv_obj_t* agenda_meta_{nullptr};
    lv_obj_t* reminder_state_{nullptr};
    lv_obj_t* timer_state_{nullptr};
    lv_obj_t* brightness_{nullptr};
    lv_obj_t* brightness_label_{nullptr};
    lv_obj_t* media_title_{nullptr};
    lv_obj_t* media_artist_{nullptr};
    lv_obj_t* media_device_{nullptr};
    lv_obj_t* media_progress_{nullptr};
    lv_obj_t* media_progress_label_{nullptr};
    lv_obj_t* media_play_label_{nullptr};
    lv_obj_t* media_favorite_label_{nullptr};
    lv_obj_t* media_volume_{nullptr};
    lv_obj_t* media_volume_label_{nullptr};
    std::array<lv_obj_t*, 3> device_buttons_{};
    std::array<lv_obj_t*, 3> device_labels_{};
    std::array<lv_obj_t*, 3> scene_buttons_{};
    std::array<lv_obj_t*, 3> scene_labels_{};
    std::array<lv_obj_t*, 4> color_buttons_{};
    std::array<lv_obj_t*, 4> media_buttons_{};
    std::array<lv_obj_t*, 7> weather_days_{};
    std::array<lv_obj_t*, 4> agenda_events_{};
    std::array<std::string, 3> device_entities_{};
    std::array<std::string, 3> scene_entities_{};
    lv_obj_t* conversation_state_{nullptr};
    lv_obj_t* execution_{nullptr};
    lv_obj_t* composer_{nullptr};
    lv_obj_t* keyboard_{nullptr};
    lv_obj_t* modal_{nullptr};
    lv_obj_t* modal_title_{nullptr};
    lv_obj_t* modal_body_{nullptr};
    lv_obj_t* toast_{nullptr};
    char brightness_text_[12]{};
    char media_title_text_[192]{};
    char media_artist_text_[192]{};
    char media_device_text_[192]{};
    char media_progress_text_[24]{};
    char media_volume_text_[16]{};
    char execution_text_[96]{};
    char selected_text_[64]{};
    char home_text_[64]{};
    char weather_current_text_[128]{};
    char weather_meta_text_[128]{};
    char sleeping_weather_part_[128]{"Clima sin sincronizar"};
    char sleeping_agenda_part_[128]{"Agenda sin sincronizar"};
    char sleeping_reminder_part_[128]{"Recordatorios sin sincronizar"};
    char sleeping_timer_part_[128]{"Timers sin sincronizar"};
    char sleeping_summary_text_[536]{};
    char weather_day_text_[7][48]{};
    char agenda_state_text_[192]{};
    char agenda_meta_text_[160]{};
    char agenda_event_text_[4][224]{};
    char reminder_state_text_[224]{};
    char timer_state_text_[224]{};
    char device_text_[3][64]{};
    char scene_text_[3][40]{};
};

}  // namespace wyss::adapters
