from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_reminders import (
    SqliteNotificationOutbox,
    SqliteReminderStore,
)
from wyss_panel_bridge.adapters.wyss_reminders import WyssReminderGateway
from wyss_panel_bridge.application.reminder_service import ReminderService
from wyss_panel_bridge.domain.reminders import Reminder, ReminderError, ReminderSnapshot
from wyss_panel_bridge.domain.v2_types import DeliveryReceipt

TIMEZONE = "America/Argentina/Cordoba"


def _raw_reminder(**changes: object) -> dict[str, object]:
    reminder: dict[str, object] = {
        "id": "reminder-1",
        "text": "Tomar medicación",
        "due_at": "2026-07-18T10:00:00-03:00",
        "timezone": TIMEZONE,
        "recurrence": "FREQ=DAILY",
        "status": "active",
        "revision": 3,
        "notification_id": "notify:reminder-1:3",
    }
    reminder.update(changes)
    return reminder


@pytest.mark.asyncio
async def test_wyss_reminder_gateway_is_strict_and_never_exposes_service_auth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"revision": 4, "reminders": [_raw_reminder()]})

    gateway = WyssReminderGateway(
        "https://wyss.local",
        "service-secret",
        TIMEZONE,
        transport=httpx.MockTransport(handler),
    )
    snapshot = await gateway.snapshot()

    assert snapshot.revision == 4
    assert snapshot.reminders[0].recurrence == "FREQ=DAILY"
    assert snapshot.reminders[0].notification_id == "notify:reminder-1:3"
    assert requests[0].url.params["timezone"] == TIMEZONE
    assert requests[0].headers["authorization"] == "Bearer service-secret"
    assert "service-secret" not in str(snapshot)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"due_at": "2026-07-18T10:00:00"},
        {"timezone": "UTC"},
        {"status": "deleted"},
        {"access_token": "must-not-pass"},
    ],
)
async def test_wyss_reminder_gateway_rejects_unsafe_payload(change: dict[str, object]) -> None:
    gateway = WyssReminderGateway(
        "https://wyss.local",
        "service-secret",
        TIMEZONE,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"revision": 4, "reminders": [_raw_reminder(**change)]},
            )
        ),
    )

    with pytest.raises(ReminderError) as captured:
        await gateway.snapshot()

    assert captured.value.code == "invalid_response"


class FakeReminders:
    def __init__(self, snapshot: ReminderSnapshot) -> None:
        self.value = snapshot
        self.calls = 0

    async def snapshot(self) -> ReminderSnapshot:
        self.calls += 1
        return self.value


class FakeNotifications:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.calls: list[dict[str, object]] = []

    async def deliver(self, notification: dict[str, object]) -> DeliveryReceipt:
        self.calls.append(notification)
        return DeliveryReceipt(str(notification["notification_id"]), self.accepted)


def _snapshot() -> ReminderSnapshot:
    return ReminderSnapshot(
        (
            Reminder(
                "reminder-1",
                "Tomar medicación",
                "2026-07-18T10:00:00-03:00",
                TIMEZONE,
                "FREQ=DAILY",
                "active",
                3,
                "notify:reminder-1:3",
            ),
        ),
        4,
        0,
    )


@pytest.mark.asyncio
async def test_reminder_survives_denied_delivery_then_retries_exactly_once(
    tmp_path: Path,
) -> None:
    reminder_store = SqliteReminderStore(tmp_path / "reminders.sqlite3")
    outbox = SqliteNotificationOutbox(tmp_path / "notifications.sqlite3")
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    gateway = FakeReminders(_snapshot())
    notifier = FakeNotifications(False)
    now = 1_000.0
    service = ReminderService(
        gateway,
        reminder_store,
        notifier,
        outbox,
        events,
        timezone=TIMEZONE,
        notifications_enabled=True,
        refresh_seconds=60,
        now=lambda: now,
    )

    projected = await service.ensure_snapshot()

    assert projected is not None
    assert projected.payload["items"][0]["recurrence"] == "FREQ=DAILY"
    assert notifier.calls[0]["deep_link"] == "wyss://reminders/reminder-1"
    assert reminder_store.load() is not None
    assert not outbox.is_delivered("notify:reminder-1:3")

    notifier.accepted = True
    await service.ensure_snapshot()
    await service.ensure_snapshot()

    assert len(notifier.calls) == 2
    assert outbox.is_delivered("notify:reminder-1:3")
    assert [event.event_type for event in events.after(0, 20)].count("notification.delivered") == 1
    assert reminder_store.load() is not None

    after_restart = FakeNotifications(True)
    restarted = ReminderService(
        gateway,
        SqliteReminderStore(tmp_path / "reminders.sqlite3"),
        after_restart,
        SqliteNotificationOutbox(tmp_path / "notifications.sqlite3"),
        events,
        timezone=TIMEZONE,
        notifications_enabled=True,
        refresh_seconds=60,
        now=lambda: now,
    )
    await restarted.ensure_snapshot()

    assert after_restart.calls == []
    assert (tmp_path / "reminders.sqlite3").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "notifications.sqlite3").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_push_disabled_keeps_authoritative_cache_and_pending_delivery(
    tmp_path: Path,
) -> None:
    store = SqliteReminderStore(tmp_path / "reminders.sqlite3")
    outbox = SqliteNotificationOutbox(tmp_path / "notifications.sqlite3")
    notifier = FakeNotifications(True)
    service = ReminderService(
        FakeReminders(_snapshot()),
        store,
        notifier,
        outbox,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        timezone=TIMEZONE,
        notifications_enabled=False,
    )

    projected = await service.ensure_snapshot()

    assert projected is not None
    assert projected.payload["notifications_enabled"] is False
    assert store.load() is not None
    assert len(outbox.pending()) == 1
    assert notifier.calls == []
