import http.cookiejar, importlib.util, json, os, pathlib, re, sys, time, urllib.error, urllib.request
WORK=pathlib.Path(os.environ['SUBBURN_TEST_WORK'])
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_browser_dispatch_wip09',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root();app=mod.SubBurnApp(root)
jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def pump(sec=.18):
    end=time.time()+sec
    while time.time()<end: root.update();time.sleep(.01)

def req(path,method='POST',payload=None):
    data=None;headers={'Accept':'application/json'}
    if payload is not None:
        data=json.dumps(payload).encode();headers['Content-Type']='application/json'
    r=urllib.request.Request(f'http://127.0.0.1:{app.dashboard_port}{path}',data=data,method=method,headers=headers)
    try:
        with opener.open(r,timeout=5) as resp:
            body=resp.read().decode()
            try: parsed=json.loads(body)
            except Exception: parsed=body
            return resp.status,parsed
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read().decode())

calls=[]
def rec(name,ret=None):
    def fn(*a,**k):calls.append(name);return ret
    return fn
method_map={
'discover_tools':'discover_tools_async','download_runtime':'download_ffmpeg_async','analyze':'analyze_async','validate':'validate_async',
'probe':'probe_encoders_async','benchmark':'benchmark_async','preview':'preview_async','compare':'compare_preview_async','encode':'start_encode',
'pause':'pause_encode','resume':'resume_encode','cancel':'cancel_encode','refresh_fonts':'scan_fonts_async','diagnostics':'export_diagnostics',
'open_file':'open_last_output','open_folder':'open_last_folder','restore_recovery':'restore_recovery','browser_only':'enter_browser_only',
'show_window':'show_desktop_window','exit_app':'request_exit','transcription_prepare':'prepare_transcription_model_async',
'transcription_start':'start_transcription_async','transcription_cancel':'cancel_transcription'}
try:
    pump(.3);assert app.dashboard_port
    # Establish authenticated dashboard session.
    st,_=req('/',method='GET');assert st==200
    # Every generic browser action exposed by the source must dispatch to its shared application method.
    html=mod.DASHBOARD_HTML
    generic=set(re.findall(r"sendAction\('([^']+)'\)",html))
    assert generic <= set(method_map), sorted(generic-set(method_map))
    for action in sorted(generic):
        name=method_map[action];setattr(app,name,rec(name,False if name=='cancel_transcription' else None))
        st,data=req('/api/action/'+action);assert st==202 and data['ok'],(action,st,data);pump()
    for action in generic:
        assert method_map[action] in calls,(action,calls)

    # Queue buttons dispatch through the shared queue engine.
    qmap={'add_current':'batch_add_current','start':'batch_start_queue','pause':'batch_pause_queue','cancel_current':'batch_cancel_current','retry_all':'batch_retry_all_failed','clear_completed':'batch_clear_completed'}
    for action,name in qmap.items():setattr(app,name,rec(name))
    for action in qmap:
        st,data=req('/api/queue/'+action);assert st==202 and data['ok'];pump()
    assert all(name in calls for name in qmap.values())

    # Live-frame / live-clip browser controls dispatch after normal media guard checks.
    app.media=type('M',(),{'duration':3.0,'fps':25.0})()
    app.live_frame_async=rec('live_frame_async');app.live_clip_async=rec('live_clip_async')
    st,data=req('/api/action/live_frame',payload={'timestamp':.5});assert st==202 and data['ok'];pump()
    st,data=req('/api/action/live_clip',payload={'timestamp':.5});assert st==202 and data['ok'];pump()
    assert 'live_frame_async' in calls and 'live_clip_async' in calls

    # Interval preview and font import controls dispatch through their event boundaries.
    app.watermark_enabled_var.set(True);app.watermark_timing_var.set('Intervals');app.watermark_rows=[(.1,1.0,'Top right')]
    app.preview_interval_async=rec('preview_interval_async')
    st,data=req('/api/action/preview_interval',payload={'index':0});assert st==202 and data['ok'];pump();assert 'preview_interval_async' in calls
    dummy=WORK/'dummy-font.ttf';dummy.write_bytes(b'dummy')
    app.import_font_path=rec('import_font_path')
    st,data=req('/api/font/import',payload={'path':str(dummy)});assert st==202 and data['ok'];pump();assert 'import_font_path' in calls

    # Recent restore control reaches the shared recovery path.
    app.recents={'projects':[{'label':'x','video':'','saved_at':0,'state':{'schema':4,'project':{},'watermark':{},'encoding':{},'subtitles':{}}}],'folders':[]}
    app.apply_recent_project_restore=rec('recent_restore',True)
    st,data=req('/api/recent/restore',payload={'index':0});assert st==202 and data['ok'];pump();assert 'recent_restore' in calls
    print('BROWSER ACTION DISPATCH WIP09 PASS',len(calls),'dispatches')
finally:
    try:app.dashboard_server.shutdown();app.dashboard_server.server_close()
    except Exception:pass
    try:app.system_usage_sampler.stop_event.set()
    except Exception:pass
    try:root.destroy()
    except Exception:pass
