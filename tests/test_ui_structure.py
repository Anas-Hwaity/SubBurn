import importlib.util,pathlib,re,sys,time,unittest
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py'
spec=importlib.util.spec_from_file_location('subburn_ui_wip07',SRC);mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
class UIStructure(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=mod.create_root();cls.app=mod.SubBurnApp(cls.root)
  for _ in range(20):cls.root.update();time.sleep(.01)
 @classmethod
 def tearDownClass(cls):
  try:cls.app.dashboard_server.shutdown()
  except:pass
  try:cls.app.system_usage_sampler.stop_event.set()
  except:pass
  try:cls.root.destroy()
  except:pass
 def test_workflow_pages_exact(self):self.assertEqual(list(self.app.workflow_pages),['Home','Subtitles','Watermark','Transcribe','Preview','Burn','Queue','Settings'])
 def test_metadata_hidden_by_default_and_toggle(self):
  self.assertFalse(self.app.metadata_visible);self.assertFalse(self.app.metadata_frame.winfo_ismapped());self.assertTrue(self.app.toggle_metadata_fields());self.root.update();self.assertTrue(self.app.metadata_visible);self.assertEqual(self.app.metadata_toggle_btn.cget('text'),'Hide optional metadata');self.app.toggle_metadata_fields()
 def test_subtitle_advanced_hidden_by_default_and_toggle(self):
  self.assertFalse(self.app.subtitle_advanced_visible)
  for f in self.app.subtitle_advanced_frames:self.assertFalse(f.winfo_ismapped())
  self.assertTrue(self.app.toggle_subtitle_advanced());self.root.update();self.assertEqual(self.app.subtitle_advanced_toggle_btn.cget('text'),'Hide advanced styling');self.app.toggle_subtitle_advanced()
 def test_global_progress_outside_burn(self):
  w=self.app.global_progress_bar;anc=[]
  while w is not None:
   anc.append(w)
   try:w=w.master
   except:break
  self.assertNotIn(self.app.page_encode,anc)
 def test_browser_progressive_disclosure(self):
  h=mod.DASHBOARD_HTML
  self.assertIn('<summary>Optional output metadata</summary>',h);self.assertIn('<summary>Advanced subtitle styling</summary>',h);self.assertIn('<summary>Advanced encoder diagnostics</summary>',h)
  self.assertEqual(re.findall(r'data-page-panel="([^"]+)"',h),['home','subtitles','watermark','transcribe','preview','burn','queue','settings'])
 def test_ffmpeg_file_or_folder_selection_contract(self):
  h=mod.DASHBOARD_HTML
  self.assertIn('FFmpeg file / folder',h)
  self.assertIn("(pickerKind==='folder'||pickerKind==='ffmpeg')",h)
  self.assertTrue(callable(getattr(self.app,'browse_ffmpeg_folder',None)))
  self.assertIn('PATH/system first',h)
 def test_browser_launcher_is_prominent_and_shortcut_bound(self):
  self.assertTrue(hasattr(self.app,'browser_launch_btn'))
  self.assertEqual(str(self.app.browser_launch_btn.cget('style')),'Accent.TButton')
  self.assertTrue(bool(self.root.bind_all('<Control-b>')))
 def test_runtime_download_widgets_show_byte_truth_not_setup_weight(self):
  op=self.app.op_state.begin('runtime_download',priority=999)
  try:
   self.app.op_state.stage(op,'Tools',100,'Local candidates checked')
   self.app.op_state.stage(op,'FFmpeg download',0,'Checking publisher checksum')
   self.app.tick_dashboard();self.root.update()
   self.assertEqual(getattr(self.app,'_global_progress_mode',None),'indeterminate')
   self.assertEqual(self.app.progress_status_var.get(),'Download: -')
   self.assertIn('Downloaded: 0.0 B / -',self.app.transfer_status_var.get())
   realistic_total=int(106.1*1024*1024); realistic_done=int(1.3*1024*1024); realistic_pct=realistic_done*100/realistic_total
   self.app.op_state.transfer(op,realistic_pct,realistic_done,realistic_total,2*1024*1024,52,'Downloading')
   self.app.tick_dashboard();self.root.update()
   self.assertAlmostEqual(float(self.app.progress_var.get()),round(realistic_pct,1),places=1)
   self.assertEqual(self.app.progress_status_var.get(),f'Download: {round(realistic_pct,1):.1f}%')
   self.assertIn('1.3 MiB / 106.1 MiB',self.app.transfer_status_var.get())
   self.app.op_state.transfer(op,50,53*1024*1024,106*1024*1024,14*1024*1024,3.8,'Downloading')
   self.app.tick_dashboard();self.root.update()
   self.assertEqual(float(self.app.progress_var.get()),50.0)
   self.assertEqual(self.app.progress_status_var.get(),'Download: 50.0%')
   self.assertIn('53.0 MiB / 106.0 MiB',self.app.transfer_status_var.get())
   self.assertIn('14.0 MiB/s',self.app.speed_status_var.get())
  finally:
   self.app.op_state.finish(op,'cancelled')
if __name__=='__main__':unittest.main(verbosity=2)
