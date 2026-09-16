import importlib.util, json, os, pathlib, sys, time, urllib.request, urllib.error, urllib.parse, http.cookiejar
WORK=pathlib.Path(os.environ['SUBBURN_TEST_WORK'])
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_dashboard_smoke_wip09',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root(); app=mod.SubBurnApp(root)
COOKIE_JAR=http.cookiejar.CookieJar(); OPENER=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))

def pump(sec=.1):
    end=time.time()+sec
    while time.time()<end:
        root.update(); time.sleep(.01)

def request(path,method='GET',payload=None,headers=None):
    url=f'http://127.0.0.1:{app.dashboard_port}{path}'
    data=None; h={'Accept':'application/json'}
    if payload is not None:
        data=json.dumps(payload).encode(); h['Content-Type']='application/json'
    if headers: h.update(headers)
    req=urllib.request.Request(url,data=data,method=method,headers=h)
    try:
        with OPENER.open(req,timeout=5) as r:
            body=r.read(); return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code,e.read(),dict(e.headers)

def j(path,method='GET',payload=None,headers=None):
    status,body,_=request(path,method,payload,headers); return status,json.loads(body.decode())

try:
    pump(.4); assert app.dashboard_port
    status,body,h=request('/'); html=body.decode(); assert status==200
    # WIP07 workflow shell, no old action wall.
    for page in ('Home','Subtitles','Watermark','Transcribe','Preview','Burn','Queue','Settings'):
        assert f'>{page}<' in html, page
    assert 'Start encode' not in html and 'Start preview' not in html
    status,data=j('/api/state'); assert status==200 and data['app']=='SubBurn' and 'overall_pct' in data
    status,data=j('/api/job'); assert status==200 and {'appearance','project','subtitles','watermark','encoding','transcription'} <= set(data); assert data['appearance']['mode'] in {'Dark','Balanced','Light'}; assert len(data['transcription']['language_display_options'])==101 and {'code':'ar','label':'Arabic (ar)'} in data['transcription']['language_display_options']
    status,data=j('/api/queue'); assert status==200 and data['ok'] and isinstance(data['items'],list)

    # Appearance is shared/persisted through the same controller boundary.
    status,data=j('/api/job/appearance','POST',{'mode':'Light'}); assert status==202 and data['ok']; pump(.2)
    assert app.appearance_var.get()=='Light'
    status,data=j('/api/state'); assert status==200 and data['appearance']=='Light'
    status,data=j('/api/job/appearance','POST',{'mode':'Balanced'}); assert status==202 and data['ok']; pump(.2)
    assert app.appearance_var.get()=='Balanced'

    # Project + all browser-editable panels.
    project={'video':str(WORK/'input.mp4'),'subtitle_source':'External','subtitle_file':str(WORK/'input.srt'),'output_dir':str(WORK/'out'),'output_name':'dashboard-wip09','clean_output':False}
    status,data=j('/api/job/project','POST',project); assert status==202 and data['ok']
    status,data=j('/api/job/encoding','POST',{'codec':'H.264','output_ext':'.mp4','quality':'Preserve visual quality','policy':'Best CPU quality','speed':'Balanced','resolution':'Original','fps':'Original','audio':'AAC 192k','encoder':'Auto','mode':'Simple','chapter':True}); assert status==202 and data['ok']
    status,data=j('/api/job/subtitles','POST',{'font_size':'40','outline':'2','margin':'36','safe_area':'0','wrap_chars':'42','max_lines':'2','offset_ms':'0','text_rgb':'FFFFFF','outline_rgb':'000000','force_bold':False,'italic':False,'underline':False,'strikeout':False,'text_opacity':'100','outline_opacity':'100','shadow_depth':'0','shadow_rgb':'000000','shadow_opacity':'0','letter_spacing':'0','rotation_angle':'0','subtitle_alignment':'Bottom center','margin_left':'20','margin_right':'20','background_box':False,'background_rgb':'000000','background_opacity':'60','background_padding':'8','platform_safe_zone':'Off','caption_effect_id':'none','caption_effect_params':{'active_rgb':'FFFF00','allow_estimated_timing':False},'fallback_fonts':[]}); assert status==202 and data['ok']
    status,data=j('/api/job/watermark','POST',{'enabled':False,'timing':'Full duration','type':'Text','text':'','same_font':True,'position':'Top right','size':'32','opacity':'70','margin':'24','outline':'2','image_width':'20','image_scale':'100','image_x':'','image_y':'','intervals':[]}); assert status==202 and data['ok']
    tr={'model':'tiny','language_mode':'Fixed language code','language_code':'en','device':'CPU'}
    status,data=j('/api/job/transcription','POST',tr); assert status==202 and data['ok']
    pump(.4)
    assert pathlib.Path(app.video_var.get()).name=='input.mp4' and app.output_name_var.get()=='dashboard-wip09'
    assert app.transcription_model_var.get()=='tiny' and app.transcription_device_var.get()=='CPU'
    # The picker may browse the now-selected project's location, but not arbitrary roots.
    status,data=j('/api/fs?kind=video&path='+urllib.parse.quote(str(WORK))); assert status==200 and any(e['name']=='input.mp4' for e in data['entries'])

    # Transcription action endpoints dispatch through the normal Tk event boundary.
    calls=[]
    app.prepare_transcription_model_async=lambda: calls.append('prepare')
    app.start_transcription_async=lambda: calls.append('start')
    app.cancel_transcription=lambda: calls.append('cancel') or True
    for action in ('transcription_prepare','transcription_start','transcription_cancel'):
        status,data=j('/api/action/'+action,'POST'); assert status==202 and data['ok']; pump(.12)
    assert calls==['prepare','start','cancel'], calls

    # Queue browser actions dispatch to the shared queue engine; route itself is real.
    qcalls=[]
    app.batch_add_current=lambda: qcalls.append('add_current')
    app.batch_start_queue=lambda: qcalls.append('start')
    app.batch_pause_queue=lambda: qcalls.append('pause')
    app.batch_cancel_current=lambda: qcalls.append('cancel_current')
    app.batch_retry_all_failed=lambda: qcalls.append('retry_all')
    app.batch_clear_completed=lambda: qcalls.append('clear_completed')
    for action in ('add_current','start','pause','cancel_current','retry_all','clear_completed'):
        status,data=j('/api/queue/'+action,'POST'); assert status==202 and data['ok']; pump(.12)
    assert qcalls==['add_current','start','pause','cancel_current','retry_all','clear_completed'], qcalls

    # Unknown/removed endpoints fail closed; cross-origin mutation is blocked.
    status,data=j('/api/action/not-a-real-action','POST',{}); assert status==400 and not data['ok']
    status,data=j('/api/queue/not-real','POST'); assert status==404 and not data['ok']
    status,data=j('/api/v1/compression','GET'); assert status==404
    status,data=j('/api/v1/compression/search','POST',{}); assert status==404
    status,data=j('/api/job/project','POST',project,{'Origin':'https://evil.example'}); assert status==403 and not data['ok']
    status,data=j('/api/job/watermark','POST',{'text':'x'*70000}); assert status==400 and not data['ok']
    print('DASHBOARD WIP09 API SMOKE PASS')
finally:
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
