"""Composition root de adapters reemplazables del Home Edge."""

from __future__ import annotations

from dataclasses import dataclass

from wyss_panel_bridge.adapters.disabled_calendar import (
    DisabledCalendarGateway,
    VolatileCalendarStore,
)
from wyss_panel_bridge.adapters.disabled_media import DisabledMediaGateway
from wyss_panel_bridge.adapters.disabled_reminders import (
    DisabledNotificationGateway,
    DisabledReminderGateway,
    VolatileNotificationOutbox,
    VolatileReminderStore,
)
from wyss_panel_bridge.adapters.disabled_speech import DisabledSpeechGateway
from wyss_panel_bridge.adapters.disabled_timers import (
    DisabledTimerGateway,
    VolatileTimerNotificationOutbox,
    VolatileTimerStore,
)
from wyss_panel_bridge.adapters.disabled_weather import (
    DisabledWeatherGateway,
    VolatileWeatherCache,
)
from wyss_panel_bridge.adapters.home_assistant import HomeAssistantGateway
from wyss_panel_bridge.adapters.open_meteo import OpenMeteoGateway
from wyss_panel_bridge.adapters.sqlite_calendar import SqliteCalendarStore
from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_light_audit import SqliteLightAuditStore
from wyss_panel_bridge.adapters.sqlite_projection import SqliteProjectionStore
from wyss_panel_bridge.adapters.sqlite_reminders import (
    SqliteNotificationOutbox,
    SqliteReminderStore,
)
from wyss_panel_bridge.adapters.sqlite_timers import (
    SqliteTimerNotificationOutbox,
    SqliteTimerStore,
)
from wyss_panel_bridge.adapters.sqlite_weather_cache import SqliteWeatherCache
from wyss_panel_bridge.adapters.tuya import TuyaGateway
from wyss_panel_bridge.adapters.wyss_calendar import WyssCalendarGateway
from wyss_panel_bridge.adapters.wyss_media import WyssMediaGateway
from wyss_panel_bridge.adapters.wyss_reminders import WyssReminderGateway
from wyss_panel_bridge.adapters.wyss_timers import WyssTimerGateway
from wyss_panel_bridge.application.calendar_service import CalendarService
from wyss_panel_bridge.application.conversation_service import ConversationService
from wyss_panel_bridge.application.light_service import LightService
from wyss_panel_bridge.application.media_service import MediaService
from wyss_panel_bridge.application.projection_service import ProjectionCoordinator
from wyss_panel_bridge.application.reminder_service import ReminderService
from wyss_panel_bridge.application.timer_service import TimerService
from wyss_panel_bridge.application.voice_service import VoiceService
from wyss_panel_bridge.application.weather_service import WeatherService
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.ports import WyssGatewayPort
from wyss_panel_bridge.ports_v2 import (
    CalendarPort,
    CalendarStorePort,
    MediaPort,
    NotificationOutboxPort,
    NotificationPort,
    ReminderPort,
    ReminderStorePort,
    SpeechPort,
    TimerNotificationOutboxPort,
    TimerPort,
    TimerStorePort,
    WeatherCachePort,
    WeatherPort,
)
from wyss_panel_bridge.ports_v2 import LightPort as LightPort


@dataclass(frozen=True, slots=True)
class V2Runtime:
    events: SqliteEventStore
    projections: ProjectionCoordinator
    lights: LightService
    conversation: ConversationService
    voice: VoiceService
    media: MediaService
    weather: WeatherService
    calendar: CalendarService
    reminders: ReminderService
    timers: TimerService


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
    calendar: CalendarPort | None = None,
    reminders: ReminderPort | None = None,
    notifications: NotificationPort | None = None,
    timers: TimerPort | None = None,
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
    calendar_gateway: CalendarPort
    calendar_cache: CalendarStorePort
    if settings.v2_calendar_enabled:
        calendar_gateway = calendar or WyssCalendarGateway(
            settings.wyss_url,
            settings.wyss_token,
            settings.v2_calendar_timezone,
        )
        calendar_cache = SqliteCalendarStore(settings.v2_calendar_cache_db)
    else:
        calendar_gateway = DisabledCalendarGateway()
        calendar_cache = VolatileCalendarStore()
    calendar_service = CalendarService(
        calendar_gateway,
        calendar_cache,
        events,
        timezone=settings.v2_calendar_timezone,
        write_enabled=settings.v2_calendar_access == "write",
        refresh_seconds=settings.v2_calendar_refresh_seconds,
    )
    reminder_gateway: ReminderPort
    reminder_cache: ReminderStorePort
    notification_outbox: NotificationOutboxPort
    if settings.v2_reminders_enabled:
        reminder_gateway = reminders or WyssReminderGateway(
            settings.wyss_url,
            settings.wyss_token,
            settings.v2_reminder_timezone,
        )
        reminder_cache = SqliteReminderStore(settings.v2_reminder_cache_db)
        notification_outbox = SqliteNotificationOutbox(settings.v2_notification_db)
    else:
        reminder_gateway = DisabledReminderGateway()
        reminder_cache = VolatileReminderStore()
        notification_outbox = VolatileNotificationOutbox()
    reminder_service = ReminderService(
        reminder_gateway,
        reminder_cache,
        notifications or DisabledNotificationGateway(),
        notification_outbox,
        events,
        timezone=settings.v2_reminder_timezone,
        notifications_enabled=settings.v2_notifications_enabled,
        refresh_seconds=settings.v2_reminder_refresh_seconds,
    )
    timer_gateway: TimerPort
    timer_cache: TimerStorePort
    timer_outbox: TimerNotificationOutboxPort
    if settings.v2_timers_enabled:
        timer_gateway = timers or WyssTimerGateway(settings.wyss_url, settings.wyss_token)
        timer_cache = SqliteTimerStore(settings.v2_timer_cache_db)
        timer_outbox = SqliteTimerNotificationOutbox(settings.v2_timer_notification_db)
    else:
        timer_gateway = DisabledTimerGateway()
        timer_cache = VolatileTimerStore()
        timer_outbox = VolatileTimerNotificationOutbox()
    timer_service = TimerService(
        timer_gateway,
        timer_cache,
        notifications or DisabledNotificationGateway(),
        timer_outbox,
        events,
        notifications_enabled=settings.v2_notifications_enabled,
        refresh_seconds=settings.v2_timer_refresh_seconds,
    )
    return V2Runtime(
        events,
        projections,
        lights,
        conversation,
        voice,
        media_service,
        weather_service,
        calendar_service,
        reminder_service,
        timer_service,
    )
