from __future__ import annotations

from typing import Any

import pytest

from wyss_panel_bridge.application.observability import ObservabilityRegistry
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.v2_api import _ClientHub


def test_percentiles_are_exact_bounded_and_do_not_retain_sensitive_correlation() -> None:
    registry = ObservabilityRegistry(max_samples=100, max_traces=4, now=lambda: 1_000)
    for duration in range(1, 101):
        registry.observe(
            "wyss.intent",
            float(duration),
            correlation_id="Bearer secret must not survive",
            status="error" if duration == 100 else "ok",
        )

    snapshot = registry.snapshot()
    metric = snapshot["metrics"]["wyss.intent"]

    assert metric == {
        "count": 100,
        "p50_ms": 50.0,
        "p95_ms": 95.0,
        "p99_ms": 99.0,
        "errors": 1,
    }
    assert len(snapshot["traces"]) == 4
    assert all(trace["correlation_id"] == "redacted" for trace in snapshot["traces"])
    assert "secret" not in str(snapshot)


def test_health_and_metric_cardinality_fail_closed() -> None:
    registry = ObservabilityRegistry(max_operations=1, max_samples=2)
    registry.set_health("home-edge", "ok", "ready")
    registry.observe("edge.request", 1, correlation_id="request:1", status="ok")
    registry.observe("edge.request", 2, correlation_id="request:2", status="dropped")
    registry.observe("edge.request", 3, correlation_id="request:3", status="ok")

    metric = registry.snapshot()["metrics"]["edge.request"]
    assert metric["count"] == 2
    assert metric["errors"] == 1
    with pytest.raises(ValueError, match="operaciones"):
        registry.observe("other.request", 1, correlation_id="request:4", status="ok")
    with pytest.raises(ValueError, match="módulos"):
        registry.set_health("wyss", "ok", "ready")


class FakeWebSocket:
    def __init__(self) -> None:
        self.closed: tuple[int, str] | None = None

    async def close(self, code: int, reason: str) -> None:
        self.closed = (code, reason)

    async def send_json(self, message: dict[str, Any]) -> None:
        del message


@pytest.mark.asyncio
async def test_initial_sync_backpressure_closes_instead_of_growing_unbounded() -> None:
    hub = _ClientHub(max_pending=1)
    websocket = FakeWebSocket()
    await hub.register("panel:slow", websocket, 0)  # type: ignore[arg-type]
    await hub.broadcast(ProjectionEvent(1, "home", 1, {}))
    await hub.broadcast(ProjectionEvent(2, "assistant", 1, {}))

    assert websocket.closed == (4413, "backpressure")
