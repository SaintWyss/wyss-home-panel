#!/usr/bin/env python3
"""Genera un CycloneDX determinista desde los locks de Python y firmware."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_NAME = "wyss-home-panel"
PRODUCT_VERSION = "2.0.0"
PLATFORM_RE = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/releases/download/"
    r"(?P<version>[^/]+)/"
)
GIT_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^#]+?)(?:\.git)?#(?P<version>[0-9a-f]{40})$"
)
REGISTRY_RE = re.compile(r"(?P<owner>[^/]+)/(?P<name>[^@]+)@(?P<version>[^\s]+)$")


def _pypi_ref(name: str, version: str) -> str:
    return f"pkg:pypi/{quote(name.lower().replace('_', '-'))}@{quote(version)}"


def _component(
    name: str, version: str, purl: str, *, kind: str = "library"
) -> dict[str, Any]:
    return {
        "type": kind,
        "bom-ref": purl,
        "name": name,
        "version": version,
        "purl": purl,
    }


def _python_inventory(
    lock_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decoded = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = {str(item["name"]): item for item in decoded["package"]}
    root = packages["wyss-home-panel-bridge"]
    pending = [str(item["name"]) for item in root.get("dependencies", [])]
    selected: set[str] = set()
    while pending:
        name = pending.pop()
        if name in selected or name not in packages:
            continue
        selected.add(name)
        pending.extend(
            str(item["name"]) for item in packages[name].get("dependencies", [])
        )

    components: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    for name in sorted(selected):
        package = packages[name]
        version = str(package["version"])
        reference = _pypi_ref(name, version)
        item = _component(name, version, reference)
        source = package.get("sdist")
        if isinstance(source, dict) and str(source.get("hash", "")).startswith(
            "sha256:"
        ):
            item["hashes"] = [
                {
                    "alg": "SHA-256",
                    "content": str(source["hash"]).removeprefix("sha256:"),
                }
            ]
        components.append(item)
        children = [
            _pypi_ref(child, str(packages[child]["version"]))
            for child in sorted(
                {
                    str(value["name"])
                    for value in package.get("dependencies", [])
                    if str(value["name"]) in selected
                }
            )
        ]
        dependencies.append({"ref": reference, "dependsOn": children})
    return components, dependencies


def _firmware_inventory(platformio_path: Path) -> list[dict[str, Any]]:
    text = platformio_path.read_text(encoding="utf-8")
    components: list[dict[str, Any]] = []
    platform = re.search(r"^platform\s*=\s*(\S+)$", text, re.MULTILINE)
    if platform is None or (matched := PLATFORM_RE.search(platform.group(1))) is None:
        raise ValueError("platformio.ini no fija una plataforma GitHub versionada")
    owner, repo, version = matched.group("owner", "repo", "version")
    purl = f"pkg:github/{owner}/{repo}@{version}"
    components.append(_component(repo, version, purl, kind="framework"))

    block = re.search(
        r"^lib_deps\s*=\s*\n(?P<body>(?:[ \t]+\S.*\n?)+)", text, re.MULTILINE
    )
    if block is None:
        raise ValueError("platformio.ini no contiene lib_deps")
    for raw in block.group("body").splitlines():
        dependency = raw.strip()
        if git := GIT_RE.fullmatch(dependency):
            owner, repo, version = git.group("owner", "repo", "version")
            purl = f"pkg:github/{owner}/{repo}@{version}"
            components.append(_component(repo, version, purl))
        elif registry := REGISTRY_RE.fullmatch(dependency):
            owner, name, version = registry.group("owner", "name", "version")
            purl = f"pkg:platformio/{quote(owner)}/{quote(name)}@{quote(version)}"
            components.append(_component(name, version, purl))
        else:
            raise ValueError(f"dependencia firmware sin pin inmutable: {dependency}")
    return components


def generate(root: Path = ROOT) -> dict[str, Any]:
    python_components, python_dependencies = _python_inventory(
        root / "bridge" / "uv.lock"
    )
    firmware_components = _firmware_inventory(root / "platformio.ini")
    components = sorted(
        [*python_components, *firmware_components],
        key=lambda item: str(item["bom-ref"]),
    )
    root_ref = f"pkg:github/SaintWyss/{PRODUCT_NAME}@{PRODUCT_VERSION}"
    serial_seed = "\n".join(str(item["bom-ref"]) for item in components)
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"{root_ref}\n{serial_seed}")
    dependencies = [
        {"ref": root_ref, "dependsOn": [str(item["bom-ref"]) for item in components]},
        *python_dependencies,
        *(
            {"ref": str(item["bom-ref"]), "dependsOn": []}
            for item in firmware_components
        ),
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": _component(
                PRODUCT_NAME, PRODUCT_VERSION, root_ref, kind="application"
            )
        },
        "components": components,
        "dependencies": sorted(dependencies, key=lambda item: str(item["ref"])),
    }


def _encoded(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    try:
        encoded = _encoded(generate(args.root.resolve()))
    except (OSError, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"sbom: {error}", file=sys.stderr)
        return 1
    if args.check is not None:
        if (
            not args.check.is_file()
            or args.check.read_text(encoding="utf-8") != encoded
        ):
            print("sbom: el artefacto no coincide con los locks", file=sys.stderr)
            return 1
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    elif args.check is None:
        print(encoded, end="")
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    print(
        f"sbom: components={len(json.loads(encoded)['components'])} sha256={digest}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
