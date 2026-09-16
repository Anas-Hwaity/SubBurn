from __future__ import annotations
import importlib.util, os, pathlib, sys, tempfile, shutil
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_ffmpeg_discovery',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
root=pathlib.Path(tempfile.mkdtemp(prefix='subburn-ffmpeg-discovery-'))
old_path=os.environ.get('PATH','')
try:
    d1=root/'first';d2=root/'second';saved=root/'saved';
    for d in (d1,d2,saved): d.mkdir(parents=True)
    exe='ffmpeg.exe' if mod.IS_WINDOWS else 'ffmpeg'
    f1=d1/exe;f2=d2/exe;fs=saved/exe
    for f in (f1,f2,fs): f.write_bytes(b'x')
    os.environ['PATH']=os.pathsep.join([str(d1),str(d2)])
    got=mod.candidate_ffmpeg_paths(str(saved))
    resolved=[p.resolve() for p in got]
    assert fs.resolve() in resolved, ('saved directory was not expanded',got)
    assert f1.resolve() in resolved and f2.resolve() in resolved, ('not all PATH FFmpeg entries discovered',got)
    assert len(resolved)==len(set(map(str,resolved))), ('candidate dedupe failed',got)
    print('FFMPEG MULTI-PATH / SAVED-DIRECTORY DISCOVERY PASS')
finally:
    os.environ['PATH']=old_path
    shutil.rmtree(root,ignore_errors=True)
