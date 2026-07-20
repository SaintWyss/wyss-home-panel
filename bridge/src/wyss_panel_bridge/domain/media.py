"""Estado y comandos de media sin detalles OAuth ni del proveedor."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MediaAction(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    PREVIOUS = "previous"
    NEXT = "next"
    SET_VOLUME = "set_volume"
    TOGGLE_FAVORITE = "toggle_favorite"
    TRANSFER_DEVICE = "transfer_device"


class MediaError(RuntimeError):
    """Fallo de media seguro para mostrar y proyectar."""

    def __init__(self, code: str, message: str, *, retry_after: int | None = None) -> None:
        self.code = code
        self.retry_after = retry_after
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class MediaDevice:
    device_id: str
    name: str
    kind: str
    active: bool
    restricted: bool
    supports_volume: bool
    volume: int | None


@dataclass(frozen=True, slots=True)
class MediaTrack:
    title: str
    artist: str


@dataclass(frozen=True, slots=True)
class MediaState:
    linked: bool
    available: bool
    playing: bool = False
    track_uri: str | None = None
    title: str = ""
    artist: str = ""
    progress_ms: int = 0
    duration_ms: int = 0
    favorite: bool = False
    device: MediaDevice | None = None
    error_code: str | None = None
    retry_after: int | None = None
    queue: tuple[MediaTrack, ...] = ()

    def projection(self) -> dict[str, Any]:
        device = None
        if self.device is not None:
            device = {
                "id": self.device.device_id,
                "name": self.device.name,
                "type": self.device.kind,
                "active": self.device.active,
                "restricted": self.device.restricted,
                "supports_volume": self.device.supports_volume,
                "volume": self.device.volume,
            }
        return {
            "linked": self.linked,
            "available": self.available,
            "playing": self.playing,
            "track_uri": self.track_uri,
            "title": self.title,
            "artist": self.artist,
            "progress_ms": self.progress_ms,
            "duration_ms": self.duration_ms,
            "favorite": self.favorite,
            "device": device,
            "error_code": self.error_code,
            "retry_after": self.retry_after,
            "queue": [
                {"title": track.title, "artist": track.artist} for track in self.queue
            ],
        }


@dataclass(frozen=True, slots=True)
class MediaCommand:
    request_id: str
    idempotency_key: str
    action: MediaAction
    value: int | None = None
    device_id: str | None = None
    expected_revision: int | None = None
