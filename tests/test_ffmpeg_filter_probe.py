from __future__ import annotations
import importlib.util, pathlib, shutil, sys
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_filter_probe',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
ff=shutil.which('ffmpeg')
if ff:
    assert mod.ffmpeg_filter_available(ff,'subtitles'), 'real FFmpeg direct subtitles probe failed'
    assert mod.ffmpeg_filter_available(ff,'ass'), 'real FFmpeg direct ass probe failed'
    assert not mod.ffmpeg_filter_available(ff,'subburn_filter_that_does_not_exist')
# Simulate a future -filters table layout that parse_filters does not recognize; direct probe must still add critical filters.
old=mod.run_capture
def fake(cmd,**kwargs):
    text=' '.join(map(str,cmd))
    if '-filters' in text: return 0, 'Filters:\n ABCDE futurefilter V->V test\n'
    if 'filter=subtitles' in text: return 0, 'Filter subtitles\n  Render text subtitles using libass.\n'
    if 'filter=ass' in text: return 0, 'Filter ass\n  Render ASS subtitles.\n'
    return 0, "Unknown filter 'x'.\n"
mod.run_capture=fake
try:
    filters=mod.parse_filters('ffmpeg.exe')
    assert 'subtitles' in filters and 'ass' in filters, filters
finally: mod.run_capture=old
print('FFMPEG CRITICAL FILTER DIRECT-PROBE PASS')
