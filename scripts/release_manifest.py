#!/usr/bin/env python3
"""Create SHA256SUMS and a machine-readable manifest for release artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


RELEASE_SUFFIXES = (".whl", ".tar.gz", ".cdx.json", ".zip", ".exe", ".msi", ".msix", ".dmg", ".pkg", ".appimage")
RELEASE_EXACT_NAMES = {"runtime-provenance.json"}

def is_release_artifact(path: Path) -> bool:
    name = path.name.lower()
    return path.is_file() and (name in RELEASE_EXACT_NAMES or any(name.endswith(suffix) for suffix in RELEASE_SUFFIXES))

def build_manifest(dist: Path) -> dict:
    files = []
    for path in sorted(p for p in dist.iterdir() if is_release_artifact(p)):
        files.append({"name": path.name, "size": path.stat().st_size, "sha256": sha256(path)})
    if not files:
        raise SystemExit("No release artifacts found")
    return {
        "schema": 1,
        "project": "SubBurn",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH", ""),
        "artifacts": files,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()
    if not dist.is_dir():
        raise SystemExit(f"Distribution directory does not exist: {dist}")
    manifest = build_manifest(dist)
    (dist / "release-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [f"{row['sha256']}  {row['name']}" for row in manifest["artifacts"]]
    (dist / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"release manifest: {len(lines)} artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
