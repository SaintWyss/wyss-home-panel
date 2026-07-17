from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_documentation_gate_passes_repository() -> None:
    result = subprocess.run(  # noqa: S603 - executable and arguments are fixed by the test
        [sys.executable, "tools/check_docs.py", "--format", "json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["status"] == "ok"


def test_documentation_gate_rejects_missing_file(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 - executable and arguments are fixed by the test
        [
            sys.executable,
            str(ROOT / "tools" / "check_docs.py"),
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["failures"]


def test_ci_has_all_blocking_jobs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in ("domain", "bridge", "firmware", "secrets", "docs"):
        assert f"  {job}:" in workflow
    assert "continue-on-error: true" not in workflow
    assert "python tools/check_docs.py --format json" in workflow
