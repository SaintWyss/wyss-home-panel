"""Composition root de adapters reemplazables del Home Edge."""

from __future__ import annotations

from dataclasses import dataclass

from wyss_panel_bridge.adapters.disabled_media import DisabledMediaGateway
from wyss_panel_bridge.adapters.disabled_speech import DisabledSpeechGateway
from wyss_panel_bridge.adapters.disabled_weather import (
    DisabledWeatherGateway,
    VolatileWeatherCache,
)
from wyss_panel_bridge.adapters.home_assistant import HomeAssistantGateway
from wyss_panel_bridge.adapters.open_meteo import OpenMeteoGateway
from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_light_audit import SqliteLightAuditStore
from wyss_panel_bridge.adapters.sqlite_projection import SqliteProjectionStore
from wyss_panel_bridge.adapters.sqlite_weather_cache import SqliteWeatherCache
from wyss_panel_bridge.adapters.tuya import TuyaGateway
from wyss_panel_bridge.adapters.wyss_media import WyssMediaGateway
from wyss_panel_bridge.application.conversation_service import ConversationService
from wyss_panel_bridge.application.light_service import LightService
from wyss_panel_bridge.application.media_service import MediaService
from wyss_panel_bridge.application.projection_service import ProjectionCoordinator
from wyss_panel_bridge.application.voice_service import VoiceService
from wyss_panel_bridge.application.weather_service import WeatherService
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.ports import WyssGatewayPort
from wyss_panel_bridge.ports_v2 import LightPort as LightPort
from wyss_panel_bridge.ports_v2 import MediaPort, SpeechPort, WeatherCachePort, WeatherPort


@dataclass(frozen=True, slots=True)
class V2Runtime:
    events: SqliteEventStore
    projections: ProjectionCoordinator
    lights: LightService
    conversation: ConversationService
    voice: VoiceService
    media: MediaService
    weather: WeatherService


def build_light_gateway(settings: Settings) -> LightPort:
    config = settings.provider_config
    if settings.provider == "home_assistant":
        return HomeAssistantGateway(str(config["url"]), str(config["token"]))
    if settings.provider == "tuya":
        return TuyaGateway.from_config(config, settings.primary_entity)
    raise RuntimeError(f"Yo no conozco el proveedor {settings.provider}")


def build_v2_runtime(
    settings: Settings,
    gateway: LightPort,
    orchestrator: WyssGatewayPort,
    speech: SpeechPort | None = None,
    media: MediaPort | None = None,
    weather: WeatherPort | None = None,
) -> V2Runtime:
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
    conversation = ConversationService(
        orchestrator,
        events,
        streaming_enabled=settings.v2_conversation_streaming,
    )
    voice = VoiceService(
        speech or DisabledSpeechGateway(),
        settings.v2_voice_max_bytes,
        settings.v2_voice_timeout_seconds,
    )
    media_gateway: MediaPort
    if settings.v2_spotify_enabled:
        media_gateway = media or WyssMediaGateway(settings.wyss_url, settings.wyss_token)
    else:
        media_gateway = DisabledMediaGateway()
    media_service = MediaService(media_gateway, events)
    weather_gateway: WeatherPort
    weather_cache: WeatherCachePort
    if settings.v2_weather_enabled:
        weather_gateway = weather or OpenMeteoGateway(
            settings.v2_weather_latitude,
            settings.v2_weather_longitude,
            settings.v2_weather_timezone,
        )
        weather_cache = SqliteWeatherCache(settings.v2_weather_cache_db)
    else:
        weather_gateway = DisabledWeatherGateway()
        weather_cache = VolatileWeatherCache()
    weather_service = WeatherService(
        weather_gateway,
        weather_cache,
        events,
        refresh_seconds=settings.v2_weather_refresh_seconds,
        max_stale_seconds=settings.v2_weather_max_stale_seconds,
    )
    return V2Runtime(
        events,
        projections,
        lights,
        conversation,
        voice,
        media_service,
        weather_service,
    )
