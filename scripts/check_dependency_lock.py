#!/usr/bin/env python3
"""Fail closed on an incomplete or suspicious SubBurn uv.lock."""
from __future__ import annotations
import argparse, re, tomllib
from pathlib import Path

NAME_RE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)')
EXACT_RE = re.compile(r'==\s*([^,;\s]+)')


def norm(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def req_name(req: str) -> str:
    m = NAME_RE.match(req)
    if not m:
        raise ValueError(f'cannot parse requirement: {req!r}')
    return norm(m.group(1))


def exact_version(req: str) -> str | None:
    m = EXACT_RE.search(req)
    return m.group(1) if m else None


def integrity_present(row: dict) -> bool:
    sdist = row.get('sdist') or {}
    if isinstance(sdist, dict) and str(sdist.get('hash','')).startswith('sha256:'):
        return True
    wheels = row.get('wheels') or []
    return any(isinstance(w, dict) and str(w.get('hash','')).startswith('sha256:') for w in wheels)


def check(root: Path) -> list[str]:
    errors: list[str] = []
    pyproject = root / 'pyproject.toml'; lock = root / 'uv.lock'
    if not lock.is_file():
        return ['uv.lock is missing']
    project = tomllib.loads(pyproject.read_text('utf-8'))['project']
    data = tomllib.loads(lock.read_text('utf-8'))
    expected_reqs = list(project.get('dependencies') or [])
    for rows in (project.get('optional-dependencies') or {}).values():
        expected_reqs.extend(rows or [])
    expected: dict[str, list[str]] = {}
    for req in expected_reqs:
        expected.setdefault(req_name(req), []).append(req)
    packages = data.get('package') or []
    by_name: dict[str, list[dict]] = {}
    for row in packages:
        if isinstance(row, dict) and row.get('name'):
            by_name.setdefault(norm(str(row['name'])), []).append(row)
    root_rows = by_name.get(norm(project['name']), [])
    if not root_rows:
        errors.append('lock does not contain the SubBurn project package')
    elif not any(str(r.get('version','')) == str(project['version']) for r in root_rows):
        errors.append('locked SubBurn project version differs from pyproject.toml')
    lock_python = re.sub(r'\s+','',str(data.get('requires-python','')))
    project_python = re.sub(r'\s+','',str(project.get('requires-python','')))
    if lock_python != project_python:
        errors.append(f'lock requires-python differs: {lock_python!r} != {project_python!r}')
    for name, reqs in sorted(expected.items()):
        rows = by_name.get(name, [])
        if not rows:
            errors.append(f'direct dependency absent from lock: {name}')
            continue
        pins = {v for req in reqs if (v := exact_version(req))}
        for pin in pins:
            if not any(str(r.get('version','')) == pin for r in rows):
                errors.append(f'exact pin mismatch for {name}: expected {pin}')
        for row in rows:
            src = row.get('source') or {}
            if not isinstance(src, dict) or 'registry' not in src:
                errors.append(f'direct dependency uses non-registry source: {name} -> {src!r}')
            elif not integrity_present(row):
                errors.append(f'direct registry dependency lacks SHA-256 artifact integrity: {name}')
    return errors


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('root', type=Path, nargs='?', default=Path(__file__).resolve().parents[1]); args=ap.parse_args()
    errors=check(args.root.resolve())
    if errors:
        print('dependency-lock check: FAIL')
        for e in errors: print('-',e)
        return 1
    print('dependency-lock check: PASS')
    return 0

if __name__=='__main__': raise SystemExit(main())
