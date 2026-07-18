from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.conversation import (
    ConfirmationResult,
    ConversationTurn,
    TerminalState,
)
from wyss_panel_bridge.domain.models import Plan, PlanStep, RiskLevel


class WyssGateway:
    """Yo conservo temporalmente el adapter HTTP v1 detrás de un feature flag."""

    def __init__(self, url: str, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )

    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return (await self.submit_turn(request_id, text, "home-panel")).plan

    async def submit_turn(
        self, request_id: str, text: str, source: str, input_kind: str = "text"
    ) -> ConversationTurn:
        del input_kind
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
                parameters=(
                    cast(dict[str, Any], item["parameters"])
                    if isinstance(item.get("parameters"), dict)
                    else {}
                ),
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
            revision=max(1, int(raw.get("revision", 1))),
        )

    async def answer_plan(
        self, plan_id: str, accepted: bool, risk: int, expected_revision: int
    ) -> None:
        del risk, expected_revision
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
            str(raw.get("outcome", "resolved")),
            int(raw["revision"]) if isinstance(raw.get("revision"), int) else None,
        )


class WyssUnixGateway:
    """Yo adapto Home Edge al JSON-RPC autenticado de la autoridad Wyss."""

    def __init__(
        self,
        socket_path: Path,
        *,
        timeout_seconds: float = 15.0,
        max_response_bytes: int = 65_536,
    ) -> None:
        if not socket_path.is_absolute():
            raise ValueError("Yo exijo una ruta absoluta para el socket de Wyss")
        if timeout_seconds <= 0 or max_response_bytes < 1024:
            raise ValueError("Yo recibí límites inválidos para el adapter Wyss")
        self._socket_path = socket_path
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes

    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return (await self.submit_turn(request_id, text, "home-panel", "text")).plan

    async def submit_turn(
        self,
        request_id: str,
        text: str,
        source: str,
        input_kind: str = "text",
    ) -> ConversationTurn:
        message_digest = hashlib.sha256(f"{source}\0{request_id}".encode()).hexdigest()[:24]
        raw = await self._rpc(
            "home.intent",
            {
                "message_id": f"intent:{message_digest}",
                "request_id": request_id,
                "source": source,
                "text": text,
                "input": input_kind,
            },
            request_id,
        )
        try:
            plan = WyssGateway._plan(raw)
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("Yo recibí una respuesta inválida de la autoridad Wyss") from error
        outcome = str(raw.get("outcome", "failed"))
        state: TerminalState = (
            "failed"
            if outcome in {"failed", "rejected", "policy_rejected", "degraded"}
            else "verified"
        )
        text_result = str(
            raw.get("response")
            or raw.get("answer")
            or raw.get("message")
            or raw.get("summary")
            or "Wyss respondió"
        )
        return ConversationTurn(text_result[:1000], state, plan)

    async def answer_plan(
        self, plan_id: str, accepted: bool, risk: int, expected_revision: int
    ) -> None:
        confirmation = "CONFIRMAR" if accepted and risk == int(RiskLevel.C) else "s"
        result = await self.confirm_turn(
            plan_id,
            accepted,
            confirmation if accepted else "",
            expected_revision,
            "home-panel",
        )
        if result.outcome != "resolved":
            raise RuntimeError("La autoridad Wyss rechazó la respuesta del plan")

    async def confirm_turn(
        self,
        plan_id: str,
        accepted: bool,
        confirmation: str,
        expected_revision: int,
        source: str,
    ) -> ConfirmationResult:
        decision = "approve" if accepted else "reject"
        digest = hashlib.sha256(
            f"{source}\0{plan_id}\0{decision}\0{confirmation}\0{expected_revision}".encode()
        ).hexdigest()[:24]
        raw = await self._rpc(
            "home.plan.answer",
            {
                "message_id": f"answer:{digest}",
                "plan_id": plan_id,
                "decision": decision,
                "confirmation": confirmation,
                "expected_revision": expected_revision,
                "source": source,
            },
            f"answer:{digest}",
        )
        outcome = str(raw.get("outcome", "failed"))
        state: TerminalState = (
            "verified"
            if accepted and outcome == "resolved" and raw.get("status") == "verified"
            else "failed"
        )
        text = str(raw.get("message") or "Plan resuelto por Wyss")
        return ConfirmationResult(
            text[:1000],
            state,
            raw.get("policy_reevaluated") is True,
            outcome,
            int(raw["revision"]) if isinstance(raw.get("revision"), int) else None,
        )

    async def _rpc(
        self,
        method: str,
        params: dict[str, object],
        request_id: str,
    ) -> dict[str, Any]:
        request = (
            json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        writer: asyncio.StreamWriter | None = None
        try:
            reader, connected_writer = await asyncio.wait_for(
                asyncio.open_unix_connection(
                    self._socket_path,
                    limit=self._max_response_bytes,
                ),
                timeout=self._timeout,
            )
            writer = connected_writer
            connected_writer.write(request)
            await asyncio.wait_for(connected_writer.drain(), timeout=self._timeout)
            encoded = await asyncio.wait_for(reader.readline(), timeout=self._timeout)
        except (OSError, TimeoutError, ValueError) as error:
            raise RuntimeError("Yo no pude comunicarme con la autoridad Wyss") from error
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
        if not encoded or len(encoded) >= self._max_response_bytes:
            raise RuntimeError("Yo recibí una respuesta inválida de la autoridad Wyss")
        try:
            decoded = json.loads(encoded)
        except (json.JSONDecodeError, RecursionError) as error:
            raise RuntimeError("Yo recibí una respuesta inválida de la autoridad Wyss") from error
        if not isinstance(decoded, dict) or decoded.get("id") != request_id:
            raise RuntimeError("Yo recibí una respuesta no correlacionada de la autoridad Wyss")
        response = cast(dict[str, Any], decoded)
        if "error" in response or not isinstance(response.get("result"), dict):
            raise RuntimeError("La autoridad Wyss rechazó la solicitud")
        return cast(dict[str, Any], response["result"])
