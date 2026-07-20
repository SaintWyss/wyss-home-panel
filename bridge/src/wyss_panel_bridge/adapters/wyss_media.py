"""Adapter de media hacia Wyss; nunca recibe ni expone tokens OAuth."""

from __future__ import annotations

from typing import Any, cast

import httpx

from wyss_panel_bridge.domain.media import (
    MediaCommand,
    MediaDevice,
    MediaError,
    MediaState,
    MediaTrack,
)


class WyssMediaGateway:
    def __init__(
        self,
        url: str,
        token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
            transport=transport,
        )

    async def state(self) -> MediaState:
        try:
            response = await self._client.get("/api/media/spotify")
        except httpx.HTTPError as error:
            raise MediaError("provider_unavailable", "Wyss no respondió") from error
        return self._decode_response(response)

    async def execute(self, command: MediaCommand) -> MediaState:
        payload: dict[str, object] = {
            "request_id": command.request_id,
            "idempotency_key": command.idempotency_key,
            "action": command.action.value,
        }
        if command.value is not None:
            payload["value"] = command.value
        if command.device_id is not None:
            payload["device_id"] = command.device_id
        try:
            response = await self._client.post("/api/media/spotify/commands", json=payload)
        except httpx.HTTPError as error:
            raise MediaError("provider_unavailable", "Wyss no respondió") from error
        return self._decode_response(response)

    @classmethod
    def _decode_response(cls, response: httpx.Response) -> MediaState:
        if response.status_code == 204:
            return MediaState(
                linked=True,
                available=False,
                error_code="no_active_playback",
            )
        if response.status_code >= 400:
            retry_after = cls._retry_after(response)
            code = {
                401: "reauthorization_required",
                403: "premium_or_scope_required",
                404: "device_inactive",
                409: "conflict",
                429: "rate_limited",
            }.get(response.status_code, "provider_unavailable")
            raise MediaError(code, cls._safe_error_message(code), retry_after=retry_after)
        try:
            decoded = response.json()
        except ValueError as error:
            raise MediaError("provider_unavailable", "Wyss devolvió media inválida") from error
        if not isinstance(decoded, dict):
            raise MediaError("provider_unavailable", "Wyss devolvió media inválida")
        return cls._state(cast(dict[str, Any], decoded))

    @classmethod
    def _state(cls, raw: dict[str, Any]) -> MediaState:
        if not isinstance(raw.get("linked"), bool) or not isinstance(raw.get("available"), bool):
            raise MediaError("provider_unavailable", "Wyss devolvió media inválida")
        raw_device = raw.get("device")
        device = cls._device(raw_device) if isinstance(raw_device, dict) else None
        return MediaState(
            linked=raw["linked"],
            available=raw["available"],
            playing=raw.get("playing") is True,
            track_uri=cls._optional_text(raw.get("track_uri"), 256),
            title=cls._text(raw.get("title"), 180),
            artist=cls._text(raw.get("artist"), 180),
            progress_ms=cls._bounded_int(raw.get("progress_ms"), 86_400_000),
            duration_ms=cls._bounded_int(raw.get("duration_ms"), 86_400_000),
            favorite=raw.get("favorite") is True,
            device=device,
            queue=cls._queue(raw.get("queue")),
            error_code=cls._optional_text(raw.get("error_code"), 64),
            retry_after=cls._optional_bounded_int(raw.get("retry_after"), 86_400),
        )

    @classmethod
    def _queue(cls, raw: Any) -> tuple[MediaTrack, ...]:
        if not isinstance(raw, list):
            return ()
        tracks: list[MediaTrack] = []
        for item in raw[:5]:
            if not isinstance(item, dict):
                continue
            title = cls._text(item.get("title"), 180)
            if title:
                tracks.append(MediaTrack(title, cls._text(item.get("artist"), 180)))
        return tuple(tracks)

    @classmethod
    def _device(cls, raw: dict[str, Any]) -> MediaDevice:
        return MediaDevice(
            device_id=cls._text(raw.get("id"), 128),
            name=cls._text(raw.get("name"), 128),
            kind=cls._text(raw.get("type"), 64),
            active=raw.get("active") is True,
            restricted=raw.get("restricted") is True,
            supports_volume=raw.get("supports_volume") is True,
            volume=cls._optional_bounded_int(raw.get("volume"), 100),
        )

    @staticmethod
    def _text(value: Any, maximum: int) -> str:
        return value[:maximum] if isinstance(value, str) else ""

    @classmethod
    def _optional_text(cls, value: Any, maximum: int) -> str | None:
        text = cls._text(value, maximum)
        return text or None

    @staticmethod
    def _bounded_int(value: Any, maximum: int) -> int:
        valid = isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum
        return value if valid else 0

    @classmethod
    def _optional_bounded_int(cls, value: Any, maximum: int) -> int | None:
        if value is None:
            return None
        return cls._bounded_int(value, maximum)

    @staticmethod
    def _retry_after(response: httpx.Response) -> int | None:
        value = response.headers.get("retry-after", "")
        return min(int(value), 86_400) if value.isdecimal() else None

    @staticmethod
    def _safe_error_message(code: str) -> str:
        return {
            "reauthorization_required": "Spotify requiere volver a vincular la cuenta",
            "premium_or_scope_required": "Spotify Premium o sus permisos no están disponibles",
            "device_inactive": "Spotify no tiene un dispositivo activo",
            "conflict": "El estado de Spotify cambió; actualizá y reintentá",
            "rate_limited": "Spotify pidió esperar antes de reintentar",
        }.get(code, "Spotify no está disponible")
