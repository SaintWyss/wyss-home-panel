#include "wyss/adapters/nvs_config_store.hpp"

#include <ArduinoJson.h>
#include <esp_system.h>
#include <mbedtls/base64.h>

#include <array>
#include <cstdio>
#include <vector>

namespace wyss::adapters {
namespace {
constexpr const char* kNamespace = "wyss-panel";

std::string read_string(Preferences& preferences, const char* key) {
    const String value = preferences.getString(key, "");
    return {value.c_str(), value.length()};
}
}  // namespace

bool NvsConfigStore::load() {
    Preferences preferences;
    if (!preferences.begin(kNamespace, true)) {
        return false;
    }
    ssid_ = read_string(preferences, "ssid");
    password_ = read_string(preferences, "wifi-pass");
    bridge_url_ = read_string(preferences, "bridge-url");
    token_ = read_string(preferences, "token");
    panel_id_ = read_string(preferences, "panel-id");
    primary_entity_ = read_string(preferences, "primary");
    ca_pem_ = read_string(preferences, "ca-pem");
    preferences.end();
    return !ssid_.empty() && !bridge_url_.empty() && !token_.empty() && !panel_id_.empty() &&
           !primary_entity_.empty() &&
           !ca_pem_.empty();
}

bool NvsConfigStore::poll_serial_provisioning() {
    while (Serial.available() > 0) {
        const char byte = static_cast<char>(Serial.read());
        if (byte == '\n') {
            serial_line_.trim();
            const bool handled = serial_line_.startsWith("WYSSCFG ");
            const bool saved = handled && save_json(serial_line_.substring(8));
            if (handled) {
                Serial.println(saved ? "PROVISIONING_OK" : "PROVISIONING_ERROR invalid_config");
            }
            serial_line_.clear();
            return saved;
        }
        if (byte != '\r' && serial_line_.length() < 8192) {
            serial_line_ += byte;
        }
    }
    return false;
}

bool NvsConfigStore::save_json(const String& encoded) {
    std::vector<unsigned char> decoded((encoded.length() * 3U) / 4U + 4U);
    std::size_t decoded_length = 0;
    const int result = mbedtls_base64_decode(decoded.data(), decoded.size(), &decoded_length,
                                             reinterpret_cast<const unsigned char*>(encoded.c_str()),
                                             encoded.length());
    if (result != 0 || decoded_length == 0) {
        return false;
    }
    decoded[decoded_length] = 0;

    JsonDocument document;
    if (deserializeJson(document, decoded.data(), decoded_length) != DeserializationError::Ok) {
        return false;
    }
    const char* ssid = document["wifi_ssid"] | "";
    const char* password = document["wifi_password"] | "";
    const char* bridge_url = document["bridge_url"] | "";
    const char* token = document["device_token"] | "";
    const char* ca_pem = document["ca_certificate"] | "";
    const char* primary_entity = document["primary_entity"] | "";
    String panel_id = document["panel_id"] | "";
    if (panel_id.isEmpty()) {
        std::array<char, 24> generated{};
        std::snprintf(generated.data(), generated.size(), "wyss-%012llx",
                      static_cast<unsigned long long>(ESP.getEfuseMac()));
        panel_id = generated.data();
    }
    if (String(ssid).isEmpty() || !String(primary_entity).startsWith("light.") ||
        !String(bridge_url).startsWith("wss://") ||
        String(token).length() < 32 || String(ca_pem).indexOf("BEGIN CERTIFICATE") < 0) {
        return false;
    }

    Preferences preferences;
    if (!preferences.begin(kNamespace, false)) {
        return false;
    }
    const bool saved = preferences.putString("ssid", ssid) > 0 &&
                       preferences.putString("wifi-pass", password) > 0 &&
                       preferences.putString("bridge-url", bridge_url) > 0 &&
                       preferences.putString("token", token) > 0 &&
                       preferences.putString("panel-id", panel_id) > 0 &&
                       preferences.putString("primary", primary_entity) > 0 &&
                       preferences.putString("ca-pem", ca_pem) > 0;
    preferences.end();
    if (saved) {
        return load();
    }
    return false;
}

}  // namespace wyss::adapters
