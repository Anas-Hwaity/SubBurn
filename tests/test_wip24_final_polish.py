import http.cookiejar
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.request

WORK = Path(os.environ['SUBBURN_TEST_WORK'])
SRC = Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec = importlib.util.spec_from_file_location('subburn_wip24_final_polish', SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
mod.open_path = lambda p: None
root = mod.create_root()
app = mod.SubBurnApp(root)


def pump(sec=.15):
    end = time.time() + sec
    while time.time() < end:
        root.update()
        time.sleep(.01)


def clear_queue():
    for item in app.batch_store.list_items():
        if item.state == 'running':
            app.batch_store.set_state(item.id, 'cancelled', finished=True)
        app.batch_store.delete(item.id)
    app.refresh_batch_tree()

try:
    pump(.35)
    assert mod.OWNER_NAME == 'Anas Al Hwaity'
    assert mod.OWNER_TELEGRAM == '@ANAS12RM'
    assert 'SubBurn Help Manual' in mod.HELP_MANUAL_TEXT
    assert 'Queue' in mod.HELP_MANUAL_TEXT and 'Progress' in mod.HELP_MANUAL_TEXT
    assert "img-src 'self' data: blob:" in mod.DASHBOARD_CSP
    assert 'Contact Owner: @ANAS12RM on Telegram' in mod.DASHBOARD_HTML
    assert 'queueAddCustom()' in mod.DASHBOARD_HTML
    assert 'queueRemoveSelected()' in mod.DASHBOARD_HTML
    assert "queueAction('clear_queued')" in mod.DASHBOARD_HTML

    # Browser live-frame bytes must be a real browser-decodable PNG served from the same session.
    from PIL import Image
    png = WORK / 'browser-frame.png'
    Image.new('RGB', (64, 36), (12, 34, 56)).save(png, format='PNG')
    with app.live_frame_lock:
        app.latest_live_frame = png
        app.latest_live_timestamp = 1.0
        app.live_frame_revision = 7
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with opener.open(f'http://127.0.0.1:{app.dashboard_port}/', timeout=5) as r:
        csp = r.headers.get('Content-Security-Policy', '')
        assert "img-src 'self' data: blob:" in csp, csp
    with opener.open(f'http://127.0.0.1:{app.dashboard_port}/api/live/frame?at=1.0&after=0', timeout=5) as r:
        data = r.read()
        assert r.headers.get_content_type() == 'image/png'
        assert data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) > 50

    # Queue can add a different video without changing the currently open project.
    clear_queue()
    current = WORK / 'input.mp4'
    other = WORK / 'other.mp4'
    shutil.copy2(current, other)
    app.video_var.set(str(current))
    app.subtitle_file_var.set(str(WORK / 'input.srt'))
    app.subtitle_source_var.set('External')
    before = app.video_var.get()
    assert app.batch_add_custom(str(other), str(WORK / 'input.srt')) is True
    assert app.video_var.get() == before
    items = app.batch_store.list_items()
    assert len(items) == 1 and Path(items[0].job.video) == other
    # Exact accidental re-add is blocked; explicit Duplicate remains available.
    assert app.batch_add_custom(str(other), str(WORK / 'input.srt')) is False
    assert len(app.batch_store.list_items()) == 1
    assert app.batch_duplicate_id(items[0].id) is True
    assert len(app.batch_store.list_items()) == 2
    assert app.batch_remove_id(items[0].id) is True
    assert len(app.batch_store.list_items()) == 1
    assert app.batch_clear_queued() == 1
    assert app.batch_store.list_items() == []

    # A recent project is queueable without restoring/mutating the active UI project.
    app.video_var.set(str(current))
    state = app.recovery_payload()
    app.recents = {'projects': [{'label': 'Recent project', 'video': str(current), 'saved_at': time.time(), 'state': state}], 'folders': []}
    active_before = app.video_var.get()
    assert app.batch_add_recent_project(0) is True
    assert app.video_var.get() == active_before
    assert len(app.batch_store.list_items()) == 1

    print('WIP24 FINAL POLISH CONTRACT PASS')
finally:
    try:
        app.dashboard_server.shutdown(); app.dashboard_server.server_close()
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
