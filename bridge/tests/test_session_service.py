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
            revision=self.state.revision + 1,
        )
        return self.state


class FakeWyss:
    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return Plan("plan-1", text, RiskLevel.B, (PlanStep("Apagar", "light.living"),), 5000)

    async def answer_plan(self, plan_id: str, accepted: bool) -> None:
        return None


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
async def test_intent_becomes_a_confirmable_plan() -> None:
    service = SessionService(FakeDevices(), FakeWyss(), frozenset({"light.living"}))
    responses = await service.handle(
        {"v": 1, "type": "intent.submit", "id": "intent-1", "text": "Apagá el living"}
    )
    assert responses[0]["type"] == "plan.proposed"
    assert responses[0]["risk"] == 1
    assert responses[0]["steps"][0]["target"] == "light.living"
