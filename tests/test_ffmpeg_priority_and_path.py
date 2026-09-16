from __future__ import annotations
import importlib.util, os, pathlib, sys, tempfile, shutil
from types import SimpleNamespace

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_ffmpeg_priority',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
root=pathlib.Path(tempfile.mkdtemp(prefix='subburn-ffmpeg-priority-'))
old_path=os.environ.get('PATH','');old_runtime=mod.RUNTIME_DIR;old_inspect=mod.inspect_toolset
try:
    system1=root/'sys1';system2=root/'sys2';user=root/'chosen';managed_root=root/'runtime'/'ffmpeg'/'bin'
    for d in (system1,system2,user,managed_root):d.mkdir(parents=True,exist_ok=True)
    exe='ffmpeg.exe' if mod.IS_WINDOWS else 'ffmpeg';probe='ffprobe.exe' if mod.IS_WINDOWS else 'ffprobe'
    paths=[system1/exe,system2/exe,user/exe,managed_root/exe]
    for f in paths:
        f.write_bytes(b'x');f.with_name(probe).write_bytes(b'p')
    mod.RUNTIME_DIR=root/'runtime'
    os.environ['PATH']=os.pathsep.join([str(system1),str(system2)])
    def caps(path,filters,score):
        path=pathlib.Path(path);return mod.Toolset(ffmpeg=path,ffprobe=path.with_name(probe),version='test',filters=set(filters),encoders=['libx264'],score=score)
    mapping={
        str((system1/exe).resolve()):caps(system1/exe,{'drawtext'},999),
        str((system2/exe).resolve()):caps(system2/exe,{'subtitles','ass'},10),
        str((user/exe).resolve()):caps(user/exe,{'subtitles','ass'},5000),
        str((managed_root/exe).resolve()):caps(managed_root/exe,{'subtitles','ass'},9000),
    }
    mod.inspect_toolset=lambda p:mapping[str(pathlib.Path(p).resolve())]
    best,found,rejected=mod.scan_local_toolsets(str(user))
    assert best.ffmpeg.resolve()==(system2/exe).resolve(),(best.ffmpeg,rejected)
    assert any(str(system1/exe) in r[0] for r in rejected),rejected
    # If every system candidate is incompatible, the explicit user location must beat managed.
    mapping[str((system2/exe).resolve())]=caps(system2/exe,{'drawtext'},10000)
    best,found,rejected=mod.scan_local_toolsets(str(user))
    assert best.ffmpeg.resolve()==(user/exe).resolve(),best.ffmpeg
    # If system and user are incompatible, a previously managed verified runtime is the third stage.
    mapping[str((user/exe).resolve())]=caps(user/exe,{'drawtext'},10000)
    best,found,rejected=mod.scan_local_toolsets(str(user))
    assert best.ffmpeg.resolve()==(managed_root/exe).resolve(),best.ffmpeg
finally:
    os.environ['PATH']=old_path;mod.RUNTIME_DIR=old_runtime;mod.inspect_toolset=old_inspect;shutil.rmtree(root,ignore_errors=True)
print('FFMPEG PRIORITY SYSTEM -> USER -> MANAGED PASS')
