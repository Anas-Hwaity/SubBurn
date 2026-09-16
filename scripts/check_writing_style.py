#!/usr/bin/env python3
"""Catch writing patterns that SubBurn intentionally avoids in authored text."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.md', '.py', '.toml', '.yml', '.yaml', '.txt', '.json', '.ini', '.cfg'}
SKIP_NAMES = {'LICENSE', 'check_writing_style.py'}
SKIP_DIRS = {'.git', 'dist', 'build', '__pycache__', '.venv', 'venv'}

PATTERNS = {
    'em dash': re.compile('—'),
    'generic transition "additionally"': re.compile(r'\badditionally\b', re.I),
    'inflated adjective "crucial"': re.compile(r'\bcrucial\b', re.I),
    'inflated adjective "pivotal"': re.compile(r'\bpivotal\b', re.I),
    'AI-style verb "underscore"': re.compile(r'\bunderscor(?:e|es|ed|ing)\b', re.I),
    'AI-style verb "foster"': re.compile(r'\bfoster(?:s|ed|ing)?\b', re.I),
    'AI-style verb "delve"': re.compile(r'\bdelv(?:e|es|ed|ing)\b', re.I),
    'promotional verb "showcase"': re.compile(r'\bshowcas(?:e|es|ed|ing)\b', re.I),
    'generic noun "landscape"': re.compile(r'\blandscape\b', re.I),
    'generic noun "tapestry"': re.compile(r'\btapestry\b', re.I),
    'promotional adjective "vibrant"': re.compile(r'\bvibrant\b', re.I),
    'promotional adjective "groundbreaking"': re.compile(r'\bgroundbreaking\b', re.I),
    'promotional adjective "renowned"': re.compile(r'\brenowned\b', re.I),
    'promotional adjective "transformative"': re.compile(r'\btransformative\b', re.I),
    'promotional phrase "cutting-edge"': re.compile(r'\bcutting[- ]edge\b', re.I),
    'promotional phrase "state-of-the-art"': re.compile(r'\bstate[- ]of[- ]the[- ]art\b', re.I),
    'generic phrase "commitment to"': re.compile(r'\bcommitment to\b', re.I),
    'ornamental phrase "serves as"': re.compile(r'\bserves as\b', re.I),
    'ornamental phrase "stands as"': re.compile(r'\bstands as\b', re.I),
    'formulaic contrast': re.compile(r'\bnot (?:just|merely|only)\b.{0,120}\bbut\b', re.I),
    'chatbot phrase': re.compile(r'\b(?:certainly!|i hope this helps|would you like me to|here(?:’|\')s a (?:breakdown|summary))\b', re.I),
}


def iter_authored_files():
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.name in SKIP_NAMES or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def main() -> int:
    errors: list[str] = []
    for path in iter_authored_files():
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT)
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count('\n', 0, match.start()) + 1
                excerpt = match.group(0).replace('\n', ' ')[:100]
                errors.append(f'{rel}:{line}: {label}: {excerpt!r}')
    if errors:
        print('writing-style check: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1
    print('writing-style check: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
