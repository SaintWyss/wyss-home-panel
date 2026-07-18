from __future__ import annotations

from pathlib import Path

import pytest

from wyss_panel_bridge.operations.soak import SoakConfig, run_soak


@pytest.mark.asyncio
async def test_full_accelerated_soak_is_exactly_once_and_recovers(tmp_path: Path) -> None:
    report = await run_soak(tmp_path, SoakConfig())

    assert report.status == "PASS"
    assert report.reconnections == 1_000
    assert report.brightness_changes == 500
    assert report.timer_completions == 100
    assert report.notification_deliveries == 100
    assert report.provider_failures_injected == 1
    assert report.process_restarts_injected == 2
    assert report.duplicate_events == 0
    assert report.ghost_states == 0
    assert report.crashes == 0
