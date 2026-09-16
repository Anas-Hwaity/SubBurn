import importlib.util, json, os, pathlib, sys, time
WORK=pathlib.Path(os.environ['SUBBURN_TEST_WORK'])
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_preset_recovery',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root(); app=mod.SubBurnApp(root)

def pump(sec=.1):
    end=time.time()+sec
    while time.time()<end:
        root.update(); time.sleep(.01)

def wait(pred,timeout=15):
    end=time.time()+timeout
    while time.time()<end:
        root.update(); time.sleep(.01)
        if pred(): return True
    return False
try:
    assert wait(lambda: app.toolset is not None and bool(getattr(app,'fonts',None)))
    font=next(iter(app.font_map))
    app.video_var.set(str(WORK/'input.mp4')); app.subtitle_source_var.set('External'); app.subtitle_file_var.set(str(WORK/'input.srt')); app.output_dir_var.set(str(WORK/'out')); app.output_name_var.set('recovery-name')
    app.primary_font_var.set(font); app.font_size_var.set('47'); app.text_rgb_var.set('11AAEE'); app.watermark_enabled_var.set(True); app.watermark_type_var.set('Text'); app.watermark_text_var.set('PRESET'); app.watermark_position_var.set('Top left'); app.codec_var.set('H.264'); app.audio_mode_var.set('AAC 192k')
    panels=app.capture_preset_panels(['subtitles','watermark','encoding']); clean=app.validate_preset_panels(panels); assert set(clean)=={'subtitles','watermark','encoding'}
    preset=mod.Preset(id='test-preset',name='Test Preset',builtin=False,panels=panels)
    app.font_size_var.set('22'); app.text_rgb_var.set('FFFFFF'); app.watermark_enabled_var.set(False); app.codec_var.set('VP9')
    assert app.apply_preset_object(preset) is True; pump(.1)
    assert app.font_size_var.get()=='47' and app.text_rgb_var.get().upper()=='11AAEE' and app.watermark_enabled_var.get() and app.codec_var.get()=='H.264'
    app.user_presets=[preset]; app.save_user_presets(); loaded=app.load_user_presets(); assert len(loaded)==1 and loaded[0].name=='Test Preset'
    # Recovery roundtrip.
    payload=app.recovery_payload(); assert payload['schema']==4 and payload['project']['output_name']=='recovery-name'
    app.output_name_var.set('changed'); app.font_size_var.set('19'); app.watermark_enabled_var.set(False); app.audio_mode_var.set('No audio')
    assert app.restore_recovery(payload) is True; pump(.15)
    assert app.output_name_var.get()=='recovery-name'; assert app.font_size_var.get()=='47'; assert app.watermark_enabled_var.get(); assert app.audio_mode_var.get()=='AAC 192k'
    # Autosave is valid JSON and can be read back.
    app.autosave_project(); raw=json.loads(mod.RECOVERY_FILE.read_text(encoding='utf-8')); assert raw['schema']==4; assert app.read_recovery_payload()['project']['output_name']=='recovery-name'
    # Corrupt preset store is rejected and preserved as invalid backup.
    mod.PRESETS_FILE.write_text('{not json',encoding='utf-8'); assert app.load_user_presets()==[]; assert list(mod.PRESETS_FILE.parent.glob(mod.PRESETS_FILE.stem+'.invalid-*'+mod.PRESETS_FILE.suffix))
    print('PRESET/RECOVERY SMOKE PASS')
finally:
    try: app.dashboard_server.shutdown()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
