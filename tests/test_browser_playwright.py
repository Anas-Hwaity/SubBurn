import json,os,pathlib,time
from playwright.sync_api import sync_playwright
from playwright_support import launch_chromium
port=int(pathlib.Path(os.environ['SUBBURN_PORT_FILE']).read_text())
base=f'http://127.0.0.1:{port}'
work=pathlib.Path(os.environ['SUBBURN_TEST_WORK']).resolve()
errors=[]
with sync_playwright() as p:
    browser=launch_chromium(p, headless=True, args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=<-loopback>','--disable-features=BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessChecks','--allow-insecure-localhost'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda e: errors.append('pageerror: '+str(e)))
    page.on('console',lambda m: errors.append('console: '+m.text) if m.type=='error' else None)
    page.goto(base,wait_until='networkidle')
    assert page.locator('.nav [data-page]').count()==8
    expected=['home','subtitles','watermark','transcribe','preview','burn','queue','settings']
    for name in expected:
        page.locator(f'.nav [data-page="{name}"]').click(); page.wait_for_timeout(120)
        assert page.locator(f'#page-{name}').evaluate('(e)=>e.classList.contains("active")')
    # Home configuration and real browser save route.
    page.locator('.nav [data-page="home"]').click()
    page.locator('#projVideo').fill(str(work/'input.mp4'))
    page.locator('#projSubSource').select_option(label='External')
    page.locator('#projSubFile').fill(str(work/'input.srt'))
    page.locator('#projOutputDir').fill(str(work/'out'))
    page.locator('#projOutputName').fill('browser-playwright')
    page.get_by_role('button',name='Save project settings').click(); page.wait_for_timeout(350)
    assert 'queued' in page.locator('#projresult').inner_text().lower()
    # File picker actual browser endpoint/UI.
    page.locator('#projVideo').locator('xpath=following-sibling::button').click(); page.wait_for_timeout(200)
    assert page.locator('#pickerBackdrop').evaluate('(e)=>getComputedStyle(e).display')=='flex'
    page.get_by_role('button',name='Cancel').last.click(); page.wait_for_timeout(100)
    # FFmpeg accepts either an executable or a directory, so its picker must expose folder selection.
    page.locator('#projFfmpeg').locator('xpath=following-sibling::button').click(); page.wait_for_timeout(200)
    entries=page.locator('#pickerList .picker-entry'); assert entries.count()>=1
    entries.first.click(); page.wait_for_timeout(180)
    assert page.locator('#pickerSelectFolder').is_visible()
    page.get_by_role('button',name='Cancel').last.click(); page.wait_for_timeout(100)
    # Subtitle settings round trip.
    page.locator('.nav [data-page="subtitles"]').click(); page.wait_for_timeout(250)
    page.get_by_role('button',name='Save subtitle settings').click(); page.wait_for_timeout(250)
    assert 'queued' in page.locator('#subresult').inner_text().lower()
    # Watermark dynamic interval controls and normal save.
    page.locator('.nav [data-page="watermark"]').click(); page.wait_for_timeout(200)
    page.locator('#wmTiming').select_option(label='Intervals'); page.get_by_role('button',name='Add interval').click()
    assert page.locator('.wm-interval').count()>=1
    page.locator('.wm-interval').last.get_by_role('button',name='Delete').click()
    page.locator('#wmTiming').select_option(label='Full duration'); page.get_by_role('button',name='Save watermark settings').click(); page.wait_for_timeout(250)
    assert 'queued' in page.locator('#wmresult').inner_text().lower()
    # Transcription config + three action buttons; harness prevents downloads/inference.
    page.locator('.nav [data-page="transcribe"]').click(); page.wait_for_timeout(250)
    page.locator('#trModel').select_option(label='tiny'); page.locator('#trLangMode').select_option(label='Fixed language code'); page.locator('#trLangCode').fill('en'); page.locator('#trDevice').select_option(label='CPU')
    page.get_by_role('button',name='Prepare model').click();page.wait_for_timeout(250)
    page.get_by_role('button',name='Transcribe video').click();page.wait_for_timeout(250)
    page.get_by_role('button',name='Cancel').click();page.wait_for_timeout(250)
    # Preview action buttons (controlled method dispatch).
    page.locator('.nav [data-page="preview"]').click();
    for label in ('Create preview','Compare quality','Validate subtitles & fonts'):
        page.get_by_role('button',name=label).click();page.wait_for_timeout(180)
    # Burn action controls (controlled method dispatch).
    page.locator('.nav [data-page="burn"]').click();
    for label in ('Burn video','Pause','Resume','Cancel','Open result','Open folder'):
        page.get_by_role('button',name=label).click();page.wait_for_timeout(140)
    # Queue action controls.
    page.locator('.nav [data-page="queue"]').click();
    for label in ('Add current project','Start / resume','Pause after current','Cancel current','Retry failures','Clear completed','Refresh'):
        page.get_by_role('button',name=label).click();page.wait_for_timeout(140)
    # Settings appearance is live, persisted through the canonical backend, and shared with Tk.
    page.locator('.nav [data-page="settings"]').click();page.wait_for_timeout(180)
    page.locator('#appearanceMode').select_option(label='Light');page.wait_for_timeout(350)
    assert page.locator('html').get_attribute('data-theme')=='light'
    state=page.evaluate("async()=>await (await fetch('/api/state',{cache:'no-store'})).json()")
    assert state.get('appearance')=='Light',state
    page.locator('#appearanceMode').select_option(label='Balanced');page.wait_for_timeout(350)
    assert page.locator('html').get_attribute('data-theme')=='balanced'
    # Settings action controls. Exit is safe because harness intercepts request_exit.
    for label in ('Auto-detect FFmpeg','Check / install FFmpeg','Refresh installed fonts','Export diagnostics','Restore last autosave','Hide desktop window','Show desktop window','Exit SubBurn'):
        page.get_by_role('button',name=label).click();page.wait_for_timeout(140)
    # No JS/runtime console errors through all workflow surfaces.
    assert not errors, errors
    browser.close()
# Verify controlled action buttons actually reached the application dispatcher.
calls=json.loads(pathlib.Path(os.environ['SUBBURN_CALLS_FILE']).read_text())
required={'prepare_transcription_model_async','start_transcription_async','cancel_transcription','preview_async','compare_preview_async','validate_async','start_encode','pause_encode','resume_encode','cancel_encode','open_last_output','open_last_folder','batch_add_current','batch_start_queue','batch_pause_queue','batch_cancel_current','batch_retry_all_failed','batch_clear_completed','discover_tools_async','download_ffmpeg_async','scan_fonts_async','export_diagnostics','restore_recovery','enter_browser_only','show_desktop_window','request_exit'}
missing=required-set(calls);assert not missing,(missing,calls)
print('PLAYWRIGHT BROWSER UI E2E PASS',len(calls),'dispatches')
