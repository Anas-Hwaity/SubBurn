from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_public_repo", ROOT / "scripts/check_public_repo.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)

assert MOD.check(ROOT) == []

with tempfile.TemporaryDirectory() as td:
    copy = Path(td) / "repo"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "build", "dist"))
    (copy / "SECURITY.md").unlink()
    errors = MOD.check(copy)
    assert any("SECURITY.md" in e for e in errors), errors

with tempfile.TemporaryDirectory() as td:
    copy = Path(td) / "repo"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "build", "dist"))
    wf = copy / ".github/workflows/ci.yml"
    wf.write_text(wf.read_text(encoding="utf-8").replace("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "actions/checkout@main", 1), encoding="utf-8")
    errors = MOD.check(copy)
    assert any("unpinned action" in e for e in errors), errors

errors = MOD.check(ROOT, publication=True)
assert errors == [], errors

print("public repository contract: PASS")
