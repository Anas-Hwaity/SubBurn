from __future__ import annotations
import importlib.util, pathlib, sys, tempfile
from types import SimpleNamespace
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_text_watermark_single_pass',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory(prefix='subburn-one-pass-') as raw:
    td=pathlib.Path(raw); fonts=td/'fonts'; fonts.mkdir(); sub=td/'input.srt'; sub.write_text('1\n00:00:00,000 --> 00:00:01,000\nX\n','utf-8')
    subtitle_ass=td/'subtitle_render.ass'; subtitle_ass.write_text('''[Script Info]\nScriptType: v4.00+\nPlayResX: 1280\nPlayResY: 720\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Arial,30,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,20,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,SUB\n''','utf-8')
    wm_ass=td/'watermark_text_render.ass'; wm_ass.write_text('''[Script Info]\nScriptType: v4.00+\nPlayResX: 1280\nPlayResY: 720\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Watermark,Aljazeera,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\nDialogue: 0,0:00:00.00,0:01:00.00,Watermark,,0,0,0,,WM\n''','utf-8')
    app=object.__new__(mod.SubBurnApp)
    app._job_local=mod.threading.local()
    app._job=SimpleNamespace(watermark_enabled=True,watermark_type='Text',same_wm_font=False,resolution='Original',fps='Original',watermark_timing='Full duration')
    app.subtitle_kind=lambda:'text'
    app.prepare_universal_ass=lambda *a,**k: subtitle_ass
    app.selected_font=lambda *a,**k: SimpleNamespace(label='Aljazeera')
    app.prepare_universal_text_watermark_ass=lambda *a,**k: wm_ass
    app.log=lambda *a,**k: None
    original=mod.read_srt_cues; mod.read_srt_cues=lambda p:[(0.0,1.0,['X'])]
    try:
        filt=app.build_filter(td,sub,fonts,SimpleNamespace(label='Arial'),preview_offset=0.0)
    finally:
        mod.read_srt_cues=original
    assert filt['mode']=='vf',filt
    assert filt['filter'].count('ass=')==1,filt['filter']
    assert 'setpts=' not in filt['filter'],filt['filter']
    assert 'subburn_text_layers.ass' in filt['filter'],filt['filter']
    merged=(td/'subburn_text_layers.ass').read_text('utf-8')
    assert 'Style: Default,' in merged and 'Style: Watermark,' in merged
    assert 'SUB' in merged and 'WM' in merged
    app.emit=lambda *a,**k: None
    app.verify_preview_filter_parity(filt,0.0,8.0,'Live playback')
print('TEXT WATERMARK + SUBTITLE SINGLE LIBASS PASS PASS')
