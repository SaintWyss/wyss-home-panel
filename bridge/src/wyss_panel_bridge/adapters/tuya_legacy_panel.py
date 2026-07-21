"""Perfil Tuya LAN compatible con el panel físico anterior.

El primer panel se comunicaba con el foco LEDVANCE/Tuya 3.3 abriendo una conexión
nueva por transacción, con hasta 3 segundos para conectar, 4 segundos para leer y
reintentos posteriores. Este adapter conserva ese comportamiento probado, pero
mantiene las credenciales en Home Edge en vez de copiarlas al ESP32.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import tinytuya  # type: ignore[import-untyped]

from wyss_panel_bridge.adapters.tuya import TuyaGateway

_MIN_TIMEOUT_SECONDS = 4.0
_MIN_RETRIES = 3
_RETRY_DELAY_SECONDS = 1
_LEGACY_DPS = {"20": None, "21": None, "22": None, "24": None}


class LegacyPanelTuyaDevice:
    """Envuelve TinyTuya con los parámetros que funcionaban en el panel original."""

    def __init__(
        self,
        device_id: str,
        address: str,
        local_key: str,
        *,
        device_factory: Callable[[str, str, str], Any] = tinytuya.Device,
    ) -> None:
        self._device = device_factory(device_id, address, local_key)
        self._call_optional("set_socketPersistent", False)
        self._call_optional("set_socketNODELAY", True)
        self._call_optional("set_socketRetryDelay", _RETRY_DELAY_SECONDS)
        self._call_optional("set_dpsUsed", dict(_LEGACY_DPS))

    def set_version(self, version: float) -> None:
        self._device.set_version(version)

    def set_socketTimeout(self, timeout: float) -> None:  # noqa: N802 - API externa
        self._device.set_socketTimeout(max(float(timeout), _MIN_TIMEOUT_SECONDS))

    def set_socketRetryLimit(self, retries: int) -> None:  # noqa: N802 - API externa
        self._device.set_socketRetryLimit(max(int(retries), _MIN_RETRIES))

    def set_multiple_values(self, values: Mapping[str, Any]) -> object:
        return self._device.set_multiple_values(values)

    def status(self) -> object:
        return self._device.status()

    def _call_optional(self, name: str, *args: object) -> None:
        method = getattr(self._device, name, None)
        if callable(method):
            method(*args)


def _legacy_device_factory(device_id: str, address: str, local_key: str) -> LegacyPanelTuyaDevice:
    return LegacyPanelTuyaDevice(device_id, address, local_key)


def build_legacy_panel_tuya_gateway(
    config: Mapping[str, Any],
    primary_entity: str,
) -> TuyaGateway:
    """Construye el gateway actual usando el transporte probado del repo anterior."""

    return TuyaGateway.from_config(
        config,
        primary_entity,
        device_factory=_legacy_device_factory,
    )
