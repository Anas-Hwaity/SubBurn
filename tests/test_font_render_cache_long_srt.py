from __future__ import annotations
import importlib.util, pathlib, sys, tempfile, time
from types import SimpleNamespace

SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_font_cache_long_srt',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

class Var:
    def __init__(self,v=None): self.v=v
    def get(self): return self.v
    def set(self,v): self.v=v

with tempfile.TemporaryDirectory(prefix='subburn-font-cache-') as raw:
    root=pathlib.Path(raw)
    font_path=root/'primary.ttf'; font_path.write_bytes(b'font')
    primary=mod.FontRecord('Primary',font_path,'Primary','Primary','test',set(range(32,0x700)))
    # Mirror the user's Windows machine (~351 fonts). Only the primary needs the sample glyphs;
    # the point is to prove candidate ordering is not rebuilt for every grapheme.
    system_fonts=[primary]
    for i in range(350):
        fp=root/f'system-{i:03d}.ttf'; fp.write_bytes(b'font')
        system_fonts.append(mod.FontRecord(f'System {i}',fp,f'System {i}',f'System {i}','test',set()))
    app=object.__new__(mod.SubBurnApp)
    app._job_local=mod.threading.local()
    app._job=SimpleNamespace(
        wrap_chars='0',max_lines='0',font_size='28',force_bold=False,italic=False,underline=False,strikeout=False,
        text_rgb='FFFFFF',text_opacity='100',outline_rgb='000000',outline_opacity='100',outline='2',shadow_rgb='000000',
        shadow_opacity='100',shadow_depth='0',letter_spacing='0',rotation_angle='0',subtitle_alignment='Bottom center',
        margin_left='10',margin_right='10',margin='24',safe_area='8',background_box=False,background_rgb='000000',
        background_opacity='65',background_padding='4',caption_effect_id='none',caption_effect_params={'active_rgb':'FFD400','allow_estimated_timing':True},
        subtitle_file='',subtitle_offset='0',primary_font='Primary',same_wm_font=True,wm_font='',watermark_enabled=False,
    )
    app.fonts=system_fonts; app.media=SimpleNamespace(width=1280,height=720,display_width=1280,display_height=720,duration=3600)
    app.fallback_fonts=lambda: []
    app.copy_render_font=lambda rec,fonts_dir: pathlib.Path(fonts_dir)/'font.ttf'
    app.prepared_font_path=lambda rec: rec.path
    app.font_glyph_has_ink=lambda rec,cp: False if cp==32 else True
    app.log=lambda *a,**k: None
    app.set_stage=lambda *a,**k: None

    # Candidate ordering must be built once for an entire long render, not once per grapheme.
    original=app.render_font_candidates
    calls={'n':0}
    def counted(configured):
        calls['n']+=1
        return original(configured)
    app.render_font_candidates=counted

    srt=root/'long.srt'
    rows=[]
    for i in range(1,2501):
        a=(i-1)*1.2; b=a+1.0
        def ts(x):
            h=int(x//3600);m=int((x%3600)//60);sec=int(x%60);ms=int(round((x-int(x))*1000))
            return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'
        rows += [str(i),f'{ts(a)} --> {ts(b)}','Hello مرحبا 123','']
    srt.write_text('\n'.join(rows),encoding='utf-8')
    fonts_dir=root/'fonts'; fonts_dir.mkdir()
    start=time.perf_counter(); out=app.prepare_universal_ass(root,srt,fonts_dir,primary); elapsed=time.perf_counter()-start
    assert out and out.is_file()
    assert calls['n']==1, f'candidate ordering rebuilt {calls["n"]} times'
    # This is intentionally loose; the regression being guarded is multi-minute preparation.
    assert elapsed < 8.0, f'long repeated-cue ASS preparation took {elapsed:.2f}s'
    text=out.read_text('utf-8')
    assert text.count('Dialogue:')==2500

print('LONG-SRT FONT RESOLUTION CACHE PASS')
