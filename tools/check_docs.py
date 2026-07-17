#!/usr/bin/env python3
"""Valida la documentación esencial y sus enlaces locales."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCUMENTS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/architecture.md",
    "docs/hardware.md",
    "docs/operations.md",
    "docs/performance.md",
    "docs/protocol.md",
    "docs/security.md",
)
LINK_RE = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def validate(root: Path) -> list[dict[str, str]]:
    root = root.resolve()
    failures: list[dict[str, str]] = []
    for relative in REQUIRED_DOCUMENTS:
        path = root / relative
        if not path.is_file():
            failures.append({"file": relative, "error": "missing"})
            continue
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            failures.append({"file": relative, "error": "empty"})
            continue
        for target in LINK_RE.findall(content):
            clean = target.split("#", 1)[0].strip()
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            candidate = (path.parent / clean).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                failures.append({"file": relative, "error": "link_outside_root"})
                continue
            if not candidate.exists():
                failures.append({"file": relative, "error": "broken_link"})
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)
    failures = validate(args.root)
    result = {
        "schema_version": 1,
        "status": "ok" if not failures else "error",
        "failures": failures,
    }
    if args.format == "json":
        print(json.dumps(result))
    elif failures:
        for failure in failures:
            print(f"FAIL {failure['file']}: {failure['error']}")
    else:
        print("PASS documentación esencial")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
