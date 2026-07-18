from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from wyss_panel_bridge.adapters.home_assistant import HomeAssistantGateway
from wyss_panel_bridge.adapters.tuya import (
    TuyaGateway,
    TuyaLightConfig,
    TuyaSceneConfig,
    TuyaSceneStep,
)
from wyss_panel_bridge.domain.models import FastCommand


class FakeTuyaDevice:
    def __init__(self, device_id: str, _address: str, _local_key: str) -> None:
        self.device_id = device_id
        self.dps: dict[str, object] = {"20": False, "21": "white", "22": 400}
        self.error = False
        self.silent_single_writes = False
        self.active_writes = 0
        self.maximum_active_writes = 0

    def set_version(self, _version: float) -> None:
        return None

    def set_socketTimeout(self, _timeout: float) -> None:  # noqa: N802
        return None

    def set_socketRetryLimit(self, _retries: int) -> None:  # noqa: N802
        return None

    def set_multiple_values(self, values: Mapping[str, Any]) -> object:
        self.active_writes += 1
        self.maximum_active_writes = max(self.maximum_active_writes, self.active_writes)
        time.sleep(0.002)
        self.active_writes -= 1
        if self.error:
            return {"Error": "offline"}
        self.dps.update(values)
        if self.silent_single_writes and len(values) == 1:
            return None
        return {"success": True}

    def status(self) -> object:
        if self.error:
            return {"Error": "offline"}
        return {"dps": dict(self.dps)}


def _tuya_gateway() -> tuple[TuyaGateway, dict[str, FakeTuyaDevice]]:
    devices: dict[str, FakeTuyaDevice] = {}

    def factory(device_id: str, address: str, local_key: str) -> FakeTuyaDevice:
        device = FakeTuyaDevice(device_id, address, local_key)
        devices[device_id] = device
        return device

    lights = (
        TuyaLightConfig("light.living", "Living", "living", "10.0.0.2", "key-a"),
        TuyaLightConfig("light.desk", "Escritorio", "desk", "10.0.0.3", "key-b"),
    )
    scenes = (
        TuyaSceneConfig(
            "scene.movie",
            "Cine",
            (
                TuyaSceneStep("light.living", brightness=20, rgb=0xFF2000),
                TuyaSceneStep("light.desk", on=False),
            ),
        ),
    )
    return TuyaGateway(lights=lights, scenes=scenes, device_factory=factory), devices


@pytest.mark.asyncio
async def test_tuya_controls_multiple_lights_color_and_scene() -> None:
    gateway, _ = _tuya_gateway()

    initial = await gateway.snapshot(["light.living", "light.desk", "scene.movie"])
    colored = await gateway.execute(
        FastCommand("color:1", "light.living", "set_color", rgb=0x3366CC)
    )
    scene = await gateway.execute(FastCommand("scene:1", "scene.movie", "activate_scene"))
    unchanged = await gateway.snapshot(["light.living", "light.desk", "scene.movie"])

    assert [state.entity_id for state in initial] == [
        "light.desk",
        "light.living",
        "scene.movie",
    ]
    assert all(state.available for state in initial)
    assert colored[0].rgb is not None
    assert abs(((colored[0].rgb >> 16) & 0xFF) - 0x33) <= 1
    assert [state.entity_id for state in scene] == ["light.desk", "light.living"]
    assert scene[0].on is False
    assert scene[1].on is True
    assert [state.revision for state in unchanged] == [
        state.revision
        for state in await gateway.snapshot(["light.living", "light.desk", "scene.movie"])
    ]


@pytest.mark.asyncio
async def test_tuya_serializes_commands_per_entity_and_marks_offline() -> None:
    gateway, devices = _tuya_gateway()

    await asyncio.gather(
        *(
            gateway.execute(
                FastCommand(f"brightness:{value}", "light.living", "set_brightness", value)
            )
            for value in range(10, 60, 10)
        )
    )
    devices["living"].error = True
    unavailable = await gateway.snapshot(["light.living"])

    assert devices["living"].maximum_active_writes == 1
    assert unavailable[0].available is False
    assert unavailable[0].brightness == 50
    with pytest.raises(RuntimeError, match="confirmación"):
        await gateway.execute(FastCommand("offline:1", "light.living", "turn_on"))


@pytest.mark.asyncio
async def test_tuya_verifies_silent_single_dp_power_writes_by_reading_state() -> None:
    gateway, devices = _tuya_gateway()
    devices["living"].silent_single_writes = True

    turned_on = await gateway.execute(FastCommand("power:1", "light.living", "turn_on"))
    turned_off = await gateway.execute(FastCommand("power:2", "light.living", "turn_off"))

    assert turned_on[0].on is True
    assert turned_off[0].on is False


@pytest.mark.asyncio
async def test_home_assistant_maps_color_scene_and_unavailable() -> None:
    states: dict[str, dict[str, object]] = {
        "light.living": {
            "state": "off",
            "attributes": {"friendly_name": "Living", "brightness": 0},
        },
        "scene.movie": {
            "state": "scening",
            "attributes": {"friendly_name": "Cine"},
        },
    }
    calls: list[tuple[str, dict[str, object]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/api/services/"):
            payload = dict(json.loads(request.content))
            calls.append((path, payload))
            return httpx.Response(200, json=[])
        entity_id = path.removeprefix("/api/states/")
        if entity_id not in states:
            return httpx.Response(404)
        return httpx.Response(200, json=states[entity_id])

    gateway = HomeAssistantGateway(
        "http://ha.local",
        "fixture-token",  # noqa: S106 - no es una credencial real
        transport=httpx.MockTransport(handler),
    )
    await gateway.execute(FastCommand("color:1", "light.living", "set_color", rgb=0x102030))
    await gateway.execute(FastCommand("scene:1", "scene.movie", "activate_scene"))
    snapshot = await gateway.snapshot(["light.unknown"])
    await gateway.close()

    assert calls == [
        ("/api/services/light/turn_on", {"entity_id": "light.living", "rgb_color": [16, 32, 48]}),
        ("/api/services/scene/turn_on", {"entity_id": "scene.movie"}),
    ]
    assert snapshot[0].available is False
