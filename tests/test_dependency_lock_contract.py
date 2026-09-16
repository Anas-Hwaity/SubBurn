from __future__ import annotations
import importlib.util, tempfile, textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lockcheck', ROOT/'scripts/check_dependency_lock.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
py=(ROOT/'pyproject.toml').read_text('utf-8')

def row(name, version):
    return f'''\n[[package]]\nname = "{name}"\nversion = "{version}"\nsource = {{ registry = "https://pypi.org/simple" }}\nsdist = {{ url = "https://example.invalid/{name}.tar.gz", hash = "sha256:{'a'*64}", size = 1 }}\n'''

def synthetic():
    return 'version = 1\nrevision = 3\nrequires-python = ">=3.10,<3.14"\n' + row('subburn','2.8.0.dev0').replace('source = { registry = "https://pypi.org/simple" }','source = { editable = "." }') + ''.join([
        row('fonttools','4.63.0'), row('regex','2026.5.9'), row('tkinterdnd2','0.6.3'),
        row('faster-whisper','1.2.1'), row('ctranslate2','4.8.2'), row('huggingface-hub','1.31.0')])

def check(lock_text=None):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'pyproject.toml').write_text(py,'utf-8')
        if lock_text is not None: (r/'uv.lock').write_text(lock_text,'utf-8')
        return m.check(r)

assert 'uv.lock is missing' in check(None)
valid=synthetic(); assert not check(valid), check(valid)
missing=valid.replace(row('ctranslate2','4.8.2'),''); assert any('ctranslate2' in x for x in check(missing))
wrong=valid.replace('version = "1.2.1"','version = "1.2.0"',1); assert any('faster-whisper' in x and 'pin mismatch' in x for x in check(wrong))
mutable=valid.replace('source = { registry = "https://pypi.org/simple" }','source = { git = "https://example.invalid/repo.git" }',1); assert any('non-registry' in x for x in check(mutable))
nohash=valid.replace(f'sdist = {{ url = "https://example.invalid/fonttools.tar.gz", hash = "sha256:{"a"*64}", size = 1 }}\n',''); assert any('fonttools' in x and 'integrity' in x for x in check(nohash))
print('DEPENDENCY LOCK CONTRACT PASS')
