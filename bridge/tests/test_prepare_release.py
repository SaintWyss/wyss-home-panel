from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "prepare_release", ROOT / "tools" / "prepare_release.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    firmware = tmp_path / "firmware.bin"
    firmware.write_bytes(b"firmware-v2")
    wheel = tmp_path / "wyss_home_panel_bridge-2.0.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel-v2")
    sbom = tmp_path / "sbom.json"
    sbom.write_text(
        json.dumps({"metadata": {"component": {"version": "2.0.0"}}}),
        encoding="utf-8",
    )
    return firmware, wheel, sbom


def test_candidate_is_deterministic_and_explicitly_blocked(tmp_path: Path) -> None:
    module = _module()
    firmware, wheel, sbom = _inputs(tmp_path)

    first = module.prepare_candidate(
        tmp_path / "first",
        firmware=firmware,
        bridge_wheel=wheel,
        sbom=sbom,
        version="2.0.0",
        source_commit="a" * 40,
    )
    second = module.prepare_candidate(
        tmp_path / "second",
        firmware=firmware,
        bridge_wheel=wheel,
        sbom=sbom,
        version="2.0.0",
        source_commit="a" * 40,
    )

    assert first == second
    assert first["status"] == "BLOCKED_CANDIDATE"
    assert len(first["unresolved_gates"]) == 5
    assert (tmp_path / "first" / "RELEASE_BLOCKED").is_file()
    assert (tmp_path / "first" / "SHA256SUMS").read_text() == (
        tmp_path / "second" / "SHA256SUMS"
    ).read_text()


def test_candidate_rejects_version_mismatch_and_nonempty_output(tmp_path: Path) -> None:
    module = _module()
    firmware, wheel, sbom = _inputs(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    (output / "keep").write_text("user data", encoding="utf-8")

    with pytest.raises(module.ReleaseCandidateError, match="vacío"):
        module.prepare_candidate(
            output,
            firmware=firmware,
            bridge_wheel=wheel,
            sbom=sbom,
            version="2.0.0",
            source_commit="b" * 40,
        )

    with pytest.raises(module.ReleaseCandidateError, match="wheel"):
        module.prepare_candidate(
            tmp_path / "other",
            firmware=firmware,
            bridge_wheel=wheel,
            sbom=sbom,
            version="2.0.1",
            source_commit="b" * 40,
        )
