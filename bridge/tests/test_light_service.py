from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_light_audit import SqliteLightAuditStore
from wyss_panel_bridge.application.light_service import LightService
from wyss_panel_bridge.domain.lights import LightConflict, LightError
from wyss_panel_bridge.domain.models import DeviceState, FastCommand


class FakeLights:
    def __init__(self) -> None:
        self.states = {
            "light.desk": DeviceState("light.desk", "Escritorio", True, False, 30, 1),
            "light.living": DeviceState("light.living", "Living", True, False, 40, 1),
            "scene.movie": DeviceState("scene.movie", "Cine", True, False, 0, 1),
        }
        self.calls = 0
        self.active: dict[str, int] = {}
        self.maximum_active: dict[str, int] = {}
        self.fail = False

    async def snapshot(self, entity_ids: list[str]) -> list[DeviceState]:
        return [self.states[entity] for entity in entity_ids if entity in self.states]

    async def execute(self, command: FastCommand) -> list[DeviceState]:
        self.calls += 1
        self.active[command.entity_id] = self.active.get(command.entity_id, 0) + 1
        self.maximum_active[command.entity_id] = max(
            self.maximum_active.get(command.entity_id, 0), self.active[command.entity_id]
        )
        await asyncio.sleep(0)
        self.active[command.entity_id] -= 1
        if self.fail:
            raise RuntimeError("foco offline")
        if command.action == "activate_scene":
            living = replace(
                self.states["light.living"],
                on=True,
                brightness=20,
                rgb=0xFF2000,
                revision=self.states["light.living"].revision + 1,
            )
            desk = replace(
                self.states["light.desk"],
                on=False,
                revision=self.states["light.desk"].revision + 1,
            )
            self.states.update({living.entity_id: living, desk.entity_id: desk})
            return [desk, living]
        current = self.states[command.entity_id]
        on = current.on
        brightness = current.brightness
        rgb = current.rgb
        if command.action == "turn_on":
            on = True
        elif command.action == "turn_off":
            on = False
        elif command.action == "toggle":
            on = not on
        elif command.action == "set_brightness":
            brightness = command.brightness or 0
            on = brightness > 0
        elif command.action == "set_color":
            rgb = command.rgb
            on = True
        updated = replace(
            current,
            on=on,
            brightness=brightness,
            rgb=rgb,
            revision=current.revision + 1,
        )
        self.states[command.entity_id] = updated
        return [updated]


def _service(tmp_path: Path) -> tuple[LightService, FakeLights, Path]:
    lights = FakeLights()
    audit_path = tmp_path / "light-audit.sqlite3"
    service = LightService(
        lights,
        SqliteEventStore(tmp_path / "events.sqlite3"),
        SqliteLightAuditStore(audit_path),
        frozenset(lights.states),
        instance_id="test",
    )
    return service, lights, audit_path


@pytest.mark.asyncio
async def test_verified_command_is_projected_and_exact_replay_does_not_execute(
    tmp_path: Path,
) -> None:
    service, lights, _ = _service(tmp_path)
    command = FastCommand("request:1", "light.living", "set_brightness", 72)

    first = await service.execute("panel:living", command, expected_revision=1)
    replay = await service.execute("panel:living", command, expected_revision=1)

    assert first.event == replay.event
    assert first.replayed is False
    assert replay.replayed is True
    assert lights.calls == 1
    assert first.event.payload["verified"] is True
    entities = first.event.payload["entities"]
    assert isinstance(entities, list)
    assert {item["entity_id"] for item in entities} == {
        "light.desk",
        "light.living",
        "scene.movie",
    }


@pytest.mark.asyncio
async def test_reused_request_with_different_command_fails_closed(tmp_path: Path) -> None:
    service, lights, _ = _service(tmp_path)
    await service.execute(
        "pc:desk",
        FastCommand("request:1", "light.living", "set_brightness", 20),
    )

    with pytest.raises(LightConflict, match="reutilizada"):
        await service.execute(
            "pc:desk",
            FastCommand("request:1", "light.living", "set_brightness", 80),
        )
    assert lights.calls == 1


@pytest.mark.asyncio
async def test_same_entity_is_serialized_while_independent_lights_progress(tmp_path: Path) -> None:
    service, lights, _ = _service(tmp_path)
    commands = [
        service.execute(
            "android:phone",
            FastCommand(f"desk:{number}", "light.desk", "set_brightness", number),
        )
        for number in range(1, 21)
    ]
    commands += [
        service.execute(
            "panel:living",
            FastCommand(f"living:{number}", "light.living", "set_brightness", number),
        )
        for number in range(1, 21)
    ]

    await asyncio.gather(*commands)

    assert lights.maximum_active == {"light.desk": 1, "light.living": 1}
    assert len(service.cached_states()) == 3


@pytest.mark.asyncio
async def test_failure_keeps_last_verified_projection_and_is_durably_audited(
    tmp_path: Path,
) -> None:
    service, lights, audit_path = _service(tmp_path)
    await service.ensure_snapshot()
    before = service.cached_states()
    lights.fail = True

    with pytest.raises(LightError) as failure:
        await service.execute("panel:living", FastCommand("offline:1", "light.living", "turn_on"))

    assert failure.value.code == "provider_unavailable"
    assert service.cached_states() == before
    with sqlite3.connect(audit_path) as connection:
        row = connection.execute(
            "SELECT status, error_code, error_message FROM light_command_audit"
        ).fetchone()
    assert row == ("failed", "provider_unavailable", "foco offline")
    assert audit_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_accepted_toggle_from_interrupted_process_is_never_repeated(tmp_path: Path) -> None:
    service, lights, audit_path = _service(tmp_path)
    command = FastCommand("toggle:1", "light.living", "toggle")
    fingerprint = service._fingerprint("panel:living", command, None)  # noqa: SLF001
    SqliteLightAuditStore(audit_path).claim(
        command.request_id,
        fingerprint,
        "panel:living",
        command.entity_id,
        command.action,
    )

    with pytest.raises(LightError) as failure:
        await service.execute("panel:living", command)

    assert failure.value.code == "conflict"
    assert failure.value.replayed is True
    assert lights.calls == 0


@pytest.mark.asyncio
async def test_five_hundred_changes_leave_no_ghost_state_or_duplicate_audit(
    tmp_path: Path,
) -> None:
    service, lights, audit_path = _service(tmp_path)
    for number in range(500):
        await service.execute(
            ("pc:desk", "android:phone", "panel:living")[number % 3],
            FastCommand(
                f"stress:{number}",
                "light.living",
                "set_brightness",
                number % 101,
            ),
        )

    living = next(state for state in service.cached_states() if state.entity_id == "light.living")
    with sqlite3.connect(audit_path) as connection:
        count, verified = connection.execute(
            "SELECT COUNT(*), SUM(status = 'verified') FROM light_command_audit"
        ).fetchone()

    assert lights.calls == 500
    assert (count, verified) == (500, 500)
    assert living.brightness == 499 % 101
