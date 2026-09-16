import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import threading
import time

SRC = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec = importlib.util.spec_from_file_location('subburn_transcription_stress', SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

MODELS = tuple(mod.TRANSCRIPTION_MODELS)
assert MODELS == ('large-v3', 'turbo', 'medium', 'small', 'base', 'tiny') or list(MODELS) == ['large-v3', 'turbo', 'medium', 'small', 'base', 'tiny']
assert set(MODELS) == set(mod.TRANSCRIPTION_MODEL_SOURCES)
assert len({mod.transcription_model_repo(m) for m in MODELS}) == len(MODELS)
for model in MODELS:
    source = mod.transcription_model_source(model)
    assert len(source['revision']) == 40 and all(c in '0123456789abcdef' for c in source['revision'])
    assert source['license'] == 'MIT'

root = pathlib.Path(tempfile.mkdtemp(prefix='subburn-transcription-stress-'))
old_model_dir = mod.TRANSCRIPTION_MODEL_DIR
old_download = mod._huggingface_snapshot_download
old_metadata = mod.transcription_model_metadata
mod.TRANSCRIPTION_MODEL_DIR = root / 'models'

calls = []
calls_lock = threading.Lock()

def write_valid_snapshot(local_dir, *, slow=False):
    d = pathlib.Path(local_dir)
    d.mkdir(parents=True, exist_ok=True)
    # Exactly 1000 bytes so known-total progress can be asserted precisely.
    (d / 'config.json').write_bytes(b'c' * 10)
    (d / 'tokenizer.json').write_bytes(b't' * 10)
    (d / 'vocabulary.json').write_bytes(b'v' * 10)
    model = d / 'model.bin'
    if slow:
        with model.open('wb') as f:
            for _ in range(5):
                f.write(b'm' * 194)
                f.flush()
                try:
                    import os
                    os.fsync(f.fileno())
                except Exception:
                    pass
                time.sleep(0.23)
    else:
        model.write_bytes(b'm' * 970)
    assert mod.directory_size_bytes(d) == 1000


def fake_download(**kwargs):
    repo = kwargs['repo_id']; revision = kwargs['revision']; local_dir = kwargs['local_dir']
    model = next(m for m in MODELS if mod.transcription_model_repo(m) == repo)
    assert revision == mod.transcription_model_revision(model)
    assert set(kwargs.get('allow_patterns') or ()) == set(mod.TRANSCRIPTION_MODEL_ALLOW_PATTERNS)
    with calls_lock:
        calls.append((model, repo, revision, str(local_dir)))
    # Long enough that the duplicate caller for the same model overlaps the lock.
    time.sleep(0.06)
    write_valid_snapshot(local_dir)
    return str(local_dir)


def fake_metadata(model_name, refresh=False, timeout=8.0, online=True):
    return {
        'model': model_name,
        'download_bytes': 1000,
        'download_size_source': 'pinned-revision',
        'ready': mod.transcription_model_ready(model_name),
    }

mod._huggingface_snapshot_download = fake_download
mod.transcription_model_metadata = fake_metadata

try:
    # 1) Stress: two concurrent callers for every model. Exactly one underlying download/model.
    results = []
    errors = []
    def worker(model):
        try:
            results.append((model, mod.prepare_transcription_model_snapshot(model)))
        except Exception as exc:
            errors.append((model, exc))

    threads = []
    for model in MODELS:
        threads.extend([threading.Thread(target=worker, args=(model,)) for _ in range(2)])
    for t in threads: t.start()
    for t in threads: t.join(20)
    assert all(not t.is_alive() for t in threads), 'transcription model prepare thread timeout'
    assert not errors, errors
    assert len(results) == 12
    assert len(calls) == 6, calls
    assert sorted(m for m, *_ in calls) == sorted(MODELS)

    # Every model must have its own valid directory + exact immutable marker.
    install_dirs = set()
    for model in MODELS:
        target = mod.transcription_model_install_dir(model)
        install_dirs.add(str(target))
        assert mod.transcription_model_ready(model), model
        marker = json.loads(mod.transcription_model_marker(model).read_text(encoding='utf-8'))
        source = mod.transcription_model_source(model)
        assert marker['model'] == model
        assert marker['repo'] == source['repo']
        assert marker['revision'] == source['revision']
        assert marker['license'] == source['license']
        assert marker['installed_bytes'] == 1000
    assert len(install_dirs) == 6

    # 2) Download once means once: every second prepare must work with network hard-disabled.
    def forbidden_download(**kwargs):
        raise AssertionError('prepared transcription model attempted a second network download')
    mod._huggingface_snapshot_download = forbidden_download
    for model in MODELS:
        before = mod.transcription_model_install_dir(model)
        got = mod.prepare_transcription_model_snapshot(model)
        assert got == before and mod.transcription_model_ready(model)

    # 3) A stale marker can never masquerade as the pinned revision.
    stale_model = 'tiny'
    marker_path = mod.transcription_model_marker(stale_model)
    stale = json.loads(marker_path.read_text(encoding='utf-8'))
    stale['revision'] = '0' * 40
    marker_path.write_text(json.dumps(stale), encoding='utf-8')
    assert not mod.transcription_model_ready(stale_model)

    # Re-preparing stale provenance performs one exact pinned download and repairs marker.
    stale_calls = []
    def repair_download(**kwargs):
        stale_calls.append((kwargs['repo_id'], kwargs['revision']))
        write_valid_snapshot(kwargs['local_dir'])
        return kwargs['local_dir']
    mod._huggingface_snapshot_download = repair_download
    mod.prepare_transcription_model_snapshot(stale_model)
    assert len(stale_calls) == 1
    assert stale_calls[0] == (mod.transcription_model_repo(stale_model), mod.transcription_model_revision(stale_model))
    assert mod.transcription_model_ready(stale_model)

    # 4) Interrupted staging is cleaned; retry installs cleanly and only the retry becomes ready.
    interrupted = 'base'
    shutil.rmtree(mod.transcription_model_install_dir(interrupted), ignore_errors=True)
    mod.transcription_model_marker(interrupted).unlink(missing_ok=True)
    interruption_calls = {'n': 0}
    def interrupted_download(**kwargs):
        interruption_calls['n'] += 1
        d = pathlib.Path(kwargs['local_dir']); d.mkdir(parents=True, exist_ok=True)
        (d / 'config.json').write_text('{}', encoding='utf-8')
        (d / 'model.bin').write_bytes(b'partial')
        raise RuntimeError('simulated network interruption')
    mod._huggingface_snapshot_download = interrupted_download
    try:
        mod.prepare_transcription_model_snapshot(interrupted)
        raise AssertionError('interrupted model preparation unexpectedly succeeded')
    except RuntimeError as exc:
        assert 'simulated network interruption' in str(exc)
    assert not mod.transcription_model_ready(interrupted)
    assert not mod.transcription_model_install_dir(interrupted).with_name(interrupted + '.new').exists()

    retry_calls = {'n': 0}
    def retry_download(**kwargs):
        retry_calls['n'] += 1
        write_valid_snapshot(kwargs['local_dir'])
        return kwargs['local_dir']
    mod._huggingface_snapshot_download = retry_download
    mod.prepare_transcription_model_snapshot(interrupted)
    assert retry_calls['n'] == 1 and interruption_calls['n'] == 1
    assert mod.transcription_model_ready(interrupted)

    # 5) Known-total progress is monotonic and finishes at the actual installed byte total.
    progress_model = 'small'
    shutil.rmtree(mod.transcription_model_install_dir(progress_model), ignore_errors=True)
    mod.transcription_model_marker(progress_model).unlink(missing_ok=True)
    progress_samples = []
    def slow_download(**kwargs):
        write_valid_snapshot(kwargs['local_dir'], slow=True)
        return kwargs['local_dir']
    mod._huggingface_snapshot_download = slow_download
    mod.transcription_model_metadata = fake_metadata
    mod.prepare_transcription_model_snapshot(progress_model, progress=lambda done,total: progress_samples.append((int(done),int(total))))
    assert len(progress_samples) >= 3, progress_samples
    dones = [x[0] for x in progress_samples]
    assert dones == sorted(dones), progress_samples
    assert all(total == 1000 for _, total in progress_samples), progress_samples
    assert progress_samples[-1] == (1000, 1000), progress_samples[-1]
    assert mod.transcription_model_ready(progress_model)

    # 6) Rapid model switching/readiness queries cannot bleed state between models.
    for _ in range(20):
        for model in reversed(MODELS):
            assert mod.transcription_model_ready(model), model
            source = mod.transcription_model_source(model)
            marker = json.loads(mod.transcription_model_marker(model).read_text(encoding='utf-8'))
            assert marker['repo'] == source['repo'] and marker['revision'] == source['revision']

    # 7) Simulate a full application restart: a fresh interpreter must reuse every prepared model
    # with the downloader hard-disabled. This proves the install-once contract is durable on disk,
    # instead of relying on process-memory state.
    import subprocess
    restart_code = f'''
import importlib.util, pathlib, sys
src=pathlib.Path({str(SRC)!r})
spec=importlib.util.spec_from_file_location("subburn_transcription_restart",src)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.TRANSCRIPTION_MODEL_DIR=pathlib.Path({str(mod.TRANSCRIPTION_MODEL_DIR)!r})
def forbidden(**kwargs):
    raise AssertionError("restart attempted a second transcription-model download")
m._huggingface_snapshot_download=forbidden
for name in {list(MODELS)!r}:
    assert m.transcription_model_ready(name), name
    got=m.prepare_transcription_model_snapshot(name)
    assert got == m.transcription_model_install_dir(name), (name, got)
print("TRANSCRIPTION CROSS-PROCESS RESTART REUSE PASS")
'''
    restart = subprocess.run([sys.executable, '-c', restart_code], text=True, capture_output=True, timeout=30)
    assert restart.returncode == 0, restart.stdout + restart.stderr
    assert 'CROSS-PROCESS RESTART REUSE PASS' in restart.stdout

    print('TRANSCRIPTION 6-MODEL INSTALL-ONCE / CONCURRENCY / RECOVERY / PROGRESS / RESTART STRESS PASS')
finally:
    mod.TRANSCRIPTION_MODEL_DIR = old_model_dir
    mod._huggingface_snapshot_download = old_download
    mod.transcription_model_metadata = old_metadata
    shutil.rmtree(root, ignore_errors=True)
