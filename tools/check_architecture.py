#!/usr/bin/env python3
"""Bloquea dependencias que apunten desde capas internas hacia adapters."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "wyss_panel_bridge"
CPP_INCLUDE_RE = re.compile(r'^\s*#include\s+"wyss/([^/"]+)/', re.MULTILINE)


def _python_layer(path: Path, package_root: Path) -> str | None:
    relative = path.relative_to(package_root)
    if relative.parts[0] == "domain":
        return "domain"
    if relative.parts[0] == "application":
        return "application"
    if relative.name in {"ports.py", "ports_v2.py"}:
        return "ports"
    if relative.parts[0] == "adapters":
        return "adapters"
    return None


def _import_layer(module: str) -> str | None:
    if not module.startswith(f"{PACKAGE}."):
        return None
    child = module.removeprefix(f"{PACKAGE}.").split(".", 1)[0]
    if child in {"ports", "ports_v2"}:
        return "ports"
    if child in {"domain", "application", "adapters"}:
        return child
    return "composition"


def _python_failures(root: Path) -> list[dict[str, str]]:
    package_root = root / "bridge/src/wyss_panel_bridge"
    failures: list[dict[str, str]] = []
    forbidden = {
        "domain": {"ports", "application", "adapters", "composition"},
        "ports": {"application", "adapters", "composition"},
        "application": {"adapters", "composition"},
        "adapters": set(),
    }
    if not package_root.is_dir():
        return [{"file": str(package_root), "error": "missing_python_package"}]
    for path in sorted(package_root.rglob("*.py")):
        layer = _python_layer(path, package_root)
        if layer is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            failures.append(
                {"file": str(path.relative_to(root)), "error": "unreadable_python"}
            )
            continue
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
        for module in modules:
            imported = _import_layer(module)
            if imported in forbidden[layer]:
                failures.append(
                    {
                        "file": str(path.relative_to(root)),
                        "error": f"{layer}_imports_{imported}",
                    }
                )
    return failures


def _cpp_layer(path: Path) -> str | None:
    parts = path.parts
    try:
        firmware = parts.index("firmware")
    except ValueError:
        return None
    if firmware + 2 >= len(parts):
        return None
    child = parts[firmware + 2]
    if child == "wyss" and firmware + 3 < len(parts):
        child = parts[firmware + 3]
    return (
        child
        if child in {"domain", "protocol", "ports", "application", "adapters"}
        else None
    )


def _cpp_failures(root: Path) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    forbidden = {
        "domain": {"protocol", "ports", "application", "adapters"},
        "protocol": {"ports", "application", "adapters"},
        "ports": {"application", "adapters"},
        "application": {"adapters"},
        "adapters": set(),
    }
    paths = [
        *root.glob("firmware/include/wyss/**/*.hpp"),
        *root.glob("firmware/src/**/*.cpp"),
    ]
    for path in sorted(paths):
        layer = _cpp_layer(path)
        if layer is None:
            continue
        try:
            imports = CPP_INCLUDE_RE.findall(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            failures.append(
                {"file": str(path.relative_to(root)), "error": "unreadable_cpp"}
            )
            continue
        for imported in imports:
            if imported in forbidden[layer]:
                failures.append(
                    {
                        "file": str(path.relative_to(root)),
                        "error": f"{layer}_includes_{imported}",
                    }
                )
    return failures


def validate(root: Path) -> list[dict[str, str]]:
    root = root.resolve()
    return _python_failures(root) + _cpp_failures(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)
    failures = validate(args.root)
    payload = {
        "schema_version": 1,
        "status": "error" if failures else "ok",
        "failures": failures,
    }
    if args.format == "json":
        print(json.dumps(payload, sort_keys=True))
    elif failures:
        for failure in failures:
            print(f"FAIL {failure['file']}: {failure['error']}")
    else:
        print("PASS architecture boundaries")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
