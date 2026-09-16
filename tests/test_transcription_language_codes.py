from __future__ import annotations
import importlib.util, pathlib, sys
SRC=pathlib.Path(__file__).resolve().parents[1]/'src'/'subburn'/'app.py'
spec=importlib.util.spec_from_file_location('subburn_language_codes',SRC)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

for code in ('en','ar','he','zh','yue','nl','ja','ko','fa','ur'):
    assert mod.parse_allowed_language_codes(code)==(code,), code
assert mod.parse_allowed_language_codes('ar, he; en ar')==('ar','he','en')
assert mod.WHISPER_LANGUAGES['zh']=='Chinese'
assert mod.WHISPER_LANGUAGES['yue']=='Cantonese'
for bad in ('cn','ch','xx','en-US','123','english'):
    try:
        mod.parse_allowed_language_codes(bad)
    except ValueError as exc:
        if bad in {'cn','ch'}:
            assert "zh" in str(exc) and "yue" in str(exc)
    else:
        raise AssertionError(f'unsupported language code accepted: {bad}')
print(f'TRANSCRIPTION LANGUAGE-CODE VALIDATION PASS ({len(mod.WHISPER_LANGUAGES)} official codes)')

# WIP17 human-readable picker mapping must cover exactly the canonical language set.
assert len(mod.WHISPER_LANGUAGE_DISPLAY_OPTIONS) == len(mod.WHISPER_LANGUAGES) + 1
assert mod.WHISPER_LANGUAGE_DISPLAY_OPTIONS[0] == mod.WHISPER_LANGUAGE_PICKER_PROMPT
for code, name in mod.WHISPER_LANGUAGES.items():
    label = f'{name} ({code})'
    assert label in mod.WHISPER_LANGUAGE_DISPLAY_OPTIONS, label
    assert mod.whisper_language_code_from_display(label) == code
    assert mod.whisper_language_display(code) == label
assert mod.whisper_language_code_from_display('not a language') == ''
print('TRANSCRIPTION HUMAN-READABLE LANGUAGE PICKER MAP PASS')
