from __future__ import annotations

from wyss_panel_bridge.application.light_service import LightService
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


class ProjectedLegacyDeviceGateway:
    """Hace que v1 publique en la misma autoridad/proyección usada por v2."""

    def __init__(self, service: LightService, source: str = "panel:v1") -> None:
        self._service = service
        self._source = source

    async def snapshot(self, entities: frozenset[str]) -> list[DeviceState]:
        await self._service.refresh()
        return [state for state in self._service.cached_states() if state.entity_id in entities]

    async def execute(self, command: FastCommand) -> DeviceState:
        await self._service.execute(self._source, command)
        states = self._service.cached_states()
        selected = next((state for state in states if state.entity_id == command.entity_id), None)
        if selected is not None:
            return selected
        if states:
            return states[0]
        raise RuntimeError("Yo no recibí estado verificado de la luz")
