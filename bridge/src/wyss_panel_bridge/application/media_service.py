"""Proyección y ejecución serializada de Spotify mediante Wyss."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.media import MediaAction, MediaCommand, MediaError, MediaState
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports_v2 import EventStorePort, MediaPort

EventSink = Callable[[ProjectionEvent], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class MediaCommandResult:
    event: ProjectionEvent
    replayed: bool


class MediaService:
    def __init__(
        self, media: MediaPort, events: EventStorePort, *, max_replays: int = 2048
    ) -> None:
        if max_replays <= 0:
            raise ValueError("cache de media inválida")
        self._media = media
        self._events = events
        self._max_replays = max_replays
        self._lock = asyncio.Lock()
        self._revision = 0
        self._last_projection: dict[str, object] | None = None
        self._replays: OrderedDict[str, tuple[str, ProjectionEvent]] = OrderedDict()
        self._event_sink: EventSink | None = None

    def set_event_sink(self, sink: EventSink | None) -> None:
        self._event_sink = sink

    async def ensure_snapshot(self) -> ProjectionEvent | None:
        async with self._lock:
            try:
                state = await self._media.state()
            except MediaError as error:
                return await self._failure_event(error, "spotify:snapshot:error")
            return await self._state_event(state, "spotify:snapshot")

    async def execute(self, source: str, command: MediaCommand) -> MediaCommandResult:
        self._validate(command)
        fingerprint = self._fingerprint(command)
        async with self._lock:
            replay = self._replays.get(command.idempotency_key)
            if replay is not None:
                if replay[0] != fingerprint:
                    raise MediaError("conflict", "La clave idempotente ya identifica otra acción")
                self._replays.move_to_end(command.idempotency_key)
                return MediaCommandResult(replay[1], True)
            if (
                command.expected_revision is not None
                and command.expected_revision != self._revision
            ):
                raise MediaError("conflict", "El estado de Spotify cambió; actualizá y reintentá")
            try:
                state = await self._media.execute(command)
            except MediaError as error:
                await self._failure_event(error, f"{command.idempotency_key}:error")
                raise
            event = await self._state_event(
                state,
                command.idempotency_key,
                request_id=command.request_id,
                action=command.action.value,
                source=source,
                force=True,
            )
            if event is None:
                raise RuntimeError("La ejecución de media no produjo estado")
            self._replays[command.idempotency_key] = (fingerprint, event)
            self._replays.move_to_end(command.idempotency_key)
            while len(self._replays) > self._max_replays:
                self._replays.popitem(last=False)
            return MediaCommandResult(event, False)

    async def _state_event(
        self,
        state: MediaState,
        idempotency_key: str,
        *,
        request_id: str | None = None,
        action: str | None = None,
        source: str | None = None,
        force: bool = False,
    ) -> ProjectionEvent | None:
        payload: dict[str, object] = state.projection()
        if request_id is not None:
            payload["request_id"] = request_id
        if action is not None:
            payload["last_action"] = action
        if source is not None:
            payload["source"] = source
        return await self._publish_payload(payload, idempotency_key, force=force)

    async def _publish_payload(
        self,
        payload: dict[str, object],
        idempotency_key: str,
        *,
        force: bool,
    ) -> ProjectionEvent | None:
        if not force and payload == self._last_projection:
            return None
        event = self._events.append(
            EventDraft("spotify.state.changed", "spotify", payload),
            self._event_key(idempotency_key, payload),
        )
        self._revision = event.revision
        self._last_projection = dict(payload)
        await self._emit(event)
        return event

    async def _failure_event(self, error: MediaError, key: str) -> ProjectionEvent | None:
        payload = dict(self._last_projection or MediaState(False, False).projection())
        payload["available"] = False
        payload["error_code"] = error.code
        payload["retry_after"] = error.retry_after
        return await self._publish_payload(
            payload,
            key,
            force=payload != self._last_projection,
        )

    async def _emit(self, event: ProjectionEvent) -> None:
        if self._event_sink is not None:
            await self._event_sink(event)

    @staticmethod
    def _validate(command: MediaCommand) -> None:
        if command.action is MediaAction.SET_VOLUME:
            if (
                command.value is None
                or not 0 <= command.value <= 100
                or command.device_id is not None
            ):
                raise MediaError("invalid_message", "El volumen debe estar entre 0 y 100")
            return
        if command.action is MediaAction.TRANSFER_DEVICE:
            if not command.device_id or command.value is not None:
                raise MediaError("invalid_message", "Falta el dispositivo de destino")
            return
        if command.value is not None or command.device_id is not None:
            raise MediaError("invalid_message", "La acción de Spotify tiene parámetros inválidos")

    @staticmethod
    def _fingerprint(command: MediaCommand) -> str:
        encoded = json.dumps(
            {
                "action": command.action.value,
                "device_id": command.device_id,
                "expected_revision": command.expected_revision,
                "request_id": command.request_id,
                "value": command.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(encoded.encode()).hexdigest()

    @staticmethod
    def _event_key(prefix: str, payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        return f"spotify:{hashlib.sha256(prefix.encode()).hexdigest()[:24]}:{digest[:24]}"
