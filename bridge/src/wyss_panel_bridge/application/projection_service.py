"""Materializa el event log y entrega vistas acotadas por cliente."""

from __future__ import annotations

from collections import OrderedDict

from wyss_panel_bridge.domain.projection import ProjectionDelivery
from wyss_panel_bridge.ports_v2 import EventStorePort, ProjectionStorePort


class ProjectionCoordinator:
    def __init__(
        self,
        events: EventStorePort,
        projections: ProjectionStorePort,
        *,
        max_clients: int = 64,
        snapshot_fallback: bool = False,
    ) -> None:
        if max_clients <= 0:
            raise ValueError("max_clients inválido")
        self._events = events
        self._projections = projections
        self._max_clients = max_clients
        self._snapshot_fallback = snapshot_fallback
        self._cursors: OrderedDict[str, int] = OrderedDict()

    def synchronize(self) -> int:
        applied = 0
        while True:
            batch = self._events.after(self._projections.last_event_id(), 256)
            if not batch:
                return applied
            for event in batch:
                if self._projections.apply(event):
                    applied += 1

    def delivery(self, client_id: str, last_event_id: int) -> ProjectionDelivery:
        if last_event_id < 0:
            raise ValueError("cursor inválido")
        self.synchronize()
        latest = self._projections.last_event_id()
        self._record_cursor(client_id, last_event_id)
        if self._snapshot_fallback or last_event_id == 0 or last_event_id > latest:
            return ProjectionDelivery(self._projections.snapshot(), (), latest)
        events = self._events.after(last_event_id, 256)
        return ProjectionDelivery(None, events, latest)

    @property
    def cached_clients(self) -> int:
        return len(self._cursors)

    def _record_cursor(self, client_id: str, cursor: int) -> None:
        if not client_id:
            raise ValueError("client_id vacío")
        if client_id not in self._cursors and len(self._cursors) >= self._max_clients:
            self._cursors.popitem(last=False)
        self._cursors[client_id] = cursor
        self._cursors.move_to_end(client_id)
