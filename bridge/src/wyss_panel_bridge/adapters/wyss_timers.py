"""Consulta el scheduler interno de Wyss sin ejecutar timers en Home Edge."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.timers import Timer, TimerError, TimerSnapshot, TimerStatus


class WyssTimerGateway:
    def __init__(
        self,
        url: str,
        token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
            transport=transport,
        )

    async def snapshot(self) -> TimerSnapshot:
        try:
            response = await self._client.get("/api/home/timers")
        except httpx.HTTPError as error:
            raise TimerError("provider_unavailable", "Wyss timers no respondió") from error
        if response.status_code in {401, 403}:
            raise TimerError("reauthorization_required", "Wyss rechazó timers")
        if response.is_error:
            raise TimerError("provider_unavailable", "Wyss timers devolvió un error")
        try:
            raw = response.json()
        except ValueError as error:
            raise TimerError("invalid_response", "Wyss timers devolvió JSON inválido") from error
        if not isinstance(raw, dict) or set(raw) != {"revision", "timers"}:
            raise TimerError("invalid_response", "Wyss timers devolvió campos inválidos")
        revision = raw["revision"]
        values = raw["timers"]
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision <= 0
            or not isinstance(values, list)
            or len(values) > 500
        ):
            raise TimerError("invalid_response", "Wyss timers devolvió snapshot inválido")
        return TimerSnapshot(tuple(self._timer(item) for item in values), revision, 0)

    def _timer(self, value: object) -> Timer:
        if not isinstance(value, dict):
            raise TimerError("invalid_response", "Timer inválido")
        raw = cast(dict[str, Any], value)
        allowed = {
            "id",
            "label",
            "status",
            "revision",
            "duration_seconds",
            "remaining_seconds",
            "deadline_at",
            "preset",
            "completion_id",
            "notification_id",
        }
        if not set(raw) <= allowed:
            raise TimerError("invalid_response", "Timer contiene campos extra")
        status = raw.get("status")
        revision = raw.get("revision")
        duration = raw.get("duration_seconds")
        remaining = raw.get("remaining_seconds")
        if status not in {"running", "paused", "cancelled", "completed"}:
            raise TimerError("invalid_response", "Estado de timer inválido")
        if any(
            not isinstance(item, int) or isinstance(item, bool)
            for item in (revision, duration, remaining)
        ):
            raise TimerError("invalid_response", "Contadores de timer inválidos")
        revision_value = cast(int, revision)
        duration_value = cast(int, duration)
        remaining_value = cast(int, remaining)
        if (
            revision_value <= 0
            or duration_value <= 0
            or remaining_value < 0
            or remaining_value > duration_value
        ):
            raise TimerError("invalid_response", "Rango de timer inválido")
        deadline = raw.get("deadline_at")
        if deadline is not None:
            deadline = self._text(deadline, 64)
            try:
                if datetime.fromisoformat(deadline).tzinfo is None:
                    raise ValueError
            except ValueError as error:
                raise TimerError("invalid_response", "Deadline de timer inválido") from error
        if status == "running" and deadline is None:
            raise TimerError("invalid_response", "Timer activo sin deadline")
        completion = raw.get("completion_id")
        notification = raw.get("notification_id")
        if status == "completed" and completion is None:
            raise TimerError("invalid_response", "Timer completo sin identidad durable")
        return Timer(
            self._text(raw.get("id"), 1024),
            self._text(raw.get("label"), 256),
            cast(TimerStatus, status),
            revision_value,
            duration_value,
            remaining_value,
            deadline,
            self._optional_text(raw.get("preset"), 128),
            self._optional_text(completion, 256),
            self._optional_text(notification, 256),
        )

    @staticmethod
    def _text(value: object, maximum: int) -> str:
        if not isinstance(value, str) or not value or len(value) > maximum:
            raise TimerError("invalid_response", "Texto de timer inválido")
        return value

    @classmethod
    def _optional_text(cls, value: object, maximum: int) -> str | None:
        return None if value is None else cls._text(value, maximum)
