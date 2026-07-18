"""Ports pequeños de capacidades v2, definidos antes de cualquier adapter real."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any, Protocol

from wyss_panel_bridge.domain.calendar import CalendarCache, CalendarEvent, CalendarPage
from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.identity import ClientIdentity
from wyss_panel_bridge.domain.lights import LightAuditRecord
from wyss_panel_bridge.domain.media import MediaCommand, MediaState
from wyss_panel_bridge.domain.models import DeviceState, FastCommand
from wyss_panel_bridge.domain.projection import ProjectionDelivery
from wyss_panel_bridge.domain.reminders import (
    ReminderNotification,
    ReminderSnapshot,
)
from wyss_panel_bridge.domain.timers import TimerNotification, TimerSnapshot
from wyss_panel_bridge.domain.v2_types import (
    CapabilityCommand,
    DeliveryReceipt,
    ProjectionEvent,
    Snapshot,
)
from wyss_panel_bridge.domain.weather import WeatherForecast


class HomePort(Protocol):
    async def snapshot(self) -> Snapshot: ...

    async def execute(self, command: CapabilityCommand) -> ProjectionEvent: ...


class LightPort(Protocol):
    async def snapshot(self, entity_ids: Sequence[str]) -> Sequence[DeviceState]: ...

    async def execute(self, command: FastCommand) -> Sequence[DeviceState]: ...


class LightAuditPort(Protocol):
    def claim(
        self,
        idempotency_key: str,
        request_id: str,
        fingerprint: str,
        source: str,
        entity_id: str,
        action: str,
    ) -> LightAuditRecord: ...

    def verified(self, idempotency_key: str, result: Mapping[str, Any]) -> LightAuditRecord: ...

    def failed(
        self,
        idempotency_key: str,
        code: str,
        message: str,
        *,
        ambiguous: bool = False,
    ) -> LightAuditRecord: ...


class ProjectionPort(Protocol):
    async def snapshot(self, client_id: str) -> Snapshot: ...

    async def deltas(self, after_event_id: int, limit: int) -> Sequence[ProjectionEvent]: ...


class ClientEventPort(Protocol):
    async def publish(self, event: ProjectionEvent) -> None: ...

    def subscribe(self, client_id: str, after_event_id: int) -> AsyncIterator[ProjectionEvent]: ...


class MediaPort(Protocol):
    async def state(self) -> MediaState: ...

    async def execute(self, command: MediaCommand) -> MediaState: ...


class WeatherPort(Protocol):
    async def forecast(self, location: str, days: int) -> WeatherForecast: ...


class WeatherCachePort(Protocol):
    def load(self) -> WeatherForecast | None: ...

    def save(self, forecast: WeatherForecast) -> None: ...


class CalendarPort(Protocol):
    async def page(self, sync_token: str | None, page_token: str | None) -> CalendarPage: ...


class CalendarStorePort(Protocol):
    def load(self) -> CalendarCache | None: ...

    def replace(self, cache: CalendarCache) -> None: ...

    def apply(
        self, events: tuple[CalendarEvent, ...], sync_token: str, synced_at: float
    ) -> None: ...


class ReminderPort(Protocol):
    async def snapshot(self) -> ReminderSnapshot: ...


class ReminderStorePort(Protocol):
    def load(self) -> ReminderSnapshot | None: ...

    def save(self, snapshot: ReminderSnapshot) -> None: ...


class NotificationOutboxPort(Protocol):
    def enqueue(self, notification: ReminderNotification) -> None: ...

    def pending(self, limit: int = 32) -> tuple[ReminderNotification, ...]: ...

    def record_attempt(self, notification_id: str, *, accepted: bool) -> None: ...

    def is_delivered(self, notification_id: str) -> bool: ...


class TimerPort(Protocol):
    async def snapshot(self) -> TimerSnapshot: ...


class TimerStorePort(Protocol):
    def load(self) -> TimerSnapshot | None: ...

    def save(self, snapshot: TimerSnapshot) -> None: ...

    def completion_recorded(self, completion_id: str) -> bool: ...

    def record_completion(self, completion_id: str, timer_id: str) -> None: ...


class TimerNotificationOutboxPort(Protocol):
    def enqueue(self, notification: TimerNotification) -> None: ...

    def pending(self, limit: int = 128) -> tuple[TimerNotification, ...]: ...

    def record_attempt(self, notification_id: str, *, accepted: bool) -> None: ...


class NotificationPort(Protocol):
    async def deliver(self, notification: Mapping[str, Any]) -> DeliveryReceipt: ...


class SpeechPort(Protocol):
    async def transcribe(self, audio: memoryview, content_type: str) -> str: ...


class CameraPort(Protocol):
    async def list(self) -> Snapshot: ...

    async def snapshot(self, camera_id: str) -> Snapshot: ...

    async def health(self, camera_id: str) -> Mapping[str, Any]: ...


class IdentityStorePort(Protocol):
    def get(self, client_id: str) -> ClientIdentity | None: ...

    def save(self, identity: ClientIdentity) -> None: ...


class EventStorePort(Protocol):
    def append(self, draft: EventDraft, idempotency_key: str) -> ProjectionEvent: ...

    def after(self, event_id: int, limit: int) -> Sequence[ProjectionEvent]: ...

    def latest_event_id(self) -> int: ...


class ProjectionStorePort(Protocol):
    def apply(self, event: ProjectionEvent) -> bool: ...

    def snapshot(self) -> Snapshot: ...

    def last_event_id(self) -> int: ...


class ProjectionCoordinatorPort(Protocol):
    def delivery(self, client_id: str, last_event_id: int) -> ProjectionDelivery: ...
