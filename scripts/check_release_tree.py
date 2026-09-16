from __future__ import annotations
from pathlib import Path
import hashlib, json, re, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {'.exe','.dll','.so','.dylib','.bin','.onnx','.pt','.pth','.safetensors'}
FORBIDDEN_NAMES = {'ffmpeg.exe','ffprobe.exe','ffmpeg','ffprobe'}


def fail(msg: str) -> None:
    raise SystemExit(f"release-tree check failed: {msg}")


def main() -> None:
    required = ['pyproject.toml','LICENSE','NOTICE','THIRD_PARTY_NOTICES.md','README.md','MANIFEST.in','docs/dependencies.md','docs/release-readiness.md','docs/distribution.md','packaging/windows/README.md','packaging/windows/SubBurn.iss.in','src/subburn/app.py','tests/browser_harness.py','tests/make_fixture.py','scripts/run_linux_smoke.py','scripts/verify_release_artifacts.py','scripts/canonicalize_sdist.py','scripts/check_source_secrets.py','scripts/check_distribution_contract.py','scripts/runtime_provenance_inventory.py','scripts/render_windows_installer.py','scripts/run_browser_e2e.py']
    for rel in required:
        if not (ROOT/rel).is_file(): fail(f'missing {rel}')
    bad=[]
    is_sdist = (ROOT / 'PKG-INFO').is_file()
    for p in ROOT.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT)
        if any(part in {'.venv','dist','build','.git'} for part in rel.parts): continue
        if any(part == '__pycache__' for part in rel.parts) or p.suffix.casefold() in {'.pyc','.pyo'}:
            fail(f'generated Python residue in release tree: {rel}')
        egg_parts = [part for part in rel.parts if part.endswith('.egg-info')]
        if egg_parts:
            expected_sdist_egg = is_sdist and rel.parts[0] == 'src' and egg_parts == ['subburn.egg-info']
            if not expected_sdist_egg:
                fail(f'generated egg-info residue in release tree: {rel}')
        if p.name.casefold() in FORBIDDEN_NAMES or p.suffix.casefold() in FORBIDDEN_SUFFIXES:
            bad.append(str(rel))
    if bad: fail('bundled runtime/model binary found: '+', '.join(bad[:20]))
    text=(ROOT/'src/subburn/app.py').read_text(encoding='utf-8')
    if 'automation_cli(' in text: fail('CLI residue')
    if re.search(r'\bcompression_', text, re.I) or 'Maximum Compression' in text: fail('Max Compression residue')
    print('release-tree check: PASS')

if __name__=='__main__': main()
