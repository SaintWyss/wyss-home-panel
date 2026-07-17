from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
CHECKER = ROOT / "tools/check_architecture.py"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and checker
        [sys.executable, str(CHECKER), "--root", str(root), "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_repository_respects_hexagonal_boundaries() -> None:
    result = _run(ROOT)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["status"] == "ok"


def test_python_domain_cannot_import_adapter(tmp_path: Path) -> None:
    domain = tmp_path / "bridge/src/wyss_panel_bridge/domain"
    domain.mkdir(parents=True)
    (domain / "bad.py").write_text(
        "from wyss_panel_bridge.adapters.tuya import TuyaGateway\n", encoding="utf-8"
    )
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "domain_imports_adapters" in result.stdout


def test_cpp_application_cannot_include_adapter(tmp_path: Path) -> None:
    package = tmp_path / "bridge/src/wyss_panel_bridge"
    package.mkdir(parents=True)
    cpp = tmp_path / "firmware/src/application"
    cpp.mkdir(parents=True)
    (cpp / "bad.cpp").write_text('#include "wyss/adapters/bridge_client.hpp"\n', encoding="utf-8")
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "application_includes_adapters" in result.stdout
