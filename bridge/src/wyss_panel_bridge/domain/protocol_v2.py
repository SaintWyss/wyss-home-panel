"""Contrato puro y acotado de Wyss Home Protocol v2."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

MAX_MESSAGE_BYTES = 8 * 1024
MAX_JSON_DEPTH = 8
MAX_ID_CHARS = 128
MAX_SOURCE_CHARS = 128
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
REQUIRED_FIELDS = {"v", "type", "message_id", "source", "payload"}
OPTIONAL_FIELDS = {"correlation_id", "causation_id", "sent_at"}
KNOWN_TYPES = {
    "session.hello",
    "session.welcome",
    "session.heartbeat",
    "home.command",
    "assistant.intent",
    "plan.answer",
    "capability.command",
    "assistant.state.changed",
    "assistant.response.delta",
    "assistant.response.completed",
    "plan.proposed",
    "plan.resolved",
    "execution.updated",
    "home.entity.changed",
    "spotify.state.changed",
    "weather.forecast.changed",
    "calendar.agenda.changed",
    "reminder.changed",
    "timer.changed",
    "timer.completed",
    "camera.state.changed",
    "notification.delivered",
    "system.health.changed",
    "projection.snapshot",
    "projection.delta",
    "error",
}
ERROR_CODES = {
    "unauthenticated",
    "forbidden",
    "device_revoked",
    "unsupported_version",
    "invalid_message",
    "message_too_large",
    "rate_limited",
    "conflict",
    "already_resolved",
    "provider_unavailable",
    "entity_unavailable",
    "timeout",
    "policy_rejected",
    "confirmation_required",
    "snapshot_required",
    "internal_error",
}


class ValidationCode(StrEnum):
    ACCEPT = "accept"
    INVALID_MESSAGE = "invalid_message"
    UNSUPPORTED_VERSION = "unsupported_version"
    MESSAGE_TOO_LARGE = "message_too_large"
    REPLAY = "replay"
    STALE_REVISION = "stale_revision"


class ProtocolV2Error(ValueError):
    def __init__(self, code: ValidationCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class EnvelopeV2:
    message_type: str
    message_id: str
    source: str
    payload: dict[str, Any]
    correlation_id: str | None = None
    causation_id: str | None = None
    sent_at: str | None = None


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        value[key] = child
    return value


def _depth(value: Any, current: int = 1) -> int:
    if isinstance(value, dict):
        return max((current, *(_depth(child, current + 1) for child in value.values())))
    if isinstance(value, list):
        return max((current, *(_depth(child, current + 1) for child in value)))
    return current


def _required_string(value: Any, maximum: int, *, identifier: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    if identifier and ID_RE.fullmatch(value) is None:
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    return value


def _non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _bounded_int(value: Any, maximum: int) -> bool:
    return _non_negative_int(value) and isinstance(value, int) and value <= maximum


def _validate_payload(message_type: str, payload: dict[str, Any]) -> None:
    if message_type == "session.hello":
        if set(payload) != {"firmware", "capabilities", "last_event_id"}:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        capabilities = payload["capabilities"]
        if (
            not isinstance(payload["firmware"], str)
            or not isinstance(capabilities, list)
            or len(capabilities) > 32
            or not all(isinstance(item, str) and 0 < len(item) <= 64 for item in capabilities)
            or not _non_negative_int(payload["last_event_id"])
        ):
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "home.command":
        required = {"request_id", "idempotency_key", "entity_id", "action"}
        allowed = required | {"value", "rgb", "expected_revision"}
        if not required <= set(payload) or not set(payload) <= allowed:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        request_id = _required_string(payload["request_id"], MAX_ID_CHARS, identifier=True)
        idempotency_key = _required_string(
            payload["idempotency_key"], MAX_ID_CHARS, identifier=True
        )
        entity_id = _required_string(payload["entity_id"], MAX_ID_CHARS, identifier=True)
        action = _required_string(payload["action"], 32)
        if not request_id or not idempotency_key:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        expected_revision = payload.get("expected_revision")
        if expected_revision is not None and not _non_negative_int(expected_revision):
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        is_scene = entity_id.startswith("scene.")
        if action == "activate_scene":
            valid = is_scene and "value" not in payload and "rgb" not in payload
        elif action == "set_brightness":
            value = payload.get("value")
            valid = (
                not is_scene
                and entity_id.startswith("light.")
                and _bounded_int(value, 100)
                and "rgb" not in payload
            )
        elif action == "set_color":
            rgb = payload.get("rgb")
            valid = (
                not is_scene
                and entity_id.startswith("light.")
                and _bounded_int(rgb, 0xFFFFFF)
                and "value" not in payload
            )
        else:
            valid = (
                action in {"turn_on", "turn_off", "toggle"}
                and entity_id.startswith("light.")
                and "value" not in payload
                and "rgb" not in payload
            )
        if not valid:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "assistant.intent":
        if set(payload) != {"request_id", "text", "input"}:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        _required_string(payload["request_id"], MAX_ID_CHARS, identifier=True)
        text = _required_string(payload["text"], 1000)
        if not text.strip() or payload["input"] not in {"text", "voice"}:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "capability.command":
        required = {"capability", "action", "idempotency_key"}
        allowed = required | {"value", "device_id", "expected_revision"}
        if not required <= set(payload) or not set(payload) <= allowed:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        capability = _required_string(payload["capability"], 64, identifier=True)
        action = _required_string(payload["action"], 32)
        _required_string(payload["idempotency_key"], MAX_ID_CHARS, identifier=True)
        expected_revision = payload.get("expected_revision")
        if expected_revision is not None and not _non_negative_int(expected_revision):
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        if capability != "spotify":
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        if action == "set_volume":
            valid = _bounded_int(payload.get("value"), 100) and "device_id" not in payload
        elif action == "transfer_device":
            device_id = payload.get("device_id")
            valid = (
                isinstance(device_id, str)
                and 0 < len(device_id) <= MAX_ID_CHARS
                and "value" not in payload
            )
        else:
            valid = (
                action in {"play", "pause", "previous", "next", "toggle_favorite"}
                and "value" not in payload
                and "device_id" not in payload
            )
        if not valid:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "plan.answer":
        if set(payload) != {
            "plan_id",
            "decision",
            "confirmation",
            "expected_revision",
        }:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        _required_string(payload["plan_id"], MAX_ID_CHARS, identifier=True)
        if payload["decision"] not in {"approve", "reject"}:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        confirmation = payload["confirmation"]
        if not isinstance(confirmation, str) or len(confirmation) > 16:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        revision = payload["expected_revision"]
        if not _non_negative_int(revision) or revision == 0:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "projection.snapshot":
        allowed = {
            "projection_version",
            "assistant",
            "home",
            "spotify",
            "weather",
            "agenda",
            "reminders",
            "timers",
            "cameras",
        }
        if "projection_version" not in payload or not set(payload) <= allowed:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        if not _non_negative_int(payload["projection_version"]):
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "projection.delta":
        if set(payload) != {"aggregate", "revision", "event_id", "changes"}:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        if (
            not isinstance(payload["aggregate"], str)
            or not _non_negative_int(payload["revision"])
            or payload["revision"] == 0
            or not _non_negative_int(payload["event_id"])
            or payload["event_id"] == 0
            or not isinstance(payload["changes"], dict)
        ):
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    elif message_type == "error":
        if set(payload) != {"code", "message"}:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        if payload["code"] not in ERROR_CODES:
            raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
        _required_string(payload["message"], 256)


def parse_envelope(raw: str | bytes) -> EnvelopeV2:
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolV2Error(ValidationCode.MESSAGE_TOO_LARGE)
    try:
        text = encoded.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_object_without_duplicates)
    except ProtocolV2Error:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE) from error
    if not isinstance(value, dict) or _depth(value) > MAX_JSON_DEPTH:
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    fields = set(value)
    if not REQUIRED_FIELDS <= fields or not fields <= REQUIRED_FIELDS | OPTIONAL_FIELDS:
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    if value["v"] != 2 or isinstance(value["v"], bool):
        code = (
            ValidationCode.UNSUPPORTED_VERSION
            if isinstance(value["v"], int)
            else ValidationCode.INVALID_MESSAGE
        )
        raise ProtocolV2Error(code)
    message_type = _required_string(value["type"], 96)
    if message_type not in KNOWN_TYPES:
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    message_id = _required_string(value["message_id"], MAX_ID_CHARS, identifier=True)
    source = _required_string(value["source"], MAX_SOURCE_CHARS, identifier=True)
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    optional_ids: dict[str, str | None] = {}
    for field in ("correlation_id", "causation_id"):
        child = value.get(field)
        optional_ids[field] = (
            _required_string(child, MAX_ID_CHARS, identifier=True) if child is not None else None
        )
    sent_at = value.get("sent_at")
    if sent_at is not None and (not isinstance(sent_at, str) or UTC_RE.fullmatch(sent_at) is None):
        raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
    _validate_payload(message_type, payload)
    return EnvelopeV2(
        message_type,
        message_id,
        source,
        payload,
        optional_ids["correlation_id"],
        optional_ids["causation_id"],
        sent_at,
    )


class ProtocolV2SessionValidator:
    """Aplica replay y revisión monotónica sin ejecutar acciones reales."""

    def __init__(self, max_recent: int = 256) -> None:
        if max_recent <= 0:
            raise ValueError("max_recent must be positive")
        self._max_recent = max_recent
        self._recent: list[str] = []
        self._seen: set[str] = set()
        self._revisions: dict[str, int] = {}

    def validate(self, raw: str | bytes) -> ValidationCode:
        try:
            envelope = parse_envelope(raw)
        except ProtocolV2Error as error:
            return error.code
        if envelope.message_id in self._seen:
            return ValidationCode.REPLAY
        if envelope.message_type == "projection.snapshot":
            revision = int(envelope.payload["projection_version"])
            self._revisions["projection"] = revision
        elif envelope.message_type == "projection.delta":
            aggregate = str(envelope.payload["aggregate"])
            revision = int(envelope.payload["revision"])
            if revision <= self._revisions.get(aggregate, 0):
                return ValidationCode.STALE_REVISION
            self._revisions[aggregate] = revision
        self._seen.add(envelope.message_id)
        self._recent.append(envelope.message_id)
        if len(self._recent) > self._max_recent:
            expired = self._recent.pop(0)
            self._seen.remove(expired)
        return ValidationCode.ACCEPT
