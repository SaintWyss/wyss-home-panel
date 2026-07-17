from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
RUNNER = ROOT / "scripts" / "verify_baseline.sh"


def _fake_tool(path: Path, name: str) -> None:
    path.joinpath(name).write_text(
        """#!/usr/bin/env bash
set -eu
tool=$(basename "$0")
step=${WYSS_FAKE_FAILURE:-}
if [[ "$tool" == uv && "${1:-}" == --version ]]; then
  echo 'uv 0.11.18 (fixture)'; exit 0
fi
if [[ "$tool" == pio && "${1:-}" == --version ]]; then
  [[ "$step" == environment ]] && exit 1
  echo 'PlatformIO Core, version 6.1.19'; exit 0
fi
if [[ "$tool" == uv && " ${*} " == *' sync '* && "$step" == dependency ]]; then exit 1; fi
if [[ "$tool" == uv && " ${*} " == *' ruff check '* && "$step" == code ]]; then exit 1; fi
if [[ "$tool" == uv && " ${*} " == *'check_baseline_evidence.py'* \
  && "$step" == evidence ]]; then exit 1; fi
if [[ "$tool" == uvx && " ${*} " == *'cmake --version'* ]]; then echo 'cmake version 4.1.2'; fi
exit 0
""",
        encoding="utf-8",
    )
    path.joinpath(name).chmod(0o700)


def _run(tmp_path: Path, failure: str, mode: str = "automated") -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for tool in ("uv", "uvx", "pio", "c++"):
        _fake_tool(fake_bin, tool)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "WYSS_FAKE_FAILURE": failure,
            "WYSS_SECRET_SENTINEL": "NEVER_RENDER_THIS_SENTINEL",
        }
    )
    return subprocess.run(  # noqa: S603 - fixed repository script
        [str(RUNNER), mode], cwd=ROOT, env=env, check=False, capture_output=True, text=True
    )


def test_runner_is_isolated_and_redacts_environment(tmp_path: Path) -> None:
    result = _run(tmp_path, "")
    assert result.returncode == 0, result.stderr
    assert "NEVER_RENDER_THIS_SENTINEL" not in result.stdout + result.stderr
    runner = RUNNER.read_text(encoding="utf-8")
    for relative in ("uv", "venv", "platformio", "cmake"):
        assert ".cache/wyss-baseline" in runner
        assert relative in runner
    for forbidden in ("eval", "sudo", "provision.py", "--target upload"):
        assert forbidden not in runner
    assert "pytest bridge/tests" in runner
    assert "ctest --test-dir" in runner


def test_runner_classifies_code_failure(tmp_path: Path) -> None:
    assert _run(tmp_path, "code").returncode == 10


def test_runner_classifies_dependency_failure(tmp_path: Path) -> None:
    assert _run(tmp_path, "dependency").returncode == 20


def test_runner_classifies_environment_failure(tmp_path: Path) -> None:
    assert _run(tmp_path, "environment").returncode == 30


def test_runner_classifies_evidence_failure(tmp_path: Path) -> None:
    assert _run(tmp_path, "evidence", "all").returncode == 40
