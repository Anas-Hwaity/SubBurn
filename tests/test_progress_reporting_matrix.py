from __future__ import annotations
import importlib.util, pathlib, sys

SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_progress_matrix',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

EXPECTED={
 'tool_discovery','runtime_download','font_scan','media_analysis','validation',
 'encoder_probe','encoder_benchmark','preview','live_frame','live_clip',
 'quality_compare','encode','transcription_model_prepare','transcription','batch','ffmpeg_inspect'
}
actual=set(mod.OPERATION_SPECS)-{'generic'}
assert actual==EXPECTED, f'progress matrix missing/extra operation kinds: expected={sorted(EXPECTED)} actual={sorted(actual)}'

# Every feature gets start/failure/cancel/success/stale-event acceptance. This intentionally
# fails when a new operation kind is added without extending this matrix.
for kind in sorted(EXPECTED):
    state=mod.OperationState(); op=state.begin(kind)
    start=state.operation_snapshot(op)
    assert start['state']=='running' and start['overall_pct']==0 and start['progress_pct']==0, (kind,start)
    # A running operation may report a stage/message but can never claim success.
    state.stage(op,'Starting',0,f'{kind} starting')
    running=state.operation_snapshot(op)
    assert running['state']=='running' and running['progress_pct']<100, (kind,running)

    # Failure path.
    fail=mod.OperationState(); fop=fail.begin(kind); fail.stage(fop,'Starting',0,'starting'); fail.finish(fop,'failed',error='simulated failure')
    fs=fail.operation_snapshot(fop); assert fs['state']=='failed' and fs['progress_pct']<100, (kind,fs)
    before=dict(fs); assert fail.progress(fop,90) is False; assert fail.operation_snapshot(fop)==before, kind

    # Cancellation path.
    cancel=mod.OperationState(); cop=cancel.begin(kind); cancel.stage(cop,'Starting',0,'starting'); cancel.finish(cop,'cancelled')
    cs=cancel.operation_snapshot(cop); assert cs['state']=='cancelled' and cs['progress_pct']<100, (kind,cs)

    # Success is the only path allowed to expose 100%.
    state.finish(op,'succeeded'); done=state.operation_snapshot(op)
    assert done['state']=='succeeded' and done['overall_pct']==100 and done['progress_pct']==100, (kind,done)

# Transfer truth at realistic FFmpeg numbers: 1.3 / 106.1 MiB must be ~1.2%, never 0 or 5.
state=mod.OperationState(); op=state.begin('runtime_download')
state.stage(op,'FFmpeg download',0,'Downloading')
total=int(106.1*1024*1024); done=int(1.3*1024*1024); pct=done*100/total
state.transfer(op,pct,done,total,2.0*1024*1024,(total-done)/(2.0*1024*1024),'Downloading')
s=state.operation_snapshot(op)
assert 1.1 <= s['transfer_pct'] <= 1.3, s
assert s['progress_pct']==s['transfer_pct'], s
assert s['downloaded'].startswith('1.3 MiB / 106.1 MiB'), s
assert s['speed']=='2.0 MiB/s' and s['eta']!='-', s

# Transfer can reach exact 100 while operation remains running below 100 pending verification.
state.transfer(op,100,total,total,3*1024*1024,0,'Archive received')
s=state.operation_snapshot(op)
assert s['transfer_pct']==100 and s['progress_pct']==99 and s['state']=='running', s
state.finish(op,'succeeded'); assert state.operation_snapshot(op)['progress_pct']==100

# Background work cannot steal or complete a foreground operation.
state=mod.OperationState(); fg=state.begin('encode'); bg=state.begin('font_scan')
assert state.snapshot()['operation_id']==fg
state.finish(bg,'succeeded'); assert state.snapshot()['operation_id']==fg and state.snapshot()['operation_state']=='running'

print('EXHAUSTIVE PROGRESS REPORTING MATRIX PASS:', ', '.join(sorted(EXPECTED)))

# Truthfulness classification: stage-only work is indeterminate; only a real denominator may
# turn the bar determinate.
INDETERMINATE_STAGE_ONLY={'tool_discovery','runtime_download','font_scan','media_analysis','validation','encoder_probe','encoder_benchmark','preview','live_frame','live_clip','encode','transcription_model_prepare','transcription','ffmpeg_inspect'}
for kind in sorted(INDETERMINATE_STAGE_ONLY):
    st=mod.OperationState(); oid=st.begin(kind); st.stage(oid,'Synthetic stage',73,'stage text only')
    snap=st.operation_snapshot(oid)
    assert snap['mode']=='indeterminate' and snap['overall_pct']==0, (kind,snap)

# Real media-duration callbacks make preview/encode/transcription determinate and byte/job-count
# callbacks do likewise for their own operations.
for kind in ('preview','encode','transcription'):
    st=mod.OperationState(); oid=st.begin(kind); st.progress(oid,50,fps='30',speed='1.0x',eta='00:10')
    snap=st.operation_snapshot(oid)
    assert snap['mode']=='determinate' and 49.4 <= snap['progress_pct'] <= 49.6, (kind,snap)

for kind in ('encoder_probe','encoder_benchmark','batch','quality_compare'):
    st=mod.OperationState(); oid=st.begin(kind); st.set_overall(oid,50,'real completed-unit fraction')
    snap=st.operation_snapshot(oid); assert snap['mode']=='determinate' and snap['progress_pct']==50, (kind,snap)

print('PROGRESS TRUTHFULNESS CLASSIFICATION PASS')

# Feature-realistic progress traces. Each operation kind is driven through the same kind of
# denominator its production worker uses; operations with no honest denominator must stay
# indeterminate rather than displaying invented stage percentages.
def trace(kind):
    st=mod.OperationState(); oid=st.begin(kind)
    if kind=='tool_discovery':
        st.stage(oid,'Tools',10,'Checking installed FFmpeg')
    elif kind=='runtime_download':
        st.stage(oid,'FFmpeg download',0,'Downloading FFmpeg runtime')
        total=106*1024*1024; st.transfer(oid,25,25*1024*1024,total,4*1024*1024,20.25,'Downloading FFmpeg runtime')
    elif kind=='font_scan':
        st.stage(oid,'Fonts',50,'Scanning installed fonts')
    elif kind=='media_analysis':
        st.stage(oid,'Media',95,'Reading streams and metadata')
    elif kind=='validation':
        st.stage(oid,'Glyphs',40,'Checking glyph coverage')
    elif kind=='encoder_probe':
        st.stage(oid,'Encoder',0,'Testing libx264 (1/4)'); st.set_overall(oid,24.75,'Tested 1/4 encoders')
    elif kind=='encoder_benchmark':
        st.stage(oid,'Encoder',0,'Benchmarking libx264 (2/4)'); st.set_overall(oid,49.5,'Benchmarked 2/4 encoders')
    elif kind=='preview':
        st.stage(oid,'Preview',35,'Rendering preview'); st.progress(oid,40,fps='52.0',speed='2.1x',eta='00:03')
    elif kind=='live_frame':
        st.stage(oid,'Preview',45,'Rendering frame')
    elif kind=='live_clip':
        st.stage(oid,'Preview',0,'Rendering playback preview'); st.progress(oid,50,fps='60.0',speed='3.0x',eta='00:01')
    elif kind=='quality_compare':
        st.set_overall(oid,50,'Rendering comparison 2 of 4')
    elif kind=='encode':
        st.stage(oid,'Encode',10,'Launching FFmpeg'); st.progress(oid,55,fps='72.0',speed='2.4x',eta='00:14')
    elif kind=='transcription_model_prepare':
        st.stage(oid,'Model download',0,'Downloading turbo transcription model'); total=1600*1024*1024; st.transfer(oid,12.5,200*1024*1024,total,20*1024*1024,70,'Downloading model')
    elif kind=='transcription':
        st.progress(oid,62.5,fps='-',speed='-',eta='-')
    elif kind=='batch':
        st.set_overall(oid,60,'3 of 5 jobs complete')
    elif kind=='ffmpeg_inspect':
        st.stage(oid,'Inspect',60,'Inspecting selected FFmpeg')
    else:
        raise AssertionError(kind)
    return st,oid,st.operation_snapshot(oid)

DETERMINATE={'runtime_download','encoder_probe','encoder_benchmark','preview','live_clip','quality_compare','encode','transcription_model_prepare','transcription','batch'}
for kind in sorted(EXPECTED):
    st,oid,snap=trace(kind)
    if kind in DETERMINATE:
        assert snap['mode']=='determinate', (kind,snap)
        assert 0 < snap['progress_pct'] < 100, (kind,snap)
    else:
        assert snap['mode']=='indeterminate', (kind,snap)
        assert snap['progress_pct']==0, (kind,snap)
    if kind in {'runtime_download','transcription_model_prepare'}:
        assert snap['metric_profile']=='transfer' and snap['bytes_done']>0 and snap['bytes_total']>snap['bytes_done'], (kind,snap)
        assert snap['speed']!='-' and snap['eta']!='-', (kind,snap)
    if kind in {'preview','live_clip','encode'}:
        assert snap['metric_profile']=='media' and snap['fps']!='-' and snap['speed']!='-' and snap['eta']!='-', (kind,snap)

print('FEATURE-REALISTIC PROGRESS TRACE MATRIX PASS')

# A transfer that stops receiving bytes must not keep advertising a stale non-zero speed/ETA.
st=mod.OperationState(); oid=st.begin('runtime_download'); st.stage(oid,'FFmpeg download',0,'Downloading')
st.transfer(oid,10,10,100,50,1.8,'Downloading')
with st.lock:
    st.operations[oid]['transfer_updated'] = mod.time.monotonic()-4.0
snap=st.operation_snapshot(oid)
assert snap['transfer_stalled'] is True and snap['speed']=='0.0 B/s' and snap['eta']=='-', snap
assert snap['transfer_pct']==10.0 and snap['downloaded'].startswith('10.0 B / 100.0 B'), snap
print('STALE TRANSFER SPEED TRUTHFULNESS PASS')
