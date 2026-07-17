from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
DOCTOR = ROOT / "tools" / "doctor.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - executable and arguments are fixed by the test
        [sys.executable, str(DOCTOR), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_doctor_json_contract() -> None:
    result = _run("--format", "json")
    assert result.returncode in {0, 1}
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["status"] in {"ok", "error"}
    assert {item["status"] for item in payload["checks"]} <= {"pass", "fail"}


def test_doctor_rejects_inline_secret_without_rendering_it(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = config_dir / "local.toml"
    sentinel = "NEVER_PRINT_THIS_SECRET"
    config.write_text(
        f"""
[panel]
token_sha256 = "{"a" * 64}"
primary_entity = "light.fixture"
allowed_entities = ["light.fixture"]
[devices]
provider = "tuya"
[tuya]
local_key = "{sentinel}"
""",
        encoding="utf-8",
    )
    config.chmod(stat.S_IRUSR | stat.S_IWUSR)
    target = ROOT / "config" / "doctor-test-local.toml"
    target.write_text(config.read_text(encoding="utf-8"), encoding="utf-8")
    target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    try:
        result = _run("--config", str(target), "--format", "json")
    finally:
        target.unlink()
    assert result.returncode == 1
    assert sentinel not in result.stdout
    assert sentinel not in result.stderr
    checks = {item["id"]: item for item in json.loads(result.stdout)["checks"]}
    assert checks["config.provider_secrets"]["status"] == "fail"


def test_doctor_rejects_config_outside_repository(tmp_path: Path) -> None:
    config = tmp_path / "local.toml"
    config.write_text("[panel]\n", encoding="utf-8")
    result = _run("--config", str(config), "--format", "json")
    assert result.returncode == 1
    checks = {item["id"]: item for item in json.loads(result.stdout)["checks"]}
    assert checks["config"]["status"] == "fail"


def test_doctor_invalid_arguments_return_2() -> None:
    assert _run("--format", "xml").returncode == 2
