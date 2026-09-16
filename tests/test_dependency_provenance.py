import importlib.util, json, os, pathlib, shutil, sys, tempfile, zipfile
from types import SimpleNamespace
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_dependency_provenance',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

# Registry: six audited immutable sources, never mutable main.
assert set(mod.TRANSCRIPTION_MODEL_SOURCES)==set(mod.TRANSCRIPTION_MODELS)
for name in mod.TRANSCRIPTION_MODELS:
    src=mod.transcription_model_source(name)
    assert len(src['revision'])==40 and all(c in '0123456789abcdef' for c in src['revision'])
    assert src['license']=='MIT'
    assert src['repo'] and src['upstream']
assert mod.transcription_model_source('turbo')['revision']=='0c94664816ec82be77b20e824c8e8675995b0029'

# Isolate model files for this test.
td=pathlib.Path(tempfile.mkdtemp(prefix='subburn-prov-'))
old_dir=mod.TRANSCRIPTION_MODEL_DIR
old_cache=mod.TRANSCRIPTION_MODEL_METADATA_CACHE
mod.TRANSCRIPTION_MODEL_DIR=td/'models'
mod.TRANSCRIPTION_MODEL_METADATA_CACHE=td/'metadata.json'

calls=[]
def fake_snapshot(**kwargs):
    calls.append(dict(kwargs))
    out=pathlib.Path(kwargs['local_dir']);out.mkdir(parents=True,exist_ok=True)
    (out/'config.json').write_text('{}',encoding='utf-8')
    (out/'model.bin').write_bytes(b'model-fixture')
    (out/'tokenizer.json').write_text('{}',encoding='utf-8')
    (out/'vocabulary.txt').write_text('hello',encoding='utf-8')
    (out/'.cache').mkdir(exist_ok=True)
    return str(out)
old_snapshot=mod._huggingface_snapshot_download
mod._huggingface_snapshot_download=fake_snapshot
try:
    path=mod.prepare_transcription_model_snapshot('tiny')
    src=mod.transcription_model_source('tiny')
    assert path==mod.transcription_model_install_dir('tiny') and path.is_dir()
    assert len(calls)==1
    call=calls[0]
    assert call['repo_id']==src['repo'] and call['revision']==src['revision']
    assert set(call['allow_patterns'])==set(mod.TRANSCRIPTION_MODEL_ALLOW_PATTERNS)
    assert not (path/'.cache').exists()
    assert mod.transcription_model_ready('tiny')
    marker=json.loads(mod.transcription_model_marker('tiny').read_text(encoding='utf-8'))
    assert marker['repo']==src['repo'] and marker['revision']==src['revision'] and marker['license']=='MIT'
    assert marker['files']['config.json']['sha256']!='' and marker['files']['model.bin']['size']>0
    # Ready model must not touch the downloader again.
    mod.prepare_transcription_model_snapshot('tiny');assert len(calls)==1
    # A stale/mutated revision marker is rejected, not silently accepted.
    marker['revision']='0'*40;mod._atomic_write_json(mod.transcription_model_marker('tiny'),marker)
    assert not mod.transcription_model_ready('tiny')
    # restore correct marker without redownload for the load-local-only test
    mod.write_transcription_marker('tiny','test')

    class FakeModel:
        seen=[]
        def __init__(self,path,**kwargs): self.seen.append((path,dict(kwargs)))
    class FakePipeline: pass
    fake_ct2=SimpleNamespace(get_cuda_device_count=lambda:0)
    old_runtime=mod.ensure_faster_whisper_runtime
    old_prepare=mod.prepare_transcription_model_snapshot
    mod.ensure_faster_whisper_runtime=lambda allow_install=False:(FakeModel,FakePipeline,fake_ct2)
    mod.prepare_transcription_model_snapshot=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network/download path used for ready model'))
    try:
        app=object.__new__(mod.SubBurnApp)
        app.log=lambda *_:None
        request=mod.TranscriptionRequest(video='dummy',model='tiny',language_mode='Fixed language code',language_code='en',allowed_languages=(),device='CPU',allow_model_download=False)
        model,pipeline,device,compute=mod.SubBurnApp.load_transcription_model(app,request,allow_download=False)
        assert FakeModel.seen
        mpath,kwargs=FakeModel.seen[-1]
        assert pathlib.Path(mpath)==mod.transcription_model_install_dir('tiny')
        assert kwargs.get('local_files_only') is True and 'download_root' not in kwargs
        assert device=='cpu'
    finally:
        mod.ensure_faster_whisper_runtime=old_runtime
        mod.prepare_transcription_model_snapshot=old_prepare
finally:
    mod._huggingface_snapshot_download=old_snapshot

# Pinned revision is part of the HF metadata request path.
class FakeResponse:
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self): return json.dumps({'siblings':[{'rfilename':'model.bin','size':10},{'rfilename':'config.json','size':2},{'rfilename':'README.md','size':999}]}).encode()
seen_url=[]
old_open=mod.urllib.request.urlopen
mod.urllib.request.urlopen=lambda req,timeout=0:(seen_url.append(req.full_url) or FakeResponse())
try:
    assert mod.fetch_transcription_model_download_bytes('base')==12
    assert mod.transcription_model_revision('base') in seen_url[-1] and '/revision/' in seen_url[-1]
finally: mod.urllib.request.urlopen=old_open

# Publisher checksum parser + authenticated archive behavior.
sha='a'*64
assert mod._parse_publisher_sha256(sha+'  ffmpeg.zip')==sha
for bad in ('','abc','g'*64):
    try: mod._parse_publisher_sha256(bad)
    except RuntimeError: pass
    else: raise AssertionError('bad checksum accepted')

download_dir=td/'download';download_dir.mkdir()
old_urlretrieve=mod.urllib.request.urlretrieve; old_fetch=mod._fetch_publisher_sha256
payload=b'verified archive fixture'; expected=mod.hashlib.sha256(payload).hexdigest()
def fake_urlretrieve(url,dest,hook=None):
    pathlib.Path(dest).write_bytes(payload)
    if hook: hook(1,len(payload),len(payload))
    return str(dest),None
mod.urllib.request.urlretrieve=fake_urlretrieve;mod._fetch_publisher_sha256=lambda url:expected
try:
    info=mod._download_verified_archive('https://example.invalid/x.zip',download_dir/'ok.zip',checksum_url='https://example.invalid/x.sha256')
    assert info['sha256']==expected and info['publisher_sha256']==expected
    mod._fetch_publisher_sha256=lambda url:'0'*64
    try: mod._download_verified_archive('x',download_dir/'bad.zip',checksum_url='y')
    except RuntimeError as e:
        msg=str(e)
        assert 'verification failed' in msg and 'nothing was installed' in msg and 'expected SHA-256' in msg and 'got ' in msg, msg
    else: raise AssertionError('checksum mismatch accepted')
finally:
    mod.urllib.request.urlretrieve=old_urlretrieve;mod._fetch_publisher_sha256=old_fetch

# ZIP extraction rejects traversal and symlinks.
unsafe=td/'unsafe.zip'
with zipfile.ZipFile(unsafe,'w') as z: z.writestr('../escape.txt','x')
try: mod._safe_extract_runtime_zip(unsafe,td/'unsafe-out')
except RuntimeError: pass
else: raise AssertionError('ZIP traversal accepted')
symlink_zip=td/'symlink.zip'
with zipfile.ZipFile(symlink_zip,'w') as z:
    i=zipfile.ZipInfo('link');i.create_system=3;i.external_attr=(0o120777<<16);z.writestr(i,'target')
try: mod._safe_extract_runtime_zip(symlink_zip,td/'symlink-out')
except RuntimeError: pass
else: raise AssertionError('ZIP symlink accepted')

# Atomic runtime swap restores prior runtime on a failed final rename.
target=td/'runtime';staged=td/'runtime.new';old=td/'runtime.old'
target.mkdir();(target/'old.txt').write_text('old')
staged.mkdir();(staged/'new.txt').write_text('new')
real_replace=mod.os.replace;count={'n':0}
def flaky_replace(a,b):
    count['n']+=1
    if count['n']==2: raise OSError('simulated swap failure')
    return real_replace(a,b)
mod.os.replace=flaky_replace
try:
    try: mod._swap_runtime_directory(staged,target,old)
    except OSError: pass
    else: raise AssertionError('simulated swap failure did not propagate')
finally: mod.os.replace=real_replace
assert target.is_dir() and (target/'old.txt').is_file()

# Runtime provenance manifest is structured, checksum-addressed, and diagnostics-safe.
fake_ff=td/'ffmpeg';fake_ff.write_bytes(b'x')
caps=mod.Toolset(ffmpeg=fake_ff,ffprobe=fake_ff,version='ffmpeg test',filters={'subtitles'},encoders=['libx264'],score=1)
old_build=mod._ffmpeg_buildconf;mod._ffmpeg_buildconf=lambda ff:'--enable-test'
try:
    man=mod.build_ffmpeg_runtime_manifest({'sha256':expected,'publisher_sha256':expected},caps,source_url=mod.FFMPEG_URL,checksum_url=mod.FFMPEG_SHA256_URL)
finally: mod._ffmpeg_buildconf=old_build
assert man['provider']==mod.FFMPEG_PROVIDER and man['archive_sha256']==expected and man['publisher_sha256']==expected
assert man['checksum_url']==mod.FFMPEG_SHA256_URL and 'buildconf' in ''.join(man.keys())

mod.TRANSCRIPTION_MODEL_DIR=old_dir;mod.TRANSCRIPTION_MODEL_METADATA_CACHE=old_cache
shutil.rmtree(td,ignore_errors=True)
print('DEPENDENCY/PROVENANCE PASS')

# Controlled managed-FFmpeg install integration writes the manifest into the atomically-swapped runtime.
td2=pathlib.Path(tempfile.mkdtemp(prefix='subburn-ffmpeg-prov-'))
old_runtime_dir=mod.RUNTIME_DIR
old_download=mod._download_verified_archive
old_inspect=mod.inspect_toolset
old_buildconf=mod._ffmpeg_buildconf
mod.RUNTIME_DIR=td2/'runtime'
archive_payload=b'zip-placeholder';archive_sha=mod.hashlib.sha256(archive_payload).hexdigest()
def fake_download_verified(url,destination,progress=None,**kwargs):
    destination=pathlib.Path(destination)
    with zipfile.ZipFile(destination,'w') as z:
        z.writestr('ffmpeg-test/bin/ffmpeg.exe',b'ffmpeg')
        z.writestr('ffmpeg-test/bin/ffprobe.exe',b'ffprobe')
    actual=mod.full_file_sha256(destination)
    return {'path':str(destination),'sha256':actual,'publisher_sha256':actual}
def fake_inspect(path):
    path=pathlib.Path(path)
    return mod.Toolset(ffmpeg=path,ffprobe=path.with_name('ffprobe.exe'),version='ffmpeg controlled-test',filters={'subtitles','ass'},encoders=['libx264'],score=1)
mod._download_verified_archive=fake_download_verified
mod.inspect_toolset=fake_inspect
mod._ffmpeg_buildconf=lambda ff:'--enable-gpl --enable-libass controlled-test'
try:
    caps2=mod.download_private_ffmpeg(url='https://example.invalid/ffmpeg.zip',checksum_url='https://example.invalid/ffmpeg.zip.sha256')
    man2=mod.read_managed_ffmpeg_manifest(mod.RUNTIME_DIR/'ffmpeg')
    assert caps2.version=='ffmpeg controlled-test'
    assert man2['source_url']=='https://example.invalid/ffmpeg.zip'
    assert len(man2['archive_sha256'])==64 and man2['archive_sha256']==man2['publisher_sha256']
    assert 'controlled-test' in man2['ffmpeg_buildconf']
finally:
    mod.RUNTIME_DIR=old_runtime_dir
    mod._download_verified_archive=old_download
    mod.inspect_toolset=old_inspect
    mod._ffmpeg_buildconf=old_buildconf
    shutil.rmtree(td2,ignore_errors=True)
print('MANAGED FFMPEG PROVENANCE INTEGRATION PASS')
