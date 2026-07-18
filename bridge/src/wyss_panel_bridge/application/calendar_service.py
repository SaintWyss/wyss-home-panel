"""Sincronizacion Calendar serializada, incremental y proyectada sin OAuth."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable

from wyss_panel_bridge.domain.calendar import (
    CalendarCache,
    CalendarError,
    CalendarEvent,
)
from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports_v2 import CalendarPort, CalendarStorePort, EventStorePort

EventSink = Callable[[ProjectionEvent], Awaitable[None]]


class CalendarService:
    def __init__(
        self,
        calendar: CalendarPort,
        cache: CalendarStorePort,
        events: EventStorePort,
        *,
        timezone: str,
        write_enabled: bool,
        refresh_seconds: float = 5 * 60,
        now: Callable[[], float] = time.time,
    ) -> None:
        if refresh_seconds <= 0:
            raise ValueError("intervalo Calendar inválido")
        self._calendar = calendar
        self._cache = cache
        self._events = events
        self._timezone = timezone
        self._write_enabled = write_enabled
        self._refresh_seconds = refresh_seconds
        self._now = now
        self._lock = asyncio.Lock()
        self._current: CalendarCache | None = None
        self._last_attempt = 0.0
        self._last_payload: dict[str, object] | None = None
        self._sink: EventSink | None = None

    def set_event_sink(self, sink: EventSink | None) -> None:
        self._sink = sink

    async def ensure_snapshot(self) -> ProjectionEvent | None:
        async with self._lock:
            current_time = self._now()
            if self._current is None:
                try:
                    self._current = self._cache.load()
                except RuntimeError:
                    self._current = None
            if current_time - self._last_attempt < self._refresh_seconds:
                if self._last_payload is not None:
                    return None
                return await self._publish(self._current, current_time, None)
            self._last_attempt = current_time
            try:
                self._current = await self._refresh(self._current, current_time)
            except CalendarError as error:
                if error.code == "invalid_cursor" and self._current is not None:
                    try:
                        self._current = await self._refresh(None, current_time)
                    except CalendarError as retry_error:
                        return await self._publish(self._current, current_time, retry_error.code)
                else:
                    return await self._publish(self._current, current_time, error.code)
            return await self._publish(self._current, current_time, None)

    async def _refresh(self, previous: CalendarCache | None, current_time: float) -> CalendarCache:
        sync_token = previous.sync_token if previous is not None else None
        changes: list[CalendarEvent] = []
        page_token: str | None = None
        next_sync: str | None = None
        for _ in range(20):
            page = await self._calendar.page(sync_token, page_token)
            changes.extend(page.events)
            if page.next_page_token is None:
                next_sync = page.next_sync_token
                break
            page_token = page.next_page_token
        if next_sync is None:
            raise CalendarError("invalid_response", "Calendar excedió la paginación permitida")
        if previous is None:
            active = tuple(event for event in changes if event.status != "cancelled")
            cache = CalendarCache(active, next_sync, current_time)
            self._cache.replace(cache)
            return cache
        merged = {event.event_id: event for event in previous.events}
        for event in changes:
            if event.status == "cancelled":
                merged.pop(event.event_id, None)
            else:
                merged[event.event_id] = event
        self._cache.apply(tuple(changes), next_sync, current_time)
        return CalendarCache(tuple(merged.values()), next_sync, current_time)

    async def _publish(
        self,
        cache: CalendarCache | None,
        current_time: float,
        error_code: str | None,
    ) -> ProjectionEvent | None:
        ordered = sorted(
            (() if cache is None else cache.events),
            key=lambda event: (event.start, event.event_id),
        )[:8]
        payload: dict[str, object] = {
            "timezone": self._timezone,
            "available": cache is not None,
            "stale": error_code is not None and cache is not None,
            "age_seconds": 0 if cache is None else max(0, int(current_time - cache.synced_at)),
            "write_enabled": self._write_enabled,
            "events": [event.projection() for event in ordered],
            "error_code": error_code,
        }
        if payload == self._last_payload:
            return None
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        key = f"calendar:{hashlib.sha256(encoded.encode()).hexdigest()[:48]}"
        event = self._events.append(EventDraft("calendar.agenda.changed", "agenda", payload), key)
        self._last_payload = payload
        if self._sink is not None:
            await self._sink(event)
        return event
