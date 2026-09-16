from __future__ import annotations
import importlib.util, pathlib, sys
from playwright.sync_api import sync_playwright
from playwright_support import launch_chromium
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_browser_lang',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    p=browser.new_page()
    # Full shipped HTML/JS. Startup fetch failures on about:blank are caught by dashboard code;
    # this test directly exercises the language-picker JS functions afterward.
    p.set_content(mod.DASHBOARD_HTML, wait_until='domcontentloaded')
    p.evaluate("showPage('transcribe')")
    p.evaluate("modes=>setSimpleSelect('trLangMode',modes,modes[0])", mod.TRANSCRIPTION_LANGUAGE_MODES)
    items=[{'code':'','label':'Choose a language…'},{'code':'ar','label':'Arabic (ar)'},{'code':'he','label':'Hebrew (he)'},{'code':'en','label':'English (en)'}]
    p.evaluate("items=>setTranscriptionLanguageOptions(items)",items)
    p.select_option('#trLangMode',label='Fixed language code')
    p.evaluate('syncTranscriptionLanguageMode()')
    p.select_option('#trLangPicker',label='Arabic (ar)');p.evaluate('applyTranscriptionLanguageChoice()')
    assert p.input_value('#trLangCode')=='ar'
    p.select_option('#trLangMode',label='Allowed languages (detect changes)');p.evaluate('syncTranscriptionLanguageMode()')
    for label in ('Hebrew (he)','English (en)','Hebrew (he)'):
        p.select_option('#trLangPicker',label=label);p.evaluate('applyTranscriptionLanguageChoice()')
    assert p.input_value('#trLangCode')=='ar, he, en'
    p.select_option('#trLangMode',label='Auto multilingual (detect changes)');p.evaluate('syncTranscriptionLanguageMode()')
    assert p.locator('#trLangPicker').is_disabled() and p.locator('#trLangCode').is_disabled()
    browser.close()
print('BROWSER TRANSCRIPTION LANGUAGE PICKER JS PASS')
