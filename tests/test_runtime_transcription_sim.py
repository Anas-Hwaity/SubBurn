import importlib.util, os, pathlib, sys, time
from types import SimpleNamespace
WORK=pathlib.Path(os.environ['SUBBURN_TEST_WORK'])
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_runtime_transcription',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root(); app=mod.SubBurnApp(root)

def pump(sec=.1):
    end=time.time()+sec
    while time.time()<end:
        root.update(); time.sleep(.01)

def wait_thread(t,timeout=20):
    end=time.time()+timeout
    vals=[]
    while t and t.is_alive() and time.time()<end:
        root.update(); s=app.op_state.operation_snapshot(getattr(t,'subburn_operation_id','')); vals.append(float(s['overall_pct']) if s else -1); time.sleep(.01)
    assert t and not t.is_alive(), 'thread timeout'; pump(.2)
    s=app.op_state.operation_snapshot(t.subburn_operation_id); assert s and s['state']=='succeeded' and s['overall_pct']==100, s
    good=[v for v in vals if v>=0]; assert good==sorted(good)
    return s

def wait(pred,timeout=15):
    end=time.time()+timeout
    while time.time()<end:
        root.update(); time.sleep(.01)
        if pred(): return True
    return False

try:
    assert wait(lambda: app.toolset is not None and bool(getattr(app,'fonts',None)))
    # Actual rediscovery button path.
    t=app.discover_tools_async(); wait_thread(t,20)
    # Actual font refresh button path.
    t=app.scan_fonts_async(); wait_thread(t,20); assert app.font_map
    # Simulated runtime download: exercises progress/callback/UI application without network.
    current=app.toolset
    orig_dl=mod.download_private_ffmpeg
    def fake_download(cb):
        for a in (10,40,70,100): cb(a,100)
        return current
    mod.download_private_ffmpeg=fake_download
    try:
        t=app.download_ffmpeg_async(); wait_thread(t,10); assert app.toolset and str(app.toolset.ffmpeg)==str(current.ffmpeg)
    finally: mod.download_private_ffmpeg=orig_dl

    # Simulated local model preparation, no network/model download.
    app.video_var.set(str(WORK/'input.mp4')); app.transcription_model_var.set('tiny'); app.transcription_language_mode_var.set('Fixed language code'); app.transcription_language_code_var.set('en'); app.transcription_device_var.set('CPU')
    class FakeModel: pass
    class FakePipeline:
        def __init__(self,model): self.model=model
        def transcribe(self,*args,**kwargs):
            words=[SimpleNamespace(start=.1,end=.4,word=' Hello',probability=.99),SimpleNamespace(start=.45,end=.8,word=' world',probability=.98)]
            seg=[SimpleNamespace(start=.1,end=.9,text='Hello world',words=words,avg_logprob=-.1)]
            return seg, SimpleNamespace(duration=3.0,language='en',language_probability=.99,all_language_probs=None)
    orig_load=app.load_transcription_model; orig_ready=mod.transcription_model_ready
    app.load_transcription_model=lambda request,allow_install=True,allow_download=False,download_progress=None,cancel_event=None,phase=None:(FakeModel(),FakePipeline,'cpu','float32')
    mod.transcription_model_ready=lambda model: True
    try:
        # prepare button path
        assert wait(lambda: app.active_job_count()==0,10)
        t=app.prepare_transcription_model_async(); wait_thread(t,10)
        # transcribe button path
        t=app.start_transcription_async(); wait_thread(t,10)
        assert app.latest_transcription_srt and pathlib.Path(app.latest_transcription_srt).is_file()
        assert app.latest_transcription_words and pathlib.Path(app.latest_transcription_words).is_file()
        assert 'Hello world' in pathlib.Path(app.latest_transcription_srt).read_text(encoding='utf-8')
        assert app.subtitle_source_var.get()=='External' and app.subtitle_file_var.get()==str(app.latest_transcription_srt)
    finally:
        app.load_transcription_model=orig_load; mod.transcription_model_ready=orig_ready
    assert app.cancel_transcription() is False
    print('RUNTIME/TRANSCRIPTION CONTROLLED-SIM PASS')
finally:
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
