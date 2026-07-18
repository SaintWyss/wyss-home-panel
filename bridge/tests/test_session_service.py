from __future__ import annotations

from dataclasses import replace

import pytest

from wyss_panel_bridge.application.session_service import SessionService
from wyss_panel_bridge.domain.models import DeviceState, FastCommand, Plan, PlanStep, RiskLevel


class FakeDevices:
    def __init__(self) -> None:
        self.state = DeviceState("light.living", "Living", True, False, 40, 1)
        self.calls = 0

    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]:
        return [self.state] if self.state.entity_id in entities else []

    async def execute(self, command: FastCommand) -> DeviceState:
        self.calls += 1
        on = command.action != "turn_off"
        brightness = command.brightness if command.brightness is not None else self.state.brightness
        self.state = replace(
            self.state,
            on=on,
            brightness=brightness,
            rgb=command.rgb if command.rgb is not None else self.state.rgb,
            revision=self.state.revision + 1,
        )
        return self.state


class FakeWyss:
    def __init__(self) -> None:
        self.answer: tuple[str, bool, int, int] | None = None

    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return Plan(
            "plan-1",
            text,
            RiskLevel.B,
            (PlanStep("Apagar", "light.living"),),
            5000,
            revision=7,
        )

    async def answer_plan(
        self, plan_id: str, accepted: bool, risk: int, expected_revision: int
    ) -> None:
        self.answer = (plan_id, accepted, risk, expected_revision)


@pytest.mark.asyncio
async def test_fast_command_is_verified_and_idempotent() -> None:
    devices = FakeDevices()
    service = SessionService(devices, FakeWyss(), frozenset({"light.living"}))
    message = {
        "v": 1,
        "type": "command.fast",
        "id": "one",
        "entity_id": "light.living",
        "action": "set_brightness",
        "brightness": 72,
    }
    first = await service.handle(message)
    second = await service.handle(message)
    assert first == second
    assert devices.calls == 1
    assert first[0]["device"]["brightness"] == 72
    assert first[1]["state"] == "verified"


@pytest.mark.asyncio
async def test_policy_rejects_an_unlisted_entity() -> None:
    service = SessionService(FakeDevices(), FakeWyss(), frozenset({"light.living"}))
    responses = await service.handle(
        {
            "v": 1,
            "type": "command.fast",
            "id": "blocked",
            "entity_id": "lock.front_door",
            "action": "toggle",
        }
    )
    assert responses[0]["state"] == "failed"
    assert "autorizada" in responses[0]["message"]


@pytest.mark.asyncio
async def test_v1_compatibility_path_accepts_verified_rgb_color() -> None:
    devices = FakeDevices()
    service = SessionService(devices, FakeWyss(), frozenset({"light.living"}))

    responses = await service.handle(
        {
            "v": 1,
            "type": "command.fast",
            "id": "color-one",
            "entity_id": "light.living",
            "action": "set_color",
            "rgb": 0x3366CC,
        }
    )

    assert responses[0]["device"]["rgb"] == 0x3366CC
    assert responses[1]["state"] == "verified"


@pytest.mark.asyncio
async def test_intent_becomes_a_confirmable_plan() -> None:
    gateway = FakeWyss()
    service = SessionService(
        FakeDevices(),
        gateway,
        frozenset({"light.living"}),
        now_ms=lambda: 1000,
    )
    responses = await service.handle(
        {"v": 1, "type": "intent.submit", "id": "intent-1", "text": "Apagá el living"}
    )
    assert responses[0]["type"] == "plan.proposed"
    assert responses[0]["risk"] == 1
    assert responses[0]["steps"][0]["target"] == "light.living"
    assert responses[0]["expires_in_ms"] == 4000
    assert responses[0]["revision"] == 7

    answered = await service.handle(
        {"v": 1, "type": "plan.answer", "plan_id": "plan-1", "accepted": True}
    )

    assert answered[0]["state"] == "executing"
    assert gateway.answer == ("plan-1", True, int(RiskLevel.B), 7)
