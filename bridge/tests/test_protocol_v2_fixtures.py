from __future__ import annotations

from pathlib import Path

from wyss_panel_bridge.domain.protocol_v2 import ProtocolV2SessionValidator

FIXTURES = Path(__file__).parents[2] / "tests/fixtures/protocol/v2/cases.jsonl"


def _generated(name: str) -> str:
    if name == "oversized":
        return "{" + (" " * 8192) + "}"
    if name == "deep":
        nested = '{"child":' * 9 + "null" + "}" * 9
        return (
            '{"v":2,"type":"session.heartbeat","message_id":"msg-deep",'
            f'"source":"panel:living","payload":{nested}}}'
        )
    raise AssertionError(f"unknown fixture generator: {name}")


def test_shared_protocol_v2_fixtures() -> None:
    validator = ProtocolV2SessionValidator()
    observed = 0
    for line in FIXTURES.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        case_id, expected, raw = line.split("\t", 2)
        if raw.startswith("@generate:"):
            raw = _generated(raw.removeprefix("@generate:"))
        assert validator.validate(raw).value == expected, case_id
        observed += 1
    assert observed >= 17
