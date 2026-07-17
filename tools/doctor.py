#!/usr/bin/env python3
"""Diagnóstico local seguro para Wyss Home Panel."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "config" / "baseline-versions.toml"
MAX_CONFIG_BYTES = 1024 * 1024
VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
HEX_64_RE = re.compile(r"[0-9a-fA-F]{64}")


@dataclass(frozen=True, slots=True)
class Check:
    id: str
    status: str
    message: str


def _version(value: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.search(value)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def _run_version(command: list[str], minimum: str | None = None) -> Check:
    check_id = f"tool.{command[0]}"
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    except FileNotFoundError:
        return Check(check_id, "fail", "no está instalado")
    except subprocess.TimeoutExpired:
        return Check(check_id, "fail", "no respondió dentro del límite")
    if result.returncode != 0:
        return Check(check_id, "fail", "terminó con error")
    found = _version(f"{result.stdout}\n{result.stderr}")
    required = _version(minimum or "")
    if found is None:
        return Check(check_id, "fail", "no pude reconocer su versión")
    if required is not None and found < required:
        return Check(check_id, "fail", f"requiere >= {minimum}")
    return Check(check_id, "pass", f"versión {'.'.join(map(str, found))}")


def _safe_file(path: Path, root: Path, check_id: str) -> Check | None:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except (FileNotFoundError, ValueError, OSError):
        return Check(check_id, "fail", "ruta ausente o fuera del directorio permitido")
    if path.is_symlink() or not resolved.is_file():
        return Check(check_id, "fail", "debe ser un archivo regular sin symlink")
    if resolved.stat().st_size > MAX_CONFIG_BYTES:
        return Check(check_id, "fail", "supera 1 MiB")
    return None


def _load_toml(
    path: Path, allowed_root: Path, check_id: str
) -> tuple[dict[str, Any] | None, Check]:
    unsafe = _safe_file(path, allowed_root, check_id)
    if unsafe is not None:
        return None, unsafe
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream), Check(check_id, "pass", "TOML válido")
    except (OSError, tomllib.TOMLDecodeError):
        return None, Check(check_id, "fail", "TOML inválido o ilegible")


def _manifest_checks(path: Path) -> tuple[dict[str, Any] | None, list[Check]]:
    raw, check = _load_toml(path, ROOT / "config", "manifest")
    checks = [check]
    if raw is None:
        return None, checks
    if raw.get("schema_version") != 1:
        checks.append(Check("manifest.schema", "fail", "schema_version debe ser 1"))
        return raw, checks
    toolchain = raw.get("toolchain")
    protocol = raw.get("protocol")
    if not isinstance(toolchain, dict) or not isinstance(protocol, dict):
        checks.append(Check("manifest.schema", "fail", "faltan toolchain o protocol"))
    else:
        checks.append(Check("manifest.schema", "pass", "schema reconocido"))
    return raw, checks


def _tool_checks(manifest: dict[str, Any]) -> list[Check]:
    toolchain = manifest.get("toolchain", {})
    return [
        _run_version(
            [sys.executable, "--version"], str(toolchain.get("python_min", "3.12"))
        ),
        _run_version(["cmake", "--version"], str(toolchain.get("cmake_min", "3.20"))),
        _run_version(["c++", "--version"]),
        _run_version(["pio", "--version"], str(toolchain.get("platformio", "6.1.19"))),
        _run_version(["uv", "--version"], str(toolchain.get("uv", "0.11"))),
        _run_version(["git", "--version"]),
    ]


def _config_checks(path: Path) -> list[Check]:
    raw, check = _load_toml(path, ROOT / "config", "config")
    checks = [check]
    if raw is None:
        return checks
    panel = raw.get("panel", {})
    devices = raw.get("devices", {})
    if not isinstance(panel, dict) or not isinstance(devices, dict):
        return checks + [Check("config.schema", "fail", "faltan panel o devices")]
    token_hash = str(panel.get("token_sha256", ""))
    checks.append(
        Check(
            "config.panel_hash",
            "pass" if HEX_64_RE.fullmatch(token_hash) else "fail",
            "hash SHA-256 válido"
            if HEX_64_RE.fullmatch(token_hash)
            else "token_sha256 inválido",
        )
    )
    allowed = panel.get("allowed_entities", [])
    primary = panel.get("primary_entity")
    checks.append(
        Check(
            "config.primary_entity",
            "pass" if isinstance(allowed, list) and primary in allowed else "fail",
            "entidad primaria autorizada"
            if isinstance(allowed, list) and primary in allowed
            else "primary_entity no está en allowed_entities",
        )
    )
    provider = str(devices.get("provider", ""))
    provider_config = raw.get(provider, {})
    inline_secret = False
    if isinstance(provider_config, dict):
        inline_secret = any(
            key in provider_config
            for key in ("token", "local_key", "password", "secret")
        )
    checks.append(
        Check(
            "config.provider_secrets",
            "fail" if inline_secret else "pass",
            "hay secretos inline"
            if inline_secret
            else "secretos referenciados por entorno",
        )
    )
    mode = stat.S_IMODE(path.stat().st_mode)
    checks.append(
        Check(
            "config.permissions",
            "pass" if mode & 0o077 == 0 else "fail",
            "permisos privados" if mode & 0o077 == 0 else "group/world tiene acceso",
        )
    )
    return checks


def diagnose(manifest_path: Path, config_path: Path | None) -> list[Check]:
    manifest, checks = _manifest_checks(manifest_path)
    if manifest is not None:
        checks.extend(_tool_checks(manifest))
        fixture = ROOT / str(manifest.get("protocol", {}).get("fixture_path", ""))
        checks.append(
            Check(
                "protocol.fixtures",
                "pass" if fixture.is_file() else "fail",
                "fixtures v1 presentes"
                if fixture.is_file()
                else "fixtures v1 ausentes",
            )
        )
    if config_path is not None:
        checks.extend(_config_checks(config_path))
    return checks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        checks = diagnose(args.manifest, args.config)
        status = "ok" if all(item.status == "pass" for item in checks) else "error"
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": status,
                        "checks": [asdict(x) for x in checks],
                    }
                )
            )
        else:
            for item in checks:
                marker = "PASS" if item.status == "pass" else "FAIL"
                print(f"[{marker}] {item.id}: {item.message}")
        return 0 if status == "ok" else 1
    except SystemExit as error:
        return int(error.code)
    except Exception:
        print("doctor: error interno redactado", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
