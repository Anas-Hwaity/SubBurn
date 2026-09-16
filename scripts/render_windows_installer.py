#!/usr/bin/env python3
"""Render the credential-free Inno Setup template for a native Windows packaging run."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'packaging/windows/SubBurn.iss.in'
VERSION_RE = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.+-]*)?$')


def render(version: str, app_dir: str) -> str:
    version = str(version).strip()
    app_dir = str(app_dir).strip()
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f'invalid installer version: {version!r}')
    if not app_dir or any(ch in app_dir for ch in ('\n', '\r', '"')):
        raise ValueError('application directory must be non-empty and contain no quote/newline characters')
    text = TEMPLATE.read_text(encoding='utf-8')
    text = text.replace('@SUBBURN_VERSION@', version).replace('@SUBBURN_APP_DIR@', app_dir.rstrip('\\/'))
    if '@SUBBURN_' in text:
        raise RuntimeError('installer template still contains unresolved SubBurn placeholders')
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', required=True)
    ap.add_argument('--app-dir', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = render(args.version, args.app_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(out, encoding='utf-8', newline='\n')
    print(f'installer template: wrote {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
