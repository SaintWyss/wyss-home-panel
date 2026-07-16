#pragma once

#include <Arduino.h>
#include <Preferences.h>

#include <string>
#include <string_view>

#include "wyss/ports/ports.hpp"

namespace wyss::adapters {

class NvsConfigStore final : public ports::ConfigStorePort {
   public:
    bool load() override;
    bool poll_serial_provisioning();

    [[nodiscard]] std::string_view bridge_url() const override { return bridge_url_; }
    [[nodiscard]] std::string_view device_token() const override { return token_; }
    [[nodiscard]] std::string_view wifi_ssid() const override { return ssid_; }
    [[nodiscard]] std::string_view wifi_password() const override { return password_; }
    [[nodiscard]] std::string_view panel_id() const override { return panel_id_; }
    [[nodiscard]] std::string_view primary_entity() const override { return primary_entity_; }
    [[nodiscard]] std::string_view ca_certificate() const override { return ca_pem_; }

   private:
    bool save_json(const String& encoded);

    std::string ssid_;
    std::string password_;
    std::string bridge_url_;
    std::string token_;
    std::string panel_id_;
    std::string primary_entity_;
    std::string ca_pem_;
    String serial_line_;
};

}  // namespace wyss::adapters
