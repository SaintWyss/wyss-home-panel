from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence

import httpx

from wyss_panel_bridge.domain.models import DeviceState, FastCommand


class HomeAssistantGateway:
    """Yo adapto el contrato del panel a la API local de Home Assistant."""

    def __init__(
        self,
        url: str,
        token: str,
        timeout_seconds: float = 2.0,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
            transport=transport,
        )
        self._locks: dict[str, asyncio.Lock] = {}

    async def snapshot(self, entities: Sequence[str]) -> list[DeviceState]:
        return [await self._state(entity) for entity in sorted(entities)]

    async def execute(self, command: FastCommand) -> list[DeviceState]:
        lock = self._locks.setdefault(command.entity_id, asyncio.Lock())
        async with lock:
            domain, _, _ = command.entity_id.partition(".")
            service = command.action
            payload: dict[str, object] = {"entity_id": command.entity_id}
            if service == "set_brightness":
                service = "turn_on"
                payload["brightness_pct"] = command.brightness
            elif service == "set_color":
                service = "turn_on"
                rgb = command.rgb or 0
                payload["rgb_color"] = [(rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF]
            elif service == "activate_scene":
                domain, service = "scene", "turn_on"
            try:
                response = await self._client.post(
                    f"/api/services/{domain}/{service}", json=payload
                )
            except httpx.HTTPError as error:
                raise RuntimeError("Yo no pude comunicarme con Home Assistant") from error
            if response.is_error:
                raise RuntimeError(f"Yo recibí HTTP {response.status_code} de Home Assistant")
            return [await self._state(command.entity_id)]

    async def _state(self, entity_id: str) -> DeviceState:
        try:
            response = await self._client.get(f"/api/states/{entity_id}")
        except httpx.HTTPError:
            return DeviceState(entity_id, entity_id, False, False, 0, time.monotonic_ns())
        if response.status_code == 404:
            return DeviceState(entity_id, entity_id, False, False, 0, time.monotonic_ns())
        if response.is_error:
            return DeviceState(entity_id, entity_id, False, False, 0, time.monotonic_ns())
        raw = response.json()
        attributes = raw.get("attributes", {})
        raw_brightness = int(attributes.get("brightness") or 0)
        raw_rgb = attributes.get("rgb_color")
        rgb = None
        if (
            isinstance(raw_rgb, Sequence)
            and not isinstance(raw_rgb, (str, bytes))
            and len(raw_rgb) == 3
        ):
            try:
                red, green, blue = (max(0, min(255, int(item))) for item in raw_rgb)
                rgb = (red << 16) | (green << 8) | blue
            except (TypeError, ValueError):
                rgb = None
        return DeviceState(
            entity_id=entity_id,
            friendly_name=str(attributes.get("friendly_name") or entity_id),
            available=raw.get("state") not in {"unavailable", "unknown"},
            on=raw.get("state") == "on",
            brightness=round(raw_brightness * 100 / 255),
            revision=time.monotonic_ns(),
            rgb=rgb,
        )

    async def close(self) -> None:
        await self._client.aclose()
