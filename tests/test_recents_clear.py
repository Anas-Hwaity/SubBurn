from __future__ import annotations
import importlib.util, pathlib, sys
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_recents_clear',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
app=object.__new__(mod.SubBurnApp)
app.recents={'projects':[{'label':'A'}],'folders':['C:/A']}
events=[]
app.save_recents=lambda: events.append('save')
app.refresh_recents_ui=lambda: events.append('refresh')
app.publish_dashboard_controls=lambda: events.append('publish')
app.log_ui=lambda msg: events.append(msg)
mod.SubBurnApp.clear_recent_projects(app)
assert app.recents['projects']==[] and app.recents['folders']==['C:/A']
assert events[:3]==['save','refresh','publish']
events.clear();mod.SubBurnApp.clear_recent_folders(app)
assert app.recents['folders']==[]
assert events[:3]==['save','refresh','publish']
app.events=mod.queue.Queue();ok,msg=mod.SubBurnApp.queue_clear_recents(app,'projects');assert ok and 'queued' in msg
kind,args=app.events.get_nowait();assert kind=='clear_recents' and args==('projects',)
ok,_=mod.SubBurnApp.queue_clear_recents(app,'invalid');assert not ok
print('RECENTS CLEAR PASS')
