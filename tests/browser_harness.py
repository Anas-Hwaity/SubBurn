import importlib.util,json,os,pathlib,sys,time
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_browser_harness',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root();app=mod.SubBurnApp(root)
portfile=pathlib.Path(os.environ['SUBBURN_PORT_FILE']);callsfile=pathlib.Path(os.environ['SUBBURN_CALLS_FILE'])
calls=[]
def rec(name,ret=None):
    def fn(*a,**k):
        calls.append(name);tmp=callsfile.with_suffix('.tmp');tmp.write_text(json.dumps(calls),encoding='utf-8');os.replace(tmp,callsfile)
        return ret
    return fn
# Controlled UI-action smoke: backend/real-render behavior is exercised by separate E2E suites.
for name in ('discover_tools_async','download_ffmpeg_async','analyze_async','validate_async','probe_encoders_async','benchmark_async','preview_async','compare_preview_async','start_encode','pause_encode','resume_encode','cancel_encode','scan_fonts_async','export_diagnostics','restore_recovery','enter_browser_only','show_desktop_window','request_exit','prepare_transcription_model_async','start_transcription_async'):
    setattr(app,name,rec(name))
app.cancel_transcription=rec('cancel_transcription',False)
for name in ('batch_add_current','batch_start_queue','batch_pause_queue','batch_cancel_current','batch_retry_all_failed','batch_clear_completed'):
    setattr(app,name,rec(name))
app.open_last_output=rec('open_last_output')
app.open_last_folder=rec('open_last_folder')
callsfile.write_text('[]',encoding='utf-8');portfile.write_text(str(app.dashboard_port),encoding='utf-8')
root.mainloop()
