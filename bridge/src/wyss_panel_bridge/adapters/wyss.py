from __future__ import annotations

import time
from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.conversation import (
    ConfirmationResult,
    ConversationTurn,
    TerminalState,
)
from wyss_panel_bridge.domain.models import Plan, PlanStep, RiskLevel


class WyssGateway:
    """Yo traduzco la pantalla al contrato público del orquestador Wyss."""

    def __init__(self, url: str, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )

    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return (await self.submit_turn(request_id, text, "home-panel")).plan

    async def submit_turn(self, request_id: str, text: str, source: str) -> ConversationTurn:
        response = await self._client.post(
            "/api/ask", json={"message": text, "request_id": request_id, "source": source}
        )
        if response.is_error:
            raise RuntimeError(f"Yo recibí HTTP {response.status_code} de Wyss")
        decoded = response.json()
        if not isinstance(decoded, dict):
            raise RuntimeError("Yo recibí una respuesta inválida de Wyss")
        raw = cast(dict[str, Any], decoded)
        plan = self._plan(raw)
        state: TerminalState = (
            "failed" if str(raw.get("status", "")).lower() == "failed" else "verified"
        )
        text_result = str(
            raw.get("response") or raw.get("answer") or raw.get("message") or "Wyss respondió"
        )
        return ConversationTurn(text_result[:1000], state, plan)

    @staticmethod
    def _plan(raw: dict[str, Any]) -> Plan | None:
        pending_id = raw.get("pending_id") or raw.get("plan_id")
        if not pending_id:
            return None
        risk_value = str(raw.get("risk", "B")).upper()
        risk = RiskLevel[risk_value] if risk_value in RiskLevel.__members__ else RiskLevel.B
        raw_plan = raw.get("plan")
        nested_steps = raw_plan.get("steps") if isinstance(raw_plan, dict) else None
        raw_steps = raw.get("steps") or nested_steps or []
        steps = tuple(
            PlanStep(
                description=str(item.get("description") or item.get("action") or "Paso")[:160],
                target=str(item.get("target") or "Wyss")[:96],
            )
            for item in raw_steps[:4]
            if isinstance(item, dict)
        )
        now_ms = time.monotonic_ns() // 1_000_000
        if "expires_in_ms" in raw:
            ttl_ms = max(0, min(int(raw["expires_in_ms"]), 300_000))
            expires_at_ms = now_ms + ttl_ms
        else:
            candidate = int(raw.get("expires_at_ms") or 0)
            expires_at_ms = (
                candidate if now_ms <= candidate <= now_ms + 300_000 else now_ms + 120_000
            )
        return Plan(
            plan_id=str(pending_id),
            summary=str(raw.get("summary") or raw.get("message") or "Plan preparado por Wyss")[
                :400
            ],
            risk=risk,
            steps=steps,
            expires_at_ms=expires_at_ms,
        )

    async def answer_plan(self, plan_id: str, accepted: bool) -> None:
        response = await self._client.post(
            f"/api/confirm/{plan_id}", json={"confirmed": accepted, "source": "home-panel"}
        )
        if response.is_error:
            raise RuntimeError(f"Yo no pude responder el plan: HTTP {response.status_code}")

    async def confirm_turn(
        self,
        plan_id: str,
        accepted: bool,
        confirmation: str,
        expected_revision: int,
        source: str,
    ) -> ConfirmationResult:
        response = await self._client.post(
            f"/api/confirm/{plan_id}",
            json={
                "confirmed": accepted,
                "confirmation": confirmation,
                "expected_revision": expected_revision,
                "source": source,
            },
        )
        if response.is_error:
            raise RuntimeError(f"Yo no pude responder el plan: HTTP {response.status_code}")
        decoded = response.json()
        if not isinstance(decoded, dict):
            raise RuntimeError("Yo recibí una confirmación inválida de Wyss")
        raw = cast(dict[str, Any], decoded)
        state: TerminalState = (
            "failed" if str(raw.get("status", "")).lower() == "failed" else "verified"
        )
        text = str(raw.get("response") or raw.get("message") or "Plan resuelto por Wyss")
        return ConfirmationResult(
            text[:1000],
            state,
            raw.get("policy_reevaluated") is True,
        )
