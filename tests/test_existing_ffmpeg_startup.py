from __future__ import annotations

import importlib.util
import pathlib
import shutil
import sys
import time

SRC = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec = importlib.util.spec_from_file_location('subburn_existing_ffmpeg_startup', SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

system_ffmpeg = shutil.which('ffmpeg')
if not system_ffmpeg:
    raise SystemExit('SKIP: system FFmpeg is not installed in this acceptance environment')

calls: list[tuple] = []

def forbidden_download(*args, **kwargs):
    calls.append((args, kwargs))
    raise AssertionError('managed FFmpeg download attempted despite a compatible installed FFmpeg')

mod.download_private_ffmpeg = forbidden_download
root = mod.create_root()
app = mod.SubBurnApp(root)
try:
    end = time.time() + 15
    while time.time() < end and app.toolset is None:
        root.update()
        time.sleep(0.02)
    assert app.toolset is not None, 'startup did not resolve the installed FFmpeg'
    assert not calls, calls
    assert pathlib.Path(app.toolset.ffmpeg).resolve() == pathlib.Path(system_ffmpeg).resolve(), (
        app.toolset.ffmpeg,
        system_ffmpeg,
    )
    assert 'FFmpeg' in app.tool_var.get()
    print('STARTUP EXISTING FFMPEG REUSE / ZERO DOWNLOAD PASS')
finally:
    try:
        app.dashboard_server.shutdown()
    except Exception:
        pass
    try:
        app.system_usage_sampler.stop_event.set()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
