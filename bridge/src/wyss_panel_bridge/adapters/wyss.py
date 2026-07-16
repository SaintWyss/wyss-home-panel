from __future__ import annotations

import time

import httpx

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
        response = await self._client.post(
            "/api/ask", json={"message": text, "request_id": request_id, "source": "home-panel"}
        )
        if response.is_error:
            raise RuntimeError(f"Yo recibí HTTP {response.status_code} de Wyss")
        raw = response.json()
        pending_id = raw.get("pending_id") or raw.get("plan_id")
        if not pending_id:
            return None
        risk_value = str(raw.get("risk", "B")).upper()
        risk = RiskLevel[risk_value] if risk_value in RiskLevel.__members__ else RiskLevel.B
        raw_steps = raw.get("steps") or raw.get("plan", {}).get("steps") or []
        steps = tuple(
            PlanStep(
                description=str(item.get("description") or item.get("action") or "Paso"),
                target=str(item.get("target") or "Wyss"),
            )
            for item in raw_steps
            if isinstance(item, dict)
        )
        expires_at_ms = int(
            raw.get("expires_at_ms") or time.monotonic_ns() // 1_000_000 + 120_000
        )
        return Plan(
            plan_id=str(pending_id),
            summary=str(raw.get("summary") or raw.get("message") or "Plan preparado por Wyss"),
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
