from __future__ import annotations

import json
import random

import pytest

from wyss_panel_bridge.domain.protocol_v2 import (
    ProtocolV2Error,
    ValidationCode,
    parse_envelope,
)


def _heartbeat(**updates: object) -> str:
    envelope: dict[str, object] = {
        "v": 2,
        "type": "session.heartbeat",
        "message_id": "security:fuzz:heartbeat",
        "source": "panel:living",
        "payload": {},
    }
    envelope.update(updates)
    return json.dumps(envelope, separators=(",", ":"))


def test_protocol_parser_fuzz_never_escapes_the_closed_error_contract() -> None:
    generator = random.Random(0x57595353)  # noqa: S311 - corpus determinista, no criptografía
    corpus: list[str | bytes] = [
        b"[" * 2_000 + b"]" * 2_000,
        b'{"v":' + b"9" * 4_000 + b"}",
        "\ud800",
        _heartbeat(),
    ]
    corpus.extend(generator.randbytes(generator.randrange(0, 513)) for _ in range(4_000))

    for raw in corpus:
        try:
            parse_envelope(raw)
        except ProtocolV2Error as error:
            assert error.code in {
                ValidationCode.INVALID_MESSAGE,
                ValidationCode.MESSAGE_TOO_LARGE,
                ValidationCode.UNSUPPORTED_VERSION,
            }


@pytest.mark.parametrize("version", [0, 1, 3, 99, "2", True])
def test_protocol_rejects_downgrade_and_type_confusion(version: object) -> None:
    with pytest.raises(ProtocolV2Error) as captured:
        parse_envelope(_heartbeat(v=version))

    expected = (
        ValidationCode.UNSUPPORTED_VERSION
        if isinstance(version, int) and not isinstance(version, bool)
        else ValidationCode.INVALID_MESSAGE
    )
    assert captured.value.code == expected


def test_protocol_rejects_command_injection_before_policy_or_adapter() -> None:
    malicious = {
        "v": 2,
        "type": "home.command",
        "message_id": "security:injection",
        "source": "panel:living",
        "payload": {
            "request_id": "security:injection",
            "idempotency_key": "security:injection",
            "entity_id": "light.living'; DROP TABLE events;--",
            "action": "turn_on",
        },
    }

    with pytest.raises(ProtocolV2Error) as captured:
        parse_envelope(json.dumps(malicious))

    assert captured.value.code == ValidationCode.INVALID_MESSAGE
