from __future__ import annotations
import importlib.util, pathlib, sys
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_terminal_elapsed',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

clock={'t':100.0}
orig=mod.time.monotonic
mod.time.monotonic=lambda: clock['t']
try:
    st=mod.OperationState(); oid=st.begin('encode')
    clock['t']=105.0; st.progress(oid,25,fps='30',speed='1.0x',eta='00:30')
    clock['t']=112.0; st.finish(oid,'succeeded',result='out.mp4')
    first=st.operation_snapshot(oid)
    assert first['elapsed']==12.0, first
    clock['t']=999.0
    later=st.operation_snapshot(oid)
    assert later['elapsed']==12.0, later
    assert later['state']=='succeeded' and later['progress_pct']==100.0

    clock['t']=1000.0
    tr=mod.OperationState(); tid=tr.begin('runtime_download')
    tr.stage(tid,'FFmpeg download',0,'Downloading')
    clock['t']=1002.0; tr.transfer(tid,0,0,100,0,None,'Downloading')
    clock['t']=1008.0; tr.transfer(tid,100,100,100,10,0,'Archive received')
    clock['t']=1015.0; tr.finish(tid,'succeeded')
    snap=tr.operation_snapshot(tid)
    assert snap['transfer_elapsed']==6.0, snap
    assert snap['elapsed']==15.0, snap
    clock['t']=2000.0
    snap2=tr.operation_snapshot(tid)
    assert snap2['transfer_elapsed']==6.0 and snap2['elapsed']==15.0, snap2
finally:
    mod.time.monotonic=orig
print('TERMINAL ELAPSED/TRANSFER TIMER FREEZE PASS')
