import importlib.util, shutil, os, pathlib, sys, time, json, subprocess
WORK=pathlib.Path(os.environ['SUBBURN_TEST_WORK'])
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_batch_e2e',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root(); app=mod.SubBurnApp(root)

def pump(sec=.1):
    end=time.time()+sec
    while time.time()<end:
        root.update(); time.sleep(.01)

def wait(pred,timeout=20):
    end=time.time()+timeout
    while time.time()<end:
        root.update(); time.sleep(.01)
        if pred(): return True
    return False

try:
    assert wait(lambda: app.toolset is not None and bool(getattr(app,'fonts',None)),15)
    font=next((x for x in app.font_map if 'DejaVu Sans' in x),next(iter(app.font_map)))
    app.video_var.set(str(WORK/'input.mp4')); app.subtitle_source_var.set('External'); app.subtitle_file_var.set(str(WORK/'input.srt'))
    app.output_dir_var.set(str(WORK/'out')); app.output_name_var.set('batch-e2e'); app.output_ext_var.set('.mp4'); app.clean_output_var.set(False)
    app.primary_font_var.set(font); app.codec_var.set('H.264'); app.quality_mode_var.set('Preserve visual quality'); app.encoder_policy_var.set('Best CPU quality'); app.audio_mode_var.set('AAC 192k')
    t=app.analyze_async(); assert t
    assert wait(lambda:not t.is_alive(),20); pump(.15); assert app.media is not None
    # Ensure isolated queue starts empty.
    for item in app.batch_store.list_items():
        app.batch_store.delete(item.id)
    app.refresh_batch_tree()
    assert app.batch_add_current() is True
    items=app.batch_store.list_items(); assert len(items)==1 and items[0].state=='queued'
    assert app.batch_start_queue() is True
    assert wait(lambda:not app.batch_is_running(),60),'batch runner timeout'
    pump(.3)
    items=app.batch_store.list_items(); assert len(items)==1, items
    item=items[0]; assert item.state=='done', item.to_dict()
    out=pathlib.Path(item.output_path); assert out.is_file() and out.stat().st_size>0
    snap=app.op_state.operation_snapshot(app.batch_operation_id); assert snap and snap['state']=='succeeded' and snap['overall_pct']==100, snap
    data=json.loads(subprocess.check_output([shutil.which('ffprobe') or 'ffprobe','-v','error','-show_entries','stream=codec_type','-of','json',str(out)],text=True))
    types=[s.get('codec_type') for s in data.get('streams',[])]; assert 'video' in types and 'subtitle' not in types
    # Retry/clear management contracts on terminal state.
    cleared=app.batch_store.clear_completed(); assert cleared==1
    assert app.batch_store.list_items()==[]
    print('BATCH E2E PASS')
finally:
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
