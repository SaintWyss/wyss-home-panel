from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: se esperaba una coincidencia y hubo {count}")
    return text.replace(old, new, 1)


def patch(path: str, replacements: list[tuple[str, str, str]]) -> None:
    text = read(path)
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
    write(path, text)


# Dominio y puertos.
patch(
    "firmware/include/wyss/domain/types.hpp",
    [
        (
            "enum class HomeQuickAction : std::uint8_t { NightMode = 0, AllOff = 1, Leaving = 2 };\n",
            """enum class HomeQuickAction : std::uint8_t { NightMode = 0, AllOff = 1, Leaving = 2 };\n\nstruct LocalDateTime {\n    bool valid{false};\n    std::uint32_t day_key{0};\n    std::uint16_t minute_of_day{0};\n};\n\nstruct DoorCheckState {\n    bool closed{false};\n    std::uint32_t confirmed_day{0};\n    std::uint16_t confirmed_minute{0};\n};\n""",
            "tipos del check de puerta",
        )
    ],
)

patch(
    "firmware/include/wyss/ports/ports.hpp",
    [
        (
            "class CommandPort {\n",
            """class LocalTimePort {\n   public:\n    virtual ~LocalTimePort() = default;\n    [[nodiscard]] virtual domain::LocalDateTime now_local() const noexcept = 0;\n};\n\nclass DoorCheckStorePort {\n   public:\n    virtual ~DoorCheckStorePort() = default;\n    [[nodiscard]] virtual domain::DoorCheckState load_door_check() = 0;\n    virtual bool save_door_check(const domain::DoorCheckState& state) = 0;\n};\n\nclass CommandPort {\n""",
            "puertos de hora y persistencia",
        ),
        (
            "    virtual void render_timers(const domain::TimerState& state) = 0;\n",
            """    virtual void render_timers(const domain::TimerState& state) = 0;\n    virtual void render_door_check(const domain::DoorCheckState& state) = 0;\n""",
            "proyeccion de puerta",
        ),
    ],
)

# Servicio de aplicación.
patch(
    "firmware/include/wyss/application/panel_service.hpp",
    [
        (
            "    void receive_timers(domain::TimerState state);\n",
            """    void receive_timers(domain::TimerState state);\n    void configure_door_check(ports::LocalTimePort& local_time,\n                              ports::DoorCheckStorePort& store);\n    void toggle_door_check();\n""",
            "API del check manual",
        ),
        (
            "    void rollback_expired();\n",
            """    void rollback_expired();\n    void refresh_door_check();\n""",
            "refresh privado de puerta",
        ),
        (
            "    std::optional<domain::Plan> pending_plan_;\n",
            """    std::optional<domain::Plan> pending_plan_;\n    ports::LocalTimePort* local_time_{nullptr};\n    ports::DoorCheckStorePort* door_check_store_{nullptr};\n    domain::DoorCheckState door_check_;\n    std::uint64_t next_door_check_refresh_ms_{0};\n""",
            "estado del check manual",
        ),
    ],
)

patch(
    "firmware/src/application/panel_service.cpp",
    [
        (
            "void PanelService::receive_timers(domain::TimerState state) {\n    view_.render_timers(state);\n}\n\n",
            """void PanelService::receive_timers(domain::TimerState state) {\n    view_.render_timers(state);\n}\n\nvoid PanelService::configure_door_check(ports::LocalTimePort& local_time,\n                                        ports::DoorCheckStorePort& store) {\n    local_time_ = &local_time;\n    door_check_store_ = &store;\n    door_check_ = store.load_door_check();\n    next_door_check_refresh_ms_ = 0;\n    refresh_door_check();\n}\n\nvoid PanelService::toggle_door_check() {\n    if (local_time_ == nullptr || door_check_store_ == nullptr) {\n        view_.render_toast("El check de puerta no esta disponible", true);\n        return;\n    }\n\n    const auto before = door_check_;\n    const auto now = local_time_->now_local();\n    door_check_.closed = !door_check_.closed;\n    if (door_check_.closed) {\n        door_check_.confirmed_day = now.valid ? now.day_key : 0U;\n        door_check_.confirmed_minute = now.valid ? now.minute_of_day : 0U;\n    } else {\n        door_check_.confirmed_day = 0U;\n        door_check_.confirmed_minute = 0U;\n    }\n\n    if (!door_check_store_->save_door_check(door_check_)) {\n        door_check_ = before;\n        view_.render_toast("No pude guardar el check de la puerta", true);\n        view_.render_door_check(door_check_);\n        return;\n    }\n    view_.render_door_check(door_check_);\n    view_.render_toast(door_check_.closed ? "Puerta marcada como cerrada"\n                                         : "Check de puerta pendiente",\n                       false);\n}\n\n",
            "implementacion del check manual",
        ),
        (
            "void PanelService::tick() {\n    rollback_expired();\n    dispatch_quick_action();\n}\n",
            """void PanelService::tick() {\n    rollback_expired();\n    dispatch_quick_action();\n    if (local_time_ != nullptr && door_check_store_ != nullptr &&\n        clock_.now_ms() >= next_door_check_refresh_ms_) {\n        refresh_door_check();\n        next_door_check_refresh_ms_ = clock_.now_ms() + 1'000U;\n    }\n}\n""",
            "tick diario de puerta",
        ),
        (
            "void PanelService::rollback(std::string_view entity_id, std::string_view message) {\n",
            """void PanelService::refresh_door_check() {\n    if (local_time_ == nullptr || door_check_store_ == nullptr) return;\n\n    const auto now = local_time_->now_local();\n    if (!now.valid || !door_check_.closed) {\n        view_.render_door_check(door_check_);\n        return;\n    }\n\n    const auto before = door_check_;\n    if (door_check_.confirmed_day == 0U) {\n        // El usuario confirmo antes de que NTP estuviera listo: adoptar el dia real sin perderlo.\n        door_check_.confirmed_day = now.day_key;\n        door_check_.confirmed_minute = now.minute_of_day;\n    } else if (door_check_.confirmed_day != now.day_key) {\n        // El check es deliberadamente diario; nunca arrastrar una confirmacion de ayer.\n        door_check_ = {};\n    }\n\n    if (door_check_.closed != before.closed ||\n        door_check_.confirmed_day != before.confirmed_day ||\n        door_check_.confirmed_minute != before.confirmed_minute) {\n        if (!door_check_store_->save_door_check(door_check_)) {\n            door_check_ = before;\n            view_.render_toast("No pude actualizar el check diario", true);\n        }\n    }\n    view_.render_door_check(door_check_);\n}\n\nvoid PanelService::rollback(std::string_view entity_id, std::string_view message) {\n""",
            "refresh persistente de puerta",
        ),
    ],
)

# Adaptadores ESP32: reloj local NTP y NVS independiente de las credenciales.
write(
    "firmware/include/wyss/adapters/arduino_local_time.hpp",
    r'''#pragma once

#include <ctime>

#include "wyss/ports/ports.hpp"

namespace wyss::adapters {

class ArduinoLocalTime final : public ports::LocalTimePort {
   public:
    [[nodiscard]] domain::LocalDateTime now_local() const noexcept override {
        const std::time_t now = std::time(nullptr);
        if (now < 1'700'000'000) return {};

        std::tm local{};
        if (localtime_r(&now, &local) == nullptr) return {};
        return {true,
                static_cast<std::uint32_t>((local.tm_year + 1900) * 10'000 +
                                           (local.tm_mon + 1) * 100 + local.tm_mday),
                static_cast<std::uint16_t>(local.tm_hour * 60 + local.tm_min)};
    }
};

}  // namespace wyss::adapters
''',
)

write(
    "firmware/include/wyss/adapters/nvs_door_check_store.hpp",
    r'''#pragma once

#include <Preferences.h>

#include "wyss/ports/ports.hpp"

namespace wyss::adapters {

class NvsDoorCheckStore final : public ports::DoorCheckStorePort {
   public:
    [[nodiscard]] domain::DoorCheckState load_door_check() override {
        Preferences preferences;
        if (!preferences.begin("wyss-door", true)) return {};
        const domain::DoorCheckState state{
            preferences.getBool("closed", false),
            preferences.getUInt("day", 0U),
            static_cast<std::uint16_t>(preferences.getUInt("minute", 0U))};
        preferences.end();
        return state;
    }

    bool save_door_check(const domain::DoorCheckState& state) override {
        Preferences preferences;
        if (!preferences.begin("wyss-door", false)) return false;
        const bool saved = preferences.putBool("closed", state.closed) == 1U &&
                           preferences.putUInt("day", state.confirmed_day) == sizeof(std::uint32_t) &&
                           preferences.putUInt("minute", state.confirmed_minute) == sizeof(std::uint32_t);
        preferences.end();
        return saved;
    }
};

}  // namespace wyss::adapters
''',
)

# Wiring del firmware y NTP Argentina.
patch(
    "firmware/src/main.cpp",
    [
        (
            "#include <memory>\n",
            "#include <memory>\n#include <time.h>\n",
            "include de hora NTP",
        ),
        (
            '#include "wyss/adapters/arduino_clock.hpp"\n',
            '#include "wyss/adapters/arduino_clock.hpp"\n#include "wyss/adapters/arduino_local_time.hpp"\n',
            "adapter de hora local",
        ),
        (
            '#include "wyss/adapters/nvs_config_store.hpp"\n',
            '#include "wyss/adapters/nvs_config_store.hpp"\n#include "wyss/adapters/nvs_door_check_store.hpp"\n',
            "adapter de puerta NVS",
        ),
        (
            "wyss::adapters::ArduinoClock clock_port;\nwyss::adapters::NvsConfigStore config;\n",
            """wyss::adapters::ArduinoClock clock_port;\nwyss::adapters::ArduinoLocalTime local_time_port;\nwyss::adapters::NvsDoorCheckStore door_check_store;\nwyss::adapters::NvsConfigStore config;\n""",
            "instancias del check",
        ),
        (
            "    view.begin(*service, configured ? std::string(config.primary_entity()) : \"light.unconfigured\");\n",
            """    view.begin(*service, configured ? std::string(config.primary_entity()) : "light.unconfigured");\n    service->configure_door_check(local_time_port, door_check_store);\n""",
            "configuracion de puerta",
        ),
        (
            "    if (configured) {\n        start_network();\n    }\n",
            """    if (configured) {\n        start_network();\n        // Argentina no usa horario de verano: ART3 mantiene el check diario en hora local.\n        configTzTime("ART3", "pool.ntp.org", "time.google.com");\n    }\n""",
            "sincronizacion NTP",
        ),
    ],
)

# Vista LVGL.
patch(
    "firmware/include/wyss/adapters/lvgl_panel_view.hpp",
    [
        (
            "    void render_timers(const domain::TimerState& state) override;\n",
            """    void render_timers(const domain::TimerState& state) override;\n    void render_door_check(const domain::DoorCheckState& state) override;\n""",
            "render de puerta",
        ),
        (
            "    static void on_resync(lv_event_t* event);\n",
            """    static void on_resync(lv_event_t* event);\n    static void on_door_check(lv_event_t* event);\n""",
            "evento de puerta",
        ),
        (
            "    lv_obj_t* banner_sub_{nullptr};\n",
            """    lv_obj_t* banner_sub_{nullptr};\n    lv_obj_t* door_icon_{nullptr};\n    lv_obj_t* door_glyph_{nullptr};\n    lv_obj_t* door_switch_{nullptr};\n    lv_obj_t* door_state_{nullptr};\n    lv_obj_t* door_meta_{nullptr};\n""",
            "widgets de puerta",
        ),
        (
            "    char weather_current_text_[128]{};\n",
            """    char door_meta_text_[64]{};\n    char weather_current_text_[128]{};\n""",
            "buffer de puerta",
        ),
    ],
)

security_old = r'''    // Seguridad (chrome estatico): candado + estado + toggle armado.
    lv_obj_t* security_card = tile(pages_[0], 16, 280, 250, 168, kSurface);
    lv_obj_set_style_radius(security_card, 18, 0);
    lv_obj_t* lock_icon = lv_obj_create(security_card);
    lv_obj_set_size(lock_icon, 48, 48);
    lv_obj_set_pos(lock_icon, 0, 0);
    flat(lock_icon);
    lv_obj_set_style_radius(lock_icon, LV_RADIUS_CIRCLE, 0);
    // Sin proyeccion de seguridad de Wyss: estado desconocido, no anunciar "armado".
    lv_obj_set_style_bg_color(lock_icon, color(kBorder), 0);
    lv_obj_clear_flag(lock_icon, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t* lock_glyph =
        label(lock_icon, LV_SYMBOL_WARNING, &lv_font_montserrat_20, kMuted);
    lv_obj_center(lock_glyph);
    lv_obj_t* arm_switch = lv_switch_create(security_card);
    lv_obj_set_size(arm_switch, 56, 30);
    lv_obj_align(arm_switch, LV_ALIGN_TOP_RIGHT, 0, 8);
    lv_obj_clear_flag(arm_switch, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_t* sec_state = label(security_card, "Sin configurar", &lv_font_montserrat_26, kMuted);
    lv_obj_set_pos(sec_state, 0, 74);
    lv_obj_t* sec_zone =
        label(security_card, "Seguridad no proyectada", &lv_font_montserrat_14, kMuted);
    lv_obj_set_pos(sec_zone, 0, 112);
'''
security_new = r'''    // Check manual diario: recuerda si Santiago confirmo que cerro la puerta.
    // No representa una alarma ni una cerradura conectada.
    lv_obj_t* security_card = tile(pages_[0], 16, 280, 250, 168, kSurface);
    lv_obj_set_style_radius(security_card, 18, 0);
    lv_obj_add_flag(security_card, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(security_card, on_door_check, LV_EVENT_CLICKED, this);
    door_icon_ = lv_obj_create(security_card);
    lv_obj_set_size(door_icon_, 48, 48);
    lv_obj_set_pos(door_icon_, 0, 0);
    flat(door_icon_);
    lv_obj_set_style_radius(door_icon_, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(door_icon_, color(kAmbarBg), 0);
    lv_obj_clear_flag(door_icon_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(door_icon_, LV_OBJ_FLAG_CLICKABLE);
    door_glyph_ = label(door_icon_, LV_SYMBOL_WARNING, &lv_font_montserrat_20, kAmbarInk);
    lv_obj_center(door_glyph_);
    door_switch_ = lv_switch_create(security_card);
    lv_obj_set_size(door_switch_, 56, 30);
    lv_obj_align(door_switch_, LV_ALIGN_TOP_RIGHT, 0, 8);
    lv_obj_set_style_bg_color(door_switch_, color(kBorder), LV_PART_MAIN);
    lv_obj_set_style_bg_color(door_switch_, color(kGreen), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(door_switch_, color(kSurface), LV_PART_KNOB);
    lv_obj_clear_flag(door_switch_, LV_OBJ_FLAG_CLICKABLE);
    door_state_ = label(security_card, "Cerraste la puerta?", &lv_font_montserrat_20, kText);
    lv_obj_set_pos(door_state_, 0, 74);
    lv_obj_set_width(door_state_, 218);
    lv_label_set_long_mode(door_state_, LV_LABEL_LONG_DOT);
    door_meta_ = label(security_card, "Toca para confirmar", &lv_font_montserrat_14, kAmbarInk);
    lv_obj_set_pos(door_meta_, 0, 112);
'''

patch(
    "firmware/src/adapters/lvgl_panel_view.cpp",
    [
        (security_old, security_new, "tarjeta manual de puerta"),
        (
            "void LvglPanelView::render_weather(const domain::WeatherState& state) {\n",
            r'''void LvglPanelView::render_door_check(const domain::DoorCheckState& state) {
    if (door_switch_ == nullptr) return;

    if (state.closed) {
        lv_obj_add_state(door_switch_, LV_STATE_CHECKED);
        lv_obj_set_style_bg_color(door_icon_, color(0xDCFCE7), 0);
        lv_label_set_text(door_glyph_, LV_SYMBOL_OK);
        lv_obj_set_style_text_color(door_glyph_, color(kGreen), 0);
        lv_label_set_text(door_state_, "Cerrada");
        lv_obj_set_style_text_color(door_state_, color(kGreen), 0);
        if (state.confirmed_day != 0U) {
            std::snprintf(door_meta_text_, sizeof(door_meta_text_), "Confirmado %02u:%02u",
                          static_cast<unsigned>(state.confirmed_minute / 60U),
                          static_cast<unsigned>(state.confirmed_minute % 60U));
        } else {
            std::snprintf(door_meta_text_, sizeof(door_meta_text_), "Confirmado - sincronizando hora");
        }
        lv_obj_set_style_text_color(door_meta_, color(kGreen), 0);
    } else {
        lv_obj_clear_state(door_switch_, LV_STATE_CHECKED);
        lv_obj_set_style_bg_color(door_icon_, color(kAmbarBg), 0);
        lv_label_set_text(door_glyph_, LV_SYMBOL_WARNING);
        lv_obj_set_style_text_color(door_glyph_, color(kAmbarInk), 0);
        lv_label_set_text(door_state_, "Cerraste la puerta?");
        lv_obj_set_style_text_color(door_state_, color(kText), 0);
        std::snprintf(door_meta_text_, sizeof(door_meta_text_), "Toca para confirmar");
        lv_obj_set_style_text_color(door_meta_, color(kAmbarInk), 0);
    }
    lv_label_set_text_static(door_meta_, door_meta_text_);
}

void LvglPanelView::render_weather(const domain::WeatherState& state) {
''',
            "render dinamico de puerta",
        ),
        (
            "void LvglPanelView::on_media_previous(lv_event_t* event) {\n",
            r'''void LvglPanelView::on_door_check(lv_event_t* event) {
    auto* view = static_cast<LvglPanelView*>(lv_event_get_user_data(event));
    if (view != nullptr && view->service_ != nullptr) view->service_->toggle_door_check();
}

void LvglPanelView::on_media_previous(lv_event_t* event) {
''',
            "callback de puerta",
        ),
    ],
)

# Pruebas de dominio y mock de ViewPort.
patch(
    "tests/domain_tests.cpp",
    [
        (
            "class Commands final : public wyss::ports::CommandPort {\n",
            r'''class LocalTime final : public wyss::ports::LocalTimePort {
   public:
    [[nodiscard]] wyss::domain::LocalDateTime now_local() const noexcept override { return now; }
    wyss::domain::LocalDateTime now{};
};

class DoorStore final : public wyss::ports::DoorCheckStorePort {
   public:
    [[nodiscard]] wyss::domain::DoorCheckState load_door_check() override { return state; }
    bool save_door_check(const wyss::domain::DoorCheckState& value) override {
        ++writes;
        if (!succeeds) return false;
        state = value;
        return true;
    }
    wyss::domain::DoorCheckState state{};
    bool succeeds{true};
    unsigned writes{0};
};

class Commands final : public wyss::ports::CommandPort {
''',
            "fakes del check manual",
        ),
        (
            "    void render_timers(const wyss::domain::TimerState& value) override { timers = value; }\n",
            """    void render_timers(const wyss::domain::TimerState& value) override { timers = value; }\n    void render_door_check(const wyss::domain::DoorCheckState& value) override { door = value; }\n""",
            "fake render de puerta",
        ),
        (
            "    wyss::domain::TimerState timers;\n",
            """    wyss::domain::TimerState timers;\n    wyss::domain::DoorCheckState door;\n""",
            "estado fake de puerta",
        ),
        (
            "void timer_projection_is_forwarded_without_local_deadline_authority() {\n",
            r'''void manual_door_check_persists_and_resets_on_the_next_day() {
    Clock clock;
    Commands commands;
    View view;
    LocalTime local_time;
    DoorStore store;
    local_time.now = {true, 20260721U, static_cast<std::uint16_t>(17U * 60U + 42U)};
    wyss::application::PanelService service(clock, commands, view);
    service.configure_door_check(local_time, store);
    assert(!view.door.closed);

    service.toggle_door_check();
    assert(view.door.closed);
    assert(view.door.confirmed_day == 20260721U);
    assert(view.door.confirmed_minute == 17U * 60U + 42U);
    assert(store.state.closed);

    local_time.now = {true, 20260722U, 1U};
    clock.now += 1'000U;
    service.tick();
    assert(!view.door.closed);
    assert(!store.state.closed);
}

void door_check_confirmed_before_ntp_is_adopted_when_time_arrives() {
    Clock clock;
    Commands commands;
    View view;
    LocalTime local_time;
    DoorStore store;
    store.state = {true, 0U, 0U};
    wyss::application::PanelService service(clock, commands, view);
    service.configure_door_check(local_time, store);
    assert(view.door.closed);

    local_time.now = {true, 20260721U, 600U};
    clock.now += 1'000U;
    service.tick();
    assert(view.door.closed);
    assert(store.state.confirmed_day == 20260721U);
    assert(store.state.confirmed_minute == 600U);
}

void failed_door_persistence_keeps_the_previous_state() {
    Clock clock;
    Commands commands;
    View view;
    LocalTime local_time;
    DoorStore store;
    local_time.now = {true, 20260721U, 600U};
    store.succeeds = false;
    wyss::application::PanelService service(clock, commands, view);
    service.configure_door_check(local_time, store);
    service.toggle_door_check();
    assert(!view.door.closed);
    assert(view.toast_error);
}

void timer_projection_is_forwarded_without_local_deadline_authority() {
''',
            "pruebas del check manual",
        ),
        (
            "    timer_projection_is_forwarded_without_local_deadline_authority();\n",
            """    timer_projection_is_forwarded_without_local_deadline_authority();\n    manual_door_check_persists_and_resets_on_the_next_day();\n    door_check_confirmed_before_ntp_is_adopted_when_time_arrives();\n    failed_door_persistence_keeps_the_previous_state();\n""",
            "ejecucion de pruebas de puerta",
        ),
    ],
)

# Documentación breve y verificable.
readme = read("README.md")
needle = "## Calidad\n"
section = """## Check manual de puerta\n\nLa tarjeta de Inicio **no controla una alarma ni una cerradura**. Es un check diario local para\nrecordar si la puerta principal quedó cerrada. El ESP32 persiste el estado en un namespace NVS\nseparado, muestra la hora local de confirmación y lo reinicia al cambiar el día una vez que NTP\nestá sincronizado. Tocar nuevamente la tarjeta vuelve el estado a pendiente.\n\n"""
if section not in readme:
    readme = replace_once(readme, needle, section + needle, "documentacion del check manual")
write("README.md", readme)
