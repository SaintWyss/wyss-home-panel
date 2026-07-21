#pragma once

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
