from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class RiskLevel(IntEnum):
    A = 0
    B = 1
    C = 2
    D = 3


@dataclass(frozen=True, slots=True)
class DeviceState:
    entity_id: str
    friendly_name: str
    available: bool
    on: bool
    brightness: int
    revision: int
    rgb: int | None = None

    def as_wire(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "entity_id": self.entity_id,
            "friendly_name": self.friendly_name,
            "available": self.available,
            "on": self.on,
            "brightness": self.brightness,
            "revision": self.revision,
        }
        if self.rgb is not None:
            result["rgb"] = self.rgb
        return result


@dataclass(frozen=True, slots=True)
class FastCommand:
    request_id: str
    entity_id: str
    action: str
    brightness: int | None = None
    rgb: int | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class PlanStep:
    description: str
    target: str


@dataclass(frozen=True, slots=True)
class Plan:
    plan_id: str
    summary: str
    risk: RiskLevel
    steps: tuple[PlanStep, ...] = field(default_factory=tuple)
    expires_at_ms: int = 0


class PolicyError(ValueError):
    """Yo indico que una acción no cumple la política del borde."""
