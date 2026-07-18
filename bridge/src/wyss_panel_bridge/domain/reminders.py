"""Recordatorios sanitizados; Wyss conserva autoridad y recurrencia durable."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

ReminderStatus = Literal["active", "completed"]


@dataclass(frozen=True, slots=True)
class Reminder:
    reminder_id: str
    text: str
    due_at: str
    timezone: str
    recurrence: str | None
    status: ReminderStatus
    revision: int
    notification_id: str | None = None

    def projection(self) -> dict[str, object]:
        identifier = self.reminder_id
        if len(identifier) > 128:
            identifier = f"sha256:{hashlib.sha256(identifier.encode()).hexdigest()}"
        return {
            "reminder_id": identifier,
            "text": self.text[:160],
            "due_at": self.due_at,
            "timezone": self.timezone,
            "recurrence": self.recurrence,
            "status": self.status,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class ReminderSnapshot:
    reminders: tuple[Reminder, ...]
    revision: int
    synced_at: float


@dataclass(frozen=True, slots=True)
class ReminderNotification:
    notification_id: str
    reminder_id: str
    title: str
    body: str
    deep_link: str

    def payload(self) -> dict[str, str]:
        return {
            "notification_id": self.notification_id,
            "reminder_id": self.reminder_id,
            "title": self.title,
            "body": self.body,
            "deep_link": self.deep_link,
        }


class ReminderError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
