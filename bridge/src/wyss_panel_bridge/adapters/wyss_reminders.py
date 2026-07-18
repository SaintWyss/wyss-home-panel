"""Consulta recordatorios en Wyss sin duplicar scheduler ni policy."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.reminders import (
    Reminder,
    ReminderError,
    ReminderSnapshot,
    ReminderStatus,
)


class WyssReminderGateway:
    def __init__(
        self,
        url: str,
        token: str,
        timezone: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timezone = timezone
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
            transport=transport,
        )

    async def snapshot(self) -> ReminderSnapshot:
        try:
            response = await self._client.get(
                "/api/home/reminders", params={"timezone": self._timezone}
            )
        except httpx.HTTPError as error:
            raise ReminderError("provider_unavailable", "Wyss reminders no respondió") from error
        if response.status_code in {401, 403}:
            raise ReminderError("reauthorization_required", "Wyss rechazó reminders")
        if response.is_error:
            raise ReminderError("provider_unavailable", "Wyss reminders devolvió un error")
        try:
            raw = response.json()
        except ValueError as error:
            raise ReminderError(
                "invalid_response", "Wyss reminders devolvió JSON inválido"
            ) from error
        if not isinstance(raw, dict) or set(raw) != {"revision", "reminders"}:
            raise ReminderError("invalid_response", "Wyss reminders devolvió campos inválidos")
        values = raw["reminders"]
        revision = raw["revision"]
        if (
            not isinstance(values, list)
            or len(values) > 250
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision <= 0
        ):
            raise ReminderError("invalid_response", "Wyss reminders devolvió un snapshot inválido")
        return ReminderSnapshot(tuple(self._reminder(item) for item in values), revision, 0)

    def _reminder(self, value: object) -> Reminder:
        if not isinstance(value, dict):
            raise ReminderError("invalid_response", "Recordatorio inválido")
        raw = cast(dict[str, Any], value)
        allowed = {
            "id",
            "text",
            "due_at",
            "timezone",
            "recurrence",
            "status",
            "revision",
            "notification_id",
        }
        if not set(raw) <= allowed:
            raise ReminderError("invalid_response", "Recordatorio contiene campos extra")
        status = raw.get("status")
        if status not in {"active", "completed"}:
            raise ReminderError("invalid_response", "Estado de recordatorio inválido")
        due_at = self._text(raw.get("due_at"), 64)
        try:
            if datetime.fromisoformat(due_at).tzinfo is None:
                raise ValueError
        except ValueError as error:
            raise ReminderError("invalid_response", "Vencimiento inválido") from error
        timezone = self._text(raw.get("timezone"), 64)
        revision = raw.get("revision")
        if (
            timezone != self._timezone
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision <= 0
        ):
            raise ReminderError("invalid_response", "Timezone o revisión inválida")
        recurrence = raw.get("recurrence")
        notification_id = raw.get("notification_id")
        return Reminder(
            self._text(raw.get("id"), 1024),
            self._text(raw.get("text"), 500),
            due_at,
            timezone,
            None if recurrence is None else self._text(recurrence, 256),
            cast(ReminderStatus, status),
            revision,
            None if notification_id is None else self._text(notification_id, 256),
        )

    @staticmethod
    def _text(value: object, maximum: int) -> str:
        if not isinstance(value, str) or not value or len(value) > maximum:
            raise ReminderError("invalid_response", "Texto de reminder inválido")
        return value
