from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "tools" / "generate_sbom.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_sbom", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sbom_is_deterministic_complete_and_contains_only_immutable_firmware_pins() -> None:
    generator = _module()
    first = generator.generate(ROOT)
    second = generator.generate(ROOT)

    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert first["specVersion"] == "1.6"
    components = first["components"]
    purls = {item["purl"] for item in components}
    assert len(purls) == len(components)
    assert "pkg:pypi/fastapi@0.139.2" in purls
    assert "pkg:platformio/lvgl/lvgl@8.4.0" in purls
    github_firmware = [item for item in components if item["purl"].startswith("pkg:github/esp-")]
    assert github_firmware
    assert all(len(item["version"]) == 40 for item in github_firmware)


def test_sbom_check_rejects_drift(tmp_path: Path) -> None:
    generator = _module()
    expected = tmp_path / "sbom.cdx.json"
    expected.write_text("{}\n", encoding="utf-8")

    assert generator.main(["--root", str(ROOT), "--check", str(expected)]) == 1
    assert generator.main(["--root", str(ROOT), "--output", str(expected)]) == 0
    assert generator.main(["--root", str(ROOT), "--check", str(expected)]) == 0
