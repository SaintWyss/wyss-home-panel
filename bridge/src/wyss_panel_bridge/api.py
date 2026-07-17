from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from wyss_panel_bridge import __version__
from wyss_panel_bridge.adapters.legacy_devices import LegacyDeviceGateway
from wyss_panel_bridge.adapters.wyss import WyssGateway
from wyss_panel_bridge.application.session_service import SessionService
from wyss_panel_bridge.composition import build_light_gateway
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.ports import DeviceGateway


def _device_gateway(settings: Settings) -> DeviceGateway:
    return LegacyDeviceGateway(build_light_gateway(settings))


def _authorized(websocket: WebSocket, settings: Settings) -> bool:
    panel_id = websocket.headers.get("x-wyss-panel", "")
    authorization = websocket.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    digest = hashlib.sha256(token.encode()).hexdigest()
    return hmac.compare_digest(panel_id, settings.panel_id) and hmac.compare_digest(
        digest, settings.panel_token_sha256
    )


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="Wyss Home Panel Bridge",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    devices = _device_gateway(settings)
    orchestrator = WyssGateway(settings.wyss_url, settings.wyss_token)

    if settings.v2_enabled:
        from wyss_panel_bridge.v2_api import create_v2_router

        app.include_router(create_v2_router(settings))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.websocket("/v1/panel")
    async def panel(websocket: WebSocket) -> None:
        if not _authorized(websocket, settings):
            await websocket.close(code=4401, reason="Yo rechacé las credenciales")
            return
        await websocket.accept(subprotocol="arduino")
        service = SessionService(devices, orchestrator, settings.allowed_entities)
        send_lock = asyncio.Lock()

        async def send(payload: dict[str, Any]) -> None:
            async with send_lock:
                encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
                await websocket.send_text(encoded)

        async def synchronize() -> None:
            while True:
                await asyncio.sleep(2.0)
                await send(await service.initial_snapshot())

        sync_task = asyncio.create_task(synchronize(), name="panel-state-sync")
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw.encode()) > 8192:
                    reason = "Yo rechacé un mensaje demasiado grande"
                    await websocket.close(code=4409, reason=reason)
                    break
                try:
                    message = json.loads(raw)
                    if not isinstance(message, dict):
                        raise ValueError("Yo esperaba un objeto JSON")
                    responses = await service.handle(message)
                except (json.JSONDecodeError, ValueError, TypeError) as error:
                    responses = [
                        {"v": 1, "type": "error", "code": "invalid_message", "message": str(error)}
                    ]
                for response in responses:
                    await send(response)
        except WebSocketDisconnect:
            pass
        finally:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task

    return app


def main() -> None:
    config_path = Path(os.environ.get("WYSS_PANEL_CONFIG", "config/local.toml"))
    settings = Settings.load(config_path)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        ssl_certfile=str(settings.certfile),
        ssl_keyfile=str(settings.keyfile),
        server_header=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
