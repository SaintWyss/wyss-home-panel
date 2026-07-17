from __future__ import annotations

from wyss_panel_bridge.domain.models import DeviceState, FastCommand
from wyss_panel_bridge.ports_v2 import LightPort


class LegacyDeviceGateway:
    """Mantiene el contrato v1 sobre el nuevo port multientidad."""

    def __init__(self, lights: LightPort) -> None:
        self._lights = lights

    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]:
        return list(await self._lights.snapshot(sorted(entities)))

    async def execute(self, command: FastCommand) -> DeviceState:
        states = list(await self._lights.execute(command))
        if not states:
            raise RuntimeError("Yo no recibí estado verificado de la luz")
        return next(
            (state for state in states if state.entity_id == command.entity_id),
            states[0],
        )
