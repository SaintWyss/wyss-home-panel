"""Proyecta conversación y aplica la segunda muralla sin reemplazar la política de Wyss."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from wyss_panel_bridge.domain.conversation import ConversationError
from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.models import Plan, RiskLevel
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports import WyssGatewayPort
from wyss_panel_bridge.ports_v2 import EventStorePort

EventSink = Callable[[ProjectionEvent], Awaitable[None]]


@dataclass(slots=True)
class _PendingPlan:
    plan: Plan
    revision: int = 1
    resolved: bool = False


class ConversationService:
    def __init__(
        self,
        gateway: WyssGatewayPort,
        events: EventStorePort,
        *,
        streaming_enabled: bool = True,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self._gateway = gateway
        self._events = events
        self._streaming = streaming_enabled
        self._now_ms = now_ms or (lambda: time.monotonic_ns() // 1_000_000)
        self._pending: dict[str, _PendingPlan] = {}
        self._session_lock = asyncio.Lock()
        self._locks: dict[str, asyncio.Lock] = {}
        self._request_locks: dict[str, asyncio.Lock] = {}
        self._requests: dict[str, str] = {}
        self._sink: EventSink | None = None

    def set_event_sink(self, sink: EventSink) -> None:
        self._sink = sink

    async def submit(
        self,
        source: str,
        request_id: str,
        text: str,
        input_kind: str,
    ) -> None:
        if not request_id or not text or len(text) > 1000 or input_kind not in {"text", "voice"}:
            raise ConversationError("invalid_message", "Intención inválida")
        fingerprint = hashlib.sha256(f"{source}\0{input_kind}\0{text}".encode()).hexdigest()
        request_lock = self._request_locks.setdefault(request_id, asyncio.Lock())
        async with self._session_lock:
            async with request_lock:
                previous = self._requests.get(request_id)
                if previous is not None:
                    if previous != fingerprint:
                        raise ConversationError("conflict", "request_id reutilizado con otro texto")
                    return
                active = next(
                    (
                        pending
                        for pending in self._pending.values()
                        if not pending.resolved and pending.plan.expires_at_ms > self._now_ms()
                    ),
                    None,
                )
                if active is not None:
                    raise ConversationError(
                        "confirmation_required", "Hay un plan pendiente de confirmación"
                    )
                try:
                    await self._submit_once(source, request_id, text, input_kind)
                except ConversationError as error:
                    if error.code == "provider_unavailable":
                        self._requests.pop(request_id, None)
                    else:
                        self._requests[request_id] = fingerprint
                    raise
                self._requests[request_id] = fingerprint

    async def _submit_once(
        self,
        source: str,
        request_id: str,
        text: str,
        input_kind: str,
    ) -> None:
        del input_kind
        await self._state(request_id, "thinking", "Wyss está pensando", "thinking")
        try:
            turn = await self._gateway.submit_turn(request_id, text, source)
        except RuntimeError as error:
            await self._state(request_id, "failed", str(error), "provider-failed")
            raise ConversationError("provider_unavailable", str(error)) from error

        if turn.text:
            await self._response(request_id, turn.text)
        plan = turn.plan
        if plan is not None and plan.risk == RiskLevel.D:
            await self._state(request_id, "failed", "La política D no admite bypass", "risk-d")
            raise ConversationError("policy_rejected", "La política D no admite bypass")
        if plan is not None and plan.risk in {RiskLevel.B, RiskLevel.C}:
            if plan.expires_at_ms <= self._now_ms():
                await self._state(request_id, "failed", "El plan ya venció", "expired")
                raise ConversationError("confirmation_required", "El plan ya venció")
            self._pending[plan.plan_id] = _PendingPlan(plan)
            await self._publish(
                "plan.proposed",
                {
                    "state": "awaiting_confirmation",
                    "request_id": request_id,
                    "plan_id": plan.plan_id,
                    "summary": plan.summary,
                    "risk": plan.risk.name,
                    "steps": [
                        {"description": step.description, "target": step.target}
                        for step in plan.steps
                    ],
                    "expires_in_ms": min(plan.expires_at_ms - self._now_ms(), 300_000),
                    "plan_revision": 1,
                },
                f"conversation:{request_id}:plan",
                request_id,
            )
            return
        if plan is not None:
            await self._state(request_id, "failed", "Wyss devolvió un plan A pendiente", "bad-a")
            raise ConversationError("internal_error", "Wyss devolvió un plan A pendiente")
        await self._state(request_id, turn.state, turn.text, "terminal")

    async def answer(
        self,
        source: str,
        plan_id: str,
        decision: str,
        confirmation: str,
        expected_revision: int,
    ) -> None:
        async with self._session_lock:
            await self._answer_once(source, plan_id, decision, confirmation, expected_revision)

    async def _answer_once(
        self,
        source: str,
        plan_id: str,
        decision: str,
        confirmation: str,
        expected_revision: int,
    ) -> None:
        accepted = decision == "approve"
        if decision not in {"approve", "reject"}:
            raise ConversationError("invalid_message", "Decisión inválida")
        if accepted and confirmation != "CONFIRMAR":
            raise ConversationError("confirmation_required", "Escribí CONFIRMAR")
        lock = self._locks.setdefault(plan_id, asyncio.Lock())
        async with lock:
            pending = self._pending.get(plan_id)
            if pending is None or pending.resolved:
                raise ConversationError("already_resolved", "El plan ya fue resuelto")
            if expected_revision != pending.revision:
                raise ConversationError("conflict", "La revisión del plan cambió")
            if pending.plan.expires_at_ms <= self._now_ms():
                pending.resolved = True
                await self._resolve_event(pending, "expired", source)
                await self._state(plan_id, "failed", "La confirmación venció", "expired")
                raise ConversationError("confirmation_required", "La confirmación venció")
            if pending.plan.risk == RiskLevel.D:
                pending.resolved = True
                await self._resolve_event(pending, "rejected", source)
                raise ConversationError("policy_rejected", "La política D no admite bypass")
            try:
                result = await self._gateway.confirm_turn(
                    plan_id,
                    accepted,
                    confirmation,
                    expected_revision,
                    source,
                )
            except RuntimeError as error:
                raise ConversationError("provider_unavailable", str(error)) from error
            if not result.policy_reevaluated:
                raise ConversationError(
                    "policy_rejected", "Wyss no acreditó la reevaluación de política"
                )
            pending.resolved = True
            await self._resolve_event(pending, decision, source)
            if not accepted:
                await self._state(plan_id, "idle", result.text, "rejected")
                return
            await self._state(plan_id, "executing", "Wyss está ejecutando", "executing")
            if result.text:
                await self._response(plan_id, result.text)
            await self._state(plan_id, result.state, result.text, "terminal")

    async def _response(self, request_id: str, text: str) -> None:
        chunks = [text]
        if self._streaming:
            chunks = [text[index : index + 160] for index in range(0, len(text), 160)] or [""]
            for index, chunk in enumerate(chunks):
                await self._publish(
                    "assistant.response.delta",
                    {"request_id": request_id, "delta": chunk, "index": index},
                    f"conversation:{request_id}:delta:{index}",
                    request_id,
                )
        await self._publish(
            "assistant.response.completed",
            {"request_id": request_id, "message": text, "streamed": self._streaming},
            f"conversation:{request_id}:response",
            request_id,
        )

    async def _state(self, request_id: str, state: str, message: str, suffix: str) -> None:
        await self._publish(
            "assistant.state.changed",
            {"request_id": request_id, "state": state, "message": message[:1000]},
            f"conversation:{request_id}:state:{suffix}",
            request_id,
        )

    async def _resolve_event(self, pending: _PendingPlan, decision: str, source: str) -> None:
        await self._publish(
            "plan.resolved",
            {
                "plan_id": pending.plan.plan_id,
                "decision": decision,
                "resolved_by": source,
                "plan_revision": pending.revision + 1,
                "policy_reevaluated": decision not in {"expired", "rejected"},
            },
            f"conversation:{pending.plan.plan_id}:resolved",
            pending.plan.plan_id,
        )

    async def _publish(
        self,
        event_type: str,
        payload: dict[str, object],
        idempotency_key: str,
        correlation_id: str,
    ) -> ProjectionEvent:
        event = self._events.append(
            EventDraft(
                event_type,
                "assistant",
                payload,
                correlation_id=correlation_id,
                causation_id=correlation_id,
            ),
            idempotency_key,
        )
        if self._sink is not None:
            await self._sink(event)
        return event
