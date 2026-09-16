from __future__ import annotations
import importlib.util, pathlib, sys
from types import SimpleNamespace
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_watermark_font_intent',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
class Var:
    def __init__(self,v): self.v=v
    def get(self): return self.v
    def set(self,v): self.v=v
app=object.__new__(mod.SubBurnApp)
app.wm_font_var=Var('Aljazeera'); app.same_wm_font_var=Var(True)
seen=[]
app.refresh_watermark_font_control_state=lambda: seen.append('refresh')
app.autosave_project=lambda: seen.append('save')
mod.SubBurnApp.on_watermark_font_selected(app)
assert app.same_wm_font_var.get() is False
assert seen==['refresh','save'],seen
job=SimpleNamespace(primary_font='SubtitleFont',same_wm_font=False,wm_font='Aljazeera')
app._job_local=mod.threading.local(); app._job=job
rec1=SimpleNamespace(label='SubtitleFont');rec2=SimpleNamespace(label='Aljazeera')
app.font_map={'SubtitleFont':rec1,'Aljazeera':rec2}
assert mod.SubBurnApp.selected_font(app,True) is rec2
job.same_wm_font=True
assert mod.SubBurnApp.selected_font(app,True) is rec1
print('WATERMARK FONT INTENT PASS')
