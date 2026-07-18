from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_requirement_evidence", ROOT / "tools" / "check_requirement_evidence.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence() -> dict[str, object]:
    return json.loads(
        (ROOT / "docs" / "evidence" / "requirements-v2.json").read_text(encoding="utf-8")
    )


def test_all_fifty_one_requirements_have_test_or_only_explicit_external_gate() -> None:
    result = _module().validate(ROOT)

    assert result["status"] == "ok"
    assert result["requirements"] == 51
    assert result["automated"] == {
        "blocked_external_gate": 4,
        "not_applicable": 2,
        "passed": 45,
    }


def test_missing_requirement_or_unclassified_open_work_fails(tmp_path: Path) -> None:
    module = _module()
    raw = _evidence()
    requirements = raw["requirements"]
    assert isinstance(requirements, list)
    requirements.pop()
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(module.EvidenceError, match="cobertura distinta"):
        module.validate(ROOT, incomplete)

    raw = _evidence()
    requirements = raw["requirements"]
    assert isinstance(requirements, list)
    base04 = next(item for item in requirements if item["id"] == "BASE-04")
    base04["remaining_gates"] = []
    unclassified = tmp_path / "unclassified.json"
    unclassified.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(module.EvidenceError, match="abierto sin gate"):
        module.validate(ROOT, unclassified)
