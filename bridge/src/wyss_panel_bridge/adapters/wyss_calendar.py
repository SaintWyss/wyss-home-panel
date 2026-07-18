"""Adapter Calendar sobre la API interna autenticada de Wyss, nunca sobre OAuth cliente."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.calendar import (
    CalendarError,
    CalendarEvent,
    CalendarPage,
    CalendarStatus,
)


class WyssCalendarGateway:
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

    async def page(self, sync_token: str | None, page_token: str | None) -> CalendarPage:
        params = {
            "timezone": self._timezone,
            "single_events": "true",
            "window_days": "7",
        }
        if sync_token:
            params["sync_token"] = sync_token
        if page_token:
            params["page_token"] = page_token
        try:
            response = await self._client.get("/api/home/calendar/events", params=params)
        except httpx.HTTPError as error:
            raise CalendarError("provider_unavailable", "Wyss Calendar no respondió") from error
        if response.status_code == 410:
            raise CalendarError("invalid_cursor", "El cursor de Calendar venció")
        if response.status_code == 401:
            raise CalendarError("reauthorization_required", "Calendar requiere revinculación")
        if response.status_code == 403:
            raise CalendarError("scope_required", "Calendar no acreditó el scope requerido")
        if response.status_code == 429:
            raise CalendarError("rate_limited", "Calendar limitó temporalmente la sincronización")
        if response.is_error:
            raise CalendarError("provider_unavailable", "Wyss Calendar devolvió un error")
        try:
            decoded = response.json()
        except ValueError as error:
            raise CalendarError("invalid_response", "Calendar devolvió JSON inválido") from error
        if not isinstance(decoded, dict):
            raise CalendarError("invalid_response", "Calendar devolvió una respuesta inválida")
        raw = cast(dict[str, Any], decoded)
        self._reject_secrets(raw)
        if not set(raw) <= {"events", "next_page_token", "next_sync_token"}:
            raise CalendarError("invalid_response", "Calendar devolvió campos no permitidos")
        raw_events = raw.get("events")
        if not isinstance(raw_events, list) or len(raw_events) > 250:
            raise CalendarError("invalid_response", "Calendar devolvió eventos inválidos")
        events = tuple(self._event(item) for item in raw_events)
        next_page = self._token(raw.get("next_page_token"))
        next_sync = self._token(raw.get("next_sync_token"))
        if (next_page is None) == (next_sync is None):
            raise CalendarError("invalid_response", "Calendar devolvió cursores ambiguos")
        return CalendarPage(events, next_page, next_sync)

    def _event(self, value: object) -> CalendarEvent:
        if not isinstance(value, dict):
            raise CalendarError("invalid_response", "Calendar devolvió un evento inválido")
        raw = cast(dict[str, Any], value)
        allowed = {
            "id",
            "etag",
            "title",
            "start",
            "end",
            "timezone",
            "all_day",
            "status",
            "recurring_event_id",
            "original_start",
            "updated_at",
        }
        if not set(raw) <= allowed:
            raise CalendarError("invalid_response", "Calendar devolvió campos de evento extra")
        event_id = self._text(raw.get("id"), 1024)
        status = str(raw.get("status", "confirmed"))
        if status not in {"confirmed", "tentative", "cancelled"}:
            raise CalendarError("invalid_response", "Calendar devolvió un estado inválido")
        if status == "cancelled":
            return CalendarEvent(
                event_id,
                "",
                "",
                "",
                "",
                self._timezone,
                False,
                cast(CalendarStatus, status),
            )
        all_day = raw.get("all_day")
        if not isinstance(all_day, bool):
            raise CalendarError("invalid_response", "Calendar omitió all_day")
        start = self._text(raw.get("start"), 64)
        end = self._text(raw.get("end"), 64)
        try:
            if all_day:
                date.fromisoformat(start)
                date.fromisoformat(end)
            else:
                if datetime.fromisoformat(start).tzinfo is None:
                    raise ValueError
                if datetime.fromisoformat(end).tzinfo is None:
                    raise ValueError
        except ValueError as error:
            raise CalendarError("invalid_response", "Calendar devolvió fechas inválidas") from error
        timezone = self._text(raw.get("timezone"), 64)
        if timezone != self._timezone:
            raise CalendarError("invalid_response", "Calendar devolvió otra zona horaria")
        return CalendarEvent(
            event_id=event_id,
            etag=self._text(raw.get("etag"), 256),
            title=self._text(raw.get("title"), 300),
            start=start,
            end=end,
            timezone=timezone,
            all_day=all_day,
            status=cast(CalendarStatus, status),
            recurring_event_id=self._optional_text(raw.get("recurring_event_id"), 1024),
            original_start=self._optional_text(raw.get("original_start"), 64),
            updated_at=self._text(raw.get("updated_at"), 64),
        )

    @staticmethod
    def _text(value: object, maximum: int) -> str:
        if not isinstance(value, str) or not value or len(value) > maximum:
            raise CalendarError("invalid_response", "Calendar devolvió texto inválido")
        return value

    @classmethod
    def _optional_text(cls, value: object, maximum: int) -> str | None:
        return None if value is None else cls._text(value, maximum)

    @classmethod
    def _token(cls, value: object) -> str | None:
        return cls._optional_text(value, 2048)

    @classmethod
    def _reject_secrets(cls, value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in {"access_token", "refresh_token", "authorization"}:
                    raise CalendarError("invalid_response", "Calendar intentó exponer un secreto")
                cls._reject_secrets(child)
        elif isinstance(value, list):
            for child in value:
                cls._reject_secrets(child)
