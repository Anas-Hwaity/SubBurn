import importlib.util, pathlib, subprocess, sys, time
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_process_controls',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root(); app=mod.SubBurnApp(root)
proc=None
try:
    proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])
    app.register_render_process(proc,'encode'); time.sleep(.1); root.update()
    assert app.current_process is proc and proc.poll() is None
    app.pause_encode(); root.update(); assert app.paused is True and proc.poll() is None
    app.resume_encode(); root.update(); assert app.paused is False and proc.poll() is None
    app.cancel_encode();
    end=time.time()+5
    while proc.poll() is None and time.time()<end: root.update(); time.sleep(.05)
    assert proc.poll() is not None, 'cancel did not terminate process'
    assert app.process_was_cancelled(proc)
    app.unregister_render_process(proc); assert app.current_process is None
    print('PROCESS CONTROL SMOKE PASS')
finally:
    if proc and proc.poll() is None:
        proc.kill(); proc.wait()
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
