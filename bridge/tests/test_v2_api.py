from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.api import create_app
from wyss_panel_bridge.application.identity_service import IdentityService
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.domain.calendar import CalendarEvent, CalendarPage
from wyss_panel_bridge.domain.conversation import ConfirmationResult, ConversationTurn
from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.media import MediaAction, MediaCommand, MediaDevice, MediaState
from wyss_panel_bridge.domain.models import DeviceState, FastCommand, Plan, PlanStep, RiskLevel
from wyss_panel_bridge.domain.protocol_v2 import parse_envelope
from wyss_panel_bridge.domain.weather import ForecastDay, WeatherForecast
from wyss_panel_bridge.ports_v2 import CalendarPort, MediaPort, SpeechPort, WeatherPort


class FakeLights:
    def __init__(self) -> None:
        self.state = DeviceState("light.living", "Living", True, False, 40, 1)
        self.calls = 0

    async def snapshot(self, entity_ids: list[str]) -> list[DeviceState]:
        return [self.state] if self.state.entity_id in entity_ids else []

    async def execute(self, command: FastCommand) -> list[DeviceState]:
        self.calls += 1
        brightness = command.brightness if command.brightness is not None else self.state.brightness
        on = self.state.on
        if command.action == "turn_on":
            on = True
        elif command.action == "turn_off":
            on = False
        elif command.action == "toggle":
            on = not on
        elif command.action in {"set_brightness", "set_color"}:
            on = True
        self.state = replace(
            self.state,
            on=on,
            brightness=brightness,
            rgb=command.rgb if command.rgb is not None else self.state.rgb,
            revision=self.state.revision + 1,
        )
        return [self.state]


class FakeConversationWyss:
    def __init__(self) -> None:
        self.confirmations = 0
        self.turns = 0

    async def submit_intent(self, request_id: str, text: str) -> Plan | None:
        return (await self.submit_turn(request_id, text, "legacy")).plan

    async def answer_plan(self, plan_id: str, accepted: bool) -> None:
        return None

    async def submit_turn(self, request_id: str, text: str, source: str) -> ConversationTurn:
        self.turns += 1
        return ConversationTurn(
            "Preparé un plan seguro",
            "verified",
            Plan(
                "plan:shared",
                "Preparar living",
                RiskLevel.B,
                (PlanStep("Ajustar luz", "light.living"),),
                9_999_999_999,
            ),
        )

    async def confirm_turn(
        self,
        plan_id: str,
        accepted: bool,
        confirmation: str,
        expected_revision: int,
        source: str,
    ) -> ConfirmationResult:
        self.confirmations += 1
        return ConfirmationResult("Plan verificado", "verified", True)


class FakeSpeech:
    def __init__(self, transcript: str = "Prepará el living") -> None:
        self.transcript = transcript
        self.calls = 0

    async def transcribe(self, audio: memoryview, content_type: str) -> str:
        assert bytes(audio) == b"audio-local"
        assert content_type == "audio/webm"
        self.calls += 1
        return self.transcript


class FakeMedia:
    def __init__(self) -> None:
        self.calls = 0
        self.state_value = MediaState(
            linked=True,
            available=True,
            playing=False,
            track_uri="spotify:track:test",
            title="Tema seguro",
            artist="Artista",
            progress_ms=2_000,
            duration_ms=120_000,
            device=MediaDevice("desk", "Escritorio", "Computer", True, False, True, 25),
        )

    async def state(self) -> MediaState:
        return self.state_value

    async def execute(self, command: MediaCommand) -> MediaState:
        self.calls += 1
        self.state_value = replace(
            self.state_value,
            playing=command.action is MediaAction.PLAY,
        )
        return self.state_value


class FakeWeather:
    def __init__(self) -> None:
        self.calls = 0

    async def forecast(self, location: str, days: int) -> WeatherForecast:
        assert location == "Resistencia, Chaco" and days == 7
        self.calls += 1
        daily = ForecastDay("2026-07-17", 0, "despejado", 15, 28, 0, 0, 12)
        return WeatherForecast(
            location=location,
            timezone="America/Argentina/Cordoba",
            provider="open-meteo",
            observed_at="2026-07-17T20:45",
            temperature=28.5,
            apparent_temperature=29.1,
            code=0,
            condition="despejado",
            wind_kmh=8.2,
            is_day=True,
            days=(daily,) * 7,
            fetched_at=1000,
        )


class FakeCalendar:
    def __init__(self) -> None:
        self.calls = 0

    async def page(self, sync_token: str | None, page_token: str | None) -> CalendarPage:
        assert sync_token is None and page_token is None
        self.calls += 1
        event = CalendarEvent(
            "event-1",
            '"event-1-1"',
            "Reunión de producto",
            "2026-07-18T10:00:00-03:00",
            "2026-07-18T11:00:00-03:00",
            "America/Argentina/Cordoba",
            False,
            updated_at="2026-07-18T12:00:00Z",
        )
        return CalendarPage((event,), None, "cursor-1")


def _app(
    settings: Settings,
    lights: FakeLights | None = None,
    orchestrator: FakeConversationWyss | None = None,
    speech: SpeechPort | None = None,
    media: MediaPort | None = None,
    weather: WeatherPort | None = None,
    calendar: CalendarPort | None = None,
) -> FastAPI:
    return create_app(
        settings, lights or FakeLights(), orchestrator, speech, media, weather, calendar
    )


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
        v2_projection_db=tmp_path / "projections.sqlite3",
        v2_light_audit_db=tmp_path / "light-audit.sqlite3",
        v2_weather_cache_db=tmp_path / "weather-cache.sqlite3",
        v2_calendar_cache_db=tmp_path / "calendar-cache.sqlite3",
        v2_lights_enabled=enabled,
        v2_conversation_enabled=enabled,
    )


def _pair(settings: Settings) -> tuple[str, IdentityService]:
    service = IdentityService(SqliteIdentityStore(settings.v2_identity_db))
    token = service.pair("panel:living", {"panel.read_projection"})
    return token, service


def _pair_as(settings: Settings, client_id: str, capability: str) -> str:
    service = IdentityService(SqliteIdentityStore(settings.v2_identity_db))
    return service.pair(client_id, {"panel.read_projection", capability})


def _pair_with(settings: Settings, client_id: str, capabilities: set[str]) -> str:
    service = IdentityService(SqliteIdentityStore(settings.v2_identity_db))
    return service.pair(client_id, {"panel.read_projection", *capabilities})


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


def _hello_as(client_id: str, number: int = 1) -> dict[str, object]:
    return {
        "v": 2,
        "type": "session.hello",
        "message_id": f"hello:{client_id}:{number}",
        "source": client_id,
        "payload": {
            "firmware": "2.0.0",
            "capabilities": ["ui.core", "light.fast"],
            "last_event_id": 0,
        },
    }


def _headers(token: str) -> dict[str, str]:
    return {"x-wyss-client": "panel:living", "authorization": f"Bearer {token}"}


def _headers_as(client_id: str, token: str) -> dict[str, str]:
    return {"x-wyss-client": client_id, "authorization": f"Bearer {token}"}


def _command(
    source: str,
    number: int,
    action: str,
    *,
    value: int | None = None,
    rgb: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "request_id": f"request:{source}:{number}",
        "idempotency_key": f"{source}:light:{number}",
        "entity_id": "light.living",
        "action": action,
    }
    if value is not None:
        payload["value"] = value
    if rgb is not None:
        payload["rgb"] = rgb
    return {
        "v": 2,
        "type": "home.command",
        "message_id": f"message:{source}:{number}",
        "source": source,
        "payload": payload,
    }


def _spotify_command(source: str, number: int, action: str = "play") -> dict[str, object]:
    return {
        "v": 2,
        "type": "capability.command",
        "message_id": f"message:{source}:spotify:{number}",
        "source": source,
        "payload": {
            "capability": "spotify",
            "action": action,
            "idempotency_key": f"{source}:spotify:{number}",
        },
    }


def _intent(source: str, number: int = 1) -> dict[str, object]:
    return {
        "v": 2,
        "type": "assistant.intent",
        "message_id": f"message:{source}:intent:{number}",
        "source": source,
        "payload": {
            "request_id": f"request:{source}:intent:{number}",
            "text": "Prepará el living",
            "input": "text",
        },
    }


def _answer(source: str, number: int = 1) -> dict[str, object]:
    return {
        "v": 2,
        "type": "plan.answer",
        "message_id": f"message:{source}:answer:{number}",
        "source": source,
        "payload": {
            "plan_id": "plan:shared",
            "decision": "approve",
            "confirmation": "CONFIRMAR",
            "expected_revision": 1,
        },
    }


def test_feature_flag_keeps_v1_and_avoids_v2_state_when_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=False)
    app = _app(settings)
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/v1/panel" in paths
    assert "/v2/client" not in paths
    assert not settings.v2_identity_db.exists()
    assert not settings.v2_event_db.exists()
    assert not settings.v2_projection_db.exists()
    assert not settings.v2_light_audit_db.exists()


def test_disabling_v2_preserves_existing_identity_state(tmp_path: Path) -> None:
    enabled = _settings(tmp_path, enabled=True)
    token, identities = _pair(enabled)

    disabled = replace(enabled, v2_enabled=False)
    app = _app(disabled)
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/v1/panel" in paths
    assert "/v2/client" not in paths
    assert identities.authenticate("panel:living", token)


def test_enabled_listener_authenticates_and_sends_welcome_snapshot(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)
    SqliteEventStore(settings.v2_event_db).append(
        EventDraft("system.internal", "internal", {"private": "not-projected"}),
        "internal:1",
    )

    with TestClient(_app(settings)) as client:
        with client.websocket_connect(
            "/v2/client", headers=_headers(token), subprotocols=["wyss-v2"]
        ) as websocket:
            websocket.send_json(_hello())
            welcome = websocket.receive_json()
            snapshot = websocket.receive_json()

    assert welcome["type"] == "session.welcome"
    assert welcome["payload"]["snapshot_required"] is True
    assert snapshot["type"] == "projection.snapshot"
    assert snapshot["payload"]["projection_version"] == 2
    assert "internal" not in snapshot["payload"]
    assert parse_envelope(json.dumps(snapshot)).message_type == "projection.snapshot"


def test_resume_sends_only_events_after_cursor(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)
    store = SqliteEventStore(settings.v2_event_db)
    for number in (1, 2):
        store.append(
            EventDraft("home.entity.changed", "home", {"brightness": number}),
            f"event:{number}",
        )

    with TestClient(_app(settings)) as client:
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

    with TestClient(_app(settings)) as client:
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


def test_light_action_without_capability_is_rejected_without_execution(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)

    with TestClient(_app(settings)) as client:
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
                    "payload": {
                        "request_id": "request:1",
                        "idempotency_key": "panel:1",
                        "entity_id": "light.living",
                        "action": "turn_on",
                    },
                }
            )
            response = websocket.receive_json()

    assert response["type"] == "error"
    assert response["payload"]["code"] == "forbidden"


def test_conversation_without_capability_is_rejected_before_wyss(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token, _ = _pair(settings)
    wyss = FakeConversationWyss()

    with TestClient(_app(settings, orchestrator=wyss)) as client:
        with client.websocket_connect(
            "/v2/client", headers=_headers(token), subprotocols=["wyss-v2"]
        ) as websocket:
            websocket.send_json(_hello())
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(_intent("panel:living"))
            response = websocket.receive_json()

    assert response["type"] == "error"
    assert response["payload"]["code"] == "forbidden"
    assert wyss.turns == 0


def test_pc_android_and_panel_receive_each_verified_light_change_live(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    lights = FakeLights()
    clients = {
        "pc:desk": _pair_as(settings, "pc:desk", "pc.light.fast"),
        "android:phone": _pair_as(settings, "android:phone", "android.light.fast"),
        "panel:living": _pair_as(settings, "panel:living", "panel.light.fast"),
    }

    with TestClient(_app(settings, lights)) as client:
        with (
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("pc:desk", clients["pc:desk"]),
                subprotocols=["wyss-v2"],
            ) as pc,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("android:phone", clients["android:phone"]),
                subprotocols=["wyss-v2"],
            ) as android,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("panel:living", clients["panel:living"]),
                subprotocols=["wyss-v2"],
            ) as panel,
        ):
            sockets = {"pc:desk": pc, "android:phone": android, "panel:living": panel}
            for client_id, websocket in sockets.items():
                websocket.send_json(_hello_as(client_id))
                assert websocket.receive_json()["type"] == "session.welcome"
                assert websocket.receive_json()["type"] == "projection.snapshot"

            scenarios = (
                ("pc:desk", _command("pc:desk", 1, "set_brightness", value=72)),
                ("android:phone", _command("android:phone", 1, "set_color", rgb=0x3366CC)),
                ("panel:living", _command("panel:living", 1, "turn_off")),
            )
            observed_event_ids: list[int] = []
            for origin, command in scenarios:
                sockets[origin].send_json(command)
                deltas = {
                    client_id: websocket.receive_json() for client_id, websocket in sockets.items()
                }
                execution = sockets[origin].receive_json()

                assert {message["type"] for message in deltas.values()} == {"projection.delta"}
                event_ids = {message["payload"]["event_id"] for message in deltas.values()}
                assert len(event_ids) == 1
                observed_event_ids.append(next(iter(event_ids)))
                assert execution["type"] == "execution.updated"
                assert execution["payload"]["replayed"] is False

            replay = _command("pc:desk", 1, "set_brightness", value=72)
            replay["message_id"] = "message:pc:desk:replay"
            pc.send_json(replay)
            replay_result = pc.receive_json()

    assert observed_event_ids == sorted(observed_event_ids)
    assert len(set(observed_event_ids)) == 3
    assert replay_result["type"] == "execution.updated"
    assert replay_result["payload"]["replayed"] is True
    assert lights.calls == 3


def test_pc_android_and_panel_converge_on_spotify_without_provider_tokens(
    tmp_path: Path,
) -> None:
    settings = replace(
        _settings(tmp_path, enabled=True),
        v2_spotify_enabled=True,
        v2_spotify_approved_scopes=frozenset(
            {
                "user-read-playback-state",
                "user-modify-playback-state",
                "user-library-read",
                "user-library-modify",
            }
        ),
    )
    media = FakeMedia()
    clients = {
        "pc:desk": _pair_as(settings, "pc:desk", "pc.spotify.control"),
        "android:phone": _pair_as(settings, "android:phone", "android.spotify.control"),
        "panel:living": _pair_as(settings, "panel:living", "panel.spotify.control"),
    }

    with TestClient(_app(settings, media=media)) as client:
        with (
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("pc:desk", clients["pc:desk"]),
                subprotocols=["wyss-v2"],
            ) as pc,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("android:phone", clients["android:phone"]),
                subprotocols=["wyss-v2"],
            ) as android,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("panel:living", clients["panel:living"]),
                subprotocols=["wyss-v2"],
            ) as panel,
        ):
            sockets = {"pc:desk": pc, "android:phone": android, "panel:living": panel}
            snapshots = []
            for client_id, websocket in sockets.items():
                websocket.send_json(_hello_as(client_id))
                assert websocket.receive_json()["type"] == "session.welcome"
                snapshot = websocket.receive_json()
                assert snapshot["type"] == "projection.snapshot"
                snapshots.append(snapshot)

            pc.send_json(_spotify_command("pc:desk", 1))
            deltas = [websocket.receive_json() for websocket in sockets.values()]
            execution = pc.receive_json()

    assert all(message["payload"]["spotify"]["title"] == "Tema seguro" for message in snapshots)
    assert {message["payload"]["event_id"] for message in deltas} == {3}
    assert all(message["payload"]["aggregate"] == "spotify" for message in deltas)
    assert all(message["payload"]["changes"]["playing"] is True for message in deltas)
    assert execution["type"] == "execution.updated"
    assert media.calls == 1
    serialized = json.dumps([snapshots, deltas, execution])
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "service-token" not in serialized


def test_pc_android_and_panel_receive_same_seven_day_weather_projection(
    tmp_path: Path,
) -> None:
    settings = replace(_settings(tmp_path, enabled=True), v2_weather_enabled=True)
    weather = FakeWeather()
    clients = {
        client_id: _pair(settings)[0]
        if client_id == "panel:living"
        else _pair_as(settings, client_id, "panel.read_projection")
        for client_id in ("panel:living", "pc:desk", "android:phone")
    }

    with TestClient(_app(settings, weather=weather)) as client:
        with (
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("pc:desk", clients["pc:desk"]),
                subprotocols=["wyss-v2"],
            ) as pc,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("android:phone", clients["android:phone"]),
                subprotocols=["wyss-v2"],
            ) as android,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("panel:living", clients["panel:living"]),
                subprotocols=["wyss-v2"],
            ) as panel,
        ):
            snapshots = []
            for client_id, websocket in {
                "pc:desk": pc,
                "android:phone": android,
                "panel:living": panel,
            }.items():
                websocket.send_json(_hello_as(client_id))
                assert websocket.receive_json()["type"] == "session.welcome"
                snapshots.append(websocket.receive_json())

    projections = [message["payload"]["weather"] for message in snapshots]
    assert all(projection["location"] == "Resistencia, Chaco" for projection in projections)
    assert all(projection["timezone"] == "America/Argentina/Cordoba" for projection in projections)
    assert all(len(projection["days"]) == 7 for projection in projections)
    assert all(projection["current"]["condition"] == "despejado" for projection in projections)
    assert weather.calls == 1


def test_connected_panel_refreshes_weather_without_reconnecting(tmp_path: Path) -> None:
    settings = replace(
        _settings(tmp_path, enabled=True),
        v2_weather_enabled=True,
        v2_weather_refresh_seconds=0.02,
        v2_weather_max_stale_seconds=1.0,
    )
    weather = FakeWeather()
    token = _pair(settings)[0]

    with TestClient(_app(settings, weather=weather)) as client:
        with client.websocket_connect(
            "/v2/client",
            headers=_headers(token),
            subprotocols=["wyss-v2"],
        ) as websocket:
            websocket.send_json(_hello())
            assert websocket.receive_json()["type"] == "session.welcome"
            assert websocket.receive_json()["type"] == "projection.snapshot"
            time.sleep(0.05)
            websocket.send_json(
                {
                    "v": 2,
                    "type": "session.heartbeat",
                    "message_id": "heartbeat:1",
                    "source": "panel:living",
                    "payload": {},
                }
            )
            received_types = [websocket.receive_json()["type"]]
            if "session.heartbeat" not in received_types:
                received_types.append(websocket.receive_json()["type"])
            assert "session.heartbeat" in received_types

    assert weather.calls >= 2


def test_pc_android_and_panel_receive_same_calendar_projection(tmp_path: Path) -> None:
    settings = replace(
        _settings(tmp_path, enabled=True),
        v2_calendar_enabled=True,
        v2_calendar_access="read",
        v2_calendar_approved_scopes=frozenset(
            {"https://www.googleapis.com/auth/calendar.events.owned.readonly"}
        ),
    )
    calendar = FakeCalendar()
    clients = {
        client_id: _pair(settings)[0]
        if client_id == "panel:living"
        else _pair_as(settings, client_id, "panel.read_projection")
        for client_id in ("panel:living", "pc:desk", "android:phone")
    }

    with TestClient(_app(settings, calendar=calendar)) as client:
        with (
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("pc:desk", clients["pc:desk"]),
                subprotocols=["wyss-v2"],
            ) as pc,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("android:phone", clients["android:phone"]),
                subprotocols=["wyss-v2"],
            ) as android,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("panel:living", clients["panel:living"]),
                subprotocols=["wyss-v2"],
            ) as panel,
        ):
            snapshots = []
            for client_id, websocket in {
                "pc:desk": pc,
                "android:phone": android,
                "panel:living": panel,
            }.items():
                websocket.send_json(_hello_as(client_id))
                assert websocket.receive_json()["type"] == "session.welcome"
                snapshots.append(websocket.receive_json())

    agendas = [message["payload"]["agenda"] for message in snapshots]
    assert all(agenda["timezone"] == "America/Argentina/Cordoba" for agenda in agendas)
    assert all(agenda["events"][0]["title"] == "Reunión de producto" for agenda in agendas)
    assert all(agenda["write_enabled"] is False for agenda in agendas)
    assert calendar.calls == 1
    serialized = json.dumps(agendas)
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized


def test_spotify_flag_rolls_back_to_shell_without_calling_provider(tmp_path: Path) -> None:
    settings = _settings(tmp_path, enabled=True)
    token = _pair_as(settings, "panel:living", "panel.spotify.control")
    media = FakeMedia()

    with TestClient(_app(settings, media=media)) as client:
        assert client.get("/health").status_code == 200
        with client.websocket_connect(
            "/v2/client",
            headers=_headers_as("panel:living", token),
            subprotocols=["wyss-v2"],
        ) as websocket:
            websocket.send_json(_hello_as("panel:living"))
            websocket.receive_json()
            snapshot = websocket.receive_json()
            websocket.send_json(_spotify_command("panel:living", 1))
            rejected = websocket.receive_json()

    assert snapshot["payload"]["spotify"] == {}
    assert rejected["type"] == "error"
    assert rejected["payload"]["code"] == "policy_rejected"
    assert media.calls == 0
    assert not settings.v2_weather_cache_db.exists()


def test_light_migration_flag_rolls_back_to_read_only_v2_without_deleting_state(
    tmp_path: Path,
) -> None:
    enabled = _settings(tmp_path, enabled=True)
    settings = replace(enabled, v2_lights_enabled=False)
    token = _pair_as(settings, "panel:living", "panel.light.fast")
    lights = FakeLights()

    with TestClient(_app(settings, lights)) as client:
        with client.websocket_connect(
            "/v2/client",
            headers=_headers_as("panel:living", token),
            subprotocols=["wyss-v2"],
        ) as websocket:
            websocket.send_json(_hello_as("panel:living"))
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(_command("panel:living", 1, "turn_on"))
            rejected = websocket.receive_json()

    assert rejected["type"] == "error"
    assert rejected["payload"]["code"] == "policy_rejected"
    assert lights.calls == 0
    assert settings.v2_identity_db.exists()
    assert settings.v2_event_db.exists()
    assert settings.v2_light_audit_db.exists()


def test_conversation_and_confirmation_converge_live_on_all_three_clients(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, enabled=True)
    wyss = FakeConversationWyss()
    clients = {
        "pc:desk": _pair_with(settings, "pc:desk", {"pc.submit_intent", "pc.answer_plan"}),
        "android:phone": _pair_with(
            settings,
            "android:phone",
            {"android.submit_intent", "android.answer_plan"},
        ),
        "panel:living": _pair_with(
            settings,
            "panel:living",
            {"panel.submit_intent", "panel.answer_plan"},
        ),
    }

    with TestClient(_app(settings, orchestrator=wyss)) as client:
        with (
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("pc:desk", clients["pc:desk"]),
                subprotocols=["wyss-v2"],
            ) as pc,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("android:phone", clients["android:phone"]),
                subprotocols=["wyss-v2"],
            ) as android,
            client.websocket_connect(
                "/v2/client",
                headers=_headers_as("panel:living", clients["panel:living"]),
                subprotocols=["wyss-v2"],
            ) as panel,
        ):
            sockets = {"pc:desk": pc, "android:phone": android, "panel:living": panel}
            for client_id, websocket in sockets.items():
                websocket.send_json(_hello_as(client_id))
                assert websocket.receive_json()["type"] == "session.welcome"
                assert websocket.receive_json()["type"] == "projection.snapshot"

            pc.send_json(_intent("pc:desk"))
            proposed: dict[str, list[dict[str, object]]] = {
                client_id: [websocket.receive_json() for _ in range(4)]
                for client_id, websocket in sockets.items()
            }
            assert all(
                [str(message["payload"]["changes"]["event_type"]) for message in messages]
                == [
                    "assistant.state.changed",
                    "assistant.response.delta",
                    "assistant.response.completed",
                    "plan.proposed",
                ]
                for messages in proposed.values()
            )
            assert all(
                messages[-1]["payload"]["changes"]["state"] == "awaiting_confirmation"
                for messages in proposed.values()
            )

            android.send_json(_answer("android:phone"))
            resolved: dict[str, list[dict[str, object]]] = {
                client_id: [websocket.receive_json() for _ in range(5)]
                for client_id, websocket in sockets.items()
            }
            expected = [
                "plan.resolved",
                "assistant.state.changed",
                "assistant.response.delta",
                "assistant.response.completed",
                "assistant.state.changed",
            ]
            assert all(
                [str(message["payload"]["changes"]["event_type"]) for message in messages]
                == expected
                for messages in resolved.values()
            )
            assert all(
                messages[-1]["payload"]["changes"]["state"] == "verified"
                for messages in resolved.values()
            )

            panel.send_json(_answer("panel:living", 2))
            duplicate = panel.receive_json()

    assert duplicate["type"] == "error"
    assert duplicate["payload"]["code"] == "already_resolved"
    assert wyss.confirmations == 1


def test_voice_client_transcribes_without_implicit_send_then_submits_reviewed_text(
    tmp_path: Path,
) -> None:
    settings = replace(_settings(tmp_path, enabled=True), v2_voice_enabled=True)
    token = _pair_with(settings, "pc:desk", {"pc.voice", "pc.submit_intent"})
    speech = FakeSpeech()
    wyss = FakeConversationWyss()

    with TestClient(_app(settings, orchestrator=wyss, speech=speech)) as client:
        page = client.get("/v2/voice/")
        assert page.status_code == 200
        assert "Mantené para hablar" in page.text
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]

        transcription = client.post(
            "/v2/voice/transcribe",
            content=b"audio-local",
            headers={
                **_headers_as("pc:desk", token),
                "content-type": "audio/webm",
            },
        )
        assert transcription.status_code == 200
        assert transcription.json() == {
            "transcript": "Prepará el living",
            "retained_audio": False,
            "requires_explicit_send": True,
        }
        assert speech.calls == 1
        assert wyss.turns == 0
        assert SqliteEventStore(settings.v2_event_db).latest_event_id() == 0

        script = client.get("/v2/voice/app.js")
        assert script.status_code == 200
        assert "getUserMedia" in script.text
        assert "pointerdown" in script.text and "pointerup" in script.text
        assert "visibilitychange" in script.text
        assert "sessionStorage" in script.text
        assert "localStorage" not in script.text

        reviewed = client.post(
            "/v2/voice/intent",
            json={
                "v": 2,
                "type": "assistant.intent",
                "message_id": "message:pc:voice:1",
                "source": "pc:desk",
                "payload": {
                    "request_id": "request:pc:voice:1",
                    "text": "Prepará sólo el living",
                    "input": "voice",
                },
            },
            headers=_headers_as("pc:desk", token),
        )
        assert reviewed.status_code == 202
        assert reviewed.json()["accepted"] is True
        assert wyss.turns == 1


def test_voice_permission_and_feature_flag_fail_closed_but_text_remains(
    tmp_path: Path,
) -> None:
    enabled = replace(_settings(tmp_path, enabled=True), v2_voice_enabled=True)
    no_voice_token = _pair_with(enabled, "android:phone", {"android.submit_intent"})
    speech = FakeSpeech()

    with TestClient(_app(enabled, speech=speech)) as client:
        forbidden = client.post(
            "/v2/voice/transcribe",
            content=b"audio-local",
            headers={
                **_headers_as("android:phone", no_voice_token),
                "content-type": "audio/webm",
            },
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "forbidden"
        assert speech.calls == 0

    disabled = replace(enabled, v2_voice_enabled=False)
    wyss = FakeConversationWyss()
    with TestClient(_app(disabled, orchestrator=wyss, speech=speech)) as client:
        unavailable = client.post(
            "/v2/voice/transcribe",
            content=b"audio-local",
            headers={
                **_headers_as("android:phone", no_voice_token),
                "content-type": "audio/webm",
            },
        )
        assert unavailable.status_code == 403
        assert unavailable.json()["code"] == "policy_rejected"

        text = client.post(
            "/v2/voice/intent",
            json={
                "v": 2,
                "type": "assistant.intent",
                "message_id": "message:android:text:1",
                "source": "android:phone",
                "payload": {
                    "request_id": "request:android:text:1",
                    "text": "Usá el camino de texto",
                    "input": "text",
                },
            },
            headers=_headers_as("android:phone", no_voice_token),
        )
        assert text.status_code == 202
        assert wyss.turns == 1
