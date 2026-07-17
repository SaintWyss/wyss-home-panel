from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.application.media_service import MediaService
from wyss_panel_bridge.domain.media import (
    MediaAction,
    MediaCommand,
    MediaDevice,
    MediaError,
    MediaState,
)


class FakeMedia:
    def __init__(self) -> None:
        self.calls = 0
        self.current = MediaState(
            linked=True,
            available=True,
            playing=False,
            track_uri="spotify:track:one",
            title="Tema",
            artist="Artista",
            progress_ms=1_000,
            duration_ms=120_000,
            device=MediaDevice("desk", "Escritorio", "Computer", True, False, True, 20),
        )
        self.failure: MediaError | None = None

    async def state(self) -> MediaState:
        if self.failure is not None:
            raise self.failure
        return self.current

    async def execute(self, command: MediaCommand) -> MediaState:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        playing = command.action is MediaAction.PLAY or (
            self.current.playing and command.action is not MediaAction.PAUSE
        )
        self.current = replace(self.current, playing=playing)
        return self.current


def _command(
    action: MediaAction = MediaAction.PLAY,
    *,
    key: str = "spotify:command:1",
    expected_revision: int | None = None,
) -> MediaCommand:
    return MediaCommand(
        request_id="request:spotify:1",
        idempotency_key=key,
        action=action,
        expected_revision=expected_revision,
    )


@pytest.mark.asyncio
async def test_media_service_projects_state_and_replays_command_once(tmp_path: Path) -> None:
    gateway = FakeMedia()
    service = MediaService(gateway, SqliteEventStore(tmp_path / "events.sqlite3"))
    observed = []

    async def observe(event: object) -> None:
        observed.append(event)

    service.set_event_sink(observe)

    snapshot = await service.ensure_snapshot()
    first = await service.execute("pc:desk", _command(expected_revision=1))
    replay = await service.execute("pc:desk", _command(expected_revision=1))

    assert snapshot is not None and snapshot.aggregate == "spotify"
    assert first.event.revision == 2
    assert first.event.payload["playing"] is True
    assert first.event.payload["device"]["name"] == "Escritorio"
    assert first.replayed is False
    assert replay.event == first.event
    assert replay.replayed is True
    assert gateway.calls == 1
    assert len(observed) == 2


@pytest.mark.asyncio
async def test_media_service_rejects_stale_revision_and_conflicting_replay(
    tmp_path: Path,
) -> None:
    gateway = FakeMedia()
    service = MediaService(gateway, SqliteEventStore(tmp_path / "events.sqlite3"))
    await service.ensure_snapshot()

    with pytest.raises(MediaError) as stale:
        await service.execute("panel:living", _command(expected_revision=0))
    assert stale.value.code == "conflict"

    await service.execute("panel:living", _command(expected_revision=1))
    with pytest.raises(MediaError) as conflict:
        await service.execute(
            "panel:living",
            _command(MediaAction.PAUSE, expected_revision=1),
        )
    assert conflict.value.code == "conflict"
    assert gateway.calls == 1


@pytest.mark.asyncio
async def test_media_service_projects_rate_limit_without_losing_track(tmp_path: Path) -> None:
    gateway = FakeMedia()
    service = MediaService(gateway, SqliteEventStore(tmp_path / "events.sqlite3"))
    observed = []

    async def observe(event: object) -> None:
        observed.append(event)

    service.set_event_sink(observe)
    await service.ensure_snapshot()
    gateway.failure = MediaError("rate_limited", "Esperá", retry_after=9)

    with pytest.raises(MediaError):
        await service.execute("android:phone", _command())

    failure = observed[-1]
    assert failure.payload["available"] is False
    assert failure.payload["title"] == "Tema"
    assert failure.payload["device"]["id"] == "desk"
    assert failure.payload["error_code"] == "rate_limited"
    assert failure.payload["retry_after"] == 9
