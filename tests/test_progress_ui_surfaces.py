from __future__ import annotations
import importlib.util, pathlib, re, sys, time
from playwright.sync_api import sync_playwright
from playwright_support import launch_chromium

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_progress_surfaces',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

# ---------- canonical snapshots ----------
def indeterminate(kind='font_scan', *, terminal=None):
    st=mod.OperationState(); oid=st.begin(kind); st.stage(oid,'Scanning',73,'Scanning files')
    if terminal: st.finish(oid,terminal,error='simulated' if terminal=='failed' else '')
    return st.snapshot()

def transfer_snapshot(done,total,rate=2*1024*1024):
    st=mod.OperationState(); oid=st.begin('runtime_download'); st.stage(oid,'FFmpeg download',0,'Downloading FFmpeg runtime')
    pct=(done*100/total) if total else None; eta=((total-done)/rate) if total and rate and done<total else 0
    st.transfer(oid,pct,done,total,rate,eta,'Downloading FFmpeg runtime')
    return st.snapshot()

def media_snapshot(kind='encode',pct=42.5):
    st=mod.OperationState(); oid=st.begin(kind); st.stage(oid,'Encode' if kind=='encode' else 'Preview',0,'Rendering')
    st.progress(oid,pct,fps='48.0',speed='2.0x',eta='00:12')
    return st.snapshot()

TOTAL=int(106.1*1024*1024)
SNAPS={
    'unknown_running': indeterminate('font_scan'),
    'unknown_failed': indeterminate('media_analysis',terminal='failed'),
    'transfer_zero': transfer_snapshot(0,TOTAL,0),
    'transfer_mid': transfer_snapshot(int(1.3*1024*1024),TOTAL),
    'encode_mid': media_snapshot('encode',42.5),
    'live_clip_mid': media_snapshot('live_clip',50.0),
}

# ---------- Tk surface ----------
# Avoid startup work from racing the synthetic state while still rendering the actual UI.
old_scan=mod.SubBurnApp.scan_fonts_async; old_disc=mod.SubBurnApp.discover_tools_async
mod.SubBurnApp.scan_fonts_async=lambda self: None
mod.SubBurnApp.discover_tools_async=lambda self: None
root=mod.create_root(); app=mod.SubBurnApp(root)
app.publish_dashboard_controls=lambda: None

def pump(n=4):
    for _ in range(n): root.update(); time.sleep(.01)

def set_snap(snapshot):
    # Recreate the operation from the snapshot so tick_dashboard reads the canonical engine.
    st=mod.OperationState(); kind=snapshot.get('operation_type') or 'generic'; oid=st.begin(kind)
    phase=snapshot.get('stage') or 'Starting'; st.stage(oid,phase,snapshot.get('stage_pct',0),snapshot.get('stage_message',''))
    if snapshot.get('metric_profile')=='transfer':
        st.transfer(oid,snapshot.get('transfer_pct'),snapshot.get('bytes_done'),snapshot.get('bytes_total'),
                    0 if snapshot.get('speed')=='-' else 2*1024*1024, None if snapshot.get('eta')=='-' else 12,
                    snapshot.get('stage_message',''))
    elif snapshot.get('progress_mode')=='determinate':
        st.progress(oid,snapshot.get('progress_pct'),fps=snapshot.get('fps','-'),speed=snapshot.get('speed','-'),eta=snapshot.get('eta','-'),explicit=True)
    if snapshot.get('operation_state') in {'failed','cancelled','succeeded'}:
        st.finish(oid,snapshot['operation_state'],error=snapshot.get('error',''))
    app.op_state=st; app.tick_dashboard(); pump(2)
    return st.snapshot()

try:
    s=set_snap(SNAPS['unknown_running'])
    assert app.progress_status_var.get()=='Progress: -', app.progress_status_var.get()
    assert str(app.global_progress_bar.cget('mode'))=='indeterminate'

    s=set_snap(SNAPS['unknown_failed'])
    assert app.progress_status_var.get()=='Progress: -', app.progress_status_var.get()

    s=set_snap(SNAPS['transfer_zero'])
    assert app.progress_status_var.get()=='Download: 0.0%', app.progress_status_var.get()
    assert app.transfer_status_var.get().startswith('Downloaded: 0.0 B / 106.1 MiB'), app.transfer_status_var.get()
    assert 'Transfer speed: -'==app.speed_status_var.get(), app.speed_status_var.get()

    s=set_snap(SNAPS['transfer_mid'])
    assert app.progress_status_var.get().startswith('Download: 1.2%'), app.progress_status_var.get()
    assert '1.3 MiB / 106.1 MiB' in app.transfer_status_var.get(), app.transfer_status_var.get()
    assert app.speed_status_var.get().startswith('Transfer speed: 2.0 MiB/s'), app.speed_status_var.get()

    s=set_snap(SNAPS['encode_mid'])
    assert app.progress_status_var.get()=='Progress: 42.1%' or app.progress_status_var.get()=='Progress: 42.5%', app.progress_status_var.get()
    assert app.fps_status_var.get()=='FPS: 48.0'
    assert app.speed_status_var.get()=='Speed: 2.0x'
finally:
    mod.SubBurnApp.scan_fonts_async=old_scan; mod.SubBurnApp.discover_tools_async=old_disc
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass

# ---------- Browser surface ----------
# Use the exact production renderState() function against the exact shipped DOM, with networking
# removed. This catches presentation drift between Tk and dashboard without localhost access.
html=re.sub(r'<script>.*?</script>', '', mod.DASHBOARD_HTML, flags=re.S|re.I)
full=mod.DASHBOARD_HTML
start=full.index('function renderState(d){'); end=full.index('\nasync function tick(){',start); render_js=full[start:end]
with sync_playwright() as pw:
    browser=launch_chromium(pw,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    ctx=browser.new_context(viewport={'width':1200,'height':800})
    page=ctx.new_page(); page.set_content(html,wait_until='domcontentloaded')
    page.evaluate("""() => {window.currentAppearance='Dark';window.applyAppearance=()=>{};window.syncLiveSeekLabel=()=>{};}""")
    page.evaluate('(code)=>eval(code)', render_js+'; window.__renderState=renderState;')
    def render(s):
        page.evaluate('(s)=>window.__renderState(s)',s)
        return page.evaluate("""() => ({
          pct:document.getElementById('pct').textContent,
          bar:document.getElementById('stagebar').style.width,
          ind:document.getElementById('stagebar').classList.contains('indeterminate'),
          downloaded:document.getElementById('downloaded').textContent,
          speed:document.getElementById('speed').textContent,
          fpsDisplay:getComputedStyle(document.getElementById('metric-fps')).display,
          downloadedDisplay:getComputedStyle(document.getElementById('metric-downloaded')).display,
          progressLabel:document.getElementById('progress-label').textContent
        })""")
    r=render(SNAPS['unknown_running']); assert r['pct']=='-' and r['ind'],r
    r=render(SNAPS['unknown_failed']); assert r['pct']=='-' and not r['ind'] and r['bar']=='0%',r
    r=render(SNAPS['transfer_zero']); assert r['pct']=='0.0%' and r['progressLabel']=='Download' and r['downloaded'].startswith('0.0 B / 106.1 MiB'),r
    r=render(SNAPS['transfer_mid']); assert r['pct'].startswith('1.2%') and '1.3 MiB / 106.1 MiB' in r['downloaded'] and r['speed']=='2.0 MiB/s' and r['fpsDisplay']=='none',r
    r=render(SNAPS['encode_mid']); assert r['pct'] in {'42.1%','42.5%'} and r['downloadedDisplay']=='none' and r['fpsDisplay']!='none',r
    r=render(SNAPS['live_clip_mid']); assert r['pct'] in {'49.5%','50.0%'},r
    ctx.close(); browser.close()

print('TK + BROWSER CANONICAL PROGRESS SURFACE MATRIX PASS')
