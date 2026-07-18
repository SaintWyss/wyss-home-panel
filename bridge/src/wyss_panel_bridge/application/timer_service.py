"""Replica timers de Wyss y publica cada finalización exactamente una vez."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable

from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.timers import TimerError, TimerNotification, TimerSnapshot
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports_v2 import (
    EventStorePort,
    NotificationPort,
    TimerNotificationOutboxPort,
    TimerPort,
    TimerStorePort,
)

EventSink = Callable[[ProjectionEvent], Awaitable[None]]


class TimerService:
    def __init__(
        self,
        timers: TimerPort,
        cache: TimerStorePort,
        notifications: NotificationPort,
        outbox: TimerNotificationOutboxPort,
        events: EventStorePort,
        *,
        notifications_enabled: bool,
        refresh_seconds: float = 1,
        now: Callable[[], float] = time.time,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if refresh_seconds <= 0:
            raise ValueError("intervalo de timers inválido")
        self._timers = timers
        self._cache = cache
        self._notifications = notifications
        self._outbox = outbox
        self._events = events
        self._notifications_enabled = notifications_enabled
        self._refresh_seconds = refresh_seconds
        self._now = now
        self._clock = clock
        self._lock = asyncio.Lock()
        self._current: TimerSnapshot | None = None
        self._last_attempt: float | None = None
        self._last_payload: dict[str, object] | None = None
        self._sink: EventSink | None = None

    def set_event_sink(self, sink: EventSink | None) -> None:
        self._sink = sink

    async def ensure_snapshot(self) -> ProjectionEvent | None:
        async with self._lock:
            current_time = self._now()
            current_tick = self._clock()
            if self._current is None:
                try:
                    self._current = self._cache.load()
                except RuntimeError:
                    self._current = None
            error_code: str | None = None
            if (
                self._last_attempt is None
                or current_tick - self._last_attempt >= self._refresh_seconds
            ):
                self._last_attempt = current_tick
                try:
                    remote = await self._timers.snapshot()
                    self._current = TimerSnapshot(remote.timers, remote.revision, current_time)
                    self._cache.save(self._current)
                except TimerError as error:
                    error_code = error.code
            event = await self._publish(self._current, current_time, error_code)
            await self._complete(self._current)
            return event

    async def _complete(self, snapshot: TimerSnapshot | None) -> None:
        if snapshot is None:
            return
        for timer in snapshot.timers:
            if timer.status != "completed" or timer.completion_id is None:
                continue
            if not self._cache.completion_recorded(timer.completion_id):
                payload = {
                    "timer_id": str(timer.projection()["timer_id"]),
                    "completion_id": timer.completion_id,
                }
                event = self._events.append(
                    EventDraft("timer.completed", "timers", {"last_completion": payload}),
                    f"timer-completed:{timer.completion_id}",
                )
                self._cache.record_completion(timer.completion_id, timer.timer_id)
                if self._sink is not None:
                    await self._sink(event)
            if timer.notification_id is not None:
                projected_id = str(timer.projection()["timer_id"])
                self._outbox.enqueue(
                    TimerNotification(
                        timer.notification_id,
                        projected_id,
                        "Timer finalizado",
                        timer.label[:96],
                        f"wyss://timers/{projected_id}",
                    )
                )
        if self._notifications_enabled:
            await self._deliver_pending()

    async def _deliver_pending(self) -> None:
        for notification in self._outbox.pending():
            receipt = await self._notifications.deliver(notification.payload())
            accepted = receipt.accepted and receipt.delivery_id == notification.notification_id
            self._outbox.record_attempt(notification.notification_id, accepted=accepted)
            if accepted:
                event = self._events.append(
                    EventDraft(
                        "notification.delivered",
                        "notifications",
                        {
                            "notification_id": notification.notification_id,
                            "timer_id": notification.timer_id,
                            "deep_link": notification.deep_link,
                        },
                    ),
                    f"notification:{notification.notification_id}",
                )
                if self._sink is not None:
                    await self._sink(event)

    async def _publish(
        self,
        snapshot: TimerSnapshot | None,
        current_time: float,
        error_code: str | None,
    ) -> ProjectionEvent | None:
        active = sorted(
            (
                timer
                for timer in (() if snapshot is None else snapshot.timers)
                if timer.status in {"running", "paused"}
            ),
            key=lambda timer: (timer.remaining_seconds, timer.timer_id),
        )[:8]
        payload: dict[str, object] = {
            "available": snapshot is not None,
            "stale": error_code is not None and snapshot is not None,
            "age_seconds": (
                0 if snapshot is None else max(0, int(current_time - snapshot.synced_at))
            ),
            "items": [timer.projection() for timer in active],
            "error_code": error_code,
        }
        if payload == self._last_payload:
            return None
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        key = f"timers:{hashlib.sha256(encoded.encode()).hexdigest()[:48]}"
        event = self._events.append(EventDraft("timer.changed", "timers", payload), key)
        self._last_payload = payload
        if self._sink is not None:
            await self._sink(event)
        return event
