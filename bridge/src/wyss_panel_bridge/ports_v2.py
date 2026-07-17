"""Ports pequeños de capacidades v2, definidos antes de cualquier adapter real."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any, Protocol

from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.identity import ClientIdentity
from wyss_panel_bridge.domain.lights import LightAuditRecord
from wyss_panel_bridge.domain.models import DeviceState, FastCommand
from wyss_panel_bridge.domain.projection import ProjectionDelivery
from wyss_panel_bridge.domain.v2_types import (
    CapabilityCommand,
    DeliveryReceipt,
    ProjectionEvent,
    Snapshot,
)


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
    async def state(self) -> Snapshot: ...

    async def execute(self, command: CapabilityCommand) -> ProjectionEvent: ...


class WeatherPort(Protocol):
    async def forecast(self, location: str, days: int) -> Snapshot: ...


class CalendarPort(Protocol):
    async def agenda(self, window: Mapping[str, str]) -> Snapshot: ...

    async def execute(self, command: CapabilityCommand) -> ProjectionEvent: ...


class ReminderPort(Protocol):
    async def list(self) -> Snapshot: ...

    async def execute(self, command: CapabilityCommand) -> ProjectionEvent: ...


class TimerPort(Protocol):
    async def list(self) -> Snapshot: ...

    async def execute(self, command: CapabilityCommand) -> ProjectionEvent: ...


class NotificationPort(Protocol):
    async def deliver(self, notification: Mapping[str, Any]) -> DeliveryReceipt: ...


class SpeechPort(Protocol):
    async def transcribe(self, audio_ref: str) -> str: ...


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
