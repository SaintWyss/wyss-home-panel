"""Composition root de adapters reemplazables del Home Edge."""

from __future__ import annotations

from wyss_panel_bridge.adapters.home_assistant import HomeAssistantGateway
from wyss_panel_bridge.adapters.tuya import TuyaGateway
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.ports_v2 import LightPort


def build_light_gateway(settings: Settings) -> LightPort:
    config = settings.provider_config
    if settings.provider == "home_assistant":
        return HomeAssistantGateway(str(config["url"]), str(config["token"]))
    if settings.provider == "tuya":
        return TuyaGateway.from_config(config, settings.primary_entity)
    raise RuntimeError(f"Yo no conozco el proveedor {settings.provider}")
