from __future__ import annotations
import importlib.util, inspect, pathlib, sys
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_output_attribution',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
assert mod.OUTPUT_MARKER_KEY=='comment'
assert mod.OUTPUT_MARKER_VALUE=='Created by SubBurn.'
assert mod.SubBurnApp.output_attribution_args()==['-metadata','comment=Created by SubBurn.']
source=SRC.read_text('utf-8')
# User-facing and temporary video-producing paths must all route through the same attribution helper.
assert source.count('output_attribution_args()') >= 4, source.count('output_attribution_args()')
# Output verification must enforce the marker on final exports.
assert 'SubBurn output marker is missing or incorrect' in source
print('OUTPUT ATTRIBUTION CONTRACT PASS')
