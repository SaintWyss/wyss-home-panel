"""Tipos seguros del ciclo de ejecución y auditoría de luces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

LightAuditStatus = Literal["accepted", "verified", "failed", "ambiguous"]


class LightError(RuntimeError):
    def __init__(self, code: str, message: str, *, replayed: bool = False) -> None:
        self.code = code
        self.replayed = replayed
        super().__init__(message)


class LightConflict(LightError):
    pass


@dataclass(frozen=True, slots=True)
class LightAuditRecord:
    request_id: str
    fingerprint: str
    source: str
    entity_id: str
    action: str
    status: LightAuditStatus
    result: Mapping[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    replayed: bool = False
