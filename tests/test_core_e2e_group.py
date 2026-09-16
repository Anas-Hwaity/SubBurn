import importlib.util, shutil, json, os, pathlib, subprocess, sys, time

GROUP=os.environ.get('SUBBURN_E2E_GROUP','A').upper()
WORK=pathlib.Path(os.environ['SUBBURN_TEST_WORK'])
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location(f'subburn_e2e_{GROUP.lower()}',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
opened=[]; mod.open_path=lambda p: opened.append(str(p))
root=mod.create_root(); app=mod.SubBurnApp(root)

def pump(seconds=.1):
    end=time.time()+seconds
    while time.time()<end:
        root.update(); time.sleep(.01)

def wait_until(pred,timeout=20):
    end=time.time()+timeout
    while time.time()<end:
        root.update(); time.sleep(.01)
        if pred(): return True
    return False

def run_thread(name,thread,timeout=35):
    assert thread is not None, f'{name}: no thread'
    op_id=getattr(thread,'subburn_operation_id',None); assert op_id, f'{name}: missing operation id'
    values=[]; states=[]; phases=[]
    start=time.time(); end=start+timeout
    while thread.is_alive() and time.time()<end:
        root.update(); s=app.op_state.operation_snapshot(op_id); assert s
        values.append(float(s['overall_pct'])); states.append(s['state']); phases.append(s['phase']); time.sleep(.01)
    assert not thread.is_alive(), f'{name}: timeout > {timeout}s'
    pump(.15); s=app.op_state.operation_snapshot(op_id); assert s
    values.append(float(s['overall_pct'])); states.append(s['state']); phases.append(s['phase'])
    assert values==sorted(values), f'{name}: nonmonotonic {values}'
    assert all(v<100 for v,st in zip(values,states) if st=='running'), f'{name}: reached 100 while running'
    assert s['state']=='succeeded', f'{name}: terminal={s}'
    assert s['overall_pct']==100, f'{name}: terminal percent {s["overall_pct"]}'
    with app.process_lock:
        leaked=[(p.pid,r,p.poll()) for p,r in app.active_processes.items() if p.poll() is None]
    assert not leaked, f'{name}: leaked processes {leaked}'
    print(f'PASS {name} {time.time()-start:.2f}s phases={list(dict.fromkeys(phases))}',flush=True)
    return s

def assert_subburn_marker(path):
    data=json.loads(subprocess.check_output([shutil.which('ffprobe') or 'ffprobe','-v','error','-show_entries','format_tags','-of','json',str(path)],text=True))
    tags=(data.get('format') or {}).get('tags') or {}
    assert any(str(v)==mod.OUTPUT_MARKER_VALUE for v in tags.values()), (path,tags)

def configure():
    assert wait_until(lambda: app.toolset is not None and bool(getattr(app,'fonts',None)),15),'startup readiness timeout'
    font=next((x for x in app.font_map if 'DejaVu Sans' in x),next(iter(app.font_map)))
    app.video_var.set(str(WORK/'input.mp4')); app.subtitle_source_var.set('External'); app.subtitle_file_var.set(str(WORK/'input.srt'))
    app.output_dir_var.set(str(WORK/'out')); app.output_name_var.set(f'e2e-{GROUP.lower()}'); app.output_ext_var.set('.mp4'); app.clean_output_var.set(False)
    app.primary_font_var.set(font); app.codec_var.set('H.264'); app.quality_mode_var.set('Preserve visual quality'); app.encoder_policy_var.set('Best CPU quality'); app.audio_mode_var.set('AAC 192k')
    run_thread('analyze',app.analyze_async(),20); assert app.media is not None

try:
    configure()
    if GROUP=='A':
        run_thread('validate',app.validate_async(),30)
        app.platform_safe_zone_var.set(next(x for x in mod.SAFE_ZONE_PRESET_NAMES if x!='Off'))
        app.open_platform_safe_zone_viewer(); pump(.1); viewer=getattr(app,'_safe_zone_viewer',None); assert viewer and viewer.winfo_exists(); viewer.destroy(); print('PASS safe_zone_viewer')
        app.watermark_enabled_var.set(True); app.watermark_type_var.set('Text'); app.watermark_text_var.set('SUBBURN TEST'); app.watermark_timing_var.set('Full duration'); app.watermark_position_var.set('Top right')
        app.live_seek_var.set(.7); run_thread('live_frame',app.live_frame_async(),35); assert pathlib.Path(app.latest_live_frame).is_file()
        run_thread('live_clip',app.live_clip_async(open_when_ready=False),40); assert pathlib.Path(app.latest_live_clip).is_file(); assert_subburn_marker(app.latest_live_clip)
    elif GROUP=='B':
        app.watermark_enabled_var.set(True); app.watermark_type_var.set('Text'); app.watermark_text_var.set('SUBBURN TEST'); app.watermark_timing_var.set('Full duration'); app.watermark_position_var.set('Top right')
        run_thread('preview',app.preview_async(),45); assert pathlib.Path(app.last_output).is_file(); assert_subburn_marker(app.last_output)
        run_thread('compare',app.compare_preview_async(),45)
        original=app.candidate_encoders; app.candidate_encoders=lambda:['libx264'] if 'libx264' in set(app.toolset.encoders) else original()[:1]
        try:
            run_thread('probe',app.probe_encoders_async(),20); run_thread('benchmark',app.benchmark_async(),25)
        finally: app.candidate_encoders=original
    elif GROUP=='C':
        app.watermark_enabled_var.set(True); app.watermark_type_var.set('Image'); app.watermark_image_var.set(str(WORK/'wm.png')); app.watermark_timing_var.set('Full duration'); app.watermark_image_scale_var.set('50'); app.watermark_image_x_var.set(''); app.watermark_image_y_var.set('')
        run_thread('validate_image_watermark',app.validate_async(),30)
        app.watermark_timing_var.set('Intervals'); app.watermark_rows=[(.25,1.25,'Top right'),(1.5,2.5,'Bottom left')]; app.refresh_intervals()
        run_thread('preview_intervals',app.preview_async(),45)
        app.watermark_enabled_var.set(False); run_thread('encode',app.start_encode(),60)
        out=pathlib.Path(app.last_output); assert out.is_file()
        data=json.loads(subprocess.check_output([shutil.which('ffprobe') or 'ffprobe','-v','error','-show_entries','stream=codec_type:format_tags','-of','json',str(out)],text=True))
        types=[x.get('codec_type') for x in data.get('streams',[])]; assert 'video' in types and 'audio' in types and 'subtitle' not in types
        tags=(data.get('format') or {}).get('tags') or {}; assert any(str(v)==mod.OUTPUT_MARKER_VALUE for v in tags.values())
        before=set(mod.DIAG_DIR.glob('SubBurn-diagnostics-*.txt')); app.export_diagnostics(); pump(.1); after=set(mod.DIAG_DIR.glob('SubBurn-diagnostics-*.txt')); assert after-before
        print('PASS output_verification_and_diagnostics')
    else: raise SystemExit('Unknown group')
    print(f'CORE E2E GROUP {GROUP} PASS')
finally:
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
