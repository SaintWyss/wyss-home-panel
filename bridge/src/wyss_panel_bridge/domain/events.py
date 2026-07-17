"""Tipos y fallos del backbone de eventos v2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from wyss_panel_bridge.domain.v2_types import ProjectionEvent


class EventError(ValueError):
    """Evento inválido o imposible de persistir de forma segura."""


class EventConflict(EventError):
    """Una idempotency key fue reutilizada con contenido diferente."""


class RateLimitExceeded(EventError):
    """El origen superó su cuota de eventos v2."""


@dataclass(frozen=True, slots=True)
class EventDraft:
    event_type: str
    aggregate: str
    payload: Mapping[str, Any]
    correlation_id: str | None = None
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResumeBatch:
    latest_event_id: int
    snapshot_required: bool
    events: Sequence[ProjectionEvent]
