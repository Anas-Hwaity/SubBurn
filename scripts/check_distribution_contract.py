#!/usr/bin/env python3
"""Validate the committed end-user distribution design without claiming native build acceptance."""
from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED = (
    'docs/distribution.md',
    'packaging/windows/README.md',
    'packaging/windows/SubBurn.iss.in',
    'scripts/render_windows_installer.py',
)


def check(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f'missing distribution file: {rel}')
    if errors:
        return errors
    docs = (root / 'docs/distribution.md').read_text(encoding='utf-8')
    win = (root / 'packaging/windows/README.md').read_text(encoding='utf-8')
    iss = (root / 'packaging/windows/SubBurn.iss.in').read_text(encoding='utf-8')
    pyproject = (root / 'pyproject.toml').read_text(encoding='utf-8')
    required_docs = (
        'PyInstaller', 'one-folder', 'Inno Setup', 'Authenticode',
        'FFmpeg', 'model weights', 'non-admin', 'Windows',
    )
    for token in required_docs:
        if token.casefold() not in docs.casefold():
            errors.append(f'distribution decision missing: {token}')
    for token in ('PrivilegesRequired=lowest', 'AppName=SubBurn', 'AppVerName=SubBurn', 'SubBurn.exe'):
        if token not in iss:
            errors.append(f'installer template missing contract: {token}')
    if '[project.gui-scripts]' not in pyproject or 'subburn = "subburn.app:main"' not in pyproject:
        errors.append('pyproject must expose SubBurn through project.gui-scripts')
    if '[project.scripts]' in pyproject:
        errors.append('console project.scripts launcher is forbidden')
    forbidden = ('ffmpeg.exe', 'ffprobe.exe', '.safetensors', 'model.bin')
    for token in forbidden:
        if token in iss.casefold():
            errors.append(f'installer template must not bundle runtime/model payload: {token}')
    if 'must be signed' not in win.casefold() or 'must not be called stable' not in win.casefold():
        errors.append('Windows packaging README must fail closed on signing/native acceptance')
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    errors = check(args.root)
    if errors:
        print('distribution contract: FAIL')
        for item in errors:
            print(f'- {item}')
        return 1
    print('distribution contract: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
