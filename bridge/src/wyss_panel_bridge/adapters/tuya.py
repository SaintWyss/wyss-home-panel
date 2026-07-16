from __future__ import annotations

import asyncio
import time
from typing import Any

import tinytuya  # type: ignore[import-untyped]

from wyss_panel_bridge.domain.models import DeviceState, FastCommand


class TuyaGateway:
    """Yo mantengo el control LEDVANCE/Tuya dentro de la red local."""

    def __init__(
        self,
        entity_id: str,
        name: str,
        device_id: str,
        address: str,
        local_key: str,
        version: float = 3.3,
    ) -> None:
        self._entity_id = entity_id
        self._name = name
        self._device = tinytuya.Device(device_id, address, local_key)
        self._device.set_version(version)
        self._device.set_socketTimeout(1.0)
        self._device.set_socketRetryLimit(1)

    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]:
        if self._entity_id not in entities:
            return []
        return [await self._read()]

    async def execute(self, command: FastCommand) -> DeviceState:
        if command.entity_id != self._entity_id:
            raise RuntimeError("Yo no administro esa entidad Tuya")
        current = await self._read()
        values: dict[str, Any]
        if command.action == "turn_on":
            values = {"20": True}
        elif command.action == "turn_off":
            values = {"20": False}
        elif command.action == "toggle":
            values = {"20": not current.on}
        elif command.action == "set_brightness" and command.brightness is not None:
            raw = max(10, min(1000, command.brightness * 10))
            values = {"20": command.brightness > 0, "21": "white", "22": raw}
        else:
            raise RuntimeError("Yo no puedo ejecutar esa acción en Tuya")
        response = await asyncio.to_thread(self._device.set_multiple_values, values)
        if not isinstance(response, dict) or response.get("Error"):
            raise RuntimeError("Yo no recibí confirmación válida del foco Tuya")
        return await self._read()

    async def _read(self) -> DeviceState:
        response = await asyncio.to_thread(self._device.status)
        if not isinstance(response, dict) or response.get("Error"):
            return DeviceState(
                self._entity_id, self._name, False, False, 0, time.monotonic_ns()
            )
        dps = response.get("dps", {})
        power = bool(dps.get("20", False))
        brightness = max(0, min(100, round(int(dps.get("22", 0)) / 10)))
        return DeviceState(
            self._entity_id,
            self._name,
            True,
            power,
            brightness,
            time.monotonic_ns(),
        )
