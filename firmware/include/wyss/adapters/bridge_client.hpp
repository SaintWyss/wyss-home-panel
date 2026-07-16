#pragma once

#include <Arduino.h>
#include <WiFiClientSecure.h>
#include <WebSocketsClient.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include <atomic>
#include <string_view>

#include "wyss/application/panel_service.hpp"
#include "wyss/ports/ports.hpp"

namespace wyss::adapters {

class BridgeClient final : public ports::CommandPort {
   public:
    explicit BridgeClient(const ports::ConfigStorePort& config);
    ~BridgeClient() override;

    bool begin();
    void poll(application::PanelService& service);
    bool send_fast(const domain::FastCommand& command) override;
    bool send_intent(const domain::Intent& intent) override;
    bool confirm(std::string_view plan_id, bool accepted, domain::RiskLevel risk) override;

   private:
    static constexpr std::size_t kMaxMessageBytes = 2048;
    struct Message {
        char text[kMaxMessageBytes];
    };

    static void task_entry(void* context);
    void run();
    void handle_socket_event(WStype_t type, std::uint8_t* payload, std::size_t length);
    bool enqueue_json(const char* json, std::size_t length);
    void dispatch(application::PanelService& service, const char* json);

    const ports::ConfigStorePort& config_;
    WebSocketsClient socket_;
    QueueHandle_t outbound_{nullptr};
    QueueHandle_t inbound_{nullptr};
    TaskHandle_t task_{nullptr};
    std::atomic<domain::ConnectionState> state_{domain::ConnectionState::Offline};
    domain::ConnectionState rendered_state_{domain::ConnectionState::Offline};
    String auth_header_;
};

}  // namespace wyss::adapters
