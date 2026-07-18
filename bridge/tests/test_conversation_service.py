from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.application.conversation_service import ConversationService
from wyss_panel_bridge.domain.conversation import (
    ConfirmationResult,
    ConversationError,
    ConversationTurn,
)
from wyss_panel_bridge.domain.models import Plan, PlanStep, RiskLevel


class Clock:
    def __init__(self) -> None:
        self.value = 1_000

    def now(self) -> int:
        return self.value


class FakeWyss:
    def __init__(
        self,
        risk: RiskLevel | None = None,
        *,
        reevaluated: bool = True,
        target: str = "light.living",
    ) -> None:
        self.risk = risk
        self.reevaluated = reevaluated
        self.target = target
        self.confirmations = 0
        self.turns = 0

    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return (await self.submit_turn(request_id, text, "legacy")).plan

    async def answer_plan(self, plan_id: str, accepted: bool) -> None:
        return None

    async def submit_turn(self, request_id: str, text: str, source: str) -> ConversationTurn:
        self.turns += 1
        plan = None
        if self.risk is not None:
            plan = Plan(
                "plan:study",
                "Preparar estudio",
                self.risk,
                (PlanStep("Ajustar", self.target),),
                5_000,
            )
        return ConversationTurn(f"Respuesta para {source}", "verified", plan)

    async def confirm_turn(
        self,
        plan_id: str,
        accepted: bool,
        confirmation: str,
        expected_revision: int,
        source: str,
    ) -> ConfirmationResult:
        self.confirmations += 1
        await asyncio.sleep(0)
        return ConfirmationResult("Plan ejecutado", "verified", self.reevaluated)


def _service(
    path: Path,
    gateway: FakeWyss,
    clock: Clock,
    *,
    streaming: bool = True,
) -> tuple[ConversationService, SqliteEventStore]:
    store = SqliteEventStore(path)
    return (
        ConversationService(
            gateway,
            store,
            streaming_enabled=streaming,
            now_ms=clock.now,
        ),
        store,
    )


@pytest.mark.asyncio
async def test_risk_a_projects_thinking_response_and_verified(tmp_path: Path) -> None:
    service, store = _service(tmp_path / "events.sqlite3", FakeWyss(), Clock())

    await service.submit("pc:desk", "request:a", "Estado del hogar", "text")

    events = store.after(0, 20)
    assert [event.event_type for event in events] == [
        "assistant.state.changed",
        "assistant.response.delta",
        "assistant.response.completed",
        "assistant.state.changed",
    ]
    assert events[0].payload["state"] == "thinking"
    assert events[-1].payload["state"] == "verified"


@pytest.mark.asyncio
async def test_intent_replay_is_idempotent_and_changed_text_conflicts(tmp_path: Path) -> None:
    gateway = FakeWyss()
    service, store = _service(tmp_path / "events.sqlite3", gateway, Clock())

    await service.submit("pc:desk", "request:same", "Estado", "text")
    await service.submit("pc:desk", "request:same", "Estado", "text")
    with pytest.raises(ConversationError) as conflict:
        await service.submit("pc:desk", "request:same", "Otro estado", "text")

    assert conflict.value.code == "conflict"
    assert gateway.turns == 1
    assert len(store.after(0, 20)) == 4


@pytest.mark.asyncio
async def test_streaming_rollback_keeps_complete_response_and_policy(tmp_path: Path) -> None:
    service, store = _service(tmp_path / "events.sqlite3", FakeWyss(), Clock(), streaming=False)

    await service.submit("panel:living", "request:fallback", "Respondé completo", "text")

    events = store.after(0, 20)
    assert "assistant.response.delta" not in {event.event_type for event in events}
    completed = next(
        event for event in events if event.event_type == "assistant.response.completed"
    )
    assert completed.payload["streamed"] is False
    assert completed.payload["message"] == "Respuesta para panel:living"


@pytest.mark.asyncio
async def test_b_confirmation_is_ttl_cas_and_first_valid_answer_wins(tmp_path: Path) -> None:
    clock = Clock()
    gateway = FakeWyss(RiskLevel.B)
    service, store = _service(tmp_path / "events.sqlite3", gateway, clock)
    await service.submit("pc:desk", "request:b", "Prepará estudio", "text")

    with pytest.raises(ConversationError) as overlapping:
        await service.submit("android:phone", "request:b:2", "Otro plan", "text")

    results = await asyncio.gather(
        service.answer("android:phone", "plan:study", "approve", "CONFIRMAR", 1),
        service.answer("panel:living", "plan:study", "approve", "CONFIRMAR", 1),
        return_exceptions=True,
    )

    assert sum(result is None for result in results) == 1
    assert overlapping.value.code == "confirmation_required"
    loser = next(result for result in results if isinstance(result, ConversationError))
    assert loser.code == "already_resolved"
    assert gateway.confirmations == 1
    event_types = [event.event_type for event in store.after(0, 30)]
    assert event_types.count("plan.resolved") == 1
    assert event_types[-1] == "assistant.state.changed"


@pytest.mark.asyncio
async def test_expired_or_unconfirmed_plan_never_reaches_wyss_execution(tmp_path: Path) -> None:
    clock = Clock()
    gateway = FakeWyss(RiskLevel.C)
    service, _ = _service(tmp_path / "events.sqlite3", gateway, clock)
    await service.submit("pc:desk", "request:c", "Acción sensible", "text")

    with pytest.raises(ConversationError, match="CONFIRMAR") as missing_word:
        await service.answer("panel:living", "plan:study", "approve", "confirmar", 1)
    clock.value = 5_001
    with pytest.raises(ConversationError, match="venció") as expired:
        await service.answer("android:phone", "plan:study", "approve", "CONFIRMAR", 1)

    assert missing_word.value.code == "confirmation_required"
    assert expired.value.code == "confirmation_required"
    assert gateway.confirmations == 0


@pytest.mark.asyncio
async def test_rejection_is_reevaluated_and_returns_shared_session_to_idle(tmp_path: Path) -> None:
    clock = Clock()
    gateway = FakeWyss(RiskLevel.B)
    service, store = _service(tmp_path / "events.sqlite3", gateway, clock)
    await service.submit("pc:desk", "request:reject", "No ejecutar", "text")

    await service.answer("android:phone", "plan:study", "reject", "", 1)

    events = store.after(0, 30)
    assert gateway.confirmations == 1
    assert events[-2].event_type == "plan.resolved"
    assert events[-2].payload["policy_reevaluated"] is True
    assert events[-1].payload["state"] == "idle"


@pytest.mark.asyncio
async def test_risk_d_and_missing_policy_reevaluation_fail_closed(tmp_path: Path) -> None:
    clock = Clock()
    risk_d, _ = _service(tmp_path / "d.sqlite3", FakeWyss(RiskLevel.D), clock)
    with pytest.raises(ConversationError) as rejected:
        await risk_d.submit("pc:desk", "request:d", "Acción prohibida", "text")
    assert rejected.value.code == "policy_rejected"

    gateway = FakeWyss(RiskLevel.B, reevaluated=False)
    service, store = _service(tmp_path / "reeval.sqlite3", gateway, clock)
    await service.submit("pc:desk", "request:reeval", "Prepará estudio", "text")
    with pytest.raises(ConversationError, match="reevaluación") as no_reevaluation:
        await service.answer("panel:living", "plan:study", "approve", "CONFIRMAR", 1)

    assert no_reevaluation.value.code == "policy_rejected"
    assert "plan.resolved" not in {event.event_type for event in store.after(0, 30)}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "intent",
    [
        "Creá una reunión mañana a las diez",
        "Mové la reunión de mañana a las once",
        "Eliminá la reunión de mañana",
    ],
)
async def test_calendar_mutations_always_cross_wyss_plan_policy_and_confirmation(
    tmp_path: Path, intent: str
) -> None:
    gateway = FakeWyss(RiskLevel.B, target="calendar.primary")
    service, store = _service(tmp_path / "events.sqlite3", gateway, Clock())

    await service.submit("panel:living", f"request:{hash(intent)}", intent, "text")
    proposed = next(event for event in store.after(0, 20) if event.event_type == "plan.proposed")
    await service.answer("panel:living", "plan:study", "approve", "CONFIRMAR", 1)

    assert proposed.payload["risk"] == "B"
    assert proposed.payload["steps"] == [{"description": "Ajustar", "target": "calendar.primary"}]
    assert gateway.confirmations == 1
