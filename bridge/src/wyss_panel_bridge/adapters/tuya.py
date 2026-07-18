from __future__ import annotations

import asyncio
import colorsys
from collections.abc import Callable, Mapping, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass, replace
from typing import Any, Protocol

import tinytuya  # type: ignore[import-untyped]

from wyss_panel_bridge.domain.models import DeviceState, FastCommand


class _TuyaDevice(Protocol):
    def set_version(self, version: float) -> None: ...

    def set_socketTimeout(self, timeout: float) -> None: ...  # noqa: N802 - API externa

    def set_socketRetryLimit(self, retries: int) -> None: ...  # noqa: N802 - API externa

    def set_multiple_values(self, values: Mapping[str, Any]) -> object: ...

    def status(self) -> object: ...


@dataclass(frozen=True, slots=True)
class TuyaLightConfig:
    entity_id: str
    name: str
    device_id: str
    address: str
    local_key: str
    version: float = 3.3
    power_dp: str = "20"
    mode_dp: str = "21"
    brightness_dp: str = "22"
    color_dp: str = "24"


@dataclass(frozen=True, slots=True)
class TuyaSceneStep:
    entity_id: str
    on: bool = True
    brightness: int | None = None
    rgb: int | None = None


@dataclass(frozen=True, slots=True)
class TuyaSceneConfig:
    entity_id: str
    name: str
    steps: tuple[TuyaSceneStep, ...]


@dataclass(slots=True)
class _ManagedLight:
    config: TuyaLightConfig
    device: _TuyaDevice
    lock: asyncio.Lock
    cached: DeviceState | None = None


class TuyaGateway:
    """Adapter multientidad Tuya LAN con reconciliación y escenas locales."""

    def __init__(
        self,
        entity_id: str | None = None,
        name: str | None = None,
        device_id: str | None = None,
        address: str | None = None,
        local_key: str | None = None,
        version: float = 3.3,
        *,
        lights: Sequence[TuyaLightConfig] | None = None,
        scenes: Sequence[TuyaSceneConfig] = (),
        device_factory: Callable[[str, str, str], _TuyaDevice] = tinytuya.Device,
    ) -> None:
        definitions = tuple(lights or ())
        if not definitions:
            if None in {entity_id, name, device_id, address, local_key}:
                raise ValueError("La configuración Tuya no contiene luces")
            definitions = (
                TuyaLightConfig(
                    entity_id=str(entity_id),
                    name=str(name),
                    device_id=str(device_id),
                    address=str(address),
                    local_key=str(local_key),
                    version=version,
                ),
            )
        self._lights: dict[str, _ManagedLight] = {}
        for definition in definitions:
            if not definition.entity_id.startswith("light."):
                raise ValueError("Una entidad Tuya debe comenzar con light.")
            if definition.entity_id in self._lights:
                raise ValueError("La configuración Tuya repite una entidad")
            device = device_factory(
                definition.device_id,
                definition.address,
                definition.local_key,
            )
            device.set_version(definition.version)
            device.set_socketTimeout(1.0)
            device.set_socketRetryLimit(1)
            self._lights[definition.entity_id] = _ManagedLight(
                definition,
                device,
                asyncio.Lock(),
            )
        self._scenes = {scene.entity_id: scene for scene in scenes}
        if len(self._scenes) != len(tuple(scenes)):
            raise ValueError("La configuración Tuya repite una escena")
        for scene in self._scenes.values():
            if not scene.entity_id.startswith("scene.") or not scene.steps:
                raise ValueError("La escena Tuya es inválida")
            if any(step.entity_id not in self._lights for step in scene.steps):
                raise ValueError("La escena Tuya referencia una luz desconocida")
        self._revision = 0
        self._scene_cache: dict[str, DeviceState] = {}

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        primary_entity: str,
        *,
        device_factory: Callable[[str, str, str], _TuyaDevice] = tinytuya.Device,
    ) -> TuyaGateway:
        raw_lights = config.get("lights")
        if raw_lights is None:
            raw_lights = config.get("devices")
        definitions: list[TuyaLightConfig] = []
        if isinstance(raw_lights, list):
            for raw in raw_lights:
                if not isinstance(raw, Mapping):
                    raise ValueError("La lista Tuya contiene una luz inválida")
                definitions.append(cls._light_config(raw))
        else:
            definitions.append(
                cls._light_config(
                    {
                        **config,
                        "entity_id": config.get("entity_id", primary_entity),
                        "name": config.get("name", "Luz principal"),
                    }
                )
            )
        scenes: list[TuyaSceneConfig] = []
        raw_scenes = config.get("scenes", [])
        if not isinstance(raw_scenes, list):
            raise ValueError("La configuración de escenas Tuya es inválida")
        for raw_scene in raw_scenes:
            if not isinstance(raw_scene, Mapping):
                raise ValueError("La configuración contiene una escena Tuya inválida")
            raw_steps = raw_scene.get("steps", [])
            if not isinstance(raw_steps, list):
                raise ValueError("Los pasos de la escena Tuya son inválidos")
            steps = tuple(cls._scene_step(step) for step in raw_steps)
            scenes.append(
                TuyaSceneConfig(
                    entity_id=str(raw_scene.get("entity_id", "")),
                    name=str(raw_scene.get("name", raw_scene.get("entity_id", ""))),
                    steps=steps,
                )
            )
        return cls(lights=definitions, scenes=scenes, device_factory=device_factory)

    async def snapshot(self, entities: Sequence[str]) -> list[DeviceState]:
        selected = set(entities)
        states: list[DeviceState] = []
        by_entity: dict[str, DeviceState] = {}
        for entity_id in sorted(selected & self._lights.keys()):
            managed = self._lights[entity_id]
            async with managed.lock:
                state = await self._read(managed)
            states.append(state)
            by_entity[entity_id] = state
        for entity_id in sorted(selected & self._scenes.keys()):
            scene = self._scenes[entity_id]
            related = [
                by_entity.get(step.entity_id) or self._lights[step.entity_id].cached
                for step in scene.steps
            ]
            scene_state = self._stable_state(
                self._scene_cache.get(scene.entity_id),
                DeviceState(
                    entity_id=scene.entity_id,
                    friendly_name=scene.name,
                    available=all(item is not None and item.available for item in related),
                    on=False,
                    brightness=0,
                    revision=0,
                ),
            )
            self._scene_cache[scene.entity_id] = scene_state
            states.append(scene_state)
        return states

    async def execute(self, command: FastCommand) -> list[DeviceState]:
        if command.entity_id in self._scenes:
            if command.action != "activate_scene":
                raise RuntimeError("Yo sólo puedo activar esa escena Tuya")
            return await self._activate_scene(self._scenes[command.entity_id])
        managed = self._lights.get(command.entity_id)
        if managed is None:
            raise RuntimeError("Yo no administro esa entidad Tuya")
        async with managed.lock:
            current = await self._read(managed)
            values = self._command_values(managed.config, command, current)
            await self._write(managed, values)
            return [await self._read(managed)]

    async def _activate_scene(self, scene: TuyaSceneConfig) -> list[DeviceState]:
        entity_ids = sorted({step.entity_id for step in scene.steps})
        async with AsyncExitStack() as stack:
            for entity_id in entity_ids:
                await stack.enter_async_context(self._lights[entity_id].lock)
            for step in scene.steps:
                managed = self._lights[step.entity_id]
                values = self._scene_values(managed.config, step)
                await self._write(managed, values)
            return [await self._read(self._lights[entity_id]) for entity_id in entity_ids]

    async def _write(self, managed: _ManagedLight, values: Mapping[str, Any]) -> None:
        try:
            response = await asyncio.to_thread(managed.device.set_multiple_values, values)
        except Exception as error:
            raise RuntimeError("Yo no pude comunicarme con el foco Tuya") from error
        if isinstance(response, dict):
            if response.get("Error") or response.get("Err"):
                raise RuntimeError("Yo no recibí confirmación válida del foco Tuya")
            return

        # Algunos focos Tuya aplican un write de un único DP pero no devuelven ACK.
        # Sólo lo aceptamos si una lectura posterior confirma exactamente el valor pedido.
        for attempt in range(3):
            try:
                status = await asyncio.to_thread(managed.device.status)
            except Exception:
                status = None
            if isinstance(status, dict) and not status.get("Error") and not status.get("Err"):
                raw_dps = status.get("dps")
                if isinstance(raw_dps, Mapping) and all(
                    self._dp(raw_dps, key, object()) == value for key, value in values.items()
                ):
                    return
            if attempt < 2:
                await asyncio.sleep(0.1)
        raise RuntimeError("Yo no recibí confirmación válida del foco Tuya")

    async def _read(self, managed: _ManagedLight) -> DeviceState:
        config = managed.config
        try:
            response = await asyncio.to_thread(managed.device.status)
        except Exception:
            response = None
        if not isinstance(response, dict) or response.get("Error"):
            unavailable = self._stable_state(
                managed.cached,
                DeviceState(
                    config.entity_id,
                    config.name,
                    False,
                    managed.cached.on if managed.cached is not None else False,
                    managed.cached.brightness if managed.cached is not None else 0,
                    0,
                    managed.cached.rgb if managed.cached is not None else None,
                ),
            )
            managed.cached = unavailable
            return unavailable
        raw_dps = response.get("dps", {})
        if not isinstance(raw_dps, Mapping):
            raw_dps = {}
        power = bool(self._dp(raw_dps, config.power_dp, False))
        raw_brightness = self._integer(self._dp(raw_dps, config.brightness_dp, 0))
        brightness = max(0, min(100, round(raw_brightness / 10)))
        rgb = self._decode_color(self._dp(raw_dps, config.color_dp, None))
        state = self._stable_state(
            managed.cached,
            DeviceState(
                config.entity_id,
                config.name,
                True,
                power,
                brightness,
                0,
                rgb,
            ),
        )
        managed.cached = state
        return state

    @staticmethod
    def _command_values(
        config: TuyaLightConfig,
        command: FastCommand,
        current: DeviceState,
    ) -> dict[str, Any]:
        if command.action == "turn_on":
            return {config.power_dp: True}
        if command.action == "turn_off":
            return {config.power_dp: False}
        if command.action == "toggle":
            return {config.power_dp: not current.on}
        if command.action == "set_brightness" and command.brightness is not None:
            raw = max(10, min(1000, command.brightness * 10))
            return {
                config.power_dp: command.brightness > 0,
                config.mode_dp: "white",
                config.brightness_dp: raw,
            }
        if command.action == "set_color" and command.rgb is not None:
            return {
                config.power_dp: True,
                config.mode_dp: "colour",
                config.color_dp: TuyaGateway._encode_color(command.rgb),
            }
        raise RuntimeError("Yo no puedo ejecutar esa acción en Tuya")

    @staticmethod
    def _scene_values(config: TuyaLightConfig, step: TuyaSceneStep) -> dict[str, Any]:
        values: dict[str, Any] = {config.power_dp: step.on}
        if step.rgb is not None:
            values[config.mode_dp] = "colour"
            values[config.color_dp] = TuyaGateway._encode_color(step.rgb, step.brightness)
        elif step.brightness is not None:
            values[config.mode_dp] = "white"
            values[config.brightness_dp] = max(10, min(1000, step.brightness * 10))
        return values

    @staticmethod
    def _encode_color(rgb: int, brightness: int | None = None) -> str:
        red = ((rgb >> 16) & 0xFF) / 255
        green = ((rgb >> 8) & 0xFF) / 255
        blue = (rgb & 0xFF) / 255
        hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
        if brightness is not None:
            value = brightness / 100
        return f"{round(hue * 360):04x}{round(saturation * 1000):04x}{round(value * 1000):04x}"

    @staticmethod
    def _decode_color(value: object) -> int | None:
        if not isinstance(value, str) or len(value) < 12:
            return None
        try:
            hue = int(value[0:4], 16) / 360
            saturation = int(value[4:8], 16) / 1000
            brightness = int(value[8:12], 16) / 1000
        except ValueError:
            return None
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, brightness)
        return (round(red * 255) << 16) | (round(green * 255) << 8) | round(blue * 255)

    @staticmethod
    def _dp(values: Mapping[object, object], key: str, default: object) -> object:
        if key in values:
            return values[key]
        try:
            numeric = int(key)
        except ValueError:
            return default
        return values.get(numeric, default)

    @staticmethod
    def _integer(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if not isinstance(value, (str, bytes, bytearray)):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _next_revision(self) -> int:
        self._revision += 1
        return self._revision

    def _stable_state(
        self,
        before: DeviceState | None,
        candidate: DeviceState,
    ) -> DeviceState:
        if before is not None and replace(before, revision=0) == candidate:
            return before
        return replace(candidate, revision=self._next_revision())

    @staticmethod
    def _light_config(raw: Mapping[str, Any]) -> TuyaLightConfig:
        required = ("entity_id", "device_id", "address", "local_key")
        if any(not str(raw.get(key, "")) for key in required):
            raise ValueError("La configuración Tuya de una luz está incompleta")
        return TuyaLightConfig(
            entity_id=str(raw["entity_id"]),
            name=str(raw.get("name", raw["entity_id"])),
            device_id=str(raw["device_id"]),
            address=str(raw["address"]),
            local_key=str(raw["local_key"]),
            version=float(raw.get("version", 3.3)),
            power_dp=str(raw.get("power_dp", "20")),
            mode_dp=str(raw.get("mode_dp", "21")),
            brightness_dp=str(raw.get("brightness_dp", "22")),
            color_dp=str(raw.get("color_dp", "24")),
        )

    @staticmethod
    def _scene_step(raw: object) -> TuyaSceneStep:
        if not isinstance(raw, Mapping):
            raise ValueError("La escena Tuya contiene un paso inválido")
        brightness = raw.get("brightness")
        rgb = raw.get("rgb")
        if brightness is not None and (
            isinstance(brightness, bool)
            or not isinstance(brightness, int)
            or not 0 <= brightness <= 100
        ):
            raise ValueError("El brillo de la escena Tuya es inválido")
        if rgb is not None and (
            isinstance(rgb, bool) or not isinstance(rgb, int) or not 0 <= rgb <= 0xFFFFFF
        ):
            raise ValueError("El color de la escena Tuya es inválido")
        return TuyaSceneStep(
            entity_id=str(raw.get("entity_id", "")),
            on=bool(raw.get("on", True)),
            brightness=brightness,
            rgb=rgb,
        )
