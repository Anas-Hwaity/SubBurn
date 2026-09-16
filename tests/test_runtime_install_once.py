import importlib.util, pathlib, shutil, sys, tempfile, threading, time, zipfile
from types import SimpleNamespace

SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_runtime_install_once',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

def fake_caps(path):
    path=pathlib.Path(path)
    return mod.Toolset(ffmpeg=path,ffprobe=path.with_name('ffprobe.exe'),version='ffmpeg test',filters={'subtitles','ass'},encoders=['libx264'],score=100)

# 1) A valid managed runtime is reused without touching the network.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-runtime-once-'))
old_runtime=mod.RUNTIME_DIR; old_inspect=mod.inspect_toolset; old_download=mod._download_verified_archive; old_build=mod._ffmpeg_buildconf
mod.RUNTIME_DIR=td/'runtime'
target=mod.RUNTIME_DIR/'ffmpeg'/'bin';target.mkdir(parents=True)
ff_name='ffmpeg.exe' if mod.IS_WINDOWS else 'ffmpeg'; fp_name='ffprobe.exe' if mod.IS_WINDOWS else 'ffprobe'
(target/ff_name).write_bytes(b'ffmpeg');(target/fp_name).write_bytes(b'ffprobe')
network={'calls':0}
def fail_download(*a,**k):
    network['calls']+=1
    raise AssertionError('network download should not be used for an already valid runtime')
mod.inspect_toolset=lambda path: fake_caps(path)
mod._download_verified_archive=fail_download
try:
    got=mod.download_private_ffmpeg(url='https://example.invalid/ffmpeg.zip',checksum_url='https://example.invalid/ffmpeg.sha256')
    assert got.ffmpeg==target/ff_name
    assert network['calls']==0
finally:
    mod.RUNTIME_DIR=old_runtime;mod.inspect_toolset=old_inspect;mod._download_verified_archive=old_download;mod._ffmpeg_buildconf=old_build
    shutil.rmtree(td,ignore_errors=True)

# 2) Two concurrent callers produce exactly one download. The second re-checks after the lock.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-runtime-concurrent-'))
old_runtime=mod.RUNTIME_DIR; old_inspect=mod.inspect_toolset; old_download=mod._download_verified_archive; old_build=mod._ffmpeg_buildconf
mod.RUNTIME_DIR=td/'runtime'
calls={'download':0}
def inspect_if_present(path):
    path=pathlib.Path(path)
    if not path.is_file(): raise RuntimeError('missing')
    return fake_caps(path)
def download_archive(url,destination,progress=None,**kwargs):
    calls['download']+=1
    time.sleep(.12)
    destination=pathlib.Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w') as z:
        z.writestr('ffmpeg-build/bin/'+('ffmpeg.exe' if mod.IS_WINDOWS else 'ffmpeg'),b'ffmpeg')
        z.writestr('ffmpeg-build/bin/'+('ffprobe.exe' if mod.IS_WINDOWS else 'ffprobe'),b'ffprobe')
    digest=mod.full_file_sha256(destination)
    if progress: progress(destination.stat().st_size,destination.stat().st_size)
    return {'path':str(destination),'sha256':digest,'publisher_sha256':digest}
mod.inspect_toolset=inspect_if_present;mod._download_verified_archive=download_archive;mod._ffmpeg_buildconf=lambda ff:'--enable-libass'
results=[];errors=[]
def worker():
    try: results.append(mod.download_private_ffmpeg(url='https://example.invalid/ffmpeg.zip',checksum_url='https://example.invalid/ffmpeg.sha256'))
    except Exception as exc: errors.append(exc)
threads=[threading.Thread(target=worker) for _ in range(2)]
for t in threads:t.start()
for t in threads:t.join(10)
try:
    assert not errors,errors
    assert len(results)==2
    assert calls['download']==1,calls
    assert all(x.ffmpeg.is_file() for x in results)
finally:
    mod.RUNTIME_DIR=old_runtime;mod.inspect_toolset=old_inspect;mod._download_verified_archive=old_download;mod._ffmpeg_buildconf=old_build
    shutil.rmtree(td,ignore_errors=True)

# 3) Transfer telemetry keeps bytes and speed in separate fields.
state=mod.OperationState();op=state.begin('runtime_download')
state.transfer(op,50,50*1024*1024,100*1024*1024,2.5*1024*1024,20.0,'Downloading FFmpeg runtime')
snap=state.operation_snapshot(op)
assert snap['downloaded']=='50.0 MiB / 100.0 MiB',snap
assert snap['speed']=='2.5 MiB/s',snap
assert str(snap['eta']).startswith('00:20'),snap
assert '/' not in snap['speed'].removesuffix('/s'),snap

# 4) Analyze uses the returned toolset immediately; it does not wait for queued Tk application.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-analyze-race-'))
video=td/'video.mp4';video.write_bytes(b'x')
app=object.__new__(mod.SubBurnApp)
app.toolset=None
app._job_local=threading.local();app._job=SimpleNamespace(video=str(video),ffmpeg='')
resolved=fake_caps(td/'ffmpeg.exe')
app._resolve_ffmpeg=lambda **kwargs:(resolved,[resolved],False)
events=[]
app.emit=lambda kind,*args:events.append((kind,args))
app.set_stage=lambda *a,**k:None
old_probe=mod.probe_media
seen=[]
mod.probe_media=lambda ffprobe,path:(seen.append((ffprobe,path)) or SimpleNamespace())
try:
    mod.SubBurnApp.analyze_worker(app)
    assert seen and seen[0][0]==resolved.ffprobe
    assert any(k=='media' for k,_ in events)
    assert not any(k=='error' for k,_ in events),events
finally:
    mod.probe_media=old_probe;shutil.rmtree(td,ignore_errors=True)


# 5) A completed verified transfer is cached and reused after a later install-stage failure.
td=pathlib.Path(tempfile.mkdtemp(prefix="subburn-runtime-cache-"))
old_cache_dir=mod.FFMPEG_DOWNLOAD_CACHE_DIR;old_cache=mod.FFMPEG_ARCHIVE_CACHE;old_meta=mod.FFMPEG_ARCHIVE_CACHE_META
old_urlretrieve=mod.urllib.request.urlretrieve;old_fetch=mod._fetch_publisher_sha256
mod.FFMPEG_DOWNLOAD_CACHE_DIR=td/"downloads";mod.FFMPEG_ARCHIVE_CACHE=mod.FFMPEG_DOWNLOAD_CACHE_DIR/"ffmpeg.zip";mod.FFMPEG_ARCHIVE_CACHE_META=mod.FFMPEG_DOWNLOAD_CACHE_DIR/"ffmpeg.verified.json"
payload=b"verified-runtime-archive"
digest=mod.hashlib.sha256(payload).hexdigest();calls={"download":0,"checksum":0}
def fake_fetch(url,timeout=30):
    calls["checksum"]+=1
    return digest
def fake_retrieve(url,destination,hook=None):
    calls["download"]+=1
    destination=pathlib.Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(payload)
    if hook: hook(1,len(payload),len(payload))
    return str(destination),None
mod._fetch_publisher_sha256=fake_fetch;mod.urllib.request.urlretrieve=fake_retrieve
try:
    first=mod._download_verified_archive("https://example.invalid/runtime.zip",mod.FFMPEG_ARCHIVE_CACHE,checksum_url="https://example.invalid/runtime.sha256")
    assert first["sha256"]==digest and first["reused_cache"] is False,first
    # A later retry must not use network/checksum again once authenticated bytes exist.
    mod._fetch_publisher_sha256=lambda *a,**k: (_ for _ in ()).throw(AssertionError("checksum network must not be used for verified cache"))
    mod.urllib.request.urlretrieve=lambda *a,**k: (_ for _ in ()).throw(AssertionError("archive network must not be used for verified cache"))
    second=mod._download_verified_archive("https://example.invalid/runtime.zip",mod.FFMPEG_ARCHIVE_CACHE,checksum_url="https://example.invalid/runtime.sha256")
    assert second["sha256"]==digest and second["reused_cache"] is True,second
    assert calls["download"]==1 and calls["checksum"]==1,calls
finally:
    mod.FFMPEG_DOWNLOAD_CACHE_DIR=old_cache_dir;mod.FFMPEG_ARCHIVE_CACHE=old_cache;mod.FFMPEG_ARCHIVE_CACHE_META=old_meta
    mod.urllib.request.urlretrieve=old_urlretrieve;mod._fetch_publisher_sha256=old_fetch
    shutil.rmtree(td,ignore_errors=True)

# 6) An already compatible installed FFmpeg path prevents the managed downloader from running.
app=object.__new__(mod.SubBurnApp);app.ffmpeg_setup_lock=threading.Lock();app._automatic_ffmpeg_install_attempted=False;app._job_local=threading.local();app._job=SimpleNamespace(ffmpeg="saved")
app.emit=lambda *a,**k:None;app.set_stage=lambda *a,**k:None
old_scan=mod.scan_local_toolsets;old_private=mod.download_private_ffmpeg
compatible=fake_caps(pathlib.Path(tempfile.gettempdir())/"existing-ffmpeg.exe")
compatible.filters={"subtitles","ass"}
mod.scan_local_toolsets=lambda saved:(compatible,[compatible],[])
mod.download_private_ffmpeg=lambda *a,**k: (_ for _ in ()).throw(AssertionError("managed runtime download should not run when compatible FFmpeg already exists"))
try:
    resolved,found,installed=mod.SubBurnApp._resolve_ffmpeg(app,allow_managed_install=True,explicit_install=False)
    assert resolved is compatible and installed is False and found==[compatible]
finally:
    mod.scan_local_toolsets=old_scan;mod.download_private_ffmpeg=old_private

print("RUNTIME VERIFIED-CACHE / EXISTING-FFMPEG REUSE PASS")
print("RUNTIME INSTALL-ONCE / RACE / TRANSFER TELEMETRY PASS")

# 7) Publisher checksum failure must happen before the large archive transfer starts.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-runtime-checksum-first-'))
old_fetch=mod._fetch_publisher_sha256;old_retrieve=mod.urllib.request.urlretrieve
transfer_calls={'n':0}
mod._fetch_publisher_sha256=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('simulated checksum service failure'))
def must_not_transfer(*a,**k):
    transfer_calls['n']+=1
    raise AssertionError('large archive transfer started before publisher checksum was available')
mod.urllib.request.urlretrieve=must_not_transfer
try:
    try:
        mod._download_verified_archive('https://example.invalid/runtime.zip',td/'runtime.zip',checksum_url='https://example.invalid/runtime.sha256')
        raise AssertionError('checksum failure unexpectedly succeeded')
    except RuntimeError as exc:
        assert 'checksum service failure' in str(exc)
    assert transfer_calls['n']==0,transfer_calls
finally:
    mod._fetch_publisher_sha256=old_fetch;mod.urllib.request.urlretrieve=old_retrieve
    shutil.rmtree(td,ignore_errors=True)

# 8) If extraction fails after a full verified download, retry reuses the authenticated archive with zero network.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-runtime-postdownload-failure-'))
old_runtime=mod.RUNTIME_DIR;old_cache_dir=mod.FFMPEG_DOWNLOAD_CACHE_DIR;old_cache=mod.FFMPEG_ARCHIVE_CACHE;old_meta=mod.FFMPEG_ARCHIVE_CACHE_META
old_fetch=mod._fetch_publisher_sha256;old_retrieve=mod.urllib.request.urlretrieve;old_extract=mod._safe_extract_runtime_zip
old_inspect=mod.inspect_toolset;old_managed=mod.inspect_managed_ffmpeg;old_build=mod._ffmpeg_buildconf
mod.RUNTIME_DIR=td/'runtime';mod.FFMPEG_DOWNLOAD_CACHE_DIR=mod.RUNTIME_DIR/'downloads';mod.FFMPEG_ARCHIVE_CACHE=mod.FFMPEG_DOWNLOAD_CACHE_DIR/'ffmpeg.zip';mod.FFMPEG_ARCHIVE_CACHE_META=mod.FFMPEG_DOWNLOAD_CACHE_DIR/'ffmpeg.verified.json'
archive_source=td/'source.zip'
with zipfile.ZipFile(archive_source,'w') as z:
    z.writestr('ffmpeg-build/bin/'+('ffmpeg.exe' if mod.IS_WINDOWS else 'ffmpeg'),b'ffmpeg')
    z.writestr('ffmpeg-build/bin/'+('ffprobe.exe' if mod.IS_WINDOWS else 'ffprobe'),b'ffprobe')
payload=archive_source.read_bytes();digest=mod.hashlib.sha256(payload).hexdigest();net={'checksum':0,'download':0}
def fetch_ok(*a,**k): net['checksum']+=1; return digest
def retrieve_ok(url,destination,hook=None):
    net['download']+=1;destination=pathlib.Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(payload)
    if hook: hook(1,len(payload),len(payload))
    return str(destination),None
mod._fetch_publisher_sha256=fetch_ok;mod.urllib.request.urlretrieve=retrieve_ok
mod.inspect_managed_ffmpeg=lambda *a,**k: None
mod.inspect_toolset=lambda path: fake_caps(path)
mod._ffmpeg_buildconf=lambda ff:'--enable-libass'
mod._safe_extract_runtime_zip=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('simulated extraction failure after verified transfer'))
try:
    try:
        mod.download_private_ffmpeg(url='https://example.invalid/runtime.zip',checksum_url='https://example.invalid/runtime.sha256',force=True)
        raise AssertionError('post-download extraction failure unexpectedly succeeded')
    except RuntimeError as exc:
        assert 'simulated extraction failure' in str(exc)
    assert net=={'checksum':1,'download':1},net
    assert mod.FFMPEG_ARCHIVE_CACHE.is_file() and mod.FFMPEG_ARCHIVE_CACHE_META.is_file()

    # Retry with network hard-disabled. The verified archive must be enough.
    mod._fetch_publisher_sha256=lambda *a,**k: (_ for _ in ()).throw(AssertionError('retry must not re-fetch checksum'))
    mod.urllib.request.urlretrieve=lambda *a,**k: (_ for _ in ()).throw(AssertionError('retry must not re-download archive'))
    mod._safe_extract_runtime_zip=old_extract
    caps=mod.download_private_ffmpeg(url='https://example.invalid/runtime.zip',checksum_url='https://example.invalid/runtime.sha256',force=True)
    assert caps and 'subtitles' in caps.filters
    assert net=={'checksum':1,'download':1},net
finally:
    mod.RUNTIME_DIR=old_runtime;mod.FFMPEG_DOWNLOAD_CACHE_DIR=old_cache_dir;mod.FFMPEG_ARCHIVE_CACHE=old_cache;mod.FFMPEG_ARCHIVE_CACHE_META=old_meta
    mod._fetch_publisher_sha256=old_fetch;mod.urllib.request.urlretrieve=old_retrieve;mod._safe_extract_runtime_zip=old_extract
    mod.inspect_toolset=old_inspect;mod.inspect_managed_ffmpeg=old_managed;mod._ffmpeg_buildconf=old_build
    shutil.rmtree(td,ignore_errors=True)

# 9) A corrupt cache never gets trusted: it triggers exactly one fresh checksum+archive transfer.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-runtime-corrupt-cache-'))
old_cache_meta=mod.FFMPEG_ARCHIVE_CACHE_META;old_fetch=mod._fetch_publisher_sha256;old_retrieve=mod.urllib.request.urlretrieve
cache=td/'runtime.zip';meta=td/'runtime.verified.json';mod.FFMPEG_ARCHIVE_CACHE_META=meta
payload=b'fresh-authenticated-runtime';digest=mod.hashlib.sha256(payload).hexdigest()
cache.write_bytes(b'corrupt-old-runtime')
mod._atomic_write_json(meta,{'schema':1,'source_url':'https://example.invalid/runtime.zip','archive_sha256':digest,'publisher_sha256':digest})
net={'checksum':0,'download':0}
def fresh_fetch(*a,**k): net['checksum']+=1; return digest
def fresh_retrieve(url,destination,hook=None):
    net['download']+=1;pathlib.Path(destination).write_bytes(payload)
    if hook: hook(1,len(payload),len(payload))
    return str(destination),None
mod._fetch_publisher_sha256=fresh_fetch;mod.urllib.request.urlretrieve=fresh_retrieve
try:
    info=mod._download_verified_archive('https://example.invalid/runtime.zip',cache,checksum_url='https://example.invalid/runtime.sha256')
    assert info['reused_cache'] is False and info['sha256']==digest
    assert cache.read_bytes()==payload
    assert net=={'checksum':1,'download':1},net
finally:
    mod.FFMPEG_ARCHIVE_CACHE_META=old_cache_meta;mod._fetch_publisher_sha256=old_fetch;mod.urllib.request.urlretrieve=old_retrieve
    shutil.rmtree(td,ignore_errors=True)

print('RUNTIME CHECKSUM-FIRST / POST-DOWNLOAD-RETRY / CORRUPT-CACHE RECOVERY PASS')

# 10) A failed automatic managed-runtime attempt cannot loop/restart automatically in the same app session.
app=object.__new__(mod.SubBurnApp);app.ffmpeg_setup_lock=threading.Lock();app._automatic_ffmpeg_install_attempted=False;app._job_local=threading.local();app._job=SimpleNamespace(ffmpeg='')
app.emit=lambda *a,**k:None;app.set_stage=lambda *a,**k:None
old_scan=mod.scan_local_toolsets;old_private=mod.download_private_ffmpeg
auto_calls={'n':0}
mod.scan_local_toolsets=lambda saved:(None,[],[])
def fail_once(*a,**k):
    auto_calls['n']+=1
    raise RuntimeError('simulated install-stage failure after transfer')
mod.download_private_ffmpeg=fail_once
try:
    try:
        mod.SubBurnApp._resolve_ffmpeg(app,allow_managed_install=True,explicit_install=False)
        raise AssertionError('first automatic setup failure unexpectedly succeeded')
    except RuntimeError as exc:
        assert 'simulated install-stage failure' in str(exc)
    assert auto_calls['n']==1 and app._automatic_ffmpeg_install_attempted is True
    try:
        mod.SubBurnApp._resolve_ffmpeg(app,allow_managed_install=True,explicit_install=False)
        raise AssertionError('second automatic setup attempt unexpectedly ran')
    except RuntimeError as exc:
        assert 'already attempted this session' in str(exc), str(exc)
    assert auto_calls['n']==1, auto_calls
finally:
    mod.scan_local_toolsets=old_scan;mod.download_private_ffmpeg=old_private

print('RUNTIME FAILED-AUTO-ATTEMPT LOOP PREVENTION PASS')
