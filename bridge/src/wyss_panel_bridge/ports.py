from __future__ import annotations

from typing import Protocol

from wyss_panel_bridge.domain.models import DeviceState, FastCommand, Plan


class DeviceGateway(Protocol):
    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]: ...

    async def execute(self, command: FastCommand) -> DeviceState: ...


class OrchestratorGateway(Protocol):
    async def submit_intent(self, request_id: str, text: str) -> Plan | None: ...

    async def answer_plan(self, plan_id: str, accepted: bool) -> None: ...


class MonotonicClock(Protocol):
    def milliseconds(self) -> int: ...
