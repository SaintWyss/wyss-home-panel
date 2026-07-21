from __future__ import annotations

from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_light_audit import SqliteLightAuditStore
from wyss_panel_bridge.application.light_service import LightService
from wyss_panel_bridge.domain.models import DeviceState, FastCommand


class RecoveringLights:
    def __init__(self) -> None:
        self.snapshot_calls = 0

    async def snapshot(self, entity_ids: list[str]) -> list[DeviceState]:
        self.snapshot_calls += 1
        if "light.living" not in entity_ids:
            return []
        if self.snapshot_calls == 1:
            return [DeviceState("light.living", "Living", False, False, 0, 1)]
        return [DeviceState("light.living", "Living", True, True, 60, 2)]

    async def execute(self, command: FastCommand) -> list[DeviceState]:
        raise AssertionError(f"no se esperaba ejecutar {command.action}")


@pytest.mark.asyncio
async def test_resync_rechecks_a_light_that_was_offline_on_first_snapshot(tmp_path: Path) -> None:
    lights = RecoveringLights()
    service = LightService(
        lights,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        SqliteLightAuditStore(tmp_path / "light-audit.sqlite3"),
        frozenset({"light.living"}),
        instance_id="resync-regression",
    )

    first = await service.ensure_snapshot()
    recovered = await service.ensure_snapshot()
    unchanged = await service.ensure_snapshot()

    assert first is not None
    assert recovered is not None
    assert unchanged is None
    assert lights.snapshot_calls == 3
    assert service.cached_states() == (
        DeviceState("light.living", "Living", True, True, 60, 2),
    )
