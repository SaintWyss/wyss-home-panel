#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#ifndef WYSS_SOURCE_DIR
#error "WYSS_SOURCE_DIR is required"
#endif

int main() {
  const std::string path = std::string(WYSS_SOURCE_DIR) + "/tests/fixtures/protocol/v1/cases.json";
  std::ifstream stream(path);
  if (!stream) {
    std::cerr << "fixture missing\n";
    return 1;
  }
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  const std::string payload = buffer.str();
  const char* required[] = {
      "\"protocol_version\": 1",
      "\"hello_snapshot\"",
      "\"fast_command\"",
      "\"intent_submit\"",
      "\"plan_accept\"",
      "\"unsupported_version\"",
      "\"unknown_message\"",
      "\"state.snapshot\"",
      "\"execution.update\"",
      "\"plan.proposed\"",
  };
  for (const char* token : required) {
    if (payload.find(token) == std::string::npos) {
      std::cerr << "fixture token missing\n";
      return 1;
    }
  }
  if (payload.find("\"v\": 2") != std::string::npos ||
      payload.find("BEGIN PRIVATE KEY") != std::string::npos) {
    std::cerr << "fixture contains forbidden content\n";
    return 1;
  }
  return 0;
}
