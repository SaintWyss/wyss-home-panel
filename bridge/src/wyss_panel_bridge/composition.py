"""Composition root de adapters reemplazables del Home Edge."""

from __future__ import annotations

from dataclasses import dataclass

from wyss_panel_bridge.adapters.home_assistant import HomeAssistantGateway
from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_light_audit import SqliteLightAuditStore
from wyss_panel_bridge.adapters.sqlite_projection import SqliteProjectionStore
from wyss_panel_bridge.adapters.tuya import TuyaGateway
from wyss_panel_bridge.application.light_service import LightService
from wyss_panel_bridge.application.projection_service import ProjectionCoordinator
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.ports_v2 import LightPort as LightPort


@dataclass(frozen=True, slots=True)
class V2Runtime:
    events: SqliteEventStore
    projections: ProjectionCoordinator
    lights: LightService


def build_light_gateway(settings: Settings) -> LightPort:
    config = settings.provider_config
    if settings.provider == "home_assistant":
        return HomeAssistantGateway(str(config["url"]), str(config["token"]))
    if settings.provider == "tuya":
        return TuyaGateway.from_config(config, settings.primary_entity)
    raise RuntimeError(f"Yo no conozco el proveedor {settings.provider}")


def build_v2_runtime(settings: Settings, gateway: LightPort) -> V2Runtime:
    events = SqliteEventStore(settings.v2_event_db)
    projections = ProjectionCoordinator(
        events,
        SqliteProjectionStore(settings.v2_projection_db),
        snapshot_fallback=settings.v2_snapshot_fallback,
    )
    lights = LightService(
        gateway,
        events,
        SqliteLightAuditStore(settings.v2_light_audit_db),
        settings.allowed_entities,
    )
    return V2Runtime(events, projections, lights)
