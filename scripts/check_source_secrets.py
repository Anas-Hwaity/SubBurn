#!/usr/bin/env python3
"""High-confidence source-tree secret scan for public-release gating.

This deliberately avoids broad entropy/password heuristics that create noisy false positives.
It looks for credential formats that should never appear in the public repository, while the
public-repo checker separately rejects sensitive file names/extensions.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

SKIP_DIRS = {'.git', '.venv', 'venv', 'build', 'dist', '__pycache__', '.pytest_cache', '.mypy_cache'}
TEXT_SUFFIXES = {
    '', '.py', '.md', '.txt', '.toml', '.yml', '.yaml', '.json', '.ini', '.cfg', '.conf',
    '.in', '.iss', '.ps1', '.sh', '.bat', '.cmd', '.xml', '.html', '.css', '.js', '.ts',
}
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ('private key material', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ('GitHub classic token', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,255}\b')),
    ('GitHub fine-grained token', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,255}\b')),
    ('OpenAI API key', re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,255}\b')),
    ('Hugging Face token', re.compile(r'\bhf_[A-Za-z0-9]{30,255}\b')),
    ('AWS access key', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('Google API key', re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b')),
    ('Slack token', re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,255}\b')),
)


def candidate_files(root: Path):
    for path in root.rglob('*'):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def scan(root: Path) -> list[str]:
    root = Path(root).resolve()
    findings: list[str] = []
    for path in candidate_files(root):
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(root)
        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                line = text.count('\n', 0, match.start()) + 1
                findings.append(f'{rel}:{line}: {label}')
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description='Scan the SubBurn public source tree for high-confidence secrets.')
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    findings = scan(args.root)
    if findings:
        print('source-secret scan: FAIL')
        for item in findings:
            print(f'- {item}')
        return 1
    print('source-secret scan: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
