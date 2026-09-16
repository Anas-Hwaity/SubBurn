from __future__ import annotations
import importlib.util, os, pathlib, sys, tempfile, shutil, types
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_windows_path_promotion',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
root=pathlib.Path(tempfile.mkdtemp(prefix='subburn-win-path-'))
old_is_windows=mod.IS_WINDOWS;old_path=os.environ.get('PATH','');old_broadcast=mod._broadcast_windows_environment_change
try:
    bindir=root/'managed'/'bin';bindir.mkdir(parents=True)
    ff=bindir/'ffmpeg.exe';fp=bindir/'ffprobe.exe';ff.write_bytes(b'x');fp.write_bytes(b'y')
    caps=mod.Toolset(ffmpeg=ff,ffprobe=fp,version='test',filters={'subtitles','ass'},encoders=[],score=1)
    os.environ['PATH']=os.pathsep.join([str(root/'old'),str(root/'other')])
    state={'path':str(root/'legacy')+';'+str(root/'other')}
    fake=types.SimpleNamespace()
    fake.HKEY_CURRENT_USER=object();fake.KEY_QUERY_VALUE=1;fake.KEY_SET_VALUE=2;fake.REG_SZ=1;fake.REG_EXPAND_SZ=2
    fake.OpenKey=lambda *a,**k:'key';fake.CloseKey=lambda key:None
    fake.QueryValueEx=lambda key,name:(state['path'],fake.REG_EXPAND_SZ)
    def set_value(key,name,reserved,typ,value): state['path']=value
    fake.SetValueEx=set_value
    sys.modules['winreg']=fake
    mod.IS_WINDOWS=True;mod._broadcast_windows_environment_change=lambda:None
    assert mod.promote_managed_ffmpeg_to_user_path(caps) is True
    assert os.environ['PATH'].split(os.pathsep)[0]==str(bindir.resolve()),os.environ['PATH']
    assert state['path'].split(';')[0]==str(bindir.resolve()),state
    assert state['path'].count(str(bindir.resolve()))==1,state
finally:
    mod.IS_WINDOWS=old_is_windows;mod._broadcast_windows_environment_change=old_broadcast;os.environ['PATH']=old_path
    sys.modules.pop('winreg',None);shutil.rmtree(root,ignore_errors=True)
print('WINDOWS MANAGED FFMPEG USER-PATH PROMOTION SIMULATION PASS')
