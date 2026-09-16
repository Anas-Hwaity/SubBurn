from __future__ import annotations
import importlib.util, pathlib, sys
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_browser_fallback',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
h=mod.DASHBOARD_HTML
assert 'id="subFallbackPicker"' in h
assert '<select id="subFallback" multiple' not in h
assert 'function addFallbackFont()' in h and 'function renderFallbackFonts()' in h
assert 'fallback_fonts:[...subFallbackFonts]' in h
assert 'class="fallback-chips"' in h
print('BROWSER FALLBACK FONT DROPDOWN PASS')
