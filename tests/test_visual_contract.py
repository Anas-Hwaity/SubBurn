from __future__ import annotations
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from subburn.app import create_root, SubBurnApp, DASHBOARD_HTML
from tkinter import ttk


def require(cond, msg):
    if not cond:
        raise AssertionError(msg)


def hex_rgb(value):
    value=value.lstrip('#')
    return tuple(int(value[i:i+2],16) for i in (0,2,4))

def rel_lum(value):
    vals=[]
    for c in hex_rgb(value):
        v=c/255.0
        vals.append(v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4)
    r,g,b=vals
    return .2126*r+.7152*g+.0722*b

def contrast(a,b):
    x,y=sorted((rel_lum(a),rel_lum(b)),reverse=True)
    return (x+.05)/(y+.05)

root = create_root()
app = SubBurnApp(root)
root.geometry('980x680+20+20')
root.update_idletasks(); root.update()

expected = ['Home','Subtitles','Watermark','Transcribe','Preview','Burn','Queue','Settings']
require(list(app.workflow_nav_buttons) == expected, 'workflow navigation order changed')
require(set(app.workflow_pages) == set(expected), 'workflow page set changed')
require(getattr(app, 'current_workflow_page', None) == 'Home', 'Home must be initial page')

style = ttk.Style(root)
colors = app.ui_colors
require(rel_lum(colors['app']) < 0.03, 'application theme is no longer dark')
require(rel_lum(colors['surface']) < 0.04, 'surface theme is no longer dark')
require(contrast(colors['text'], colors['surface']) >= 7.0, 'primary text contrast regressed')
require(contrast(colors['muted'], colors['surface']) >= 4.5, 'muted text contrast regressed')
require(style.lookup('TLabel','background') == colors['surface'], 'labels must share card surface to avoid text boxes')
require(style.lookup('TFrame','background') == colors['surface'], 'nested rows must share card surface to avoid rectangular seams')
require(root.title() == 'SubBurn', 'desktop title must expose only the SubBurn product name')
require('<title>SubBurn</title>' in DASHBOARD_HTML, 'browser title must expose only SubBurn')
source_text = (ROOT / 'src' / 'subburn' / 'app.py').read_text(encoding='utf-8')
require('lines.append(f\"SubBurn {APP_VERSION}\")' not in source_text, 'diagnostics must not expose a visible development version')
require('-webkit-text-stroke:.5px var(--control-stroke)' in DASHBOARD_HTML, 'boxed-control subtle text stroke contract missing')
require('select option,select optgroup' in DASHBOARD_HTML and '--menu-bg:' in DASHBOARD_HTML, 'theme-aware dropdown menu colors missing')
require('backdrop-filter:blur(28px)' in DASHBOARD_HTML and 'backdrop-filter:blur(32px)' in DASHBOARD_HTML, 'browser liquid-glass blur contract missing')
require(colors['app'] != colors['surface'], 'app and card surfaces must remain visually distinct')
require(colors['accent'] != colors['danger'], 'primary and destructive roles must remain distinct')
require(style.lookup('Accent.TButton','background') == colors['accent'], 'primary button style lost accent')
require(style.lookup('Danger.TButton','background') == colors['danger'], 'danger button style lost destructive color')
require(style.lookup('NavActive.TButton','background') == colors['accent_soft'], 'active navigation style lost selected state')
require(app.appearance_var.get() in ['Dark','Balanced','Light'], 'appearance setting is invalid')
for mode in ['Dark','Balanced','Light']:
    app.appearance_var.set(mode); app.apply_appearance(persist=False); root.update_idletasks(); root.update()
    themed=app.ui_colors
    require(contrast(themed['text'],themed['surface']) >= 7.0, f'{mode} primary text contrast regressed')
    require(contrast(themed['muted'],themed['surface']) >= 4.0, f'{mode} muted text contrast regressed')
    require(style.lookup('TLabel','background') == themed['surface'], f'{mode} label surface mismatch')
app.appearance_var.set('Dark'); app.apply_appearance(persist=False); root.update_idletasks(); root.update()

for i, name in enumerate(expected, 1):
    binding = root.bind_all(f'<Control-KeyPress-{i}>')
    require(bool(binding), f'missing Ctrl+{i} shortcut for {name}')
    require(app.show_workflow_page(name), f'cannot show {name}')
    root.update_idletasks(); root.update()
    require(app.current_workflow_page == name, f'current page did not become {name}')
    require(str(app.workflow_nav_buttons[name].cget('style')) == 'NavActive.TButton', f'{name} nav item is not visibly selected')
    require(app.workflow_pages[name].winfo_ismapped(), f'{name} page is not mapped')
    # All page containers must remain within the page host at the supported minimum size.
    require(app.workflow_pages[name].winfo_width() <= app.page_host.winfo_width() + 2, f'{name} overflows page host width')
    require(app.workflow_pages[name].winfo_height() <= app.page_host.winfo_height() + 2, f'{name} overflows page host height')

require(root.winfo_width() >= 980 and root.winfo_height() >= 680, 'supported minimum window size regressed')
require(app.start_btn.cget('style') == 'Accent.TButton', 'Burn video must remain the primary action')
require(app.cancel_btn.cget('style') == 'Danger.TButton', 'encode cancel must remain destructive style')

# The seven content-heavy pages stay scrollable; Preview intentionally fits without a scrolling shell.
for name in ['Home','Subtitles','Watermark','Transcribe','Burn','Queue','Settings']:
    require(name in app._page_scroll_canvases, f'{name} lost scrolling support')
require('Preview' not in app._page_scroll_canvases, 'Preview should remain a direct rendered workspace')

print('VISUAL CONTRACT PASS: 8 pages, styles, shortcuts, minimum-size containment')
try:
    root.destroy()
except Exception:
    pass
