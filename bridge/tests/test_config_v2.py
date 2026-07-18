from __future__ import annotations

from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.tuya import TuyaGateway
from wyss_panel_bridge.config import Settings


def test_settings_load_v2_feature_flag_and_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text(
        """
[bridge]
certfile = "server.crt"
keyfile = "server.key"
[panel]
id = "panel-v1"
token_sha256 = "hash"
allowed_entities = ["light.living"]
primary_entity = "light.living"
[devices]
provider = "tuya"
[tuya]
device_id = "fake"
address = "127.0.0.1"
local_key = "fake"
[wyss]
url = "http://127.0.0.1:8000/"
token_env = "TEST_WYSS_TOKEN"
[protocol_v2]
enabled = true
identity_db = "private/identities.sqlite3"
event_db = "private/events.sqlite3"
projection_db = "private/projections.sqlite3"
light_audit_db = "private/light-audit.sqlite3"
rate_limit = 8
heartbeat_seconds = 9.5
snapshot_fallback = true
lights_enabled = true
conversation_enabled = true
conversation_streaming = false
voice_enabled = true
voice_max_bytes = 2097152
voice_timeout_seconds = 12.5
spotify_enabled = true
spotify_approved_scopes = [
  "user-read-playback-state",
  "user-modify-playback-state",
  "user-library-read",
  "user-library-modify",
]
weather_enabled = true
weather_cache_db = "private/weather-cache.sqlite3"
weather_latitude = -27.4514
weather_longitude = -58.9867
weather_timezone = "America/Argentina/Cordoba"
weather_refresh_seconds = 900
weather_max_stale_seconds = 21600
calendar_enabled = true
calendar_access = "write"
calendar_approved_scopes = ["https://www.googleapis.com/auth/calendar.events.owned"]
calendar_cache_db = "private/calendar-cache.sqlite3"
calendar_timezone = "America/Argentina/Cordoba"
calendar_refresh_seconds = 120
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_WYSS_TOKEN", "fake")

    settings = Settings.load(config)

    assert settings.v2_enabled is True
    assert settings.v2_identity_db == Path("private/identities.sqlite3")
    assert settings.v2_event_db == Path("private/events.sqlite3")
    assert settings.v2_projection_db == Path("private/projections.sqlite3")
    assert settings.v2_light_audit_db == Path("private/light-audit.sqlite3")
    assert settings.v2_rate_limit == 8
    assert settings.v2_heartbeat_seconds == 9.5
    assert settings.v2_snapshot_fallback is True
    assert settings.v2_lights_enabled is True
    assert settings.v2_conversation_enabled is True
    assert settings.v2_conversation_streaming is False
    assert settings.v2_voice_enabled is True
    assert settings.v2_voice_max_bytes == 2_097_152
    assert settings.v2_voice_timeout_seconds == 12.5
    assert settings.v2_spotify_enabled is True
    assert settings.v2_spotify_approved_scopes == frozenset(
        {
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-library-read",
            "user-library-modify",
        }
    )
    assert settings.v2_weather_enabled is True
    assert settings.v2_weather_cache_db == Path("private/weather-cache.sqlite3")
    assert settings.v2_weather_latitude == -27.4514
    assert settings.v2_weather_longitude == -58.9867
    assert settings.v2_weather_timezone == "America/Argentina/Cordoba"
    assert settings.v2_weather_refresh_seconds == 900
    assert settings.v2_weather_max_stale_seconds == 21_600
    assert settings.v2_calendar_enabled is True
    assert settings.v2_calendar_access == "write"
    assert settings.v2_calendar_approved_scopes == frozenset(
        {"https://www.googleapis.com/auth/calendar.events.owned"}
    )
    assert settings.v2_calendar_cache_db == Path("private/calendar-cache.sqlite3")
    assert settings.v2_calendar_timezone == "America/Argentina/Cordoba"
    assert settings.v2_calendar_refresh_seconds == 120
    assert settings.wyss_url == "http://127.0.0.1:8000"


def test_settings_reject_spotify_enable_without_exact_approved_scopes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text(
        """
[bridge]
certfile = "server.crt"
keyfile = "server.key"
[panel]
id = "panel-v1"
token_sha256 = "hash"
allowed_entities = ["light.living"]
primary_entity = "light.living"
[devices]
provider = "tuya"
[tuya]
device_id = "fake"
address = "127.0.0.1"
local_key = "fake"
[wyss]
url = "http://127.0.0.1:8000"
token_env = "TEST_WYSS_TOKEN"
[protocol_v2]
enabled = true
spotify_enabled = true
spotify_approved_scopes = ["user-read-playback-state", "playlist-modify-public"]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_WYSS_TOKEN", "fake")

    with pytest.raises(RuntimeError, match="scopes Spotify no requeridos"):
        Settings.load(config)


def test_settings_reject_calendar_scope_wider_than_selected_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text(
        """
[bridge]
certfile = "server.crt"
keyfile = "server.key"
[panel]
id = "panel-v1"
token_sha256 = "hash"
allowed_entities = ["light.living"]
primary_entity = "light.living"
[devices]
provider = "tuya"
[tuya]
device_id = "fake"
address = "127.0.0.1"
local_key = "fake"
[wyss]
url = "http://127.0.0.1:8000"
token_env = "TEST_WYSS_TOKEN"
[protocol_v2]
enabled = true
calendar_enabled = true
calendar_access = "read"
calendar_approved_scopes = ["https://www.googleapis.com/auth/calendar"]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_WYSS_TOKEN", "fake")

    with pytest.raises(RuntimeError, match="scope mínimo aprobado exacto"):
        Settings.load(config)


def test_settings_resolve_nested_multilight_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text(
        """
[bridge]
certfile = "server.crt"
keyfile = "server.key"
[panel]
id = "panel-v1"
token_sha256 = "hash"
allowed_entities = ["light.living", "light.desk", "scene.movie"]
primary_entity = "light.living"
[devices]
provider = "tuya"
[[tuya.lights]]
entity_id = "light.living"
name = "Living"
device_id_env = "TEST_TUYA_LIVING_ID"
address = "10.0.0.2"
local_key_env = "TEST_TUYA_LIVING_KEY"
[[tuya.lights]]
entity_id = "light.desk"
name = "Escritorio"
device_id_env = "TEST_TUYA_DESK_ID"
address = "10.0.0.3"
local_key_env = "TEST_TUYA_DESK_KEY"
[[tuya.scenes]]
entity_id = "scene.movie"
name = "Cine"
[[tuya.scenes.steps]]
entity_id = "light.living"
brightness = 20
rgb = 16719872
[[tuya.scenes.steps]]
entity_id = "light.desk"
on = false
[wyss]
url = "http://127.0.0.1:8000"
token_env = "TEST_WYSS_TOKEN"
""".strip(),
        encoding="utf-8",
    )
    for name, value in {
        "TEST_TUYA_LIVING_ID": "living-id",
        "TEST_TUYA_LIVING_KEY": "living-key",
        "TEST_TUYA_DESK_ID": "desk-id",
        "TEST_TUYA_DESK_KEY": "desk-key",
        "TEST_WYSS_TOKEN": "wyss-token",
    }.items():
        monkeypatch.setenv(name, value)

    settings = Settings.load(config)
    gateway = TuyaGateway.from_config(
        settings.provider_config,
        settings.primary_entity,
        device_factory=lambda device_id, _address, _key: _ConfigDevice(device_id),
    )

    assert settings.allowed_entities == frozenset({"light.living", "light.desk", "scene.movie"})
    assert len(gateway._lights) == 2  # noqa: SLF001 - prueba de composición
    assert set(gateway._scenes) == {"scene.movie"}  # noqa: SLF001


class _ConfigDevice:
    def __init__(self, device_id: str) -> None:
        self.device_id = device_id

    def set_version(self, _version: float) -> None:
        return None

    def set_socketTimeout(self, _timeout: float) -> None:  # noqa: N802
        return None

    def set_socketRetryLimit(self, _retries: int) -> None:  # noqa: N802
        return None

    def set_multiple_values(self, _values: object) -> object:
        return {"success": True}

    def status(self) -> object:
        return {"dps": {"20": False, "22": 0}}
