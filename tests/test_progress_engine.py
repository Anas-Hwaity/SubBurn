import importlib.util
import json
import pathlib
import queue
import sys
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec = importlib.util.spec_from_file_location('subburn_wip07_tested', SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class OperationStateTests(unittest.TestCase):
    def test_encode_monotonic_and_not_100_before_finish(self):
        o = mod.OperationState(); op = o.begin('encode')
        # Preparation has no honest denominator, so it stays indeterminate at 0.
        for phase,pct in [('Encode',3),('Subtitles',30),('Fonts',50),('Glyphs',40),('Filters',100),('Encoder',100)]:
            self.assertTrue(o.stage(op,phase,pct,phase))
            snap=o.snapshot(); self.assertEqual(snap['overall_pct'],0); self.assertEqual(snap['progress_mode'],'indeterminate')
        values=[]
        for pct in (0,10,50,100):
            o.stage(op,'Encode',pct,f'Encode {pct}')
            o.progress(op,pct,fps='30',speed='1x',eta='1s')
            values.append(o.snapshot()['overall_pct'])
        self.assertEqual(values, sorted(values)); self.assertEqual(values[-1],99.0)
        # Verification is real work but has no denominator: spinner, never fake 96/99% text.
        o.stage(op,'Verify',35,'Verifying output')
        self.assertEqual(o.snapshot()['progress_mode'],'indeterminate')
        self.assertLess(o.snapshot()['overall_pct'],100)
        o.finish(op,'succeeded')
        snap=o.snapshot(); self.assertEqual(snap['overall_pct'],100); self.assertEqual(snap['operation_state'],'succeeded')

    def test_terminal_state_is_immutable(self):
        o=mod.OperationState(); op=o.begin('preview'); o.stage(op,'Preview',50,'half')
        o.finish(op,'failed',error='boom')
        self.assertFalse(o.stage(op,'Preview',100,'late'))
        self.assertFalse(o.progress(op,100))
        self.assertFalse(o.finish(op,'succeeded'))
        self.assertEqual(o.state_of(op),'failed')

    def test_download_direct_progress_caps_at_99(self):
        o=mod.OperationState(); op=o.begin('runtime_download'); o.stage(op,'FFmpeg download',0,'Downloading')
        total=100
        for p in [0,5,25,75,100]: o.transfer(op,p,p,total,10,1,'Downloading')
        self.assertEqual(o.snapshot()['overall_pct'],99.0)
        o.finish(op,'succeeded'); self.assertEqual(o.snapshot()['overall_pct'],100.0); self.assertEqual(o.snapshot()['progress_pct'],100.0)

    def test_ffmpeg_transfer_reports_download_percent_separately_from_overall_setup(self):
        o=mod.OperationState(); op=o.begin('tool_discovery')
        o.stage(op,'Tools',100,'Local candidates checked')
        o.stage(op,'FFmpeg download',0,'Downloading')
        o.transfer(op,3.125,3_125_000,100_000_000,0,None,'Downloading FFmpeg runtime')
        snap=o.snapshot()
        self.assertEqual(snap['metric_profile'],'transfer')
        self.assertAlmostEqual(snap['transfer_pct'],3.1,places=1)
        self.assertEqual(snap['progress_pct'],3.1)
        self.assertAlmostEqual(snap['overall_pct'],3.1,places=1)
        self.assertLess(snap['overall_pct'],100.0)
        self.assertNotEqual(snap['progress_pct'],37.0)

    def test_transfer_profile_ends_when_install_phase_begins(self):
        o=mod.OperationState(); op=o.begin('runtime_download')
        o.stage(op,'FFmpeg download',0,'Downloading')
        o.transfer(op,100,100,100,10,0,'Downloaded')
        self.assertEqual(o.snapshot()['metric_profile'],'transfer')
        o.stage(op,'FFmpeg install',20,'Extracting')
        self.assertEqual(o.snapshot()['metric_profile'],'basic')
        self.assertLess(o.snapshot()['overall_pct'],100)

    def test_transcription_maps_direct_progress(self):
        o=mod.OperationState(); op=o.begin('transcription')
        o.progress(op,0); self.assertEqual(o.snapshot()['overall_pct'],0.0)
        o.progress(op,50); self.assertAlmostEqual(o.snapshot()['overall_pct'],49.5,places=1)
        o.progress(op,100); self.assertEqual(o.snapshot()['overall_pct'],99.0)

    def test_indeterminate_operation_does_not_fake_percentage(self):
        o=mod.OperationState(); op=o.begin('font_scan')
        snap=o.snapshot(); self.assertEqual(snap['progress_mode'],'indeterminate'); self.assertEqual(snap['overall_pct'],0)
        o.stage(op,'Fonts',90,'Scanning'); self.assertEqual(o.snapshot()['overall_pct'],0)
        o.finish(op,'succeeded'); self.assertEqual(o.snapshot()['overall_pct'],100)

    def test_priority_prevents_background_operation_from_stealing_foreground(self):
        o=mod.OperationState(); foreground=o.begin('encode'); bg=o.begin('font_scan')
        self.assertEqual(o.snapshot()['operation_id'],foreground)
        o.finish(foreground,'succeeded')
        self.assertEqual(o.snapshot()['operation_id'],bg)


    def test_background_completion_cannot_mark_foreground_complete(self):
        o=mod.OperationState(); foreground=o.begin('runtime_download'); bg=o.begin('font_scan')
        self.assertEqual(o.snapshot()['operation_id'],foreground)
        o.transfer(foreground,35,35,100,10,6.5,'Downloading FFmpeg runtime')
        o.finish(bg,'succeeded')
        snap=o.snapshot()
        self.assertEqual(snap['operation_id'],foreground)
        self.assertEqual(snap['operation_state'],'running')
        self.assertEqual(snap['status'],'Running')
        self.assertLess(snap['overall_pct'],100)
        o.finish(foreground,'succeeded')
        self.assertEqual(o.snapshot()['status'],'Complete')

    def test_batch_child_encode_returns_to_batch(self):
        o=mod.OperationState(); batch=o.begin('batch'); o.set_overall(batch,30,'1/3')
        child=o.begin('encode',priority=100); self.assertEqual(o.snapshot()['operation_id'],child)
        o.stage(child,'Encode',50,'encoding'); o.finish(child,'succeeded')
        self.assertEqual(o.snapshot()['operation_id'],batch)
        self.assertEqual(o.snapshot()['overall_pct'],30)
        o.set_overall(batch,66,'2/3'); self.assertEqual(o.snapshot()['overall_pct'],66)
        o.finish(batch,'succeeded'); self.assertEqual(o.snapshot()['overall_pct'],100)

    def test_paused_batch_is_terminal_for_that_run_segment(self):
        o=mod.OperationState(); op=o.begin('batch'); o.set_overall(op,40); o.finish(op,'paused')
        self.assertEqual(o.state_of(op),'paused'); self.assertEqual(o.snapshot()['overall_pct'],40)
        newer=o.begin('batch'); self.assertEqual(o.snapshot()['operation_id'],newer)

    def test_snapshot_json_serializable(self):
        o=mod.OperationState(); op=o.begin('preview'); o.stage(op,'Preview',25,'rendering')
        json.dumps(o.snapshot())

class AppProgressAdapterTests(unittest.TestCase):
    def app_shell(self):
        app=mod.SubBurnApp.__new__(mod.SubBurnApp)
        app._operation_local=mod.threading.local(); app.op_state=mod.OperationState(); app.events=queue.Queue()
        return app

    def test_emit_error_fails_current_operation(self):
        app=self.app_shell(); op=app.begin_operation('preview'); app._operation_local.operation_id=op
        app.emit('error','bad')
        self.assertEqual(app.op_state.state_of(op),'failed')

    def test_emit_done_succeeds_current_operation(self):
        app=self.app_shell(); op=app.begin_operation('encode'); app._operation_local.operation_id=op
        app.emit('done','x.mp4')
        snap=app.op_state.operation_snapshot(op); self.assertEqual(snap['state'],'succeeded'); self.assertEqual(snap['overall_pct'],100)

    def test_transfer_progress_adapter_matches_operation_state_signature(self):
        app=self.app_shell(); op=app.begin_operation('runtime_download'); app._operation_local.operation_id=op
        app.emit('transfer_progress',35.0,35*1024*1024,100*1024*1024,2.5*1024*1024,26.0,'Downloading FFmpeg runtime')
        snap=app.op_state.operation_snapshot(op)
        self.assertEqual(snap['bytes_done'],35*1024*1024)
        self.assertEqual(snap['bytes_total'],100*1024*1024)
        self.assertEqual(snap['speed'],'2.5 MiB/s')
        self.assertIn('35.0 MiB / 100.0 MiB',snap['downloaded'])
        self.assertLess(snap['overall_pct'],100)

    def test_finish_result_does_not_override_prior_failure(self):
        app=self.app_shell(); op=app.begin_operation('preview'); app.finish_operation(op,'failed',error='bad')
        app._finish_operation_from_result(op,True)
        self.assertEqual(app.op_state.state_of(op),'failed')

    def test_cancelled_result(self):
        app=self.app_shell(); op=app.begin_operation('preview'); app._finish_operation_from_result(op,False)
        self.assertEqual(app.op_state.state_of(op),'cancelled')

if __name__ == '__main__':
    unittest.main(verbosity=2)
