"""Reducción determinista de proyecciones v2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from wyss_panel_bridge.domain.v2_types import ProjectionEvent, Snapshot


class ProjectionError(ValueError):
    """La proyección no puede avanzar de forma segura."""


class ProjectionGap(ProjectionError):
    """Falta un evento global o una revisión del agregado."""


@dataclass(frozen=True, slots=True)
class AggregateProjection:
    revision: int
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ProjectionDelivery:
    snapshot: Snapshot | None
    events: Sequence[ProjectionEvent]
    latest_event_id: int


def reduce_event(
    current: AggregateProjection | None,
    event: ProjectionEvent,
) -> AggregateProjection:
    revision = current.revision if current is not None else 0
    if event.revision <= revision:
        raise ProjectionError("revisión obsoleta")
    if event.revision != revision + 1:
        raise ProjectionGap("hueco de revisión")
    payload = dict(current.payload) if current is not None else {}
    payload.update(event.payload)
    return AggregateProjection(event.revision, payload)
