from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_timers import (
    SqliteTimerNotificationOutbox,
    SqliteTimerStore,
)
from wyss_panel_bridge.adapters.wyss_timers import WyssTimerGateway
from wyss_panel_bridge.application.timer_service import TimerService
from wyss_panel_bridge.domain.timers import Timer, TimerError, TimerSnapshot
from wyss_panel_bridge.domain.v2_types import DeliveryReceipt


def _raw_timer(**changes: object) -> dict[str, object]:
    timer: dict[str, object] = {
        "id": "timer-1",
        "label": "Horno",
        "status": "running",
        "revision": 2,
        "duration_seconds": 600,
        "remaining_seconds": 300,
        "deadline_at": "2026-07-18T01:05:00Z",
        "preset": "horno",
    }
    timer.update(changes)
    return timer


@pytest.mark.asyncio
async def test_wyss_timer_gateway_keeps_deadline_authoritative_and_auth_private() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"revision": 2, "timers": [_raw_timer()]})

    gateway = WyssTimerGateway(
        "https://wyss.local",
        "service-secret",
        transport=httpx.MockTransport(handler),
    )
    snapshot = await gateway.snapshot()

    assert snapshot.timers[0].deadline_at == "2026-07-18T01:05:00Z"
    assert snapshot.timers[0].remaining_seconds == 300
    assert requests[0].headers["authorization"] == "Bearer service-secret"
    assert "service-secret" not in str(snapshot)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"deadline_at": "2026-07-18T01:05:00"},
        {"remaining_seconds": 601},
        {"status": "unknown"},
        {"access_token": "must-not-pass"},
    ],
)
async def test_wyss_timer_gateway_rejects_unsafe_state(change: dict[str, object]) -> None:
    gateway = WyssTimerGateway(
        "https://wyss.local",
        "service-secret",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, json={"revision": 2, "timers": [_raw_timer(**change)]}
            )
        ),
    )

    with pytest.raises(TimerError) as captured:
        await gateway.snapshot()

    assert captured.value.code == "invalid_response"


class FakeTimers:
    def __init__(self, snapshot: TimerSnapshot) -> None:
        self.value = snapshot
        self.calls = 0

    async def snapshot(self) -> TimerSnapshot:
        self.calls += 1
        return self.value


class FakeNotifications:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted
        self.calls: list[dict[str, object]] = []

    async def deliver(self, notification: dict[str, object]) -> DeliveryReceipt:
        self.calls.append(notification)
        return DeliveryReceipt(str(notification["notification_id"]), self.accepted)


def _completed(index: int) -> Timer:
    return Timer(
        f"timer-{index}",
        f"Timer {index}",
        "completed",
        3,
        60,
        0,
        None,
        completion_id=f"completion:{index}",
        notification_id=f"notification:{index}",
    )


@pytest.mark.asyncio
async def test_one_hundred_timers_complete_and_notify_exactly_once_across_restart(
    tmp_path: Path,
) -> None:
    snapshot = TimerSnapshot(tuple(_completed(index) for index in range(100)), 5, 0)
    gateway = FakeTimers(snapshot)
    notifier = FakeNotifications()
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    service = TimerService(
        gateway,
        SqliteTimerStore(tmp_path / "timers.sqlite3"),
        notifier,
        SqliteTimerNotificationOutbox(tmp_path / "notifications.sqlite3"),
        events,
        notifications_enabled=True,
        refresh_seconds=60,
        now=lambda: 1_000,
    )

    await service.ensure_snapshot()
    await service.ensure_snapshot()

    event_types = [event.event_type for event in events.after(0, 256)]
    assert event_types.count("timer.completed") == 100
    assert event_types.count("notification.delivered") == 100
    assert len(notifier.calls) == 100

    restarted_notifier = FakeNotifications()
    restarted = TimerService(
        gateway,
        SqliteTimerStore(tmp_path / "timers.sqlite3"),
        restarted_notifier,
        SqliteTimerNotificationOutbox(tmp_path / "notifications.sqlite3"),
        events,
        notifications_enabled=True,
        refresh_seconds=60,
        now=lambda: 1_000,
    )
    await restarted.ensure_snapshot()

    assert restarted_notifier.calls == []
    assert [event.event_type for event in events.after(0, 256)].count("timer.completed") == 100


def test_active_timer_export_and_import_preserve_identity_deadline_and_state(
    tmp_path: Path,
) -> None:
    source = SqliteTimerStore(tmp_path / "source.sqlite3")
    running = Timer(
        "timer-running",
        "Café",
        "running",
        4,
        300,
        125,
        "2026-07-18T01:05:00Z",
        "cafe",
    )
    paused = Timer("timer-paused", "Descanso", "paused", 2, 600, 400, None)
    source.save(TimerSnapshot((running, paused, _completed(3)), 9, 1_000))

    exported = source.export_active()
    target = SqliteTimerStore(tmp_path / "target.sqlite3")
    imported = target.import_active(exported, 10, 1_100)

    assert [timer.timer_id for timer in imported.timers] == ["timer-running", "timer-paused"]
    assert imported.timers[0].deadline_at == "2026-07-18T01:05:00Z"
    assert imported.timers[1].status == "paused"
    assert (tmp_path / "target.sqlite3").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_wall_clock_adjustment_does_not_delay_authoritative_refresh(tmp_path: Path) -> None:
    running = Timer("timer-1", "Horno", "running", 2, 600, 300, "2026-07-18T01:05:00Z")
    gateway = FakeTimers(TimerSnapshot((running,), 2, 0))
    wall = 2_000.0
    monotonic = 10.0
    service = TimerService(
        gateway,
        SqliteTimerStore(tmp_path / "timers.sqlite3"),
        FakeNotifications(),
        SqliteTimerNotificationOutbox(tmp_path / "notifications.sqlite3"),
        SqliteEventStore(tmp_path / "events.sqlite3"),
        notifications_enabled=False,
        refresh_seconds=1,
        now=lambda: wall,
        clock=lambda: monotonic,
    )
    await service.ensure_snapshot()

    wall = 1_000.0
    monotonic = 12.0
    gateway.value = TimerSnapshot(
        (Timer("timer-1", "Horno", "running", 3, 600, 100, "2026-07-18T01:05:00Z"),),
        3,
        0,
    )
    refreshed = await service.ensure_snapshot()

    assert refreshed is not None
    assert refreshed.payload["items"][0]["remaining_seconds"] == 100
    assert gateway.calls == 2
