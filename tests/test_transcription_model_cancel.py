from __future__ import annotations
import importlib.util, pathlib, shutil, sys, tempfile, threading, time

SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_transcription_cancel',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

root=pathlib.Path(tempfile.mkdtemp(prefix='subburn-model-cancel-'))
old_dir=mod.TRANSCRIPTION_MODEL_DIR
old_helper=mod._huggingface_snapshot_download_cancellable
mod.TRANSCRIPTION_MODEL_DIR=root/'models'
try:
    # Real child-process cancellation primitive: cancellation must terminate promptly rather
    # than waiting for the helper command's long sleep to finish.
    stage=root/'child-stage'; cancel=threading.Event(); errors=[]
    child_code=(
        "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); p.mkdir(parents=True,exist_ok=True); "
        "(p/'partial.bin').write_bytes(b'x'*100); time.sleep(30)"
    )
    def child_worker():
        try:
            mod._huggingface_snapshot_download_cancellable(
                mod.transcription_model_source('tiny'), stage, cancel, poll_interval=0.03,
                _command=[sys.executable,'-c',child_code,str(stage)],
            )
        except Exception as exc:
            errors.append(exc)
    th=threading.Thread(target=child_worker); th.start()
    deadline=time.time()+5
    while time.time()<deadline and not (stage/'partial.bin').is_file(): time.sleep(0.02)
    assert (stage/'partial.bin').is_file(), 'child download fixture never started'
    started=time.monotonic(); cancel.set(); th.join(4)
    assert not th.is_alive(), 'cancelled model helper remained alive'
    assert time.monotonic()-started < 3.0
    assert len(errors)==1 and isinstance(errors[0],mod.TranscriptionModelPreparationCancelled),errors

    # prepare_transcription_model_snapshot must discard partial staging and never write ready state.
    def cancelled_helper(source,local_dir,cancel_event,**kwargs):
        d=pathlib.Path(local_dir);d.mkdir(parents=True,exist_ok=True);(d/'model.bin').write_bytes(b'partial')
        raise mod.TranscriptionModelPreparationCancelled('test cancellation')
    mod._huggingface_snapshot_download_cancellable=cancelled_helper
    event=threading.Event()
    try:
        mod.prepare_transcription_model_snapshot('tiny',cancel_event=event)
    except mod.TranscriptionModelPreparationCancelled:
        pass
    else:
        raise AssertionError('cancelled model preparation unexpectedly succeeded')
    target=mod.transcription_model_install_dir('tiny')
    assert not target.exists() and not target.with_name(target.name+'.new').exists()
    assert not mod.transcription_model_marker('tiny').exists() and not mod.transcription_model_ready('tiny')

    # Cancellation cannot poison the per-model install lock. A waiting sibling caller retries
    # after the cancelled owner and becomes the sole installed ready snapshot.
    calls=[]; first_entered=threading.Event(); release_first=threading.Event()
    def valid_snapshot(d):
        d=pathlib.Path(d);d.mkdir(parents=True,exist_ok=True)
        (d/'config.json').write_text('{}',encoding='utf-8');(d/'tokenizer.json').write_text('{}',encoding='utf-8')
        (d/'vocabulary.txt').write_text('x',encoding='utf-8');(d/'model.bin').write_bytes(b'model')
    def racing_helper(source,local_dir,cancel_event,**kwargs):
        calls.append(id(cancel_event))
        if len(calls)==1:
            first_entered.set(); release_first.wait(5)
            raise mod.TranscriptionModelPreparationCancelled('owner cancelled')
        valid_snapshot(local_dir); return str(local_dir)
    mod._huggingface_snapshot_download_cancellable=racing_helper
    a_event=threading.Event();b_event=threading.Event();results=[];errs=[]
    def prepare(ev,label):
        try: results.append((label,mod.prepare_transcription_model_snapshot('base',cancel_event=ev)))
        except Exception as exc: errs.append((label,exc))
    a=threading.Thread(target=prepare,args=(a_event,'a'));b=threading.Thread(target=prepare,args=(b_event,'b'))
    a.start(); assert first_entered.wait(3); b.start(); time.sleep(0.1); a_event.set(); release_first.set()
    a.join(5); b.join(5)
    assert not a.is_alive() and not b.is_alive()
    assert any(label=='a' and isinstance(exc,mod.TranscriptionModelPreparationCancelled) for label,exc in errs),errs
    assert any(label=='b' for label,_ in results),results
    assert len(calls)==2,calls
    assert mod.transcription_model_ready('base')
    assert not mod.transcription_model_install_dir('base').with_name('base.new').exists()

    print('TRANSCRIPTION MODEL CANCELLATION / CLEANUP / LOCK RECOVERY PASS')
finally:
    mod.TRANSCRIPTION_MODEL_DIR=old_dir
    mod._huggingface_snapshot_download_cancellable=old_helper
    shutil.rmtree(root,ignore_errors=True)
