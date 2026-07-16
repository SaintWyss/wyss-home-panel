#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import getpass
import json
import subprocess
import time
from pathlib import Path

import serial


def active_ssid() -> str:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"],
        check=True,
        capture_output=True,
        text=True,
    )
    return next(
        (line.split(":", 1)[1] for line in result.stdout.splitlines() if line.startswith("yes:")),
        "",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Yo aprovisiono el panel sin publicar secretos")
    parser.add_argument("--port", required=True)
    parser.add_argument("--bridge-url", required=True)
    parser.add_argument("--panel-id", required=True)
    parser.add_argument("--primary-entity", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--ca-file", required=True, type=Path)
    args = parser.parse_args()

    detected = active_ssid()
    ssid = input(f"SSID Wi-Fi [{detected}]: ").strip() or detected
    password = getpass.getpass("Contraseña Wi-Fi (oculta): ")
    payload = {
        "wifi_ssid": ssid,
        "wifi_password": password,
        "bridge_url": args.bridge_url,
        "device_token": args.token_file.read_text().strip(),
        "panel_id": args.panel_id,
        "primary_entity": args.primary_entity,
        "ca_certificate": args.ca_file.read_text(),
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    command = f"WYSSCFG {encoded}\n".encode()

    with serial.Serial(args.port, 115200, timeout=0.25) as connection:
        connection.reset_input_buffer()
        connection.write(command)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            line = connection.readline().decode("utf-8", "replace").strip()
            if line == "PROVISIONING_OK":
                args.token_file.unlink(missing_ok=True)
                print("Yo guardé la configuración y eliminé el token temporal.")
                return
            if line.startswith("PROVISIONING_ERROR"):
                raise SystemExit(line)
    raise SystemExit("Yo no recibí confirmación de la placa")


if __name__ == "__main__":
    main()

