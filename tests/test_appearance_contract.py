from __future__ import annotations
import importlib.util, pathlib, sys, tempfile, json
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_appearance_contract',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
assert mod.APPEARANCE_MODES==['Dark','Balanced','Light']
for mode in mod.APPEARANCE_MODES:
    p=mod.appearance_palette(mode)
    for key in ('app','surface','surface_alt','entry','border','text','muted','accent','disabled_bg','disabled_text'):
        assert key in p and p[key],(mode,key)
assert mod.normalize_appearance_mode('inbetween')=='Balanced'
html=mod.DASHBOARD_HTML
for token in ('data-theme="balanced"','data-theme="light"','backdrop-filter:blur(32px)','backdrop-filter:blur(28px)','--control-stroke:','select option,select optgroup','id="appearanceMode"','/api/job/appearance','function applyAppearance'):
    assert token in html,token
assert '<title>SubBurn</title>' in html
print('APPEARANCE DARK / BALANCED / LIGHT CONTRACT PASS')
