from __future__ import annotations

import time
from collections import OrderedDict, deque
from collections.abc import Callable
from typing import Any

from wyss_panel_bridge.domain.models import FastCommand, PolicyError
from wyss_panel_bridge.domain.policy import validate_fast_command
from wyss_panel_bridge.ports import DeviceGateway, OrchestratorGateway


class SessionService:
    """Yo aplico política, idempotencia y límites antes de tocar el hogar."""

    def __init__(
        self,
        devices: DeviceGateway,
        orchestrator: OrchestratorGateway,
        allowed_entities: frozenset[str],
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self._devices = devices
        self._orchestrator = orchestrator
        self._allowed = allowed_entities
        self._now_ms = now_ms or (lambda: time.monotonic_ns() // 1_000_000)
        self._recent_commands: deque[int] = deque()
        self._responses: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()

    async def initial_snapshot(self) -> dict[str, Any]:
        devices = await self._devices.snapshot(self._allowed)
        return {"v": 1, "type": "state.snapshot", "devices": [item.as_wire() for item in devices]}

    async def handle(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        message_type = str(message.get("type", ""))
        if message.get("v") != 1:
            return [self._error("unsupported_version", "Yo sólo acepto el protocolo v1")]
        if message_type == "hello":
            return [await self.initial_snapshot()]
        if message_type == "command.fast":
            return await self._fast(message)
        if message_type == "intent.submit":
            return await self._intent(message)
        if message_type == "plan.answer":
            return await self._answer(message)
        return [self._error("unknown_message", "Yo no reconozco ese mensaje")]

    async def _fast(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        request_id = self._safe_id(message.get("id"))
        if request_id in self._responses:
            return self._responses[request_id]
        if not self._consume_rate_slot():
            return [self._execution(request_id, "failed", "Yo limité demasiadas órdenes", 0)]
        command = FastCommand(
            request_id=request_id,
            entity_id=str(message.get("entity_id", "")),
            action=str(message.get("action", "")),
            brightness=self._brightness(message.get("brightness")),
        )
        try:
            validate_fast_command(command, self._allowed)
            started = self._now_ms()
            state = await self._devices.execute(command)
            elapsed = max(0, self._now_ms() - started)
            responses = [
                {"v": 1, "type": "state.changed", "device": state.as_wire()},
                self._execution(request_id, "verified", "Yo verifiqué el cambio", elapsed),
            ]
        except (PolicyError, RuntimeError, ValueError) as error:
            responses = [self._execution(request_id, "failed", str(error), 0)]
        self._remember(request_id, responses)
        return responses

    async def _intent(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        request_id = self._safe_id(message.get("id"))
        text = str(message.get("text", "")).strip()
        if not text or len(text) > 500:
            return [self._execution(request_id, "failed", "Yo necesito una intención válida", 0)]
        try:
            plan = await self._orchestrator.submit_intent(request_id, text)
        except RuntimeError as error:
            return [self._execution(request_id, "failed", str(error), 0)]
        if plan is None:
            return [self._execution(request_id, "executing", "Yo inicié la ejecución segura", 0)]
        return [
            {
                "v": 1,
                "type": "plan.proposed",
                "plan_id": plan.plan_id,
                "summary": plan.summary,
                "risk": int(plan.risk),
                "steps": [
                    {"description": step.description, "target": step.target} for step in plan.steps
                ],
                "expires_at_ms": plan.expires_at_ms,
            }
        ]

    async def _answer(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        plan_id = self._safe_id(message.get("plan_id"))
        accepted = message.get("accepted") is True
        try:
            await self._orchestrator.answer_plan(plan_id, accepted)
        except RuntimeError as error:
            return [self._execution(plan_id, "failed", str(error), 0)]
        state = "executing" if accepted else "failed"
        text = "Yo ejecuté el plan confirmado" if accepted else "Yo cancelé el plan"
        return [self._execution(plan_id, state, text, 0)]

    def _consume_rate_slot(self) -> bool:
        now = self._now_ms()
        while self._recent_commands and self._recent_commands[0] <= now - 1_000:
            self._recent_commands.popleft()
        if len(self._recent_commands) >= 12:
            return False
        self._recent_commands.append(now)
        return True

    def _remember(self, request_id: str, responses: list[dict[str, Any]]) -> None:
        self._responses[request_id] = responses
        self._responses.move_to_end(request_id)
        while len(self._responses) > 256:
            self._responses.popitem(last=False)

    @staticmethod
    def _brightness(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Yo recibí un brillo inválido")
        return value

    @staticmethod
    def _safe_id(value: Any) -> str:
        identifier = str(value or "")
        if not identifier or len(identifier) > 96:
            raise ValueError("Yo recibí un identificador inválido")
        return identifier

    @staticmethod
    def _execution(request_id: str, state: str, message: str, rtt: int) -> dict[str, Any]:
        return {
            "v": 1,
            "type": "execution.update",
            "id": request_id,
            "state": state,
            "message": message,
            "round_trip_ms": rtt,
        }

    @staticmethod
    def _error(code: str, message: str) -> dict[str, Any]:
        return {"v": 1, "type": "error", "code": code, "message": message}
