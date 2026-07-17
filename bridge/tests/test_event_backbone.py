from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.application.event_backbone import (
    ClientRateLimiter,
    EventBackbone,
    SessionHeartbeat,
)
from wyss_panel_bridge.domain.events import (
    EventConflict,
    EventDraft,
    EventError,
    RateLimitExceeded,
)


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def now(self) -> float:
        return self.value


def _draft(value: int, *, aggregate: str = "home") -> EventDraft:
    return EventDraft(
        event_type="home.entity.changed",
        aggregate=aggregate,
        payload={"brightness": value},
        correlation_id="corr:1",
        causation_id="cmd:1",
    )


def _backbone(path: Path, *, limit: int = 20) -> EventBackbone:
    return EventBackbone(
        SqliteEventStore(path),
        ClientRateLimiter(limit=limit, window_seconds=1.0),
    )


def test_exact_replay_returns_original_event_without_duplicate(tmp_path: Path) -> None:
    backbone = _backbone(tmp_path / "events.sqlite3")

    first = backbone.publish("panel:living", "panel:1", _draft(72))
    replay = backbone.publish("panel:living", "panel:1", _draft(72))

    assert replay == first
    assert first.event_id == 1
    assert first.revision == 1
    assert first.correlation_id == "corr:1"
    assert first.causation_id == "cmd:1"


def test_reused_key_with_changed_payload_fails_closed(tmp_path: Path) -> None:
    backbone = _backbone(tmp_path / "events.sqlite3")
    backbone.publish("panel:living", "panel:1", _draft(72))

    with pytest.raises(EventConflict, match="contenido diferente"):
        backbone.publish("panel:living", "panel:1", _draft(40))


def test_idempotency_claim_expires_without_deleting_event_history(tmp_path: Path) -> None:
    clock = Clock()
    store = SqliteEventStore(
        tmp_path / "events.sqlite3",
        idempotency_ttl_seconds=10,
        now=clock.now,
    )
    first = store.append(_draft(72), "panel:1")
    clock.value += 10.01

    after_expiry = store.append(_draft(72), "panel:1")

    assert (first.event_id, after_expiry.event_id) == (1, 2)
    assert [event.event_id for event in store.after(0, 10)] == [1, 2]


def test_idempotency_cache_has_a_hard_entry_limit(tmp_path: Path) -> None:
    store = SqliteEventStore(tmp_path / "events.sqlite3", max_idempotency_keys=2)
    for number in range(1, 4):
        store.append(_draft(number), f"panel:{number}")

    replay_after_eviction = store.append(_draft(1), "panel:1")

    assert replay_after_eviction.event_id == 4
    assert replay_after_eviction.revision == 4


def test_revisions_are_monotonic_per_aggregate(tmp_path: Path) -> None:
    backbone = _backbone(tmp_path / "events.sqlite3")

    home_one = backbone.publish("panel:living", "panel:1", _draft(10))
    timer_one = backbone.publish("panel:living", "panel:2", _draft(20, aggregate="timers"))
    home_two = backbone.publish("panel:living", "panel:3", _draft(30))

    assert (home_one.revision, timer_one.revision, home_two.revision) == (1, 1, 2)
    assert (home_one.event_id, timer_one.event_id, home_two.event_id) == (1, 2, 3)


def test_resume_requires_snapshot_then_returns_ordered_deltas(tmp_path: Path) -> None:
    backbone = _backbone(tmp_path / "events.sqlite3")
    for number in range(1, 5):
        backbone.publish("panel:living", f"panel:{number}", _draft(number))

    initial = backbone.resume(0)
    resumed = backbone.resume(2)
    impossible = backbone.resume(99)

    assert initial.snapshot_required is True
    assert initial.latest_event_id == 4
    assert initial.events == ()
    assert resumed.snapshot_required is False
    assert [event.event_id for event in resumed.events] == [3, 4]
    assert impossible.snapshot_required is True


def test_rate_limit_is_per_source_and_recovers_after_window(tmp_path: Path) -> None:
    clock = Clock()
    store = SqliteEventStore(tmp_path / "events.sqlite3")
    backbone = EventBackbone(
        store,
        ClientRateLimiter(limit=2, window_seconds=1.0, now=clock.now),
    )
    backbone.publish("panel:living", "panel:1", _draft(1))
    backbone.publish("panel:living", "panel:2", _draft(2))

    with pytest.raises(RateLimitExceeded):
        backbone.publish("panel:living", "panel:3", _draft(3))

    backbone.publish("android:phone", "android:1", _draft(4))
    clock.value += 1.01
    backbone.publish("panel:living", "panel:3", _draft(3))


def test_heartbeat_expires_after_two_missed_intervals() -> None:
    clock = Clock()
    heartbeat = SessionHeartbeat(heartbeat_seconds=12, now=clock.now)

    clock.value += 24
    assert heartbeat.alive()
    clock.value += 0.01
    assert not heartbeat.alive()
    heartbeat.beat()
    assert heartbeat.alive()


def test_concurrent_appends_preserve_unique_monotonic_revisions(tmp_path: Path) -> None:
    store = SqliteEventStore(tmp_path / "events.sqlite3")

    def append(number: int) -> tuple[int, int]:
        event = store.append(_draft(number), f"concurrent:{number}")
        return event.event_id, event.revision

    with ThreadPoolExecutor(max_workers=4) as executor:
        stored = list(executor.map(append, range(12)))

    assert sorted(event_id for event_id, _ in stored) == list(range(1, 13))
    assert sorted(revision for _, revision in stored) == list(range(1, 13))


@pytest.mark.parametrize(
    ("cursor", "limit"),
    [(-1, 10), (0, 0), (0, 257)],
)
def test_store_rejects_invalid_cursor_bounds(tmp_path: Path, cursor: int, limit: int) -> None:
    store = SqliteEventStore(tmp_path / "events.sqlite3")

    with pytest.raises(EventError):
        store.after(cursor, limit)


def test_event_database_is_private(tmp_path: Path) -> None:
    database = tmp_path / "events.sqlite3"
    SqliteEventStore(database)

    assert database.stat().st_mode & 0o777 == 0o600


def test_legacy_event_schema_migrates_without_losing_replay(tmp_path: Path) -> None:
    database = tmp_path / "events.sqlite3"
    payload_json, fingerprint = SqliteEventStore._encode(_draft(72), "panel:1")
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE projection_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                idempotency_key TEXT NOT NULL UNIQUE,
                fingerprint TEXT NOT NULL,
                event_type TEXT NOT NULL,
                aggregate_name TEXT NOT NULL,
                revision INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                correlation_id TEXT,
                causation_id TEXT,
                UNIQUE (aggregate_name, revision)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO projection_events (
                idempotency_key, fingerprint, event_type, aggregate_name, revision,
                payload_json, correlation_id, causation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "panel:1",
                fingerprint,
                "home.entity.changed",
                "home",
                1,
                payload_json,
                "corr:1",
                "cmd:1",
            ),
        )

    migrated = SqliteEventStore(database)

    assert migrated.append(_draft(72), "panel:1").event_id == 1
    assert migrated.latest_event_id() == 1
