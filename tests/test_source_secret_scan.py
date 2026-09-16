from __future__ import annotations
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_source_secrets', ROOT/'scripts/check_source_secrets.py')
mod = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
assert mod.scan(ROOT) == []
with tempfile.TemporaryDirectory() as td:
    p = Path(td)/'leak.txt'
    p.write_text('token=' + 'AK' + 'IA' + 'ABCDEFGHIJKLMNOP' + '\n', encoding='utf-8')
    findings = mod.scan(Path(td))
    assert findings and 'AWS access key' in findings[0]
print('SOURCE SECRET SCAN PASS')
