from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from wyss_panel_bridge.adapters.sqlite_calendar import SqliteCalendarStore
from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.wyss_calendar import WyssCalendarGateway
from wyss_panel_bridge.application.calendar_service import CalendarService
from wyss_panel_bridge.domain.calendar import (
    CalendarCache,
    CalendarError,
    CalendarEvent,
    CalendarPage,
)

TIMEZONE = "America/Argentina/Cordoba"


def _event(
    event_id: str,
    *,
    title: str = "Reunión",
    start: str = "2026-07-18T10:00:00-03:00",
    end: str = "2026-07-18T11:00:00-03:00",
    all_day: bool = False,
    status: str = "confirmed",
) -> dict[str, object]:
    return {
        "id": event_id,
        "etag": f'"{event_id}-1"',
        "title": title,
        "start": start,
        "end": end,
        "timezone": TIMEZONE,
        "all_day": all_day,
        "status": status,
        "updated_at": "2026-07-18T12:00:00Z",
    }


@pytest.mark.asyncio
async def test_wyss_calendar_parses_timed_all_day_and_recurring_without_oauth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        recurring = _event("instance-1", title="Clase")
        recurring["recurring_event_id"] = "series-1"
        recurring["original_start"] = "2026-07-18T10:00:00-03:00"
        return httpx.Response(
            200,
            json={
                "events": [
                    _event("timed-1"),
                    _event(
                        "day-1",
                        title="Feriado",
                        start="2026-07-19",
                        end="2026-07-20",
                        all_day=True,
                    ),
                    recurring,
                ],
                "next_sync_token": "sync-2",
            },
        )

    gateway = WyssCalendarGateway(
        "https://wyss.local",
        "service-secret",
        TIMEZONE,
        transport=httpx.MockTransport(handler),
    )
    page = await gateway.page(None, None)

    assert len(page.events) == 3
    assert page.events[1].all_day is True
    assert page.events[2].recurring_event_id == "series-1"
    assert page.next_sync_token == "sync-2"  # noqa: S105 - cursor opaco, no credencial
    assert requests[0].url.params["single_events"] == "true"
    assert requests[0].url.params["window_days"] == "7"
    assert requests[0].url.params["timezone"] == TIMEZONE
    assert requests[0].headers["authorization"] == "Bearer service-secret"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "reauthorization_required"), (403, "scope_required"), (410, "invalid_cursor")],
)
async def test_wyss_calendar_maps_provider_failures(status: int, code: str) -> None:
    gateway = WyssCalendarGateway(
        "https://wyss.local",
        "service-secret",
        TIMEZONE,
        transport=httpx.MockTransport(lambda _request: httpx.Response(status)),
    )

    with pytest.raises(CalendarError) as captured:
        await gateway.page("old", None)

    assert captured.value.code == code


@pytest.mark.asyncio
async def test_wyss_calendar_rejects_provider_secret_and_wrong_timezone() -> None:
    gateway = WyssCalendarGateway(
        "https://wyss.local",
        "service-secret",
        TIMEZONE,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "events": [
                        {
                            **_event("event-1"),
                            "timezone": "UTC",
                            "access_token": "must-not-pass",
                        }
                    ],
                    "next_sync_token": "sync-1",
                },
            )
        ),
    )

    with pytest.raises(CalendarError) as captured:
        await gateway.page(None, None)

    assert captured.value.code == "invalid_response"


def _domain_event(event_id: str, title: str = "Reunión") -> CalendarEvent:
    return CalendarEvent(
        event_id,
        f'"{event_id}-1"',
        title,
        "2026-07-18T10:00:00-03:00",
        "2026-07-18T11:00:00-03:00",
        TIMEZONE,
        False,
        updated_at="2026-07-18T12:00:00Z",
    )


class FakeCalendar:
    def __init__(self, pages: list[CalendarPage]) -> None:
        self.pages = pages
        self.calls: list[tuple[str | None, str | None]] = []
        self.failure: CalendarError | None = None

    async def page(self, sync_token: str | None, page_token: str | None) -> CalendarPage:
        self.calls.append((sync_token, page_token))
        if self.failure is not None:
            raise self.failure
        if not self.pages:
            raise AssertionError("no quedan páginas fake")
        return self.pages.pop(0)


@pytest.mark.asyncio
async def test_calendar_full_sync_paginates_then_applies_incremental_deletion(
    tmp_path: Path,
) -> None:
    store = SqliteCalendarStore(tmp_path / "calendar.sqlite3")
    gateway = FakeCalendar(
        [
            CalendarPage((_domain_event("one"),), "page-2", None),
            CalendarPage((_domain_event("two"),), None, "sync-1"),
        ]
    )
    now = 1000.0
    service = CalendarService(
        gateway,
        store,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        timezone=TIMEZONE,
        write_enabled=False,
        refresh_seconds=60,
        now=lambda: now,
    )
    full = await service.ensure_snapshot()

    assert full is not None
    assert len(full.payload["events"]) == 2
    assert gateway.calls == [(None, None), (None, "page-2")]
    assert (
        store.load() is not None and store.load().sync_token == "sync-1"  # noqa: S105 - cursor no secreto
    )

    cancelled = CalendarEvent("one", "", "", "", "", TIMEZONE, False, "cancelled")
    gateway.pages = [CalendarPage((cancelled, _domain_event("two", "Actualizada")), None, "sync-2")]
    now = 1061.0
    delta = await service.ensure_snapshot()

    assert delta is not None
    projected = delta.payload["events"]
    assert isinstance(projected, list)
    assert [event["event_id"] for event in projected] == ["two"]
    assert projected[0]["title"] == "Actualizada"
    assert gateway.calls[-1] == ("sync-1", None)
    assert store.load() is not None and len(store.load().events) == 1


@pytest.mark.asyncio
async def test_invalid_cursor_triggers_atomic_full_resync(tmp_path: Path) -> None:
    store = SqliteCalendarStore(tmp_path / "calendar.sqlite3")
    store.replace(CalendarCache((_domain_event("old"),), "expired", 900))

    class InvalidThenFull(FakeCalendar):
        async def page(self, sync_token: str | None, page_token: str | None) -> CalendarPage:
            self.calls.append((sync_token, page_token))
            if sync_token == "expired":  # noqa: S105 - fixture de cursor vencido
                raise CalendarError("invalid_cursor", "gone")
            return CalendarPage((_domain_event("new"),), None, "sync-new")

    gateway = InvalidThenFull([])
    service = CalendarService(
        gateway,
        store,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        timezone=TIMEZONE,
        write_enabled=True,
        refresh_seconds=60,
        now=lambda: 1000,
    )
    event = await service.ensure_snapshot()

    assert event is not None
    assert gateway.calls == [("expired", None), (None, None)]
    assert event.payload["write_enabled"] is True
    assert [item["event_id"] for item in event.payload["events"]] == ["new"]


@pytest.mark.asyncio
async def test_provider_failure_keeps_cache_explicitly_stale(tmp_path: Path) -> None:
    store = SqliteCalendarStore(tmp_path / "calendar.sqlite3")
    gateway = FakeCalendar([CalendarPage((_domain_event("one"),), None, "sync-1")])
    now = 1000.0
    service = CalendarService(
        gateway,
        store,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        timezone=TIMEZONE,
        write_enabled=False,
        refresh_seconds=60,
        now=lambda: now,
    )
    await service.ensure_snapshot()
    gateway.failure = CalendarError("provider_unavailable", "offline")
    now = 1120.0
    stale = await service.ensure_snapshot()

    assert stale is not None
    assert stale.payload["available"] is True
    assert stale.payload["stale"] is True
    assert stale.payload["age_seconds"] == 120
    assert stale.payload["error_code"] == "provider_unavailable"
    assert (tmp_path / "calendar.sqlite3").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_client_projection_is_bounded_and_uses_opaque_long_ids(tmp_path: Path) -> None:
    projected_events = tuple(
        _domain_event(f"provider-event-{index}-" + "x" * 300, "T" * 300) for index in range(20)
    )
    service = CalendarService(
        FakeCalendar([CalendarPage(projected_events, None, "sync-bounded")]),
        SqliteCalendarStore(tmp_path / "calendar.sqlite3"),
        SqliteEventStore(tmp_path / "events.sqlite3"),
        timezone=TIMEZONE,
        write_enabled=False,
        now=lambda: 1000,
    )

    event = await service.ensure_snapshot()

    assert event is not None
    client_events = event.payload["events"]
    assert isinstance(client_events, list) and len(client_events) == 8
    assert all(str(item["event_id"]).startswith("sha256:") for item in client_events)
    assert len(json.dumps(event.payload, separators=(",", ":")).encode()) < 4096


@pytest.mark.asyncio
async def test_revoking_write_keeps_read_cache_explicitly_stale(tmp_path: Path) -> None:
    store = SqliteCalendarStore(tmp_path / "calendar.sqlite3")
    writer = CalendarService(
        FakeCalendar([CalendarPage((_domain_event("one"),), None, "sync-1")]),
        store,
        SqliteEventStore(tmp_path / "writer-events.sqlite3"),
        timezone=TIMEZONE,
        write_enabled=True,
        now=lambda: 1000,
    )
    first = await writer.ensure_snapshot()
    assert first is not None and first.payload["write_enabled"] is True

    read_gateway = FakeCalendar([])
    read_gateway.failure = CalendarError("scope_required", "write revocado")
    reader = CalendarService(
        read_gateway,
        store,
        SqliteEventStore(tmp_path / "reader-events.sqlite3"),
        timezone=TIMEZONE,
        write_enabled=False,
        now=lambda: 1100,
    )
    after_revoke = await reader.ensure_snapshot()

    assert after_revoke is not None
    assert after_revoke.payload["write_enabled"] is False
    assert after_revoke.payload["available"] is True
    assert after_revoke.payload["stale"] is True
    assert [item["event_id"] for item in after_revoke.payload["events"]] == ["one"]
