from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.api import create_app
from wyss_panel_bridge.application.identity_service import IdentityService
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.domain.events import EventDraft


def _settings(tmp_path: Path, *, enabled: bool) -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8443,
        certfile=tmp_path / "server.crt",
        keyfile=tmp_path / "server.key",
        panel_id="panel-v1",
        panel_token_sha256="0" * 64,
        allowed_entities=frozenset({"light.living"}),
        primary_entity="light.living",
        provider="tuya",
        provider_config={
            "device_id": "fake",
            "address": "127.0.0.1",
            "local_key": "fake",
        },
        wyss_url="http://127.0.0.1:8000",
        wyss_token="fake",  # noqa: S106 - fixture, no es una credencial real
        v2_enabled=enabled,
        v2_identity_db=tmp_path / "identities.sqlite3",
        v2_event_db=tmp_path / "events.sqlite3",
    )


def _pair(settings: Settings) -> tuple[str, IdentityService]:
    service = IdentityService(SqliteIdentityStore(settings.v2_identity_db))
    token = service.pair("panel:living", {"panel.read_projection"})
    return token, service


def _hello(last_event_id: int = 0) -> dict[str, object]:
    return {
        "v": 2,
        "type": "session.hello",
        "message_id": "hello:1",
        "source": "panel:living",
        "payload": {
            "firmware": "2.0.0",
            "capabilities": ["ui.core"],
            "last_event_id": last_event_id,
        },
    }


def _headers(token: str) -> dict[str, str]:
    return {"x-wyss-client": "panel:living", "authorization": f"Bearer {token}"}


def test_feature_flag_keeps_v1_and_avoids_v2_state_when_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=False)
    app = create_app(settings)
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/v1/panel" in paths
    assert "/v2/client" not in paths
    assert not settings.v2_identity_db.exists()
    assert not settings.v2_event_db.exists()


def test_disabling_v2_preserves_existing_identity_state(tmp_path: Path) -> None:
    enabled = _settings(tmp_path, enabled=True)
    token, identities = _pair(enabled)

    disabled = replace(enabled, v2_enabled=False)
    app = create_app(disabled)
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/v1/panel" in paths
    assert "/v2/client" not in paths
    assert identities.authenticate("panel:living", token)


def test_enabled_listener_authenticates_and_sends_welcome_snapshot(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)

    with TestClient(create_app(settings)) as client:
        with client.websocket_connect(
            "/v2/client", headers=_headers(token), subprotocols=["wyss-v2"]
        ) as websocket:
            websocket.send_json(_hello())
            welcome = websocket.receive_json()
            snapshot = websocket.receive_json()

    assert welcome["type"] == "session.welcome"
    assert welcome["payload"]["snapshot_required"] is True
    assert snapshot["type"] == "projection.snapshot"
    assert snapshot["payload"]["projection_version"] == 0


def test_resume_sends_only_events_after_cursor(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)
    store = SqliteEventStore(settings.v2_event_db)
    for number in (1, 2):
        store.append(
            EventDraft("home.entity.changed", "home", {"brightness": number}),
            f"event:{number}",
        )

    with TestClient(create_app(settings)) as client:
        with client.websocket_connect(
            "/v2/client", headers=_headers(token), subprotocols=["wyss-v2"]
        ) as websocket:
            websocket.send_json(_hello(last_event_id=1))
            welcome = websocket.receive_json()
            delta = websocket.receive_json()

    assert welcome["payload"]["snapshot_required"] is False
    assert delta["type"] == "projection.delta"
    assert delta["payload"]["event_id"] == 2
    assert delta["payload"]["changes"]["brightness"] == 2


def test_revocation_is_observed_on_the_next_message(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, identities = _pair(settings)

    with TestClient(create_app(settings)) as client:
        with client.websocket_connect(
            "/v2/client", headers=_headers(token), subprotocols=["wyss-v2"]
        ) as websocket:
            websocket.send_json(_hello())
            websocket.receive_json()
            websocket.receive_json()
            identities.revoke("panel:living")
            websocket.send_json(
                {
                    "v": 2,
                    "type": "session.heartbeat",
                    "message_id": "heartbeat:1",
                    "source": "panel:living",
                    "payload": {},
                }
            )
            with pytest.raises(WebSocketDisconnect) as disconnected:
                websocket.receive_json()

    assert disconnected.value.code == 4403


def test_non_session_action_is_rejected_without_execution(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)

    with TestClient(create_app(settings)) as client:
        with client.websocket_connect(
            "/v2/client", headers=_headers(token), subprotocols=["wyss-v2"]
        ) as websocket:
            websocket.send_json(_hello())
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(
                {
                    "v": 2,
                    "type": "home.command",
                    "message_id": "command:1",
                    "source": "panel:living",
                    "payload": {"entity_id": "light.living", "action": "turn_on"},
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "error"
    assert response["payload"]["code"] == "policy_rejected"
