from __future__ import annotations
import importlib.util, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('render_windows_installer', ROOT/'scripts/render_windows_installer.py')
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
text=mod.render('2.8.0', r'C:\build\SubBurn')
assert '@SUBBURN_' not in text
assert '#define AppVersion "2.8.0"' in text
assert r'#define AppSourceDir "C:\build\SubBurn"' in text
assert 'AppName=SubBurn' in text and 'PrivilegesRequired=lowest' in text
for bad in ('2.8', 'v2.8.0', '2.8.0\nInjected'):
    try: mod.render(bad, r'C:\build\SubBurn')
    except ValueError: pass
    else: raise AssertionError(f'invalid version accepted: {bad!r}')
try: mod.render('2.8.0', 'C:\\bad"path')
except ValueError: pass
else: raise AssertionError('quoted app path accepted')
print('WINDOWS INSTALLER RENDERER PASS')
