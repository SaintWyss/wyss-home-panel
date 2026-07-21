from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from wyss_panel_bridge.adapters.tuya_legacy_panel import LegacyPanelTuyaDevice


class FakeRawTuyaDevice:
    def __init__(self, device_id: str, address: str, local_key: str) -> None:
        self.device_id = device_id
        self.address = address
        self.local_key = local_key
        self.version = 0.0
        self.persistent = True
        self.no_delay = False
        self.timeout = 0.0
        self.retries = 0
        self.retry_delay = 0
        self.dps_used: dict[str, object] = {}
        self.dps: dict[str, object] = {"20": False, "21": "white", "22": 400}

    def set_version(self, version: float) -> None:
        self.version = version

    def set_socketPersistent(self, persistent: bool) -> None:  # noqa: N802
        self.persistent = persistent

    def set_socketNODELAY(self, no_delay: bool) -> None:  # noqa: N802
        self.no_delay = no_delay

    def set_socketTimeout(self, timeout: float) -> None:  # noqa: N802
        self.timeout = timeout

    def set_socketRetryLimit(self, retries: int) -> None:  # noqa: N802
        self.retries = retries

    def set_socketRetryDelay(self, delay: int) -> None:  # noqa: N802
        self.retry_delay = delay

    def set_dpsUsed(self, dps: Mapping[str, object]) -> None:  # noqa: N802
        self.dps_used = dict(dps)

    def set_multiple_values(self, values: Mapping[str, Any]) -> object:
        self.dps.update(values)
        return {"success": True}

    def status(self) -> object:
        return {"dps": dict(self.dps)}


def test_legacy_panel_profile_restores_proven_tuya_connection_parameters() -> None:
    raw_devices: list[FakeRawTuyaDevice] = []

    def factory(device_id: str, address: str, local_key: str) -> FakeRawTuyaDevice:
        raw = FakeRawTuyaDevice(device_id, address, local_key)
        raw_devices.append(raw)
        return raw

    device = LegacyPanelTuyaDevice(
        "device-id",
        "192.168.1.50",
        "0123456789abcdef",
        device_factory=factory,
    )
    device.set_version(3.3)
    device.set_socketTimeout(1.0)
    device.set_socketRetryLimit(1)

    raw = raw_devices[0]
    assert raw.version == 3.3
    assert raw.persistent is False
    assert raw.no_delay is True
    assert raw.timeout == 4.0
    assert raw.retries == 3
    assert raw.retry_delay == 1
    assert raw.dps_used == {"20": None, "21": None, "22": None, "24": None}
    assert device.status() == {"dps": {"20": False, "21": "white", "22": 400}}
