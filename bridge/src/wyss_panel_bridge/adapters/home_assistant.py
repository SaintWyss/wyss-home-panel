from __future__ import annotations

import time

import httpx

from wyss_panel_bridge.domain.models import DeviceState, FastCommand


class HomeAssistantGateway:
    """Yo adapto el contrato del panel a la API local de Home Assistant."""

    def __init__(self, url: str, token: str, timeout_seconds: float = 2.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
        )

    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]:
        return [await self._state(entity) for entity in sorted(entities)]

    async def execute(self, command: FastCommand) -> DeviceState:
        domain, _, _ = command.entity_id.partition(".")
        service = command.action
        payload: dict[str, object] = {"entity_id": command.entity_id}
        if service == "set_brightness":
            service = "turn_on"
            payload["brightness_pct"] = command.brightness
        elif service == "activate_scene":
            domain, service = "scene", "turn_on"
        response = await self._client.post(f"/api/services/{domain}/{service}", json=payload)
        if response.is_error:
            raise RuntimeError(f"Yo recibí HTTP {response.status_code} de Home Assistant")
        return await self._state(command.entity_id)

    async def _state(self, entity_id: str) -> DeviceState:
        response = await self._client.get(f"/api/states/{entity_id}")
        if response.status_code == 404:
            return DeviceState(entity_id, entity_id, False, False, 0, time.monotonic_ns())
        response.raise_for_status()
        raw = response.json()
        attributes = raw.get("attributes", {})
        raw_brightness = int(attributes.get("brightness") or 0)
        return DeviceState(
            entity_id=entity_id,
            friendly_name=str(attributes.get("friendly_name") or entity_id),
            available=raw.get("state") not in {"unavailable", "unknown"},
            on=raw.get("state") == "on",
            brightness=round(raw_brightness * 100 / 255),
            revision=time.monotonic_ns(),
        )
