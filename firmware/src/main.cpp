#include <Arduino.h>
#include <WiFi.h>

#include <esp_display_panel.hpp>
#include <memory>

#include "lvgl_v8_port.h"
#include "wyss/adapters/arduino_clock.hpp"
#include "wyss/adapters/bridge_client.hpp"
#include "wyss/adapters/lvgl_panel_view.hpp"
#include "wyss/adapters/nvs_config_store.hpp"
#include "wyss/application/panel_service.hpp"
#include "wyss/ui/design_tokens.hpp"

using esp_panel::board::Board;
using esp_panel::drivers::BusRGB;

namespace {
Board* board = nullptr;
wyss::adapters::ArduinoClock clock_port;
wyss::adapters::NvsConfigStore config;
wyss::adapters::LvglPanelView view;
std::unique_ptr<wyss::adapters::BridgeClient> bridge;
std::unique_ptr<wyss::application::PanelService> service;
bool configured = false;
bool backlight_sleeping = false;

void start_display() {
    board = new Board();
    board->init();
#if LVGL_PORT_AVOID_TEARING_MODE
    auto* lcd = board->getLCD();
    lcd->configFrameBufferNumber(LVGL_PORT_DISP_BUFFER_NUM);
#if ESP_PANEL_DRIVERS_BUS_ENABLE_RGB && CONFIG_IDF_TARGET_ESP32S3
    auto* bus = lcd->getBus();
    if (bus->getBasicAttributes().type == ESP_PANEL_BUS_TYPE_RGB) {
        static_cast<BusRGB*>(bus)->configRGB_BounceBufferSize(lcd->getFrameWidth() * 10);
    }
#endif
#endif
    if (!board->begin()) {
        Serial.println("FATAL display_init_failed");
        return;
    }
    lvgl_port_init(board->getLCD(), board->getTouch());
}

void start_network() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.setSleep(false);
    WiFi.begin(config.wifi_ssid().data(), config.wifi_password().data());
    bridge->begin();
}
}  // namespace

void setup() {
    Serial.begin(115200);
    delay(250);
    Serial.println("Wyss Home Panel 2.0.0");

    configured = config.load();
    bridge = std::make_unique<wyss::adapters::BridgeClient>(config);
    service = std::make_unique<wyss::application::PanelService>(clock_port, *bridge, view);
    start_display();

    lvgl_port_lock(-1);
    view.begin(*service, configured ? std::string(config.primary_entity()) : "light.unconfigured");
    if (!configured) {
        view.render_toast("Conectame por USB y ejecutá tools/provision.py", true);
    }
    lvgl_port_unlock();

    if (configured) {
        start_network();
    }
}

void loop() {
    if (config.poll_serial_provisioning()) {
        delay(100);
        ESP.restart();
    }
    if (configured && service != nullptr && bridge != nullptr) {
        lvgl_port_lock(-1);
        bridge->poll(*service);
        service->tick();
        lvgl_port_unlock();
    }
    if (board != nullptr) {
        const bool should_sleep =
            lv_disp_get_inactive_time(nullptr) > wyss::ui::tokens::sleeping_after_ms;
        if (should_sleep != backlight_sleeping) {
            backlight_sleeping = should_sleep;
            lvgl_port_lock(-1);
            if (should_sleep) {
                view.set_mode(wyss::ui::ShellMode::Sleeping);
                board->getBacklight()->setBrightness(wyss::ui::tokens::sleeping_brightness);
            } else {
                if (view.mode() == wyss::ui::ShellMode::Sleeping) {
                    view.set_mode(wyss::ui::ShellMode::Manual);
                }
                board->getBacklight()->setBrightness(wyss::ui::tokens::active_brightness);
            }
            lvgl_port_unlock();
        }
    }
    delay(5);
}
