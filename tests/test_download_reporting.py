from __future__ import annotations
import importlib.util, pathlib, sys, tempfile, threading
from types import SimpleNamespace
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_download_reporting',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

# Transcription sentence must identify what, why, once/reuse, and size context.
msg=mod.transcription_model_download_message('tiny')
low=msg.lower()
assert 'pinned tiny transcription model' in low, msg
assert 'local transcription' in low, msg
assert 'once' in low and 'reused' in low, msg
assert '(' in msg and ')' in msg, msg

# FFmpeg foreground status must stay concise while the technical log retains the rejected path.
app=object.__new__(mod.SubBurnApp)
app.ffmpeg_setup_lock=threading.Lock();app._automatic_ffmpeg_install_attempted=False
app._job_local=threading.local();app._job=SimpleNamespace(ffmpeg='')
events=[];stages=[]
app.emit=lambda kind,*args: events.append((kind,args))
app.set_stage=lambda *args,**kwargs: stages.append(args)
old_scan=mod.scan_local_toolsets;old_dl=mod.download_private_ffmpeg
bad=mod.Toolset(ffmpeg=pathlib.Path(tempfile.gettempdir())/'old-ffmpeg.exe',ffprobe=pathlib.Path(tempfile.gettempdir())/'ffprobe.exe',version='old',filters={'drawtext'},encoders=['libx264'],score=1)
good=mod.Toolset(ffmpeg=pathlib.Path(tempfile.gettempdir())/'managed-ffmpeg.exe',ffprobe=pathlib.Path(tempfile.gettempdir())/'managed-ffprobe.exe',version='good',filters={'subtitles','ass'},encoders=['libx264'],score=100)
mod.scan_local_toolsets=lambda saved:(None,[bad],[(str(bad.ffmpeg),'subtitle rendering filter is missing')])
mod.download_private_ffmpeg=lambda *args,**kwargs: good
try:
    resolved,found,installed=mod.SubBurnApp._resolve_ffmpeg(app,allow_managed_install=True,explicit_install=False)
    assert resolved is good and installed is True
    statuses=[str(args[0]) for kind,args in events if kind=='status' and args]
    logs=[str(args[0]) for kind,args in events if kind=='log' and args]
    assert statuses, events
    front=statuses[-1]
    assert 'installed FFmpeg cannot render subtitles' in front, front
    assert 'once' in front and '100 MB' in front, front
    assert str(bad.ffmpeg) not in front, front
    assert any(str(bad.ffmpeg) in line for line in logs), logs
    assert len(front) < 190, len(front)
finally:
    mod.scan_local_toolsets=old_scan;mod.download_private_ffmpeg=old_dl

print('DOWNLOAD EXPLANATION / LOG DETAIL SEPARATION PASS')
