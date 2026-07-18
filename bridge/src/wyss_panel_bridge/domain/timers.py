"""Temporizadores proyectados; Wyss conserva scheduler y deadlines autoritativos."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

TimerStatus = Literal["running", "paused", "cancelled", "completed"]


@dataclass(frozen=True, slots=True)
class Timer:
    timer_id: str
    label: str
    status: TimerStatus
    revision: int
    duration_seconds: int
    remaining_seconds: int
    deadline_at: str | None
    preset: str | None = None
    completion_id: str | None = None
    notification_id: str | None = None

    def projection(self) -> dict[str, object]:
        identifier = self.timer_id
        if len(identifier) > 128:
            identifier = f"sha256:{hashlib.sha256(identifier.encode()).hexdigest()}"
        return {
            "timer_id": identifier,
            "label": self.label[:96],
            "status": self.status,
            "revision": self.revision,
            "duration_seconds": self.duration_seconds,
            "remaining_seconds": self.remaining_seconds,
            "deadline_at": self.deadline_at,
            "preset": None if self.preset is None else self.preset[:64],
        }


@dataclass(frozen=True, slots=True)
class TimerSnapshot:
    timers: tuple[Timer, ...]
    revision: int
    synced_at: float


@dataclass(frozen=True, slots=True)
class TimerNotification:
    notification_id: str
    timer_id: str
    title: str
    body: str
    deep_link: str

    def payload(self) -> dict[str, str]:
        return {
            "notification_id": self.notification_id,
            "timer_id": self.timer_id,
            "title": self.title,
            "body": self.body,
            "deep_link": self.deep_link,
        }


class TimerError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
