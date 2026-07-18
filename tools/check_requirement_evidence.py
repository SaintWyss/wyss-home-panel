#!/usr/bin/env python3
"""Valida trazabilidad 1:1 y que sólo queden gates físicos/externos explícitos."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / ".planning" / "REQUIREMENTS.md"
EVIDENCE = ROOT / "docs" / "evidence" / "requirements-v2.json"
DEFINITION_RE = re.compile(r"^- \[(?P<checked>[ x])\] \*\*(?P<id>[A-Z]+-[0-9]+)\*\*:")
TRACE_RE = re.compile(
    r"^\| (?P<id>[A-Z]+-[0-9]+) \| (?P<phase>Phase [0-9]+ — PR-[0-9]+) \|"
)
ENTRY_KEYS = {
    "id",
    "phase",
    "automated_status",
    "tests",
    "verification",
    "remaining_gates",
}
GATE_KEYS = {"id", "kind", "reason"}
STATUSES = {"passed", "not_applicable", "blocked_external_gate"}
GATE_KINDS = {"physical", "external", "authorization"}


class EvidenceError(ValueError):
    pass


def _relative_file(root: Path, value: object, label: str) -> tuple[Path, str | None]:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise EvidenceError(f"{label}: referencia inválida")
    path_text, separator, selector = value.partition("::")
    path = Path(path_text)
    if ".." in path.parts:
        raise EvidenceError(f"{label}: path fuera del repositorio")
    resolved = root / path
    if not resolved.is_file():
        raise EvidenceError(f"{label}: no existe {path_text}")
    return resolved, selector if separator else None


def _definitions(text: str) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for line in text.splitlines():
        if match := DEFINITION_RE.match(line):
            identifier = match.group("id")
            if identifier in result:
                raise EvidenceError(f"requisito duplicado: {identifier}")
            result[identifier] = match.group("checked") == "x"
    return result


def _trace(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if match := TRACE_RE.match(line):
            identifier = match.group("id")
            if identifier in result:
                raise EvidenceError(f"mapeo duplicado: {identifier}")
            result[identifier] = match.group("phase")
    return result


def validate(root: Path = ROOT, evidence_path: Path | None = None) -> dict[str, Any]:
    requirements_path = root / ".planning" / "REQUIREMENTS.md"
    text = requirements_path.read_text(encoding="utf-8")
    definitions = _definitions(text)
    trace = _trace(text)
    path = evidence_path or root / "docs" / "evidence" / "requirements-v2.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "requirements"}:
        raise EvidenceError("schema raíz inválido")
    if raw["schema_version"] != 1 or not isinstance(raw["requirements"], list):
        raise EvidenceError("versión o lista de evidencia inválida")
    entries: dict[str, dict[str, Any]] = {}
    for value in raw["requirements"]:
        if not isinstance(value, dict) or set(value) != ENTRY_KEYS:
            raise EvidenceError("entrada de evidencia con schema inválido")
        entry = value
        identifier = entry["id"]
        if not isinstance(identifier, str) or identifier in entries:
            raise EvidenceError(f"id de evidencia duplicado o inválido: {identifier}")
        entries[identifier] = entry

    expected = set(definitions)
    if set(trace) != expected or set(entries) != expected:
        raise EvidenceError(
            "cobertura distinta de 51/51: "
            f"definitions={len(expected)} trace={len(trace)} evidence={len(entries)}"
        )
    for identifier in sorted(expected):
        entry = entries[identifier]
        if entry["phase"] != trace[identifier]:
            raise EvidenceError(f"{identifier}: fase no coincide")
        status = entry["automated_status"]
        if status not in STATUSES:
            raise EvidenceError(f"{identifier}: estado automatizado inválido")
        tests = entry["tests"]
        if not isinstance(tests, list) or any(
            not isinstance(item, str) for item in tests
        ):
            raise EvidenceError(f"{identifier}: tests inválidos")
        if status == "passed" and not tests:
            raise EvidenceError(f"{identifier}: PASS sin test")
        if status == "blocked_external_gate" and tests:
            raise EvidenceError(
                f"{identifier}: gate previo no debe simular implementación"
            )
        for reference in tests:
            test_path, selector = _relative_file(root, reference, identifier)
            if selector is not None and selector not in test_path.read_text(
                encoding="utf-8"
            ):
                raise EvidenceError(f"{identifier}: selector inexistente {selector}")
        _relative_file(root, entry["verification"], f"{identifier}.verification")

        gates = entry["remaining_gates"]
        if not isinstance(gates, list):
            raise EvidenceError(f"{identifier}: gates inválidos")
        seen_gates: set[str] = set()
        for gate in gates:
            if not isinstance(gate, dict) or set(gate) != GATE_KEYS:
                raise EvidenceError(f"{identifier}: gate con schema inválido")
            gate_id = gate["id"]
            if (
                not isinstance(gate_id, str)
                or not gate_id
                or gate_id in seen_gates
                or gate["kind"] not in GATE_KINDS
                or not isinstance(gate["reason"], str)
                or not gate["reason"]
            ):
                raise EvidenceError(f"{identifier}: gate inválido")
            seen_gates.add(gate_id)
        if definitions[identifier] and gates:
            raise EvidenceError(f"{identifier}: marcado completo pero conserva gates")
        if not definitions[identifier] and not gates:
            raise EvidenceError(
                f"{identifier}: abierto sin gate físico/externo/autorización"
            )
        if status in {"not_applicable", "blocked_external_gate"} and not gates:
            raise EvidenceError(f"{identifier}: estado bloqueado sin gate")

    counts = {
        status: sum(entry["automated_status"] == status for entry in entries.values())
        for status in sorted(STATUSES)
    }
    return {
        "schema_version": 1,
        "status": "ok",
        "requirements": len(entries),
        "checked_complete": sum(definitions.values()),
        "automated": counts,
        "remaining_gate_kinds": {
            kind: sum(
                gate["kind"] == kind
                for entry in entries.values()
                for gate in entry["remaining_gates"]
            )
            for kind in sorted(GATE_KINDS)
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        result = validate(args.root.resolve(), args.evidence)
    except (EvidenceError, OSError, json.JSONDecodeError) as error:
        if args.format == "json":
            print(
                json.dumps({"schema_version": 1, "status": "fail", "error": str(error)})
            )
        else:
            print(f"requirement evidence: FAIL: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "requirement evidence: PASS "
            f"requirements={result['requirements']} checked={result['checked_complete']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
