"""Listener WebSocket v2 autenticado, reanudable y con proyección en vivo."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.application.event_backbone import ClientRateLimiter
from wyss_panel_bridge.application.identity_service import IdentityService
from wyss_panel_bridge.composition import V2Runtime
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.domain.conversation import ConversationError
from wyss_panel_bridge.domain.events import RateLimitExceeded
from wyss_panel_bridge.domain.lights import LightError
from wyss_panel_bridge.domain.media import MediaAction, MediaCommand, MediaError
from wyss_panel_bridge.domain.models import FastCommand
from wyss_panel_bridge.domain.protocol_v2 import ProtocolV2Error, ValidationCode, parse_envelope
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.domain.voice import VoiceError

_VOICE_ASSETS = Path(__file__).parent / "static" / "voice"


def _message(message_type: str, payload: dict[str, Any], **metadata: str | None) -> dict[str, Any]:
    message: dict[str, Any] = {
        "v": 2,
        "type": message_type,
        "message_id": f"edge:{secrets.token_hex(12)}",
        "source": "edge:home",
        "payload": payload,
    }
    message.update({key: value for key, value in metadata.items() if value is not None})
    return message


def _delta(event: ProjectionEvent) -> dict[str, Any]:
    return _message(
        "projection.delta",
        {
            "aggregate": event.aggregate,
            "revision": event.revision,
            "event_id": event.event_id,
            "changes": {"event_type": event.event_type, **event.payload},
        },
        correlation_id=event.correlation_id,
        causation_id=event.causation_id,
    )


@dataclass(slots=True)
class _Connection:
    client_id: str
    websocket: WebSocket
    last_event_id: int
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ready: bool = False
    pending: list[ProjectionEvent] = field(default_factory=list)


class _ClientHub:
    def __init__(self) -> None:
        self._connections: dict[str, _Connection] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        client_id: str,
        websocket: WebSocket,
        last_event_id: int,
    ) -> _Connection:
        connection = _Connection(client_id, websocket, last_event_id)
        async with self._lock:
            previous = self._connections.get(client_id)
            self._connections[client_id] = connection
        if previous is not None:
            await previous.websocket.close(code=4409, reason="session_replaced")
        return connection

    async def finish_initial(
        self,
        connection: _Connection,
        messages: list[dict[str, Any]],
        latest_event_id: int,
    ) -> None:
        async with connection.lock:
            for message in messages:
                await connection.websocket.send_json(message)
            async with self._lock:
                connection.last_event_id = latest_event_id
                connection.ready = True
                pending = sorted(
                    (
                        event
                        for event in connection.pending
                        if event.event_id > connection.last_event_id
                    ),
                    key=lambda event: event.event_id,
                )
                connection.pending.clear()
            for event in pending:
                await connection.websocket.send_json(_delta(event))
                connection.last_event_id = event.event_id

    async def broadcast(self, event: ProjectionEvent) -> None:
        async with self._lock:
            ready: list[_Connection] = []
            for connection in self._connections.values():
                if event.event_id <= connection.last_event_id:
                    continue
                if connection.ready:
                    ready.append(connection)
                else:
                    connection.pending.append(event)
        if ready:
            results = await asyncio.gather(
                *(self._send_event(connection, event) for connection in ready),
                return_exceptions=True,
            )
            for connection, result in zip(ready, results, strict=True):
                if isinstance(result, BaseException):
                    await self.remove(connection)

    @staticmethod
    async def send(connection: _Connection, message: dict[str, Any]) -> None:
        async with connection.lock:
            await connection.websocket.send_json(message)

    async def remove(self, connection: _Connection) -> None:
        async with self._lock:
            if self._connections.get(connection.client_id) is connection:
                del self._connections[connection.client_id]

    @staticmethod
    async def _send_event(connection: _Connection, event: ProjectionEvent) -> None:
        async with connection.lock:
            if event.event_id <= connection.last_event_id:
                return
            await connection.websocket.send_json(_delta(event))
            connection.last_event_id = event.event_id


def _projection_snapshot(payload: dict[str, Any], revision: int) -> dict[str, Any]:
    projection_payload: dict[str, Any] = {
        "assistant": {"state": "idle"},
        "home": {"entities": []},
        "spotify": {},
        "weather": {"days": []},
        "agenda": {"next": []},
        "timers": [],
        "cameras": [],
    }
    for aggregate, value in payload.items():
        if aggregate in projection_payload:
            projection_payload[aggregate] = value
    return _message(
        "projection.snapshot",
        {"projection_version": revision, **projection_payload},
    )


def _light_capability(client_id: str) -> str | None:
    prefix = client_id.partition(":")[0]
    return {
        "panel": "panel.light.fast",
        "android": "android.light.fast",
        "pc": "pc.light.fast",
    }.get(prefix)


def _conversation_capability(client_id: str, message_type: str) -> str | None:
    prefix = client_id.partition(":")[0]
    suffix = {
        "assistant.intent": "submit_intent",
        "plan.answer": "answer_plan",
    }.get(message_type)
    if prefix not in {"panel", "android", "pc"} or suffix is None:
        return None
    return f"{prefix}.{suffix}"


def _voice_capability(client_id: str) -> str | None:
    prefix = client_id.partition(":")[0]
    return f"{prefix}.voice" if prefix in {"android", "pc"} else None


def _media_capability(client_id: str) -> str | None:
    prefix = client_id.partition(":")[0]
    return f"{prefix}.spotify.control" if prefix in {"panel", "android", "pc"} else None


def _media_error_code(code: str) -> str:
    return {
        "reauthorization_required": "unauthenticated",
        "premium_or_scope_required": "forbidden",
        "device_inactive": "entity_unavailable",
        "invalid_message": "invalid_message",
        "conflict": "conflict",
        "rate_limited": "rate_limited",
        "policy_rejected": "policy_rejected",
    }.get(code, "provider_unavailable")


def _bearer(request: Request) -> tuple[str, str]:
    client_id = request.headers.get("x-wyss-client", "")
    authorization = request.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    return client_id, token


def _no_store(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(payload, status_code=status_code, headers={"Cache-Control": "no-store"})


def _wipe(buffer: bytearray) -> None:
    buffer[:] = b"\x00" * len(buffer)
    buffer.clear()


def create_v2_router(settings: Settings, runtime: V2Runtime) -> APIRouter:
    router = APIRouter()
    identities = SqliteIdentityStore(settings.v2_identity_db)
    identity_service = IdentityService(identities)
    ingress_limit = ClientRateLimiter(settings.v2_rate_limit, 1.0)
    hub = _ClientHub()
    runtime.lights.set_event_sink(hub.broadcast)
    runtime.conversation.set_event_sink(hub.broadcast)
    runtime.media.set_event_sink(hub.broadcast)

    @router.get("/v2/voice/config")
    async def voice_config() -> JSONResponse:
        return _no_store(
            {
                "enabled": settings.v2_voice_enabled,
                "max_bytes": settings.v2_voice_max_bytes,
                "requires_explicit_send": True,
                "retains_audio": False,
            }
        )

    @router.get("/v2/voice/")
    async def voice_client() -> FileResponse:
        return FileResponse(
            _VOICE_ASSETS / "index.html",
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'self'; connect-src 'self'; media-src 'none'; "
                    "script-src 'self'; style-src 'self'; object-src 'none'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                ),
                "Permissions-Policy": "microphone=(self)",
            },
        )

    @router.get("/v2/voice/app.js")
    async def voice_script() -> FileResponse:
        return FileResponse(_VOICE_ASSETS / "app.js", media_type="text/javascript")

    @router.get("/v2/voice/styles.css")
    async def voice_styles() -> FileResponse:
        return FileResponse(_VOICE_ASSETS / "styles.css", media_type="text/css")

    @router.post("/v2/voice/transcribe")
    async def transcribe_voice(request: Request) -> JSONResponse:
        if not settings.v2_voice_enabled:
            return _no_store(
                {"code": "policy_rejected", "message": "La entrada por voz está desactivada"},
                403,
            )
        client_id, token = _bearer(request)
        capability = _voice_capability(client_id)
        if not identity_service.authenticate(client_id, token):
            return _no_store({"code": "unauthenticated", "message": "Credenciales inválidas"}, 401)
        if capability is None or not identity_service.authenticate(client_id, token, capability):
            return _no_store({"code": "forbidden", "message": "Falta permiso de voz"}, 403)

        content_length = request.headers.get("content-length", "")
        if content_length.isdecimal() and int(content_length) > runtime.voice.max_bytes:
            return _no_store(
                {"code": "audio_too_large", "message": "El audio supera el límite permitido"},
                413,
            )
        audio = bytearray()
        async for chunk in request.stream():
            if len(audio) + len(chunk) > runtime.voice.max_bytes:
                _wipe(audio)
                return _no_store(
                    {
                        "code": "audio_too_large",
                        "message": "El audio supera el límite permitido",
                    },
                    413,
                )
            audio.extend(chunk)
        try:
            result = await runtime.voice.transcribe(
                audio,
                request.headers.get("content-type", "").lower(),
            )
        except VoiceError as error:
            status = {
                "unsupported_audio": 415,
                "audio_too_large": 413,
                "silence": 422,
                "noise": 422,
                "provider_timeout": 504,
                "provider_unavailable": 503,
            }.get(error.code, 422)
            return _no_store({"code": error.code, "message": str(error)}, status)
        return _no_store(
            {
                "transcript": result.text,
                "retained_audio": result.retained_audio,
                "requires_explicit_send": result.requires_explicit_send,
            }
        )

    @router.post("/v2/voice/intent")
    async def submit_reviewed_intent(request: Request) -> JSONResponse:
        client_id, token = _bearer(request)
        capability = _conversation_capability(client_id, "assistant.intent")
        if not identity_service.authenticate(client_id, token):
            return _no_store({"code": "unauthenticated", "message": "Credenciales inválidas"}, 401)
        if capability is None or not identity_service.authenticate(client_id, token, capability):
            return _no_store({"code": "forbidden", "message": "Falta permiso conversacional"}, 403)
        if not settings.v2_conversation_enabled:
            return _no_store(
                {"code": "policy_rejected", "message": "La conversación v2 está desactivada"},
                403,
            )
        raw = await request.body()
        if len(raw) > 8192:
            return _no_store(
                {"code": "message_too_large", "message": "Mensaje demasiado grande"}, 413
            )
        try:
            envelope = parse_envelope(raw.decode("utf-8"))
            if envelope.message_type != "assistant.intent" or envelope.source != client_id:
                raise ProtocolV2Error(ValidationCode.INVALID_MESSAGE)
            if envelope.payload["input"] == "voice" and not settings.v2_voice_enabled:
                return _no_store(
                    {"code": "policy_rejected", "message": "La entrada por voz está desactivada"},
                    403,
                )
            await runtime.conversation.submit(
                client_id,
                str(envelope.payload["request_id"]),
                str(envelope.payload["text"]),
                str(envelope.payload["input"]),
            )
        except ProtocolV2Error as error:
            return _no_store({"code": error.code.value, "message": str(error)}, 400)
        except ConversationError as error:
            return _no_store({"code": error.code, "message": str(error)}, 409)
        return _no_store({"accepted": True, "requires_explicit_send": True}, 202)

    @router.websocket("/v2/client")
    async def client(websocket: WebSocket) -> None:
        client_id = websocket.headers.get("x-wyss-client", "")
        authorization = websocket.headers.get("authorization", "")
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
        identity = identities.get(client_id)
        if identity is not None and identity.revoked:
            await websocket.close(code=4403, reason="device_revoked")
            return
        if not identity_service.authenticate(client_id, token):
            await websocket.close(code=4401, reason="unauthenticated")
            return
        await websocket.accept(subprotocol="wyss-v2")
        connection: _Connection | None = None
        try:
            raw_hello = await websocket.receive_text()
            ingress_limit.check(client_id)
            hello = parse_envelope(raw_hello)
            if hello.message_type != "session.hello" or hello.source != client_id:
                await websocket.close(code=4400, reason="invalid_message")
                return
            last_event_id = int(hello.payload["last_event_id"])
            connection = await hub.register(client_id, websocket, last_event_id)
            await runtime.lights.ensure_snapshot()
            if settings.v2_spotify_enabled:
                await runtime.media.ensure_snapshot()
            delivery = runtime.projections.delivery(client_id, last_event_id)
            messages = [
                _message(
                    "session.welcome",
                    {
                        "session_id": f"session:{secrets.token_hex(12)}",
                        "heartbeat_ms": int(settings.v2_heartbeat_seconds * 1000),
                        "max_message_bytes": 8192,
                        "snapshot_required": delivery.snapshot is not None,
                    },
                    correlation_id=hello.correlation_id or hello.message_id,
                    causation_id=hello.message_id,
                )
            ]
            if delivery.snapshot is not None:
                messages.append(
                    _projection_snapshot(
                        dict(delivery.snapshot.payload),
                        delivery.snapshot.revision,
                    )
                )
            else:
                messages.extend(_delta(event) for event in delivery.events)
            await hub.finish_initial(connection, messages, delivery.latest_event_id)

            while True:
                raw = await websocket.receive_text()
                if not identity_service.authenticate(client_id, token):
                    await websocket.close(code=4403, reason="device_revoked")
                    return
                ingress_limit.check(client_id)
                envelope = parse_envelope(raw)
                if envelope.source != client_id:
                    await websocket.close(code=4403, reason="forbidden")
                    return
                if envelope.message_type == "session.heartbeat":
                    await hub.send(
                        connection,
                        _message(
                            "session.heartbeat",
                            {},
                            correlation_id=envelope.correlation_id or envelope.message_id,
                            causation_id=envelope.message_id,
                        ),
                    )
                    continue
                if envelope.message_type == "home.command":
                    if not settings.v2_lights_enabled:
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {
                                    "code": "policy_rejected",
                                    "message": "La migración de luces v2 está desactivada",
                                },
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    capability = _light_capability(client_id)
                    if capability is None or not identity_service.authenticate(
                        client_id, token, capability
                    ):
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {"code": "forbidden", "message": "Falta permiso de luces"},
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    payload = envelope.payload
                    command = FastCommand(
                        request_id=str(payload["request_id"]),
                        entity_id=str(payload["entity_id"]),
                        action=str(payload["action"]),
                        brightness=int(payload["value"]) if "value" in payload else None,
                        rgb=int(payload["rgb"]) if "rgb" in payload else None,
                        idempotency_key=str(payload["idempotency_key"]),
                    )
                    try:
                        result = await runtime.lights.execute(
                            client_id,
                            command,
                            expected_revision=(
                                int(payload["expected_revision"])
                                if "expected_revision" in payload
                                else None
                            ),
                        )
                    except LightError as error:
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {"code": error.code, "message": str(error)},
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    await hub.send(
                        connection,
                        _message(
                            "execution.updated",
                            {
                                "request_id": command.request_id,
                                "state": "verified",
                                "event_id": result.event.event_id,
                                "replayed": result.replayed,
                            },
                            correlation_id=envelope.message_id,
                            causation_id=envelope.message_id,
                        ),
                    )
                    continue
                if envelope.message_type == "capability.command":
                    if not settings.v2_spotify_enabled:
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {
                                    "code": "policy_rejected",
                                    "message": "Spotify está desactivado",
                                },
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    capability = _media_capability(client_id)
                    if capability is None or not identity_service.authenticate(
                        client_id, token, capability
                    ):
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {"code": "forbidden", "message": "Falta permiso de Spotify"},
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    payload = envelope.payload
                    media_command = MediaCommand(
                        request_id=envelope.message_id,
                        idempotency_key=str(payload["idempotency_key"]),
                        action=MediaAction(str(payload["action"])),
                        value=int(payload["value"]) if "value" in payload else None,
                        device_id=(str(payload["device_id"]) if "device_id" in payload else None),
                        expected_revision=(
                            int(payload["expected_revision"])
                            if "expected_revision" in payload
                            else None
                        ),
                    )
                    try:
                        media_result = await runtime.media.execute(client_id, media_command)
                    except MediaError as error:
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {"code": _media_error_code(error.code), "message": str(error)},
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    await hub.send(
                        connection,
                        _message(
                            "execution.updated",
                            {
                                "request_id": media_command.request_id,
                                "state": "verified",
                                "event_id": media_result.event.event_id,
                                "replayed": media_result.replayed,
                            },
                            correlation_id=envelope.message_id,
                            causation_id=envelope.message_id,
                        ),
                    )
                    continue
                if envelope.message_type in {"assistant.intent", "plan.answer"}:
                    if not settings.v2_conversation_enabled:
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {
                                    "code": "policy_rejected",
                                    "message": "La conversación v2 está desactivada",
                                },
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    capability = _conversation_capability(client_id, envelope.message_type)
                    if capability is None or not identity_service.authenticate(
                        client_id, token, capability
                    ):
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {"code": "forbidden", "message": "Falta permiso conversacional"},
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                        continue
                    try:
                        if envelope.message_type == "assistant.intent":
                            await runtime.conversation.submit(
                                client_id,
                                str(envelope.payload["request_id"]),
                                str(envelope.payload["text"]),
                                str(envelope.payload["input"]),
                            )
                        else:
                            await runtime.conversation.answer(
                                client_id,
                                str(envelope.payload["plan_id"]),
                                str(envelope.payload["decision"]),
                                str(envelope.payload["confirmation"]),
                                int(envelope.payload["expected_revision"]),
                            )
                    except ConversationError as error:
                        await hub.send(
                            connection,
                            _message(
                                "error",
                                {"code": error.code, "message": str(error)},
                                correlation_id=envelope.message_id,
                                causation_id=envelope.message_id,
                            ),
                        )
                    continue
                await hub.send(
                    connection,
                    _message(
                        "error",
                        {
                            "code": "policy_rejected",
                            "message": "La acción debe pasar por el funnel de Wyss",
                        },
                        correlation_id=envelope.correlation_id or envelope.message_id,
                        causation_id=envelope.message_id,
                    ),
                )
        except RateLimitExceeded:
            await websocket.close(code=4429, reason="rate_limited")
        except ProtocolV2Error as error:
            await websocket.close(code=4400, reason=error.code.value)
        except WebSocketDisconnect:
            pass
        finally:
            if connection is not None:
                await hub.remove(connection)

    return router
