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
    assert settings.wyss_url == "http://127.0.0.1:8000"


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
