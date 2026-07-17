#include "wyss/protocol/envelope_v2.hpp"

#if defined(WYSS_ENABLE_PROTOCOL_V2)

#include <algorithm>
#include <charconv>
#include <cctype>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace wyss::protocol {
namespace {

enum class Kind : std::uint8_t { Null, Boolean, Number, String, Array, Object };

struct JsonValue {
  Kind kind{Kind::Null};
  bool boolean{false};
  bool integer_valid{false};
  std::int64_t integer{0};
  std::string string;
  std::vector<JsonValue> array;
  std::unordered_map<std::string, JsonValue> object;
};

class ParseError final : public std::runtime_error {
 public:
  ParseError() : std::runtime_error("invalid JSON") {}
};

class Parser final {
 public:
  explicit Parser(std::string_view input) : input_(input) {}

  [[nodiscard]] JsonValue parse() {
    JsonValue result = value(1U);
    whitespace();
    if (position_ != input_.size()) {
      throw ParseError();
    }
    return result;
  }

 private:
  [[nodiscard]] JsonValue value(std::size_t depth) {
    if (depth > kMaxJsonDepth) {
      throw ParseError();
    }
    whitespace();
    if (position_ >= input_.size()) {
      throw ParseError();
    }
    const char current = input_[position_];
    if (current == '{') {
      return object(depth);
    }
    if (current == '[') {
      return array(depth);
    }
    if (current == '"') {
      JsonValue result;
      result.kind = Kind::String;
      result.string = string();
      return result;
    }
    if (current == 't') {
      literal("true");
      JsonValue result;
      result.kind = Kind::Boolean;
      result.boolean = true;
      return result;
    }
    if (current == 'f') {
      literal("false");
      JsonValue result;
      result.kind = Kind::Boolean;
      return result;
    }
    if (current == 'n') {
      literal("null");
      return JsonValue{};
    }
    if (current == '-' || std::isdigit(static_cast<unsigned char>(current)) != 0) {
      return number();
    }
    throw ParseError();
  }

  [[nodiscard]] JsonValue object(std::size_t depth) {
    consume('{');
    JsonValue result;
    result.kind = Kind::Object;
    whitespace();
    if (peek('}')) {
      consume('}');
      return result;
    }
    while (true) {
      whitespace();
      if (!peek('"')) {
        throw ParseError();
      }
      std::string key = string();
      whitespace();
      consume(':');
      if (result.object.contains(key)) {
        throw ParseError();
      }
      result.object.emplace(std::move(key), value(depth + 1U));
      whitespace();
      if (peek('}')) {
        consume('}');
        return result;
      }
      consume(',');
    }
  }

  [[nodiscard]] JsonValue array(std::size_t depth) {
    consume('[');
    JsonValue result;
    result.kind = Kind::Array;
    whitespace();
    if (peek(']')) {
      consume(']');
      return result;
    }
    while (true) {
      result.array.push_back(value(depth + 1U));
      whitespace();
      if (peek(']')) {
        consume(']');
        return result;
      }
      consume(',');
    }
  }

  [[nodiscard]] std::string string() {
    consume('"');
    std::string result;
    while (position_ < input_.size()) {
      const char current = input_[position_++];
      if (current == '"') {
        return result;
      }
      if (static_cast<unsigned char>(current) < 0x20U) {
        throw ParseError();
      }
      if (current != '\\') {
        result.push_back(current);
        continue;
      }
      if (position_ >= input_.size()) {
        throw ParseError();
      }
      const char escaped = input_[position_++];
      switch (escaped) {
        case '"':
        case '\\':
        case '/':
          result.push_back(escaped);
          break;
        case 'b':
          result.push_back('\b');
          break;
        case 'f':
          result.push_back('\f');
          break;
        case 'n':
          result.push_back('\n');
          break;
        case 'r':
          result.push_back('\r');
          break;
        case 't':
          result.push_back('\t');
          break;
        case 'u':
          unicode_escape(result);
          break;
        default:
          throw ParseError();
      }
    }
    throw ParseError();
  }

  void unicode_escape(std::string& output) {
    if (position_ + 4U > input_.size()) {
      throw ParseError();
    }
    for (std::size_t index = 0; index < 4U; ++index) {
      if (std::isxdigit(static_cast<unsigned char>(input_[position_ + index])) == 0) {
        throw ParseError();
      }
    }
    position_ += 4U;
    output.push_back('?');
  }

  [[nodiscard]] JsonValue number() {
    const std::size_t start = position_;
    if (peek('-')) {
      ++position_;
    }
    if (position_ >= input_.size()) {
      throw ParseError();
    }
    if (input_[position_] == '0') {
      ++position_;
      if (position_ < input_.size() &&
          std::isdigit(static_cast<unsigned char>(input_[position_])) != 0) {
        throw ParseError();
      }
    } else {
      if (std::isdigit(static_cast<unsigned char>(input_[position_])) == 0) {
        throw ParseError();
      }
      while (position_ < input_.size() &&
             std::isdigit(static_cast<unsigned char>(input_[position_])) != 0) {
        ++position_;
      }
    }
    bool integer_valid = true;
    if (position_ < input_.size() && input_[position_] == '.') {
      integer_valid = false;
      ++position_;
      digits();
    }
    if (position_ < input_.size() && (input_[position_] == 'e' || input_[position_] == 'E')) {
      integer_valid = false;
      ++position_;
      if (position_ < input_.size() && (input_[position_] == '+' || input_[position_] == '-')) {
        ++position_;
      }
      digits();
    }
    JsonValue result;
    result.kind = Kind::Number;
    result.integer_valid = integer_valid;
    if (integer_valid) {
      const std::string_view token = input_.substr(start, position_ - start);
      const auto parsed = std::from_chars(token.data(), token.data() + token.size(), result.integer);
      if (parsed.ec != std::errc{} || parsed.ptr != token.data() + token.size()) {
        throw ParseError();
      }
    }
    return result;
  }

  void digits() {
    const std::size_t start = position_;
    while (position_ < input_.size() &&
           std::isdigit(static_cast<unsigned char>(input_[position_])) != 0) {
      ++position_;
    }
    if (position_ == start) {
      throw ParseError();
    }
  }

  void literal(std::string_view expected) {
    if (input_.substr(position_, expected.size()) != expected) {
      throw ParseError();
    }
    position_ += expected.size();
  }

  void whitespace() {
    while (position_ < input_.size() &&
           std::isspace(static_cast<unsigned char>(input_[position_])) != 0) {
      ++position_;
    }
  }

  [[nodiscard]] bool peek(char expected) const noexcept {
    return position_ < input_.size() && input_[position_] == expected;
  }

  void consume(char expected) {
    if (!peek(expected)) {
      throw ParseError();
    }
    ++position_;
  }

  std::string_view input_;
  std::size_t position_{0};
};

[[nodiscard]] const JsonValue& required(const JsonValue& object, std::string_view key) {
  const auto found = object.object.find(std::string(key));
  if (found == object.object.end()) {
    throw ParseError();
  }
  return found->second;
}

[[nodiscard]] bool non_negative_integer(const JsonValue& value) noexcept {
  return value.kind == Kind::Number && value.integer_valid && value.integer >= 0;
}

[[nodiscard]] bool valid_identifier(std::string_view value, std::size_t maximum = 128U) {
  if (value.empty() || value.size() > maximum ||
      std::isalnum(static_cast<unsigned char>(value.front())) == 0) {
    return false;
  }
  return std::all_of(value.begin() + 1, value.end(), [](char character) {
    return std::isalnum(static_cast<unsigned char>(character)) != 0 || character == ':' ||
           character == '.' || character == '_' || character == '-';
  });
}

[[nodiscard]] bool exact_keys(const JsonValue& object,
                              const std::unordered_set<std::string>& expected) {
  if (object.kind != Kind::Object || object.object.size() != expected.size()) {
    return false;
  }
  return std::all_of(expected.begin(), expected.end(), [&](const std::string& key) {
    return object.object.contains(key);
  });
}

[[nodiscard]] bool subset_keys(const JsonValue& object,
                               const std::unordered_set<std::string>& allowed) {
  return object.kind == Kind::Object &&
         std::all_of(object.object.begin(), object.object.end(), [&](const auto& entry) {
           return allowed.contains(entry.first);
         });
}

const std::unordered_set<std::string> kKnownTypes = {
    "session.hello",             "session.welcome",          "session.heartbeat",
    "home.command",             "assistant.intent",         "plan.answer",
    "capability.command",       "assistant.state.changed",  "assistant.response.delta",
    "assistant.response.completed", "plan.proposed",        "plan.resolved",
    "execution.updated",        "home.entity.changed",      "spotify.state.changed",
    "weather.forecast.changed", "calendar.agenda.changed",  "reminder.changed",
    "timer.changed",            "timer.completed",          "camera.state.changed",
    "notification.delivered",   "system.health.changed",    "projection.snapshot",
    "projection.delta",         "error",
};

const std::unordered_set<std::string> kErrorCodes = {
    "unauthenticated",       "forbidden",             "device_revoked",
    "unsupported_version",  "invalid_message",       "message_too_large",
    "rate_limited",          "conflict",              "already_resolved",
    "provider_unavailable", "entity_unavailable",    "timeout",
    "policy_rejected",      "confirmation_required", "snapshot_required",
    "internal_error",
};

class ProtocolV2Error final : public std::runtime_error {
 public:
  explicit ProtocolV2Error(ValidationCode code)
      : std::runtime_error("protocol v2 error"), code_(code) {}
  [[nodiscard]] ValidationCode code() const noexcept { return code_; }

 private:
  ValidationCode code_;
};

struct ParsedEnvelope {
  std::string type;
  std::string message_id;
  std::string aggregate;
  std::uint64_t revision{0};
};

void validate_payload(const std::string& type, const JsonValue& payload) {
  if (payload.kind != Kind::Object) {
    throw ParseError();
  }
  if (type == "session.hello") {
    if (!exact_keys(payload, {"firmware", "capabilities", "last_event_id"})) {
      throw ParseError();
    }
    const JsonValue& firmware = required(payload, "firmware");
    const JsonValue& capabilities = required(payload, "capabilities");
    if (firmware.kind != Kind::String || capabilities.kind != Kind::Array ||
        capabilities.array.size() > 32U ||
        !std::all_of(capabilities.array.begin(), capabilities.array.end(), [](const auto& item) {
          return item.kind == Kind::String && !item.string.empty() && item.string.size() <= 64U;
        }) ||
        !non_negative_integer(required(payload, "last_event_id"))) {
      throw ParseError();
    }
  } else if (type == "home.command") {
    const std::unordered_set<std::string> required_fields = {
        "request_id", "idempotency_key", "entity_id", "action",
    };
    const std::unordered_set<std::string> allowed_fields = {
        "request_id", "idempotency_key", "entity_id", "action",
        "value",      "rgb",             "expected_revision",
    };
    if (!subset_keys(payload, allowed_fields) ||
        !std::all_of(required_fields.begin(), required_fields.end(),
                     [&](const std::string& key) { return payload.object.contains(key); })) {
      throw ParseError();
    }
    const JsonValue& request_id = required(payload, "request_id");
    const JsonValue& idempotency_key = required(payload, "idempotency_key");
    const JsonValue& entity_id = required(payload, "entity_id");
    const JsonValue& action = required(payload, "action");
    if (request_id.kind != Kind::String || !valid_identifier(request_id.string) ||
        idempotency_key.kind != Kind::String || !valid_identifier(idempotency_key.string) ||
        entity_id.kind != Kind::String || !valid_identifier(entity_id.string) ||
        action.kind != Kind::String || action.string.empty() || action.string.size() > 32U) {
      throw ParseError();
    }
    const auto expected = payload.object.find("expected_revision");
    if (expected != payload.object.end() && !non_negative_integer(expected->second)) {
      throw ParseError();
    }
    const auto value = payload.object.find("value");
    const auto rgb = payload.object.find("rgb");
    const bool is_light = entity_id.string.starts_with("light.");
    const bool is_scene = entity_id.string.starts_with("scene.");
    bool valid = false;
    if (action.string == "activate_scene") {
      valid = is_scene && value == payload.object.end() && rgb == payload.object.end();
    } else if (action.string == "set_brightness") {
      valid = is_light && value != payload.object.end() &&
              non_negative_integer(value->second) && value->second.integer <= 100 &&
              rgb == payload.object.end();
    } else if (action.string == "set_color") {
      valid = is_light && rgb != payload.object.end() && non_negative_integer(rgb->second) &&
              rgb->second.integer <= 0xFFFFFF && value == payload.object.end();
    } else {
      valid = is_light && value == payload.object.end() && rgb == payload.object.end() &&
              (action.string == "turn_on" || action.string == "turn_off" ||
               action.string == "toggle");
    }
    if (!valid) {
      throw ParseError();
    }
  } else if (type == "projection.snapshot") {
    const std::unordered_set<std::string> allowed = {
        "projection_version", "assistant", "home", "spotify", "weather",
        "agenda",             "timers",    "cameras",
    };
    if (!subset_keys(payload, allowed) || !payload.object.contains("projection_version") ||
        !non_negative_integer(required(payload, "projection_version"))) {
      throw ParseError();
    }
  } else if (type == "projection.delta") {
    if (!exact_keys(payload, {"aggregate", "revision", "event_id", "changes"})) {
      throw ParseError();
    }
    const JsonValue& aggregate = required(payload, "aggregate");
    const JsonValue& revision = required(payload, "revision");
    const JsonValue& event_id = required(payload, "event_id");
    if (aggregate.kind != Kind::String || aggregate.string.empty() ||
        !non_negative_integer(revision) || revision.integer == 0 ||
        !non_negative_integer(event_id) || event_id.integer == 0 ||
        required(payload, "changes").kind != Kind::Object) {
      throw ParseError();
    }
  } else if (type == "error") {
    if (!exact_keys(payload, {"code", "message"})) {
      throw ParseError();
    }
    const JsonValue& code = required(payload, "code");
    const JsonValue& message = required(payload, "message");
    if (code.kind != Kind::String || !kErrorCodes.contains(code.string) ||
        message.kind != Kind::String || message.string.empty() || message.string.size() > 256U) {
      throw ParseError();
    }
  }
}

[[nodiscard]] ParsedEnvelope parse_envelope(std::string_view raw) {
  JsonValue root = Parser(raw).parse();
  if (root.kind != Kind::Object) {
    throw ParseError();
  }
  const std::unordered_set<std::string> required_fields = {
      "v", "type", "message_id", "source", "payload",
  };
  const std::unordered_set<std::string> allowed_fields = {
      "v", "type", "message_id", "source", "payload", "correlation_id", "causation_id", "sent_at",
  };
  if (!subset_keys(root, allowed_fields) ||
      !std::all_of(required_fields.begin(), required_fields.end(), [&](const std::string& key) {
        return root.object.contains(key);
      })) {
    throw ParseError();
  }
  const JsonValue& version = required(root, "v");
  if (version.kind != Kind::Number || !version.integer_valid) {
    throw ParseError();
  }
  if (version.integer != 2) {
    throw ProtocolV2Error(ValidationCode::UnsupportedVersion);
  }
  const JsonValue& type = required(root, "type");
  const JsonValue& message_id = required(root, "message_id");
  const JsonValue& source = required(root, "source");
  if (type.kind != Kind::String || !kKnownTypes.contains(type.string) ||
      message_id.kind != Kind::String || !valid_identifier(message_id.string) ||
      source.kind != Kind::String || !valid_identifier(source.string)) {
    throw ParseError();
  }
  for (const char* field : {"correlation_id", "causation_id"}) {
    const auto found = root.object.find(field);
    if (found != root.object.end() &&
        (found->second.kind != Kind::String || !valid_identifier(found->second.string))) {
      throw ParseError();
    }
  }
  const auto sent_at = root.object.find("sent_at");
  if (sent_at != root.object.end() &&
      (sent_at->second.kind != Kind::String || sent_at->second.string.size() < 20U ||
       sent_at->second.string.back() != 'Z')) {
    throw ParseError();
  }
  const JsonValue& payload = required(root, "payload");
  validate_payload(type.string, payload);
  ParsedEnvelope envelope{type.string, message_id.string, {}, 0U};
  if (type.string == "projection.snapshot") {
    envelope.aggregate = "projection";
    envelope.revision = static_cast<std::uint64_t>(
        required(payload, "projection_version").integer);
  } else if (type.string == "projection.delta") {
    envelope.aggregate = required(payload, "aggregate").string;
    envelope.revision =
        static_cast<std::uint64_t>(required(payload, "revision").integer);
  }
  return envelope;
}

}  // namespace

std::string_view to_string(ValidationCode code) noexcept {
  switch (code) {
    case ValidationCode::Accept:
      return "accept";
    case ValidationCode::InvalidMessage:
      return "invalid_message";
    case ValidationCode::UnsupportedVersion:
      return "unsupported_version";
    case ValidationCode::MessageTooLarge:
      return "message_too_large";
    case ValidationCode::Replay:
      return "replay";
    case ValidationCode::StaleRevision:
      return "stale_revision";
  }
  return "invalid_message";
}

ProtocolV2SessionValidator::ProtocolV2SessionValidator(std::size_t max_recent)
    : max_recent_(max_recent) {
  if (max_recent_ == 0U) {
    throw std::invalid_argument("max_recent must be positive");
  }
}

ValidationCode ProtocolV2SessionValidator::validate(std::string_view raw) {
  if (raw.size() > kMaxMessageBytes) {
    return ValidationCode::MessageTooLarge;
  }
  try {
    const ParsedEnvelope envelope = parse_envelope(raw);
    if (seen_.contains(envelope.message_id)) {
      return ValidationCode::Replay;
    }
    if (envelope.type == "projection.snapshot") {
      revisions_[envelope.aggregate] = envelope.revision;
    } else if (envelope.type == "projection.delta") {
      if (envelope.revision <= revisions_[envelope.aggregate]) {
        return ValidationCode::StaleRevision;
      }
      revisions_[envelope.aggregate] = envelope.revision;
    }
    seen_.insert(envelope.message_id);
    recent_.push_back(envelope.message_id);
    if (recent_.size() > max_recent_) {
      seen_.erase(recent_.front());
      recent_.pop_front();
    }
    return ValidationCode::Accept;
  } catch (const ProtocolV2Error& error) {
    return error.code();
  } catch (const ParseError&) {
    return ValidationCode::InvalidMessage;
  }
}

}  // namespace wyss::protocol

#endif  // WYSS_ENABLE_PROTOCOL_V2
