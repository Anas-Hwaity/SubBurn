from __future__ import annotations
import importlib.util, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_provenance_inventory', ROOT/'scripts/runtime_provenance_inventory.py')
mod = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
source_text=(ROOT/'scripts/runtime_provenance_inventory.py').read_text(encoding='utf-8')
assert 'from subburn' not in source_text and 'import subburn' not in source_text
raw1 = mod.render_inventory(); raw2 = mod.render_inventory()
assert raw1 == raw2
obj = json.loads(raw1)
assert obj['schema'] == 1 and obj['product'] == 'SubBurn'
ff = obj['ffmpeg']
assert ff['source_url'].startswith('https://') and ff['publisher_checksum_url'] == ff['source_url'] + '.sha256'
assert ff['bundled'] is False and 'subtitles' in ff['required_capability']
models = obj['transcription_models']
assert len(models) == 6 and {m['name'] for m in models} == {'large-v3','turbo','medium','small','base','tiny'}
for m in models:
    assert re.fullmatch(r'[0-9a-f]{40}', m['revision'])
    assert m['license'] and m['repository'] and m['estimated_download_bytes'] > 0
    assert m['bundled'] is False and m['installation'] == 'download-on-demand'
print('RUNTIME PROVENANCE INVENTORY PASS')
