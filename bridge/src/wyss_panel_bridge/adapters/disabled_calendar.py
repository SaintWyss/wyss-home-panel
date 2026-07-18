"""Calendar apagado no toca red, OAuth ni persistencia."""

from __future__ import annotations

from wyss_panel_bridge.domain.calendar import (
    CalendarCache,
    CalendarError,
    CalendarEvent,
    CalendarPage,
)


class DisabledCalendarGateway:
    async def page(self, sync_token: str | None, page_token: str | None) -> CalendarPage:
        del sync_token, page_token
        raise CalendarError("policy_rejected", "Calendar está desactivado")


class VolatileCalendarStore:
    def load(self) -> CalendarCache | None:
        return None

    def replace(self, cache: CalendarCache) -> None:
        del cache

    def apply(self, events: tuple[CalendarEvent, ...], sync_token: str, synced_at: float) -> None:
        del events, sync_token, synced_at
