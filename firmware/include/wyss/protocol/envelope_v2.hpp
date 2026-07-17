#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace wyss::protocol {

inline constexpr std::size_t kMaxMessageBytes = 8U * 1024U;
inline constexpr std::size_t kMaxJsonDepth = 8U;

enum class ValidationCode : std::uint8_t {
  Accept,
  InvalidMessage,
  UnsupportedVersion,
  MessageTooLarge,
  Replay,
  StaleRevision,
};

[[nodiscard]] std::string_view to_string(ValidationCode code) noexcept;

class ProtocolV2SessionValidator {
 public:
  explicit ProtocolV2SessionValidator(std::size_t max_recent = 256U);
  [[nodiscard]] ValidationCode validate(std::string_view raw);

 private:
  std::size_t max_recent_;
  std::deque<std::string> recent_;
  std::unordered_set<std::string> seen_;
  std::unordered_map<std::string, std::uint64_t> revisions_;
};

}  // namespace wyss::protocol
