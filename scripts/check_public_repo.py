#!/usr/bin/env python3
"""Fail closed on missing public-repository governance/security contracts."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED = [
    "README.md", "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "SECURITY.md",
    "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md", "pyproject.toml",
    ".github/dependabot.yml", ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml", ".github/workflows/ci.yml",
    ".github/workflows/dependency-review.yml", ".github/workflows/release-candidate.yml",
    "docs/github-security-settings.md", "docs/release-process.md", "docs/sbom.md", "docs/compatibility.md",
    "docs/distribution.md", "packaging/windows/README.md", "packaging/windows/SubBurn.iss.in",
    "scripts/check_dependency_lock.py", "scripts/check_source_secrets.py", "scripts/check_writing_style.py",
    "scripts/check_distribution_contract.py", "scripts/runtime_provenance_inventory.py",
    "scripts/render_windows_installer.py", "scripts/run_browser_e2e.py",
    "tests/test_dependency_lock_contract.py", "tests/test_source_secret_scan.py", "tests/test_writing_style_contract.py",
    "tests/test_distribution_contract.py", "tests/test_runtime_provenance_inventory.py",
    "tests/test_release_workflow_contract.py", "tests/test_windows_installer_renderer.py",
    "tests/test_transcription_model_cancel.py", "tests/playwright_support.py",
]

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
PINNED_RE = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def check(root: Path, publication: bool = False) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            fail(f"missing required file: {rel}", errors)

    for wf in sorted((root / ".github/workflows").glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        for use in USES_RE.findall(text):
            if use.startswith("./"):
                continue
            if not PINNED_RE.fullmatch(use):
                fail(f"unpinned action in {wf.relative_to(root)}: {use}", errors)
        if re.search(r"(?m)^\s*permissions:\s*write-all\s*$", text):
            fail(f"write-all token permission forbidden: {wf.relative_to(root)}", errors)

    dep = (root / ".github/dependabot.yml")
    if dep.is_file():
        text = dep.read_text(encoding="utf-8")
        for ecosystem in ("pip", "github-actions"):
            if f"package-ecosystem: {ecosystem}" not in text:
                fail(f"Dependabot missing ecosystem: {ecosystem}", errors)

    sec = root / "SECURITY.md"
    if sec.is_file() and "private vulnerability reporting" not in sec.read_text(encoding="utf-8").lower():
        fail("SECURITY.md does not direct reporters to private vulnerability reporting", errors)

    config = root / ".github/ISSUE_TEMPLATE/config.yml"
    if publication and config.is_file() and "OWNER/REPOSITORY" in config.read_text(encoding="utf-8"):
        fail("publication placeholder OWNER/REPOSITORY still present", errors)

    forbidden_names = {".env", "id_rsa", "id_ed25519", "cookies.txt"}
    for p in root.rglob("*"):
        if p.is_file() and (p.name in forbidden_names or p.suffix.lower() in {".pem", ".p12", ".pfx", ".key"}):
            fail(f"forbidden sensitive-looking file: {p.relative_to(root)}", errors)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--publication", action="store_true")
    args = ap.parse_args()
    errors = check(args.root.resolve(), publication=args.publication)
    if errors:
        print("public-repo check: FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print("public-repo check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
