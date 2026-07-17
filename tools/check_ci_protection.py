#!/usr/bin/env python3
"""Valida el contrato CI local, check-runs reales y protección de main."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DEFAULT_CONTRACT = ROOT / ".github/required-checks.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*-\s+uses:\s*([^\s@]+)@([^\s#]+)", re.MULTILINE)
JOB_RE = re.compile(r"^  ([a-z][a-z0-9_-]*):\s*$", re.MULTILINE)


class ContractError(ValueError):
    """Error de validación sin incluir respuestas o secretos externos."""


def _json(path: Path | str | TextIO) -> dict[str, Any]:
    try:
        if path == "-":
            value = json.load(sys.stdin)
        elif hasattr(path, "read"):
            value = json.load(path)  # type: ignore[arg-type]
        else:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractError("JSON inválido o ilegible") from error
    if not isinstance(value, dict):
        raise ContractError("la respuesta debe ser un objeto")
    return value


def _contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    value = _json(path)
    required = {
        "schema_version",
        "repository",
        "branch",
        "checks",
        "pins",
        "protection",
    }
    if set(value) != required or value.get("schema_version") != 1:
        raise ContractError("contrato de checks inválido")
    checks = value.get("checks")
    if not isinstance(checks, list) or len(checks) != 5:
        raise ContractError("el contrato debe contener cinco checks")
    expected_ids = {"domain", "bridge", "firmware", "secrets", "docs"}
    if {
        item.get("job_id") for item in checks if isinstance(item, dict)
    } != expected_ids:
        raise ContractError("los job ids no coinciden")
    names = [item.get("name") for item in checks if isinstance(item, dict)]
    if (
        len(names) != 5
        or len(set(names)) != 5
        or not all(isinstance(x, str) for x in names)
    ):
        raise ContractError("los nombres visibles no son cinco valores únicos")
    pins = value.get("pins")
    if not isinstance(pins, dict) or set(pins) != {
        "actions/checkout",
        "actions/setup-python",
        "gitleaks/gitleaks-action",
    }:
        raise ContractError("pins incompletos")
    if not all(isinstance(pin, str) and SHA_RE.fullmatch(pin) for pin in pins.values()):
        raise ContractError("pin no inmutable")
    return value


def _job_block(text: str, job_id: str) -> str:
    match = re.search(
        rf"^  {re.escape(job_id)}:\s*$\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:\s*$|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ContractError(f"falta el job {job_id}")
    return match.group("body")


def validate_local(workflow: Path, contract_path: Path) -> dict[str, Any]:
    contract = _contract(contract_path)
    try:
        text = workflow.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ContractError("workflow ilegible") from error
    for forbidden in ("pull_request_target", "continue-on-error: true"):
        if forbidden in text:
            raise ContractError("workflow contiene una capacidad prohibida")
    if re.search(r"permissions:.*?\bwrite\b", text, re.DOTALL):
        raise ContractError("workflow solicita permisos write")
    if "permissions:\n  contents: read\n  pull-requests: read" not in text:
        raise ContractError("permisos globales no son read-only")

    declared = set(JOB_RE.findall(text[text.find("jobs:") :]))
    expected = {item["job_id"] for item in contract["checks"]}
    if declared != expected:
        raise ContractError("los jobs del workflow no coinciden exactamente")
    for item in contract["checks"]:
        block = _job_block(text, item["job_id"])
        if f"    name: {item['name']}" not in block:
            raise ContractError(f"nombre visible incorrecto en {item['job_id']}")

    uses = USES_RE.findall(text)
    if not uses or any(not SHA_RE.fullmatch(ref) for _, ref in uses):
        raise ContractError("toda action debe usar SHA completo")
    pins = contract["pins"]
    for action, ref in uses:
        if action not in pins or ref != pins[action]:
            raise ContractError("action o scanner no coincide con el pin aprobado")
    if sum(action == "gitleaks/gitleaks-action" for action, _ in uses) != 1:
        raise ContractError("la cadena gitleaks debe aparecer exactamente una vez")

    domain = _job_block(text, "domain")
    bridge = _job_block(text, "bridge")
    firmware = _job_block(text, "firmware")
    secrets = _job_block(text, "secrets")
    docs = _job_block(text, "docs")
    required_fragments = (
        (domain, "ctest --test-dir build --output-on-failure"),
        (bridge, "uv sync --project bridge --locked --extra dev"),
        (bridge, "ruff check"),
        (bridge, "mypy bridge/src"),
        (bridge, "pytest bridge/tests --quiet"),
        (bridge, "python tools/check_architecture.py --format json"),
        (firmware, "platformio==6.1.19"),
        (firmware, "pio run -e waveshare_esp32_s3_touch_lcd_7"),
        (docs, "python tools/check_docs.py --format json"),
    )
    if any(fragment not in block for block, fragment in required_fragments):
        raise ContractError("falta un gate obligatorio")
    checkout_at = secrets.find(f"actions/checkout@{pins['actions/checkout']}")
    gitleaks_at = secrets.find(
        f"gitleaks/gitleaks-action@{pins['gitleaks/gitleaks-action']}"
    )
    if checkout_at < 0 or gitleaks_at <= checkout_at or "fetch-depth: 0" not in secrets:
        raise ContractError("cadena secrets/gitleaks incompleta")
    return {"schema_version": 1, "status": "ok", "jobs": sorted(expected)}


def validate_check_runs(
    payload: dict[str, Any], tested_commit: str, contract_path: Path
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(tested_commit):
        raise ContractError("tested_commit inválido")
    contract = _contract(contract_path)
    runs = payload.get("check_runs")
    if not isinstance(runs, list) or len(runs) != 5:
        raise ContractError("se requieren exactamente cinco check-runs")
    expected = {item["name"] for item in contract["checks"]}
    observed: set[str] = set()
    conclusions: dict[str, str] = {}
    for run in runs:
        if not isinstance(run, dict):
            raise ContractError("check-run inválido")
        name = run.get("name")
        if name not in expected or name in observed:
            raise ContractError("contexto inesperado o duplicado")
        if run.get("head_sha") != tested_commit:
            raise ContractError("check-run atribuido a otro SHA")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ContractError("check-run incompleto o fallido")
        observed.add(name)
        conclusions[str(name)] = "success"
    if observed != expected:
        raise ContractError("falta un contexto requerido")
    return {
        "schema_version": 1,
        "status": "VERIFIED",
        "tested_commit": tested_commit,
        "checks": conclusions,
    }


def _enabled(value: Any) -> bool:
    return isinstance(value, dict) and value.get("enabled") is True


def validate_remote(payload: dict[str, Any], contract_path: Path) -> dict[str, Any]:
    contract = _contract(contract_path)
    required = payload.get("required_status_checks")
    if not isinstance(required, dict) or required.get("strict") is not True:
        raise ContractError("required_status_checks.strict no está activo")
    contexts = required.get("contexts")
    if not isinstance(contexts, list):
        checks = required.get("checks")
        contexts = (
            [item.get("context") for item in checks] if isinstance(checks, list) else []
        )
    expected = {item["name"] for item in contract["checks"]}
    if set(contexts) != expected or len(contexts) != 5:
        raise ContractError("required checks remotos no coinciden")
    reviews = payload.get("required_pull_request_reviews")
    if not isinstance(reviews, dict):
        raise ContractError("faltan revisiones requeridas")
    if (
        reviews.get("required_approving_review_count", 0) < 1
        or reviews.get("dismiss_stale_reviews") is not True
    ):
        raise ContractError("política de revisiones incompleta")
    if not _enabled(payload.get("enforce_admins")):
        raise ContractError("enforce_admins no está activo")
    if not _enabled(payload.get("required_conversation_resolution")):
        raise ContractError("resolución de conversaciones no está activa")
    for field in ("allow_force_pushes", "allow_deletions"):
        value = payload.get(field)
        if not isinstance(value, dict) or value.get("enabled") is not False:
            raise ContractError(f"{field} no está deshabilitado")
    return {
        "schema_version": 1,
        "status": "VERIFIED",
        "strict": True,
        "required_checks": sorted(expected),
        "enforce_admins": True,
        "required_conversation_resolution": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--local", action="store_true")
    modes.add_argument("--check-runs-json")
    modes.add_argument("--remote-json")
    parser.add_argument("--tested-commit")
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.local:
            result = validate_local(args.workflow, args.contract)
        elif args.check_runs_json is not None:
            if args.tested_commit is None:
                raise ContractError("--tested-commit es obligatorio")
            result = validate_check_runs(
                _json(args.check_runs_json), args.tested_commit, args.contract
            )
        else:
            result = validate_remote(_json(args.remote_json), args.contract)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ContractError as error:
        print(f"ci-protection: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("ci-protection: error interno redactado", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
