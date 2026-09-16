import http.client, importlib.util, json, os, pathlib, sys, tempfile, urllib.parse

BASE = pathlib.Path(os.environ.get('SUBBURN_SECURITY_WORK', tempfile.mkdtemp(prefix='subburn-security-'))).resolve()
HOME = BASE / 'home'; OUTSIDE = BASE / 'outside'
HOME.mkdir(parents=True, exist_ok=True); OUTSIDE.mkdir(parents=True, exist_ok=True)
for name, value in {
    'HOME': HOME,
    'XDG_CONFIG_HOME': HOME / '.config',
    'XDG_DATA_HOME': HOME / '.local' / 'share',
    'XDG_CACHE_HOME': HOME / '.cache',
    'XDG_STATE_HOME': HOME / '.local' / 'state',
}.items(): os.environ[name] = str(value)
SAFE = HOME / 'Videos'; SAFE.mkdir(parents=True, exist_ok=True)
(SAFE / 'demo.mp4').write_bytes(b'not-real-video')
(OUTSIDE / 'secret.txt').write_text('secret', encoding='utf-8')
try:
    (SAFE / 'escape').symlink_to(OUTSIDE, target_is_directory=True)
except (OSError, NotImplementedError):
    pass

SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_security_wip09',SRC)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
mod.open_path=lambda p: None
root=mod.create_root(); app=mod.SubBurnApp(root)
port=app.dashboard_port
assert port and app.dashboard_server.server_address[0]=='127.0.0.1'
GOOD_HOST=f'127.0.0.1:{port}'

def raw(method, path, headers=None, body=b'', host=GOOD_HOST, add_length=True):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    c.putrequest(method,path,skip_host=True,skip_accept_encoding=True)
    if host is not None: c.putheader('Host',host)
    for k,v in (headers or {}).items(): c.putheader(k,v)
    if add_length and body is not None and not any(k.casefold()=='content-length' for k in (headers or {})):
        c.putheader('Content-Length',str(len(body)))
    c.endheaders(body if body else None)
    r=c.getresponse(); data=r.read(); hs={k.lower():v for k,v in r.getheaders()}; status=r.status
    c.close(); return status,data,hs

def get_json(*args,**kwargs):
    st,b,h=raw(*args,**kwargs)
    try: obj=json.loads(b.decode())
    except Exception: obj=None
    return st,obj,h

try:
    # Bootstrap page establishes an HttpOnly same-site session and strong browser headers.
    st,html,h=raw('GET','/',add_length=False)
    assert st==200
    text=html.decode('utf-8')
    cookie=h.get('set-cookie','').split(';',1)[0]
    assert cookie.startswith('SubBurnSession=') and len(cookie.split('=',1)[1]) >= 32
    assert 'HttpOnly' in h['set-cookie'] and 'SameSite=Strict' in h['set-cookie']
    assert h.get('x-content-type-options')=='nosniff'
    assert h.get('x-frame-options')=='DENY'
    assert 'frame-ancestors' in h.get('content-security-policy','')
    assert app.dashboard_server.session_token not in text

    auth={'Cookie':cookie,'Accept':'application/json'}
    # API is unusable without the session cookie, with a forged cookie, Host or Origin.
    st,obj,_=get_json('GET','/api/state',headers={'Accept':'application/json'},add_length=False); assert st==403
    st,obj,_=get_json('GET','/api/state',headers={'Cookie':'SubBurnSession=wrong'},add_length=False); assert st==403
    st,obj,_=get_json('GET','/api/state',headers=auth,host='evil.example',add_length=False); assert st==403
    st,obj,_=get_json('GET','/',host=None,add_length=False); assert st==403
    st,obj,_=get_json('POST','/api/action/diagnostics',headers={**auth,'Origin':'https://evil.example'},body=b'{}'); assert st==403

    # Authenticated same-origin API works; obsolete generic API fails closed.
    st,obj,_=get_json('GET','/api/state',headers=auth,add_length=False); assert st==200 and obj['app']=='SubBurn'
    st,obj,_=get_json('GET','/api/v1/state',headers=auth,add_length=False); assert st==404
    st,obj,_=get_json('GET','/does-not-exist',headers=auth,add_length=False); assert st==404

    # Body parser hard limits and rejects unsupported transfer encodings/content types.
    st,obj,_=get_json('POST','/api/action/diagnostics',headers={**auth,'Content-Length':'70000'},body=b'',add_length=False); assert st==400
    st,obj,_=get_json('POST','/api/action/diagnostics',headers={**auth,'Transfer-Encoding':'chunked'},body=b'',add_length=False); assert st==400
    st,obj,_=get_json('POST','/api/job/project',headers={**auth,'Content-Type':'text/plain'},body=b'{}'); assert st==400
    st,obj,_=get_json('POST','/api/job/project',headers={**auth,'Content-Type':'application/json'},body=b'{broken'); assert st==400

    # Picker roots are intentionally constrained and a symlink cannot escape an allowed root.
    st,obj,_=get_json('GET','/api/fs?kind=folder&path=',headers=auth,add_length=False); assert st==200
    roots={pathlib.Path(e['path']).resolve() for e in obj['entries']}
    assert HOME.resolve() in roots
    assert pathlib.Path('/').resolve() not in roots if os.name!='nt' else True
    qs=urllib.parse.quote(str(SAFE))
    st,obj,_=get_json('GET',f'/api/fs?kind=video&path={qs}',headers=auth,add_length=False); assert st==200
    names={e['name'] for e in obj['entries']}; assert 'demo.mp4' in names and 'escape' not in names
    qs=urllib.parse.quote(str(OUTSIDE))
    st,obj,_=get_json('GET',f'/api/fs?kind=folder&path={qs}',headers=auth,add_length=False); assert st==400

    # Redaction removes session secrets, URL credentials and exact home/app paths.
    sample=(f"path={HOME}/private/file.srt SubBurnSession=TOPSECRET "
            "Authorization: Bearer ABC123 https://alice:password@example.test/x?token=XYZ")
    red=mod.redact_sensitive_text(sample)
    assert str(HOME) not in red and 'TOPSECRET' not in red and 'ABC123' not in red
    assert 'password' not in red and 'XYZ' not in red and '<redacted>' in red

    # Diagnostic export must not reveal exact source path or secret-bearing log strings.
    secret_video=HOME/'private'/'very-private-name.mp4'; secret_video.parent.mkdir(parents=True,exist_ok=True); secret_video.write_bytes(b'x')
    app.video_var.set(str(secret_video)); app.ffmpeg_var.set(str(HOME/'tools'/'ffmpeg'))
    app.log_ui(sample)
    mod.open_path=lambda p: None
    before=set(mod.DIAG_DIR.glob('SubBurn-diagnostics-*.txt'))
    app.export_diagnostics()
    after=set(mod.DIAG_DIR.glob('SubBurn-diagnostics-*.txt')); new=sorted(after-before)
    assert new
    diag=new[-1].read_text(encoding='utf-8')
    assert str(HOME) not in diag and 'TOPSECRET' not in diag and 'ABC123' not in diag and 'password' not in diag and 'XYZ' not in diag
    assert 'very-private-name.mp4' in diag and 'ffmpeg' in diag

    print('BROWSER SECURITY WIP09 PASS')
finally:
    try: app.dashboard_server.shutdown(); app.dashboard_server.server_close()
    except Exception: pass
    try: app.system_usage_sampler.stop_event.set()
    except Exception: pass
    try: root.destroy()
    except Exception: pass
