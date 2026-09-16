from __future__ import annotations
import importlib.util, pathlib, sys, threading
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_progress_pressure',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

class Fake:
    def __init__(self):
        self.op_state=mod.OperationState(); self.op=self.op_state.begin('runtime_download'); self._operation_local=threading.local(); self._operation_local.operation_id=self.op
        self.events=[]
    def current_operation_id(self): return self.op
    def emit(self,kind,*args):
        if kind=='transfer_progress': self.op_state.transfer(self.op,*(list(args[:6])+[None]*6)[:6])
        self.events.append((kind,args))

f=Fake(); cb=mod.SubBurnApp._transfer_progress_callback(f,'FFmpeg runtime')
total=106*1024*1024
# Simulate a pathological 8 KiB reporthook cadence (~13k callbacks) that previously flooded Tk.
step=8192
for done in range(0,total,step): cb(done,total)
cb(total,total)
transfer=[e for e in f.events if e[0]=='transfer_progress']
assert transfer, 'no transfer events'
assert len(transfer)<250, f'progress callback flooded UI queue: {len(transfer)} events'
s=f.op_state.operation_snapshot(f.op)
assert s['transfer_pct']==100 and s['bytes_done']==total and s['bytes_total']==total, s
print(f'PROGRESS EVENT PRESSURE PASS: {len(transfer)} UI events for {total//step:,}+ source callbacks')
