#include <fstream>
#include <iostream>
#include <string>
#include <string_view>

#include "wyss/protocol/envelope_v2.hpp"

#ifndef WYSS_SOURCE_DIR
#error "WYSS_SOURCE_DIR is required"
#endif

namespace {

std::string generated(std::string_view name) {
  if (name == "oversized") {
    return "{" + std::string(8192U, ' ') + "}";
  }
  if (name == "deep") {
    std::string nested;
    for (std::size_t index = 0; index < 9U; ++index) {
      nested += R"({"child":)";
    }
    nested += "null";
    nested += std::string(9U, '}');
    return R"({"v":2,"type":"session.heartbeat","message_id":"msg-deep",)" +
           std::string(R"("source":"panel:living","payload":)") + nested + "}";
  }
  return {};
}

}  // namespace

int main() {
  const std::string path =
      std::string(WYSS_SOURCE_DIR) + "/tests/fixtures/protocol/v2/cases.jsonl";
  std::ifstream stream(path);
  if (!stream) {
    std::cerr << "v2 fixture missing\n";
    return 1;
  }

  wyss::protocol::ProtocolV2SessionValidator validator;
  std::string line;
  std::size_t observed = 0U;
  while (std::getline(stream, line)) {
    if (line.empty() || line.front() == '#') {
      continue;
    }
    const std::size_t first = line.find('\t');
    const std::size_t second = line.find('\t', first + 1U);
    if (first == std::string::npos || second == std::string::npos) {
      std::cerr << "invalid fixture row\n";
      return 1;
    }
    const std::string case_id = line.substr(0U, first);
    const std::string expected = line.substr(first + 1U, second - first - 1U);
    std::string raw = line.substr(second + 1U);
    constexpr std::string_view prefix = "@generate:";
    if (raw.starts_with(prefix)) {
      raw = generated(std::string_view(raw).substr(prefix.size()));
    }
    const std::string_view actual = wyss::protocol::to_string(validator.validate(raw));
    if (actual != expected) {
      std::cerr << case_id << ": expected " << expected << ", got " << actual << '\n';
      return 1;
    }
    ++observed;
  }
  if (observed < 17U) {
    std::cerr << "insufficient v2 fixtures\n";
    return 1;
  }
  return 0;
}
