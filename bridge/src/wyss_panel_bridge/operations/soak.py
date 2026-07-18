"""Soak acelerado y reproducible sobre los stores y servicios reales del bridge."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_light_audit import SqliteLightAuditStore
from wyss_panel_bridge.adapters.sqlite_projection import SqliteProjectionStore
from wyss_panel_bridge.adapters.sqlite_timers import (
    SqliteTimerNotificationOutbox,
    SqliteTimerStore,
)
from wyss_panel_bridge.application.light_service import LightService
from wyss_panel_bridge.application.projection_service import ProjectionCoordinator
from wyss_panel_bridge.application.timer_service import TimerService
from wyss_panel_bridge.domain.lights import LightError
from wyss_panel_bridge.domain.models import DeviceState, FastCommand
from wyss_panel_bridge.domain.timers import Timer, TimerSnapshot
from wyss_panel_bridge.domain.v2_types import DeliveryReceipt, ProjectionEvent


@dataclass(frozen=True, slots=True)
class SoakConfig:
    reconnections: int = 1_000
    brightness_changes: int = 500
    timers: int = 100

    def __post_init__(self) -> None:
        if self.reconnections <= 0 or self.brightness_changes <= 0 or self.timers <= 0:
            raise ValueError("los conteos del soak deben ser positivos")
        if self.timers > 128:
            raise ValueError("el soak admite hasta 128 timers por ciclo de outbox")


@dataclass(frozen=True, slots=True)
class SoakReport:
    status: str
    reconnections: int
    brightness_changes: int
    timer_completions: int
    notification_deliveries: int
    provider_failures_injected: int
    process_restarts_injected: int
    duplicate_events: int
    ghost_states: int
    crashes: int
    final_brightness: int
    latest_event_id: int
    elapsed_seconds: float


class _SoakLights:
    def __init__(self) -> None:
        self.state = DeviceState("light.soak", "Soak", True, False, 0, 1)
        self.calls = 0
        self.fail_next = False

    async def snapshot(self, entity_ids: Sequence[str]) -> Sequence[DeviceState]:
        return [self.state] if self.state.entity_id in entity_ids else []

    async def execute(self, command: FastCommand) -> Sequence[DeviceState]:
        self.calls += 1
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("provider fault injected")
        brightness = self.state.brightness
        on = self.state.on
        if command.action == "set_brightness":
            brightness = command.brightness or 0
            on = brightness > 0
        elif command.action == "turn_on":
            on = True
        self.state = replace(
            self.state,
            brightness=brightness,
            on=on,
            revision=self.state.revision + 1,
        )
        return [self.state]


class _CompletedTimers:
    def __init__(self, count: int) -> None:
        self._snapshot = TimerSnapshot(
            tuple(
                Timer(
                    timer_id=f"soak-timer-{index}",
                    label=f"Soak {index}",
                    status="completed",
                    revision=1,
                    duration_seconds=1,
                    remaining_seconds=0,
                    deadline_at=None,
                    completion_id=f"soak-completion:{index}",
                    notification_id=f"soak-notification:{index}",
                )
                for index in range(count)
            ),
            1,
            0,
        )

    async def snapshot(self) -> TimerSnapshot:
        return self._snapshot


class _Notifications:
    def __init__(self) -> None:
        self.calls = 0

    async def deliver(self, notification: Mapping[str, Any]) -> DeliveryReceipt:
        self.calls += 1
        return DeliveryReceipt(str(notification["notification_id"]), True)


def _all_events(store: SqliteEventStore) -> list[ProjectionEvent]:
    events: list[ProjectionEvent] = []
    cursor = 0
    while batch := store.after(cursor, 256):
        events.extend(batch)
        cursor = batch[-1].event_id
    return events


async def run_soak(state_dir: Path, config: SoakConfig | None = None) -> SoakReport:
    """Ejecuta carga, resume y fallos deterministas sin depender de hardware simulado como real."""
    started = time.monotonic()
    config = config or SoakConfig()
    state_dir.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
    database_names = (
        "events.sqlite3",
        "light-audit.sqlite3",
        "timers.sqlite3",
        "notifications.sqlite3",
        "projections.sqlite3",
    )
    if any((state_dir / name).exists() for name in database_names):
        raise RuntimeError("el directorio de soak debe estar vacío para conservar reproducibilidad")

    events = SqliteEventStore(state_dir / "events.sqlite3")
    audit_path = state_dir / "light-audit.sqlite3"
    lights = _SoakLights()
    service = LightService(
        lights,
        events,
        SqliteLightAuditStore(audit_path),
        frozenset({"light.soak"}),
        instance_id="soak",
    )

    commands: list[FastCommand] = []
    for index in range(config.brightness_changes):
        command = FastCommand(
            request_id=f"soak-brightness:{index}",
            entity_id="light.soak",
            action="set_brightness",
            brightness=index % 101,
        )
        commands.append(command)
        await service.execute(("pc", "android", "panel")[index % 3], command)

    expected_brightness = (config.brightness_changes - 1) % 101
    if lights.state.brightness != expected_brightness:
        raise RuntimeError("estado fantasma después de cambios de brillo")

    calls_before_restart = lights.calls
    restarted_lights = LightService(
        lights,
        events,
        SqliteLightAuditStore(audit_path),
        frozenset({"light.soak"}),
        instance_id="soak-restarted",
    )
    replay = await restarted_lights.execute("pc", commands[0])
    if not replay.replayed or lights.calls != calls_before_restart:
        raise RuntimeError("el reinicio repitió una acción ya verificada")

    lights.fail_next = True
    try:
        await restarted_lights.execute(
            "panel",
            FastCommand("soak-provider-failure", "light.soak", "turn_on"),
        )
    except LightError as error:
        if error.code != "provider_unavailable":
            raise
    else:
        raise RuntimeError("la caída del proveedor no falló cerrada")
    await restarted_lights.execute(
        "panel",
        FastCommand("soak-provider-recovery", "light.soak", "turn_on"),
    )

    timer_gateway = _CompletedTimers(config.timers)
    notifier = _Notifications()
    timer_store_path = state_dir / "timers.sqlite3"
    outbox_path = state_dir / "notifications.sqlite3"
    timer_service = TimerService(
        timer_gateway,
        SqliteTimerStore(timer_store_path),
        notifier,
        SqliteTimerNotificationOutbox(outbox_path),
        events,
        notifications_enabled=True,
        refresh_seconds=60,
        now=lambda: 1_000,
    )
    await timer_service.ensure_snapshot()
    restarted_notifier = _Notifications()
    restarted_timers = TimerService(
        timer_gateway,
        SqliteTimerStore(timer_store_path),
        restarted_notifier,
        SqliteTimerNotificationOutbox(outbox_path),
        events,
        notifications_enabled=True,
        refresh_seconds=60,
        now=lambda: 1_000,
    )
    await restarted_timers.ensure_snapshot()
    if restarted_notifier.calls:
        raise RuntimeError("el reinicio duplicó notificaciones de timer")

    coordinator = ProjectionCoordinator(
        events,
        SqliteProjectionStore(state_dir / "projections.sqlite3"),
        max_clients=3,
    )
    latest = events.latest_event_id()
    for index in range(config.reconnections):
        distance = index % min(200, latest) + 1
        cursor = latest - distance
        delivery = coordinator.delivery(("pc", "android", "panel")[index % 3], cursor)
        delivered_ids = [event.event_id for event in delivery.events]
        if delivery.latest_event_id != latest:
            raise RuntimeError("el cursor cambió durante el soak determinista")
        if cursor == 0:
            if delivery.snapshot is None:
                raise RuntimeError("reconexión inicial sin snapshot")
        elif delivered_ids != list(range(cursor + 1, latest + 1)):
            raise RuntimeError("resume produjo huecos, desorden o duplicados")

    all_events = _all_events(events)
    event_ids = [event.event_id for event in all_events]
    completion_count = sum(event.event_type == "timer.completed" for event in all_events)
    notification_count = sum(event.event_type == "notification.delivered" for event in all_events)
    duplicate_events = len(event_ids) - len(set(event_ids))
    if completion_count != config.timers or notification_count != config.timers:
        raise RuntimeError("timers o notificaciones no fueron exactamente una vez")
    if duplicate_events:
        raise RuntimeError("el event log contiene ids duplicados")

    return SoakReport(
        status="PASS",
        reconnections=config.reconnections,
        brightness_changes=config.brightness_changes,
        timer_completions=completion_count,
        notification_deliveries=notification_count,
        provider_failures_injected=1,
        process_restarts_injected=2,
        duplicate_events=duplicate_events,
        ghost_states=0,
        crashes=0,
        final_brightness=lights.state.brightness,
        latest_event_id=latest,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--reconnections", type=int, default=1_000)
    parser.add_argument("--brightness-changes", type=int, default=500)
    parser.add_argument("--timers", type=int, default=100)
    return parser


def main() -> None:
    args = _parser().parse_args()
    config = SoakConfig(args.reconnections, args.brightness_changes, args.timers)
    if args.state_dir is not None:
        report = asyncio.run(run_soak(args.state_dir, config))
    else:
        with tempfile.TemporaryDirectory(prefix="wyss-soak-") as temporary:
            report = asyncio.run(run_soak(Path(temporary), config))
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
