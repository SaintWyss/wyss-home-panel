from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from wyss_panel_bridge.application.session_service import SessionService
from wyss_panel_bridge.domain.models import DeviceState, FastCommand, Plan, PlanStep, RiskLevel

FIXTURES = Path(__file__).parents[2] / "tests" / "fixtures" / "protocol" / "v1" / "cases.json"


class FixtureDevices:
    def __init__(self) -> None:
        self.state = DeviceState("light.fixture", "Fixture", True, False, 40, 1)
        self.calls = 0

    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]:
        return [self.state] if self.state.entity_id in entities else []

    async def execute(self, command: FastCommand) -> DeviceState:
        self.calls += 1
        self.state = replace(
            self.state,
            on=command.action != "turn_off",
            brightness=command.brightness or self.state.brightness,
            revision=self.state.revision + 1,
        )
        return self.state


class FixtureWyss:
    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return Plan(
            "fixture-plan",
            text,
            RiskLevel.B,
            (PlanStep("Apagar", "light.fixture"),),
            5_000,
        )

    async def answer_plan(
        self, plan_id: str, accepted: bool, risk: int, expected_revision: int
    ) -> None:
        return None


def _cases() -> list[dict[str, Any]]:
    payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 1
    cases = payload["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    return cases


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _cases(), ids=lambda case: str(case["id"]))
async def test_protocol_v1_golden_cases(case: dict[str, Any]) -> None:
    devices = FixtureDevices()
    service = SessionService(
        devices,
        FixtureWyss(),
        frozenset({"light.fixture"}),
        now_ms=lambda: 1_000,
    )
    responses = await service.handle(case["message"])
    assert [item["type"] for item in responses] == case["expected_types"]
    if expected_code := case.get("expected_code"):
        assert responses[0]["code"] == expected_code
    if case.get("idempotent"):
        assert await service.handle(case["message"]) == responses
        assert devices.calls == 1
