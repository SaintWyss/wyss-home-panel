#!/usr/bin/env python3
"""Valida y liga evidencia PR-00 sin aceptar simulaciones ni secretos."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/evidence/pr-00/manifest.json"
DEFAULT_ALLOWLIST = ROOT / "config/baseline-evidence-allowlist.json"
SCHEMA = ROOT / "schemas/pr00-evidence.schema.json"
EXIT_INVALID = 1
EXIT_INCOMPLETE = 40
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
SENSITIVE_KEY_RE = re.compile(
    r"(?:token|password|secret|credential|private_key|local_key)", re.IGNORECASE
)
SENSITIVE_VALUE_RE = re.compile(
    r"(?:WYSS_SECRET_SENTINEL|BEGIN [A-Z ]*PRIVATE KEY|password\s*=|local_key\s*=)",
    re.IGNORECASE,
)
EVIDENCE_KEYS = {
    "factory_backup",
    "lvgl_cycle",
    "touch_handler",
    "tuya_round_trip",
    "firmware_resources",
    "real_light_smoke",
    "rollback",
    "branch_protection",
}
PHYSICAL_KEYS = EVIDENCE_KEYS - {"firmware_resources", "branch_protection"}
ITEM_KEYS = {
    "status",
    "tested_commit",
    "observed_at",
    "provenance",
    "hardware",
    "tool",
    "result",
    "artifact_ref",
    "sha256",
}


class EvidenceError(ValueError):
    """Error seguro que nunca incluye contenido controlado por el manifest."""


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("archivo ausente, irregular o symlink")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError("JSON inválido o ilegible") from error
    if not isinstance(value, dict):
        raise EvidenceError("la raíz debe ser un objeto")
    return value


def _canonical(path: Path) -> Path:
    try:
        return path.resolve(strict=True)
    except OSError as error:
        raise EvidenceError("ruta ausente") from error


def _load_allowed(explicit: list[Path]) -> set[Path]:
    if explicit:
        return {
            _canonical(path if path.is_absolute() else ROOT / path) for path in explicit
        }
    raw = _load_json(DEFAULT_ALLOWLIST)
    if set(raw) != {"schema_version", "paths"} or raw.get("schema_version") != 1:
        raise EvidenceError("allowlist inválida")
    paths = raw.get("paths")
    if (
        not isinstance(paths, list)
        or not paths
        or not all(isinstance(x, str) for x in paths)
    ):
        raise EvidenceError("allowlist inválida")
    resolved: set[Path] = set()
    for relative in paths:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise EvidenceError("allowlist contiene una ruta insegura")
        resolved.add((ROOT / candidate).resolve())
    return resolved


def _require_allowed(
    path: Path, allowed: set[Path], *, must_exist: bool = True
) -> Path:
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError as error:
        raise EvidenceError("ruta ausente") from error
    if path.is_symlink() or resolved not in allowed:
        raise EvidenceError("ruta fuera de la allowlist exacta")
    return resolved


def _reject_sensitive(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                raise EvidenceError("campo sensible prohibido")
            _reject_sensitive(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive(child)
    elif isinstance(value, str) and SENSITIVE_VALUE_RE.search(value):
        raise EvidenceError("contenido sensible prohibido")


def _validate_item(
    name: str, item: Any, tested_commit: str | None, allowed: set[Path]
) -> bool:
    if not isinstance(item, dict) or set(item) != ITEM_KEYS:
        raise EvidenceError(f"estructura cerrada inválida en {name}")
    status = item["status"]
    if status not in {"NOT_VERIFIED", "VERIFIED"}:
        raise EvidenceError(f"status inválido en {name}")
    provenance = item["provenance"]
    expected = (
        "physical"
        if name in PHYSICAL_KEYS
        else ("automated" if name == "firmware_resources" else "external")
    )
    if provenance != expected:
        raise EvidenceError(f"provenance inválida en {name}")
    for field in ("hardware", "tool", "result"):
        if not isinstance(item[field], str) or not item[field].strip():
            raise EvidenceError(f"campo requerido inválido en {name}")

    item_commit = item["tested_commit"]
    observed_at = item["observed_at"]
    artifact_ref = item["artifact_ref"]
    checksum = item["sha256"]
    if status == "VERIFIED":
        if not isinstance(tested_commit, str) or item_commit != tested_commit:
            raise EvidenceError(f"tested_commit no coincide en {name}")
        if not isinstance(observed_at, str) or not UTC_RE.fullmatch(observed_at):
            raise EvidenceError(f"observed_at debe ser UTC en {name}")
        if not isinstance(artifact_ref, str) or not artifact_ref:
            raise EvidenceError(f"falta artifact_ref en {name}")
        if not isinstance(checksum, str) or not SHA256_RE.fullmatch(checksum):
            raise EvidenceError(f"falta sha256 válido en {name}")
    else:
        if item_commit is not None and not SHA_RE.fullmatch(str(item_commit)):
            raise EvidenceError(f"tested_commit inválido en {name}")
        if observed_at is not None and not UTC_RE.fullmatch(str(observed_at)):
            raise EvidenceError(f"observed_at inválido en {name}")
        if checksum is not None and not SHA256_RE.fullmatch(str(checksum)):
            raise EvidenceError(f"sha256 inválido en {name}")

    if isinstance(artifact_ref, str) and not artifact_ref.startswith("external://"):
        relative = Path(artifact_ref)
        if relative.is_absolute() or ".." in relative.parts:
            raise EvidenceError(f"artifact_ref inseguro en {name}")
        if status == "VERIFIED":
            artifact = _require_allowed(ROOT / relative, allowed)
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if digest != checksum:
                raise EvidenceError(f"checksum no coincide en {name}")
    elif artifact_ref is not None and not isinstance(artifact_ref, str):
        raise EvidenceError(f"artifact_ref inválido en {name}")
    return status == "VERIFIED"


def validate(
    manifest_path: Path, allowed: set[Path], expected_commit: str | None = None
) -> tuple[int, dict[str, Any]]:
    if not SCHEMA.is_file():
        raise EvidenceError("falta el schema versionado")
    _require_allowed(manifest_path, allowed)
    manifest = _load_json(manifest_path)
    _reject_sensitive(manifest)
    if set(manifest) != {"schema_version", "status", "tested_commit", "evidence"}:
        raise EvidenceError("estructura raíz cerrada inválida")
    if manifest["schema_version"] != 1:
        raise EvidenceError("schema_version inválido")
    status = manifest["status"]
    if status not in {"NOT_VERIFIED", "VERIFIED"}:
        raise EvidenceError("status raíz inválido")
    tested_commit = manifest["tested_commit"]
    if tested_commit is not None and not SHA_RE.fullmatch(str(tested_commit)):
        raise EvidenceError("tested_commit raíz inválido")
    if expected_commit is not None:
        if not SHA_RE.fullmatch(expected_commit) or tested_commit != expected_commit:
            raise EvidenceError("tested_commit no coincide con el esperado")
    evidence = manifest["evidence"]
    if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_KEYS:
        raise EvidenceError("conjunto de evidencia incompleto o extendido")
    verified = sum(
        _validate_item(name, item, tested_commit, allowed)
        for name, item in evidence.items()
    )
    all_verified = verified == len(EVIDENCE_KEYS)
    if (status == "VERIFIED") != all_verified:
        raise EvidenceError("status raíz no coincide con los items")
    payload = {
        "schema_version": 1,
        "status": status,
        "tested_commit": tested_commit,
        "verified": verified,
        "required": len(EVIDENCE_KEYS),
    }
    return (0 if all_verified else EXIT_INCOMPLETE), payload


def bind(manifest_path: Path, source_path: Path, allowed: set[Path]) -> str:
    manifest_resolved = _require_allowed(manifest_path, allowed)
    _require_allowed(source_path, allowed)
    source = _load_json(source_path)
    _reject_sensitive(source)
    commit = source.get("tested_commit")
    if not isinstance(commit, str) or not SHA_RE.fullmatch(commit):
        raise EvidenceError("fuente de binding sin tested_commit válido")
    manifest = _load_json(manifest_resolved)
    current = manifest.get("tested_commit")
    if current not in {None, commit}:
        raise EvidenceError("el manifest ya está ligado a otro commit")
    manifest["tested_commit"] = commit
    evidence = manifest.get("evidence")
    if not isinstance(evidence, dict):
        raise EvidenceError("manifest sin evidencia válida")
    for item in evidence.values():
        if not isinstance(item, dict) or item.get("tested_commit") not in {
            None,
            commit,
        }:
            raise EvidenceError("item ligado a otro commit")
        item["tested_commit"] = commit
    manifest_resolved.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return commit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--bind-from", type=Path)
    parser.add_argument("--allow-path", action="append", type=Path, default=[])
    parser.add_argument("--expected-commit")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        manifest = (
            args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
        )
        allowed = _load_allowed(args.allow_path)
        if args.bind_from is not None:
            source = (
                args.bind_from
                if args.bind_from.is_absolute()
                else ROOT / args.bind_from
            )
            bind(manifest, source, allowed)
        code, payload = validate(manifest, allowed, args.expected_commit)
        print(json.dumps(payload, sort_keys=True))
        return code
    except EvidenceError as error:
        print(f"baseline-evidence: {error}", file=sys.stderr)
        return EXIT_INVALID
    except Exception:
        print("baseline-evidence: error interno redactado", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())
