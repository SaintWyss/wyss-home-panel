from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
CHECKER = ROOT / "tools" / "check_baseline_evidence.py"
TEMPLATE = ROOT / "docs" / "evidence" / "pr-00" / "manifest.json"
COMMIT = "a" * 40


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    _write(path, payload)
    return payload


def _run(
    manifest: Path, *args: str, allowed: tuple[Path, ...] = ()
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(CHECKER), str(manifest), *args]
    for path in allowed or (manifest,):
        command.extend(("--allow-path", str(path)))
    return subprocess.run(  # noqa: S603 - executable and checker are fixed
        command, cwd=ROOT, check=False, capture_output=True, text=True
    )


def _verified(path: Path) -> dict[str, Any]:
    payload = _manifest(path)
    payload["status"] = "VERIFIED"
    payload["tested_commit"] = COMMIT
    for name, item in payload["evidence"].items():
        item.update(
            {
                "status": "VERIFIED",
                "tested_commit": COMMIT,
                "observed_at": "2026-07-17T20:00:00Z",
                "artifact_ref": f"external://pr00/{name}",
                "sha256": "b" * 64,
            }
        )
    _write(path, payload)
    return payload


def test_incomplete_manifest_returns_40(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _manifest(manifest)
    result = _run(manifest)
    assert result.returncode == 40, result.stderr
    assert json.loads(result.stdout)["verified"] == 0


def test_complete_physical_manifest_returns_zero(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _verified(manifest)
    result = _run(manifest, "--expected-commit", COMMIT)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "VERIFIED"


def test_binding_uses_exact_allowed_source(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    source = tmp_path / "branch-protection.json"
    _manifest(manifest)
    _write(source, {"tested_commit": COMMIT})
    result = _run(
        manifest,
        "--bind-from",
        str(source),
        allowed=(manifest, source),
    )
    assert result.returncode == 40, result.stderr
    bound = json.loads(manifest.read_text(encoding="utf-8"))
    assert bound["tested_commit"] == COMMIT
    assert {item["tested_commit"] for item in bound["evidence"].values()} == {COMMIT}


def test_same_basename_in_other_directory_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed" / "manifest.json"
    displaced = tmp_path / "other" / "manifest.json"
    _manifest(allowed)
    _manifest(displaced)
    result = _run(displaced, allowed=(allowed,))
    assert result.returncode == 1


def test_sha_mismatch_is_invalid(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    payload = _verified(manifest)
    payload["evidence"]["touch_handler"]["tested_commit"] = "c" * 40
    _write(manifest, payload)
    assert _run(manifest).returncode == 1


def test_simulation_cannot_verify_physical_item(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    payload = _verified(manifest)
    payload["evidence"]["real_light_smoke"]["provenance"] = "simulation"
    _write(manifest, payload)
    assert _run(manifest).returncode == 1


def test_secret_is_rejected_without_rendering_it(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    payload = _manifest(manifest)
    sentinel = "WYSS_SECRET_SENTINEL-DO-NOT-PRINT"
    payload["evidence"]["factory_backup"]["result"] = sentinel
    _write(manifest, payload)
    result = _run(manifest)
    assert result.returncode == 1
    assert sentinel not in result.stdout + result.stderr


def test_closed_schema_rejects_extra_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    payload = _manifest(manifest)
    payload["unexpected"] = True
    _write(manifest, payload)
    assert _run(manifest).returncode == 1
