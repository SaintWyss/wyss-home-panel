from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Yo necesito la variable de entorno {name}")
    return value


def _resolve_env(value: Any) -> Any:
    if isinstance(value, list):
        return [_resolve_env(item) for item in value]
    if not isinstance(value, dict):
        return value
    resolved: dict[str, Any] = {}
    for raw_key, child in value.items():
        key = str(raw_key)
        if key.endswith("_env"):
            key = key.removesuffix("_env")
            if key in value or key in resolved:
                raise RuntimeError(f"Yo recibí una configuración duplicada para {key}")
            resolved[key] = _env(str(child))
        else:
            resolved[key] = _resolve_env(child)
    return resolved


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    certfile: Path
    keyfile: Path
    panel_id: str
    panel_token_sha256: str
    allowed_entities: frozenset[str]
    primary_entity: str
    provider: str
    provider_config: dict[str, Any]
    wyss_url: str
    wyss_token: str
    wyss_transport: str = "http_v1"
    wyss_socket_path: Path = Path("/run/wyss-home/wyss-home.sock")
    v2_enabled: bool = False
    v2_identity_db: Path = Path("bridge/data/identities.sqlite3")
    v2_event_db: Path = Path("bridge/data/events.sqlite3")
    v2_projection_db: Path = Path("bridge/data/projections.sqlite3")
    v2_light_audit_db: Path = Path("bridge/data/light-audit.sqlite3")
    v2_rate_limit: int = 12
    v2_heartbeat_seconds: float = 12.0
    v2_snapshot_fallback: bool = False
    v2_lights_enabled: bool = False
    v2_conversation_enabled: bool = False
    v2_conversation_streaming: bool = True
    v2_voice_enabled: bool = False
    v2_voice_max_bytes: int = 4_194_304
    v2_voice_timeout_seconds: float = 30.0
    v2_spotify_enabled: bool = False
    v2_spotify_approved_scopes: frozenset[str] = frozenset()
    v2_weather_enabled: bool = False
    v2_weather_cache_db: Path = Path("bridge/data/weather-cache.sqlite3")
    v2_weather_latitude: float = -27.4514
    v2_weather_longitude: float = -58.9867
    v2_weather_timezone: str = "America/Argentina/Cordoba"
    v2_weather_refresh_seconds: float = 30 * 60
    v2_weather_max_stale_seconds: float = 6 * 60 * 60
    v2_calendar_enabled: bool = False
    v2_calendar_access: str = "disabled"
    v2_calendar_approved_scopes: frozenset[str] = frozenset()
    v2_calendar_cache_db: Path = Path("bridge/data/calendar-cache.sqlite3")
    v2_calendar_timezone: str = "America/Argentina/Cordoba"
    v2_calendar_refresh_seconds: float = 5 * 60
    v2_reminders_enabled: bool = False
    v2_reminder_cache_db: Path = Path("bridge/data/reminder-cache.sqlite3")
    v2_reminder_timezone: str = "America/Argentina/Cordoba"
    v2_reminder_refresh_seconds: float = 60
    v2_notifications_enabled: bool = False
    v2_notification_db: Path = Path("bridge/data/notification-outbox.sqlite3")
    v2_timers_enabled: bool = False
    v2_timer_cache_db: Path = Path("bridge/data/timer-cache.sqlite3")
    v2_timer_notification_db: Path = Path("bridge/data/timer-notification-outbox.sqlite3")
    v2_timer_refresh_seconds: float = 1
    v2_observability_enabled: bool = False
    v2_observability_max_samples: int = 512
    v2_max_pending_events: int = 256

    @classmethod
    def load(cls, path: Path) -> Settings:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
        bridge = raw["bridge"]
        panel = raw["panel"]
        devices = raw["devices"]
        wyss = raw["wyss"]
        v2 = raw.get("protocol_v2", {})
        provider = str(devices["provider"])
        provider_config = _resolve_env(dict(raw[provider]))
        if not isinstance(provider_config, dict):
            raise RuntimeError("Yo recibí una configuración de proveedor inválida")
        spotify_scopes = frozenset(str(item) for item in v2.get("spotify_approved_scopes", []))
        allowed_spotify_scopes = {
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-library-read",
            "user-library-modify",
        }
        if not spotify_scopes <= allowed_spotify_scopes:
            raise RuntimeError("Yo rechacé scopes Spotify no requeridos")
        spotify_enabled = bool(v2.get("spotify_enabled", False))
        if spotify_enabled and spotify_scopes != allowed_spotify_scopes:
            raise RuntimeError("Yo no habilito Spotify sin scopes mínimos aprobados")
        weather_refresh = float(v2.get("weather_refresh_seconds", 30 * 60))
        weather_max_stale = float(v2.get("weather_max_stale_seconds", 6 * 60 * 60))
        if weather_refresh <= 0 or weather_max_stale < weather_refresh:
            raise RuntimeError("Yo recibí ventanas meteorológicas inválidas")
        weather_timezone = str(v2.get("weather_timezone", "America/Argentina/Cordoba"))
        if weather_timezone != "America/Argentina/Cordoba":
            raise RuntimeError("Yo rechacé otra zona horaria para Resistencia")
        calendar_access = str(v2.get("calendar_access", "disabled"))
        calendar_scopes = frozenset(str(item) for item in v2.get("calendar_approved_scopes", []))
        calendar_scope_by_access = {
            "disabled": frozenset(),
            "read": frozenset({"https://www.googleapis.com/auth/calendar.events.owned.readonly"}),
            "write": frozenset({"https://www.googleapis.com/auth/calendar.events.owned"}),
        }
        if calendar_access not in calendar_scope_by_access:
            raise RuntimeError("Yo rechacé un nivel de acceso Calendar desconocido")
        if calendar_scopes != calendar_scope_by_access[calendar_access]:
            raise RuntimeError("Yo no habilito Calendar sin el scope mínimo aprobado exacto")
        calendar_enabled = bool(v2.get("calendar_enabled", False))
        if calendar_enabled and calendar_access == "disabled":
            raise RuntimeError("Yo no habilito Calendar sin acceso aprobado")
        calendar_timezone = str(v2.get("calendar_timezone", "America/Argentina/Cordoba"))
        if calendar_timezone != "America/Argentina/Cordoba":
            raise RuntimeError("Yo rechacé otra zona horaria para Calendar")
        calendar_refresh = float(v2.get("calendar_refresh_seconds", 5 * 60))
        if calendar_refresh <= 0:
            raise RuntimeError("Yo recibí un intervalo Calendar inválido")
        reminders_enabled = bool(v2.get("reminders_enabled", False))
        timers_enabled = bool(v2.get("timers_enabled", False))
        notifications_enabled = bool(v2.get("notifications_enabled", False))
        if notifications_enabled and not (reminders_enabled or timers_enabled):
            raise RuntimeError("Yo no habilito notificaciones sin recordatorios o timers")
        reminder_timezone = str(v2.get("reminder_timezone", "America/Argentina/Cordoba"))
        if reminder_timezone != "America/Argentina/Cordoba":
            raise RuntimeError("Yo rechacé otra zona horaria para recordatorios")
        reminder_refresh = float(v2.get("reminder_refresh_seconds", 60))
        if reminder_refresh <= 0:
            raise RuntimeError("Yo recibí un intervalo de recordatorios inválido")
        timer_refresh = float(v2.get("timer_refresh_seconds", 1))
        if timer_refresh <= 0:
            raise RuntimeError("Yo recibí un intervalo de timers inválido")
        observability_max_samples = int(v2.get("observability_max_samples", 512))
        if not 32 <= observability_max_samples <= 4096:
            raise RuntimeError("Yo recibí una retención de métricas inválida")
        max_pending_events = int(v2.get("max_pending_events", 256))
        if not 16 <= max_pending_events <= 1024:
            raise RuntimeError("Yo recibí un límite de backpressure inválido")
        wyss_transport = str(wyss.get("transport", "http_v1"))
        if wyss_transport not in {"unix", "http_v1"}:
            raise RuntimeError("Yo recibí un transporte Wyss desconocido")
        wyss_socket_path = Path(str(wyss.get("socket_path", "/run/wyss-home/wyss-home.sock")))
        if wyss_transport == "unix" and not wyss_socket_path.is_absolute():
            raise RuntimeError("Yo exijo una ruta absoluta para el socket Home de Wyss")
        if wyss_transport == "http_v1":
            wyss_url = str(wyss["url"]).rstrip("/")
            wyss_token = _env(str(wyss["token_env"]))
        else:
            wyss_url = ""
            wyss_token = ""
            legacy_features = {
                "spotify": spotify_enabled,
                "calendar": calendar_enabled,
                "reminders": reminders_enabled,
                "timers": timers_enabled,
            }
            enabled_legacy = [name for name, enabled in legacy_features.items() if enabled]
            if enabled_legacy:
                raise RuntimeError(
                    "Yo no habilito adapters HTTP legacy con transporte Unix: "
                    + ", ".join(enabled_legacy)
                )
        return cls(
            host=str(bridge.get("host", "0.0.0.0")),
            port=int(bridge.get("port", 8443)),
            certfile=Path(bridge["certfile"]),
            keyfile=Path(bridge["keyfile"]),
            panel_id=str(panel["id"]),
            panel_token_sha256=str(panel["token_sha256"]),
            allowed_entities=frozenset(str(item) for item in panel["allowed_entities"]),
            primary_entity=str(panel["primary_entity"]),
            provider=provider,
            provider_config=provider_config,
            wyss_url=wyss_url,
            wyss_token=wyss_token,
            wyss_transport=wyss_transport,
            wyss_socket_path=wyss_socket_path,
            v2_enabled=bool(v2.get("enabled", False)),
            v2_identity_db=Path(v2.get("identity_db", "bridge/data/identities.sqlite3")),
            v2_event_db=Path(v2.get("event_db", "bridge/data/events.sqlite3")),
            v2_projection_db=Path(v2.get("projection_db", "bridge/data/projections.sqlite3")),
            v2_light_audit_db=Path(v2.get("light_audit_db", "bridge/data/light-audit.sqlite3")),
            v2_rate_limit=int(v2.get("rate_limit", 12)),
            v2_heartbeat_seconds=float(v2.get("heartbeat_seconds", 12.0)),
            v2_snapshot_fallback=bool(v2.get("snapshot_fallback", False)),
            v2_lights_enabled=bool(v2.get("lights_enabled", False)),
            v2_conversation_enabled=bool(v2.get("conversation_enabled", False)),
            v2_conversation_streaming=bool(v2.get("conversation_streaming", True)),
            v2_voice_enabled=bool(v2.get("voice_enabled", False)),
            v2_voice_max_bytes=int(v2.get("voice_max_bytes", 4_194_304)),
            v2_voice_timeout_seconds=float(v2.get("voice_timeout_seconds", 30.0)),
            v2_spotify_enabled=spotify_enabled,
            v2_spotify_approved_scopes=spotify_scopes,
            v2_weather_enabled=bool(v2.get("weather_enabled", False)),
            v2_weather_cache_db=Path(
                v2.get("weather_cache_db", "bridge/data/weather-cache.sqlite3")
            ),
            v2_weather_latitude=float(v2.get("weather_latitude", -27.4514)),
            v2_weather_longitude=float(v2.get("weather_longitude", -58.9867)),
            v2_weather_timezone=weather_timezone,
            v2_weather_refresh_seconds=weather_refresh,
            v2_weather_max_stale_seconds=weather_max_stale,
            v2_calendar_enabled=calendar_enabled,
            v2_calendar_access=calendar_access,
            v2_calendar_approved_scopes=calendar_scopes,
            v2_calendar_cache_db=Path(
                v2.get("calendar_cache_db", "bridge/data/calendar-cache.sqlite3")
            ),
            v2_calendar_timezone=calendar_timezone,
            v2_calendar_refresh_seconds=calendar_refresh,
            v2_reminders_enabled=reminders_enabled,
            v2_reminder_cache_db=Path(
                v2.get("reminder_cache_db", "bridge/data/reminder-cache.sqlite3")
            ),
            v2_reminder_timezone=reminder_timezone,
            v2_reminder_refresh_seconds=reminder_refresh,
            v2_notifications_enabled=notifications_enabled,
            v2_notification_db=Path(
                v2.get("notification_db", "bridge/data/notification-outbox.sqlite3")
            ),
            v2_timers_enabled=timers_enabled,
            v2_timer_cache_db=Path(v2.get("timer_cache_db", "bridge/data/timer-cache.sqlite3")),
            v2_timer_notification_db=Path(
                v2.get(
                    "timer_notification_db",
                    "bridge/data/timer-notification-outbox.sqlite3",
                )
            ),
            v2_timer_refresh_seconds=timer_refresh,
            v2_observability_enabled=bool(v2.get("observability_enabled", False)),
            v2_observability_max_samples=observability_max_samples,
            v2_max_pending_events=max_pending_events,
        )
