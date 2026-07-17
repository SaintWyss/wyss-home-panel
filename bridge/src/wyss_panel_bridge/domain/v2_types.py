"""DTOs opacos de contratos v2; no contienen detalles de adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CapabilityCommand:
    request_id: str
    action: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    expected_revision: int | None = None


@dataclass(frozen=True, slots=True)
class ProjectionEvent:
    event_id: int
    aggregate: str
    revision: int
    payload: Mapping[str, Any]
    event_type: str = "projection.delta"
    correlation_id: str | None = None
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class Snapshot:
    revision: int
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    delivery_id: str
    accepted: bool
