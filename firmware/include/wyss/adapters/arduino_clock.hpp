#pragma once

#include <Arduino.h>

#include "wyss/ports/ports.hpp"

namespace wyss::adapters {

class ArduinoClock final : public ports::Clock {
   public:
    [[nodiscard]] std::uint64_t now_ms() const noexcept override { return millis(); }
};

}  // namespace wyss::adapters
