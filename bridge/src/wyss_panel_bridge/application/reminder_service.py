"""Proyección de reminders y entrega idempotente sin duplicar autoridad de Wyss."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable

from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.reminders import (
    ReminderError,
    ReminderNotification,
    ReminderSnapshot,
)
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports_v2 import (
    EventStorePort,
    NotificationOutboxPort,
    NotificationPort,
    ReminderPort,
    ReminderStorePort,
)

EventSink = Callable[[ProjectionEvent], Awaitable[None]]


class ReminderService:
    def __init__(
        self,
        reminders: ReminderPort,
        cache: ReminderStorePort,
        notifications: NotificationPort,
        outbox: NotificationOutboxPort,
        events: EventStorePort,
        *,
        timezone: str,
        notifications_enabled: bool,
        refresh_seconds: float = 60,
        now: Callable[[], float] = time.time,
    ) -> None:
        if refresh_seconds <= 0:
            raise ValueError("intervalo de recordatorios inválido")
        self._reminders = reminders
        self._cache = cache
        self._notifications = notifications
        self._outbox = outbox
        self._events = events
        self._timezone = timezone
        self._notifications_enabled = notifications_enabled
        self._refresh_seconds = refresh_seconds
        self._now = now
        self._lock = asyncio.Lock()
        self._current: ReminderSnapshot | None = None
        self._last_attempt: float | None = None
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
            error_code: str | None = None
            refresh_due = (
                self._last_attempt is None
                or current_time - self._last_attempt >= self._refresh_seconds
            )
            if refresh_due:
                self._last_attempt = current_time
                try:
                    remote = await self._reminders.snapshot()
                    self._current = ReminderSnapshot(
                        remote.reminders,
                        remote.revision,
                        current_time,
                    )
                    self._cache.save(self._current)
                except ReminderError as error:
                    error_code = error.code
            event = await self._publish(self._current, current_time, error_code)
            self._enqueue_notifications(self._current)
            if self._notifications_enabled:
                await self._deliver_pending()
            return event

    def _enqueue_notifications(self, snapshot: ReminderSnapshot | None) -> None:
        if snapshot is None:
            return
        for reminder in snapshot.reminders:
            if reminder.status != "active" or reminder.notification_id is None:
                continue
            projected_id = str(reminder.projection()["reminder_id"])
            self._outbox.enqueue(
                ReminderNotification(
                    reminder.notification_id,
                    projected_id,
                    "Recordatorio de Wyss",
                    reminder.text[:160],
                    f"wyss://reminders/{projected_id}",
                )
            )

    async def _deliver_pending(self) -> None:
        for notification in self._outbox.pending():
            receipt = await self._notifications.deliver(notification.payload())
            accepted = receipt.accepted and receipt.delivery_id == notification.notification_id
            self._outbox.record_attempt(notification.notification_id, accepted=accepted)
            if not accepted:
                continue
            payload = {
                "notification_id": notification.notification_id,
                "reminder_id": notification.reminder_id,
                "deep_link": notification.deep_link,
            }
            key = f"notification:{notification.notification_id}"
            event = self._events.append(
                EventDraft("notification.delivered", "notifications", payload), key
            )
            if self._sink is not None:
                await self._sink(event)

    async def _publish(
        self,
        snapshot: ReminderSnapshot | None,
        current_time: float,
        error_code: str | None,
    ) -> ProjectionEvent | None:
        ordered = sorted(
            (
                reminder
                for reminder in (() if snapshot is None else snapshot.reminders)
                if reminder.status == "active"
            ),
            key=lambda reminder: (reminder.due_at, reminder.reminder_id),
        )[:8]
        payload: dict[str, object] = {
            "timezone": self._timezone,
            "available": snapshot is not None,
            "stale": error_code is not None and snapshot is not None,
            "age_seconds": (
                0 if snapshot is None else max(0, int(current_time - snapshot.synced_at))
            ),
            "notifications_enabled": self._notifications_enabled,
            "items": [reminder.projection() for reminder in ordered],
            "error_code": error_code,
        }
        if payload == self._last_payload:
            return None
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        key = f"reminders:{hashlib.sha256(encoded.encode()).hexdigest()[:48]}"
        event = self._events.append(EventDraft("reminder.changed", "reminders", payload), key)
        self._last_payload = payload
        if self._sink is not None:
            await self._sink(event)
        return event
