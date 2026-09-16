import json, os, pathlib, sqlite3, subprocess, sys
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
home=pathlib.Path(os.environ['SUBBURN_MIGRATION_HOME'])
legacy=home/'.subburn';legacy.mkdir(parents=True,exist_ok=True)
(legacy/'settings.json').write_text(json.dumps({'codec':'H.264'}),encoding='utf-8')
(legacy/'presets.json').write_text(json.dumps({'schema':1,'presets':[]}),encoding='utf-8')
(legacy/'recents.json').write_text(json.dumps({'projects':[],'folders':['legacy-folder']}),encoding='utf-8')
(legacy/'fonts').mkdir(exist_ok=True);(legacy/'fonts'/'marker.txt').write_text('legacy-font-dir',encoding='utf-8')
con=sqlite3.connect(legacy/'queue.sqlite3');con.execute('create table legacy_marker(value text)');con.execute('insert into legacy_marker values (?)',('queue-ok',));con.commit();con.close()
code=f'''import importlib.util,sys,sqlite3,pathlib,json\np={str(SRC)!r}\ns=importlib.util.spec_from_file_location("migrate_probe",p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)\nassert m.SETTINGS_FILE.is_file()\nassert json.loads(m.SETTINGS_FILE.read_text())["codec"]=="H.264"\nassert m.RECENTS_FILE.is_file()\nassert (m.FONT_DIR/"marker.txt").read_text()=="legacy-font-dir"\nc=sqlite3.connect(m.QUEUE_DB);v=c.execute("select value from legacy_marker").fetchone()[0];c.close();assert v=="queue-ok"\nassert (pathlib.Path.home()/".subburn"/"settings.json").is_file()\nprint("MIGRATION PASS",sorted(m.LEGACY_MIGRATED_ITEMS))'''
env=dict(os.environ);env['HOME']=str(home);env.pop('XDG_CONFIG_HOME',None);env.pop('XDG_DATA_HOME',None);env.pop('XDG_CACHE_HOME',None);env.pop('XDG_STATE_HOME',None)
r=subprocess.run([sys.executable,'-c',code],env=env,text=True,capture_output=True,timeout=20)
print(r.stdout,end='');
if r.returncode: print(r.stderr,file=sys.stderr)
assert r.returncode==0
print('LEGACY STORAGE MIGRATION PASS')
