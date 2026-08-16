#!/usr/bin/env python3
"""Publish one built-in LEC system module to the official module repository."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_builtin_modules import build_archive

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = REPO_ROOT / "src/linuxeasyconfig/modules"
REPOSITORY_DIR = REPO_ROOT / "module-repository"
PACKAGES_DIR = REPOSITORY_DIR / "packages"
INDEX_PATH = REPOSITORY_DIR / "index.json"
RAW_BASE = (
    "https://raw.githubusercontent.com/"
    "candre23/LinuxEasyConfig/main/module-repository/packages"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a .lec archive for one official system module and update "
            "module-repository/index.json."
        )
    )
    parser.add_argument("module", help="Module package directory name, e.g. reverse_proxy.")
    parser.add_argument(
        "--min-lec-version",
        default="1.0.0",
        help="Oldest LEC Core version compatible with this module (default: 1.0.0).",
    )
    args = parser.parse_args()
    module_dir = MODULES_DIR / args.module
    manifest_path = module_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"No built-in module found at {module_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_id = str(manifest.get("id", "")).strip()
    name = str(manifest.get("name", args.module)).strip()
    version = str(manifest.get("version", "")).strip()
    if not module_id or not version:
        raise SystemExit("The module manifest must contain id and version.")
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    filename = f"{args.module}-{version}.lec"
    output_path = PACKAGES_DIR / filename
    build_archive(module_dir, output_path)
    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    if INDEX_PATH.is_file():
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    else:
        index = {"schema_version": 1, "modules": []}
    if index.get("schema_version") != 1:
        raise SystemExit("Unsupported module repository index schema.")
    modules = index.setdefault("modules", [])
    if not isinstance(modules, list):
        raise SystemExit("module-repository/index.json has an invalid modules value.")
    entry = {
        "id": module_id,
        "name": name,
        "version": version,
        "min_lec_version": args.min_lec_version,
        "url": f"{RAW_BASE}/{filename}",
        "sha256": digest,
    }
    modules[:] = [
        item
        for item in modules
        if not (isinstance(item, dict) and item.get("id") == module_id)
    ]
    modules.append(entry)
    modules.sort(key=lambda item: str(item.get("name", item.get("id", ""))).casefold())
    INDEX_PATH.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Published {name} {version}")
    print(f"Package: {output_path.relative_to(REPO_ROOT)}")
    print(f"SHA-256: {digest}")
    print(f"Index: {INDEX_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
