from __future__ import annotations
import importlib.util, pathlib, re, sys, tempfile
from playwright.sync_api import sync_playwright
from playwright_support import launch_chromium

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_static_visual',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

# Render the exact shipped dashboard markup/CSS without executing its network/control script.
html=re.sub(r'<script>.*?</script>', '', mod.DASHBOARD_HTML, flags=re.S|re.I)
pages=['home','subtitles','watermark','transcribe','preview','burn','queue','settings']
viewports=[('desktop',1440,900),('compact',900,720),('mobile',390,844)]
themes=['dark','balanced','light']
outdir=pathlib.Path(tempfile.mkdtemp(prefix='subburn-browser-visual-'))

with sync_playwright() as pw:
    browser=launch_chromium(pw, headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
    page=pw.browser.new_page() if False else None
    for label,width,height in viewports:
      for theme in themes:
        ctx=browser.new_context(viewport={'width':width,'height':height}, device_scale_factor=1)
        p=ctx.new_page(); p.set_content(html, wait_until='domcontentloaded')
        p.evaluate("theme => document.documentElement.dataset.theme=theme",theme)
        assert p.title()=='SubBurn'
        assert p.locator('text=SubBurn').first.is_visible()
        body_font=p.evaluate("getComputedStyle(document.body).fontFamily")
        assert 'Times New Roman' not in body_font and ('Segoe UI' in body_font or 'system-ui' in body_font or 'Inter' in body_font), body_font
        body_bg=p.evaluate("getComputedStyle(document.body).backgroundImage")
        assert 'gradient' in body_bg, body_bg
        card_style=p.evaluate("""() => {const s=getComputedStyle(document.querySelector('.card'));return {radius:s.borderRadius,backdrop:s.backdropFilter,bg:s.backgroundImage}}""")
        assert card_style['radius'] not in ('0px',''),card_style
        assert 'blur' in card_style['backdrop'],card_style
        assert 'gradient' in card_style['bg'],card_style
        control_style=p.evaluate("""() => {const sel=document.getElementById('appearanceMode'),opt=sel&&sel.options[0],body=getComputedStyle(document.body);return {selectColor:sel?getComputedStyle(sel).color:'', optionColor:opt?getComputedStyle(opt).color:'', optionBg:opt?getComputedStyle(opt).backgroundColor:'', stroke:sel?getComputedStyle(sel).webkitTextStrokeWidth:'', bodyShadow:body.textShadow}}""")
        assert control_style['stroke'] not in ('0px',''),control_style
        assert control_style['selectColor'] and control_style['optionColor'],control_style
        assert control_style['optionBg'] not in ('rgba(0, 0, 0, 0)','transparent',''),control_style
        assert control_style['bodyShadow'] in ('none',''),control_style
        for target in pages:
            p.evaluate("""name => {
              document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));
              document.querySelectorAll('.nav button').forEach(x=>x.classList.toggle('active',x.dataset.page===name));
              document.getElementById('page-'+name).classList.add('active');
            }""", target)
            p.wait_for_timeout(15)
            dims=p.evaluate("""() => ({
              vw: innerWidth, doc: document.documentElement.scrollWidth, body: document.body.scrollWidth,
              pageRight: document.querySelector('.page.active').getBoundingClientRect().right,
              mainRight: document.querySelector('.main').getBoundingClientRect().right
            })""")
            assert dims['doc'] <= dims['vw'] + 1, (theme,label,target,dims)
            assert dims['body'] <= dims['vw'] + 1, (theme,label,target,dims)
            assert dims['pageRight'] <= dims['vw'] + 1, (theme,label,target,dims)
            bad=p.evaluate("""() => [...document.querySelectorAll('.page.active input,.page.active select,.page.active button,.page.active textarea')]
              .filter(e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0&&!e.closest('.queue-table-wrap')&&(r.left < -1 || r.right > innerWidth+1)})
              .map(e=>({tag:e.tagName,id:e.id||'',text:(e.textContent||'').trim().slice(0,50),rect:e.getBoundingClientRect().toJSON()}))""")
            assert not bad, (theme,label,target,bad)
        if label=='desktop':
            for target in ('home','settings'):
                p.evaluate("""name => {document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.nav button').forEach(x=>x.classList.toggle('active',x.dataset.page===name));document.getElementById('page-'+name).classList.add('active')}""", target)
                p.screenshot(path=str(outdir/f'{theme}-{label}-{target}.png'), full_page=True)
        ctx.close()
    browser.close()
print(f'BROWSER STATIC VISUAL PASS: {len(pages)} pages x {len(viewports)} viewports x {len(themes)} themes; screenshots={outdir}')
