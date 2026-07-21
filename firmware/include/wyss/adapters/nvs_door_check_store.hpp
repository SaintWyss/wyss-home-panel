#pragma once

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
