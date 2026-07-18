"""Métricas acotadas y trazas por identificador, nunca por contenido doméstico."""

from __future__ import annotations

import math
import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

SAFE_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class MetricSummary:
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    errors: int


@dataclass(frozen=True, slots=True)
class TracePoint:
    operation: str
    correlation_id: str
    status: str
    duration_ms: float
    observed_at: float


class ObservabilityRegistry:
    def __init__(
        self,
        *,
        max_operations: int = 32,
        max_samples: int = 512,
        max_traces: int = 128,
        now: Callable[[], float] = time.time,
    ) -> None:
        if min(max_operations, max_samples, max_traces) <= 0:
            raise ValueError("límites de observabilidad inválidos")
        self._max_operations = max_operations
        self._max_samples = max_samples
        self._samples: dict[str, deque[tuple[float, bool]]] = {}
        self._traces: deque[TracePoint] = deque(maxlen=max_traces)
        self._health: dict[str, tuple[str, str]] = {}
        self._now = now

    def observe(
        self,
        operation: str,
        duration_ms: float,
        *,
        correlation_id: str,
        status: str,
    ) -> None:
        if SAFE_NAME.fullmatch(operation) is None or status not in {"ok", "error", "dropped"}:
            raise ValueError("dimensión de métrica inválida")
        if not math.isfinite(duration_ms) or duration_ms < 0 or duration_ms > 3_600_000:
            raise ValueError("duración inválida")
        samples = self._samples.get(operation)
        if samples is None:
            if len(self._samples) >= self._max_operations:
                raise ValueError("límite de operaciones excedido")
            samples = deque(maxlen=self._max_samples)
            self._samples[operation] = samples
        samples.append((duration_ms, status != "ok"))
        safe_correlation = (
            correlation_id if SAFE_CORRELATION.fullmatch(correlation_id) else "redacted"
        )
        self._traces.append(
            TracePoint(operation, safe_correlation, status, duration_ms, self._now())
        )

    def set_health(self, module: str, status: str, reason: str) -> None:
        if SAFE_NAME.fullmatch(module) is None or status not in {"ok", "degraded", "down"}:
            raise ValueError("health inválido")
        safe_reason = reason if SAFE_NAME.fullmatch(reason) else "redacted"
        if len(self._health) >= self._max_operations and module not in self._health:
            raise ValueError("límite de módulos excedido")
        self._health[module] = (status, safe_reason)

    def snapshot(self) -> dict[str, object]:
        metrics = {
            operation: self._summary(samples)
            for operation, samples in sorted(self._samples.items())
        }
        return {
            "metrics": {
                name: {
                    "count": value.count,
                    "p50_ms": value.p50_ms,
                    "p95_ms": value.p95_ms,
                    "p99_ms": value.p99_ms,
                    "errors": value.errors,
                }
                for name, value in metrics.items()
            },
            "health": {
                module: {"status": value[0], "reason": value[1]}
                for module, value in sorted(self._health.items())
            },
            "traces": [
                {
                    "operation": trace.operation,
                    "correlation_id": trace.correlation_id,
                    "status": trace.status,
                    "duration_ms": trace.duration_ms,
                    "observed_at": trace.observed_at,
                }
                for trace in self._traces
            ],
        }

    @staticmethod
    def _summary(samples: deque[tuple[float, bool]]) -> MetricSummary:
        ordered = sorted(value for value, _error in samples)

        def percentile(fraction: float) -> float:
            index = max(0, math.ceil(len(ordered) * fraction) - 1)
            return round(ordered[index], 3)

        return MetricSummary(
            len(ordered),
            percentile(0.50),
            percentile(0.95),
            percentile(0.99),
            sum(1 for _value, error in samples if error),
        )
