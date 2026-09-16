import importlib.util, os, pathlib, sys, tempfile
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
TEXT=SRC.read_text(encoding='utf-8')
before=tempfile.tempdir
spec=importlib.util.spec_from_file_location('subburn_storage_hygiene',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
assert tempfile.tempdir is before, (before,tempfile.tempdir)
assert mod.CONFIG_DIR != mod.CACHE_DIR != mod.STATE_DIR
assert mod.DATA_DIR != mod.CACHE_DIR and mod.DATA_DIR != mod.CONFIG_DIR
assert mod.SETTINGS_FILE.parent == mod.CONFIG_DIR
assert mod.PRESETS_FILE.parent == mod.CONFIG_DIR
assert mod.RECOVERY_FILE.parent == mod.STATE_DIR
assert mod.RECENTS_FILE.parent == mod.STATE_DIR
assert mod.QUEUE_DB.parent == mod.STATE_DIR
assert mod.ENCODER_CACHE_FILE.parent == mod.CACHE_DIR
assert mod.PREVIEW_DIR.parent == mod.CACHE_DIR
assert mod.RUNTIME_DIR.parent == mod.DATA_DIR
assert mod.FONT_DIR.parent == mod.DATA_DIR
assert mod.TRANSCRIPTION_DIR.parent == mod.DATA_DIR
assert 'tempfile.tempdir =' not in TEXT
assert 'ArabicHardBurner' not in TEXT
assert '"pip", "install"' not in TEXT and "'pip', 'install'" not in TEXT
assert 'pip install' not in TEXT.casefold()
# Unix/XDG behavior is deterministic and honors overrides.
if not mod.IS_WINDOWS and not mod.IS_MACOS:
    old={k:os.environ.get(k) for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME')}
    try:
        root=pathlib.Path(os.environ.get('HOME',str(pathlib.Path.home())))/'xdg-check'
        os.environ['XDG_CONFIG_HOME']=str(root/'cfg')
        os.environ['XDG_DATA_HOME']=str(root/'data')
        os.environ['XDG_CACHE_HOME']=str(root/'cache')
        os.environ['XDG_STATE_HOME']=str(root/'state')
        cfg,data,cache,state=mod._platform_storage_dirs()
        assert cfg == root/'cfg'/'subburn'
        assert data == root/'data'/'subburn'
        assert cache == root/'cache'/'subburn'
        assert state == root/'state'/'subburn'
    finally:
        for k,v in old.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v
print('STORAGE/RUNTIME HYGIENE PASS')
# Same-root file migrations are safe: if source==destination and exists, helper is a no-op.
probe=mod.CONFIG_DIR/'same-root-probe.json';probe.write_text('{}',encoding='utf-8')
try:
    assert mod._copy_if_missing(probe,probe) is False
finally:
    probe.unlink(missing_ok=True)
