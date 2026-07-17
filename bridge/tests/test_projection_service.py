from __future__ import annotations

from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_projection import SqliteProjectionStore
from wyss_panel_bridge.application.projection_service import ProjectionCoordinator
from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.projection import ProjectionError, ProjectionGap
from wyss_panel_bridge.domain.v2_types import ProjectionEvent


def _append(store: SqliteEventStore, number: int, aggregate: str = "home") -> None:
    store.append(
        EventDraft(
            event_type=f"{aggregate}.changed",
            aggregate=aggregate,
            payload={"value": number},
        ),
        f"{aggregate}:{number}",
    )


def test_clients_converge_on_same_materialized_snapshot(tmp_path: Path) -> None:
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    projections = SqliteProjectionStore(tmp_path / "projections.sqlite3")
    coordinator = ProjectionCoordinator(events, projections)
    _append(events, 1)
    _append(events, 1, "timers")
    _append(events, 2)

    views = [
        coordinator.delivery(client_id, 0)
        for client_id in ("pc:desk", "android:phone", "panel:living")
    ]

    assert all(view.snapshot is not None for view in views)
    assert [view.snapshot for view in views] == [views[0].snapshot] * 3
    assert views[0].snapshot is not None
    assert views[0].snapshot.revision == 3
    assert views[0].snapshot.payload == {"home": {"value": 2}, "timers": {"value": 1}}


def test_reducer_is_deterministic_across_rebuilds(tmp_path: Path) -> None:
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    for number in range(1, 6):
        _append(events, number)
    first = SqliteProjectionStore(tmp_path / "first.sqlite3")
    second = SqliteProjectionStore(tmp_path / "second.sqlite3")

    ProjectionCoordinator(events, first).synchronize()
    ProjectionCoordinator(events, second).synchronize()

    assert first.snapshot() == second.snapshot()
    assert first.snapshot().payload == {"home": {"value": 5}}


def test_cursor_gets_only_deltas_after_known_event(tmp_path: Path) -> None:
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    projections = SqliteProjectionStore(tmp_path / "projections.sqlite3")
    for number in range(1, 5):
        _append(events, number)

    delivery = ProjectionCoordinator(events, projections).delivery("panel:living", 2)

    assert delivery.snapshot is None
    assert [event.event_id for event in delivery.events] == [3, 4]
    assert delivery.latest_event_id == 4


def test_gap_and_stale_revision_fail_closed(tmp_path: Path) -> None:
    projections = SqliteProjectionStore(tmp_path / "projections.sqlite3")
    second = ProjectionEvent(2, "home", 2, {"value": 2})

    with pytest.raises(ProjectionGap, match="event_id"):
        projections.apply(second)

    first = ProjectionEvent(1, "home", 1, {"value": 1})
    assert projections.apply(first)
    assert not projections.apply(first)
    stale_new_event = ProjectionEvent(2, "home", 1, {"value": 99})
    with pytest.raises(ProjectionError, match="obsoleta"):
        projections.apply(stale_new_event)


def test_snapshot_fallback_can_replace_delta_delivery(tmp_path: Path) -> None:
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    projections = SqliteProjectionStore(tmp_path / "projections.sqlite3")
    _append(events, 1)
    _append(events, 2)
    coordinator = ProjectionCoordinator(events, projections, snapshot_fallback=True)

    delivery = coordinator.delivery("panel:living", 1)

    assert delivery.snapshot is not None
    assert delivery.events == ()
    assert delivery.snapshot.payload == {"home": {"value": 2}}


def test_client_cursor_cache_is_bounded_and_not_an_authority(tmp_path: Path) -> None:
    events = SqliteEventStore(tmp_path / "events.sqlite3")
    projections = SqliteProjectionStore(tmp_path / "projections.sqlite3")
    coordinator = ProjectionCoordinator(events, projections, max_clients=2)

    for client_id in ("panel:one", "panel:two", "panel:three"):
        coordinator.delivery(client_id, 0)

    assert coordinator.cached_clients == 2
    assert not hasattr(coordinator, "write_projection")
    assert not hasattr(projections, "save")


def test_projection_database_is_private(tmp_path: Path) -> None:
    database = tmp_path / "projections.sqlite3"
    SqliteProjectionStore(database)

    assert database.stat().st_mode & 0o777 == 0o600
