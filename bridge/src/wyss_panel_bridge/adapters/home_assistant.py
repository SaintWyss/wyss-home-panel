from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace

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
        self._cache: dict[str, DeviceState] = {}
        self._revision = 0

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
            return self._unavailable(entity_id)
        if response.status_code == 404:
            return self._unavailable(entity_id)
        if response.is_error:
            return self._unavailable(entity_id)
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
        return self._stable(
            DeviceState(
                entity_id=entity_id,
                friendly_name=str(attributes.get("friendly_name") or entity_id),
                available=raw.get("state") not in {"unavailable", "unknown"},
                on=raw.get("state") == "on",
                brightness=round(raw_brightness * 100 / 255),
                revision=0,
                rgb=rgb,
            )
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _unavailable(self, entity_id: str) -> DeviceState:
        before = self._cache.get(entity_id)
        return self._stable(
            DeviceState(
                entity_id,
                before.friendly_name if before is not None else entity_id,
                False,
                before.on if before is not None else False,
                before.brightness if before is not None else 0,
                0,
                before.rgb if before is not None else None,
            )
        )

    def _stable(self, candidate: DeviceState) -> DeviceState:
        before = self._cache.get(candidate.entity_id)
        if before is not None and replace(before, revision=0) == candidate:
            return before
        self._revision += 1
        state = replace(candidate, revision=self._revision)
        self._cache[candidate.entity_id] = state
        return state
