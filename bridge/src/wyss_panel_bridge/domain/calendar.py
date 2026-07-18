"""Agenda sanitizada; OAuth y la autoridad de escritura permanecen en Wyss."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

CalendarStatus = Literal["confirmed", "tentative", "cancelled"]


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    event_id: str
    etag: str
    title: str
    start: str
    end: str
    timezone: str
    all_day: bool
    status: CalendarStatus = "confirmed"
    recurring_event_id: str | None = None
    original_start: str | None = None
    updated_at: str = ""

    def projection(self) -> dict[str, object]:
        event_id = self._client_id(self.event_id)
        recurring_id = (
            None if self.recurring_event_id is None else self._client_id(self.recurring_event_id)
        )
        return {
            "event_id": event_id,
            "title": self.title[:160],
            "start": self.start,
            "end": self.end,
            "timezone": self.timezone,
            "all_day": self.all_day,
            "status": self.status,
            "recurring_event_id": recurring_id,
            "original_start": self.original_start,
        }

    @staticmethod
    def _client_id(value: str) -> str:
        if len(value) <= 128:
            return value
        return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


@dataclass(frozen=True, slots=True)
class CalendarPage:
    events: tuple[CalendarEvent, ...]
    next_page_token: str | None
    next_sync_token: str | None


@dataclass(frozen=True, slots=True)
class CalendarCache:
    events: tuple[CalendarEvent, ...]
    sync_token: str
    synced_at: float


class CalendarError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
