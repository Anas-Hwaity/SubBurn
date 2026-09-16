from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('release_manifest', ROOT / 'scripts/release_manifest.py')
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)

with tempfile.TemporaryDirectory() as td:
    dist = Path(td)
    (dist / 'b.whl').write_bytes(b'bbb')
    (dist / 'a.tar.gz').write_bytes(b'aaa')
    (dist / 'subburn.cdx.json').write_text('{\"bomFormat\":\"CycloneDX\"}\n', encoding='utf-8')
    (dist / 'runtime-provenance.json').write_text('{"schema":1}\n', encoding='utf-8')
    (dist / 'notes.json').write_text('{}\n', encoding='utf-8')
    (dist / '.gitignore').write_text('*\n', encoding='utf-8')
    manifest = MOD.build_manifest(dist)
    assert [x['name'] for x in manifest['artifacts']] == ['a.tar.gz', 'b.whl', 'runtime-provenance.json', 'subburn.cdx.json']
    assert manifest['artifacts'][0]['sha256'] == hashlib.sha256(b'aaa').hexdigest()

with tempfile.TemporaryDirectory() as td:
    dist = Path(td)
    try:
        MOD.build_manifest(dist)
    except SystemExit:
        pass
    else:
        raise AssertionError('empty dist must fail')

print('release manifest contract: PASS')
