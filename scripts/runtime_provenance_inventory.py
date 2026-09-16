#!/usr/bin/env python3
"""Emit deterministic provenance for SubBurn's non-Python downloadable components.

The generator parses audited constants from ``src/subburn/app.py`` instead of importing the
application. This keeps release provenance generation independent of installed runtime/optional
Python dependencies. It complements, but does not replace, the locked CycloneDX Python SBOM.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / 'src/subburn/app.py'
REQUIRED_CONSTANTS = {
    'APP_NAME', 'APP_VERSION', 'FFMPEG_URL', 'FFMPEG_SHA256_URL', 'FFMPEG_PROVIDER',
    'FFMPEG_RUNTIME_MANIFEST_NAME', 'TRANSCRIPTION_MODELS', 'TRANSCRIPTION_MODEL_SOURCES',
    'TRANSCRIPTION_MODEL_ALLOW_PATTERNS', 'TRANSCRIPTION_MODEL_ESTIMATED_BYTES',
}


def _safe_eval(node: ast.AST, values: dict[str, object]) -> object:
    try:
        return ast.literal_eval(node)
    except Exception:
        pass
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _safe_eval(node.left, values)
        right = _safe_eval(node.right, values)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
    raise ValueError(f'unsupported non-literal constant expression: {ast.dump(node, include_attributes=False)}')


def load_constants(source: Path = APP_SOURCE) -> dict[str, object]:
    tree = ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        if value_node is None:
            continue
        names = [target.id for target in targets if isinstance(target, ast.Name)]
        wanted = [name for name in names if name in REQUIRED_CONSTANTS]
        if not wanted:
            continue
        value = _safe_eval(value_node, values)
        for name in wanted:
            values[name] = value
    missing = REQUIRED_CONSTANTS - values.keys()
    if missing:
        raise RuntimeError(f'missing provenance constants in app source: {sorted(missing)}')
    return values


def build_inventory(source: Path = APP_SOURCE) -> dict:
    c = load_constants(source)
    model_names = list(c['TRANSCRIPTION_MODELS'])
    sources = dict(c['TRANSCRIPTION_MODEL_SOURCES'])
    estimates = dict(c['TRANSCRIPTION_MODEL_ESTIMATED_BYTES'])
    allow_patterns = list(c['TRANSCRIPTION_MODEL_ALLOW_PATTERNS'])
    if set(model_names) != set(sources) or set(model_names) != set(estimates):
        raise RuntimeError('transcription model provenance registries disagree')
    models = []
    for name in model_names:
        source_info = dict(sources[name])
        revision = str(source_info.get('revision') or '').strip().lower()
        repo = str(source_info.get('repo') or '').strip()
        license_id = str(source_info.get('license') or '').strip()
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise RuntimeError(f'model {name} is not pinned to an immutable 40-hex revision')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise RuntimeError(f'model {name} has invalid repository metadata')
        if not license_id:
            raise RuntimeError(f'model {name} has no recorded license')
        models.append({
            'name': name,
            'repository': repo,
            'revision': revision,
            'license': license_id,
            'upstream': str(source_info.get('upstream') or ''),
            'bundled': False,
            'installation': 'download-on-demand',
            'estimated_download_bytes': int(estimates[name]),
            'allowlisted_files': allow_patterns,
        })
    ffmpeg_url = str(c['FFMPEG_URL'])
    checksum_url = str(c['FFMPEG_SHA256_URL'])
    if not ffmpeg_url.startswith('https://') or checksum_url != ffmpeg_url + '.sha256':
        raise RuntimeError('managed FFmpeg source/checksum provenance contract is invalid')
    return {
        'schema': 1,
        'product': str(c['APP_NAME']),
        'internal_application_version': str(c['APP_VERSION']),
        'python_sbom_relationship': 'complementary-runtime-provenance',
        'ffmpeg': {
            'provider': str(c['FFMPEG_PROVIDER']),
            'source_url': ffmpeg_url,
            'publisher_checksum_url': checksum_url,
            'bundled': False,
            'installation': 'download-on-demand-if-no-compatible-local-pair',
            'required_capability': 'subtitles/libass rendering',
            'verification': 'publisher SHA-256 before extraction',
            'runtime_manifest': str(c['FFMPEG_RUNTIME_MANIFEST_NAME']),
            'redistribution_license_review_required': True,
        },
        'transcription_models': models,
    }


def render_inventory(source: Path = APP_SOURCE) -> bytes:
    return (json.dumps(build_inventory(source), indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def main() -> int:
    ap = argparse.ArgumentParser(description='Emit deterministic SubBurn runtime/model provenance JSON.')
    ap.add_argument('--source', type=Path, default=APP_SOURCE)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    data = render_inventory(args.source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print(f'runtime provenance: wrote {args.output} ({len(data)} bytes)')
    else:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
