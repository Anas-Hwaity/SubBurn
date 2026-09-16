from __future__ import annotations
import os, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from subburn.app import create_root, SubBurnApp, WHISPER_LANGUAGE_PICKER_PROMPT

root=create_root(); app=SubBurnApp(root); root.update_idletasks(); root.update()
try:
    # Auto: both human picker and canonical-code field are disabled.
    app.transcription_language_mode_var.set('Auto multilingual (detect changes)')
    app.refresh_transcription_language_state(); root.update_idletasks()
    assert str(app.transcription_language_picker.cget('state')) == 'disabled'
    assert str(app.transcription_language_entry.cget('state')) == 'disabled'

    # Fixed: picking a human-readable language replaces the canonical code.
    app.transcription_language_mode_var.set('Fixed language code')
    app.refresh_transcription_language_state(); root.update_idletasks()
    app.transcription_language_picker_var.set('Arabic (ar)')
    app.apply_transcription_language_picker()
    assert app.transcription_language_code_var.get() == 'ar'
    assert app.transcription_language_picker_var.get() == WHISPER_LANGUAGE_PICKER_PROMPT

    # Allowed: successive choices append unique canonical codes, never duplicate.
    app.transcription_language_mode_var.set('Allowed languages (detect changes)')
    app.transcription_language_code_var.set('ar')
    app.refresh_transcription_language_state()
    for label in ('Hebrew (he)','English (en)','Hebrew (he)'):
        app.transcription_language_picker_var.set(label); app.apply_transcription_language_picker()
    assert app.transcription_language_code_var.get() == 'ar, he, en'

    # Mode switch back to fixed keeps the picker usable without inventing a code.
    app.transcription_language_mode_var.set('Fixed language code'); app.refresh_transcription_language_state()
    assert str(app.transcription_language_picker.cget('state')) == 'readonly'
    print('TRANSCRIPTION LANGUAGE PICKER TK UI PASS')
finally:
    try: root.destroy()
    except Exception: pass
