#pragma once

#include <functional>
#include <span>
#include <string_view>

#include "wyss/domain/types.hpp"

namespace wyss::ports {

class Clock {
   public:
    virtual ~Clock() = default;
    [[nodiscard]] virtual std::uint64_t now_ms() const noexcept = 0;
};

class CommandPort {
   public:
    virtual ~CommandPort() = default;
    virtual bool send_fast(const domain::FastCommand& command) = 0;
    virtual bool send_media(const domain::MediaCommand& command) = 0;
    virtual bool send_intent(const domain::Intent& intent) = 0;
    virtual bool confirm(std::string_view plan_id, bool accepted, domain::RiskLevel risk,
                         std::uint64_t revision) = 0;
    // ponytail: no-op default so mocks/stubs don't need to implement resync.
    virtual void request_resync() {}
};

class ViewPort {
   public:
    virtual ~ViewPort() = default;
    virtual void render_connection(domain::ConnectionState state) = 0;
    virtual void render_devices(std::span<const domain::DeviceState> devices) = 0;
    virtual void render_media(const domain::MediaState& state) = 0;
    virtual void render_weather(const domain::WeatherState& state) = 0;
    virtual void render_agenda(const domain::AgendaState& state) = 0;
    virtual void render_reminders(const domain::ReminderState& state) = 0;
    virtual void render_timers(const domain::TimerState& state) = 0;
    virtual void render_execution(const domain::ExecutionUpdate& update) = 0;
    virtual void render_plan(const domain::Plan& plan) = 0;
    virtual void render_toast(std::string_view message, bool error) = 0;
};

class ConfigStorePort {
   public:
    virtual ~ConfigStorePort() = default;
    virtual bool load() = 0;
    [[nodiscard]] virtual std::string_view bridge_url() const = 0;
    [[nodiscard]] virtual std::string_view device_token() const = 0;
    [[nodiscard]] virtual std::string_view wifi_ssid() const = 0;
    [[nodiscard]] virtual std::string_view wifi_password() const = 0;
    [[nodiscard]] virtual std::string_view panel_id() const = 0;
    [[nodiscard]] virtual std::string_view primary_entity() const = 0;
    [[nodiscard]] virtual std::string_view ca_certificate() const = 0;
};

}  // namespace wyss::ports
