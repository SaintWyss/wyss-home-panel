from __future__ import annotations

from pathlib import Path

import pytest

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
rate_limit = 8
heartbeat_seconds = 9.5
snapshot_fallback = true
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_WYSS_TOKEN", "fake")

    settings = Settings.load(config)

    assert settings.v2_enabled is True
    assert settings.v2_identity_db == Path("private/identities.sqlite3")
    assert settings.v2_event_db == Path("private/events.sqlite3")
    assert settings.v2_projection_db == Path("private/projections.sqlite3")
    assert settings.v2_rate_limit == 8
    assert settings.v2_heartbeat_seconds == 9.5
    assert settings.v2_snapshot_fallback is True
    assert settings.wyss_url == "http://127.0.0.1:8000"
