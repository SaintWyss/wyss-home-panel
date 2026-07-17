"""Listener WebSocket v2 opt-in, autenticado y reanudable."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from wyss_panel_bridge.adapters.sqlite_events import SqliteEventStore
from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.adapters.sqlite_projection import SqliteProjectionStore
from wyss_panel_bridge.application.event_backbone import ClientRateLimiter
from wyss_panel_bridge.application.identity_service import IdentityService
from wyss_panel_bridge.application.projection_service import ProjectionCoordinator
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.domain.events import RateLimitExceeded
from wyss_panel_bridge.domain.protocol_v2 import ProtocolV2Error, parse_envelope
from wyss_panel_bridge.domain.v2_types import ProjectionEvent


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


def create_v2_router(settings: Settings) -> APIRouter:
    router = APIRouter()
    identities = SqliteIdentityStore(settings.v2_identity_db)
    identity_service = IdentityService(identities)
    event_store = SqliteEventStore(settings.v2_event_db)
    projections = ProjectionCoordinator(
        event_store,
        SqliteProjectionStore(settings.v2_projection_db),
        snapshot_fallback=settings.v2_snapshot_fallback,
    )
    ingress_limit = ClientRateLimiter(settings.v2_rate_limit, 1.0)

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
        try:
            raw_hello = await websocket.receive_text()
            ingress_limit.check(client_id)
            hello = parse_envelope(raw_hello)
            if hello.message_type != "session.hello" or hello.source != client_id:
                await websocket.close(code=4400, reason="invalid_message")
                return
            delivery = projections.delivery(client_id, int(hello.payload["last_event_id"]))
            await websocket.send_json(
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
            )
            if delivery.snapshot is not None:
                projection_payload: dict[str, Any] = {
                    "assistant": {"state": "idle"},
                    "home": {"entities": []},
                    "spotify": {},
                    "weather": {"days": []},
                    "agenda": {"next": []},
                    "timers": [],
                    "cameras": [],
                }
                for aggregate, value in delivery.snapshot.payload.items():
                    if aggregate in projection_payload:
                        projection_payload[aggregate] = value
                await websocket.send_json(
                    _message(
                        "projection.snapshot",
                        {
                            "projection_version": delivery.snapshot.revision,
                            **projection_payload,
                        },
                    )
                )
            else:
                for event in delivery.events:
                    await websocket.send_json(_delta(event))

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
                    await websocket.send_json(
                        _message(
                            "session.heartbeat",
                            {},
                            correlation_id=envelope.correlation_id or envelope.message_id,
                            causation_id=envelope.message_id,
                        )
                    )
                    continue
                await websocket.send_json(
                    _message(
                        "error",
                        {
                            "code": "policy_rejected",
                            "message": (
                                "El listener v2 no ejecuta acciones fuera del funnel de Wyss"
                            ),
                        },
                        correlation_id=envelope.correlation_id or envelope.message_id,
                        causation_id=envelope.message_id,
                    )
                )
        except RateLimitExceeded:
            await websocket.close(code=4429, reason="rate_limited")
        except ProtocolV2Error as error:
            await websocket.close(code=4400, reason=error.code.value)
        except WebSocketDisconnect:
            pass

    return router
