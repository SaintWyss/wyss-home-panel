from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from wyss_panel_bridge import __version__
from wyss_panel_bridge.adapters.legacy_devices import (
    LegacyDeviceGateway,
    ProjectedLegacyDeviceGateway,
)
from wyss_panel_bridge.adapters.wyss import WyssGateway
from wyss_panel_bridge.application.session_service import SessionService
from wyss_panel_bridge.composition import (
    CalendarPort,
    LightPort,
    MediaPort,
    NotificationPort,
    ReminderPort,
    SpeechPort,
    TimerPort,
    WeatherPort,
    build_light_gateway,
    build_v2_runtime,
)
from wyss_panel_bridge.config import Settings
from wyss_panel_bridge.ports import DeviceGateway, WyssGatewayPort


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


def create_app(
    settings: Settings,
    light_gateway: LightPort | None = None,
    orchestrator_gateway: WyssGatewayPort | None = None,
    speech_gateway: SpeechPort | None = None,
    media_gateway: MediaPort | None = None,
    weather_gateway: WeatherPort | None = None,
    calendar_gateway: CalendarPort | None = None,
    reminder_gateway: ReminderPort | None = None,
    notification_gateway: NotificationPort | None = None,
    timer_gateway: TimerPort | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Wyss Home Panel Bridge",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    light_gateway = light_gateway or build_light_gateway(settings)
    orchestrator = orchestrator_gateway or WyssGateway(settings.wyss_url, settings.wyss_token)
    runtime = (
        build_v2_runtime(
            settings,
            light_gateway,
            orchestrator,
            speech_gateway,
            media_gateway,
            weather_gateway,
            calendar_gateway,
            reminder_gateway,
            notification_gateway,
            timer_gateway,
        )
        if settings.v2_enabled
        else None
    )
    devices: DeviceGateway = (
        ProjectedLegacyDeviceGateway(runtime.lights)
        if runtime is not None and settings.v2_lights_enabled
        else LegacyDeviceGateway(light_gateway)
    )
    if settings.v2_enabled:
        from wyss_panel_bridge.v2_api import create_v2_router

        if runtime is None:
            raise RuntimeError("El runtime v2 no fue construido")
        app.include_router(create_v2_router(settings, runtime))

    @app.middleware("http")
    async def observe_http(request: Request, call_next: Any) -> Response:
        started = time.monotonic()
        correlation = request.headers.get("x-correlation-id", "http:anonymous")
        try:
            response = await call_next(request)
        except Exception:
            if runtime is not None:
                runtime.observability.observe(
                    "http.request",
                    (time.monotonic() - started) * 1000,
                    correlation_id=correlation,
                    status="error",
                )
            raise
        if runtime is not None:
            runtime.observability.observe(
                "http.request",
                (time.monotonic() - started) * 1000,
                correlation_id=correlation,
                status="ok" if response.status_code < 500 else "error",
            )
        return response

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
