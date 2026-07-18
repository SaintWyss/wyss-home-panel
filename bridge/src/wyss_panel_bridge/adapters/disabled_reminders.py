"""Recordatorios y notificaciones apagados no realizan I/O externo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from wyss_panel_bridge.domain.reminders import ReminderError, ReminderNotification, ReminderSnapshot
from wyss_panel_bridge.domain.v2_types import DeliveryReceipt


class DisabledReminderGateway:
    async def snapshot(self) -> ReminderSnapshot:
        raise ReminderError("policy_rejected", "Recordatorios están desactivados")


class VolatileReminderStore:
    def load(self) -> ReminderSnapshot | None:
        return None

    def save(self, snapshot: ReminderSnapshot) -> None:
        del snapshot


class VolatileNotificationOutbox:
    def enqueue(self, notification: ReminderNotification) -> None:
        del notification

    def pending(self, limit: int = 32) -> tuple[ReminderNotification, ...]:
        del limit
        return ()

    def record_attempt(self, notification_id: str, *, accepted: bool) -> None:
        del notification_id, accepted

    def is_delivered(self, notification_id: str) -> bool:
        del notification_id
        return False


class DisabledNotificationGateway:
    async def deliver(self, notification: Mapping[str, Any]) -> DeliveryReceipt:
        return DeliveryReceipt(str(notification.get("notification_id", "disabled")), False)
