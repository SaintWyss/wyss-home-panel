#!/usr/bin/env python3
"""Prepara un candidato local trazable; nunca firma, etiqueta ni publica por sí solo."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?")
BOARD_ID = "waveshare-esp32-s3-touch-lcd-7"
BLOCKERS = (
    "signed-manifest-with-authorized-release-key",
    "branch-protection-and-required-ci",
    "72-hour-physical-soak",
    "physical-e2e-smoke",
    "upgrade-backup-restore-downgrade-drill",
)


class ReleaseCandidateError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_input(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ReleaseCandidateError(f"{label} ausente o vacío")


def prepare_candidate(
    output: Path,
    *,
    firmware: Path,
    bridge_wheel: Path,
    sbom: Path,
    version: str,
    source_commit: str,
) -> dict[str, Any]:
    """Copia artefactos y genera hashes sin confundir el candidato con una release aprobada."""
    if VERSION_RE.fullmatch(version) is None:
        raise ReleaseCandidateError("versión SemVer inválida")
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise ReleaseCandidateError("commit fuente inválido")
    _validate_input(firmware, "firmware")
    _validate_input(bridge_wheel, "wheel")
    _validate_input(sbom, "SBOM")
    if version not in bridge_wheel.name:
        raise ReleaseCandidateError("el wheel no coincide con la versión")
    try:
        decoded_sbom = json.loads(sbom.read_text(encoding="utf-8"))
        sbom_version = decoded_sbom["metadata"]["component"]["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError("SBOM inválido") from error
    if sbom_version != version:
        raise ReleaseCandidateError("el SBOM no coincide con la versión")

    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ReleaseCandidateError("el directorio de candidato debe estar vacío")
    destinations = (
        (
            "firmware",
            firmware,
            output / f"wyss-home-panel-{version}-{BOARD_ID}.bin",
        ),
        ("bridge-wheel", bridge_wheel, output / bridge_wheel.name),
        ("sbom", sbom, output / f"wyss-home-panel-{version}.cdx.json"),
    )
    artifacts: list[dict[str, object]] = []
    for kind, source, destination in destinations:
        shutil.copyfile(source, destination)
        artifacts.append(
            {
                "name": destination.name,
                "type": kind,
                "size": destination.stat().st_size,
                "sha256": _sha256(destination),
            }
        )
    artifacts.sort(key=lambda item: str(item["name"]))
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "status": "BLOCKED_CANDIDATE",
        "version": version,
        "source_commit": source_commit,
        "board_id": BOARD_ID,
        "artifacts": artifacts,
        "unresolved_gates": list(BLOCKERS),
    }
    (output / "release-candidate.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksums = "".join(f"{item['sha256']}  {item['name']}\n" for item in artifacts)
    (output / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    (output / "RELEASE_BLOCKED").write_text(
        "\n".join(BLOCKERS) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--firmware", required=True, type=Path)
    parser.add_argument("--bridge-wheel", required=True, type=Path)
    parser.add_argument("--sbom", required=True, type=Path)
    parser.add_argument("--version", default="2.0.0")
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = prepare_candidate(
            args.output,
            firmware=args.firmware,
            bridge_wheel=args.bridge_wheel,
            sbom=args.sbom,
            version=args.version,
            source_commit=args.source_commit,
        )
    except (OSError, ReleaseCandidateError) as error:
        print(f"release candidate: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
