import ast,pathlib,re,unittest
SRC=pathlib.Path(__file__).resolve().parents[1] / 'src' / 'subburn' / 'app.py';TEXT=SRC.read_text(encoding='utf-8')
EXPECTED_TK={'Add','Add fallback','Add font','Apply','Auto-detect','Benchmark','Browse','Browser-only mode','Browser dashboard  ↗','Burn video','Cancel','Cancel current','Cancel transcription','Clear projects','Clear folders','Center now','Close','Compare quality','Choose folder','Copy link','Copy log','Delete','Check / install FFmpeg','Edit','Export diagnostics','OK','Open file','Open folder','Open in browser','Open layout editor','Open safe-zone viewer','Pause','Pause after current','Play 8s clip','Prepare model','Preview','Preview selected boundary','Quick probe','Refresh','Refresh size','Remove fallback','Render frame','Reset image layout','Reset to 100%','Restore last autosave','Restore selected project','Resume','Save','Show advanced styling','Show optional metadata','Start / Resume queue','Transcribe current video','Use preset position','Use selected as output folder','Validate subtitles and fonts'}
EXPECTED_BROWSER={'Add current project','Add fallback','Add interval','Auto-detect FFmpeg','Browse','Burn','Burn video','Cancel','Cancel current','Clear completed','Clear projects','Clear folders','Compare quality','Copy log','Create preview','Check / install FFmpeg','Exit SubBurn','Export diagnostics','Full encoder benchmark','Hide desktop window','Home','Import selected font','Open folder','Open result','Pause','Pause after current','Play 8s inline','Prepare model','Preview','Queue','Quick encoder test','Refresh','Refresh installed fonts','Refresh recents','Render frame','Restore last autosave','Restore selected project','Resume','Retry failures','Roots','Save encoding settings','Save project settings','Save subtitle settings','Save watermark settings','Select this folder','Settings','Show desktop window','Start / resume','Subtitles','Transcribe','Transcribe video','Up','Use selected as output folder','Validate subtitles & fonts','Watermark'}
class C(unittest.TestCase):
 def test_tk_static_buttons_exact(self):
  tree=ast.parse(TEXT);found=set()
  for n in ast.walk(tree):
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Button':
    for kw in n.keywords:
     if kw.arg=='text':
      try:v=ast.literal_eval(kw.value)
      except:continue
      if isinstance(v,str):found.add(v)
  self.assertEqual(found,EXPECTED_TK)
 def test_browser_buttons_exact(self):
  labels=set()
  for m in re.finditer(r'<button([^>]*)>(.*?)</button>',TEXT,re.S|re.I):
   x=re.sub(r'<.*?>','',m.group(2)).strip()
   if x:labels.add(x)
  self.assertEqual(labels,EXPECTED_BROWSER)
 def test_dom_and_handlers_complete(self):
  a=TEXT.index('DASHBOARD_HTML = """');b=TEXT.index('"""\n\nclass DashboardHandler',a);h=TEXT[a:b]
  ids=set(re.findall(r'\bid="([^"]+)"',h));refs=set(re.findall(r'getElementById\([\'\"]([^\'\"]+)[\'\"]\)',h));self.assertEqual(refs-ids,set())
  funcs=set(re.findall(r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(',h));calls=set()
  for m in re.finditer(r'on(?:click|change|input|pointerup)="([^"]+)"',h):calls.update(f for f in re.findall(r'\b([A-Za-z_$][\w$]*)\s*\(',m.group(1)) if f not in {'if','confirm','setTimeout','Number','String','Math'})
  self.assertEqual(calls-funcs,set())
 def test_diagnostics_not_duplicated_in_tk(self):self.assertEqual(TEXT.count('text="Export diagnostics"'),1)
 def test_removed_features_absent(self):
  low=TEXT.casefold();self.assertNotIn('maximum compression',low);self.assertNotIn('automation_cli',TEXT)
if __name__=='__main__':unittest.main(verbosity=2)
