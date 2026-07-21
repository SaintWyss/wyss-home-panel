#!/usr/bin/env python3
"""Sonda local para entender por qué una luz aparece como no disponible.

Yo replico exactamente la lectura que hace TuyaGateway._read() y separo las causas
que el puente colapsa en un único "available=False": host inalcanzable, clave
rechazada, respuesta lenta o DP inesperado.

Yo no imprimo local_key ni device_id completos.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

TUYA_PORT = 6668


def _redact(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return f"...{value[-4:]}"


def _resolve(raw: dict[str, Any], direct: str, env_key: str) -> tuple[str | None, str]:
    """Devuelve (valor, origen). El puente acepta el valor directo o vía entorno."""
    if raw.get(direct):
        return str(raw[direct]), "config"
    env_name = raw.get(env_key)
    if not env_name:
        return None, f"falta {direct} y {env_key}"
    value = os.environ.get(str(env_name))
    if not value:
        return None, f"la variable {env_name} no está definida en este proceso"
    return value, f"entorno {env_name}"


def _tcp(address: str, timeout: float) -> tuple[bool, float, str]:
    start = time.monotonic()
    try:
        with socket.create_connection((address, TUYA_PORT), timeout=timeout):
            return True, time.monotonic() - start, "abierto"
    except socket.timeout:
        return False, time.monotonic() - start, "timeout (nadie contesta en esa IP)"
    except ConnectionRefusedError:
        return (
            False,
            time.monotonic() - start,
            "conexión rechazada (hay un host, pero no es el foco)",
        )
    except OSError as error:
        return False, time.monotonic() - start, f"sin ruta ({error.__class__.__name__})"


def _status(
    device_id: str, address: str, local_key: str, version: float, timeout: float
) -> tuple[str, str]:
    try:
        import tinytuya  # type: ignore[import-untyped]
    except ImportError:
        return "omitido", "tinytuya no está instalado en este intérprete"
    device = tinytuya.Device(device_id, address, local_key)
    device.set_version(version)
    device.set_socketTimeout(timeout)
    device.set_socketRetryLimit(1)
    start = time.monotonic()
    try:
        response = device.status()
    except Exception as error:  # noqa: BLE001 - queremos clasificar cualquier fallo
        return (
            "error",
            f"{error.__class__.__name__} tras {time.monotonic() - start:.2f}s",
        )
    elapsed = time.monotonic() - start
    if not isinstance(response, dict):
        return "error", f"respuesta no es un dict ({elapsed:.2f}s)"
    problem = response.get("Error") or response.get("Err")
    if problem:
        hint = ""
        if str(problem) in {"901", "914"} or "key" in str(response).lower():
            hint = " — típico de local_key vencida: se rota al re-vincular el foco en la app"
        return "error", f"el foco respondió con error {problem}{hint} ({elapsed:.2f}s)"
    dps = response.get("dps")
    if not isinstance(dps, dict):
        return "error", f"sin bloque dps ({elapsed:.2f}s)"
    return "ok", f"dps {sorted(dps)} en {elapsed:.2f}s"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--timeout",
        type=float,
        default=3.0,
        help="más generoso que el 1.0s del puente, para ver si sólo es lentitud",
    )
    args = parser.parse_args()

    try:
        config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        print(
            f"no pude leer la configuración: {error.__class__.__name__}",
            file=sys.stderr,
        )
        return 2

    provider = config.get("devices", {}).get("provider")
    print(f"proveedor configurado: {provider}")
    if provider != "tuya":
        print("esta sonda sólo cubre Tuya; con home_assistant revisá url y token.")
        return 0

    gates = config.get("protocol_v2", {})
    for key in ("enabled", "lights_enabled"):
        value = gates.get(key)
        mark = "OK" if value else "APAGADO"
        print(f"gate protocol_v2.{key}: {value!r} [{mark}]")
    if not gates.get("lights_enabled", False):
        print("  -> con lights_enabled en false el panel conecta pero no ve luces.")

    lights = config.get("tuya", {}).get("lights") or []
    if not lights:
        print("no hay bloques [[tuya.lights]]: el puente no administra ninguna luz.")
        return 1

    failures = 0
    for raw in lights:
        entity = raw.get("entity_id", "?")
        address = str(raw.get("address", ""))
        print(f"\n--- {entity} @ {address or 'sin address'} ---")
        device_id, id_origin = _resolve(raw, "device_id", "device_id_env")
        local_key, key_origin = _resolve(raw, "local_key", "local_key_env")
        print(
            f"device_id: {_redact(device_id) if device_id else 'AUSENTE'} ({id_origin})"
        )
        print(f"local_key: {'presente' if local_key else 'AUSENTE'} ({key_origin})")
        if not address or not device_id or not local_key:
            print(
                "resultado: configuración incompleta, el puente ni siquiera intenta hablar."
            )
            failures += 1
            continue

        reachable, elapsed, detail = _tcp(address, args.timeout)
        print(f"tcp {address}:{TUYA_PORT}: {detail} ({elapsed:.2f}s)")
        if not reachable:
            print(
                "resultado: la IP no responde. Si tu router usa DHCP, probablemente cambió;"
                " fijá una reserva y actualizá 'address'."
            )
            failures += 1
            continue

        status, detail = _status(
            device_id, address, local_key, float(raw.get("version", 3.3)), args.timeout
        )
        print(f"status(): {status} — {detail}")
        if status == "ok":
            if elapsed > 1.0:
                print(
                    "resultado: responde, pero por encima del timeout de 1.0s del puente."
                    " Por eso lo ves intermitente o no disponible."
                )
                failures += 1
            else:
                print(
                    "resultado: el foco contesta bien. Si el panel lo ve caído,"
                    " el problema está entre panel y puente, no entre puente y foco."
                )
        elif status == "error":
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
