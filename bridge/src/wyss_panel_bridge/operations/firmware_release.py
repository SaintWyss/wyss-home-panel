"""Manifest Ed25519 y ledger de promoción OTA sin tocar flash ni eFuses."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

MANIFEST_FIELDS = {
    "schema_version",
    "version",
    "board_id",
    "build_commit",
    "firmware_size",
    "firmware_sha256",
    "signature",
}
SIGNED_FIELDS = MANIFEST_FIELDS - {"signature"}
HEALTH_COMPONENTS = {"boot", "display", "touch", "network", "handshake"}


class FirmwareReleaseError(ValueError):
    pass


def _canonical(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _run_openssl(arguments: list[str], payload: bytes) -> bytes:
    executable = shutil.which("openssl")
    if executable is None:
        raise FirmwareReleaseError("verificación criptográfica no disponible")
    try:
        with tempfile.NamedTemporaryFile() as payload_stream:
            payload_stream.write(payload)
            payload_stream.flush()
            result = subprocess.run(  # noqa: S603 - argv cerrado, sin shell
                [executable, *arguments, "-in", payload_stream.name],
                capture_output=True,
                check=False,
                timeout=10,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FirmwareReleaseError("verificación criptográfica no disponible") from error
    if result.returncode != 0:
        raise FirmwareReleaseError("firma de firmware inválida")
    return result.stdout


def create_manifest(
    firmware: Path,
    private_key: Path,
    *,
    version: str,
    board_id: str,
    build_commit: str,
) -> dict[str, object]:
    image = firmware.read_bytes()
    if not image or len(image) > 16 * 1024 * 1024:
        raise FirmwareReleaseError("tamaño de firmware inválido")
    if not version or len(version) > 32 or not board_id or len(board_id) > 64:
        raise FirmwareReleaseError("identidad de release inválida")
    if len(build_commit) != 40 or any(
        character not in "0123456789abcdef" for character in build_commit
    ):
        raise FirmwareReleaseError("commit de release inválido")
    signed: dict[str, object] = {
        "schema_version": 1,
        "version": version,
        "board_id": board_id,
        "build_commit": build_commit,
        "firmware_size": len(image),
        "firmware_sha256": hashlib.sha256(image).hexdigest(),
    }
    signature = _run_openssl(
        ["pkeyutl", "-sign", "-rawin", "-inkey", str(private_key)],
        _canonical(signed),
    )
    return {
        **signed,
        "signature": {
            "algorithm": "ed25519",
            "value": base64.b64encode(signature).decode("ascii"),
        },
    }


def verify_manifest(
    manifest: object,
    firmware: Path,
    public_key: Path,
    *,
    expected_board_id: str,
) -> dict[str, object]:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise FirmwareReleaseError("manifest de firmware inválido")
    raw = cast(dict[str, Any], manifest)
    if raw.get("schema_version") != 1 or raw.get("board_id") != expected_board_id:
        raise FirmwareReleaseError("manifest incompatible con la placa")
    signature = raw.get("signature")
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "value"}:
        raise FirmwareReleaseError("firma de manifest inválida")
    if signature.get("algorithm") != "ed25519" or not isinstance(signature.get("value"), str):
        raise FirmwareReleaseError("algoritmo de firma no autorizado")
    image = firmware.read_bytes()
    size = raw.get("firmware_size")
    digest = raw.get("firmware_sha256")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size != len(image)
        or not isinstance(digest, str)
        or digest != hashlib.sha256(image).hexdigest()
    ):
        raise FirmwareReleaseError("checksum de firmware inválido")
    signed = {key: raw[key] for key in SIGNED_FIELDS}
    try:
        decoded = base64.b64decode(signature["value"], validate=True)
    except (ValueError, TypeError) as error:
        raise FirmwareReleaseError("firma de manifest inválida") from error
    with tempfile.NamedTemporaryFile() as stream:
        stream.write(decoded)
        stream.flush()
        _run_openssl(
            [
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_key),
                "-rawin",
                "-sigfile",
                stream.name,
            ],
            _canonical(signed),
        )
    return {key: cast(object, raw[key]) for key in MANIFEST_FIELDS}


@dataclass(frozen=True, slots=True)
class OtaDecision:
    action: str
    version: str | None
    reason: str


class OtaHealthLedger:
    """Estado host-side; la integración A/B física queda explícitamente separada."""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self._save({"healthy": None, "candidate": None, "checks": {}})
        os.chmod(path, 0o600)

    def stage(self, manifest: dict[str, object]) -> None:
        state = self._load()
        candidate = {
            "version": manifest["version"],
            "sha256": manifest["firmware_sha256"],
            "commit": manifest["build_commit"],
        }
        if state["candidate"] is not None and state["candidate"] != candidate:
            raise FirmwareReleaseError("ya existe otro candidato OTA")
        state["candidate"] = candidate
        state["checks"] = {}
        self._save(state)

    def record_health(self, component: str, healthy: bool) -> OtaDecision:
        if component not in HEALTH_COMPONENTS:
            raise FirmwareReleaseError("componente health desconocido")
        state = self._load()
        candidate = state["candidate"]
        if not isinstance(candidate, dict):
            raise FirmwareReleaseError("no existe candidato OTA")
        checks = state["checks"]
        if not isinstance(checks, dict):
            raise FirmwareReleaseError("ledger OTA corrupto")
        checks[component] = healthy
        if not healthy:
            version = str(candidate["version"])
            state["candidate"] = None
            state["checks"] = {}
            self._save(state)
            return OtaDecision("rollback", version, f"health_failed:{component}")
        if set(checks) == HEALTH_COMPONENTS and all(checks.values()):
            state["healthy"] = candidate
            state["candidate"] = None
            state["checks"] = {}
            self._save(state)
            return OtaDecision("promote", str(candidate["version"]), "all_healthy")
        self._save(state)
        return OtaDecision("wait", str(candidate["version"]), "health_incomplete")

    def recover_interrupted(self) -> OtaDecision:
        state = self._load()
        candidate = state["candidate"]
        if not isinstance(candidate, dict):
            return OtaDecision("keep", None, "no_candidate")
        version = str(candidate["version"])
        state["candidate"] = None
        state["checks"] = {}
        self._save(state)
        return OtaDecision("rollback", version, "interrupted_before_promotion")

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise FirmwareReleaseError("ledger OTA corrupto") from error
        if not isinstance(value, dict) or set(value) != {"healthy", "candidate", "checks"}:
            raise FirmwareReleaseError("ledger OTA corrupto")
        return cast(dict[str, Any], value)

    def _save(self, state: dict[str, Any]) -> None:
        temporary = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temporary.write_text(
            json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(self._path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica releases OTA sin escribir la placa")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-manifest")
    create.add_argument("--firmware", required=True, type=Path)
    create.add_argument("--private-key", required=True, type=Path)
    create.add_argument("--version", required=True)
    create.add_argument("--board-id", required=True)
    create.add_argument("--build-commit", required=True)
    create.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("--manifest", required=True, type=Path)
    verify.add_argument("--firmware", required=True, type=Path)
    verify.add_argument("--public-key", required=True, type=Path)
    verify.add_argument("--board-id", required=True)
    args = parser.parse_args()

    if args.command == "create-manifest":
        manifest = create_manifest(
            args.firmware,
            args.private_key,
            version=args.version,
            board_id=args.board_id,
            build_commit=args.build_commit,
        )
        args.output.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Manifest firmado: {args.output}")
        return
    try:
        raw = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit("Manifest ilegible") from error
    verified = verify_manifest(
        raw,
        args.firmware,
        args.public_key,
        expected_board_id=args.board_id,
    )
    print(
        json.dumps(
            {
                "status": "verified",
                "version": verified["version"],
                "board_id": verified["board_id"],
                "firmware_sha256": verified["firmware_sha256"],
            },
            sort_keys=True,
        )
    )
