
from __future__ import annotations
import ctypes
import collections
import functools
from contextlib import contextmanager
import http.server
import http.cookies
import hashlib
import importlib
import inspect
import json
import math
import os
import queue
import re
import secrets
import shutil
import signal
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
import uuid
import zipfile
from dataclasses import asdict, dataclass, field, fields as dataclass_fields
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "SubBurn"
OWNER_NAME = "Anas Al Hwaity"
OWNER_TELEGRAM = "@ANAS12RM"
OWNER_TELEGRAM_URL = "https://t.me/ANAS12RM"
HELP_MANUAL_TEXT = """SubBurn Help Manual

QUICK START
1. Home: choose a video, subtitle source, output folder, filename, and optional metadata.
2. Subtitles: choose the primary font, fallback fonts, style, placement, and timing options.
3. Watermark: enable a text or image watermark, choose its font/position/opacity, and optionally define intervals.
4. Preview: render an exact frame or an 8-second clip using the same subtitle and watermark pipeline as the final burn.
5. Burn: choose Simple or Advanced encoding options, then burn the video.
6. Queue: add the current project, another video with the current settings, or a recent saved project. Reorder, retry, duplicate, or remove jobs before or after processing.

HOME
Video: media file to process.
Subtitle source: Auto chooses a usable source, External uses the selected subtitle file, Embedded uses a subtitle stream inside the video.
Output: choose the destination folder, filename, and container. Clean output folder keeps generated files isolated.
Metadata: optional title, artist, album, genre, date, description, and copyright tags. SubBurn also writes the standard comment `Created by SubBurn.` to produced videos.
Recent projects/folders: restore previous project state or reuse an output folder. Clear buttons remove only the history list, not your media files.

SUBTITLES
Primary font: preferred subtitle font.
Fallback fonts: additional fonts used only when the primary font lacks required glyphs.
Style: size, bold/italic/underline/strikeout, colors, opacity, outline, shadow, spacing, rotation, alignment, margins, background box, wrapping, line limits, safe areas, and caption effects.
RTL: Arabic and Hebrew are rendered through libass with HarfBuzz/FriBidi and deterministic fallback planning.

WATERMARK
Text watermark: enter text, choose whether to reuse the subtitle font, or select a separate watermark font.
Image watermark: choose an image and control scale, opacity, coordinates, and position.
Timing: full duration or defined intervals. The preview page can move an enabled watermark by clicking the rendered frame.

TRANSCRIBE
Runs local Faster-Whisper/CTranslate2 transcription. Choose a model, language mode, language codes, and device. Model downloads are cached and reused. Cancel stops active preparation/inference when supported.

PREVIEW
Render frame: produces an exact still at the selected timestamp.
Play 8s inline/clip: produces a short preview using the same subtitle and watermark filter logic as final output.
Compare quality: creates comparison material for the selected encoding settings.

BURN / ENCODING
Simple mode keeps the common choices visible. Advanced mode exposes codec, quality mode, encoder policy, speed preset, resolution, frame rate, audio handling, explicit encoder, bitrate/target size, and chapter preservation.
Auto encoder selection benchmarks compatible encoders and caches the fastest measured usable option. Explicit encoder selection remains authoritative.
Progress is canonical across desktop and browser: determinate percentages are shown only when a real denominator exists; otherwise SubBurn reports indeterminate progress rather than inventing a percentage.

QUEUE
Jobs persist in SQLite across restarts. Add current project, add another video without changing the open project, or add a recent saved project. Select one or more rows to remove them. Running jobs are cancelled before removal. Queue jobs run one at a time to prevent progress/cancellation state from crossing between jobs.

SETTINGS
Appearance: Dark, Balanced, or Light.
Runtime & FFmpeg: SubBurn checks compatible system/PATH FFmpeg first, then a user-selected file/folder, then the verified managed runtime.
Diagnostics: export logs and environment details for troubleshooting.
Recovery: restore the last autosaved project after an interruption.

PROGRESS & REPORTING
Download metrics: percentage, downloaded/total bytes, speed, and ETA are separate.
Encode metrics: percentage, FPS, encode speed, ETA, and elapsed time freeze at terminal completion.
100% is reserved for verified completion. Failure and cancellation never masquerade as success.

OWNER
Made by: Anas Al Hwaity
Contact Owner: @ANAS12RM on Telegram
"""
APP_VERSION = "2.8.0-dev"
APPEARANCE_MODES = ["Dark", "Balanced", "Light"]

def normalize_appearance_mode(value):
    raw = str(value or "").strip().casefold()
    aliases = {"dark": "Dark", "balanced": "Balanced", "medium": "Balanced", "inbetween": "Balanced", "light": "Light"}
    return aliases.get(raw, "Dark")

def appearance_palette(value):
    mode = normalize_appearance_mode(value)
    palettes = {
        "Dark": {
            "app":"#04111E","surface":"#0B2032","surface_alt":"#12324B","surface_hover":"#194761",
            "sidebar":"#061725","entry":"#071B2B","border":"#4F718F","border_soft":"#29465E",
            "glass_highlight":"#9CC6E5","text":"#F7FBFF","muted":"#ADC0D2","sidebar_muted":"#86A1B8",
            "accent":"#6E94FF","accent_hover":"#8AA9FF","accent_soft":"#1B4275","danger":"#D86170",
            "danger_hover":"#E27683","success":"#4FC58B","trough":"#122A3D","disabled_bg":"#0C1B29",
            "disabled_text":"#6E8295","selection_text":"#FFFFFF"},
        "Balanced": {
            "app":"#182938","surface":"#263D50","surface_alt":"#31536A","surface_hover":"#3B627B",
            "sidebar":"#1C3041","entry":"#20384B","border":"#7896AD","border_soft":"#526F85",
            "glass_highlight":"#B4CDDE","text":"#FAFCFF","muted":"#C9D5DF","sidebar_muted":"#A2B6C7",
            "accent":"#7399FF","accent_hover":"#91AEFF","accent_soft":"#3A6192","danger":"#D96877",
            "danger_hover":"#E6838E","success":"#55C893","trough":"#304A5D","disabled_bg":"#293B49",
            "disabled_text":"#8E9EAC","selection_text":"#FFFFFF"},
        "Light": {
            "app":"#DFEAF3","surface":"#F8FBFD","surface_alt":"#EAF3F8","surface_hover":"#DCEAF2",
            "sidebar":"#D7E5EF","entry":"#FFFFFF","border":"#94AFC3","border_soft":"#C2D1DC",
            "glass_highlight":"#FFFFFF","text":"#142334","muted":"#586E82","sidebar_muted":"#607B91",
            "accent":"#4D72DB","accent_hover":"#3F64CB","accent_soft":"#D4E3FF","danger":"#BF4F60",
            "danger_hover":"#A94151","success":"#25865E","trough":"#CEDDE7","disabled_bg":"#EAF0F4",
            "disabled_text":"#8796A4","selection_text":"#FFFFFF"},
    }
    return dict(palettes[mode])

OUTPUT_MARKER_KEY = "comment"
OUTPUT_MARKER_VALUE = "Created by SubBurn."

def command_text(cmd):
    """Stable human-readable subprocess command for technical logs/diagnostics only."""
    return subprocess.list2cmdline([str(x) for x in cmd])



SPACE_CODEPOINTS = {0x0020, 0x00A0, 0x1680, 0x180E, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000, 0xFEFF}
IS_WINDOWS = os.name == "nt"
IS_MACOS = sys.platform == "darwin"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WINDOWS else 0


def _expanded_env_path(name, fallback):
    raw = str(os.environ.get(name, "") or "").strip()
    return Path(os.path.expandvars(os.path.expanduser(raw))) if raw else Path(fallback)


def _platform_storage_dirs():
    """Return platform-appropriate config/data/cache/state roots.

    Large/re-downloadable assets never live in Windows roaming AppData, and Unix-like
    systems respect XDG locations rather than putting all state in one hidden directory.
    """
    home = Path.home()
    if IS_WINDOWS:
        roaming = _expanded_env_path("APPDATA", home / "AppData" / "Roaming")
        local = _expanded_env_path("LOCALAPPDATA", home / "AppData" / "Local")
        return roaming / APP_NAME, local / APP_NAME / "data", local / APP_NAME / "cache", local / APP_NAME / "state"
    if IS_MACOS:
        base = home / "Library"
        data = base / "Application Support" / APP_NAME
        return data / "config", data, base / "Caches" / APP_NAME, data / "state"
    config = _expanded_env_path("XDG_CONFIG_HOME", home / ".config") / "subburn"
    data = _expanded_env_path("XDG_DATA_HOME", home / ".local" / "share") / "subburn"
    cache = _expanded_env_path("XDG_CACHE_HOME", home / ".cache") / "subburn"
    state = _expanded_env_path("XDG_STATE_HOME", home / ".local" / "state") / "subburn"
    return config, data, cache, state


def _linux_xdg_video_dir():
    override = str(os.environ.get("XDG_VIDEOS_DIR", "") or "").strip()
    if override:
        return Path(os.path.expandvars(os.path.expanduser(override.replace("$HOME", str(Path.home())))))
    cfg = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "user-dirs.dirs"
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'^XDG_VIDEOS_DIR=["\']?(.+?)["\']?$', text, re.MULTILINE)
        if match:
            raw = match.group(1).replace("$HOME", str(Path.home()))
            return Path(os.path.expandvars(os.path.expanduser(raw)))
    except Exception:
        pass
    return Path.home() / "Videos"


def _default_output_root():
    if IS_MACOS:
        base = Path.home() / "Movies"
    elif IS_WINDOWS:
        base = Path.home() / "Videos"
    else:
        base = _linux_xdg_video_dir()
    return base / APP_NAME


def _ensure_writable_dir(primary, fallback=None):
    candidates = [Path(primary)]
    if fallback is not None and Path(fallback) != Path(primary):
        candidates.append(Path(fallback))
    last = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / f".{APP_NAME.casefold()}-write-probe-{os.getpid()}"
            probe.write_bytes(b"ok")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception as exc:
            last = exc
    raise RuntimeError(f"SubBurn cannot create a writable application directory: {last}")


CONFIG_DIR, DATA_DIR, CACHE_DIR, STATE_DIR = _platform_storage_dirs()
for _subburn_dir in (CONFIG_DIR, DATA_DIR, CACHE_DIR, STATE_DIR):
    _subburn_dir.mkdir(parents=True, exist_ok=True)

# Compatibility alias for internal code that still means persistent application data.
APP_HOME = DATA_DIR
RUNTIME_DIR = DATA_DIR / "runtime"
PREPARED_FONT_DIR = RUNTIME_DIR / "prepared_fonts"
FONT_DIR = DATA_DIR / "fonts"
TRANSCRIPTION_DIR = DATA_DIR / "transcriptions"
PREVIEW_DIR = CACHE_DIR / "previews"
SUBBURN_TEMP_DIR = CACHE_DIR / "temp"
LOG_DIR = STATE_DIR / "logs"
DIAG_DIR = STATE_DIR / "diagnostics"
SUBBURN_OUTPUT_DIR = _ensure_writable_dir(_default_output_root(), DATA_DIR / "Output")
for _subburn_dir in (RUNTIME_DIR, PREPARED_FONT_DIR, FONT_DIR, TRANSCRIPTION_DIR, PREVIEW_DIR, SUBBURN_TEMP_DIR, LOG_DIR, DIAG_DIR):
    _subburn_dir.mkdir(parents=True, exist_ok=True)

# Do not mutate tempfile.tempdir globally. SubBurn-owned temporary work may explicitly use
# SUBBURN_TEMP_DIR; third-party libraries keep their normal platform temporary-directory rules.

SETTINGS_FILE = CONFIG_DIR / "settings.json"
RECOVERY_FILE = STATE_DIR / "recovery_project.json"
RECENTS_FILE = STATE_DIR / "recents.json"
PRESETS_FILE = CONFIG_DIR / "presets.json"
QUEUE_DB = STATE_DIR / "queue.sqlite3"
TRANSCRIPTION_MODEL_DIR = RUNTIME_DIR / "models" / "faster-whisper"
TRANSCRIPTION_MODELS = ["large-v3", "turbo", "medium", "small", "base", "tiny"]
TRANSCRIPTION_LANGUAGE_MODES = [
    "Auto multilingual (detect changes)",
    "Allowed languages (detect changes)",
    "Fixed language code",
]
TRANSCRIPTION_DEVICES = ["Auto", "CUDA", "CPU"]
# Canonical OpenAI Whisper language-token set. Keep validation local so invalid country/
# pseudo-codes fail before model inference rather than surfacing as a deep tokenizer error.
WHISPER_LANGUAGES = {
    "en":"English","zh":"Chinese","de":"German","es":"Spanish","ru":"Russian","ko":"Korean",
    "fr":"French","ja":"Japanese","pt":"Portuguese","tr":"Turkish","pl":"Polish","ca":"Catalan",
    "nl":"Dutch","ar":"Arabic","sv":"Swedish","it":"Italian","id":"Indonesian","hi":"Hindi",
    "fi":"Finnish","vi":"Vietnamese","he":"Hebrew","uk":"Ukrainian","el":"Greek","ms":"Malay",
    "cs":"Czech","ro":"Romanian","da":"Danish","hu":"Hungarian","ta":"Tamil","no":"Norwegian",
    "th":"Thai","ur":"Urdu","hr":"Croatian","bg":"Bulgarian","lt":"Lithuanian","la":"Latin",
    "mi":"Maori","ml":"Malayalam","cy":"Welsh","sk":"Slovak","te":"Telugu","fa":"Persian",
    "lv":"Latvian","bn":"Bengali","sr":"Serbian","az":"Azerbaijani","sl":"Slovenian","kn":"Kannada",
    "et":"Estonian","mk":"Macedonian","br":"Breton","eu":"Basque","is":"Icelandic","hy":"Armenian",
    "ne":"Nepali","mn":"Mongolian","bs":"Bosnian","kk":"Kazakh","sq":"Albanian","sw":"Swahili",
    "gl":"Galician","mr":"Marathi","pa":"Punjabi","si":"Sinhala","km":"Khmer","sn":"Shona",
    "yo":"Yoruba","so":"Somali","af":"Afrikaans","oc":"Occitan","ka":"Georgian","be":"Belarusian",
    "tg":"Tajik","sd":"Sindhi","gu":"Gujarati","am":"Amharic","yi":"Yiddish","lo":"Lao",
    "uz":"Uzbek","fo":"Faroese","ht":"Haitian Creole","ps":"Pashto","tk":"Turkmen","nn":"Nynorsk",
    "mt":"Maltese","sa":"Sanskrit","lb":"Luxembourgish","my":"Myanmar","bo":"Tibetan","tl":"Tagalog",
    "mg":"Malagasy","as":"Assamese","tt":"Tatar","haw":"Hawaiian","ln":"Lingala","ha":"Hausa",
    "ba":"Bashkir","jw":"Javanese","su":"Sundanese","yue":"Cantonese",
}
WHISPER_LANGUAGE_PICKER_PROMPT = "Choose a language…"
WHISPER_LANGUAGE_DISPLAY_OPTIONS = [
    WHISPER_LANGUAGE_PICKER_PROMPT,
    *[f"{name} ({code})" for code, name in sorted(WHISPER_LANGUAGES.items(), key=lambda item: (item[1].casefold(), item[0]))],
]
WHISPER_LANGUAGE_DISPLAY_TO_CODE = {f"{name} ({code})": code for code, name in WHISPER_LANGUAGES.items()}

def whisper_language_display(code):
    code = str(code or "").strip().lower()
    name = WHISPER_LANGUAGES.get(code)
    return f"{name} ({code})" if name else WHISPER_LANGUAGE_PICKER_PROMPT

def whisper_language_code_from_display(value):
    return WHISPER_LANGUAGE_DISPLAY_TO_CODE.get(str(value or "").strip(), "")

TRANSCRIPTION_MODEL_METADATA_CACHE = RUNTIME_DIR / "transcription-model-metadata.json"
def _path_within(path, root):
    """Return True when path resolves inside root (or equals root)."""
    try:
        resolved = Path(path).expanduser().resolve()
        resolved_root = Path(root).expanduser().resolve()
        return resolved == resolved_root or resolved_root in resolved.parents
    except Exception:
        return False


def redact_sensitive_text(text):
    """Redact secrets and machine-specific private paths from exported diagnostics/crash logs."""
    value = str(text or "")
    # Secret-bearing headers/cookies/query parameters first.
    value = re.sub(r"(?i)(SubBurnSession\s*=\s*)[^;\s]+", r"\1<redacted>", value)
    value = re.sub(r"(?i)(Authorization\s*:\s*(?:Bearer|Basic)\s+)[^\s]+", r"\1<redacted>", value)
    value = re.sub(r"(?i)(https?://)([^/@\s:]+):([^/@\s]+)@", r"\1<redacted>:<redacted>@", value)
    value = re.sub(r"(?i)([?&](?:token|access_token|api[_-]?key|password|passwd|secret|auth)=)[^&#\s]+", r"\1<redacted>", value)
    # Replace known application/user roots longest-first so diagnostics stay useful without
    # exposing the local username or exact private directory layout.
    replacements = []
    for root, label in (
        (STATE_DIR, "<STATE>"), (CACHE_DIR, "<CACHE>"), (DATA_DIR, "<DATA>"),
        (CONFIG_DIR, "<CONFIG>"), (Path.home(), "~"),
    ):
        try:
            raw = str(Path(root).resolve())
        except Exception:
            raw = str(root)
        if raw:
            replacements.append((raw, label))
            if os.name == "nt":
                replacements.append((raw.replace("\\", "/"), label))
    for raw, label in sorted(set(replacements), key=lambda x: len(x[0]), reverse=True):
        value = value.replace(raw, label)
    return value


# Audited immutable CTranslate2 model snapshots.  Never resolve these names through a
# mutable Hugging Face ``main`` branch: the exact repository + 40-hex revision pair is
# part of SubBurn's reproducibility/security contract.
TRANSCRIPTION_MODEL_SOURCES = {
    "large-v3": {
        "repo": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
        "license": "MIT",
        "upstream": "openai/whisper-large-v3",
    },
    "turbo": {
        "repo": "dropbox-dash/faster-whisper-large-v3-turbo",
        "revision": "0c94664816ec82be77b20e824c8e8675995b0029",
        "license": "MIT",
        "upstream": "openai/whisper-large-v3-turbo",
    },
    "medium": {
        "repo": "Systran/faster-whisper-medium",
        "revision": "7832330bcea9a8d5fd6d6637c49fe5d256e98277",
        "license": "MIT",
        "upstream": "openai/whisper-medium",
    },
    "small": {
        "repo": "Systran/faster-whisper-small",
        "revision": "536b0662742c02347bc0e980a01041f333bce120",
        "license": "MIT",
        "upstream": "openai/whisper-small",
    },
    "base": {
        "repo": "Systran/faster-whisper-base",
        "revision": "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
        "license": "MIT",
        "upstream": "openai/whisper-base",
    },
    "tiny": {
        "repo": "Systran/faster-whisper-tiny",
        "revision": "d90ca5fe260221311c53c58e660288d3deb8d356",
        "license": "MIT",
        "upstream": "openai/whisper-tiny",
    },
}
TRANSCRIPTION_MODEL_ALLOW_PATTERNS = (
    "config.json", "preprocessor_config.json", "model.bin", "tokenizer.json",
    "vocabulary.json", "vocabulary.txt",
)
# Offline fallbacks only. Exact download bytes are queried from Hugging Face when reachable.
# These are intentionally displayed as estimates, never as authoritative current sizes.
TRANSCRIPTION_MODEL_ESTIMATED_BYTES = {
    "large-v3": 3_095_000_000,
    "turbo": 1_625_000_000,
    "medium": 1_535_000_000,
    "small": 486_000_000,
    "base": 148_000_000,
    "tiny": 79_000_000,
}
TRANSCRIPTION_MODEL_MEMORY_GUIDANCE = {
    "large-v3": {"ram": "~6–10 GB typical", "vram": "~3–6+ GB typical (compute/batch dependent)"},
    "turbo": {"ram": "~4–8 GB typical", "vram": "~2–5+ GB typical (compute/batch dependent)"},
    "medium": {"ram": "~3–6 GB typical", "vram": "~2–4+ GB typical (compute/batch dependent)"},
    "small": {"ram": "~1.5–4 GB typical", "vram": "~1–3+ GB typical (compute/batch dependent)"},
    "base": {"ram": "~1–2.5 GB typical", "vram": "~1–2 GB typical (compute/batch dependent)"},
    "tiny": {"ram": "~0.7–2 GB typical", "vram": "~0.5–1.5 GB typical (compute/batch dependent)"},
}
TRANSCRIPTION_ALLOWED_WINDOW_TARGET = 15.0
TRANSCRIPTION_ALLOWED_WINDOW_MIN = 5.0
TRANSCRIPTION_ALLOWED_WINDOW_MAX = 30.0
TRANSCRIPTION_ALLOWED_LOW_CONFIDENCE = 0.25
TRANSCRIPTION_ALLOWED_RETRIES = 1
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_SHA256_URL = FFMPEG_URL + ".sha256"
FFMPEG_PROVIDER = "Gyan.dev"
# A completed, verified transfer is cached separately from the installed runtime. If
# extraction/validation/install fails after the 100+ MB transfer, retrying reuses these
# authenticated bytes instead of starting the network transfer again.
FFMPEG_DOWNLOAD_CACHE_DIR = RUNTIME_DIR / "downloads"
FFMPEG_ARCHIVE_CACHE = FFMPEG_DOWNLOAD_CACHE_DIR / "ffmpeg-release-essentials.zip"
FFMPEG_ARCHIVE_CACHE_META = FFMPEG_DOWNLOAD_CACHE_DIR / "ffmpeg-release-essentials.verified.json"
FFMPEG_RUNTIME_MANIFEST_NAME = "subburn-runtime-manifest.json"
TEXT_SUB_EXTS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}
BITMAP_SUB_EXTS = {".sup", ".idx"}
SUBTITLE_FILE_EXTS = TEXT_SUB_EXTS | BITMAP_SUB_EXTS
BITMAP_SUBTITLE_CODECS = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".ts", ".m2ts"}
OUTPUT_EXTS = [".mp4", ".mkv", ".mov", ".webm"]
CODEC_MODES = ["Match source", "H.264", "HEVC", "AV1", "VP9"]
QUALITY_MODES = ["Preserve visual quality", "Match source size", "Target file size", "Custom bitrate"]



def presentation_stage(name, message):
    name = str(name or "")
    return name, str(message or "")

def presentation_history(history):
    out=[]
    for item in history or []:
        name,msg=presentation_stage(item.get("name"),item.get("message"))
        out.append({"name":name,"message":msg,"ts":item.get("ts","")})
    return out


SPEED_MODES = ["Fastest", "Fast", "Balanced", "Quality", "Maximum"]
ENCODER_POLICIES = ["Balanced", "Prefer hardware", "Fastest measured", "Best CPU quality"]
AUDIO_MODES = ["Copy all audio", "Copy first audio", "AAC 192k", "Opus 160k", "No audio"]
USER_METADATA_KEYS = ("title", "artist", "album", "genre", "date", "description", "copyright")
RESOLUTION_MODES = ["Original", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
FPS_MODES = ["Original", "23.976", "24", "25", "29.97", "30", "50", "59.94", "60"]
WATERMARK_TYPES = ["Text", "Image"]
WATERMARK_TIMING = ["Full duration", "Intervals"]
POSITIONS = ["Top left", "Top center", "Top right", "Middle left", "Center", "Middle right", "Bottom left", "Bottom center", "Bottom right"]
SUBTITLE_ALIGNMENT_MAP = {"Bottom left": 1, "Bottom center": 2, "Bottom right": 3, "Middle left": 4, "Center": 5, "Middle right": 6, "Top left": 7, "Top center": 8, "Top right": 9}
SUBTITLE_ALIGNMENT_NAMES = list(SUBTITLE_ALIGNMENT_MAP.keys())
CAPTION_EFFECT_LABEL_TO_ID = {
    "None": "none",
    "Karaoke progress highlight": "karaoke_progress",
    "Progressive word reveal": "word_reveal",
}
CAPTION_EFFECT_ID_TO_LABEL = {v: k for k, v in CAPTION_EFFECT_LABEL_TO_ID.items()}
CAPTION_EFFECT_LABELS = list(CAPTION_EFFECT_LABEL_TO_ID.keys())
AUTO_ENCODERS = {
    "H.264": ["h264_nvenc", "h264_qsv", "h264_amf", "h264_videotoolbox", "h264_mf", "libx264", "libopenh264"],
    "HEVC": ["hevc_nvenc", "hevc_qsv", "hevc_amf", "hevc_videotoolbox", "hevc_mf", "libx265"],
    "AV1": ["av1_nvenc", "av1_qsv", "av1_amf", "av1_videotoolbox", "av1_mf", "libsvtav1", "libaom-av1", "librav1e"],
    "VP9": ["vp9_qsv", "libvpx-vp9"]
}
SOFTWARE_ENCODERS = {"H.264": ["libx264", "libopenh264"], "HEVC": ["libx265"], "AV1": ["libsvtav1", "libaom-av1", "librav1e"], "VP9": ["libvpx-vp9"]}
ENCODER_CACHE_FILE = CACHE_DIR / "encoder_cache.json"


def _legacy_storage_root():
    if IS_WINDOWS:
        return _expanded_env_path("APPDATA", Path.home() / "AppData" / "Roaming") / APP_NAME
    return Path.home() / ".subburn"


def _copy_if_missing(source, destination):
    source=Path(source);destination=Path(destination)
    if destination.exists() or not source.is_file():
        return False
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=destination.with_name(destination.name+f".migrate-{os.getpid()}.tmp")
    shutil.copy2(source,tmp)
    os.replace(tmp,destination)
    return True


def _migrate_legacy_user_state():
    """Non-destructively import lightweight pre-public SubBurn state once.

    Old files are intentionally left untouched for rollback. Large runtimes/models are not
    copied during application import; they can be re-prepared explicitly in the new data root.
    """
    legacy=_legacy_storage_root()
    if not legacy.exists():
        return []
    migrated=[]
    file_map={
        "settings.json":SETTINGS_FILE,
        "presets.json":PRESETS_FILE,
        "recovery_project.json":RECOVERY_FILE,
        "recents.json":RECENTS_FILE,
        "encoder_cache.json":ENCODER_CACHE_FILE,
    }
    for name,dst in file_map.items():
        try:
            if _copy_if_missing(legacy/name,dst):migrated.append(name)
        except Exception:
            pass
    # SQLite backup preserves committed queue state without relying on copying WAL/SHM files.
    old_queue=legacy/"queue.sqlite3"
    if old_queue.is_file() and not QUEUE_DB.exists():
        try:
            QUEUE_DB.parent.mkdir(parents=True,exist_ok=True)
            src=sqlite3.connect(f"file:{old_queue}?mode=ro",uri=True,timeout=2)
            dst=sqlite3.connect(str(QUEUE_DB),timeout=2)
            try:src.backup(dst)
            finally:src.close();dst.close()
            migrated.append("queue.sqlite3")
        except Exception:
            try:QUEUE_DB.unlink(missing_ok=True)
            except Exception:pass
    for dirname,target in (("fonts",FONT_DIR),("transcriptions",TRANSCRIPTION_DIR)):
        src=legacy/dirname
        try:
            if src.is_dir() and not any(target.iterdir()):
                shutil.copytree(src,target,dirs_exist_ok=True)
                migrated.append(dirname+"/")
        except Exception:
            pass
    return migrated


LEGACY_MIGRATED_ITEMS = _migrate_legacy_user_state()
CONTAINER_CODECS = {
    ".mp4": {"H.264", "HEVC", "AV1"},
    ".mov": {"H.264", "HEVC"},
    ".mkv": {"H.264", "HEVC", "AV1", "VP9"},
    ".webm": {"AV1", "VP9"}
}
HARDWARE_MARKERS = ("_nvenc", "_qsv", "_amf", "_mf", "videotoolbox")

class SystemUsageSampler:
    def __init__(self):
        self._lock = threading.Lock()
        self._cpu_percent = None
        self._gpu_percent = None
        self._cpu_prev = None
        self._started = False
        self._nvidia_smi = self._find_nvidia_smi()

    def _find_nvidia_smi(self):
        if not IS_WINDOWS:
            return None
        found = shutil.which("nvidia-smi")
        if found:
            return found
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"
        return str(candidate) if candidate.is_file() else None

    @staticmethod
    def _filetime_value(ft):
        return (int(ft.dwHighDateTime) << 32) | int(ft.dwLowDateTime)

    def _sample_cpu(self):
        if not IS_WINDOWS:
            return None
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]
        idle = FILETIME(); kernel = FILETIME(); user = FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        current = (self._filetime_value(idle), self._filetime_value(kernel), self._filetime_value(user))
        prev = self._cpu_prev
        self._cpu_prev = current
        if prev is None:
            return None
        idle_delta = current[0] - prev[0]
        kernel_delta = current[1] - prev[1]
        user_delta = current[2] - prev[2]
        total = kernel_delta + user_delta
        if total <= 0:
            return None
        return max(0.0, min(100.0, (total - idle_delta) * 100.0 / total))

    def _sample_gpu(self):
        if not self._nvidia_smi:
            return None
        try:
            proc = subprocess.run(
                [self._nvidia_smi, "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5,
                creationflags=CREATE_NO_WINDOW,
            )
            if proc.returncode != 0:
                return None
            values=[]
            for line in proc.stdout.splitlines():
                try: values.append(float(line.strip()))
                except Exception: pass
            return max(values) if values else None
        except Exception:
            return None

    def _worker(self):
        while True:
            cpu = self._sample_cpu()
            gpu = self._sample_gpu()
            with self._lock:
                if cpu is not None: self._cpu_percent = cpu
                if gpu is not None: self._gpu_percent = gpu
            time.sleep(1.5)

    def start(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._worker, name="SubBurn-resource-monitor", daemon=True).start()

    def snapshot(self):
        with self._lock:
            return self._cpu_percent, self._gpu_percent

@dataclass
class MediaInfo:
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    video_bitrate: int = 0
    total_bitrate: int = 0
    audio_bitrate: int = 0
    audio_streams: list = field(default_factory=list)
    subtitle_streams: list = field(default_factory=list)
    # Extended source descriptor fields used for rendering, compatibility, and verification.
    video_stream_index: int = 0
    r_fps: float = 0.0
    avg_fps: float = 0.0
    frame_count: int = 0
    time_base: str = ""
    start_time: float = 0.0
    pixel_format: str = ""
    bit_depth: int = 0
    chroma_subsampling: str = ""
    has_alpha: bool = False
    profile: str = ""
    level: int = 0
    sample_aspect_ratio: str = ""
    display_aspect_ratio: str = ""
    rotation: int = 0
    display_width: int = 0
    display_height: int = 0
    field_order: str = ""
    interlaced: bool = False
    vfr_likely: bool = False
    frame_interval_p10_ms: float = 0.0
    frame_interval_p50_ms: float = 0.0
    frame_interval_p90_ms: float = 0.0
    timing_samples: int = 0
    color_range: str = ""
    color_space: str = ""
    color_transfer: str = ""
    color_primaries: str = ""
    hdr_mode: str = "SDR"
    mastering_display: str = ""
    max_cll: int = 0
    max_fall: int = 0
    dolby_vision_profile: int = 0
    dolby_vision_level: int = 0
    hdr_side_data_types: list = field(default_factory=list)
    format_name: str = ""
    file_size: int = 0


@dataclass
class FontRecord:
    label: str
    path: Path
    full_name: str
    family: str
    source: str
    coverage: set | None = None

@dataclass
class Toolset:
    ffmpeg: Path
    ffprobe: Path
    version: str
    filters: set
    encoders: list
    score: int
    decoders: set = field(default_factory=set)
    audio_encoders: set = field(default_factory=set)

@dataclass(frozen=True)
class NormalizedRect:
    x: float
    y: float
    w: float
    h: float
    label: str = ""

    def __post_init__(self):
        vals = (float(self.x), float(self.y), float(self.w), float(self.h))
        if any(not math.isfinite(v) for v in vals):
            raise ValueError("Safe-zone rectangle values must be finite")
        if self.x < 0 or self.y < 0 or self.w < 0 or self.h < 0 or self.x + self.w > 1.000001 or self.y + self.h > 1.000001:
            raise ValueError("Safe-zone rectangle must stay inside normalized frame coordinates")

    def display_box(self, left, top, width, height):
        return (
            left + self.x * width,
            top + self.y * height,
            left + (self.x + self.w) * width,
            top + (self.y + self.h) * height,
        )

@dataclass(frozen=True)
class SafeZonePreset:
    key: str
    name: str
    aspect_hint: str
    caption_safe: NormalizedRect
    watermark_safe: NormalizedRect
    obscured: tuple[NormalizedRect, ...] = ()
    note: str = ""

# These are deliberately conservative SubBurn guidance overlays, not claims that one rectangle
# exactly reproduces every device/platform UI. Platform UI changes by device, captions, CTA and
# add-ons; the UI labels these as guidance and asks users to verify in the platform preview.
SAFE_ZONE_PRESETS = {
    "Off": None,
    "Generic 16:9 title/action safe": SafeZonePreset(
        "generic_16_9", "Generic 16:9 title/action safe", "16:9",
        NormalizedRect(.10, .10, .80, .80, "caption safe"),
        NormalizedRect(.05, .05, .90, .90, "watermark safe"),
        (), "Conservative television-style title/action guide."),
    "Generic 9:16 social": SafeZonePreset(
        "generic_9_16", "Generic 9:16 social", "9:16",
        NormalizedRect(.08, .10, .76, .70, "caption safe"),
        NormalizedRect(.07, .08, .78, .74, "watermark safe"),
        (NormalizedRect(.86, .08, .14, .76, "right-side UI"), NormalizedRect(0, .83, 1, .17, "bottom UI")),
        "Conservative vertical-video guide."),
    "YouTube Shorts (conservative)": SafeZonePreset(
        "youtube_shorts", "YouTube Shorts (conservative)", "9:16",
        NormalizedRect(.06, .08, .76, .70, "caption safe"),
        NormalizedRect(.06, .07, .77, .72, "watermark safe"),
        (NormalizedRect(.84, .12, .16, .72, "right-hand controls"), NormalizedRect(0, .82, 1, .18, "description / CTA area")),
        "RHS controls and CTA/description placement can vary by surface/device."),
    "TikTok In-Feed LTR (conservative)": SafeZonePreset(
        "tiktok_ltr", "TikTok In-Feed LTR (conservative)", "9:16",
        NormalizedRect(.06, .08, .73, .69, "caption safe"),
        NormalizedRect(.06, .07, .74, .71, "watermark safe"),
        (NormalizedRect(.81, .09, .19, .70, "right-side TikTok UI"), NormalizedRect(0, .78, 1, .22, "caption / CTA / nav"), NormalizedRect(0, 0, 1, .055, "top device/UI area")),
        "TikTok publishes separate safe-zone assets; caption length/add-ons can shrink the safe region."),
    "TikTok In-Feed RTL (conservative)": SafeZonePreset(
        "tiktok_rtl", "TikTok In-Feed RTL (conservative)", "9:16",
        NormalizedRect(.21, .08, .73, .69, "caption safe"),
        NormalizedRect(.20, .07, .74, .71, "watermark safe"),
        (NormalizedRect(0, .09, .19, .70, "left-side RTL UI"), NormalizedRect(0, .78, 1, .22, "caption / CTA / nav"), NormalizedRect(0, 0, 1, .055, "top device/UI area")),
        "Mirrored conservative guide for TikTok's separately documented Arabic/RTL layout family."),
    "Instagram/Facebook Reels (conservative)": SafeZonePreset(
        "meta_reels", "Instagram/Facebook Reels (conservative)", "9:16",
        NormalizedRect(.07, .08, .75, .69, "caption safe"),
        NormalizedRect(.06, .07, .77, .71, "watermark safe"),
        (NormalizedRect(.84, .10, .16, .69, "right-side controls"), NormalizedRect(0, .78, 1, .22, "caption / controls")),
        "Conservative Reels guide; verify key elements with Meta's current safe-zone checker."),
}
SAFE_ZONE_PRESET_NAMES = list(SAFE_ZONE_PRESETS.keys())

@dataclass(frozen=True)
class SubtitleStyle:
    font_size: float = 28.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikeout: bool = False
    text_rgb: str = "FFFFFF"
    text_opacity: float = 100.0
    outline_rgb: str = "000000"
    outline_opacity: float = 100.0
    outline_width: float = 2.0
    shadow_rgb: str = "000000"
    shadow_opacity: float = 100.0
    shadow_depth: float = 0.0
    spacing: float = 0.0
    angle: float = 0.0
    alignment: int = 2
    margin_l: int = 10
    margin_r: int = 10
    margin_v: int = 32
    background_box: bool = False
    background_rgb: str = "000000"
    background_opacity: float = 65.0
    background_padding: float = 4.0

    @staticmethod
    def _ass_color(rgb, opacity):
        value = str(rgb).strip().lstrip("#").lstrip("＃")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
            raise ValueError("Subtitle style RGB colors must use six hexadecimal digits")
        opacity = float(opacity)
        if not math.isfinite(opacity) or opacity < 0 or opacity > 100:
            raise ValueError("Subtitle style opacity must be between 0 and 100")
        alpha = 255 - int(round(opacity / 100.0 * 255))
        bgr = value[4:6] + value[2:4] + value[0:2]
        return f"&H{alpha:02X}{bgr.upper()}"

    def ass_style_line(self, name, font_name):
        primary = self._ass_color(self.text_rgb, self.text_opacity)
        if self.background_box:
            # Standard ASS BorderStyle=3 is the portable opaque-box mode. In this mode the
            # OutlineColour/Outline fields form the box, so regular outline/shadow styling is
            # intentionally replaced rather than faked with a second renderer.
            outline_color = self._ass_color(self.background_rgb, self.background_opacity)
            back_color = outline_color
            border_style = 3
            outline = self.background_padding
            shadow = 0.0
        else:
            outline_color = self._ass_color(self.outline_rgb, self.outline_opacity)
            back_color = self._ass_color(self.shadow_rgb, self.shadow_opacity)
            border_style = 1
            outline = self.outline_width
            shadow = self.shadow_depth
        return (
            f"Style: {name},{font_name},{self.font_size:g},{primary},&H000000FF,{outline_color},{back_color},"
            f"{-1 if self.bold else 0},{-1 if self.italic else 0},{-1 if self.underline else 0},{-1 if self.strikeout else 0},"
            f"100,100,{self.spacing:g},{self.angle:g},{border_style},{outline:g},{shadow:g},{int(self.alignment)},"
            f"{int(self.margin_l)},{int(self.margin_r)},{int(self.margin_v)},1"
        )

@dataclass(frozen=True)
class CaptionEffectSpec:
    effect_id: str = "none"
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.effect_id not in set(CAPTION_EFFECT_ID_TO_LABEL):
            raise ValueError("Unknown caption effect")
        if not isinstance(self.params, dict):
            raise ValueError("Caption effect parameters must be a JSON object")
        active = str(self.params.get("active_rgb", "FFD400")).strip().lstrip("#").lstrip("＃")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", active):
            raise ValueError("Caption active-word RGB must use six hexadecimal digits")
        object.__setattr__(self, "params", {
            "active_rgb": active.upper(),
            "allow_estimated_timing": bool(self.params.get("allow_estimated_timing", True)),
        })

    def to_dict(self):
        return {"effect_id": self.effect_id, "params": dict(self.params)}

@dataclass
class Preset:
    id: str
    name: str
    panels: dict
    builtin: bool = False
    schema: int = 1

    def to_dict(self):
        return {"schema": int(self.schema), "id": self.id, "name": self.name, "builtin": bool(self.builtin), "panels": self.panels}

    @classmethod
    def from_dict(cls, data, *, builtin=False):
        if not isinstance(data, dict):
            raise ValueError("Preset must be a JSON object")
        schema = int(data.get("schema", 1))
        if schema != 1:
            raise ValueError(f"Unsupported preset schema {schema}")
        name = str(data.get("name", "")).strip()
        if not name or len(name) > 120:
            raise ValueError("Preset name must be 1-120 characters")
        preset_id = str(data.get("id") or uuid.uuid4().hex).strip()
        if not preset_id or len(preset_id) > 128:
            raise ValueError("Preset id is invalid")
        panels = data.get("panels")
        if not isinstance(panels, dict) or not panels:
            raise ValueError("Preset must contain at least one settings panel")
        allowed_panels = {"subtitles", "watermark", "encoding"}
        unknown = set(panels) - allowed_panels
        if unknown:
            raise ValueError("Unknown preset panel: " + ", ".join(sorted(unknown)))
        clean = {}
        for key, value in panels.items():
            if not isinstance(value, dict):
                raise ValueError(f"Preset panel '{key}' must be an object")
            clean[key] = json.loads(json.dumps(value, ensure_ascii=False))
        return cls(id=preset_id, name=name, panels=clean, builtin=bool(builtin or data.get("builtin", False)), schema=schema)

@dataclass
class BurnJob:
    """Snapshot-at-launch job state used by preview/encode workers and future queue/API layers.

    The object is intentionally a plain typed data container in this milestone.  Existing worker
    code can keep attribute access semantics while queue/preset/automation work gains one
    documented serialization boundary instead of duplicating snapshot_job() fields.
    """
    ffmpeg: str = ""
    primary_font: str = ""
    same_wm_font: bool = True
    wm_font: str = ""
    video: str = ""
    embedded_track: str = ""
    subtitle_file: str = ""
    subtitle_offset: str = "0"
    subtitle_source: str = "Auto"
    watermark_enabled: bool = False
    watermark_image: str = ""
    watermark_text: str = ""
    watermark_type: str = "Text"
    font_size: str = "28"
    force_bold: bool = False
    italic: bool = False
    underline: bool = False
    strikeout: bool = False
    text_opacity: str = "100"
    outline_opacity: str = "100"
    shadow_depth: str = "0"
    shadow_rgb: str = "000000"
    shadow_opacity: str = "100"
    letter_spacing: str = "0"
    rotation_angle: str = "0"
    subtitle_alignment: str = "Bottom center"
    margin_left: str = "10"
    margin_right: str = "10"
    background_box: bool = False
    background_rgb: str = "000000"
    background_opacity: str = "65"
    background_padding: str = "4"
    caption_effect_id: str = "none"
    caption_effect_params: dict = field(default_factory=lambda: {"active_rgb": "FFD400", "allow_estimated_timing": True})
    fps: str = "Original"
    margin: str = "24"
    outline_rgb: str = "000000"
    outline: str = "2"
    resolution: str = "Original"
    safe_area: str = "8"
    text_rgb: str = "FFFFFF"
    watermark_image_width: str = "15"
    watermark_image_scale: str = "100"
    watermark_image_x: str = ""
    watermark_image_y: str = ""
    watermark_margin: str = "20"
    watermark_opacity: float = 0.85
    watermark_outline: str = "2"
    watermark_position: str = "Top right"
    watermark_size: str = "24"
    watermark_timing: str = "Full duration"
    audio_mode: str = "Copy all audio"
    custom_bitrate: str = "2000"
    quality_mode: str = "Preserve visual quality"
    target_size: str = "100"
    codec: str = "Match source"
    output_ext: str = ".mp4"
    speed_mode: str = "Balanced"
    encoder_policy: str = "Balanced"
    encoder: str = "Auto"
    clean_output: bool = True
    output_dir: str = ""
    output_name: str = "SubBurn-output"
    metadata: dict = field(default_factory=dict)
    chapter: bool = True
    wrap_chars: str = "0"
    max_lines: str = "0"
    fallback_labels: list = field(default_factory=list)
    watermark_rows: list = field(default_factory=list)
    selected_interval_idx: int | None = None
    live_timestamp: float = 0.0
    live_generation: int = 0
    live_clip_timestamp: float = 0.0
    live_clip_duration: float = 0.0
    live_clip_generation: int = 0
    live_clip_open: bool = False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("BurnJob payload must be a JSON object")
        allowed = {f.name for f in dataclass_fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError("Unknown BurnJob field(s): " + ", ".join(sorted(unknown)))
        clean = dict(data)
        if "watermark_rows" in clean:
            rows = []
            for row in clean["watermark_rows"] or []:
                if not isinstance(row, (list, tuple)) or len(row) != 3:
                    raise ValueError("Each watermark interval must contain start, end, and position")
                rows.append((float(row[0]), float(row[1]), str(row[2])))
            clean["watermark_rows"] = rows
        if "fallback_labels" in clean:
            clean["fallback_labels"] = [str(x) for x in (clean["fallback_labels"] or [])]
        if "metadata" in clean:
            if not isinstance(clean["metadata"], dict):
                raise ValueError("BurnJob metadata must be a JSON object")
            clean["metadata"] = {str(k): str(v) for k, v in clean["metadata"].items()}
        if "caption_effect_params" in clean:
            if not isinstance(clean["caption_effect_params"], dict):
                raise ValueError("BurnJob caption_effect_params must be a JSON object")
            effect_id = str(clean.get("caption_effect_id", "none"))
            clean["caption_effect_params"] = CaptionEffectSpec(effect_id, clean["caption_effect_params"]).params
        return cls(**clean)

@dataclass(frozen=True)
class TranscriptionRequest:
    video: str
    model: str = "large-v3"
    language_mode: str = "Auto multilingual (detect changes)"
    language_code: str = ""
    allowed_languages: tuple = ()
    device: str = "Auto"
    allow_model_download: bool = False

@dataclass
class QueueItem:
    id: str
    position: int
    state: str
    job: BurnJob
    created_ts: float
    started_ts: float | None = None
    finished_ts: float | None = None
    error: str = ""
    output_path: str = ""
    retry_count: int = 0

def queue_item_to_dict(item, *, include_job=True):
    if item is None:
        return None
    data = {
        "id": item.id, "position": int(item.position), "state": item.state,
        "created_ts": item.created_ts, "started_ts": item.started_ts, "finished_ts": item.finished_ts,
        "error": item.error, "output_path": item.output_path, "retry_count": int(item.retry_count),
    }
    if include_job:
        data["job"] = item.job.to_dict()
    return data

class BurnQueueStore:
    STATES = {"queued", "running", "done", "failed", "cancelled"}
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._init_db()
        self.recover_interrupted()
    def _connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        return con
    @contextmanager
    def connection(self):
        """Open one queue connection for one operation and always close it on the same thread."""
        con = self._connect()
        try:
            with con:
                yield con
        finally:
            con.close()
    def _init_db(self):
        with self.lock, self.connection() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS queue_jobs (
                id TEXT PRIMARY KEY,
                position INTEGER NOT NULL,
                state TEXT NOT NULL,
                job_json TEXT NOT NULL,
                created_ts REAL NOT NULL,
                started_ts REAL,
                finished_ts REAL,
                error TEXT NOT NULL DEFAULT '',
                output_path TEXT NOT NULL DEFAULT '',
                retry_count INTEGER NOT NULL DEFAULT 0
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_queue_position ON queue_jobs(position)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_queue_state ON queue_jobs(state)")
    def recover_interrupted(self):
        with self.lock, self.connection() as con:
            con.execute("UPDATE queue_jobs SET state='queued', started_ts=NULL, finished_ts=NULL, error='Recovered after app restart before completion' WHERE state='running'")
    def _row_to_item(self, row):
        return QueueItem(
            id=row["id"], position=int(row["position"]), state=row["state"],
            job=BurnJob.from_dict(json.loads(row["job_json"])), created_ts=float(row["created_ts"]),
            started_ts=row["started_ts"], finished_ts=row["finished_ts"], error=row["error"] or "",
            output_path=row["output_path"] or "", retry_count=int(row["retry_count"] or 0),
        )
    def list_items(self, states=None):
        with self.lock, self.connection() as con:
            if states:
                states = tuple(states)
                marks = ",".join("?" for _ in states)
                rows = con.execute(f"SELECT * FROM queue_jobs WHERE state IN ({marks}) ORDER BY position,id", states).fetchall()
            else:
                rows = con.execute("SELECT * FROM queue_jobs ORDER BY position,id").fetchall()
        return [self._row_to_item(r) for r in rows]
    def get(self, item_id):
        with self.lock, self.connection() as con:
            row = con.execute("SELECT * FROM queue_jobs WHERE id=?", (str(item_id),)).fetchone()
        return self._row_to_item(row) if row else None
    def add(self, job, *, state="queued"):
        if state not in self.STATES:
            raise ValueError("Invalid queue state")
        if not isinstance(job, BurnJob):
            job = BurnJob.from_dict(job.to_dict() if hasattr(job, "to_dict") else dict(job))
        item_id = uuid.uuid4().hex
        now = time.time()
        with self.lock, self.connection() as con:
            row = con.execute("SELECT COALESCE(MAX(position),0)+1 AS p FROM queue_jobs").fetchone()
            position = int(row["p"])
            con.execute("INSERT INTO queue_jobs(id,position,state,job_json,created_ts) VALUES(?,?,?,?,?)",
                        (item_id, position, state, json.dumps(job.to_dict(), ensure_ascii=False), now))
        return self.get(item_id)
    def delete(self, item_id):
        with self.lock, self.connection() as con:
            row = con.execute("SELECT state FROM queue_jobs WHERE id=?", (str(item_id),)).fetchone()
            if not row:
                return False
            if row["state"] == "running":
                raise ValueError("Cannot remove the currently running queue item")
            con.execute("DELETE FROM queue_jobs WHERE id=?", (str(item_id),))
            self._normalize_positions(con)
        return True
    def _normalize_positions(self, con):
        ids = [r[0] for r in con.execute("SELECT id FROM queue_jobs ORDER BY position,id").fetchall()]
        for pos, item_id in enumerate(ids, 1):
            con.execute("UPDATE queue_jobs SET position=? WHERE id=?", (pos, item_id))
    def move(self, item_id, delta):
        with self.lock, self.connection() as con:
            rows = con.execute("SELECT id,state FROM queue_jobs ORDER BY position,id").fetchall()
            ids = [r["id"] for r in rows]
            states = {r["id"]: r["state"] for r in rows}
            item_id = str(item_id)
            if item_id not in ids:
                return False
            if states[item_id] == "running":
                raise ValueError("Cannot reorder the currently running queue item")
            i = ids.index(item_id); j = max(0, min(len(ids)-1, i + int(delta)))
            if i == j:
                return False
            if states.get(ids[j]) == "running":
                return False
            ids[i], ids[j] = ids[j], ids[i]
            for pos, qid in enumerate(ids, 1):
                con.execute("UPDATE queue_jobs SET position=? WHERE id=?", (pos, qid))
        return True
    def duplicate(self, item_id):
        item = self.get(item_id)
        if not item:
            return None
        return self.add(BurnJob.from_dict(item.job.to_dict()))
    def set_state(self, item_id, state, *, error=None, output_path=None, started=False, finished=False, increment_retry=False):
        if state not in self.STATES:
            raise ValueError("Invalid queue state")
        fields = ["state=?"]; values = [state]
        if error is not None: fields.append("error=?"); values.append(str(error))
        if output_path is not None: fields.append("output_path=?"); values.append(str(output_path))
        if started: fields.append("started_ts=?"); values.append(time.time())
        if finished: fields.append("finished_ts=?"); values.append(time.time())
        if increment_retry: fields.append("retry_count=retry_count+1")
        values.append(str(item_id))
        with self.lock, self.connection() as con:
            con.execute("UPDATE queue_jobs SET " + ",".join(fields) + " WHERE id=?", values)
    def retry(self, item_id):
        item = self.get(item_id)
        if not item or item.state not in {"failed", "cancelled"}:
            return False
        self.set_state(item_id, "queued", error="", output_path="", increment_retry=True)
        return True
    def retry_all_failed(self):
        with self.lock, self.connection() as con:
            cur = con.execute("UPDATE queue_jobs SET state='queued', error='', output_path='', retry_count=retry_count+1, started_ts=NULL, finished_ts=NULL WHERE state='failed'")
            return cur.rowcount
    def clear_completed(self):
        with self.lock, self.connection() as con:
            cur = con.execute("DELETE FROM queue_jobs WHERE state='done'")
            self._normalize_positions(con)
            return cur.rowcount
    def clear_queued(self):
        with self.lock, self.connection() as con:
            cur = con.execute("DELETE FROM queue_jobs WHERE state='queued'")
            self._normalize_positions(con)
            return cur.rowcount
    def find_equivalent_active(self, job):
        if not isinstance(job, BurnJob):
            job = BurnJob.from_dict(job.to_dict() if hasattr(job, "to_dict") else dict(job))
        target = json.dumps(job.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in self.list_items({"queued", "running"}):
            current = json.dumps(item.job.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if current == target:
                return item
        return None

@dataclass
class JobLog:
    path: Path
    lines: list = field(default_factory=list)
    def add(self, text):
        self.lines.append(f"[{time.strftime('%H:%M:%S')}] {text}")
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")

def run_capture(cmd, cwd=None, timeout=None):
    cp = subprocess.run([str(x) for x in cmd], cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=CREATE_NO_WINDOW)
    return cp.returncode, cp.stdout

def quick_file_fingerprint(path, chunk_size=1024*1024):
    p = Path(path)
    st = p.stat()
    h = hashlib.sha256()
    h.update(str(p.resolve()).encode("utf-8", errors="ignore"))
    h.update(f"|{st.st_size}|{st.st_mtime_ns}|".encode("ascii"))
    with p.open("rb") as f:
        head = f.read(min(chunk_size, st.st_size))
        h.update(head)
        if st.st_size > chunk_size:
            f.seek(max(0, st.st_size - chunk_size))
            h.update(f.read(chunk_size))
    return {"path": str(p.resolve()), "size": int(st.st_size), "mtime_ns": int(st.st_mtime_ns), "digest": h.hexdigest()}

def full_file_sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()







































def human_bytes(n):
    if n is None:
        return "unknown"
    n = float(n)
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or u == "TiB":
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TiB"

def human_bitrate(n):
    if not n:
        return "unknown"
    if n >= 1000000:
        return f"{n/1000000:.2f} Mbps"
    return f"{n/1000:.1f} kbps"

def parse_time_value(s):
    s = str(s).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    p = s.split(":")
    if len(p) == 2:
        return int(p[0]) * 60 + float(p[1])
    if len(p) == 3:
        return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
    raise ValueError(f"Invalid time: {s}")

def fmt_time(seconds):
    if seconds is None or not math.isfinite(seconds):
        return "--:--"
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{m:02d}:{s:06.3f}"

def fmt_minutes_seconds(seconds):
    if seconds is None or not math.isfinite(float(seconds)):
        return "--:--"
    total = max(0, int(round(float(seconds))))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"

def srt_time(seconds):
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    if s >= 60:
        m += 1
        s -= 60
    if m >= 60:
        h += 1
        m -= 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_srt_time(s):
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", s.strip())
    if not m:
        raise ValueError(f"Invalid SRT time: {s}")
    h, mi, sec, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(sec) + float("0." + ms[:3].ljust(3, "0"))

def fraction_float(s):
    if not s:
        return 0.0
    try:
        if "/" in s:
            a, b = s.split("/", 1)
            b = float(b)
            return float(a) / b if b else 0.0
        return float(s)
    except Exception:
        return 0.0

def safe_filename(s):
    s = str(s).strip()
    s = re.sub(r'[<>:"/\\|?*]', "_", s).rstrip(". ")
    return s or "SubBurn-output"

def unique_path(path):
    path = Path(path)
    if not path.exists():
        return path
    for i in range(1, 10000):
        p = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not p.exists():
            return p
    raise RuntimeError("Could not create unique filename")

def open_path(path):
    raw = str(path)
    if raw.startswith(("http://", "https://", "tg://")):
        target = raw
    else:
        target = str(Path(path))
    if IS_WINDOWS:
        os.startfile(target)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])

def normalize_key(s):
    return re.sub(r"[^0-9a-z]+", "", str(s).casefold())

def is_hardware_encoder(e):
    e = str(e).casefold()
    return any(x in e for x in HARDWARE_MARKERS)

def sanitize_subtitle_text(text):
    out = []
    for ch in unicodedata.normalize("NFC", str(text)):
        cat = unicodedata.category(ch)
        if ch in "\r\n":
            out.append(ch)
        elif ch == "\t":
            out.append(" ")
        elif cat == "Cc":
            continue
        elif ch in "\ufffd□":
            continue
        else:
            out.append(ch)
    return "".join(out).strip(" ")

def normalize_render_text(text):
    out = []
    for ch in unicodedata.normalize("NFC", str(text)):
        cat = unicodedata.category(ch)
        if ch == "\t" or cat.startswith("Z"):
            out.append(" ")
        elif cat in {"Cf", "Cc"} and ch not in "\r\n":
            continue
        else:
            out.append(ch)
    return "".join(out)

def sanitize_srt_file(src, dst):
    text = Path(src).read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    out = []
    index = 1
    for block in blocks:
        lines = [x.rstrip("\n") for x in block.split("\n") if x.strip()]
        if not lines:
            continue
        time_i = None
        for i, line in enumerate(lines):
            if "-->" in line:
                time_i = i
                break
        if time_i is None:
            continue
        body = [sanitize_subtitle_text(x) for x in lines[time_i + 1:]]
        body = [x for x in body if x]
        if not body:
            continue
        out.append(str(index))
        out.append(lines[time_i].strip())
        out.extend(body)
        out.append("")
        index += 1
    Path(dst).write_text("\n".join(out), encoding="utf-8")

def read_srt_cues(path):
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text)
    cues = []
    for block in blocks:
        lines = [x.strip("\n") for x in block.split("\n") if x.strip()]
        if not lines:
            continue
        ti = None
        for i, line in enumerate(lines):
            if "-->" in line:
                ti = i
                break
        if ti is None:
            continue
        left, right = lines[ti].split("-->", 1)
        start = parse_srt_time(left.strip().split()[0])
        end = parse_srt_time(right.strip().split()[0])
        body = [sanitize_subtitle_text(x) for x in lines[ti + 1:]]
        body = [x for x in body if x]
        if end > start and body:
            cues.append((start, end, body))
    return cues

def write_srt_cues(cues, path):
    out = []
    for i, (start, end, body) in enumerate(cues, 1):
        out.append(str(i))
        out.append(f"{srt_time(start)} --> {srt_time(end)}")
        out.extend(body)
        out.append("")
    Path(path).write_text("\n".join(out), encoding="utf-8")

def crop_shift_srt(src, dst, start, duration):
    end_window = start + duration
    out = []
    for a, b, body in read_srt_cues(src):
        x = max(a, start)
        y = min(b, end_window)
        if y > x:
            out.append((x - start, y - start, body))
    write_srt_cues(out, dst)

def subtitle_characters(path):
    chars = set()
    saw_space = False
    for _, _, body in read_srt_cues(path):
        for line in body:
            for ch in line:
                cat = unicodedata.category(ch)
                if ch.isspace() or cat[0] == "Z":
                    saw_space = True
                elif cat not in {"Cf", "Cc"}:
                    chars.add(ch)
    if saw_space:
        chars.add(" ")
    return chars

def decode_font_name(platform, raw):
    try:
        if platform in (0, 3):
            return raw.decode("utf-16-be", errors="replace").strip("\x00 ").strip()
        if platform == 1:
            return raw.decode("mac_roman", errors="replace").strip("\x00 ").strip()
        return raw.decode("utf-8", errors="replace").strip("\x00 ").strip()
    except Exception:
        return ""

def sfnt_table_map(data):
    if len(data) < 12 or data[:4] == b"ttcf":
        return {}
    count = struct.unpack(">H", data[4:6])[0]
    pos = 12
    tables = {}
    for _ in range(count):
        rec = data[pos:pos + 16]
        pos += 16
        if len(rec) != 16:
            break
        tag, checksum, off, length = struct.unpack(">4sIII", rec)
        tables[tag.decode("latin1")] = (off, length)
    return tables

def read_font_names(path):
    try:
        data = Path(path).read_bytes()
        tables = sfnt_table_map(data)
        if "name" not in tables:
            return {}
        off, length = tables["name"]
        table = data[off:off + length]
        if len(table) < 6:
            return {}
        fmt, count, string_off = struct.unpack(">HHH", table[:6])
        result = {}
        pos = 6
        for _ in range(count):
            rec = table[pos:pos + 12]
            pos += 12
            if len(rec) != 12:
                break
            platform, encoding, language, name_id, size, start = struct.unpack(">HHHHHH", rec)
            a = string_off + start
            b = a + size
            if b <= len(table):
                value = decode_font_name(platform, table[a:b])
                if value and value not in result.setdefault(name_id, []):
                    result[name_id].append(value)
        return result
    except Exception:
        return {}

def read_cmap_coverage(path):
    try:
        data = Path(path).read_bytes()
        tables = sfnt_table_map(data)
        if "cmap" not in tables:
            return set()
        off, length = tables["cmap"]
        cmap = data[off:off + length]
        if len(cmap) < 4:
            return set()
        count = struct.unpack(">H", cmap[2:4])[0]
        subtables = []
        pos = 4
        for _ in range(count):
            rec = cmap[pos:pos + 8]
            pos += 8
            if len(rec) != 8:
                break
            platform, encoding, suboff = struct.unpack(">HHI", rec)
            if suboff < len(cmap):
                subtables.append((platform, encoding, suboff))
        coverage = set()
        for platform, encoding, suboff in subtables:
            if suboff + 2 > len(cmap):
                continue
            fmt = struct.unpack(">H", cmap[suboff:suboff + 2])[0]
            if fmt == 0 and suboff + 262 <= len(cmap):
                arr = cmap[suboff + 6:suboff + 262]
                for cp, gid in enumerate(arr):
                    if gid:
                        coverage.add(cp)
            elif fmt == 4 and suboff + 8 <= len(cmap):
                length4 = struct.unpack(">H", cmap[suboff + 2:suboff + 4])[0]
                t = cmap[suboff:suboff + length4]
                if len(t) < 16:
                    continue
                seg_count = struct.unpack(">H", t[6:8])[0] // 2
                end_pos = 14
                start_pos = end_pos + 2 * seg_count + 2
                delta_pos = start_pos + 2 * seg_count
                range_pos = delta_pos + 2 * seg_count
                for i in range(seg_count):
                    endc = struct.unpack(">H", t[end_pos + 2 * i:end_pos + 2 * i + 2])[0]
                    startc = struct.unpack(">H", t[start_pos + 2 * i:start_pos + 2 * i + 2])[0]
                    if startc == 0xFFFF and endc == 0xFFFF:
                        continue
                    for cp in range(startc, min(endc, 0xFFFF) + 1):
                        coverage.add(cp)
            elif fmt == 12 and suboff + 16 <= len(cmap):
                length12 = struct.unpack(">I", cmap[suboff + 4:suboff + 8])[0]
                t = cmap[suboff:suboff + length12]
                if len(t) < 16:
                    continue
                groups = struct.unpack(">I", t[12:16])[0]
                pos2 = 16
                for _ in range(groups):
                    rec = t[pos2:pos2 + 12]
                    pos2 += 12
                    if len(rec) != 12:
                        break
                    startc, endc, startgid = struct.unpack(">III", rec)
                    for cp in range(startc, min(endc, 0x10FFFF) + 1):
                        coverage.add(cp)
        return coverage
    except Exception:
        return set()

def ensure_fonttools_runtime():
    """Load the packaged/source dependency without modifying the Python environment."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        return TTFont, TTGlyphPen
    except Exception as exc:
        raise RuntimeError(
            "FontTools is unavailable. Install SubBurn with its declared Python dependencies "
            "or use an official packaged build; SubBurn will not run pip automatically."
        ) from exc

_GRAPHEME_PATTERN = None
_GRAPHEME_PATTERN_LOCK = threading.Lock()

def ensure_grapheme_pattern():
    """Return the packaged Unicode Extended Grapheme Cluster matcher (UAX #29 \\X)."""
    global _GRAPHEME_PATTERN
    if _GRAPHEME_PATTERN is not None:
        return _GRAPHEME_PATTERN
    with _GRAPHEME_PATTERN_LOCK:
        if _GRAPHEME_PATTERN is not None:
            return _GRAPHEME_PATTERN
        try:
            import regex as regex_module
        except Exception as exc:
            raise RuntimeError(
                "The 'regex' dependency is unavailable. Install SubBurn with its declared Python "
                "dependencies or use an official packaged build; SubBurn will not run pip automatically."
            ) from exc
        try:
            _GRAPHEME_PATTERN = regex_module.compile(r"\X")
        except Exception as exc:
            raise RuntimeError("Unicode grapheme segmentation engine is unusable: " + str(exc))
        return _GRAPHEME_PATTERN

_FASTER_WHISPER_RUNTIME = None
_FASTER_WHISPER_LOCK = threading.Lock()

def ensure_faster_whisper_runtime(allow_install=False):
    """Load faster-whisper/CTranslate2 without installing packages at runtime.

    `allow_install` remains in the internal signature for compatibility with existing call sites,
    but public SubBurn never invokes pip. Official packages must ship the dependency; source users
    install the declared transcription extra before using this feature.
    """
    global _FASTER_WHISPER_RUNTIME
    if _FASTER_WHISPER_RUNTIME is not None:
        return _FASTER_WHISPER_RUNTIME
    with _FASTER_WHISPER_LOCK:
        if _FASTER_WHISPER_RUNTIME is not None:
            return _FASTER_WHISPER_RUNTIME
        try:
            fw = importlib.import_module("faster_whisper")
            WhisperModel = getattr(fw, "WhisperModel")
            BatchedInferencePipeline = getattr(fw, "BatchedInferencePipeline")
            params = inspect.signature(BatchedInferencePipeline.transcribe).parameters
            if "multilingual" not in params or "word_timestamps" not in params:
                raise RuntimeError("installed faster-whisper is too old for SubBurn transcription")
            ct2 = importlib.import_module("ctranslate2")
        except Exception as exc:
            raise RuntimeError(
                "The local transcription runtime is not installed. Install SubBurn with its "
                "transcription dependencies or use an official packaged build. SubBurn does not "
                "run pip or modify Python environments at runtime. Technical detail: " + str(exc)
            ) from exc
        _FASTER_WHISPER_RUNTIME = (WhisperModel, BatchedInferencePipeline, ct2)
        return _FASTER_WHISPER_RUNTIME

def transcription_model_marker(model_name):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(model_name)).strip("._") or "model"
    return TRANSCRIPTION_MODEL_DIR / f"{safe}.ready.json"

def _read_json_file(path, default=None):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return raw
    except Exception:
        return {} if default is None else default

def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def directory_size_bytes(path):
    total = 0
    root = Path(path)
    if not root.exists():
        return 0
    try:
        for p in root.rglob("*"):
            try:
                if p.is_file() and not p.is_symlink():
                    total += p.stat().st_size
            except Exception:
                pass
    except Exception:
        pass
    return int(total)

def transcription_model_source(model_name):
    name = str(model_name or "").strip()
    source = TRANSCRIPTION_MODEL_SOURCES.get(name)
    if not isinstance(source, dict):
        raise ValueError(f"Unknown transcription model: {name or 'empty'}")
    repo = str(source.get("repo") or "").strip()
    revision = str(source.get("revision") or "").strip().lower()
    license_id = str(source.get("license") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise RuntimeError(f"Invalid pinned repository for transcription model {name}")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError(f"Invalid immutable revision for transcription model {name}")
    if not license_id:
        raise RuntimeError(f"Missing license metadata for transcription model {name}")
    out = dict(source)
    out.update({"model": name, "repo": repo, "revision": revision, "license": license_id})
    return out

def transcription_model_repo(model_name):
    return transcription_model_source(model_name)["repo"]

def transcription_model_revision(model_name):
    return transcription_model_source(model_name)["revision"]

def transcription_model_install_dir(model_name):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(model_name)).strip("._") or "model"
    return TRANSCRIPTION_MODEL_DIR / safe

def transcription_model_local_bytes(model_name):
    # Report bytes that actually exist now.  A stale marker must never make a deleted or
    # superseded model look installed.
    return directory_size_bytes(transcription_model_install_dir(model_name))

def _hf_allowed_model_file(name):
    base = str(name or "").rsplit("/", 1)[-1]
    return base in set(TRANSCRIPTION_MODEL_ALLOW_PATTERNS)

def _transcription_model_files_valid(path):
    root = Path(path)
    required = ("config.json", "model.bin", "tokenizer.json")
    if not root.is_dir() or any(not (root / name).is_file() for name in required):
        return False
    return (root / "vocabulary.json").is_file() or (root / "vocabulary.txt").is_file()

def _small_model_file_manifest(path):
    root = Path(path)
    manifest = {}
    for name in ("config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "vocabulary.txt"):
        candidate = root / name
        if candidate.is_file():
            manifest[name] = {"size": int(candidate.stat().st_size), "sha256": full_file_sha256(candidate)}
    model_bin = root / "model.bin"
    if model_bin.is_file():
        manifest["model.bin"] = {"size": int(model_bin.stat().st_size), "sha256": "not-computed-large-file"}
    return manifest

def _huggingface_snapshot_download(**kwargs):
    try:
        hub = importlib.import_module("huggingface_hub")
        fn = getattr(hub, "snapshot_download")
    except Exception as exc:
        raise RuntimeError(
            "The transcription download helper is unavailable. Install SubBurn with its "
            "transcription dependencies or use an official packaged build. Technical detail: " + str(exc)
        ) from exc
    return fn(**kwargs)

class TranscriptionModelPreparationCancelled(RuntimeError):
    """Raised when a user cancels a killable transcription-model preparation transfer."""

def _huggingface_snapshot_download_cancellable(source, local_dir, cancel_event, *, poll_interval=0.20, _command=None):
    """Run snapshot_download in a helper process so a user cancellation can really stop I/O.

    ``huggingface_hub.snapshot_download`` does not expose a portable cancellation token for an
    in-flight transfer. Running it in a short-lived child keeps the main SubBurn process safe:
    cancelling terminates only the downloader, and the caller's staging/finally logic removes
    incomplete bytes before any ready marker can be written. ``_command`` is an internal test
    hook; production callers always use the pinned repository/revision command built here.
    """
    if cancel_event is not None and cancel_event.is_set():
        raise TranscriptionModelPreparationCancelled("Transcription model download cancelled")
    local_dir = Path(local_dir)
    if _command is None:
        payload = json.dumps({
            "repo": str(source["repo"]),
            "revision": str(source["revision"]),
            "allow_patterns": list(TRANSCRIPTION_MODEL_ALLOW_PATTERNS),
            "local_dir": str(local_dir),
        }, ensure_ascii=False)
        child_code = (
            "import json,sys; "
            "from huggingface_hub import snapshot_download; "
            "c=json.loads(sys.argv[1]); "
            "snapshot_download(repo_id=c['repo'],revision=c['revision'],"
            "allow_patterns=c['allow_patterns'],local_dir=c['local_dir'])"
        )
        command = [sys.executable, "-c", child_code, payload]
    else:
        command = [str(x) for x in _command]
    local_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(mode="w+b") as child_log:
        proc = subprocess.Popen(
            command, stdout=child_log, stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )
        while True:
            rc = proc.poll()
            if rc is not None:
                break
            if cancel_event is not None and cancel_event.wait(max(0.02, float(poll_interval))):
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=5)
                raise TranscriptionModelPreparationCancelled("Transcription model download cancelled")
            if cancel_event is None:
                time.sleep(max(0.02, float(poll_interval)))
        if rc != 0:
            child_log.flush(); child_log.seek(0, os.SEEK_END); size = child_log.tell()
            child_log.seek(max(0, size - 8192)); detail = child_log.read().decode("utf-8", errors="replace").strip()
            if detail:
                detail = detail[-4000:]
            raise RuntimeError("Pinned transcription model download helper failed" + (": " + detail if detail else f" (exit {rc})"))
    return str(local_dir)

def prepare_transcription_model_snapshot(model_name, progress=None, cancel_event=None, phase=None):
    """Download exactly one audited model revision and atomically install it.

    A ready model is returned without touching the network. Concurrent callers serialize on
    the per-model install lock and re-check readiness after acquiring it, so one underlying
    download serves every waiter. When possible, progress reports exact pinned-revision bytes;
    otherwise it reports bytes/rate with an unknown total rather than inventing a percentage.
    """
    source = transcription_model_source(model_name)
    target = transcription_model_install_dir(model_name)
    if transcription_model_ready(model_name):
        return target
    TRANSCRIPTION_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".new")
    old = target.with_name(target.name + ".old")
    with _dependency_install_lock("transcription-model-" + str(model_name), timeout=3600.0, lock_dir=TRANSCRIPTION_MODEL_DIR):
        if transcription_model_ready(model_name):
            return target
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)
        staged.mkdir(parents=True, exist_ok=True)
        monitor_stop = threading.Event()
        monitor_thread = None
        expected_total = 0
        if progress is not None:
            try:
                meta = transcription_model_metadata(model_name, refresh=False, timeout=8.0, online=True)
                if str(meta.get("download_size_source") or "") != "estimate":
                    expected_total = max(0, int(meta.get("download_bytes") or 0))
            except Exception:
                expected_total = 0
            def monitor():
                while not monitor_stop.wait(0.20):
                    try:
                        progress(directory_size_bytes(staged), expected_total)
                    except Exception:
                        pass
            monitor_thread = threading.Thread(target=monitor, daemon=True, name=f"SubBurn-{model_name}-download-progress")
            monitor_thread.start()
        try:
            if phase:
                phase("Downloading the pinned transcription model.")
            if cancel_event is None:
                _huggingface_snapshot_download(
                    repo_id=source["repo"],
                    revision=source["revision"],
                    allow_patterns=list(TRANSCRIPTION_MODEL_ALLOW_PATTERNS),
                    local_dir=str(staged),
                )
            else:
                _huggingface_snapshot_download_cancellable(source, staged, cancel_event)
            if cancel_event is not None and cancel_event.is_set():
                raise TranscriptionModelPreparationCancelled("Transcription model download cancelled")
            if phase:
                phase("Validating the downloaded transcription model.")
            shutil.rmtree(staged / ".cache", ignore_errors=True)
            if not _transcription_model_files_valid(staged):
                raise RuntimeError("Pinned transcription snapshot is incomplete or missing required CTranslate2 files")
            if progress is not None:
                final_bytes = directory_size_bytes(staged)
                progress(final_bytes, expected_total or final_bytes)
            if phase:
                phase("Installing the verified transcription model.")
            if old.exists():
                shutil.rmtree(old, ignore_errors=True)
            moved_old = False
            if target.exists():
                os.replace(target, old)
                moved_old = True
            try:
                os.replace(staged, target)
            except Exception:
                if moved_old and old.exists() and not target.exists():
                    os.replace(old, target)
                raise
            if old.exists():
                shutil.rmtree(old, ignore_errors=True)
            write_transcription_marker(model_name, "prepared")
            if phase:
                phase("Transcription model installed and ready.")
            return target
        finally:
            monitor_stop.set()
            if monitor_thread is not None:
                monitor_thread.join(timeout=1.0)
            if staged.exists():
                shutil.rmtree(staged, ignore_errors=True)
            if old.exists() and target.exists():
                shutil.rmtree(old, ignore_errors=True)

def fetch_transcription_model_download_bytes(model_name, timeout=8.0):
    """Return advertised bytes for the exact pinned Hugging Face revision, when reachable."""
    source = transcription_model_source(model_name)
    url = ("https://huggingface.co/api/models/" + urllib.parse.quote(source["repo"], safe="/")
           + "/revision/" + urllib.parse.quote(source["revision"], safe="") + "?blobs=true")
    req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=float(timeout)) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    total = 0
    found = 0
    for item in payload.get("siblings") or []:
        if not _hf_allowed_model_file(item.get("rfilename")):
            continue
        size = item.get("size")
        if size is None and isinstance(item.get("lfs"), dict):
            size = item["lfs"].get("size")
        if size is None:
            continue
        try:
            total += int(size)
            found += 1
        except Exception:
            pass
    if total <= 0 or found <= 0:
        raise RuntimeError("Hugging Face metadata did not include downloadable model file sizes")
    return int(total)

def transcription_model_metadata(model_name, refresh=False, timeout=8.0, online=True):
    model_name = str(model_name)
    source_info = transcription_model_source(model_name)
    cache = _read_json_file(TRANSCRIPTION_MODEL_METADATA_CACHE, {})
    cached = cache.get(model_name) if isinstance(cache, dict) else None
    if isinstance(cached, dict) and (cached.get("repo") != source_info["repo"] or cached.get("revision") != source_info["revision"]):
        cached = None
    now = time.time()
    exact_bytes = None
    source = "estimate"
    if isinstance(cached, dict):
        try:
            age = now - float(cached.get("checked_at") or 0)
            if age <= 30 * 86400 and int(cached.get("download_bytes") or 0) > 0 and not refresh:
                exact_bytes = int(cached["download_bytes"])
                source = "cached-online"
        except Exception:
            pass
    online_error = ""
    if online and exact_bytes is None:
        try:
            exact_bytes = fetch_transcription_model_download_bytes(model_name, timeout=timeout)
            source = "online"
            if not isinstance(cache, dict):
                cache = {}
            cache[model_name] = {
                "download_bytes": exact_bytes,
                "checked_at": now,
                "repo": source_info["repo"],
                "revision": source_info["revision"],
            }
            _atomic_write_json(TRANSCRIPTION_MODEL_METADATA_CACHE, cache)
        except Exception as exc:
            online_error = str(exc)
    if exact_bytes is None:
        try:
            if isinstance(cached, dict) and int(cached.get("download_bytes") or 0) > 0:
                exact_bytes = int(cached["download_bytes"])
                source = "stale-cache"
        except Exception:
            pass
    if exact_bytes is None:
        exact_bytes = int(TRANSCRIPTION_MODEL_ESTIMATED_BYTES.get(model_name, 0))
        source = "estimate"
    installed = transcription_model_local_bytes(model_name)
    try:
        usage = shutil.disk_usage(TRANSCRIPTION_MODEL_DIR if TRANSCRIPTION_MODEL_DIR.exists() else RUNTIME_DIR)
        free_bytes = int(usage.free)
    except Exception:
        free_bytes = 0
    guidance = TRANSCRIPTION_MODEL_MEMORY_GUIDANCE.get(model_name, {})
    return {
        "model": model_name,
        "repo": source_info["repo"],
        "revision": source_info["revision"],
        "license": source_info["license"],
        "upstream": source_info.get("upstream", ""),
        "download_bytes": int(exact_bytes or 0),
        "download_size_source": source,
        "installed_bytes": int(installed or 0),
        "free_bytes": free_bytes,
        "ram_guidance": str(guidance.get("ram") or "device dependent"),
        "vram_guidance": str(guidance.get("vram") or "device/compute-type dependent"),
        "ready": transcription_model_ready(model_name),
        "online_error": online_error,
    }

def format_transcription_model_metadata(meta):
    source = str(meta.get("download_size_source") or "estimate")
    exact = source in {"online", "cached-online"}
    download = human_bytes(int(meta.get("download_bytes") or 0)) if int(meta.get("download_bytes") or 0) else "unknown"
    installed = human_bytes(int(meta.get("installed_bytes") or 0)) if int(meta.get("installed_bytes") or 0) else "not installed"
    free = human_bytes(int(meta.get("free_bytes") or 0)) if int(meta.get("free_bytes") or 0) else "unknown"
    qualifier = "pinned-revision metadata" if exact else "estimated"
    state = "ready locally" if meta.get("ready") else "not prepared"
    rev = str(meta.get("revision") or "")[:12]
    return (f"Download: {download} ({qualifier})   |   Installed: {installed}   |   Free disk: {free}   |   {state}\n"
            f"Source: {meta.get('repo')}@{rev}   |   License: {meta.get('license')}\n"
            f"RAM: {meta.get('ram_guidance')}   |   VRAM: {meta.get('vram_guidance')}")

def transcription_model_download_message(model_name):
    meta = transcription_model_metadata(model_name, refresh=False, timeout=0.01, online=False)
    model_bytes = int(meta.get("download_bytes") or 0)
    size_text = human_bytes(model_bytes) if model_bytes > 0 else "size unknown"
    source = str(meta.get("download_size_source") or "")
    size_kind = "estimated" if source.startswith("estimate") else "cached size"
    return (f"Downloading the pinned {model_name} transcription model ({size_text}, {size_kind}) once for local "
            "transcription; it will be reused.")

def parse_allowed_language_codes(text):
    raw = re.split(r"[,;\s]+", str(text or "").strip().lower())
    out = []
    for code in raw:
        if not code:
            continue
        if not re.fullmatch(r"[a-z]{2,3}", code):
            raise ValueError(f"Invalid Whisper language code '{code}'. Use codes such as ar, he, en, zh, or yue.")
        if code not in WHISPER_LANGUAGES:
            hint = " Use 'zh' for Chinese/Mandarin or 'yue' for Cantonese." if code in {"cn", "ch"} else ""
            raise ValueError(f"Unsupported Whisper language code '{code}'.{hint}")
        if code not in out:
            out.append(code)
    return tuple(out)


def merge_vad_speech_windows(speech_chunks, sampling_rate, duration, *,
                             target=TRANSCRIPTION_ALLOWED_WINDOW_TARGET,
                             minimum=TRANSCRIPTION_ALLOWED_WINDOW_MIN,
                             maximum=TRANSCRIPTION_ALLOWED_WINDOW_MAX,
                             merge_gap=1.5):
    """Merge tiny VAD regions into bounded context windows for reliable language detection."""
    sr = max(1.0, float(sampling_rate or 16000))
    total = max(0.0, float(duration or 0.0))
    target = max(float(minimum), min(float(maximum), float(target)))
    minimum = max(0.25, min(float(minimum), target))
    maximum = max(target, float(maximum))
    spans = []
    for chunk in speech_chunks or []:
        try:
            a = max(0.0, float(chunk.get("start", 0)) / sr)
            b = max(a, float(chunk.get("end", 0)) / sr)
        except Exception:
            continue
        if total > 0:
            a, b = min(a, total), min(b, total)
        if b > a:
            spans.append((a, b))
    spans.sort()
    if not spans:
        if total <= 0:
            return []
        out = []
        a = 0.0
        while a < total:
            out.append((round(a, 3), round(min(total, a + maximum), 3)))
            a += maximum
        return out
    split_spans = []
    for a, b in spans:
        cur = a
        while b - cur > maximum:
            split_spans.append((cur, cur + maximum))
            cur += maximum
        if b > cur:
            split_spans.append((cur, b))
    windows = []
    cur_a = cur_b = None
    for a, b in split_spans:
        if cur_a is None:
            cur_a, cur_b = a, b
            continue
        proposed_span = b - cur_a
        gap = max(0.0, a - cur_b)
        if proposed_span <= maximum and (cur_b - cur_a < target or gap <= merge_gap):
            cur_b = b
        else:
            windows.append((cur_a, cur_b))
            cur_a, cur_b = a, b
    if cur_a is not None:
        windows.append((cur_a, cur_b))
    if len(windows) >= 2 and windows[-1][1] - windows[-1][0] < minimum:
        pa, _pb = windows[-2]
        _ta, tb = windows[-1]
        if tb - pa <= maximum:
            windows[-2:] = [(pa, tb)]
    fixed = []
    for idx2, (a, b) in enumerate(windows):
        if b - a < minimum:
            need = minimum - (b - a)
            left_bound = fixed[-1][1] if fixed else 0.0
            right_bound = windows[idx2 + 1][0] if idx2 + 1 < len(windows) else (total if total > 0 else b + need)
            left = min(need / 2.0, max(0.0, a - left_bound))
            a -= left
            need -= left
            b += min(need, max(0.0, right_bound - b))
        fixed.append((round(a, 3), round(b, 3)))
    return fixed

def choose_allowed_language(all_language_probs, allowed_languages):
    allowed = {str(x).lower() for x in (allowed_languages or ())}
    ranked = []
    for item in all_language_probs or []:
        try:
            code, prob = str(item[0]).lower(), float(item[1])
        except Exception:
            continue
        ranked.append((code, prob))
    permitted = [(code, prob) for code, prob in ranked if code in allowed]
    if not permitted:
        return None, 0.0, tuple(ranked)
    permitted.sort(key=lambda x: x[1], reverse=True)
    code, prob = permitted[0]
    return code, float(prob), tuple(ranked)

def transcription_model_ready(model_name):
    try:
        source = transcription_model_source(model_name)
        target = transcription_model_install_dir(model_name)
        raw = _read_json_file(transcription_model_marker(model_name), {})
        return (
            bool(raw.get("ready"))
            and str(raw.get("model")) == str(model_name)
            and str(raw.get("repo")) == source["repo"]
            and str(raw.get("revision")) == source["revision"]
            and str(raw.get("license")) == source["license"]
            and _transcription_model_files_valid(target)
        )
    except Exception:
        return False

def write_transcription_marker(model_name, device="prepared"):
    source = transcription_model_source(model_name)
    target = transcription_model_install_dir(model_name)
    if not _transcription_model_files_valid(target):
        raise RuntimeError("Cannot mark an incomplete transcription model as ready")
    payload = {
        "schema": 2,
        "ready": True,
        "model": str(model_name),
        "repo": source["repo"],
        "revision": source["revision"],
        "license": source["license"],
        "upstream": source.get("upstream", ""),
        "prepared_at": time.time(),
        "device": str(device),
        "installed_bytes": directory_size_bytes(target),
        "files": _small_model_file_manifest(target),
    }
    _atomic_write_json(transcription_model_marker(model_name), payload)

def detected_unicode_scripts(text):
    scripts = set()
    for ch in str(text):
        cp = ord(ch)
        if 0x0590 <= cp <= 0x05FF:
            scripts.add("Hebrew")
        elif 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0x08A0 <= cp <= 0x08FF:
            scripts.add("Arabic")
        elif (0x0041 <= cp <= 0x024F):
            scripts.add("Latin")
        elif 0x0900 <= cp <= 0x097F:
            scripts.add("Devanagari")
        elif 0x0E00 <= cp <= 0x0E7F:
            scripts.add("Thai")
        elif 0x3040 <= cp <= 0x30FF:
            scripts.add("Japanese")
        elif 0x4E00 <= cp <= 0x9FFF:
            scripts.add("Han")
        elif 0xAC00 <= cp <= 0xD7AF:
            scripts.add("Hangul")
    return sorted(scripts)

def repair_font_for_render(src, dst, runtime_name=None):
    shutil.copy2(src, dst)
    try:
        TTFont, TTGlyphPen = ensure_fonttools_runtime()
        font = TTFont(dst)
        cmap = font.getBestCmap() or {}
        glyph_order = font.getGlyphOrder()
        space_glyph = cmap.get(0x20)
        if not space_glyph:
            for name in ("space", "uni0020", "u0020"):
                if name in glyph_order:
                    space_glyph = name
                    break
        if not space_glyph and "glyf" in font:
            space_glyph = "space"
            if space_glyph not in glyph_order:
                glyph_order.append(space_glyph)
                font.setGlyphOrder(glyph_order)
            pen = TTGlyphPen(None)
            font["glyf"][space_glyph] = pen.glyph()
            if "hmtx" in font:
                font["hmtx"][space_glyph] = (max(200, int(getattr(font["head"], "unitsPerEm", 1000) * 0.2)), 0)
        if space_glyph:
            if "glyf" in font and space_glyph in font["glyf"]:
                pen = TTGlyphPen(None)
                font["glyf"][space_glyph] = pen.glyph()
            if "hmtx" in font:
                width = font["hmtx"].metrics.get(space_glyph, (0, 0))[0]
                if not width or width < 1:
                    width = max(200, int(getattr(font["head"], "unitsPerEm", 1000) * 0.2))
                font["hmtx"][space_glyph] = (width, 0)
            for table in font["cmap"].tables:
                if getattr(table, "isUnicode", lambda: False)():
                    for cp in SPACE_CODEPOINTS:
                        table.cmap[cp] = space_glyph
        if runtime_name:
            post = re.sub(r"[^A-Za-z0-9]", "", runtime_name) or "SubBurnRuntimeFont"
            for name in list(font["name"].names):
                if name.nameID in {1, 4, 16, 17}:
                    try:
                        if name.platformID in {0, 3}:
                            name.string = runtime_name.encode("utf-16-be")
                        elif name.platformID == 1:
                            name.string = runtime_name.encode("mac_roman", errors="ignore")
                        else:
                            name.string = runtime_name.encode("utf-8")
                    except Exception:
                        pass
                elif name.nameID == 6:
                    try:
                        if name.platformID in {0, 3}:
                            name.string = post.encode("utf-16-be")
                        elif name.platformID == 1:
                            name.string = post.encode("mac_roman", errors="ignore")
                        else:
                            name.string = post.encode("utf-8")
                    except Exception:
                        pass
        font.save(dst)
        font.close()
        return dst
    except Exception:
        shutil.copy2(src, dst)
        return dst

def font_space_report(path):
    try:
        coverage = read_cmap_coverage(path)
        return {hex(cp): (cp in coverage) for cp in sorted(SPACE_CODEPOINTS)}
    except Exception:
        return {}

def font_record_from_path(path, source):
    names = read_font_names(path)
    full = (names.get(4) or names.get(6) or names.get(1) or [Path(path).stem])[0]
    family = (names.get(16) or names.get(1) or [full])[0]
    label = full or family or Path(path).stem
    return FontRecord(label=label, path=Path(path), full_name=full, family=family, source=source, coverage=None)

def scan_fonts():
    result = []
    seen = set()
    def add(p, source):
        try:
            p = Path(p)
            if not p.is_file() or p.suffix.casefold() not in {".ttf", ".otf", ".ttc"}:
                return
            key = str(p.resolve()).casefold()
            if key in seen:
                return
            seen.add(key)
            result.append(font_record_from_path(p, source))
        except Exception:
            pass
    if IS_WINDOWS:
        try:
            import winreg
            items = [(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Fonts"), (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")]
            for hive, key_name, base in items:
                try:
                    with winreg.OpenKey(hive, key_name) as k:
                        i = 0
                        while True:
                            try:
                                display, value, typ = winreg.EnumValue(k, i)
                                i += 1
                            except OSError:
                                break
                            p = Path(str(value))
                            if not p.is_absolute():
                                p = base / p
                            add(p, "System")
                except OSError:
                    pass
        except Exception:
            pass
    else:
        roots = [Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path.home() / "Library" / "Fonts", Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".local" / "share" / "fonts", Path.home() / ".fonts"]
        for root in roots:
            if root.is_dir():
                for ext in ("*.ttf", "*.otf", "*.ttc"):
                    for p in root.rglob(ext):
                        add(p, "System")
    if FONT_DIR.is_dir():
        for ext in ("*.ttf", "*.otf", "*.ttc"):
            for p in FONT_DIR.glob(ext):
                add(p, "SubBurn")
    result.sort(key=lambda r: (r.label.casefold(), str(r.path).casefold()))
    return result

def ffmpeg_filter_available(ffmpeg, name):
    """Probe one FFmpeg filter without depending on the column layout of ``-filters``.

    FFmpeg's filter-table flag columns have changed across releases/builds.  A direct help
    query is the authoritative compatibility probe for release-critical filters such as
    subtitles/libass.  FFmpeg returns exit code 0 even for an unknown filter, so inspect the
    response text as well.
    """
    name = str(name or "").strip()
    if not name:
        return False
    try:
        _rc, out = run_capture([ffmpeg, "-hide_banner", "-h", f"filter={name}"], timeout=20)
    except Exception:
        return False
    text = str(out or "")
    if re.search(r"(?i)unknown\s+filter", text):
        return False
    return bool(re.search(rf"(?im)^\s*Filter\s+{re.escape(name)}\s*$", text))

def parse_filters(ffmpeg):
    rc, out = run_capture([ffmpeg, "-hide_banner", "-filters"], timeout=25)
    items = set()
    if rc == 0:
        for line in out.splitlines():
            # Do not assume exactly three capability-flag columns.  Accept any compact flag
            # token followed by the filter name and validate release-critical filters below.
            m = re.match(r"^\s*[A-Z\.]{3,8}\s+(\S+)", line)
            if m:
                items.add(m.group(1))
    for critical in ("subtitles", "ass", "drawtext", "overlay", "colorchannelmixer"):
        if critical not in items and ffmpeg_filter_available(ffmpeg, critical):
            items.add(critical)
    return items

def parse_encoders(ffmpeg):
    rc, out = run_capture([ffmpeg, "-hide_banner", "-encoders"], timeout=25)
    if rc != 0:
        return []
    encoders = []
    for line in out.splitlines():
        m = re.match(r"^\s*V\S{5}\s+(\S+)", line)
        if m:
            encoders.append(m.group(1))
    return sorted(set(encoders))

def parse_audio_encoders(ffmpeg):
    rc, out = run_capture([ffmpeg, "-hide_banner", "-encoders"], timeout=25)
    if rc != 0:
        return set()
    encoders=set()
    for line in out.splitlines():
        m=re.match(r"^\s*A\S{5}\s+(\S+)",line)
        if m: encoders.add(m.group(1))
    return encoders

def parse_decoders(ffmpeg):
    rc, out = run_capture([ffmpeg, "-hide_banner", "-decoders"], timeout=20)
    if rc != 0:
        return set()
    decoders = set()
    for line in out.splitlines():
        m = re.match(r"^\s*S\S{5}\s+(\S+)", line)
        if m:
            decoders.add(m.group(1))
    return decoders

def encoder_supported_pixel_formats(ffmpeg, encoder):
    try:
        rc, out = run_capture([ffmpeg, "-hide_banner", "-h", f"encoder={encoder}"], timeout=20)
        if rc != 0:
            return set()
        for line in out.splitlines():
            if "Supported pixel formats:" in line:
                return set(line.split(":", 1)[1].strip().split())
    except Exception:
        pass
    return set()



def _percentile(values, q, default=0.0):
    vals = sorted(float(x) for x in values if x is not None and math.isfinite(float(x)))
    if not vals:
        return float(default)
    q = max(0.0, min(1.0, float(q)))
    pos = q * (len(vals) - 1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi: return vals[lo]
    f = pos - lo
    return vals[lo] * (1.0 - f) + vals[hi] * f

















def inspect_toolset(ffmpeg):
    ffmpeg = Path(ffmpeg)
    ffprobe = ffmpeg.with_name("ffprobe.exe" if IS_WINDOWS else "ffprobe")
    if not ffprobe.is_file():
        p = shutil.which("ffprobe")
        if p:
            ffprobe = Path(p)
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise RuntimeError("ffmpeg or ffprobe missing")
    rc, out = run_capture([ffmpeg, "-version"], timeout=15)
    version = out.splitlines()[0] if rc == 0 and out else str(ffmpeg)
    filters = parse_filters(ffmpeg)
    encoders = parse_encoders(ffmpeg)
    audio_encoders = parse_audio_encoders(ffmpeg)
    decoders = parse_decoders(ffmpeg)
    score = 0
    if "ass" in filters:
        score += 12000
    if "subtitles" in filters:
        score += 5000
    if "drawtext" in filters:
        score += 1000
    if "overlay" in filters:
        score += 700
    if "colorchannelmixer" in filters:
        score += 200
    score += len(encoders)
    score += 30 * sum(1 for e in encoders if is_hardware_encoder(e))
    return Toolset(ffmpeg=ffmpeg, ffprobe=ffprobe, version=version, filters=filters, encoders=encoders, score=score, decoders=decoders, audio_encoders=audio_encoders)

def ffmpeg_signature(toolset):
    try:
        st = toolset.ffmpeg.stat()
        size, mtime = st.st_size, int(st.st_mtime)
    except Exception:
        size, mtime = 0, 0
    return f"{toolset.ffmpeg}|{size}|{mtime}"









def load_encoder_cache():
    try:
        return json.loads(ENCODER_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_encoder_cache(cache):
    try:
        ENCODER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = ENCODER_CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, ENCODER_CACHE_FILE)
    except Exception:
        pass

def encoder_cache_get(cache, sig, enc):
    return (cache.get(sig) or {}).get(enc)

def encoder_cache_put(cache, sig, enc, ok, speed_factor, args):
    bucket = cache.setdefault(sig, {})
    bucket[enc] = {"ok": bool(ok), "speed": float(speed_factor or 0), "args": list(args or []), "ts": time.time()}
    save_encoder_cache(cache)

def _ffmpeg_paths_from_location(value):
    """Expand one user/system location into plausible FFmpeg executable paths."""
    if not value:
        return []
    p = Path(str(value)).expanduser()
    exe = "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"
    out = [p]
    # Saved settings are historically executable paths, but accepting a directory avoids
    # a needless managed download when a user pastes/selects an FFmpeg folder instead.
    try:
        if p.is_dir():
            out.extend([p / exe, p / "bin" / exe])
    except Exception:
        pass
    return out


def _dedupe_existing_ffmpeg_paths(paths):
    unique=[];seen=set()
    for candidate in paths:
        try:
            candidate=Path(candidate).expanduser()
            if candidate.is_file():
                key=str(candidate.resolve()).casefold() if IS_WINDOWS else str(candidate.resolve())
                if key not in seen:
                    seen.add(key);unique.append(candidate)
        except Exception:
            pass
    return unique

def _system_ffmpeg_paths():
    """System/PATH candidates, excluding SubBurn's managed runtime and explicit user choice."""
    paths=[]
    exe_names=("ffmpeg.exe","ffmpeg") if IS_WINDOWS else ("ffmpeg",)
    for raw_dir in str(os.environ.get("PATH","") or "").split(os.pathsep):
        raw_dir=raw_dir.strip().strip('"')
        if not raw_dir: continue
        base=Path(raw_dir).expanduser()
        for exe_name in exe_names: paths.append(base/exe_name)
    first=shutil.which("ffmpeg")
    if first: paths.append(Path(first))
    if IS_WINDOWS:
        local_appdata=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/"AppData"/"Local")))
        program_files=Path(os.environ.get("ProgramFiles",r"C:\Program Files"))
        program_files_x86=Path(os.environ.get("ProgramFiles(x86)",r"C:\Program Files (x86)"))
        user_profile=Path(os.environ.get("USERPROFILE",str(Path.home())))
        paths.extend([
            Path(r"C:\Tools\bin\ffmpeg.exe"),Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
            program_files/"ffmpeg"/"bin"/"ffmpeg.exe",program_files_x86/"ffmpeg"/"bin"/"ffmpeg.exe",
            user_profile/"ffmpeg"/"bin"/"ffmpeg.exe",local_appdata/"Programs"/"ffmpeg"/"bin"/"ffmpeg.exe",
            Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"),
            user_profile/"scoop"/"apps"/"ffmpeg"/"current"/"bin"/"ffmpeg.exe",
            local_appdata/"Microsoft"/"WinGet"/"Links"/"ffmpeg.exe",
        ])
    managed=managed_ffmpeg_executable()
    managed_key=str(managed.resolve()).casefold() if managed.exists() and IS_WINDOWS else (str(managed.resolve()) if managed.exists() else "")
    return [p for p in _dedupe_existing_ffmpeg_paths(paths) if not managed_key or ((str(p.resolve()).casefold() if IS_WINDOWS else str(p.resolve())) != managed_key)]

def candidate_ffmpeg_groups(saved=""):
    """Ordered discovery policy: system/PATH, explicit user location, then managed runtime."""
    system=_system_ffmpeg_paths()
    seen={(str(p.resolve()).casefold() if IS_WINDOWS else str(p.resolve())) for p in system}
    user=[]
    for p in _dedupe_existing_ffmpeg_paths(_ffmpeg_paths_from_location(saved)):
        key=str(p.resolve()).casefold() if IS_WINDOWS else str(p.resolve())
        if key not in seen:
            seen.add(key);user.append(p)
    managed=[]
    for p in _dedupe_existing_ffmpeg_paths([managed_ffmpeg_executable()]):
        key=str(p.resolve()).casefold() if IS_WINDOWS else str(p.resolve())
        if key not in seen: managed.append(p)
    return [("system",system),("user",user),("managed",managed)]

def candidate_ffmpeg_paths(saved=""):
    out=[]
    for _source,paths in candidate_ffmpeg_groups(saved): out.extend(paths)
    return out

def managed_ffmpeg_executable(runtime_root=None):
    root = Path(runtime_root) if runtime_root is not None else (RUNTIME_DIR / "ffmpeg")
    return root / "bin" / ("ffmpeg.exe" if IS_WINDOWS else "ffmpeg")

def inspect_managed_ffmpeg(runtime_root=None):
    ffmpeg = managed_ffmpeg_executable(runtime_root)
    if not ffmpeg.is_file():
        return None
    try:
        caps = inspect_toolset(ffmpeg)
    except Exception:
        return None
    return caps if "subtitles" in caps.filters else None

def scan_local_toolsets(saved=""):
    found=[];rejected=[]
    # Product policy is priority based, not a global score race. A compatible PATH/system
    # install wins; only then do we try the user-selected location; the managed runtime is last.
    for source,candidates in candidate_ffmpeg_groups(saved):
        group=[]
        for candidate in candidates:
            try:
                caps=inspect_toolset(candidate);found.append(caps);group.append(caps)
                if "subtitles" not in caps.filters:
                    rejected.append((str(candidate),"subtitle rendering filter is missing"))
            except Exception as exc:
                rejected.append((str(candidate),str(exc)))
        usable=[x for x in group if "subtitles" in x.filters]
        if usable:
            usable.sort(key=lambda x:x.score,reverse=True)
            return usable[0],found,rejected
    return None,found,rejected

def best_local_toolset(saved=""):
    best, found, _rejected = scan_local_toolsets(saved)
    return best, found

@contextmanager
def _dependency_install_lock(name, *, timeout=3600.0, poll=0.10, lock_dir=None):
    """Serialize fixed-path dependency installers across threads and processes.

    The small lock file is only a rendezvous point. The kernel lock is authoritative and
    is automatically released if a thread/process exits or crashes, so SubBurn never has
    to guess whether a persistent lock file is stale.
    """
    name=re.sub(r"[^0-9A-Za-z_.-]+","_",str(name or "dependency")).strip("._") or "dependency"
    root=Path(lock_dir or RUNTIME_DIR);root.mkdir(parents=True,exist_ok=True)
    lock_path=root/("."+name+".install.lock")
    handle=lock_path.open("a+b")
    acquired=False;started=time.monotonic();timeout=max(0.0,float(timeout));poll=max(0.01,float(poll))
    try:
        if handle.seek(0,os.SEEK_END)==0:
            handle.write(b"\0");handle.flush()
            try:os.fsync(handle.fileno())
            except Exception:pass
        while True:
            try:
                handle.seek(0)
                if IS_WINDOWS:
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                acquired=True;break
            except (BlockingIOError,OSError):
                if time.monotonic()-started>=timeout:
                    raise RuntimeError(f"Another SubBurn {name} setup is already running")
                time.sleep(min(poll,max(0.01,timeout-(time.monotonic()-started))))
        yield lock_path
    finally:
        if acquired:
            try:
                handle.seek(0)
                if IS_WINDOWS:
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
            except Exception:
                pass
        handle.close()

def _serialized_dependency_install(lock_name):
    def decorate(func):
        @functools.wraps(func)
        def wrapped(*args,**kwargs):
            lock_timeout=kwargs.pop("_install_lock_timeout",3600.0)
            with _dependency_install_lock(lock_name,timeout=lock_timeout):
                return func(*args,**kwargs)
        return wrapped
    return decorate





def _parse_publisher_sha256(text):
    """Parse a publisher SHA-256 sidecar without trusting filenames or formatting."""
    raw=str(text or "").strip()
    match=re.search(r"(?i)(?<![0-9a-f])([0-9a-f]{64})(?![0-9a-f])",raw)
    if not match:
        raise RuntimeError("Publisher checksum response does not contain a SHA-256 value")
    return match.group(1).lower()

def _fetch_publisher_sha256(url, *, timeout=30):
    try:
        with urllib.request.urlopen(str(url), timeout=timeout) as response:
            data=response.read(16*1024)
    except Exception as exc:
        raise RuntimeError(f"Could not retrieve publisher checksum: {exc}") from exc
    try:
        text=data.decode("utf-8-sig",errors="strict")
    except Exception as exc:
        raise RuntimeError("Publisher checksum response is not valid UTF-8 text") from exc
    return _parse_publisher_sha256(text)

def _ffmpeg_archive_cache_record(path=FFMPEG_ARCHIVE_CACHE_META):
    raw = _read_json_file(path, {})
    return raw if isinstance(raw, dict) else {}

def _verified_cached_ffmpeg_archive(destination, *, url, require_checksum=True):
    destination = Path(destination)
    if not destination.is_file():
        return None
    meta_path = FFMPEG_ARCHIVE_CACHE_META if destination == FFMPEG_ARCHIVE_CACHE else destination.with_suffix(destination.suffix + ".verified.json")
    meta = _ffmpeg_archive_cache_record(meta_path)
    if str(meta.get("source_url") or "") != str(url):
        return None
    expected = str(meta.get("archive_sha256") or "").strip().lower()
    publisher = str(meta.get("publisher_sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        return None
    if require_checksum and not re.fullmatch(r"[0-9a-f]{64}", publisher):
        return None
    try:
        actual = full_file_sha256(destination).lower()
    except Exception:
        return None
    if actual != expected or (publisher and actual != publisher):
        return None
    return {
        "path": str(destination), "sha256": actual, "publisher_sha256": publisher,
        "reused_cache": True, "bytes": int(destination.stat().st_size),
    }

def _download_verified_archive(url, destination, progress=None, *, checksum_url=None, require_checksum=True, phase=None, reuse_cache=True):
    """Download an archive once and authenticate it before extraction.

    The publisher checksum is fetched *before* the large transfer. This prevents a transient
    checksum failure after a completed 100+ MB download from throwing the bytes away. A verified
    archive is retained as a recovery cache, so extraction/validation/install retries do not
    redownload the same artifact.
    """
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if reuse_cache:
        cached = _verified_cached_ffmpeg_archive(destination, url=url, require_checksum=require_checksum)
        if cached is not None:
            if phase:
                phase("Using the previously downloaded verified FFmpeg archive; no network download is needed.")
            if progress:
                progress(cached["bytes"], cached["bytes"])
            return cached

    expected=""
    if checksum_url:
        if phase:
            phase("Checking the publisher SHA-256 before downloading FFmpeg.")
        expected=_fetch_publisher_sha256(checksum_url)
    elif require_checksum:
        raise RuntimeError("A publisher checksum URL is required for this runtime download")

    partial=destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    def hook(blocks,block_size,total):
        if progress:
            done=max(0,blocks*block_size)
            if total>0: done=min(total,done)
            progress(done,max(0,total))
    try:
        if phase:
            phase("Downloading one verified FFmpeg Essentials runtime for subtitle burning. This is a one-time download.")
        urllib.request.urlretrieve(str(url),partial,hook)
        actual=full_file_sha256(partial).lower()
        if expected and actual!=expected:
            raise RuntimeError(f"Download finished, but FFmpeg verification failed; nothing was installed (expected SHA-256 {expected}, got {actual}).")
        os.replace(partial,destination)
        meta_path = FFMPEG_ARCHIVE_CACHE_META if destination == FFMPEG_ARCHIVE_CACHE else destination.with_suffix(destination.suffix + ".verified.json")
        _atomic_write_json(meta_path,{
            "schema":1,"source_url":str(url),"checksum_url":str(checksum_url or ""),
            "archive_sha256":actual,"publisher_sha256":expected,"bytes":int(destination.stat().st_size),
            "verified_at":time.time(),
        })
        if progress:
            size=int(destination.stat().st_size); progress(size,size)
        if phase:
            phase("FFmpeg download verified; preparing the cached runtime for installation.")
        return {"path":str(destination),"sha256":actual,"publisher_sha256":expected,"reused_cache":False,"bytes":int(destination.stat().st_size)}
    except Exception:
        partial.unlink(missing_ok=True)
        raise

def _safe_extract_runtime_zip(archive, destination):
    """Extract a runtime ZIP only after rejecting traversal/absolute/symlink entries."""
    archive=Path(archive);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    root=destination.resolve()
    with zipfile.ZipFile(archive,"r") as z:
        for info in z.infolist():
            raw=str(info.filename or "").replace("\\","/")
            if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:",raw):
                raise RuntimeError(f"Unsafe path in downloaded FFmpeg archive: {info.filename!r}")
            parts=[x for x in raw.split("/") if x not in ("", ".")]
            if any(x==".." for x in parts):
                raise RuntimeError(f"Unsafe path in downloaded FFmpeg archive: {info.filename!r}")
            mode=(int(info.external_attr)>>16)&0xFFFF
            if (mode & 0o170000)==0o120000:
                raise RuntimeError(f"Symlink entry is not allowed in downloaded FFmpeg archive: {info.filename!r}")
            target=(destination.joinpath(*parts) if parts else destination).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise RuntimeError(f"Unsafe path in downloaded FFmpeg archive: {info.filename!r}") from exc
        z.extractall(destination)

def _recover_interrupted_runtime_swap(target, old, staged=None):
    """Recover the only unsafe filesystem state a crash can leave between rename operations."""
    target=Path(target);old=Path(old);staged=Path(staged) if staged is not None else None
    if old.exists() and not target.exists():
        os.replace(old,target)
    elif old.exists() and target.exists():
        shutil.rmtree(old,ignore_errors=True)
    if staged is not None and staged.exists():
        shutil.rmtree(staged,ignore_errors=True)

def _swap_runtime_directory(staged, target, old):
    """Atomically replace a validated runtime, restoring the old tree on swap failure."""
    staged=Path(staged);target=Path(target);old=Path(old)
    if old.exists():
        shutil.rmtree(old,ignore_errors=True)
    moved_old=False
    if target.exists():
        os.replace(target,old);moved_old=True
    try:
        os.replace(staged,target)
    except Exception:
        if moved_old and old.exists() and not target.exists():
            os.replace(old,target)
        raise
    if old.exists():
        shutil.rmtree(old,ignore_errors=True)


def managed_ffmpeg_manifest_path(runtime_root=None):
    root = Path(runtime_root) if runtime_root is not None else (RUNTIME_DIR / "ffmpeg")
    return root / FFMPEG_RUNTIME_MANIFEST_NAME

def read_managed_ffmpeg_manifest(runtime_root=None):
    raw = _read_json_file(managed_ffmpeg_manifest_path(runtime_root), {})
    return raw if isinstance(raw, dict) else {}

def _ffmpeg_buildconf(ffmpeg):
    try:
        rc, out = run_capture([ffmpeg, "-hide_banner", "-buildconf"], timeout=20)
        return out.strip() if rc == 0 else ""
    except Exception:
        return ""

def build_ffmpeg_runtime_manifest(download_info, caps, *, source_url, checksum_url):
    return {
        "schema": 1,
        "provider": FFMPEG_PROVIDER if str(source_url) == FFMPEG_URL else "custom",
        "source_url": str(source_url),
        "checksum_url": str(checksum_url or ""),
        "archive_sha256": str((download_info or {}).get("sha256") or ""),
        "publisher_sha256": str((download_info or {}).get("publisher_sha256") or ""),
        "ffmpeg_version": str(caps.version),
        "ffmpeg_buildconf": _ffmpeg_buildconf(caps.ffmpeg),
        "installed_at": time.time(),
        "license_review": "Inspect exact FFmpeg build configuration before redistribution",
    }

@_serialized_dependency_install("burn-ffmpeg")
def download_private_ffmpeg(progress=None, *, url=None, checksum_url=None, force=False, phase=None):
    """Install SubBurn's managed FFmpeg once, reusing a valid installed runtime thereafter.

    The install lock is acquired before this function runs.  Re-checking the managed runtime
    here is essential: a concurrent caller may have completed installation while this caller
    was waiting for the lock.
    """
    target=RUNTIME_DIR/"ffmpeg"
    _recover_interrupted_runtime_swap(target,target.with_name(target.name+".old"),target.with_name(target.name+".new"))
    if not force:
        existing = inspect_managed_ffmpeg(target)
        if existing is not None:
            return existing
    explicit_url=url is not None
    url=str(url or FFMPEG_URL)
    if checksum_url is None and not explicit_url:
        checksum_url=FFMPEG_SHA256_URL
    RUNTIME_DIR.mkdir(parents=True,exist_ok=True)
    # The installer owns its cache-directory precondition. Do not rely on a particular
    # downloader implementation (or a prior test/run) to create it as a side effect.
    FFMPEG_DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archive=FFMPEG_ARCHIVE_CACHE
    temp=RUNTIME_DIR/"extract"
    staged=target.with_name(target.name+".new")
    old=target.with_name(target.name+".old")
    _recover_interrupted_runtime_swap(target,old,staged)
    try:
        download_info = _download_verified_archive(url,archive,progress,checksum_url=checksum_url,require_checksum=not explicit_url,phase=phase)
        if phase:
            phase("Extracting the verified FFmpeg runtime.")
        if temp.exists():shutil.rmtree(temp,ignore_errors=True)
        temp.mkdir(parents=True)
        _safe_extract_runtime_zip(archive,temp)
        root=next((p for p in temp.iterdir() if p.is_dir() and (p/"bin").is_dir()),None)
        if root is None:root=temp if (temp/"bin").is_dir() else None
        if root is None:raise RuntimeError("Downloaded FFmpeg package has no bin directory")
        if staged.exists():shutil.rmtree(staged,ignore_errors=True)
        shutil.copytree(root,staged)
        ffmpeg=managed_ffmpeg_executable(staged)
        if phase:
            phase("Validating FFmpeg and subtitle-rendering support.")
        caps=inspect_toolset(ffmpeg)
        if "subtitles" not in caps.filters:
            raise RuntimeError("Downloaded FFmpeg does not support subtitle rendering")
        _atomic_write_json(
            staged / FFMPEG_RUNTIME_MANIFEST_NAME,
            build_ffmpeg_runtime_manifest(download_info, caps, source_url=url, checksum_url=checksum_url),
        )
        if phase:
            phase("Installing the verified FFmpeg runtime.")
        _swap_runtime_directory(staged,target,old)
        final_caps = inspect_toolset(managed_ffmpeg_executable(target))
        manifest = read_managed_ffmpeg_manifest(target)
        if str(manifest.get("archive_sha256") or "") != str(download_info.get("sha256") or ""):
            raise RuntimeError("Installed FFmpeg runtime provenance manifest did not survive the atomic swap")
        if phase:
            phase("FFmpeg runtime is installed and ready; future launches will reuse it.")
        return final_caps
    finally:
        # Keep the verified archive cache. If a later extraction/validation/install step fails,
        # the next attempt reuses the authenticated bytes instead of downloading them again.
        if temp.exists():shutil.rmtree(temp,ignore_errors=True)
        if staged.exists():shutil.rmtree(staged,ignore_errors=True)
        if old.exists() and target.exists():shutil.rmtree(old,ignore_errors=True)


def _broadcast_windows_environment_change():
    if not IS_WINDOWS:
        return
    try:
        HWND_BROADCAST=0xFFFF;WM_SETTINGCHANGE=0x001A;SMTO_ABORTIFHUNG=0x0002
        result=ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST,WM_SETTINGCHANGE,0,"Environment",SMTO_ABORTIFHUNG,3000,ctypes.byref(result))
    except Exception:
        pass

def promote_managed_ffmpeg_to_user_path(caps):
    """Make SubBurn's verified FFmpeg/FFprobe pair the user's preferred command pair on Windows.

    We intentionally do not overwrite package-manager shims or unrelated project binaries.
    Instead the verified runtime directory is placed first in the current process and in the
    user's persistent PATH. This is reversible and preserves package-manager ownership.
    """
    if not IS_WINDOWS or caps is None:
        return False
    ffmpeg=Path(caps.ffmpeg);ffprobe=Path(caps.ffprobe)
    if not ffmpeg.is_file() or not ffprobe.is_file() or ffmpeg.parent.resolve()!=ffprobe.parent.resolve():
        raise RuntimeError("Managed FFmpeg and FFprobe are not a valid executable pair")
    bindir=str(ffmpeg.parent.resolve())
    def key(v):
        try:return os.path.normcase(os.path.normpath(os.path.expandvars(str(v).strip().strip('"'))))
        except Exception:return str(v).casefold()
    # Current process: this immediately makes shutil.which/subprocess resolve the verified pair first.
    current=[x for x in str(os.environ.get("PATH","") or "").split(os.pathsep) if x.strip()]
    current=[x for x in current if key(x)!=key(bindir)]
    os.environ["PATH"]=os.pathsep.join([bindir]+current)
    try:
        import winreg
        reg_key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,"Environment",0,winreg.KEY_QUERY_VALUE|winreg.KEY_SET_VALUE)
        try:
            try: raw,typ=winreg.QueryValueEx(reg_key,"Path")
            except FileNotFoundError: raw,typ="",winreg.REG_EXPAND_SZ
            entries=[x for x in str(raw or "").split(";") if x.strip()]
            entries=[x for x in entries if key(x)!=key(bindir)]
            value=";".join([bindir]+entries)
            winreg.SetValueEx(reg_key,"Path",0,typ if typ in (winreg.REG_SZ,winreg.REG_EXPAND_SZ) else winreg.REG_EXPAND_SZ,value)
        finally:
            winreg.CloseKey(reg_key)
        _broadcast_windows_environment_change()
    except Exception as exc:
        raise RuntimeError(f"FFmpeg installed, but SubBurn could not update your Windows user PATH: {exc}") from exc
    return True

def _infer_video_bit_depth(pixel_format, bits_per_raw_sample=0):
    try:
        raw = int(bits_per_raw_sample or 0)
        if raw > 0:
            return raw
    except Exception:
        pass
    pf = str(pixel_format or "").casefold()
    m = re.search(r"(?:p|yuv|gbrp|gray)(?:420|422|444)?p?(10|12|14|16)(?:le|be)?$", pf)
    if m:
        return int(m.group(1))
    m = re.search(r"(10|12|14|16)(?:le|be)", pf)
    if m:
        return int(m.group(1))
    return 8 if pf else 0

def _infer_chroma_subsampling(pixel_format):
    pf = str(pixel_format or "").casefold()
    if "420" in pf or pf.startswith(("nv12", "p010", "p012")):
        return "4:2:0"
    if "422" in pf:
        return "4:2:2"
    if "444" in pf or pf.startswith("gbr") or pf.startswith("rgb") or pf.startswith("bgr"):
        return "4:4:4/RGB"
    if pf.startswith("gray"):
        return "monochrome"
    return ""

def _pixel_format_has_alpha(pixel_format):
    pf=str(pixel_format or "").casefold()
    return pf.startswith(("yuva","gbrap","rgba","bgra","argb","abgr","ya")) or "alpha" in pf

def _parse_rotation(stream):
    tags = stream.get("tags") or {}
    for value in (tags.get("rotate"), tags.get("ROTATE")):
        try:
            if value is not None:
                return int(round(float(value))) % 360
        except Exception:
            pass
    for side in stream.get("side_data_list") or []:
        try:
            if side.get("rotation") is not None:
                return int(round(float(side.get("rotation")))) % 360
        except Exception:
            pass
    return 0

def _parse_hdr_side_data(stream):
    mastering = ""
    max_cll = max_fall = 0
    dv_profile = dv_level = 0
    types = []
    for side in stream.get("side_data_list") or []:
        typ = str(side.get("side_data_type") or "")
        if typ and typ not in types:
            types.append(typ)
        if "Mastering display metadata" in typ:
            mastering = json.dumps(side, ensure_ascii=False, sort_keys=True)
        if "Content light level metadata" in typ:
            try: max_cll = int(side.get("max_content") or side.get("MaxCLL") or 0)
            except Exception: pass
            try: max_fall = int(side.get("max_average") or side.get("MaxFALL") or 0)
            except Exception: pass
        if "DOVI" in typ.upper() or "DOLBY VISION" in typ.upper():
            try: dv_profile = int(side.get("dv_profile") or side.get("profile") or 0)
            except Exception: pass
            try: dv_level = int(side.get("dv_level") or side.get("level") or 0)
            except Exception: pass
    return mastering, max_cll, max_fall, dv_profile, dv_level, types

def probe_media(ffprobe, video):
    rc, out = run_capture([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", video], timeout=45)
    if rc != 0:
        raise RuntimeError(out)
    data = json.loads(out)
    info = MediaInfo()
    fmt = data.get("format") or {}
    try: info.duration = float(fmt.get("duration") or 0)
    except Exception: pass
    try: info.total_bitrate = int(fmt.get("bit_rate") or 0)
    except Exception: pass
    try: info.file_size = int(fmt.get("size") or Path(video).stat().st_size)
    except Exception:
        try: info.file_size = int(Path(video).stat().st_size)
        except Exception: pass
    info.format_name = str(fmt.get("format_name") or "")
    for st in data.get("streams") or []:
        typ = st.get("codec_type")
        if typ == "video" and not info.width:
            info.video_stream_index = int(st.get("index") or 0)
            info.width = int(st.get("width") or 0)
            info.height = int(st.get("height") or 0)
            info.avg_fps = fraction_float(st.get("avg_frame_rate"))
            info.r_fps = fraction_float(st.get("r_frame_rate"))
            info.fps = info.avg_fps or info.r_fps
            info.video_codec = str(st.get("codec_name") or "")
            info.profile = str(st.get("profile") or "")
            try: info.level = int(st.get("level") or 0)
            except Exception: pass
            try: info.video_bitrate = int(st.get("bit_rate") or 0)
            except Exception: pass
            try: info.frame_count = int(st.get("nb_frames") or 0)
            except Exception: pass
            info.time_base = str(st.get("time_base") or "")
            try: info.start_time = float(st.get("start_time") or 0)
            except Exception: pass
            info.pixel_format = str(st.get("pix_fmt") or "")
            info.bit_depth = _infer_video_bit_depth(info.pixel_format, st.get("bits_per_raw_sample"))
            info.chroma_subsampling = _infer_chroma_subsampling(info.pixel_format)
            info.has_alpha = _pixel_format_has_alpha(info.pixel_format)
            info.sample_aspect_ratio = str(st.get("sample_aspect_ratio") or "")
            info.display_aspect_ratio = str(st.get("display_aspect_ratio") or "")
            info.rotation = _parse_rotation(st)
            if info.rotation in {90, 270}:
                info.display_width, info.display_height = info.height, info.width
            else:
                info.display_width, info.display_height = info.width, info.height
            info.field_order = str(st.get("field_order") or "")
            info.interlaced = info.field_order.casefold() not in {"", "progressive", "unknown"}
            if info.avg_fps > 0 and info.r_fps > 0:
                info.vfr_likely = abs(info.avg_fps - info.r_fps) / max(info.avg_fps, info.r_fps) > 0.01
            info.color_range = str(st.get("color_range") or "")
            info.color_space = str(st.get("color_space") or "")
            info.color_transfer = str(st.get("color_transfer") or "")
            info.color_primaries = str(st.get("color_primaries") or "")
            transfer = info.color_transfer.casefold()
            info.mastering_display, info.max_cll, info.max_fall, info.dolby_vision_profile, info.dolby_vision_level, info.hdr_side_data_types = _parse_hdr_side_data(st)
            has_dovi = bool(info.dolby_vision_profile or any("DOVI" in str(x).upper() or "DOLBY VISION" in str(x).upper() for x in info.hdr_side_data_types))
            info.hdr_mode = "Dolby Vision" if has_dovi else ("HDR10/PQ" if transfer in {"smpte2084", "smpte-st-2084"} else ("HLG" if transfer in {"arib-std-b67", "hlg"} else "SDR"))
        elif typ == "audio":
            try: br = int(st.get("bit_rate") or 0)
            except Exception: br = 0
            info.audio_bitrate += br
            info.audio_streams.append({"index": st.get("index"), "codec": st.get("codec_name") or "", "bitrate": br, "language": (st.get("tags") or {}).get("language", ""), "title": (st.get("tags") or {}).get("title", "")})
        elif typ == "subtitle":
            info.subtitle_streams.append({"index": st.get("index"), "codec": st.get("codec_name") or "", "language": (st.get("tags") or {}).get("language", ""), "title": (st.get("tags") or {}).get("title", "")})
    if not info.video_bitrate:
        if info.total_bitrate:
            info.video_bitrate = max(100000, info.total_bitrate - info.audio_bitrate)
        else:
            info.video_bitrate = 2000000
    return info

def probe_video_timing_variability(ffprobe, video, duration, window_seconds=6.0):
    """Cheap packet-timestamp sample for CFR/VFR evidence without decoding the whole source."""
    duration = max(0.0, float(duration or 0.0))
    w = max(2.0, float(window_seconds))
    starts = [0.0]
    if duration > w * 3:
        starts.extend([max(0.0, duration * 0.5 - w * 0.5), max(0.0, duration - w)])
    elif duration > w:
        starts.append(max(0.0, duration - w))
    starts = sorted({round(x, 3) for x in starts})
    deltas = []
    for start in starts:
        interval = ("%+" + f"{min(w,duration):.3f}") if start <= 0 else (f"{start:.3f}%+{min(w,max(0.1,duration-start)):.3f}")
        cmd=[ffprobe,"-v","error","-select_streams","v:0","-read_intervals",interval,
             "-show_entries","packet=pts_time","-of","csv=p=0",video]
        try:
            rc,out=run_capture(cmd,timeout=30)
        except Exception:
            continue
        if rc!=0:
            continue
        pts=[]
        for line in str(out).splitlines():
            raw=line.strip().strip(",")
            try: pts.append(float(raw))
            except Exception: pass
        pts=sorted(set(pts))
        for a,b in zip(pts,pts[1:]):
            d=b-a
            if d>1e-6 and d<5.0:
                deltas.append(d)
    if not deltas:
        return {"sample_count":0,"p10_ms":0.0,"p50_ms":0.0,"p90_ms":0.0,"vfr_likely":False}
    p10=_percentile(deltas,0.10);p50=_percentile(deltas,0.50);p90=_percentile(deltas,0.90)
    absolute_spread=max(0.0,p90-p10)
    spread=absolute_spread/max(p50,1e-9)
    # Packet timestamps are quantized to the stream/container time base.  At high CFR rates a
    # perfectly regular cadence can therefore alternate between adjacent ticks (for example
    # 8/9 ms at 120 fps), which looks like a large *relative* spread even though it is only
    # timestamp rounding. Require both meaningful relative variation and >1.5 ms absolute
    # spread before calling a source VFR. Genuine dropped/variable cadence clears this easily.
    quantization_floor=0.0015
    vfr=bool(len(deltas)>=8 and spread>0.05 and absolute_spread>quantization_floor)
    return {"sample_count":len(deltas),"p10_ms":p10*1000.0,"p50_ms":p50*1000.0,"p90_ms":p90*1000.0,
            "vfr_likely":vfr,"relative_spread":spread,"absolute_spread_ms":absolute_spread*1000.0}



def encoder_group(enc):
    e = str(enc).casefold()
    if "264" in e or e == "libopenh264":
        return "H.264"
    if "hevc" in e or "265" in e:
        return "HEVC"
    if "av1" in e:
        return "AV1"
    if "vp9" in e:
        return "VP9"
    return None

def source_codec_group(codec):
    c = str(codec).casefold()
    if c in {"h264", "avc1"}:
        return "H.264"
    if c in {"hevc", "h265"}:
        return "HEVC"
    if c == "av1":
        return "AV1"
    if c == "vp9":
        return "VP9"
    return "H.264"

def normalize_codec_mode(mode):
    raw = str(mode or "").strip()
    if raw in CODEC_MODES:
        return raw
    folded = raw.casefold()
    if folded in {"auto", "auto - any compatible codec", "automatic", "any compatible codec", "match", "match source codec"}:
        return "Match source"
    aliases = {"h264": "H.264", "h.264": "H.264", "h265": "HEVC", "h.265": "HEVC", "hevc": "HEVC", "av1": "AV1", "vp9": "VP9"}
    return aliases.get(folded, raw)

def compatible_groups(ext, mode, media=None):
    mode = normalize_codec_mode(mode)
    allowed = CONTAINER_CODECS.get(ext, {"H.264"})
    if mode == "Match source":
        g = source_codec_group(media.video_codec if media else "h264")
        if g in allowed:
            return [g]
        return ["H.264"] if "H.264" in allowed else [next(iter(allowed))]
    return [mode] if mode in allowed else []

def encoder_help(ffmpeg, enc, cache):
    if enc not in cache:
        rc, out = run_capture([ffmpeg, "-hide_banner", "-h", f"encoder={enc}"], timeout=20)
        cache[enc] = out if rc == 0 else ""
    return cache[enc]

def help_has_value(text, value):
    return bool(re.search(rf"(?mi)^\s+{re.escape(value)}\s+", text))

def tuning_args(ffmpeg, enc, speed, cache):
    idx = SPEED_MODES.index(speed) if speed in SPEED_MODES else 2
    e = enc.casefold()
    h = encoder_help(ffmpeg, enc, cache)
    if "_nvenc" in e:
        modern = ["p1", "p3", "p5", "p6", "p7"][idx]
        if help_has_value(h, modern):
            return ["-preset", modern]
        for v in [["fast", "hp", "default"], ["fast", "hp", "default"], ["medium", "default", "hq"], ["slow", "hq", "medium"], ["hq", "slow", "medium"]][idx]:
            if help_has_value(h, v):
                return ["-preset", v]
        return []
    if "_qsv" in e:
        for v in [["veryfast", "faster", "medium"], ["faster", "fast", "medium"], ["medium", "fast"], ["slow", "medium"], ["veryslow", "slow", "medium"]][idx]:
            if help_has_value(h, v):
                return ["-preset", v]
        return []
    if "_amf" in e:
        v = ["speed", "speed", "balanced", "quality", "quality"][idx]
        return ["-quality", v] if help_has_value(h, v) else []
    if enc in {"libx264", "libx265"}:
        return ["-preset", ["ultrafast", "veryfast", "medium", "slow", "veryslow"][idx]]
    if enc == "libsvtav1":
        return ["-preset", ["12", "10", "8", "6", "4"][idx]]
    if enc == "libaom-av1":
        return ["-cpu-used", ["8", "7", "5", "3", "1"][idx]]
    if enc == "librav1e":
        return ["-speed", ["10", "8", "6", "4", "2"][idx]]
    if enc == "libvpx-vp9":
        return ["-deadline", ["realtime", "good", "good", "good", "best"][idx], "-cpu-used", ["8", "7", "5", "3", "0"][idx]]
    return []

def pixfmt_args(enc):
    if enc.casefold().endswith("_mf"):
        return ["-pix_fmt", "nv12"]
    return ["-pix_fmt", "yuv420p"]

def position_expr(pos, margin, kind):
    if kind == "text":
        w, h, ow, oh = "w", "h", "text_w", "text_h"
    else:
        w, h, ow, oh = "main_w", "main_h", "overlay_w", "overlay_h"
    xs = {"left": str(margin), "center": f"({w}-{ow})/2", "right": f"{w}-{ow}-{margin}"}
    ys = {"top": str(margin), "middle": f"({h}-{oh})/2", "bottom": f"{h}-{oh}-{margin}"}
    table = {
        "Top left": (xs["left"], ys["top"]), "Top center": (xs["center"], ys["top"]), "Top right": (xs["right"], ys["top"]),
        "Middle left": (xs["left"], ys["middle"]), "Center": (xs["center"], ys["middle"]), "Middle right": (xs["right"], ys["middle"]),
        "Bottom left": (xs["left"], ys["bottom"]), "Bottom center": (xs["center"], ys["bottom"]), "Bottom right": (xs["right"], ys["bottom"])
    }
    return table[pos]

def grid_position_from_fraction(x, y):
    x = min(0.999999, max(0.0, float(x)))
    y = min(0.999999, max(0.0, float(y)))
    return POSITIONS[min(2, int(y * 3)) * 3 + min(2, int(x * 3))]

def interval_enable(rows, offset=0.0):
    if not rows:
        return None
    return "+".join(f"between(t\\,{max(0, a - offset):.3f}\\,{max(0, b - offset):.3f})" for a, b, p in rows)

def dynamic_axis(rows, margin, kind, axis, offset=0.0):
    if not rows:
        return None
    last = position_expr(rows[-1][2], margin, kind)[0 if axis == "x" else 1]
    expr = last
    for a, b, pos in reversed(rows[:-1]):
        val = position_expr(pos, margin, kind)[0 if axis == "x" else 1]
        expr = f"if(between(t\\,{max(0, a - offset):.3f}\\,{max(0, b - offset):.3f})\\,{val}\\,{expr})"
    return expr

def suspend_pid(pid):
    if IS_WINDOWS:
        access = 0x0800
        handle = ctypes.windll.kernel32.OpenProcess(access, False, pid)
        if not handle:
            raise OSError("OpenProcess failed")
        try:
            rc = ctypes.windll.ntdll.NtSuspendProcess(handle)
            if rc != 0:
                raise OSError(f"NtSuspendProcess returned {rc}")
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGSTOP)

def resume_pid(pid):
    if IS_WINDOWS:
        access = 0x0800
        handle = ctypes.windll.kernel32.OpenProcess(access, False, pid)
        if not handle:
            raise OSError("OpenProcess failed")
        try:
            rc = ctypes.windll.ntdll.NtResumeProcess(handle)
            if rc != 0:
                raise OSError(f"NtResumeProcess returned {rc}")
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGCONT)

DND_RUNTIME_ERROR = ""
DND_RUNTIME_MODULE = None

def load_tkinterdnd(allow_install=False, retry_seconds=86400):
    """Load optional drag/drop support without installing packages at application runtime."""
    global DND_RUNTIME_ERROR, DND_RUNTIME_MODULE
    if DND_RUNTIME_MODULE is not None:
        return DND_RUNTIME_MODULE
    runtime = RUNTIME_DIR / "pydeps"
    try:
        if runtime.is_dir() and str(runtime) not in sys.path:
            sys.path.insert(0, str(runtime))
        importlib.invalidate_caches()
        mod = importlib.import_module("tkinterdnd2")
        DND_RUNTIME_MODULE = mod
        DND_RUNTIME_ERROR = ""
        return mod
    except Exception as exc:
        DND_RUNTIME_ERROR = (
            "Optional drag & drop is unavailable. Install the declared tkinterdnd2 dependency "
            "or use an official packaged build. SubBurn will not run pip automatically. " + str(exc)
        )
        return None

class DropBinder:
    def __init__(self, root):
        self.available = False
        self.root = root
        self.DND_FILES = None
        mod = load_tkinterdnd(allow_install=False)
        if mod is not None:
            self.DND_FILES = mod.DND_FILES
            self.available = hasattr(root, "drop_target_register")
    def bind(self, widget, callback):
        if not self.available:
            return False
        widget.drop_target_register(self.DND_FILES)
        widget.dnd_bind("<<Drop>>", lambda e: callback(self.first_path(e.data)))
        return True
    def first_path(self, data):
        raw = str(data).strip()
        try:
            items = self.root.tk.splitlist(raw)
            if items:
                return str(items[0])
        except Exception:
            pass
        if raw.startswith("{") and "}" in raw:
            return raw[1:raw.index("}")]
        return raw.split()[0].strip("{}") if raw else ""
    def status_text(self):
        if self.available:
            return "Drag & drop: ready"
        detail = DND_RUNTIME_ERROR.strip()
        if detail:
            detail = detail.replace("\n", " ")[-240:]
            return "Drag & drop unavailable: " + detail
        return "Drag & drop unavailable"

def apply_native_windows_glass(root, mode="Dark"):
    """Best-effort Windows 11 Acrylic/Mica backdrop for the Tk top-level.

    Tk widgets remain opaque controls, but the native window material gives the desktop shell
    genuine OS-level depth in gutters/background regions. Failure is non-fatal on older Windows.
    """
    if not IS_WINDOWS:
        return False
    try:
        root.update_idletasks()
        hwnd = int(root.winfo_id())
        try:
            parent = int(ctypes.windll.user32.GetParent(hwnd) or 0)
            if parent:
                hwnd = parent
        except Exception:
            pass
        dark = ctypes.c_int(0 if normalize_appearance_mode(mode) == "Light" else 1)
        rounded = ctypes.c_int(2)  # DWMWCP_ROUND
        backdrop = ctypes.c_int(3)  # DWMSBT_TRANSIENTWINDOW / Acrylic on Windows 11
        dwm = ctypes.windll.dwmapi
        for attr, value in ((20, dark), (33, rounded), (38, backdrop)):
            try:
                dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), ctypes.c_uint(attr), ctypes.byref(value), ctypes.sizeof(value))
            except Exception:
                pass
        return True
    except Exception:
        return False

def create_root():
    mod = load_tkinterdnd(allow_install=False)
    if mod is not None:
        try:
            return mod.TkinterDnD.Tk()
        except Exception as e:
            global DND_RUNTIME_ERROR
            DND_RUNTIME_ERROR = f"TkDnD initialization failed: {e}"
    return tk.Tk()

OPERATION_SPECS = {
    # Reporting policy: no fabricated weighted percentages.  Operations stay indeterminate
    # until SubBurn has a real denominator (bytes, media duration, completed queue jobs, etc.).
    # 100% is reserved for terminal success.
    "tool_discovery": {"label": "FFmpeg setup", "priority": 30, "mode": "indeterminate", "ranges": {}},
    "runtime_download": {"label": "FFmpeg runtime download", "priority": 80, "mode": "indeterminate", "ranges": {}},
    "font_scan": {"label": "Font scan", "priority": 10, "mode": "indeterminate", "ranges": {}},
    "media_analysis": {"label": "Media analysis", "priority": 80, "mode": "indeterminate", "ranges": {}},
    "validation": {"label": "Subtitle/font validation", "priority": 80, "mode": "indeterminate", "ranges": {}},
    "encoder_probe": {"label": "Encoder test", "priority": 80, "mode": "indeterminate", "ranges": {}},
    "encoder_benchmark": {"label": "Encoder benchmark", "priority": 80, "mode": "indeterminate", "ranges": {}},
    # FFmpeg out_time / target duration is a real denominator for preview and final encoding.
    "preview": {"label": "Preview", "priority": 90, "mode": "indeterminate", "ranges": {}, "direct_range": (0.0, 99.0)},
    "live_frame": {"label": "Rendered frame", "priority": 90, "mode": "indeterminate", "ranges": {}},
    "live_clip": {"label": "Playback preview", "priority": 90, "mode": "indeterminate", "ranges": {}, "direct_range": (0.0, 99.0)},
    "quality_compare": {"label": "Quality comparison", "priority": 90, "mode": "determinate", "ranges": {}},
    "encode": {"label": "Burn video", "priority": 100, "mode": "indeterminate", "ranges": {}, "direct_range": (0.0, 99.0)},
    "transcription_model_prepare": {"label": "Prepare transcription model", "priority": 85, "mode": "indeterminate", "ranges": {}},
    "transcription": {"label": "Transcription", "priority": 90, "mode": "indeterminate", "ranges": {}, "direct_range": (0.0, 99.0)},
    "batch": {"label": "Batch queue", "priority": 95, "mode": "determinate", "ranges": {}},
    "ffmpeg_inspect": {"label": "Inspect FFmpeg", "priority": 70, "mode": "indeterminate", "ranges": {}},
    "generic": {"label": "Operation", "priority": 50, "mode": "indeterminate", "ranges": {}},
}

class OperationState:
    """Thread-safe canonical operation/progress state shared by desktop and browser UIs.

    Multiple background operations may exist, but exactly one foreground operation is presented.
    Progress is monotonic within an operation, never reaches 100 before success, and may be
    indeterminate when the work cannot be measured honestly.
    """
    TERMINAL_STATES = {"succeeded", "failed", "cancelled", "paused"}

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "Ready"
        self.log_lines = collections.deque(maxlen=300)
        self.history = collections.deque(maxlen=50)
        self.media_info = {}
        self.job_name = ""
        self.controls = {}
        self.operations = collections.OrderedDict()
        self.foreground_id = None
        self.last_terminal_id = None

    @staticmethod
    def _clamp_pct(value, maximum=100.0):
        try:
            value = float(value)
        except Exception:
            value = 0.0
        if not math.isfinite(value):
            value = 0.0
        return max(0.0, min(float(maximum), value))

    def begin(self, kind="generic", label=None, *, priority=None, mode=None):
        spec = OPERATION_SPECS.get(str(kind), OPERATION_SPECS["generic"])
        op_id = uuid.uuid4().hex
        now = time.monotonic()
        rec = {
            "id": op_id,
            "kind": str(kind),
            "label": str(label or spec.get("label") or kind),
            "priority": int(spec.get("priority", 50) if priority is None else priority),
            "state": "running",
            "mode": str(mode or spec.get("mode") or "indeterminate"),
            "phase": "Starting",
            "phase_message": "Starting",
            "phase_pct": 0.0,
            "overall_pct": 0.0,
            "started": now,
            "updated": now,
            "finished": None,
            "phase_started": now,
            "fps": "-",
            "speed": "-",
            "eta": "-",
            "bytes_done": 0,
            "bytes_total": 0,
            "transfer_pct": 0.0,
            "transfer_started": None,
            "transfer_updated": None,
            "transfer_finished": None,
            "rate_bps": 0.0,
            "error": "",
            "result": "",
        }
        with self.lock:
            self.operations[op_id] = rec
            while len(self.operations) > 64:
                old_id, old = next(iter(self.operations.items()))
                if old_id == self.foreground_id or old.get("state") not in self.TERMINAL_STATES:
                    break
                self.operations.pop(old_id, None)
            current = self.operations.get(self.foreground_id) if self.foreground_id else None
            if current is None or current.get("state") in self.TERMINAL_STATES or rec["priority"] >= int(current.get("priority", 0)):
                self.foreground_id = op_id
            self.status = rec["label"]
        return op_id

    def _record(self, op_id):
        return self.operations.get(str(op_id)) if op_id else None

    def _choose_foreground_locked(self):
        running = [r for r in self.operations.values() if r.get("state") not in self.TERMINAL_STATES]
        if running:
            running.sort(key=lambda r: (int(r.get("priority", 0)), float(r.get("updated", 0.0))), reverse=True)
            self.foreground_id = running[0]["id"]
        elif self.last_terminal_id in self.operations:
            self.foreground_id = self.last_terminal_id
        else:
            self.foreground_id = None

    def stage(self, op_id, name, pct, message):
        with self.lock:
            rec = self._record(op_id)
            if rec is None or rec.get("state") in self.TERMINAL_STATES:
                return False
            name = str(name)
            message = str(message)
            local_pct = self._clamp_pct(pct)
            if name != rec.get("phase"):
                self.history.appendleft({"operation_id": rec["id"], "name": rec.get("phase", ""), "message": rec.get("phase_message", ""), "ts": time.strftime("%H:%M:%S")})
                rec["phase_started"] = time.monotonic()
            rec["phase"] = name
            rec["phase_message"] = message
            rec["phase_pct"] = local_pct
            spec = OPERATION_SPECS.get(rec.get("kind"), OPERATION_SPECS["generic"])
            rng = (spec.get("ranges") or {}).get(name)
            if rng:
                lo, hi = map(float, rng)
                mapped = lo + (hi - lo) * local_pct / 100.0
                rec["overall_pct"] = max(float(rec.get("overall_pct", 0.0)), min(99.0, mapped))
                rec["mode"] = "determinate"
            elif str(spec.get("mode") or "indeterminate") == "indeterminate":
                # A named stage is not automatically a measurable percentage.  If this
                # operation has no stage range, show an indeterminate bar until a byte/media/
                # job-count callback supplies a real denominator.
                rec["mode"] = "indeterminate"
            rec["updated"] = time.monotonic()
            return True

    def progress(self, op_id, pct=None, fps="-", speed="-", eta="-", *, explicit=False):
        with self.lock:
            rec = self._record(op_id)
            if rec is None or rec.get("state") in self.TERMINAL_STATES:
                return False
            rec["fps"] = str(fps)
            rec["speed"] = str(speed)
            rec["eta"] = str(eta)
            spec = OPERATION_SPECS.get(rec.get("kind"), OPERATION_SPECS["generic"])
            direct = spec.get("direct_range")
            if pct is not None and (explicit or direct):
                raw = self._clamp_pct(pct)
                if direct and not explicit:
                    lo, hi = map(float, direct)
                    mapped = lo + (hi - lo) * raw / 100.0
                else:
                    mapped = raw
                rec["overall_pct"] = max(float(rec.get("overall_pct", 0.0)), min(99.0, mapped))
                rec["mode"] = "determinate"
            rec["updated"] = time.monotonic()
            return True

    def transfer(self, op_id, pct, done, total, rate_bps=0.0, eta_seconds=None, message=None):
        with self.lock:
            rec = self._record(op_id)
            if rec is None or rec.get("state") in self.TERMINAL_STATES:
                return False
            now = time.monotonic()
            spec = OPERATION_SPECS.get(rec.get("kind"), OPERATION_SPECS["generic"])
            direct = spec.get("direct_range")
            raw = self._clamp_pct(pct) if pct is not None else None
            previous_done = int(rec.get("bytes_done", 0) or 0)
            previous_total = int(rec.get("bytes_total", 0) or 0)
            next_done = max(0, int(done or 0))
            next_total = max(0, int(total or 0))
            # A lower byte count or changed total means a new transfer attempt. Metrics restart,
            # while canonical overall progress remains monotonic for the operation as a whole.
            if rec.get("transfer_started") is None or next_done < previous_done or (previous_total and next_total and next_total != previous_total):
                rec["transfer_started"] = now
            if raw is not None:
                rec["transfer_pct"] = raw
                rec["phase_pct"] = raw
                phase_name = str(rec.get("phase") or "")
                rng = (spec.get("ranges") or {}).get(phase_name)
                # Once an operation enters a real download phase, byte progress is the truthful
                # progress signal. Keep the canonical operation monotonic/capped at 99, but do
                # not remap transfer bytes through setup weights such as the FFmpeg 5%-90%
                # range; doing so is what made a zero-byte download appear to start at 5%.
                if phase_name.casefold().endswith("download"):
                    mapped = raw
                elif rng:
                    lo, hi = map(float, rng)
                    mapped = lo + (hi - lo) * raw / 100.0
                elif direct:
                    lo, hi = map(float, direct)
                    mapped = lo + (hi - lo) * raw / 100.0
                else:
                    mapped = raw
                rec["overall_pct"] = max(float(rec.get("overall_pct", 0.0)), min(99.0, mapped))
                rec["mode"] = "determinate"
            rec["bytes_done"] = next_done
            rec["bytes_total"] = next_total
            rec["transfer_updated"] = now
            if next_total > 0 and next_done >= next_total:
                rec["transfer_finished"] = rec.get("transfer_finished") or now
            elif next_total <= 0 or next_done < next_total:
                rec["transfer_finished"] = None
            rec["rate_bps"] = max(0.0, float(rate_bps or 0.0))
            rec["speed"] = (human_bytes(rec["rate_bps"]) + "/s") if rec["rate_bps"] > 0 else "-"
            rec["eta"] = fmt_time(float(eta_seconds)) if eta_seconds is not None and math.isfinite(float(eta_seconds)) else "-"
            if message:
                rec["phase_message"] = str(message)
            rec["updated"] = now
            return True

    def set_overall(self, op_id, pct, message=None):
        with self.lock:
            rec = self._record(op_id)
            if rec is None or rec.get("state") in self.TERMINAL_STATES:
                return False
            value = min(99.0, self._clamp_pct(pct))
            rec["overall_pct"] = max(float(rec.get("overall_pct", 0.0)), value)
            rec["mode"] = "determinate"
            if message is not None:
                rec["phase_message"] = str(message)
            rec["updated"] = time.monotonic()
            return True

    def finish(self, op_id, state="succeeded", *, error="", result=""):
        state = str(state)
        if state not in self.TERMINAL_STATES:
            raise ValueError(f"Invalid terminal operation state: {state}")
        with self.lock:
            rec = self._record(op_id)
            if rec is None:
                return False
            if rec.get("state") in self.TERMINAL_STATES:
                return rec.get("state") == state
            rec["state"] = state
            finished = time.monotonic()
            rec["updated"] = finished
            rec["finished"] = finished
            rec["error"] = str(error or "")
            rec["result"] = str(result or "")
            if state == "succeeded":
                rec["overall_pct"] = 100.0
                rec["phase_pct"] = 100.0
                rec["mode"] = "determinate"
                if rec.get("phase") in {"Starting", "Idle"}:
                    rec["phase"] = "Complete"
                if not rec.get("phase_message") or rec.get("phase_message") == "Starting":
                    rec["phase_message"] = "Complete"
            elif state == "paused":
                rec["phase_message"] = "Paused"
            elif state == "cancelled":
                rec["phase_message"] = rec.get("phase_message") or "Cancelled"
            else:
                rec["phase_message"] = str(error or rec.get("phase_message") or "Failed")
            self.last_terminal_id = rec["id"]
            if self.foreground_id == rec["id"]:
                self._choose_foreground_locked()
            current = self._record(self.foreground_id) if self.foreground_id else None
            self.status = self._operation_status_label(current if current is not None else rec)
            return True

    def state_of(self, op_id):
        with self.lock:
            rec = self._record(op_id)
            return str(rec.get("state")) if rec else None

    def is_foreground(self, op_id):
        with self.lock:
            return bool(op_id) and str(op_id) == str(self.foreground_id)

    def operation_snapshot(self, op_id):
        with self.lock:
            rec = self._record(op_id)
            if rec is None:
                return None
            now = time.monotonic()
            terminal = rec.get("state") in self.TERMINAL_STATES
            elapsed_now = float(rec.get("finished") or now) if terminal else now
            transfer_clock = float(rec.get("transfer_finished") or (rec.get("finished") if terminal else 0.0) or now)
            transfer_profile = str(rec.get("phase") or "").casefold().endswith("download")
            bytes_done = int(rec.get("bytes_done", 0) or 0)
            bytes_total = int(rec.get("bytes_total", 0) or 0)
            transfer_pct = round(float(rec.get("transfer_pct", 0.0) or 0.0), 1)
            overall_pct = round(float(rec.get("overall_pct", 0.0)), 1)
            transfer_idle = max(0.0, now - float(rec.get("transfer_updated") or now)) if rec.get("transfer_updated") else 0.0
            transfer_waiting = bool(transfer_profile and rec.get("state") == "running" and bytes_total > 0 and bytes_done < bytes_total and transfer_idle >= 3.0)
            display_speed = "0.0 B/s" if transfer_waiting else rec.get("speed", "-")
            display_eta = "-" if transfer_waiting else rec.get("eta", "-")
            # The visible download bar is byte-truthful. It can show exact 100% in the metric,
            # while the canonical operation bar remains at 99% until verification/install wins.
            progress_pct = 100.0 if rec.get("state") == "succeeded" else (min(99.0, transfer_pct) if transfer_profile else overall_pct)
            return {
                "id": rec["id"], "kind": rec.get("kind"), "label": rec.get("label"),
                "state": rec.get("state"), "mode": rec.get("mode", "indeterminate"),
                "phase": rec.get("phase", ""), "message": rec.get("phase_message", ""),
                "phase_pct": round(float(rec.get("phase_pct", 0.0)), 1),
                "overall_pct": overall_pct, "progress_pct": progress_pct,
                "elapsed": round(max(0.0, elapsed_now - float(rec.get("started", elapsed_now))), 1),
                "fps": rec.get("fps", "-"), "speed": display_speed, "eta": display_eta,
                "bytes_done": bytes_done, "bytes_total": bytes_total,
                "transfer_pct": transfer_pct, "transfer_stalled": transfer_waiting,
                "transfer_elapsed": round(max(0.0, transfer_clock - float(rec.get("transfer_started") or transfer_clock)), 1) if rec.get("transfer_started") else 0.0,
                "metric_profile": ("transfer" if transfer_profile else ("media" if rec.get("fps", "-") != "-" else "basic")),
                "downloaded": ((human_bytes(bytes_done) + " / " + human_bytes(bytes_total)) if bytes_total > 0 else (human_bytes(bytes_done) + " / -" if transfer_profile else "-")),
                "error": rec.get("error", ""), "result": rec.get("result", ""),
            }

    @staticmethod
    def _operation_status_label(rec):
        state = str((rec or {}).get("state") or "idle")
        return {
            "running": "Running", "queued": "Queued", "paused": "Paused",
            "succeeded": "Complete", "failed": "Error", "cancelled": "Cancelled",
        }.get(state, state.replace("_", " ").title() or "Ready")

    def set_status(self, text):
        with self.lock:
            self.status = str(text)

    def add_log(self, text):
        with self.lock:
            self.log_lines.append({"ts": time.strftime("%H:%M:%S"), "text": str(text)})

    def set_media(self, info):
        with self.lock:
            self.media_info = info

    def set_job(self, name):
        with self.lock:
            self.job_name = name

    def set_controls(self, controls):
        with self.lock:
            self.controls = controls

    def control_snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.controls))

    def snapshot(self):
        with self.lock:
            rec = self._record(self.foreground_id)
            if rec is None:
                return {
                    "app": APP_NAME, "version": APP_VERSION, "job": self.job_name, "appearance": str((self.controls.get("appearance") or {}).get("mode") or "Dark"),
                    "operation_id": None, "operation_type": None, "operation_label": "Idle", "operation_state": "idle",
                    "progress_mode": "indeterminate", "overall_pct": 0.0,
                    "stage": "Idle", "stage_pct": 0.0, "stage_message": "Ready",
                    "display_stage": "Idle", "display_stage_message": "Ready",
                    "elapsed": 0.0, "status": self.status, "progress_pct": 0.0,
                    "fps": "-", "speed": "-", "eta": "-", "bytes_done": 0, "bytes_total": 0, "transfer_pct": 0.0, "transfer_stalled": False, "transfer_elapsed": 0.0, "metric_profile": "basic", "downloaded": "-",
                    "log": list(self.log_lines)[-80:], "history": list(self.history), "display_history": presentation_history(list(self.history)),
                    "media": self.media_info,
                }
            now = time.monotonic()
            terminal = rec.get("state") in self.TERMINAL_STATES
            elapsed_now = float(rec.get("finished") or now) if terminal else now
            transfer_clock = float(rec.get("transfer_finished") or (rec.get("finished") if terminal else 0.0) or now)
            display_stage, display_message = presentation_stage(rec.get("phase", "Idle"), rec.get("phase_message", ""))
            transfer_profile = str(rec.get("phase") or "").casefold().endswith("download")
            bytes_done = int(rec.get("bytes_done", 0) or 0)
            bytes_total = int(rec.get("bytes_total", 0) or 0)
            transfer_pct = round(float(rec.get("transfer_pct", 0.0) or 0.0), 1)
            overall_pct = round(float(rec.get("overall_pct", 0.0)), 1)
            transfer_idle = max(0.0, now - float(rec.get("transfer_updated") or now)) if rec.get("transfer_updated") else 0.0
            transfer_waiting = bool(transfer_profile and rec.get("state") == "running" and bytes_total > 0 and bytes_done < bytes_total and transfer_idle >= 3.0)
            display_speed = "0.0 B/s" if transfer_waiting else rec.get("speed", "-")
            display_eta = "-" if transfer_waiting else rec.get("eta", "-")
            progress_pct = 100.0 if rec.get("state") == "succeeded" else (min(99.0, transfer_pct) if transfer_profile else overall_pct)
            return {
                "app": APP_NAME, "version": APP_VERSION, "job": self.job_name, "appearance": str((self.controls.get("appearance") or {}).get("mode") or "Dark"),
                "operation_id": rec["id"], "operation_type": rec.get("kind"), "operation_label": rec.get("label"), "operation_state": rec.get("state"),
                "progress_mode": rec.get("mode", "indeterminate"), "overall_pct": overall_pct,
                "stage": rec.get("phase", "Idle"), "stage_pct": round(float(rec.get("phase_pct", 0.0)), 1), "stage_message": rec.get("phase_message", ""),
                "display_stage": display_stage, "display_stage_message": display_message,
                "elapsed": round(max(0.0, elapsed_now - float(rec.get("started", elapsed_now))), 1), "status": self._operation_status_label(rec),
                "progress_pct": progress_pct, "fps": rec.get("fps", "-"), "speed": display_speed, "eta": display_eta,
                "bytes_done": bytes_done, "bytes_total": bytes_total,
                "transfer_pct": transfer_pct, "transfer_stalled": transfer_waiting,
                "transfer_elapsed": round(max(0.0, transfer_clock - float(rec.get("transfer_started") or transfer_clock)), 1) if rec.get("transfer_started") else 0.0,
                "metric_profile": ("transfer" if transfer_profile else ("media" if rec.get("fps", "-") != "-" else "basic")),
                "downloaded": ((human_bytes(bytes_done) + " / " + human_bytes(bytes_total)) if bytes_total > 0 else (human_bytes(bytes_done) + " / -" if transfer_profile else "-")),
                "error": rec.get("error", ""), "result": rec.get("result", ""),
                "log": list(self.log_lines)[-80:], "history": list(self.history), "display_history": presentation_history(list(self.history)),
                "media": self.media_info,
            }

DASHBOARD_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self'; connect-src 'self'; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"

DASHBOARD_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>SubBurn</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>

:root{color-scheme:dark;--bg:#06111e;--bg2:#0a1a2c;--panel:rgba(20,39,59,.42);--panel-strong:rgba(17,34,52,.66);--panel2:rgba(32,54,76,.42);--border:rgba(186,218,255,.18);--border-strong:rgba(205,230,255,.34);--highlight:rgba(255,255,255,.20);--text:#f6f9ff;--muted:#a8b9ca;--accent:#6f96ff;--accent2:#8bb1ff;--danger:#dc6878;--shadow:rgba(0,5,13,.30);--menu-bg:#10263a;--control-stroke:rgba(0,0,0,.68);--sidebar:230px;}
:root[data-theme="balanced"]{color-scheme:dark;--bg:#1d2b39;--bg2:#314659;--panel:rgba(77,103,127,.38);--panel-strong:rgba(58,80,101,.58);--panel2:rgba(93,119,143,.34);--border:rgba(226,240,255,.24);--border-strong:rgba(240,248,255,.42);--highlight:rgba(255,255,255,.28);--text:#f8fbff;--muted:#c7d1dc;--accent:#7aa0ff;--accent2:#9ab8ff;--danger:#df7280;--shadow:rgba(10,20,30,.24);--menu-bg:#314b60;--control-stroke:rgba(0,0,0,.58)}
:root[data-theme="light"]{color-scheme:light;--bg:#dce7f1;--bg2:#f5f8fc;--panel:rgba(255,255,255,.46);--panel-strong:rgba(255,255,255,.69);--panel2:rgba(244,249,253,.52);--border:rgba(65,90,116,.16);--border-strong:rgba(65,90,116,.26);--highlight:rgba(255,255,255,.88);--text:#172536;--muted:#607287;--accent:#4e72d9;--accent2:#6788e8;--danger:#be5263;--shadow:rgba(35,55,75,.17);--menu-bg:#f2f7fb;--control-stroke:rgba(0,0,0,.28)}
*{box-sizing:border-box}html,body{min-height:100%}body{position:relative;isolation:isolate;background:linear-gradient(145deg,var(--bg) 0%,var(--bg2) 52%,var(--bg) 100%);background-attachment:fixed;color:var(--text);font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif;margin:0;line-height:1.4;overflow-x:hidden}body::before,body::after{content:"";position:fixed;z-index:-2;border-radius:50%;filter:blur(42px);pointer-events:none;opacity:.82}body::before{width:58vw;height:58vw;right:-18vw;top:-26vw;background:radial-gradient(circle at 35% 35%,rgba(112,155,255,.58),rgba(72,113,204,.23) 42%,transparent 72%)}body::after{width:46vw;height:46vw;left:-21vw;bottom:-22vw;background:radial-gradient(circle at 60% 40%,rgba(73,222,207,.34),rgba(57,116,180,.18) 44%,transparent 72%)}button,input,select,textarea{font:inherit}button,input:not([type=checkbox]):not([type=radio]),select,textarea,option,.picker-entry{-webkit-text-stroke:.5px var(--control-stroke);paint-order:stroke fill;text-shadow:0 0 .35px var(--control-stroke)}select option,select optgroup{background-color:var(--menu-bg)!important;color:var(--text)!important}select:disabled option{color:var(--muted)!important}button{transition:background .16s ease,border-color .16s ease,transform .16s ease,box-shadow .16s ease;color:inherit}
.app-shell{display:grid;grid-template-columns:var(--sidebar) minmax(0,1fr);min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;background:linear-gradient(165deg,var(--panel-strong),rgba(14,28,44,.28));border-right:1px solid var(--border);padding:22px 14px;display:flex;flex-direction:column;gap:18px;backdrop-filter:blur(32px) saturate(155%);-webkit-backdrop-filter:blur(32px) saturate(155%);box-shadow:inset -1px 0 var(--highlight),12px 0 45px var(--shadow)}.brand{padding:0 10px}.brand h1{font-size:22px;margin:0;letter-spacing:.1px}.brand .sub{margin:5px 0 0;color:var(--muted);font-size:12px}.nav{display:flex;flex-direction:column;gap:6px}.nav button{border:1px solid transparent;background:transparent;color:var(--muted);text-align:left;border-radius:13px;padding:10px 12px;cursor:pointer}.nav button:hover{background:linear-gradient(135deg,rgba(255,255,255,.10),rgba(109,150,255,.08));border-color:var(--border);color:var(--text);box-shadow:inset 0 1px rgba(255,255,255,.08)}.nav button.active{background:linear-gradient(135deg,rgba(126,164,255,.28),rgba(100,139,226,.12));border-color:rgba(153,190,255,.36);color:var(--text);font-weight:650;box-shadow:inset 0 1px var(--highlight),0 9px 25px rgba(28,71,140,.17)}.sidebar-footer{margin-top:auto;padding:0 10px;color:var(--muted);font-size:11px}
.main{min-width:0;padding:24px 30px 44px}.topbar{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:15px}.page-title{font-size:26px;font-weight:720;letter-spacing:-.3px}.page-help{color:var(--muted);font-size:13px;margin-top:3px}.page{display:none;max-width:1180px}.page.active{display:block}.card{position:relative;overflow:hidden;background:linear-gradient(145deg,var(--panel),rgba(255,255,255,.025));border:1px solid var(--border);border-radius:20px;padding:19px 21px;margin-bottom:15px;box-shadow:inset 0 1px var(--highlight),inset 1px 0 rgba(255,255,255,.06),0 18px 48px var(--shadow);backdrop-filter:blur(28px) saturate(155%);-webkit-backdrop-filter:blur(28px) saturate(155%)}.card::before{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(118deg,rgba(255,255,255,.10),transparent 17%,transparent 72%,rgba(122,164,255,.055));opacity:.72}.card>*{position:relative}.section-title{font-size:17px;font-weight:690}.section-sub,.muted{color:var(--muted);font-size:12px;margin-top:3px}.action-card{border-color:rgba(133,177,255,.34)}
.operation-card{position:sticky;top:10px;z-index:20;max-width:1180px;background:linear-gradient(145deg,var(--panel-strong),rgba(255,255,255,.04));backdrop-filter:blur(34px) saturate(165%);-webkit-backdrop-filter:blur(34px) saturate(165%);padding:14px 17px;border-color:rgba(144,184,255,.34);box-shadow:inset 0 1px var(--highlight),0 16px 45px var(--shadow)}.stage{font-size:16px;font-weight:690}.msg{color:var(--muted);font-size:12px;margin-top:2px}.barwrap{background:rgba(15,30,46,.42);border:1px solid var(--border);border-radius:999px;height:9px;margin-top:9px;overflow:hidden;box-shadow:inset 0 1px 5px rgba(0,0,0,.23),0 1px rgba(255,255,255,.05)}.bar{background:linear-gradient(90deg,var(--accent),var(--accent2));height:100%;width:0%;transition:width .25s ease;box-shadow:0 0 16px rgba(109,142,255,.38)}.bar.indeterminate{width:35%!important;animation:subburn-indeterminate 1.1s ease-in-out infinite}@keyframes subburn-indeterminate{0%{transform:translateX(-120%)}50%{transform:translateX(90%)}100%{transform:translateX(300%)}}.metrics{display:flex;gap:18px;margin-top:8px;font-size:11px;color:var(--muted);flex-wrap:wrap}.metrics b{color:var(--text)}.status-pill{display:inline-block;padding:3px 9px;border-radius:999px;background:rgba(109,150,255,.13);border:1px solid rgba(137,178,255,.24);font-size:10px;margin-left:8px;box-shadow:inset 0 1px rgba(255,255,255,.10)}
.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.section-actions{margin-top:14px}.actions button,.card button{background:linear-gradient(145deg,var(--panel2),rgba(255,255,255,.045));color:var(--text);border:1px solid var(--border-strong);border-radius:13px;padding:8px 12px;cursor:pointer;box-shadow:inset 0 1px rgba(255,255,255,.025)}.actions button:hover,.card button:hover{background:linear-gradient(145deg,rgba(111,145,178,.32),rgba(255,255,255,.08));transform:translateY(-1px)}.actions button.primary,.hero-action{background:linear-gradient(135deg,#5f80f2,#6d8eff);border-color:#7f9bff;box-shadow:0 7px 18px rgba(68,100,205,.22)}.actions button.primary:hover{background:linear-gradient(135deg,#6b8af5,#7a99ff)}.actions button.danger{background:rgba(83,35,48,.78);border-color:rgba(216,97,112,.52)}.actions button:disabled{opacity:.43;cursor:not-allowed;transform:none}.action-result{font-size:11px;color:var(--muted);margin-top:7px}
.form-grid{display:grid;grid-template-columns:190px minmax(180px,1fr);gap:10px 14px;margin-top:14px;align-items:center}.form-grid label{color:var(--text);opacity:.88;font-size:12px}.form-grid input,.form-grid select{width:100%;background:linear-gradient(145deg,var(--panel2),rgba(255,255,255,.045));color:var(--text);border:1px solid var(--border-strong);border-radius:12px;padding:8px 9px;outline:none;box-shadow:inset 0 1px var(--highlight),inset 0 -1px 5px rgba(0,0,0,.10)}.form-grid input:focus,.form-grid select:focus{border-color:rgba(109,142,255,.72);box-shadow:0 0 0 2px rgba(109,142,255,.10),inset 0 1px 4px rgba(0,0,0,.18)}.form-grid input[type=checkbox]{width:auto}.pathrow{display:flex;gap:11px}.pathrow input{flex:1}.pathrow button{white-space:nowrap}.wm-interval{display:grid;grid-template-columns:1fr 1fr 1fr auto auto;gap:8px;margin-top:8px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}.loglines{font-family:"Cascadia Mono",Consolas,monospace;font-size:11px;max-height:300px;overflow:auto;white-space:pre-wrap;color:var(--text);opacity:.86}.hist{font-size:11px;color:var(--muted)}.hist div{padding:4px 0;border-bottom:1px solid rgba(120,151,194,.12)}
.queue-table-wrap{overflow:auto;margin-top:14px}.queue-table{width:100%;border-collapse:collapse;font-size:12px}.queue-table th,.queue-table td{padding:8px 9px;border-bottom:1px solid rgba(120,151,194,.14);text-align:left;vertical-align:top}.queue-table th{color:var(--muted);font-weight:650}.queue-table td:nth-child(4){white-space:nowrap}.queue-actions{display:flex;gap:6px;min-width:150px}.queue-actions button{padding:5px 8px;font-size:11px}.inline-field{display:flex;gap:9px;align-items:center;min-width:0}.inline-field>input,.inline-field>select{flex:1;min-width:0}.button-link{display:inline-flex;align-items:center;padding:8px 12px;border:1px solid var(--border-strong);border-radius:13px;background:linear-gradient(145deg,var(--panel2),rgba(255,255,255,.045));color:var(--text);text-decoration:none}.button-link:hover{background:linear-gradient(145deg,rgba(111,145,178,.32),rgba(255,255,255,.08));transform:translateY(-1px)}.help-manual{font-size:13px;color:var(--text);max-height:520px;overflow:auto;padding:4px 2px 8px}.help-manual h3{margin:14px 0 4px;font-size:14px}.help-manual p{margin:0 0 8px;color:var(--muted)}
.advanced-box{margin-top:14px;border:1px solid var(--border);border-radius:15px;background:linear-gradient(145deg,var(--panel2),rgba(255,255,255,.028));padding:0 12px;box-shadow:inset 0 1px rgba(255,255,255,.07);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}.advanced-box summary{cursor:pointer;color:var(--text);font-weight:650;padding:11px 2px}.advanced-box[open]{padding-bottom:12px}.advanced-box .form-grid{margin-top:4px}
.picker-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.74);z-index:100;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(5px);-webkit-backdrop-filter:blur(5px)}.picker{background:linear-gradient(145deg,var(--panel-strong),var(--panel));border:1px solid var(--border-strong);border-radius:22px;width:min(900px,96vw);max-height:85vh;display:flex;flex-direction:column;padding:16px;box-shadow:0 24px 80px rgba(0,0,0,.42);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}.picker-list{overflow:auto;min-height:250px;max-height:60vh;border:1px solid var(--border);margin-top:10px;border-radius:10px}.picker-entry{display:block;width:100%;text-align:left;background:var(--panel2);color:var(--text);border:0;border-bottom:1px solid var(--border);padding:9px 10px;cursor:pointer}.picker-entry:hover{background:rgba(125,157,190,.24)}
.fallback-picker{min-width:0}.fallback-picker .inline{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px}.fallback-chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px;min-height:20px}.fallback-chip{display:inline-flex;align-items:center;gap:7px;padding:5px 9px;border-radius:999px;background:var(--panel2);border:1px solid var(--border);color:var(--text);font-size:12px}.fallback-chip button{padding:0 4px;min-height:0;border:0;background:transparent;color:var(--muted);box-shadow:none}.fallback-chip button:hover{color:var(--text);background:transparent}
@media(max-width:850px){.app-shell{display:block}.sidebar{position:relative;height:auto;border-right:0;border-bottom:1px solid var(--border);padding:12px}.brand{display:flex;align-items:center;justify-content:space-between}.nav{display:flex;flex-direction:row;overflow-x:auto;padding-bottom:2px}.nav button{white-space:nowrap}.sidebar-footer{display:none}.main{padding:16px}.form-grid{grid-template-columns:1fr}.grid2{grid-template-columns:1fr}.operation-card{top:0}.topbar{display:none}}
</style></head><body><div class="app-shell"><aside class="sidebar"><div class="brand"><h1 id="app">SubBurn</h1><div class="sub" id="jobline">Connecting…</div></div><nav class="nav" aria-label="SubBurn sections">
<button data-page="home" class="active" onclick="showPage('home')">Home</button><button data-page="subtitles" onclick="showPage('subtitles')">Subtitles</button><button data-page="watermark" onclick="showPage('watermark')">Watermark</button><button data-page="transcribe" onclick="showPage('transcribe')">Transcribe</button><button data-page="preview" onclick="showPage('preview')">Preview</button><button data-page="burn" onclick="showPage('burn')">Burn</button><button data-page="queue" onclick="showPage('queue')">Queue</button><button data-page="settings" onclick="showPage('settings')">Settings</button></nav><div class="sidebar-footer">Local dashboard · same SubBurn session</div></aside><main class="main"><div class="card operation-card">
<div class="stage" id="stagename">Idle<span class="status-pill" id="statuspill">Ready</span></div>
<div class="msg" id="stagemsg"></div>
<div class="barwrap"><div class="bar" id="stagebar"></div></div>
<div class="metrics">
<span id="metric-elapsed"><span id="elapsed-label">Elapsed</span> <b id="elapsed">-</b></span>
<span id="metric-progress"><span id="progress-label">Progress</span> <b id="pct">-</b></span>
<span id="metric-fps">FPS <b id="fps">-</b></span>
<span id="metric-speed"><span id="speed-label">Speed</span> <b id="speed">-</b></span>
<span id="metric-downloaded">Downloaded <b id="downloaded">-</b></span>
<span id="metric-eta"><span id="eta-label">ETA</span> <b id="eta">-</b></span>
</div>
</div><section class="page active" id="page-home" data-page-panel="home"><div class="topbar"><div><div class="page-title">Home</div><div class="page-help">Start with the video, subtitles, and destination.</div></div></div><div class="card">
<div class="section-title">Project</div><div class="section-sub">Choose the source video, subtitle source, and output destination.</div>
<div class="form-grid">
<label for="projFfmpeg">FFmpeg file / folder</label><div class="pathrow"><input id="projFfmpeg"/><button onclick="openPicker('projFfmpeg','ffmpeg')">Browse</button></div>
<label for="projVideo">Video path</label><div class="pathrow"><input id="projVideo"/><button onclick="openPicker('projVideo','video')">Browse</button></div>
<label for="projSubSource">Subtitle source</label><select id="projSubSource"></select>
<label for="projSubFile">External subtitle path</label><div class="pathrow"><input id="projSubFile"/><button onclick="openPicker('projSubFile','subtitle')">Browse</button></div>
<label for="projEmbedded">Embedded track</label><select id="projEmbedded"></select>
<label for="projOutputDir">Output folder</label><div class="pathrow"><input id="projOutputDir"/><button onclick="openPicker('projOutputDir','folder')">Browse</button></div>
<label for="projOutputName">Output filename</label><input id="projOutputName"/>
<label for="projClean">Clean output folder</label><div><input id="projClean" type="checkbox"/></div>
</div>
<details class="advanced-box"><summary>Optional output metadata</summary><div class="form-grid">
<label for="metaTitle">Title</label><input id="metaTitle"/>
<label for="metaArtist">Artist</label><input id="metaArtist"/>
<label for="metaAlbum">Album</label><input id="metaAlbum"/>
<label for="metaGenre">Genre</label><input id="metaGenre"/>
<label for="metaDate">Date</label><input id="metaDate"/>
<label for="metaDescription">Description</label><input id="metaDescription"/>
<label for="metaCopyright">Copyright</label><input id="metaCopyright"/>
</div></details>
<div class="actions" style="margin-top:14px">
<button class="primary" onclick="saveProject()">Save project settings</button>
<button onclick="loadProject()">Refresh</button>
<span class="action-result" id="projresult"></span>
</div>
</div><div class="card">
<div class="section-title">Recent work</div>
<div class="form-grid">
<label for="recentProjects">Recent projects</label><select id="recentProjects" size="5"></select>
<label for="recentFolders">Recent folders</label><select id="recentFolders" size="5"></select>
</div>
<div class="actions" style="margin-top:14px">
<button onclick="restoreRecentProject()">Restore selected project</button>
<button onclick="clearRecents('projects')">Clear projects</button>
<button onclick="useRecentFolder()">Use selected as output folder</button>
<button onclick="clearRecents('folders')">Clear folders</button>
<button onclick="loadRecents()">Refresh recents</button>
<span class="action-result" id="recentresult"></span>
</div>
</div></section><section class="page" id="page-subtitles" data-page-panel="subtitles"><div class="topbar"><div><div class="page-title">Subtitles</div><div class="page-help">Style and validate the captions that will be burned into the video.</div></div></div><div class="card">
<div class="section-title">Subtitle styling</div><div class="section-sub">Essential styling is visible first; advanced typography remains available below.</div>
<div class="form-grid">
<label for="subFont">Primary font</label><select id="subFont"></select>
<label for="subFallbackPicker">Fallback fonts</label><div class="fallback-picker"><div class="inline"><select id="subFallbackPicker"></select><button type="button" onclick="addFallbackFont()">Add fallback</button></div><div id="subFallbackSelected" class="fallback-chips" aria-live="polite"></div></div>
<label for="subFontSize">Font size</label><input id="subFontSize"/>
<label for="subOutline">Outline</label><input id="subOutline"/>
<label for="subMargin">Bottom margin</label><input id="subMargin"/>
<label for="subSafe">Safe area</label><input id="subSafe"/>
<label for="subWrap">Wrap chars</label><input id="subWrap"/>
<label for="subMaxLines">Max lines</label><input id="subMaxLines"/>
<label for="subOffset">Offset ms</label><input id="subOffset"/>
<label for="subTextRgb">Text RGB</label><input id="subTextRgb"/>
<label for="subOutlineRgb">Outline RGB</label><input id="subOutlineRgb"/>
</div>
<details class="advanced-box"><summary>Advanced subtitle styling</summary><div class="form-grid">
<label for="subBold">Synthetic bold</label><div><input id="subBold" type="checkbox"/></div>
<label for="subItalic">Italic</label><div><input id="subItalic" type="checkbox"/></div>
<label for="subUnderline">Underline</label><div><input id="subUnderline" type="checkbox"/></div>
<label for="subStrikeout">Strikeout</label><div><input id="subStrikeout" type="checkbox"/></div>
<label for="subTextOpacity">Text opacity %</label><input id="subTextOpacity"/>
<label for="subOutlineOpacity">Outline opacity %</label><input id="subOutlineOpacity"/>
<label for="subShadowDepth">Shadow px</label><input id="subShadowDepth"/>
<label for="subShadowRgb">Shadow RGB</label><input id="subShadowRgb"/>
<label for="subShadowOpacity">Shadow opacity %</label><input id="subShadowOpacity"/>
<label for="subLetterSpacing">Letter spacing</label><input id="subLetterSpacing"/>
<label for="subRotation">Rotation °</label><input id="subRotation"/>
<label for="subAlignment">Alignment</label><select id="subAlignment"></select>
<label for="subMarginLeft">Left margin</label><input id="subMarginLeft"/>
<label for="subMarginRight">Right margin</label><input id="subMarginRight"/>
<label for="subBackgroundBox">Opaque background box</label><div><input id="subBackgroundBox" type="checkbox"/></div>
<label for="subBackgroundRgb">Background RGB</label><input id="subBackgroundRgb"/>
<label for="subBackgroundOpacity">Background opacity %</label><input id="subBackgroundOpacity"/>
<label for="subBackgroundPadding">Box padding</label><input id="subBackgroundPadding"/>
<label for="subCaptionEffect">Animated caption effect</label><select id="subCaptionEffect"></select>
<label for="subCaptionActiveRgb">Caption highlight RGB</label><input id="subCaptionActiveRgb"/>
<label for="subCaptionEstimate">Estimate word timing without sidecar</label><div><input id="subCaptionEstimate" type="checkbox"/></div>
<label for="subSafeZone">Platform safe-zone guide</label><select id="subSafeZone"></select>
<label for="subImportFontPath">Import font file</label><div class="pathrow"><input id="subImportFontPath"/><button onclick="openPicker('subImportFontPath','font')">Browse</button></div>
</div></details>
<div class="actions" style="margin-top:14px">
<button class="primary" onclick="saveSubtitles()">Save subtitle settings</button>
<button onclick="importFont()">Import selected font</button>
<button onclick="sendAction('refresh_fonts');setTimeout(loadSubtitles,1500)">Refresh installed fonts</button>
<button onclick="loadSubtitles()">Refresh</button>
<span class="action-result" id="subresult"></span>
</div>
</div></section><section class="page" id="page-watermark" data-page-panel="watermark"><div class="topbar"><div><div class="page-title">Watermark</div><div class="page-help">Optional text or image watermarking.</div></div></div><div class="card">
<div class="section-title">Watermark</div>
<div class="muted">Browser edits are applied to the same job settings used by Tkinter.</div>
<div class="form-grid">
<label for="wmEnabled">Enabled</label><div><input id="wmEnabled" type="checkbox"/></div>
<label for="wmTiming">Timing</label><select id="wmTiming" onchange="syncWatermarkVisibility()"><option>Full duration</option><option>Intervals</option></select>
<label for="wmType">Type</label><select id="wmType" onchange="syncWatermarkVisibility()"><option>Text</option><option>Image</option></select>
<label class="wmTextOnly" for="wmText">Text</label><input class="wmTextOnly" id="wmText"/>
<label class="wmTextOnly" for="wmSameFont">Use subtitle font</label><div class="wmTextOnly"><input id="wmSameFont" type="checkbox" onchange="syncWatermarkFontControl()"/></div>
<label class="wmTextOnly" for="wmFont">Watermark font</label><select class="wmTextOnly" id="wmFont" onchange="watermarkFontChosen()"></select>
<label class="wmImageOnly" for="wmImage">Image path</label><div class="wmImageOnly pathrow"><input id="wmImage"/><button onclick="openPicker('wmImage','image')">Browse</button></div>
<label class="wmFullOnly" for="wmPosition">Position</label><select class="wmFullOnly" id="wmPosition"></select>
<label class="wmTextOnly" for="wmSize">Text size</label><input class="wmTextOnly" id="wmSize"/>
<label for="wmOpacity">Opacity %</label><input id="wmOpacity" inputmode="decimal"/>
<label for="wmMargin">Margin</label><input id="wmMargin"/>
<label class="wmTextOnly" for="wmOutline">Text outline</label><input class="wmTextOnly" id="wmOutline"/>
<label class="wmImageOnly" for="wmImageWidth">Scale % (100 = natural)</label><input class="wmImageOnly" id="wmImageWidth"/>
<label class="wmImageOnly" for="wmImageX">Custom X px</label><input class="wmImageOnly" id="wmImageX" placeholder="blank = preset position"/>
<label class="wmImageOnly" for="wmImageY">Custom Y px</label><input class="wmImageOnly" id="wmImageY" placeholder="blank = preset position"/>
</div>
<div id="wmIntervalsBox" style="margin-top:14px;display:none">
<b>Intervals</b><div id="wmIntervals"></div>
<button onclick="addWatermarkInterval()" style="margin-top:8px">Add interval</button>
</div>
<div class="actions" style="margin-top:14px">
<button class="primary" onclick="saveWatermark()">Save watermark settings</button>
<button onclick="loadWatermark()">Refresh</button>
<span class="action-result" id="wmresult"></span>
</div>
</div></section><section class="page" id="page-transcribe" data-page-panel="transcribe"><div class="topbar"><div><div class="page-title">Transcribe</div><div class="page-help">Create subtitles locally from the selected video.</div></div></div>
<div class="card">
  <div class="section-title">Transcribe locally</div>
  <div class="section-sub">Generate subtitles on this computer using SubBurn's local transcription engine. No paid API is required.</div>
  <div class="form-grid">
    <label for="trModel">Model</label><select id="trModel"></select>
    <label for="trLangMode">Language mode</label><select id="trLangMode" onchange="syncTranscriptionLanguageMode()"></select>
    <label for="trLangPicker">Choose language</label><select id="trLangPicker" onchange="applyTranscriptionLanguageChoice()"></select>
    <label for="trLangCode">Selected language codes</label><input id="trLangCode" placeholder="Canonical codes, e.g. ar, he, en, zh, yue">
    <label for="trDevice">Device</label><select id="trDevice"></select>
  </div>
  <div class="actions section-actions">
    <button onclick="prepareTranscription()">Prepare model</button>
    <button class="primary" onclick="startTranscription()">Transcribe video</button>
    <button class="danger" onclick="cancelTranscription()">Cancel</button>
    <span class="action-result" id="trresult">Loading transcription state…</span>
  </div>
  <div class="muted" id="trModelInfo"></div>
</div>
</section><section class="page" id="page-preview" data-page-panel="preview"><div class="topbar"><div><div class="page-title">Preview</div><div class="page-help">Render the real subtitle and watermark pipeline before burning.</div></div></div><div class="card">
<div class="section-title">Rendered preview</div>
<div class="muted">Render exact interactive frames or create an 8-second inline playback preview from the selected timestamp, using the same subtitle and watermark timeline.</div>
<div class="actions" style="margin-top:12px">
<input id="liveSeek" max="0" min="0" oninput="syncLiveSeekLabel()" step="0.1" style="flex:1;min-width:260px" type="range" value="0"/>
<b id="liveSeekLabel">00:00.000</b>
<button class="primary" onclick="renderLiveFrame()">Render frame</button>
<button onclick="renderLiveClip()">Play 8s inline</button>
<span class="action-result" id="liveresult"></span>
</div>
<div style="margin-top:12px;text-align:center"><img alt="Rendered preview frame" draggable="false" id="liveFrameImg" onpointerup="positionLiveFrame(event)" style="display:none;max-width:100%;max-height:520px;border:1px solid #2a2e38;border-radius:8px;cursor:crosshair" title="Click or drag-release to move the enabled watermark to the nearest 3x3 position"/></div>
<video controls="" id="liveClipVideo" playsinline="" style="display:none;margin-top:12px;width:100%;max-height:540px;background:#000;border-radius:8px"></video>
</div>
<div class="card action-card"><div class="section-title">Preview actions</div><div class="actions"><button class="primary" onclick="sendAction('preview')">Create preview</button><button onclick="sendAction('compare')">Compare quality</button><button onclick="sendAction('validate')">Validate subtitles & fonts</button><span class="action-result" id="previewActionResult"></span></div></div></section><section class="page" id="page-burn" data-page-panel="burn"><div class="topbar"><div><div class="page-title">Burn</div><div class="page-help">Choose output settings and create the final video.</div></div></div><div class="card">
<div class="section-title">Output & encoding</div><div class="section-sub">Simple choices first. Advanced encoder controls appear only when Advanced mode is selected.</div>
<div class="form-grid">
<label for="encMode">Interface mode</label><select id="encMode" onchange="syncEncodingVisibility()"></select>
<label for="encExt">Output container</label><select id="encExt"></select>
<label for="encCodec">Codec</label><select id="encCodec"></select>
<label for="encQuality">Quality mode</label><select id="encQuality" onchange="syncEncodingVisibility()"></select>
<label class="encAdvancedOnly" for="encPolicy">Encoder policy</label><select class="encAdvancedOnly" id="encPolicy"></select>
<label class="encAdvancedOnly" for="encSpeed">Speed preset</label><select class="encAdvancedOnly" id="encSpeed"></select>
<label for="encResolution">Resolution</label><select id="encResolution"></select>
<label for="encFps">Frame rate</label><select id="encFps"></select>
<label for="encAudio">Audio</label><select id="encAudio"></select>
<label class="encAdvancedOnly" for="encEncoder">Encoder</label><select class="encAdvancedOnly" id="encEncoder"></select>
<label class="encBitrateOnly" for="encBitrate">Custom bitrate kbps</label><input class="encBitrateOnly" id="encBitrate"/>
<label class="encTargetOnly" for="encTarget">Target size MB</label><input class="encTargetOnly" id="encTarget"/>
<label class="encAdvancedOnly" for="encChapter">Preserve chapters</label><div class="encAdvancedOnly"><input id="encChapter" type="checkbox"/></div>
</div>
<div class="actions" style="margin-top:14px">
<button class="primary" onclick="saveEncoding()">Save encoding settings</button>
<button onclick="loadEncoding()">Refresh</button>
<span class="action-result" id="encresult"></span>
</div>
</div>
<div class="card action-card"><div class="section-title">Burn</div><div class="actions"><button class="primary hero-action" onclick="sendAction('encode')">Burn video</button><button onclick="sendAction('pause')">Pause</button><button onclick="sendAction('resume')">Resume</button><button class="danger" onclick="sendAction('cancel')">Cancel</button><button onclick="sendAction('open_file')">Open result</button><button onclick="sendAction('open_folder')">Open folder</button></div><div class="action-result" id="burnActionResult"></div></div></section><section class="page" id="page-queue" data-page-panel="queue"><div class="topbar"><div><div class="page-title">Queue</div><div class="page-help">Process multiple saved SubBurn jobs.</div></div></div>
<div class="card">
  <div class="section-title">Queue</div>
  <div class="section-sub">Build a persistent queue without changing the project that is currently open.</div>
  <div class="form-grid section-actions">
    <label for="queueRecentProject">Recent project</label><div class="inline-field"><select id="queueRecentProject"></select><button onclick="queueAddRecent()">Add recent project</button></div>
    <label for="queueVideoPath">Another video</label><div class="inline-field"><input id="queueVideoPath" placeholder="Choose a video without changing the open project"><button onclick="openPicker('queueVideoPath','video')">Browse</button></div>
    <label for="queueSubtitlePath">External subtitle (optional)</label><div class="inline-field"><input id="queueSubtitlePath" placeholder="Leave blank to use Auto subtitle selection"><button onclick="openPicker('queueSubtitlePath','subtitle')">Browse</button><button onclick="queueAddCustom()">Add to queue</button></div>
  </div>
  <div class="actions section-actions">
    <button onclick="queueAddCurrent()">Add current project</button>
    <button onclick="queueRemoveSelected()">Remove selected</button>
    <button onclick="queueAction('clear_queued')">Clear queued</button>
    <button class="primary" onclick="queueAction('start')">Start / resume</button>
    <button onclick="queueAction('pause')">Pause after current</button>
    <button class="danger" onclick="queueAction('cancel_current')">Cancel current</button>
    <button onclick="queueAction('retry_all')">Retry failures</button>
    <button onclick="queueAction('clear_completed')">Clear completed</button>
    <button onclick="loadQueue()">Refresh</button>
  </div>
  <div class="action-result" id="queueresult"></div>
  <div class="queue-table-wrap"><table class="queue-table"><thead><tr><th></th><th>#</th><th>Video</th><th>State</th><th>Progress</th><th>Output / error</th><th>Actions</th></tr></thead><tbody id="queueRows"><tr><td colspan="7" class="muted">Loading queue…</td></tr></tbody></table></div>
</div>
</section><section class="page" id="page-settings" data-page-panel="settings"><div class="topbar"><div><div class="page-title">Settings</div><div class="page-help">Appearance, runtime, diagnostics, recovery, and advanced tools.</div></div></div>
<div class="card">
  <div class="section-title">Appearance</div>
  <div class="section-sub">Choose the liquid-glass contrast level. The desktop and browser stay synchronized.</div>
  <div class="form-grid section-actions"><label for="appearanceMode">Theme</label><select id="appearanceMode" onchange="saveAppearance()"><option>Dark</option><option>Balanced</option><option>Light</option></select></div>
  <div class="action-result" id="appearanceResult"></div>
</div>
<div class="card">
  <div class="section-title">Runtime & tools</div>
  <div class="section-sub">Order: PATH/system first → selected FFmpeg file/folder → verified SubBurn runtime. If the managed runtime is needed on Windows, SubBurn places its bin folder first in your user PATH so future sessions reuse the compatible FFmpeg/FFprobe pair.</div>
  <div class="actions section-actions">
    <button onclick="sendAction('discover_tools')">Auto-detect FFmpeg</button>
    <button onclick="sendAction('download_runtime')">Check / install FFmpeg</button>
    <button onclick="sendAction('refresh_fonts');setTimeout(loadSubtitles,1500)">Refresh installed fonts</button>
  </div>
  <details class="advanced-box"><summary>Advanced encoder diagnostics</summary><div class="actions section-actions">
    <button onclick="sendAction('probe')">Quick encoder test</button>
    <button onclick="sendAction('benchmark')">Full encoder benchmark</button>
  </div></details>
</div>
<div class="card">
  <div class="section-title">Owner & help</div>
  <div class="section-sub">Made by: Anas Al Hwaity</div>
  <div class="actions section-actions"><a class="button-link" href="https://t.me/ANAS12RM" target="_blank" rel="noopener noreferrer">Contact Owner: @ANAS12RM on Telegram</a></div>
  <details class="advanced-box"><summary>Help Manual</summary><div class="help-manual">
    <h3>Quick start</h3><p>Open a video, choose or create subtitles, style them, preview the result, then burn.</p>
    <h3>Home</h3><p>Choose video, subtitle source, output folder/name/container, optional metadata, and restore or clear recent projects/folders.</p>
    <h3>Subtitles</h3><p>Choose the primary font and fallback fonts, then configure size, emphasis, colors, opacity, outline, shadow, spacing, rotation, alignment, margins, background, wrapping, safe areas, and caption effects. Arabic and Hebrew use libass with HarfBuzz/FriBidi and deterministic fallback planning.</p>
    <h3>Watermark</h3><p>Use text or image watermarks. Text can reuse the subtitle font or use its own font. Control position, opacity, scale, outline, coordinates, full-duration timing, or intervals.</p>
    <h3>Transcribe</h3><p>Generate subtitles locally with the selected Faster-Whisper model, language mode, language codes, and device. Prepared models are cached and reused.</p>
    <h3>Preview</h3><p>Render an exact frame or an 8-second inline preview using the same subtitle and watermark timeline/filter logic as final output.</p>
    <h3>Burn</h3><p>Simple mode exposes common choices. Advanced mode adds codec, quality, encoder policy, speed preset, resolution, frame rate, audio, explicit encoder, bitrate/target size, and chapters. Explicit user settings stay authoritative.</p>
    <h3>Queue</h3><p>Add the current project, another video using current settings, or a recent saved project. Reorder, duplicate, retry, remove selected items, clear queued jobs, or clear completed jobs. Running items are cancelled before removal.</p>
    <h3>Settings</h3><p>Choose Dark, Balanced, or Light appearance. Runtime discovery checks system/PATH FFmpeg, then a selected FFmpeg, then the managed runtime. Diagnostics and recovery tools are available here.</p>
    <h3>Progress reporting</h3><p>SubBurn only shows determinate percentages when a real denominator exists. Download bytes/speed/ETA and encode FPS/speed/ETA are separate metrics. Elapsed time and final metrics freeze when an operation ends. 100% is reserved for verified completion.</p>
  </div></details>
</div>
<div class="card">
  <div class="section-title">Recovery & diagnostics</div>
  <div class="actions section-actions">
    <button onclick="sendAction('diagnostics')">Export diagnostics</button>
    <button onclick="sendAction('restore_recovery')">Restore last autosave</button>
    <button onclick="sendAction('browser_only')">Hide desktop window</button>
    <button onclick="sendAction('show_window')">Show desktop window</button>
    <button class="danger" onclick="if(confirm('Exit SubBurn after any active work finishes?'))sendAction('exit_app')">Exit SubBurn</button>
  </div>
  <div class="action-result" id="actionresult">Connected to the current local SubBurn session.</div>
</div>
<div class="grid2">
<div class="card"><b>Recent stages</b><div class="hist" id="hist"></div></div>
<div class="card"><b>Log</b><button onclick="copyDashboardLog()" style="float:right">Copy log</button><div class="loglines" id="log"></div></div>
</div></section></main></div><div class="picker-backdrop" id="pickerBackdrop">
<div class="picker">
<div class="actions"><button onclick="pickerParent()">Up</button><button onclick="pickerRoots()">Roots</button><b id="pickerPath"></b></div>
<div class="picker-list" id="pickerList"></div>
<div class="actions" style="margin-top:10px"><button id="pickerSelectFolder" onclick="selectPickerFolder()">Select this folder</button><span class="action-result" id="pickerInfo"></span><button onclick="closePicker()" style="margin-left:auto">Cancel</button></div>
</div>
</div><script>
let activePage='home';
let currentAppearance='Dark';
function applyAppearance(mode){
  const normalized=['Dark','Balanced','Light'].includes(mode)?mode:'Dark';
  currentAppearance=normalized;document.documentElement.dataset.theme=normalized.toLowerCase();
  const el=document.getElementById('appearanceMode');if(el&&el.value!==normalized)el.value=normalized;
}
async function loadAppearance(){
  try{const r=await fetch('/api/job',{cache:'no-store'});const d=await r.json();applyAppearance((d.appearance||{}).mode||'Dark');}
  catch(e){}
}
async function saveAppearance(){
  const out=document.getElementById('appearanceResult'),mode=document.getElementById('appearanceMode').value;applyAppearance(mode);
  try{const r=await fetch('/api/job/appearance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})});const d=await r.json();if(out)out.textContent=d.message||(r.ok?'Applied':'Could not apply');}
  catch(e){if(out)out.textContent='Could not apply appearance';}
}
function showPage(name){
  const panel=document.getElementById('page-'+name); if(!panel)return;
  document.querySelectorAll('[data-page-panel]').forEach(p=>p.classList.toggle('active',p===panel));
  document.querySelectorAll('.nav [data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===name));
  activePage=name; try{sessionStorage.setItem('subburnPage',name);}catch(e){}
  if(name==='queue')loadQueue(); if(name==='transcribe')loadTranscription();
}
let queueSelected=new Set();
async function loadQueue(){
  const out=document.getElementById('queueresult'), body=document.getElementById('queueRows'); if(!body)return;
  try{const r=await fetch('/api/queue',{cache:'no-store'});const d=await r.json();if(!r.ok)throw new Error(d.message||'Queue unavailable');
    const recent=document.getElementById('queueRecentProject'); const previous=recent?recent.value:'';
    if(recent){recent.innerHTML='<option value="">Choose a recent project</option>';(d.recents||[]).forEach((p,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=p.label||p.video||('Recent project '+(i+1));recent.appendChild(o);});if([...recent.options].some(o=>o.value===previous))recent.value=previous;}
    body.innerHTML=''; const rows=d.items||[]; const liveIds=new Set(rows.map(x=>String(x.id))); queueSelected=new Set([...queueSelected].filter(id=>liveIds.has(id)));
    if(!rows.length){body.innerHTML='<tr><td colspan="7" class="muted">Queue is empty</td></tr>';}
    rows.forEach((item,i)=>{const tr=document.createElement('tr');const id=String(item.id||'');const name=(item.job&&item.job.video)?item.job.video.split(/[\\/]/).pop():(item.video||'');
      tr.innerHTML='<td><input type="checkbox" class="queue-check"></td><td>'+(i+1)+'</td><td></td><td></td><td></td><td></td><td class="queue-actions"></td>';
      const check=tr.querySelector('.queue-check');check.checked=queueSelected.has(id);check.onchange=()=>{if(check.checked)queueSelected.add(id);else queueSelected.delete(id);};
      tr.children[2].textContent=name;tr.children[3].textContent=item.state||'';tr.children[4].textContent=(Number(item.progress)||0).toFixed(0)+'%';tr.children[5].textContent=item.error||item.output_path||'';
      const actions=tr.children[6];const dup=document.createElement('button');dup.textContent='Duplicate';dup.onclick=()=>queueItemAction('duplicate',id);actions.appendChild(dup);const del=document.createElement('button');del.textContent=item.state==='running'?'Cancel & remove':'Remove';del.className='danger';del.onclick=()=>queueItemAction('delete',id);actions.appendChild(del);body.appendChild(tr);});
    out.textContent=d.running?'Queue is running':(d.paused?'Queue pauses after current job':'');
  }catch(e){out.textContent=e.message||'Could not load queue';}
}
async function queueAddCurrent(){const out=document.getElementById('queueresult');out.textContent='Adding current project...';try{const r=await fetch('/api/queue/add_current',{method:'POST'});const d=await r.json();out.textContent=d.message||(r.ok?'Added':'Failed');if(r.ok)setTimeout(loadQueue,200);}catch(e){out.textContent='Could not add current project';}}
async function queueAddRecent(){const out=document.getElementById('queueresult'),sel=document.getElementById('queueRecentProject');if(!sel.value){out.textContent='Choose a recent project';return;}try{const r=await fetch('/api/queue/add_recent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:Number(sel.value)})});const d=await r.json();out.textContent=d.message||(r.ok?'Added':'Failed');if(r.ok)setTimeout(loadQueue,200);}catch(e){out.textContent='Could not add recent project';}}
async function queueAddCustom(){const out=document.getElementById('queueresult'),video=document.getElementById('queueVideoPath').value.trim(),subtitle=document.getElementById('queueSubtitlePath').value.trim();if(!video){out.textContent='Choose a video';return;}try{const r=await fetch('/api/queue/add_custom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video,subtitle})});const d=await r.json();out.textContent=d.message||(r.ok?'Added':'Failed');if(r.ok){document.getElementById('queueVideoPath').value='';document.getElementById('queueSubtitlePath').value='';setTimeout(loadQueue,200);}}catch(e){out.textContent='Could not add queue project';}}
async function queueItemAction(action,id){const out=document.getElementById('queueresult');try{const r=await fetch('/api/queue/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});const d=await r.json();out.textContent=d.message||(r.ok?'Done':'Failed');queueSelected.delete(id);setTimeout(loadQueue,200);}catch(e){out.textContent='Queue item action failed';}}
async function queueRemoveSelected(){const ids=[...queueSelected];const out=document.getElementById('queueresult');if(!ids.length){out.textContent='Select one or more queue items';return;}try{const r=await fetch('/api/queue/delete_many',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});const d=await r.json();out.textContent=d.message||(r.ok?'Removed':'Failed');if(r.ok)queueSelected.clear();setTimeout(loadQueue,200);}catch(e){out.textContent='Could not remove selected items';}}
async function queueAction(action){const out=document.getElementById('queueresult');out.textContent='Sending...';try{const r=await fetch('/api/queue/'+action,{method:'POST'});const d=await r.json();out.textContent=d.message||(r.ok?'Queued':'Failed');setTimeout(loadQueue,250);}catch(e){out.textContent='Queue action failed';}}
function syncTranscriptionLanguageMode(){
  const mode=document.getElementById('trLangMode').value, disabled=mode==='Auto multilingual (detect changes)';
  document.getElementById('trLangPicker').disabled=disabled; document.getElementById('trLangCode').disabled=disabled;
}
function applyTranscriptionLanguageChoice(){
  const picker=document.getElementById('trLangPicker'), code=picker.options[picker.selectedIndex]?.dataset.code||''; if(!code)return;
  const mode=document.getElementById('trLangMode').value, field=document.getElementById('trLangCode');
  if(mode==='Fixed language code'){field.value=code;}
  else if(mode==='Allowed languages (detect changes)'){const values=field.value.split(/[,;\\s]+/).filter(Boolean);if(!values.includes(code))values.push(code);field.value=values.join(', ');}
  picker.selectedIndex=0;
}
function setTranscriptionLanguageOptions(items){
  const el=document.getElementById('trLangPicker'); el.innerHTML='';
  (items||[]).forEach((item,i)=>{const o=document.createElement('option');o.textContent=item.label||item.code||'';o.dataset.code=item.code||'';if(i===0)o.selected=true;el.appendChild(o);});
}
async function loadTranscription(){
 const out=document.getElementById('trresult'); if(!out)return;
 try{const r=await fetch('/api/job',{cache:'no-store'});const d=await r.json(),t=d.transcription||{};setSimpleSelect('trModel',t.model_options,t.model);setSimpleSelect('trLangMode',t.language_mode_options,t.language_mode);setTranscriptionLanguageOptions(t.language_display_options||[]);document.getElementById('trLangCode').value=t.language_code||'';setSimpleSelect('trDevice',t.device_options,t.device);syncTranscriptionLanguageMode();document.getElementById('trModelInfo').textContent=t.model_info||'';out.textContent=t.result||t.status||'';}catch(e){out.textContent='Could not load transcription state';}
}
async function saveTranscription(){const payload={model:document.getElementById('trModel').value,language_mode:document.getElementById('trLangMode').value,language_code:document.getElementById('trLangCode').value,device:document.getElementById('trDevice').value};const r=await fetch('/api/job/transcription',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw new Error(d.message||'Could not apply transcription settings');return d;}
async function prepareTranscription(){const out=document.getElementById('trresult');out.textContent='Preparing…';try{await saveTranscription();const r=await fetch('/api/action/transcription_prepare',{method:'POST'});const d=await r.json();out.textContent=d.message||(r.ok?'Queued':'Failed');}catch(e){out.textContent=e.message||'Preparation failed';}}
async function startTranscription(){const out=document.getElementById('trresult');out.textContent='Starting…';try{await saveTranscription();const r=await fetch('/api/action/transcription_start',{method:'POST'});const d=await r.json();out.textContent=d.message||(r.ok?'Queued':'Failed');}catch(e){out.textContent=e.message||'Transcription failed';}}
async function cancelTranscription(){const out=document.getElementById('trresult');try{const r=await fetch('/api/action/transcription_cancel',{method:'POST'});const d=await r.json();out.textContent=d.message||(r.ok?'Cancel requested':'Failed');}catch(e){out.textContent='Cancel failed';}}

let pickerTarget=null, pickerKind=null, pickerData=null;
async function openPicker(target,kind){pickerTarget=target;pickerKind=kind;let p=document.getElementById(target).value.trim();await browsePicker(p);}
async function browsePicker(path=''){
  const info=document.getElementById('pickerInfo'); info.textContent='Loading...';
  try{
    const r=await fetch('/api/fs?kind='+encodeURIComponent(pickerKind)+'&path='+encodeURIComponent(path),{cache:'no-store'}); const d=await r.json();
    if(!r.ok){info.textContent=d.message||'Could not browse';return;}
    pickerData=d; document.getElementById('pickerBackdrop').style.display='flex'; document.getElementById('pickerPath').textContent=d.path||'Computer roots';
    const list=document.getElementById('pickerList'); list.innerHTML='';
    (d.entries||[]).forEach(e=>{const b=document.createElement('button');b.className='picker-entry';b.textContent=(e.is_dir?'📁 ':'📄 ')+e.name;b.onclick=()=>e.is_dir?browsePicker(e.path):selectPicker(e.path);list.appendChild(b);});
    document.getElementById('pickerSelectFolder').style.display=(pickerKind==='folder'||pickerKind==='ffmpeg')&&d.path?'':'none';
    info.textContent=d.truncated?'Showing first 2000 entries':'';
  }catch(err){info.textContent='Could not browse filesystem';}
}
function pickerParent(){if(pickerData&&pickerData.parent!==undefined)browsePicker(pickerData.parent);}
function pickerRoots(){browsePicker('');}
function selectPicker(path){document.getElementById(pickerTarget).value=path;closePicker();}
function selectPickerFolder(){if(pickerData&&pickerData.path)selectPicker(pickerData.path);}
function closePicker(){document.getElementById('pickerBackdrop').style.display='none';}
async function copyDashboardLog(){
  const text=document.getElementById('log').textContent;
  try{await navigator.clipboard.writeText(text);document.getElementById('actionresult').textContent='Log copied';}
  catch(e){document.getElementById('actionresult').textContent='Clipboard unavailable';}
}
function formatLiveTime(seconds){
  seconds=Math.max(0,Number(seconds)||0); const h=Math.floor(seconds/3600),m=Math.floor((seconds%3600)/60),s=seconds%60;
  return h?String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+s.toFixed(3).padStart(6,'0'):String(m).padStart(2,'0')+':'+s.toFixed(3).padStart(6,'0');
}
function syncLiveSeekLabel(){document.getElementById('liveSeekLabel').textContent=formatLiveTime(document.getElementById('liveSeek').value);}
async function renderLiveFrame(){
  const out=document.getElementById('liveresult'); const timestamp=Number(document.getElementById('liveSeek').value); out.textContent='Queuing...';
  try{
    const r=await fetch('/api/action/live_frame',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({timestamp})});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Queued':'Failed');
    if(r.ok){liveFrameStamp=0;setTimeout(()=>refreshLiveFrame(timestamp,Number(d.after_revision||0)),350);}
  }catch(err){out.textContent='Live frame request failed';}
}
let liveFrameStamp=0;
async function refreshLiveFrame(expected,afterRevision=0){
  const img=document.getElementById('liveFrameImg');
  try{
    const r=await fetch('/api/live/frame?at='+encodeURIComponent(expected)+'&after='+encodeURIComponent(afterRevision)+'&ts='+Date.now(),{cache:'no-store'});
    if(r.ok){const type=(r.headers.get('Content-Type')||'').toLowerCase();if(!type.startsWith('image/'))throw new Error('Preview endpoint returned '+(type||'unknown content'));const blob=await r.blob();if(!blob.size)throw new Error('Preview image is empty');const url=URL.createObjectURL(blob);const old=img.dataset.url;img.onload=()=>{if(old)URL.revokeObjectURL(old);img.dataset.loaded='1';document.getElementById('liveresult').textContent='Frame ready';};img.onerror=()=>{URL.revokeObjectURL(url);img.dataset.loaded='0';document.getElementById('liveresult').textContent='Frame could not be decoded';};img.dataset.url=url;img.src=url;img.style.display='inline-block';return;}
  }catch(e){}
  if(liveFrameStamp++<80)setTimeout(()=>refreshLiveFrame(expected,afterRevision),350); else {document.getElementById('liveresult').textContent='Frame not ready';liveFrameStamp=0;}
}
async function positionLiveFrame(event){
  const img=event.currentTarget, rect=img.getBoundingClientRect(); if(!rect.width||!rect.height)return;
  const x=Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)), y=Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height));
  const timestamp=Number(document.getElementById('liveSeek').value), out=document.getElementById('liveresult'); out.textContent='Moving watermark...';
  try{
    const r=await fetch('/api/live/position',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({x,y,timestamp})});
    const d=await r.json();out.textContent=d.message||(r.ok?'Position queued':'Position failed');
    if(r.ok){liveFrameStamp=0;setTimeout(loadWatermark,250);setTimeout(()=>refreshLiveFrame(timestamp,Number(d.after_revision||0)),350);}
  }catch(e){out.textContent='Position request failed';}
}
async function renderLiveClip(){
  const out=document.getElementById('liveresult'), timestamp=Number(document.getElementById('liveSeek').value); out.textContent='Rendering playback preview...';
  try{
    const r=await fetch('/api/action/live_clip',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({timestamp})});
    const d=await r.json();out.textContent=d.message||(r.ok?'Queued':'Failed');
    if(r.ok)setTimeout(()=>pollLiveClip(timestamp,Number(d.after_revision||0),0),500);
  }catch(e){out.textContent='Playback preview request failed';}
}
async function pollLiveClip(timestamp,afterRevision,attempt){
  const out=document.getElementById('liveresult');
  try{
    const r=await fetch('/api/live/clip/status?at='+encodeURIComponent(timestamp)+'&after='+encodeURIComponent(afterRevision),{cache:'no-store'});
    const d=await r.json();
    if(r.ok&&d.ready){
      const video=document.getElementById('liveClipVideo');video.src='/api/live/clip?at='+encodeURIComponent(timestamp)+'&rev='+encodeURIComponent(d.revision)+'&ts='+Date.now();video.style.display='block';video.load();video.play().catch(()=>{});out.textContent='Playback preview ready';return;
    }
  }catch(e){}
  if(attempt<150)setTimeout(()=>pollLiveClip(timestamp,afterRevision,attempt+1),500);else out.textContent='Playback preview not ready';
}
function currentActionResult(){
  const byPage={preview:'previewActionResult',burn:'burnActionResult',settings:'actionresult'};
  return document.getElementById(byPage[activePage]||'actionresult') || document.getElementById('actionresult');
}
async function sendAction(name){
  const out = currentActionResult();
  out.textContent = 'Sending ' + name + '...';
  try{
    const r = await fetch('/api/action/' + name, {method:'POST', cache:'no-store'});
    const d = await r.json();
    out.textContent = d.message || (r.ok ? 'Queued' : 'Request failed');
  }catch(e){
    out.textContent = 'Dashboard action failed';
  }
}
async function loadProject(){
  const out=document.getElementById('projresult');
  try{
    const r=await fetch('/api/job',{cache:'no-store'}); const d=await r.json(); const p=d.project || {};
    document.getElementById('projFfmpeg').value=p.ffmpeg || '';
    document.getElementById('projVideo').value=p.video || '';
    setSimpleSelect('projSubSource', p.subtitle_source_options, p.subtitle_source);
    document.getElementById('projSubFile').value=p.subtitle_file || '';
    setSimpleSelect('projEmbedded', p.embedded_options, p.embedded_track);
    document.getElementById('projOutputDir').value=p.output_dir || '';
    document.getElementById('projOutputName').value=p.output_name || '';
    document.getElementById('projClean').checked=!!p.clean_output;
    const md=p.metadata || {};
    document.getElementById('metaTitle').value=md.title || '';
    document.getElementById('metaArtist').value=md.artist || '';
    document.getElementById('metaAlbum').value=md.album || '';
    document.getElementById('metaGenre').value=md.genre || '';
    document.getElementById('metaDate').value=md.date || '';
    document.getElementById('metaDescription').value=md.description || '';
    document.getElementById('metaCopyright').value=md.copyright || '';
    out.textContent='Settings loaded';
  }catch(err){out.textContent='Could not load project settings';}
}
async function saveProject(){
  const payload={ffmpeg:document.getElementById('projFfmpeg').value,video:document.getElementById('projVideo').value,
    subtitle_source:document.getElementById('projSubSource').value,subtitle_file:document.getElementById('projSubFile').value,
    embedded_track:document.getElementById('projEmbedded').value,output_dir:document.getElementById('projOutputDir').value,
    output_name:document.getElementById('projOutputName').value,clean_output:document.getElementById('projClean').checked,
    metadata:{title:document.getElementById('metaTitle').value,artist:document.getElementById('metaArtist').value,
      album:document.getElementById('metaAlbum').value,genre:document.getElementById('metaGenre').value,
      date:document.getElementById('metaDate').value,description:document.getElementById('metaDescription').value,
      copyright:document.getElementById('metaCopyright').value}};
  const out=document.getElementById('projresult'); out.textContent='Saving...';
  try{
    const r=await fetch('/api/job/project',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Queued':'Save failed');
    if(r.ok) setTimeout(loadProject,250);
  }catch(err){out.textContent='Save failed';}
}
const WM_POSITIONS = ['Top left','Top center','Top right','Middle left','Center','Middle right','Bottom left','Bottom center','Bottom right'];
function setSelectOptions(el, values, selected){
  el.innerHTML = values.map(v => `<option${v===selected?' selected':''}>${v}</option>`).join('');
}
function syncWatermarkVisibility(){
  const type=document.getElementById('wmType').value;
  const timing=document.getElementById('wmTiming').value;
  document.querySelectorAll('.wmTextOnly').forEach(x => x.style.display = type==='Text' ? '' : 'none');
  document.querySelectorAll('.wmImageOnly').forEach(x => x.style.display = type==='Image' ? '' : 'none');
  document.querySelectorAll('.wmFullOnly').forEach(x => x.style.display = timing==='Full duration' ? '' : 'none');
  document.getElementById('wmIntervalsBox').style.display = timing==='Intervals' ? '' : 'none';
}
function addWatermarkInterval(row={start:'0',end:'10',position:'Top right'}){
  const box=document.getElementById('wmIntervals');
  const div=document.createElement('div'); div.className='wm-interval';
  const a=document.createElement('input'); a.value=row.start ?? '0'; a.placeholder='Start';
  const b=document.createElement('input'); b.value=row.end ?? '10'; b.placeholder='End';
  const p=document.createElement('select'); setSelectOptions(p, WM_POSITIONS, row.position || 'Top right');
  const preview=document.createElement('button'); preview.textContent='Preview boundary'; preview.onclick=()=>previewWatermarkInterval(div);
  const del=document.createElement('button'); del.textContent='Delete'; del.onclick=()=>div.remove();
  div.append(a,b,p,preview,del); box.appendChild(div);
}
async function loadRecents(){
  const out=document.getElementById('recentresult');
  try{
    const r=await fetch('/api/job',{cache:'no-store'}); const d=await r.json(); const rec=d.recents || {};
    const projects=document.getElementById('recentProjects'); projects.innerHTML='';
    (rec.projects || []).forEach((item,index)=>{const o=document.createElement('option');o.value=String(index);o.textContent=item.label || item.video || ('Project '+(index+1));projects.appendChild(o);});
    const folders=document.getElementById('recentFolders'); folders.innerHTML='';
    (rec.folders || []).forEach(path=>{const o=document.createElement('option');o.value=path;o.textContent=path;folders.appendChild(o);});
    out.textContent='';
  }catch(e){out.textContent='Could not load recents';}
}
async function clearRecents(kind){
  const out=document.getElementById('recentresult');
  try{const r=await fetch('/api/recent/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind})});const d=await r.json();out.textContent=d.message||'';if(r.ok)setTimeout(loadRecents,150);}
  catch(e){out.textContent='Could not clear recent '+kind;}
}
async function restoreRecentProject(){
  const select=document.getElementById('recentProjects'); const out=document.getElementById('recentresult');
  if(select.value===''){out.textContent='Choose a recent project';return;}
  try{
    const r=await fetch('/api/recent/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:Number(select.value)})});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Restore queued':'Restore failed');
    if(r.ok)setTimeout(()=>{loadProject();loadWatermark();loadEncoding();loadSubtitles();loadRecents();},600);
  }catch(e){out.textContent='Restore failed';}
}
function useRecentFolder(){
  const select=document.getElementById('recentFolders'); const out=document.getElementById('recentresult');
  if(!select.value){out.textContent='Choose a recent folder';return;}
  document.getElementById('projOutputDir').value=select.value; out.textContent='Output folder selected; save project settings to apply';
}
function syncWatermarkFontControl(){
  const same=document.getElementById('wmSameFont'); const font=document.getElementById('wmFont');
  if(font)font.disabled=!!(same&&same.checked);
}
function watermarkFontChosen(){
  const same=document.getElementById('wmSameFont'); if(same)same.checked=false; syncWatermarkFontControl();
}
async function loadWatermark(){
  const out=document.getElementById('wmresult');
  try{
    const r=await fetch('/api/job',{cache:'no-store'}); const d=await r.json(); const w=d.watermark || {};
    document.getElementById('wmEnabled').checked=!!w.enabled;
    document.getElementById('wmTiming').value=w.timing || 'Full duration';
    document.getElementById('wmType').value=w.type || 'Text';
    document.getElementById('wmText').value=w.text || '';
    document.getElementById('wmSameFont').checked=!!w.same_font;
    setSelectOptions(document.getElementById('wmFont'), w.font_options || [], w.font || '');
    document.getElementById('wmImage').value=w.image || '';
    setSelectOptions(document.getElementById('wmPosition'), WM_POSITIONS, w.position || 'Top right');
    document.getElementById('wmSize').value=w.size ?? '24';
    document.getElementById('wmOpacity').value=w.opacity ?? '85';
    document.getElementById('wmMargin').value=w.margin ?? '20';
    document.getElementById('wmOutline').value=w.outline ?? '2';
    document.getElementById('wmImageWidth').value=w.image_scale ?? w.image_width ?? '100';
    document.getElementById('wmImageX').value=w.image_x ?? '';
    document.getElementById('wmImageY').value=w.image_y ?? '';
    const ib=document.getElementById('wmIntervals'); ib.innerHTML=''; (w.intervals || []).forEach(addWatermarkInterval);
    syncWatermarkVisibility(); syncWatermarkFontControl(); out.textContent='Settings loaded';
  }catch(e){out.textContent='Could not load watermark settings';}
}
async function saveWatermark(){
  const intervals=[...document.querySelectorAll('.wm-interval')].map(row=>({start:row.children[0].value,end:row.children[1].value,position:row.children[2].value}));
  const payload={
    enabled:document.getElementById('wmEnabled').checked,
    timing:document.getElementById('wmTiming').value,
    type:document.getElementById('wmType').value,
    text:document.getElementById('wmText').value,
    same_font:document.getElementById('wmSameFont').checked,
    font:document.getElementById('wmFont').value,
    image:document.getElementById('wmImage').value,
    position:document.getElementById('wmPosition').value,
    size:document.getElementById('wmSize').value,
    opacity:document.getElementById('wmOpacity').value,
    margin:document.getElementById('wmMargin').value,
    outline:document.getElementById('wmOutline').value,
    image_scale:document.getElementById('wmImageWidth').value,
    image_x:document.getElementById('wmImageX').value,
    image_y:document.getElementById('wmImageY').value,
    intervals
  };
  const out=document.getElementById('wmresult'); out.textContent='Saving...';
  try{
    const r=await fetch('/api/job/watermark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Queued':'Save failed');
    if(r.ok) setTimeout(loadWatermark,250);
    return r.ok;
  }catch(e){out.textContent='Save failed';return false;}
}
async function previewWatermarkInterval(row){
  const rows=[...document.querySelectorAll('.wm-interval')]; const index=rows.indexOf(row); const out=document.getElementById('wmresult');
  if(index<0){out.textContent='Interval is no longer available';return;}
  if(!await saveWatermark()) return;
  try{
    const r=await fetch('/api/action/preview_interval',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index})});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Boundary preview queued':'Preview failed');
  }catch(e){out.textContent='Boundary preview failed';}
}
function setSimpleSelect(id, values, selected){setSelectOptions(document.getElementById(id), values || [], selected || '');}
function syncEncodingVisibility(){
  const advanced=document.getElementById('encMode').value==='Advanced';
  const quality=document.getElementById('encQuality').value;
  document.querySelectorAll('.encAdvancedOnly').forEach(e=>e.style.display=advanced?'':'none');
  document.querySelectorAll('.encBitrateOnly').forEach(e=>e.style.display=(advanced||quality==='Custom bitrate')?'':'none');
  document.querySelectorAll('.encTargetOnly').forEach(e=>e.style.display=(advanced||quality==='Target file size')?'':'none');
}
async function loadEncoding(){
  const out=document.getElementById('encresult');
  try{
    const r=await fetch('/api/job',{cache:'no-store'}); const d=await r.json(); const e=d.encoding || {};
    setSimpleSelect('encMode', e.mode_options, e.mode);
    setSimpleSelect('encExt', e.output_ext_options, e.output_ext);
    setSimpleSelect('encCodec', e.codec_options, e.codec);
    setSimpleSelect('encQuality', e.quality_options, e.quality);
    setSimpleSelect('encPolicy', e.policy_options, e.policy);
    setSimpleSelect('encSpeed', e.speed_options, e.speed);
    setSimpleSelect('encResolution', e.resolution_options, e.resolution);
    setSimpleSelect('encFps', e.fps_options, e.fps);
    setSimpleSelect('encAudio', e.audio_options, e.audio);
    setSimpleSelect('encEncoder', e.encoder_options, e.encoder);
    document.getElementById('encBitrate').value=e.custom_bitrate ?? '2000';
    document.getElementById('encTarget').value=e.target_size ?? '100';
    document.getElementById('encChapter').checked=!!e.chapter;
    syncEncodingVisibility(); out.textContent='Settings loaded';
  }catch(err){out.textContent='Could not load encoding settings';}
}
async function saveEncoding(){
  const payload={
    mode:document.getElementById('encMode').value,
    output_ext:document.getElementById('encExt').value,
    codec:document.getElementById('encCodec').value,
    quality:document.getElementById('encQuality').value,
    policy:document.getElementById('encPolicy').value,
    speed:document.getElementById('encSpeed').value,
    resolution:document.getElementById('encResolution').value,
    fps:document.getElementById('encFps').value,
    audio:document.getElementById('encAudio').value,
    encoder:document.getElementById('encEncoder').value,
    custom_bitrate:document.getElementById('encBitrate').value,
    target_size:document.getElementById('encTarget').value,
    chapter:document.getElementById('encChapter').checked
  };
  const out=document.getElementById('encresult'); out.textContent='Saving...';
  try{
    const r=await fetch('/api/job/encoding',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Queued':'Save failed');
    if(r.ok) setTimeout(loadEncoding,250);
  }catch(err){out.textContent='Save failed';}
}
let subFallbackFonts=[];
function renderFallbackFonts(){
  const box=document.getElementById('subFallbackSelected'); if(!box)return; box.innerHTML='';
  subFallbackFonts.forEach((name,index)=>{
    const chip=document.createElement('span'); chip.className='fallback-chip';
    const text=document.createElement('span'); text.textContent=name; chip.appendChild(text);
    const remove=document.createElement('button'); remove.type='button'; remove.textContent='×'; remove.setAttribute('aria-label','Remove '+name);
    remove.onclick=()=>{subFallbackFonts.splice(index,1);renderFallbackFonts();}; chip.appendChild(remove); box.appendChild(chip);
  });
  if(!subFallbackFonts.length){const empty=document.createElement('span');empty.className='muted';empty.textContent='No fallback fonts selected';box.appendChild(empty);}
}
function addFallbackFont(){
  const picker=document.getElementById('subFallbackPicker'); const value=(picker&&picker.value)||'';
  if(value && !subFallbackFonts.includes(value)){subFallbackFonts.push(value);renderFallbackFonts();}
}

async function loadSubtitles(){
  const out=document.getElementById('subresult');
  try{
    const r=await fetch('/api/job',{cache:'no-store'}); const d=await r.json(); const s=d.subtitles || {};
    setSimpleSelect('subFont', s.font_options, s.primary_font);
    const fb=document.getElementById('subFallbackPicker'); setSelectOptions(fb, s.font_options || [], (s.fallback_fonts || [])[0] || '');
    subFallbackFonts=[...(s.fallback_fonts || [])]; renderFallbackFonts();
    document.getElementById('subFontSize').value=s.font_size ?? '28';
    document.getElementById('subOutline').value=s.outline ?? '2';
    document.getElementById('subMargin').value=s.margin ?? '24';
    document.getElementById('subSafe').value=s.safe_area ?? '8';
    document.getElementById('subWrap').value=s.wrap_chars ?? '0';
    document.getElementById('subMaxLines').value=s.max_lines ?? '0';
    document.getElementById('subOffset').value=s.offset_ms ?? '0';
    document.getElementById('subTextRgb').value=s.text_rgb ?? 'FFFFFF';
    document.getElementById('subOutlineRgb').value=s.outline_rgb ?? '000000';
    document.getElementById('subBold').checked=!!s.force_bold;
    document.getElementById('subItalic').checked=!!s.italic;
    document.getElementById('subUnderline').checked=!!s.underline;
    document.getElementById('subStrikeout').checked=!!s.strikeout;
    document.getElementById('subTextOpacity').value=s.text_opacity ?? '100';
    document.getElementById('subOutlineOpacity').value=s.outline_opacity ?? '100';
    document.getElementById('subShadowDepth').value=s.shadow_depth ?? '0';
    document.getElementById('subShadowRgb').value=s.shadow_rgb ?? '000000';
    document.getElementById('subShadowOpacity').value=s.shadow_opacity ?? '100';
    document.getElementById('subLetterSpacing').value=s.letter_spacing ?? '0';
    document.getElementById('subRotation').value=s.rotation_angle ?? '0';
    setSelectOptions(document.getElementById('subAlignment'), s.alignment_options || [], s.subtitle_alignment || 'Bottom center');
    document.getElementById('subMarginLeft').value=s.margin_left ?? '10';
    document.getElementById('subMarginRight').value=s.margin_right ?? '10';
    document.getElementById('subBackgroundBox').checked=!!s.background_box;
    document.getElementById('subBackgroundRgb').value=s.background_rgb ?? '000000';
    document.getElementById('subBackgroundOpacity').value=s.background_opacity ?? '65';
    document.getElementById('subBackgroundPadding').value=s.background_padding ?? '4';
    const ce=document.getElementById('subCaptionEffect'); ce.innerHTML='';
    (s.caption_effect_options || []).forEach(item=>{const o=document.createElement('option');o.value=item.id;o.textContent=item.label;ce.appendChild(o);});
    ce.value=s.caption_effect_id || 'none';
    const cp=s.caption_effect_params || {};
    document.getElementById('subCaptionActiveRgb').value=cp.active_rgb ?? 'FFD400';
    document.getElementById('subCaptionEstimate').checked=cp.allow_estimated_timing !== false;
    setSelectOptions(document.getElementById('subSafeZone'), s.platform_safe_zone_options || [], s.platform_safe_zone || 'Off');
    out.textContent='Settings loaded';
  }catch(err){out.textContent='Could not load subtitle settings';}
}
async function saveSubtitles(){
  const payload={
    primary_font:document.getElementById('subFont').value,
    fallback_fonts:[...subFallbackFonts],
    font_size:document.getElementById('subFontSize').value,
    outline:document.getElementById('subOutline').value,
    margin:document.getElementById('subMargin').value,
    safe_area:document.getElementById('subSafe').value,
    wrap_chars:document.getElementById('subWrap').value,
    max_lines:document.getElementById('subMaxLines').value,
    offset_ms:document.getElementById('subOffset').value,
    text_rgb:document.getElementById('subTextRgb').value,
    outline_rgb:document.getElementById('subOutlineRgb').value,
    force_bold:document.getElementById('subBold').checked,
    italic:document.getElementById('subItalic').checked,
    underline:document.getElementById('subUnderline').checked,
    strikeout:document.getElementById('subStrikeout').checked,
    text_opacity:document.getElementById('subTextOpacity').value,
    outline_opacity:document.getElementById('subOutlineOpacity').value,
    shadow_depth:document.getElementById('subShadowDepth').value,
    shadow_rgb:document.getElementById('subShadowRgb').value,
    shadow_opacity:document.getElementById('subShadowOpacity').value,
    letter_spacing:document.getElementById('subLetterSpacing').value,
    rotation_angle:document.getElementById('subRotation').value,
    subtitle_alignment:document.getElementById('subAlignment').value,
    margin_left:document.getElementById('subMarginLeft').value,
    margin_right:document.getElementById('subMarginRight').value,
    background_box:document.getElementById('subBackgroundBox').checked,
    background_rgb:document.getElementById('subBackgroundRgb').value,
    background_opacity:document.getElementById('subBackgroundOpacity').value,
    background_padding:document.getElementById('subBackgroundPadding').value,
    caption_effect_id:document.getElementById('subCaptionEffect').value,
    caption_effect_params:{active_rgb:document.getElementById('subCaptionActiveRgb').value,allow_estimated_timing:document.getElementById('subCaptionEstimate').checked},
    platform_safe_zone:document.getElementById('subSafeZone').value
  };
  const out=document.getElementById('subresult'); out.textContent='Saving...';
  try{
    const r=await fetch('/api/job/subtitles',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Queued':'Save failed');
    if(r.ok) setTimeout(loadSubtitles,250);
  }catch(err){out.textContent='Save failed';}
}
async function importFont(){
  const path=document.getElementById('subImportFontPath').value.trim(); const out=document.getElementById('subresult');
  if(!path){out.textContent='Choose a font file first';return;}
  try{
    const r=await fetch('/api/font/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})});
    const d=await r.json(); out.textContent=d.message || (r.ok?'Queued':'Import failed');
    if(r.ok)setTimeout(loadSubtitles,1500);
  }catch(err){out.textContent='Import failed';}
}
function renderState(d){
    applyAppearance(d.appearance||currentAppearance);
    document.getElementById('app').textContent = d.app;
    document.getElementById('jobline').textContent = d.job ? ('Job: ' + d.job) : 'No active job';
    document.getElementById('stagename').firstChild.textContent = (d.display_stage || d.stage) + ' ';
    document.getElementById('statuspill').textContent = d.status;
    document.getElementById('stagemsg').textContent = (d.display_stage_message || d.stage_message);
    const stageBar=document.getElementById('stagebar');
    const transfer=d.metric_profile==='transfer';
    const transferKnown=transfer && Number(d.bytes_total||0)>0;
    const numericKnown=transferKnown || d.progress_mode==='determinate';
    const animateIndeterminate=!numericKnown && !['succeeded','failed','cancelled'].includes(d.operation_state);
    stageBar.classList.toggle('indeterminate', animateIndeterminate);
    stageBar.style.width = animateIndeterminate ? '35%' : (numericKnown ? (Number(d.progress_pct ?? d.overall_pct ?? 0) + '%') : '0%');
    const setMetric=(id,visible)=>{const el=document.getElementById(id);if(el)el.style.display=visible?'':'none';};
    document.getElementById('elapsed-label').textContent = transfer ? 'Transfer time' : 'Elapsed';
    document.getElementById('elapsed').textContent = (transfer?Number(d.transfer_elapsed||0):Number(d.elapsed||0)).toFixed(1) + 's';
    document.getElementById('progress-label').textContent = transfer ? 'Download' : 'Progress';
    document.getElementById('pct').textContent = numericKnown ? (Number(transfer?d.transfer_pct:(d.progress_pct ?? d.overall_pct ?? 0)).toFixed(1) + '%') : '-';
    document.getElementById('fps').textContent = d.fps;
    document.getElementById('speed-label').textContent = transfer ? 'Transfer speed' : 'Speed';
    document.getElementById('speed').textContent = d.speed;
    document.getElementById('downloaded').textContent = d.downloaded || '-';
    document.getElementById('eta-label').textContent = transfer ? 'Remaining' : 'ETA';
    document.getElementById('eta').textContent = d.eta;
    setMetric('metric-fps', !transfer && d.fps && d.fps!=='-');
    setMetric('metric-downloaded', transfer);
    setMetric('metric-speed', transfer || (d.speed && d.speed!=='-'));
    setMetric('metric-eta', transfer || (d.eta && d.eta!=='-'));
    const media=d.media||{}, duration=Number(media.duration||0), fpsValue=Number(media.fps||0), seek=document.getElementById('liveSeek');
    const liveMax=duration>0?Math.max(0,duration-(fpsValue>0?1/fpsValue:0.04)):0; seek.max=liveMax; if(Number(seek.value)>liveMax&&liveMax>=0)seek.value=0; syncLiveSeekLabel();
    document.getElementById('hist').innerHTML = (d.display_history || d.history).map(h => `<div>${h.ts} - ${h.name}: ${h.message}</div>`).join('') || '<div>No history yet</div>';
    const logEl = document.getElementById('log');
    const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 10;
    logEl.textContent = d.log.map(l => `[${l.ts}] ${l.text}`).join('\\n');
    if(atBottom) logEl.scrollTop = logEl.scrollHeight;
}
async function tick(){
  try{
    const r = await fetch('/api/state', {cache:'no-store'});
    const d = await r.json();
    renderState(d);
  }catch(e){
    document.getElementById('jobline').textContent = 'Disconnected, retrying...';
  }
  setTimeout(tick, 600);
}
tick();
try{showPage(sessionStorage.getItem('subburnPage')||'home');}catch(e){showPage('home');}
loadAppearance();
loadProject();
loadRecents();
loadWatermark();
loadEncoding();
loadSubtitles();
</script></body></html>"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass
    def _allowed_hosts(self):
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}".casefold(), f"localhost:{port}".casefold()}
    def trusted_request(self):
        host = str(self.headers.get("Host", "") or "").strip().casefold()
        if not host or host not in self._allowed_hosts():
            return False
        origin = str(self.headers.get("Origin", "") or "").strip().casefold()
        if origin and origin not in {f"http://{x}" for x in self._allowed_hosts()}:
            return False
        return True
    def authenticated_request(self):
        raw = str(self.headers.get("Cookie", "") or "")
        try:
            jar = http.cookies.SimpleCookie(); jar.load(raw)
            morsel = jar.get("SubBurnSession")
            supplied = morsel.value if morsel is not None else ""
        except Exception:
            supplied = ""
        expected = str(getattr(self.server, "session_token", "") or "")
        return bool(expected and supplied and secrets.compare_digest(supplied, expected))
    def session_cookie_value(self):
        token = str(getattr(self.server, "session_token", "") or "")
        return f"SubBurnSession={token}; Path=/; HttpOnly; SameSite=Strict"
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", DASHBOARD_CSP)
        super().end_headers()
    def validate_post_request(self, limit=65536):
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-Encoding is not supported")
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except Exception:
            raise ValueError("Invalid Content-Length")
        if length < 0 or length > int(limit):
            raise ValueError("Request body is too large")
        return length
    def send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
    def read_json_body(self, limit=65536, validated_length=None):
        length = self.validate_post_request(limit) if validated_length is None else int(validated_length)
        content_type = str(self.headers.get("Content-Type", "") or "").split(";", 1)[0].strip().casefold()
        if length and content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON request body must be an object")
        return value
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not self.trusted_request():
            self.send_json(403, {"ok": False, "message": "Dashboard request rejected"})
            return
        if path.startswith("/api/") and not self.authenticated_request():
            self.send_json(403, {"ok": False, "message": "Dashboard session is not authorized"})
            return
        controller = getattr(self.server, "controller", None)
        if path == "/api/live/clip/status":
            controller = getattr(self.server, "controller", None)
            qs = urllib.parse.parse_qs(parsed.query)
            expected = (qs.get("at") or [None])[0]
            after_revision = (qs.get("after") or [None])[0]
            info = controller.dashboard_live_clip_info(expected, after_revision) if controller is not None else None
            if info:
                self.send_json(200, {"ready": True, "timestamp": info["timestamp"], "duration": info["duration"], "revision": info["revision"]})
            else:
                self.send_json(200, {"ready": False})
        elif path == "/api/live/clip":
            controller = getattr(self.server, "controller", None)
            qs = urllib.parse.parse_qs(parsed.query)
            expected = (qs.get("at") or [None])[0]
            revision = (qs.get("rev") or [None])[0]
            info = controller.dashboard_live_clip_info(expected, None) if controller is not None else None
            if not info or (revision is not None and str(info["revision"]) != str(revision)):
                self.send_json(404, {"ok": False, "message": "Playback preview is not ready"})
                return
            clip = Path(info["path"]); size = clip.stat().st_size
            start, end = 0, size - 1
            range_header = self.headers.get("Range", "")
            partial = False
            if range_header:
                m = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
                if not m:
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
                a, b = m.groups()
                if a:
                    start = int(a); end = int(b) if b else size - 1
                elif b:
                    length = int(b); start = max(0, size - length); end = size - 1
                if start < 0 or start >= size or end < start:
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
                end = min(end, size - 1); partial = True
            length = end - start + 1
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with clip.open("rb") as f:
                f.seek(start); self.wfile.write(f.read(length))
        elif path == "/api/live/frame":
            controller = getattr(self.server, "controller", None)
            qs = urllib.parse.parse_qs(parsed.query)
            expected = (qs.get("at") or [None])[0]
            after_revision = (qs.get("after") or [None])[0]
            frame = controller.dashboard_live_frame_path(expected, after_revision) if controller is not None else None
            if not frame:
                self.send_json(404, {"ok": False, "message": "No live preview frame is ready"})
                return
            try:
                data = Path(frame).read_bytes()
            except Exception as e:
                self.send_json(404, {"ok": False, "message": str(e)})
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/state":
            self.send_json(200, self.server.op_state.snapshot())
        elif path == "/api/job":
            self.send_json(200, self.server.op_state.control_snapshot())
        elif path == "/api/queue":
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            self.send_json(200, controller.dashboard_queue_snapshot())
        elif path == "/api/fs":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            qs = urllib.parse.parse_qs(parsed.query)
            kind = (qs.get("kind") or [""])[0]
            raw_path = (qs.get("path") or [""])[0]
            try:
                self.send_json(200, controller.dashboard_filesystem_listing(raw_path, kind))
            except Exception as e:
                self.send_json(400, {"ok": False, "message": str(e)})
        elif path in {"/", "/index.html"}:
            data = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Set-Cookie", self.session_cookie_value())
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_json(404, {"ok": False, "message": "Dashboard resource not found"})
    def do_POST(self):
        if not self.trusted_request() or not self.authenticated_request():
            self.send_json(403, {"ok": False, "message": "Dashboard request rejected"})
            return
        try:
            request_length = self.validate_post_request(65536)
        except ValueError as exc:
            self.send_json(400, {"ok": False, "message": str(exc)})
            return
        path = self.path.split("?", 1)[0]
        controller = getattr(self.server, "controller", None)
        if path.startswith("/api/queue/"):
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            action = path[len("/api/queue/"):].strip().casefold()
            if action in {"add_recent", "add_custom", "delete", "delete_many", "duplicate"}:
                try:
                    payload = self.read_json_body(65536, request_length)
                except Exception as e:
                    self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                    return
                ok, message = controller.queue_dashboard_queue_item_action(action, payload)
                self.send_json(202 if ok else 400, {"ok": ok, "message": message})
                return
            allowed = {"add_current", "start", "pause", "cancel_current", "retry_all", "clear_completed", "clear_queued"}
            if action not in allowed:
                self.send_json(404, {"ok": False, "message": "Unknown queue action"})
                return
            ok, message = controller.queue_dashboard_queue_action(action)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message})
            return
        if path == "/api/font/import":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                font_path = payload.get("path", "") if isinstance(payload, dict) else ""
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            ok, message = controller.queue_dashboard_font_import(font_path)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message})
            return
        if path in {"/api/job/appearance", "/api/job/watermark", "/api/job/encoding", "/api/job/subtitles", "/api/job/project", "/api/job/transcription"}:
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            panel = path.rsplit("/", 1)[-1]
            ok, message = controller.queue_dashboard_settings(panel, payload)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message})
            return
        if path == "/api/recent/clear":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                kind = payload.get("kind") if isinstance(payload, dict) else None
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            ok, message = controller.queue_clear_recents(kind)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message})
            return
        if path == "/api/recent/restore":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                index = payload.get("index") if isinstance(payload, dict) else None
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            ok, message = controller.queue_recent_project_restore(index)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message})
            return
        if path == "/api/action/live_clip":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                timestamp = payload.get("timestamp") if isinstance(payload, dict) else None
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            revision = controller.dashboard_live_clip_revision()
            ok, message = controller.queue_dashboard_live_clip(timestamp)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message, "after_revision": revision})
            return
        if path == "/api/action/live_frame":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                timestamp = payload.get("timestamp") if isinstance(payload, dict) else None
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            revision = controller.dashboard_live_frame_revision()
            ok, message = controller.queue_dashboard_live_frame(timestamp)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message, "after_revision": revision})
            return
        if path == "/api/live/position":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                x = payload.get("x") if isinstance(payload, dict) else None
                y = payload.get("y") if isinstance(payload, dict) else None
                timestamp = payload.get("timestamp") if isinstance(payload, dict) else None
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            revision = controller.dashboard_live_frame_revision()
            ok, message = controller.queue_dashboard_live_position(x, y, timestamp)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message, "after_revision": revision})
            return
        if path == "/api/action/preview_interval":
            controller = getattr(self.server, "controller", None)
            if controller is None:
                self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
                return
            try:
                payload = self.read_json_body(65536, request_length)
                index = payload.get("index") if isinstance(payload, dict) else None
            except Exception as e:
                self.send_json(400, {"ok": False, "message": f"Invalid JSON: {e}"})
                return
            ok, message = controller.queue_dashboard_interval_preview(index)
            self.send_json(202 if ok else 400, {"ok": ok, "message": message})
            return
        prefix = "/api/action/"
        if not path.startswith(prefix):
            self.send_json(404, {"ok": False, "message": "Unknown dashboard endpoint"})
            return
        action = path[len(prefix):].strip().casefold()
        controller = getattr(self.server, "controller", None)
        if controller is None:
            self.send_json(503, {"ok": False, "message": "SubBurn controls are not ready yet"})
            return
        ok, message = controller.queue_dashboard_action(action)
        self.send_json(202 if ok else 400, {"ok": ok, "message": message})

def start_dashboard_server(op_state, preferred_port=None, controller=None):
    ports = [0] if preferred_port is None else list(range(int(preferred_port), int(preferred_port) + 25))
    for port in ports:
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
        except OSError:
            continue
        server.op_state = op_state
        server.controller = controller
        server.session_token = secrets.token_urlsafe(32)
        thread = threading.Thread(target=server.serve_forever, daemon=True, name="SubBurn-dashboard")
        thread.start()
        return server, int(server.server_address[1])
    return None, None

class SubBurnApp:
    @property
    def _job(self):
        local = getattr(self, "_job_local", None)
        if local is not None and hasattr(local, "job"):
            return local.job
        return None
    @_job.setter
    def _job(self, value):
        # Compatibility for focused tests/helpers that assign app._job directly, while keeping
        # the value local to the calling thread.  Production run_job() installs the snapshot only
        # inside its worker and never writes a shared main-thread fallback.
        if getattr(self, "_job_local", None) is None:
            self._job_local = threading.local()
        self._job_local.job = value
    def __init__(self, root):
        self.root = root
        self.root.title("SubBurn")
        self.root.geometry("1180x820")
        self.root.minsize(980, 680)
        for p in (APP_HOME, RUNTIME_DIR, FONT_DIR, PREVIEW_DIR, LOG_DIR, DIAG_DIR):
            p.mkdir(parents=True, exist_ok=True)
        self.events = queue.Queue()
        self.toolset = None
        self.local_toolsets = []
        self.fonts = []
        self.font_map = {}
        self.media = None
        self.help_cache = {}
        self.benchmark_scores = {}
        self.tuning_cache = {}
        self._font_cache_keys = {}
        self._glyph_coverage_cache = {}
        self.encoder_cache = load_encoder_cache()
        self.current_process = None
        self.process_lock = threading.Lock()
        self.active_processes = {}
        self.cancelled_processes = set()
        self.active_jobs_lock = threading.Lock()
        self.active_jobs = 0
        self.running = False
        self.paused = False
        self.close_when_idle = False
        self.browser_only = False
        self._autosave_after = None
        self.live_frame_generation = 0
        self.live_frame_lock = threading.Lock()
        self.live_frame_revision = 0
        self.latest_live_frame = None
        self.latest_live_timestamp = None
        self.live_clip_generation = 0
        self.live_clip_lock = threading.Lock()
        self.live_clip_revision = 0
        self.latest_live_clip = None
        self.latest_live_clip_timestamp = None
        self.latest_live_clip_duration = 0.0
        self.watermark_rows = []
        self.recents = self.load_recents()
        self.last_output = None
        self.drop = DropBinder(root)
        self.stage_names = ["Tools", "Fonts", "Media", "Subtitles", "Glyphs", "Filters", "Watermark", "Encoder", "Preview", "Encode", "Verify"]
        self._operation_local = threading.local()
        self.op_state = OperationState()
        self.ffmpeg_setup_lock = threading.Lock()
        self._automatic_ffmpeg_install_attempted = False
        self._theme_canvases = []
        self.dashboard_server, self.dashboard_port = start_dashboard_server(self.op_state, controller=self)
        self._job_local = threading.local()
        self._job = None
        self.vars()
        self.load_settings()
        self.user_presets = self.load_user_presets()
        self.batch_store = BurnQueueStore(QUEUE_DB)
        self.batch_runner_lock = threading.Lock()
        self.batch_runner_thread = None
        self.batch_runner_active = False
        self.batch_operation_id = None
        self.batch_current_id = None
        self.batch_pause_requested = False
        self.batch_continue_on_error = True
        self.transcription_cancel_event = threading.Event()
        self.transcription_thread = None
        self.latest_transcription_srt = None
        self.latest_transcription_words = None
        self.system_usage_sampler = SystemUsageSampler()
        self.system_usage_sampler.start()
        self.style()
        self.ui()
        self.root.after(0, lambda: apply_native_windows_glass(self.root, self.appearance_var.get()))
        self.install_autosave_traces()
        self.publish_dashboard_controls()
        self.root.after(100, self.drain)
        self.root.after(200, self.scan_fonts_async)
        self.root.after(300, self.discover_tools_async)
        self.root.after(500, self.tick_dashboard)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
    def vars(self):
        self.ffmpeg_var = tk.StringVar()
        self.appearance_var = tk.StringVar(value="Dark")
        self.tool_var = tk.StringVar(value="Toolset not ready")
        self.video_var = tk.StringVar()
        self.subtitle_source_var = tk.StringVar(value="Auto")
        self.subtitle_file_var = tk.StringVar()
        self.embedded_track_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(SUBBURN_OUTPUT_DIR))
        self.output_name_var = tk.StringVar(value="SubBurn-output")
        self.output_ext_var = tk.StringVar(value=".mp4")
        self.clean_output_var = tk.BooleanVar(value=True)
        self.primary_font_var = tk.StringVar()
        self.fallback_font_var = tk.StringVar()
        self.same_wm_font_var = tk.BooleanVar(value=True)
        self.wm_font_var = tk.StringVar()
        self.font_size_var = tk.StringVar(value="28")
        self.force_bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        self.underline_var = tk.BooleanVar(value=False)
        self.strikeout_var = tk.BooleanVar(value=False)
        self.text_opacity_var = tk.StringVar(value="100")
        self.outline_opacity_var = tk.StringVar(value="100")
        self.shadow_depth_var = tk.StringVar(value="0")
        self.shadow_rgb_var = tk.StringVar(value="000000")
        self.shadow_opacity_var = tk.StringVar(value="100")
        self.letter_spacing_var = tk.StringVar(value="0")
        self.rotation_angle_var = tk.StringVar(value="0")
        self.subtitle_alignment_var = tk.StringVar(value="Bottom center")
        self.margin_left_var = tk.StringVar(value="10")
        self.margin_right_var = tk.StringVar(value="10")
        self.background_box_var = tk.BooleanVar(value=False)
        self.background_rgb_var = tk.StringVar(value="000000")
        self.background_opacity_var = tk.StringVar(value="65")
        self.background_padding_var = tk.StringVar(value="4")
        self.caption_effect_var = tk.StringVar(value="None")
        self.caption_active_rgb_var = tk.StringVar(value="FFD400")
        self.caption_estimated_timing_var = tk.BooleanVar(value=True)
        self.outline_var = tk.StringVar(value="2")
        self.margin_var = tk.StringVar(value="24")
        self.text_rgb_var = tk.StringVar(value="FFFFFF")
        self.outline_rgb_var = tk.StringVar(value="000000")
        self.safe_area_var = tk.StringVar(value="8")
        self.platform_safe_zone_var = tk.StringVar(value="Off")
        self.wrap_chars_var = tk.StringVar(value="0")
        self.max_lines_var = tk.StringVar(value="0")
        self.subtitle_offset_var = tk.StringVar(value="0")
        self.watermark_enabled_var = tk.BooleanVar(value=False)
        self.watermark_type_var = tk.StringVar(value="Text")
        self.watermark_text_var = tk.StringVar()
        self.watermark_image_var = tk.StringVar()
        self.watermark_timing_var = tk.StringVar(value="Full duration")
        self.watermark_position_var = tk.StringVar(value="Top right")
        self.watermark_size_var = tk.StringVar(value="24")
        self.watermark_opacity_var = tk.StringVar(value="85")
        self.watermark_margin_var = tk.StringVar(value="20")
        self.watermark_outline_var = tk.StringVar(value="2")
        self.watermark_image_width_var = tk.StringVar(value="15")
        self.watermark_image_scale_var = tk.StringVar(value="100")
        self.watermark_image_x_var = tk.StringVar(value="")
        self.watermark_image_y_var = tk.StringVar(value="")
        self.codec_var = tk.StringVar(value="Match source")
        self.quality_mode_var = tk.StringVar(value="Preserve visual quality")
        self.speed_mode_var = tk.StringVar(value="Balanced")
        self.encoder_policy_var = tk.StringVar(value="Balanced")
        self.encoder_var = tk.StringVar(value="Auto")
        self.custom_bitrate_var = tk.StringVar(value="2000")
        self.target_size_var = tk.StringVar(value="100")
        self.resolution_var = tk.StringVar(value="Original")
        self.fps_var = tk.StringVar(value="Original")
        self.audio_mode_var = tk.StringVar(value="Copy all audio")
        self.chapter_var = tk.BooleanVar(value=True)
        self.mode_var = tk.StringVar(value="Simple")
        self.media_var = tk.StringVar(value="No media loaded")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.fps_status_var = tk.StringVar(value="FPS: -")
        self.speed_status_var = tk.StringVar(value="Speed: -")
        self.transfer_status_var = tk.StringVar(value="Downloaded: -")
        self.eta_var = tk.StringVar(value="ETA: -")
        self.estimate_var = tk.StringVar(value="Estimated size: -")
        self.dnd_var = tk.StringVar(value=self.drop.status_text())
        self.metadata_vars = {key: tk.StringVar() for key in USER_METADATA_KEYS}
        self.live_seek_var = tk.DoubleVar(value=0.0)
        self.live_seek_text_var = tk.StringVar(value="00:00.000")
        self.preset_name_var = tk.StringVar(value="")
        self.preset_scope_subtitles_var = tk.BooleanVar(value=True)
        self.preset_scope_watermark_var = tk.BooleanVar(value=True)
        self.preset_scope_encoding_var = tk.BooleanVar(value=True)
        self.batch_continue_on_error_var = tk.BooleanVar(value=True)
        self.batch_status_var = tk.StringVar(value="Queue idle")
        self.batch_progress_var = tk.DoubleVar(value=0.0)
        self.transcription_model_var = tk.StringVar(value="large-v3")
        self.transcription_language_mode_var = tk.StringVar(value="Auto multilingual (detect changes)")
        self.transcription_language_code_var = tk.StringVar(value="")
        self.transcription_language_picker_var = tk.StringVar(value=WHISPER_LANGUAGE_PICKER_PROMPT)
        self.transcription_device_var = tk.StringVar(value="Auto")
        self.transcription_status_var = tk.StringVar(value="Local transcription idle")
        self.transcription_progress_var = tk.DoubleVar(value=0.0)
        self.transcription_result_var = tk.StringVar(value="No transcription generated yet")
        self.transcription_model_info_var = tk.StringVar(value="Model size information loading…")
    def style(self):
        style = ttk.Style(self.root)
        # Tk cannot do true per-widget backdrop blur. We use a liquid-glass hierarchy instead:
        # luminous edge highlights, layered blue/slate surfaces and mode-aware contrast. The
        # browser dashboard uses real backdrop-filter blur where the browser supports it.
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self.appearance_var.set(normalize_appearance_mode(self.appearance_var.get()))
        self.ui_colors = appearance_palette(self.appearance_var.get())
        c = self.ui_colors
        self.root.configure(background=c["app"])
        # Combobox pop-downs are classic Tk listboxes even when the field is ttk.
        for pattern, value in (
            ("*TCombobox*Listbox.background", c["surface"]),
            ("*TCombobox*Listbox.foreground", c["text"]),
            ("*TCombobox*Listbox.selectBackground", c["accent_soft"]),
            ("*TCombobox*Listbox.selectForeground", c["selection_text"]),
            ("*TCombobox*Listbox.font", "{Segoe UI} 10"),
            ("*TCombobox*Listbox.relief", "flat"),
            ("*TCombobox*Listbox.borderWidth", 1),
        ):
            try:
                self.root.option_add(pattern, value)
            except Exception:
                pass
        style.configure(".", font=("Segoe UI", 10), background=c["surface"], foreground=c["text"])
        # Structural frames explicitly opt into page/sidebar backgrounds. Default frames are
        # surface-colored so nested rows inside cards do not create contrasting rectangles.
        style.configure("TFrame", background=c["surface"])
        style.configure("App.TFrame", background=c["app"])
        style.configure("Header.TFrame", background=c["app"])
        style.configure("Sidebar.TFrame", background=c["sidebar"])
        style.configure("Page.TFrame", background=c["app"])
        style.configure("Surface.TFrame", background=c["surface"])
        style.configure("TLabel", background=c["surface"], foreground=c["text"])
        style.configure("Title.TLabel", background=c["app"], foreground=c["text"], font=("Segoe UI", 23, "bold"))
        style.configure("Subtitle.TLabel", background=c["app"], foreground=c["muted"], font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=c["surface"], foreground=c["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Muted.TLabel", background=c["surface"], foreground=c["muted"], font=("Segoe UI", 9))
        style.configure("SidebarMuted.TLabel", background=c["sidebar"], foreground=c["sidebar_muted"], font=("Segoe UI", 8, "bold"))
        style.configure("TButton", padding=(11, 7), borderwidth=1, relief="flat", background=c["surface_alt"], foreground=c["text"], bordercolor=c["border"], lightcolor=c["glass_highlight"], darkcolor=c["border_soft"], focusthickness=1, focuscolor=c["accent"])
        style.map("TButton", background=[("active", c["surface_hover"]), ("pressed", c["accent_soft"]), ("disabled", c["surface"])], foreground=[("disabled", c["disabled_text"])], bordercolor=[("focus", c["accent"]), ("active", c["border"])])
        style.configure("Accent.TButton", padding=(15, 9), borderwidth=1, relief="flat", background=c["accent"], foreground="#FFFFFF", bordercolor=c["accent"], lightcolor=c["accent"], darkcolor=c["accent"], font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", c["accent_hover"]), ("pressed", c["accent_soft"]), ("disabled", c["disabled_bg"])], foreground=[("disabled", c["disabled_text"])], bordercolor=[("focus", "#AFC1FF")])
        style.configure("Danger.TButton", padding=(11, 7), borderwidth=1, relief="flat", background=c["danger"], foreground="#FFFFFF", bordercolor=c["danger"], lightcolor=c["danger"], darkcolor=c["danger"])
        style.map("Danger.TButton", background=[("active", c["danger_hover"]), ("pressed", c["danger"]), ("disabled", c["surface"])], foreground=[("disabled", c["disabled_text"])], bordercolor=[("focus", c["danger_hover"])])
        style.configure("Nav.TButton", padding=(14, 11), anchor="w", borderwidth=1, relief="flat", background=c["sidebar"], foreground=c["muted"], bordercolor=c["sidebar"], lightcolor=c["sidebar"], darkcolor=c["sidebar"])
        style.map("Nav.TButton", background=[("active", c["surface_hover"]), ("pressed", c["accent_soft"])], foreground=[("active", c["text"])], bordercolor=[("focus", c["accent"])])
        style.configure("NavActive.TButton", padding=(14, 11), anchor="w", borderwidth=1, relief="flat", background=c["accent_soft"], foreground=c["text"], bordercolor="#31538A", lightcolor="#31538A", darkcolor="#31538A", font=("Segoe UI", 10, "bold"))
        style.map("NavActive.TButton", background=[("active", c["accent_hover"]), ("pressed", c["accent"])], foreground=[("active", c["selection_text"])], bordercolor=[("focus", c["accent_hover"])])
        style.configure("Status.TFrame", background=c["surface_alt"], relief="raised", borderwidth=1, bordercolor=c["border"], lightcolor=c["glass_highlight"], darkcolor=c["border_soft"])
        style.configure("Status.TLabel", background=c["surface_alt"], foreground=c["text"])
        style.configure("StatusMuted.TLabel", background=c["surface_alt"], foreground=c["muted"], font=("Segoe UI", 9))
        # LabelFrames retain semantic grouping but the heavy native etched/cutout frame is removed.
        # The surface contrast supplies the grouping, eliminating the boxed strips behind labels.
        style.configure("Card.TLabelframe", background=c["surface"], borderwidth=1, bordercolor=c["border"], lightcolor=c["glass_highlight"], darkcolor=c["border_soft"], relief="raised", padding=14)
        style.configure("Card.TLabelframe.Label", background=c["surface"], foreground=c["text"], font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe", background=c["surface"], borderwidth=1, bordercolor=c["border"], lightcolor=c["glass_highlight"], darkcolor=c["border_soft"], relief="raised")
        style.configure("TLabelframe.Label", background=c["surface"], foreground=c["text"], font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background=c["surface"], foreground=c["text"], padding=(2, 2))
        style.map("TCheckbutton", background=[("active", c["surface"])], foreground=[("disabled", c["disabled_text"])])
        style.configure("TRadiobutton", background=c["surface"], foreground=c["text"])
        style.map("TRadiobutton", background=[("active", c["surface"])], foreground=[("disabled", c["disabled_text"])])
        style.configure("TEntry", fieldbackground=c["entry"], foreground=c["text"], bordercolor=c["border"], lightcolor=c["glass_highlight"], darkcolor=c["border"], insertcolor=c["text"], padding=(7, 6))
        style.map("TEntry", fieldbackground=[("disabled", c["disabled_bg"])], foreground=[("disabled", c["disabled_text"])], bordercolor=[("focus", c["accent"])])
        style.configure("TCombobox", fieldbackground=c["entry"], background=c["surface_alt"], foreground=c["text"], selectbackground=c["accent_soft"], selectforeground=c["selection_text"], arrowcolor=c["text"], bordercolor=c["border"], lightcolor=c["glass_highlight"], darkcolor=c["border_soft"], padding=(7, 6), relief="flat")
        style.map("TCombobox", fieldbackground=[("readonly", c["entry"]), ("disabled", c["disabled_bg"])], background=[("readonly", c["surface_alt"]), ("active", c["surface_hover"])], foreground=[("readonly", c["text"]), ("disabled", c["disabled_text"])], selectbackground=[("readonly", c["accent_soft"])], selectforeground=[("readonly", c["selection_text"])], bordercolor=[("focus", c["accent"]), ("active", c["glass_highlight"])], arrowcolor=[("readonly", c["text"]), ("disabled", c["disabled_text"])])
        style.configure("Treeview", background=c["surface"], fieldbackground=c["surface"], foreground=c["text"], rowheight=27, bordercolor=c["border_soft"], lightcolor=c["glass_highlight"], darkcolor=c["border_soft"])
        style.configure("Treeview.Heading", background=c["surface_alt"], foreground=c["muted"], font=("Segoe UI", 9, "bold"), relief="flat", padding=(6, 5), bordercolor=c["border_soft"])
        style.map("Treeview", background=[("selected", c["accent_soft"])], foreground=[("selected", c["selection_text"])])
        for scrollbar_style in ("TScrollbar", "Vertical.TScrollbar", "Horizontal.TScrollbar"):
            style.configure(scrollbar_style, background=c["surface_alt"], troughcolor=c["app"], bordercolor=c["app"], arrowcolor=c["muted"], lightcolor=c["surface_alt"], darkcolor=c["surface_alt"], relief="flat", borderwidth=0, gripcount=0)
            style.map(scrollbar_style, background=[("active", c["surface_hover"]), ("pressed", c["accent_soft"])], arrowcolor=[("active", c["text"])])
        style.configure("Horizontal.TScale", background=c["surface"], troughcolor=c["trough"], bordercolor=c["surface"], lightcolor=c["accent"], darkcolor=c["accent"], sliderrelief="flat")
        style.map("Horizontal.TScale", background=[("active", c["surface"]), ("disabled", c["surface"])])
        style.configure("TSeparator", background=c["border_soft"])
        style.configure("Horizontal.TProgressbar", troughcolor=c["trough"], background=c["accent"], bordercolor=c["trough"], lightcolor=c["accent"], darkcolor=c["accent"], thickness=8)
    def apply_appearance(self, *_args, persist=True):
        mode=normalize_appearance_mode(self.appearance_var.get())
        if self.appearance_var.get()!=mode:
            self.appearance_var.set(mode)
            return
        self.style()
        c=self.ui_colors
        apply_native_windows_glass(self.root, mode)
        for canvas in list(getattr(self,"_theme_canvases",[])):
            try: canvas.configure(background=c["app"])
            except Exception: pass
        for name in ("log_text","recent_projects_list","recent_folders_list","fallback_list"):
            widget=getattr(self,name,None)
            if widget is None: continue
            try:
                widget.configure(bg=c["entry"],fg=c["text"],selectbackground=c["accent_soft"],selectforeground=c["selection_text"],highlightbackground=c["border_soft"],highlightcolor=c["accent"])
                if isinstance(widget,tk.Text): widget.configure(insertbackground=c["text"])
            except Exception: pass
        if persist:
            self.save_settings()
        self.publish_dashboard_controls()

    def apply_appearance_from_settings(self, _event=None):
        self.apply_appearance(persist=True)
        self.log_ui(f"Appearance changed to {self.appearance_var.get()}")

    def create_notebook_page(self, name, scroll=False):
        # Compatibility shim retained during WIP05 migration. New code uses create_workflow_page().
        return self.create_workflow_page(name, scroll=scroll)

    def create_workflow_page(self, name, scroll=False):
        outer = ttk.Frame(self.page_host, style="Page.TFrame")
        outer.grid(row=0, column=0, sticky="nsew")
        self.workflow_pages[name] = outer
        if not scroll:
            inner = ttk.Frame(outer, padding=(22, 18), style="Page.TFrame")
            inner.pack(fill="both", expand=True)
            return inner
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0, background=self.ui_colors["app"])
        self._theme_canvases.append(canvas)
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        inner = ttk.Frame(canvas, padding=(22, 18), style="Page.TFrame")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        def refresh_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def fit_width(event):
            canvas.itemconfigure(window_id, width=max(1, event.width))
            refresh_region()
        inner.bind("<Configure>", refresh_region)
        canvas.bind("<Configure>", fit_width)
        self._page_scroll_canvases[name] = canvas
        return inner
    def scroll_active_page(self, units):
        try:
            canvas = self._page_scroll_canvases.get(getattr(self, "current_workflow_page", ""))
            if canvas is None or not canvas.winfo_exists():
                return None
            canvas.yview_scroll(int(units), "units")
            return "break"
        except Exception:
            return None
    def on_notebook_mousewheel(self, event):
        try:
            delta = int(getattr(event, "delta", 0))
            if not delta:
                return None
            return self.scroll_active_page(-3 if delta > 0 else 3)
        except Exception:
            return None

    def show_workflow_page(self, name):
        page = self.workflow_pages.get(name)
        if page is None:
            return False
        page.tkraise()
        self.current_workflow_page = name
        for label, button in getattr(self, "workflow_nav_buttons", {}).items():
            try:
                button.configure(style="NavActive.TButton" if label == name else "Nav.TButton")
            except Exception:
                pass
        return True
    def ui(self):
        root = ttk.Frame(self.root, padding=(18, 16), style="App.TFrame")
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Header.TFrame")
        header.pack(fill="x", pady=(0, 10))
        title_col = ttk.Frame(header, style="Header.TFrame")
        title_col.pack(side="left", fill="x", expand=True)
        ttk.Label(title_col, text="SubBurn", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_col, text="Burn subtitles into video - preview exactly, then export.", style="Subtitle.TLabel").pack(anchor="w", pady=(1, 0))
        owner_col = ttk.Frame(header, style="Header.TFrame")
        owner_col.pack(side="right", anchor="ne", padx=(18, 0))
        ttk.Label(owner_col, text=f"Made by: {OWNER_NAME}", style="Subtitle.TLabel").pack(anchor="e")
        owner_link = ttk.Label(owner_col, text=f"Contact Owner: {OWNER_TELEGRAM}", style="Subtitle.TLabel", cursor="hand2")
        owner_link.pack(anchor="e", pady=(3, 0))
        owner_link.bind("<Button-1>", lambda _e: open_path(OWNER_TELEGRAM_URL))
        ttk.Button(owner_col, text="Help Manual", command=self.open_help_manual).pack(anchor="e", pady=(7, 0))

        # One canonical operation strip stays visible on every workflow page. Message, bar and
        # operation-specific metrics occupy separate rows so download telemetry never collides.
        status = ttk.Frame(root, padding=(14, 11), style="Status.TFrame")
        status.pack(fill="x", pady=(0, 12))
        status.columnconfigure(0, weight=1)
        self.status_text_label = ttk.Label(status, textvariable=self.status_var, style="Status.TLabel", wraplength=980)
        self.status_text_label.grid(row=0, column=0, sticky="w")
        self.global_progress_bar = ttk.Progressbar(status, variable=self.progress_var, maximum=100, mode="determinate")
        self.global_progress_bar.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._global_progress_mode = "determinate"
        metric_row = ttk.Frame(status, style="Status.TFrame")
        metric_row.grid(row=2, column=0, sticky="w", pady=(7, 0))
        self.progress_status_var = tk.StringVar(value="Progress: 0.0%")
        self.progress_status_label = ttk.Label(metric_row, textvariable=self.progress_status_var, style="StatusMuted.TLabel")
        self.progress_status_label.grid(row=0, column=0, sticky="w")
        self.fps_status_label = ttk.Label(metric_row, textvariable=self.fps_status_var, style="StatusMuted.TLabel")
        self.fps_status_label.grid(row=0, column=1, sticky="w", padx=(14, 0))
        self.speed_status_label = ttk.Label(metric_row, textvariable=self.speed_status_var, style="StatusMuted.TLabel")
        self.speed_status_label.grid(row=0, column=2, sticky="w", padx=(14, 0))
        self.transfer_status_label = ttk.Label(metric_row, textvariable=self.transfer_status_var, style="StatusMuted.TLabel")
        self.transfer_status_label.grid(row=0, column=3, sticky="w", padx=(14, 0))
        self.eta_status_label = ttk.Label(metric_row, textvariable=self.eta_var, style="StatusMuted.TLabel")
        self.eta_status_label.grid(row=0, column=4, sticky="w", padx=(14, 0))
        for _metric in (self.fps_status_label, self.speed_status_label, self.transfer_status_label, self.eta_status_label):
            _metric.grid_remove()

        body = ttk.Frame(root, style="App.TFrame")
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        nav = ttk.Frame(body, padding=(8, 10, 10, 10), style="Sidebar.TFrame")
        nav.grid(row=0, column=0, sticky="ns")
        self.page_host = ttk.Frame(body, style="Page.TFrame")
        self.page_host.grid(row=0, column=1, sticky="nsew")
        self.page_host.rowconfigure(0, weight=1)
        self.page_host.columnconfigure(0, weight=1)
        self.workflow_pages = {}
        self.workflow_nav_buttons = {}
        self._page_scroll_canvases = {}
        ttk.Label(nav, text="WORKSPACE", style="SidebarMuted.TLabel").pack(anchor="w", padx=8, pady=(2, 8))
        self.browser_launch_btn = ttk.Button(nav, text="Browser dashboard  ↗", style="Accent.TButton", command=self.open_dashboard_browser, state=("normal" if self.dashboard_port else "disabled"))
        self.browser_launch_btn.pack(fill="x", padx=4, pady=(0, 14))
        self.root.bind_all("<Control-b>", lambda _e: self.open_dashboard_browser() if self.dashboard_port else None, add="+")

        # Public-edition information architecture: eight logical destinations.
        page_names = ["Home", "Subtitles", "Watermark", "Transcribe", "Preview", "Burn", "Queue", "Settings"]
        for index, name in enumerate(page_names, 1):
            btn = ttk.Button(nav, text=name, style="Nav.TButton", width=18, command=lambda n=name: self.show_workflow_page(n))
            btn.pack(fill="x", pady=(0, 4))
            self.workflow_nav_buttons[name] = btn
            self.root.bind_all(f"<Control-KeyPress-{index}>", lambda _e, n=name: (self.show_workflow_page(n), "break")[1], add="+")

        home = self.create_workflow_page("Home", scroll=True)
        self.page_project = ttk.Frame(home)
        self.page_project.grid(row=0, column=0, sticky="ew")
        self.page_dashboard = ttk.Frame(home)
        self.page_dashboard.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        home.columnconfigure(0, weight=1)

        self.page_design = self.create_workflow_page("Subtitles", scroll=True)
        self.page_watermark = self.create_workflow_page("Watermark", scroll=True)
        self.page_transcription = self.create_workflow_page("Transcribe", scroll=True)
        self.page_live = self.create_workflow_page("Preview", scroll=False)
        self.page_encode = self.create_workflow_page("Burn", scroll=True)
        self.page_batch = self.create_workflow_page("Queue", scroll=True)

        settings = self.create_workflow_page("Settings", scroll=True)
        settings.columnconfigure(0, weight=1)
        self.page_runtime = ttk.Frame(settings)
        self.page_runtime.grid(row=0, column=0, sticky="ew")
        self.page_presets = ttk.Frame(settings)
        self.page_presets.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        self.page_activity = ttk.Frame(settings)
        self.page_activity.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        self.page_about = ttk.Frame(settings)
        self.page_about.grid(row=3, column=0, sticky="ew", pady=(14, 0))

        self.root.bind_all("<MouseWheel>", self.on_notebook_mousewheel, add="+")
        self.root.bind_all("<Button-4>", lambda _e: self.scroll_active_page(-3), add="+")
        self.root.bind_all("<Button-5>", lambda _e: self.scroll_active_page(3), add="+")

        self.project_ui()
        self.dashboard_ui()
        self.design_ui()
        self.watermark_ui()
        self.transcription_ui()
        self.live_preview_ui()
        self.encode_ui()
        self.batch_ui()
        self.runtime_settings_ui()
        self.presets_ui()
        self.activity_ui()
        self.about_ui()
        self.show_workflow_page("Home")
    def builtin_presets(self):
        return [Preset(
            id="builtin-default-burn",
            name="Default burn settings",
            builtin=True,
            panels={
                "subtitles": {
                    "font_size": "28", "outline": "2", "margin": "24", "safe_area": "8",
                    "wrap_chars": "0", "max_lines": "0", "offset_ms": "0",
                    "text_rgb": "FFFFFF", "outline_rgb": "000000", "force_bold": False,
                },
                "watermark": {"enabled": False},
                "encoding": {
                    "mode": "Simple", "output_ext": ".mp4", "codec": "Match source",
                    "quality": "Preserve visual quality", "policy": "Balanced", "speed": "Balanced",
                    "resolution": "Original", "fps": "Original", "audio": "Copy all audio",
                    "encoder": "Auto", "chapter": True,
                },
            },
        )]
    def all_presets(self):
        return self.builtin_presets() + list(getattr(self, "user_presets", []))
    def load_user_presets(self):
        if not PRESETS_FILE.is_file():
            return []
        try:
            raw = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or int(raw.get("schema", 1)) != 1:
                raise ValueError("Unsupported preset store schema")
            rows = raw.get("presets") or []
            if not isinstance(rows, list):
                raise ValueError("Preset store is malformed")
            out = []
            seen = set()
            for item in rows:
                preset = Preset.from_dict(item, builtin=False)
                if preset.id in seen:
                    preset.id = uuid.uuid4().hex
                seen.add(preset.id)
                preset.builtin = False
                out.append(preset)
            return out
        except Exception as exc:
            try:
                bad = PRESETS_FILE.with_name(PRESETS_FILE.stem + f".invalid-{int(time.time())}" + PRESETS_FILE.suffix)
                shutil.copy2(PRESETS_FILE, bad)
            except Exception:
                pass
            return []
    def save_user_presets(self):
        PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": 1, "presets": [p.to_dict() for p in self.user_presets if not p.builtin]}
        tmp = PRESETS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, PRESETS_FILE)
    def preset_by_id(self, preset_id):
        for preset in self.all_presets():
            if preset.id == preset_id:
                return preset
        return None
    def selected_preset(self):
        tree = getattr(self, "preset_tree", None)
        if tree is None or not tree.winfo_exists():
            return None
        sel = tree.selection()
        return self.preset_by_id(sel[0]) if sel else None
    def refresh_preset_tree(self, select_id=None):
        tree = getattr(self, "preset_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        for iid in tree.get_children():
            tree.delete(iid)
        for preset in self.all_presets():
            scope = ", ".join(x.title() for x in preset.panels)
            kind = "Built-in" if preset.builtin else "User"
            tree.insert("", "end", iid=preset.id, values=(preset.name, scope, kind))
        if select_id and tree.exists(select_id):
            tree.selection_set(select_id); tree.focus(select_id); tree.see(select_id)
    def preset_scope_selection(self):
        panels = []
        if self.preset_scope_subtitles_var.get(): panels.append("subtitles")
        if self.preset_scope_watermark_var.get(): panels.append("watermark")
        if self.preset_scope_encoding_var.get(): panels.append("encoding")
        return panels
    def capture_preset_panels(self, panels=None):
        panels = list(panels or self.preset_scope_selection())
        if not panels:
            raise ValueError("Select at least one preset scope")
        snap = self.dashboard_control_snapshot()
        allowed = {
            "subtitles": {"primary_font", "fallback_fonts", "font_size", "outline", "margin", "safe_area", "platform_safe_zone", "wrap_chars", "max_lines", "offset_ms", "text_rgb", "outline_rgb", "force_bold", "italic", "underline", "strikeout", "text_opacity", "outline_opacity", "shadow_depth", "shadow_rgb", "shadow_opacity", "letter_spacing", "rotation_angle", "subtitle_alignment", "margin_left", "margin_right", "background_box", "background_rgb", "background_opacity", "background_padding", "caption_effect_id", "caption_effect_params"},
            "watermark": {"enabled", "timing", "type", "text", "same_font", "font", "image", "position", "size", "opacity", "margin", "outline", "image_width", "image_scale", "image_x", "image_y", "intervals"},
            "encoding": {"mode", "output_ext", "codec", "quality", "policy", "speed", "resolution", "fps", "audio", "encoder", "custom_bitrate", "target_size", "chapter"},
        }
        result = {}
        for panel in panels:
            source = snap.get(panel) or {}
            result[panel] = {key: json.loads(json.dumps(source[key], ensure_ascii=False)) for key in allowed[panel] if key in source}
        return result
    def validate_preset_panels(self, panels):
        if not isinstance(panels, dict) or not panels:
            raise ValueError("Preset has no settings")
        clean = {}
        if "subtitles" in panels:
            clean["subtitles"] = self.normalize_dashboard_subtitles(panels["subtitles"])
        if "watermark" in panels:
            wm = self.normalize_dashboard_watermark(panels["watermark"])
            # normalize_dashboard_watermark returns interval tuples for application, while persisted
            # preset JSON uses objects. Keep both representations accepted at the boundary.
            clean["watermark"] = wm
        if "encoding" in panels:
            clean["encoding"] = self.normalize_dashboard_encoding(panels["encoding"])
        unknown = set(panels) - {"subtitles", "watermark", "encoding"}
        if unknown:
            raise ValueError("Unknown preset panel: " + ", ".join(sorted(unknown)))
        return clean
    def apply_preset_object(self, preset):
        try:
            clean = self.validate_preset_panels(preset.panels)
            if "subtitles" in clean: self.apply_dashboard_subtitles(clean["subtitles"])
            if "watermark" in clean: self.apply_dashboard_watermark(clean["watermark"])
            if "encoding" in clean: self.apply_dashboard_encoding(clean["encoding"])
            self.publish_dashboard_controls()
            self.autosave_project()
            self.log_ui(f"Applied preset: {preset.name}")
            self.status_var.set(f"Preset applied: {preset.name}")
            return True
        except Exception as exc:
            self.error_ui(f"Could not apply preset '{preset.name}': {exc}")
            return False
    def apply_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.error_ui("Choose a preset first")
            return False
        return self.apply_preset_object(preset)
    def save_new_preset(self):
        try:
            name = self.preset_name_var.get().strip()
            if not name or len(name) > 120:
                raise ValueError("Enter a preset name (1-120 characters)")
            if any(p.name.casefold() == name.casefold() for p in self.all_presets()):
                raise ValueError("A preset with this name already exists")
            preset = Preset(id=uuid.uuid4().hex, name=name, panels=self.capture_preset_panels(), builtin=False)
            self.user_presets.append(preset)
            self.save_user_presets(); self.refresh_preset_tree(preset.id)
            self.log_ui(f"Saved preset: {name}")
            return True
        except Exception as exc:
            self.error_ui(f"Could not save preset: {exc}")
            return False
    def overwrite_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.error_ui("Choose a preset first"); return False
        if preset.builtin:
            self.error_ui("Built-in presets are read-only. Duplicate it first."); return False
        try:
            preset.panels = self.capture_preset_panels()
            self.save_user_presets(); self.refresh_preset_tree(preset.id)
            self.log_ui(f"Updated preset: {preset.name}")
            return True
        except Exception as exc:
            self.error_ui(f"Could not update preset: {exc}"); return False
    def duplicate_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.error_ui("Choose a preset first"); return False
        base = preset.name + " copy"; name = base; n = 2
        names = {p.name.casefold() for p in self.all_presets()}
        while name.casefold() in names:
            name = f"{base} {n}"; n += 1
        dup = Preset(id=uuid.uuid4().hex, name=name, panels=json.loads(json.dumps(preset.panels, ensure_ascii=False)), builtin=False)
        self.user_presets.append(dup); self.save_user_presets(); self.refresh_preset_tree(dup.id); self.preset_name_var.set(name)
        return True
    def rename_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.error_ui("Choose a preset first"); return False
        if preset.builtin:
            self.error_ui("Built-in presets are read-only. Duplicate it first."); return False
        name = self.preset_name_var.get().strip()
        if not name or len(name) > 120:
            self.error_ui("Enter a preset name (1-120 characters)"); return False
        if any(p.id != preset.id and p.name.casefold() == name.casefold() for p in self.all_presets()):
            self.error_ui("A preset with this name already exists"); return False
        preset.name = name; self.save_user_presets(); self.refresh_preset_tree(preset.id); return True
    def delete_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.error_ui("Choose a preset first"); return False
        if preset.builtin:
            self.error_ui("Built-in presets cannot be deleted"); return False
        self.user_presets = [p for p in self.user_presets if p.id != preset.id]
        self.save_user_presets(); self.refresh_preset_tree(); return True
    def export_selected_preset(self):
        preset = self.selected_preset()
        if not preset:
            self.error_ui("Choose a preset first"); return False
        path = filedialog.asksaveasfilename(title="Export SubBurn preset", defaultextension=".subburn-preset.json", initialfile=safe_filename(preset.name) + ".subburn-preset.json", filetypes=[("SubBurn preset", "*.subburn-preset.json"), ("JSON", "*.json")])
        if not path: return False
        data = preset.to_dict(); data["builtin"] = False
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    def import_preset(self):
        path = filedialog.askopenfilename(title="Import SubBurn preset", filetypes=[("SubBurn preset", "*.subburn-preset.json *.json"), ("All files", "*.*")])
        if not path: return False
        try:
            preset = Preset.from_dict(json.loads(Path(path).read_text(encoding="utf-8")), builtin=False)
            preset.builtin = False; preset.id = uuid.uuid4().hex
            base = preset.name; name = base; n = 2; names = {p.name.casefold() for p in self.all_presets()}
            while name.casefold() in names:
                name = f"{base} {n}"; n += 1
            preset.name = name
            self.user_presets.append(preset); self.save_user_presets(); self.refresh_preset_tree(preset.id); self.preset_name_var.set(name)
            return True
        except Exception as exc:
            self.error_ui(f"Could not import preset: {exc}"); return False
    def presets_ui(self):
        p = self.page_presets
        p.columnconfigure(0, weight=1)
        intro = ttk.LabelFrame(p, text="Reusable burn presets", padding=10)
        intro.grid(row=0, column=0, sticky="ew")
        ttk.Label(intro, text="Presets save only burn settings - never the current video, subtitle path, output folder, or metadata. Choose which sections the preset owns.", wraplength=950).grid(row=0, column=0, columnspan=4, sticky="w")
        scope = ttk.Frame(intro); scope.grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Label(scope, text="Save scope:").pack(side="left")
        ttk.Checkbutton(scope, text="Subtitles", variable=self.preset_scope_subtitles_var).pack(side="left", padx=(10,0))
        ttk.Checkbutton(scope, text="Watermark", variable=self.preset_scope_watermark_var).pack(side="left", padx=(10,0))
        ttk.Checkbutton(scope, text="Encoding", variable=self.preset_scope_encoding_var).pack(side="left", padx=(10,0))
        ttk.Label(intro, text="Name").grid(row=2, column=0, sticky="w", pady=(10,4))
        ttk.Entry(intro, textvariable=self.preset_name_var).grid(row=2, column=1, columnspan=3, sticky="ew", pady=(10,4))
        intro.columnconfigure(1, weight=1)
        listbox = ttk.LabelFrame(p, text="Presets", padding=10); listbox.grid(row=1, column=0, sticky="nsew", pady=(10,0)); listbox.columnconfigure(0, weight=1)
        self.preset_tree = ttk.Treeview(listbox, columns=("name","scope","kind"), show="headings", height=10)
        for col,title,width in (("name","Name",300),("scope","Scope",360),("kind","Type",100)):
            self.preset_tree.heading(col,text=title); self.preset_tree.column(col,width=width,anchor="w")
        self.preset_tree.grid(row=0,column=0,sticky="nsew")
        bar=ttk.Scrollbar(listbox,orient="vertical",command=self.preset_tree.yview);bar.grid(row=0,column=1,sticky="ns");self.preset_tree.configure(yscrollcommand=bar.set)
        def on_select(_event=None):
            preset=self.selected_preset()
            if preset:self.preset_name_var.set(preset.name)
        self.preset_tree.bind("<<TreeviewSelect>>",on_select)
        buttons=ttk.Frame(listbox);buttons.grid(row=1,column=0,columnspan=2,sticky="w",pady=(10,0))
        for text_,cmd in (("Apply",self.apply_selected_preset),("Save current as new",self.save_new_preset),("Overwrite selected",self.overwrite_selected_preset),("Duplicate",self.duplicate_selected_preset),("Rename",self.rename_selected_preset),("Delete",self.delete_selected_preset),("Export",self.export_selected_preset),("Import",self.import_preset)):
            ttk.Button(buttons,text=text_,command=cmd).pack(side="left",padx=(0,6),pady=2)
        self.refresh_preset_tree()

    def batch_selected_id(self):
        tree = getattr(self, "batch_tree", None)
        if tree is None or not tree.winfo_exists():
            return None
        sel = tree.selection()
        return sel[0] if sel else None
    def refresh_batch_tree(self, select_id=None):
        tree = getattr(self, "batch_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        previous = select_id or self.batch_selected_id()
        items = self.batch_store.list_items()
        snap = self.op_state.snapshot()
        current = getattr(self, "batch_current_id", None)
        current_pct = float(snap.get("progress_pct", 0.0) or 0.0)
        for iid in tree.get_children():
            tree.delete(iid)
        terminal_units = 0.0
        for item in items:
            if item.state in {"done", "failed", "cancelled"}:
                pct = 100.0; terminal_units += 1.0
            elif item.id == current and item.state == "running":
                pct = max(0.0, min(100.0, current_pct)); terminal_units += pct / 100.0
            else:
                pct = 0.0
            video = Path(item.job.video).name if item.job.video else "(no video)"
            subtitle = Path(item.job.subtitle_file).name if item.job.subtitle_file else item.job.subtitle_source
            state = item.state.title()
            if item.retry_count:
                state += f" (retry {item.retry_count})"
            tree.insert("", "end", iid=item.id, values=(item.position, video, subtitle, state, f"{pct:.0f}%", item.error or item.output_path))
        if previous and tree.exists(previous):
            tree.selection_set(previous); tree.focus(previous); tree.see(previous)
        total = len(items)
        global_pct = 100.0 * terminal_units / total if total else 0.0
        self.batch_progress_var.set(global_pct)
        queued = sum(1 for x in items if x.state == "queued")
        failed = sum(1 for x in items if x.state == "failed")
        done = sum(1 for x in items if x.state == "done")
        with self.batch_runner_lock:
            active = bool(self.batch_runner_active)
            paused = bool(self.batch_pause_requested)
        if current:
            status = f"Running queue item {current[:8]} - {done} done, {queued} queued, {failed} failed"
        elif active:
            status = f"Queue runner active - {done} done, {queued} queued, {failed} failed"
        elif paused and queued:
            status = f"Queue paused - {queued} queued, {failed} failed"
        elif queued:
            status = f"Queue ready - {queued} queued, {failed} failed"
        else:
            status = f"Queue idle - {done} done, {failed} failed"
        self.batch_status_var.set(status)
        batch_op_id = getattr(self, "batch_operation_id", None)
        if batch_op_id and self.op_state.state_of(batch_op_id) not in OperationState.TERMINAL_STATES:
            self.op_state.set_overall(batch_op_id, min(99.0, global_pct), status)
    def batch_add_job(self, job, *, allow_duplicate=False, source_label="job"):
        if not isinstance(job, BurnJob):
            job = BurnJob.from_dict(job.to_dict() if hasattr(job, "to_dict") else dict(job))
        if not job.video or not Path(job.video).is_file():
            raise ValueError("Choose an existing video before adding the queue job")
        if not allow_duplicate:
            duplicate = self.batch_store.find_equivalent_active(job)
            if duplicate:
                raise ValueError(f"This exact {source_label} is already queued or running. Use Duplicate on that row if you intentionally want another copy.")
        item = self.batch_store.add(job)
        self.refresh_batch_tree(item.id)
        self.log_ui(f"Batch queued: {Path(job.video).name}")
        return item
    def batch_add_current(self):
        try:
            self.batch_add_job(self.snapshot_job(), source_label="current project")
            return True
        except Exception as exc:
            self.error_ui(f"Could not add batch job: {exc}")
            return False
    def job_from_saved_state(self, state):
        if not isinstance(state, dict):
            raise ValueError("Saved project state is invalid")
        job = BurnJob.from_dict(self.snapshot_job().to_dict())
        project = dict(state.get("project") or {})
        subtitles = dict(state.get("subtitles") or {})
        watermark = dict(state.get("watermark") or {})
        encoding = dict(state.get("encoding") or {})
        field_map = {
            "ffmpeg":"ffmpeg", "video":"video", "subtitle_source":"subtitle_source", "subtitle_file":"subtitle_file", "embedded_track":"embedded_track", "output_dir":"output_dir", "output_name":"output_name", "clean_output":"clean_output",
        }
        for src,dst in field_map.items():
            if src in project: setattr(job,dst,project[src])
        if isinstance(project.get("metadata"), dict): job.metadata={str(k):str(v) for k,v in project["metadata"].items()}
        subtitle_map={"primary_font":"primary_font","font_size":"font_size","outline":"outline","margin":"margin","wrap_chars":"wrap_chars","max_lines":"max_lines","offset_ms":"subtitle_offset","text_rgb":"text_rgb","outline_rgb":"outline_rgb","force_bold":"force_bold","italic":"italic","underline":"underline","strikeout":"strikeout","text_opacity":"text_opacity","outline_opacity":"outline_opacity","shadow_depth":"shadow_depth","shadow_rgb":"shadow_rgb","shadow_opacity":"shadow_opacity","letter_spacing":"letter_spacing","rotation_angle":"rotation_angle","subtitle_alignment":"subtitle_alignment","margin_left":"margin_left","margin_right":"margin_right","background_box":"background_box","background_rgb":"background_rgb","background_opacity":"background_opacity","background_padding":"background_padding","caption_effect_id":"caption_effect_id","caption_effect_params":"caption_effect_params"}
        for src,dst in subtitle_map.items():
            if src in subtitles: setattr(job,dst,subtitles[src])
        if "fallback_fonts" in subtitles: job.fallback_labels=[str(x) for x in subtitles.get("fallback_fonts") or []]
        wm_map={"enabled":"watermark_enabled","timing":"watermark_timing","type":"watermark_type","text":"watermark_text","same_font":"same_wm_font","font":"wm_font","image":"watermark_image","position":"watermark_position","size":"watermark_size","margin":"watermark_margin","outline":"watermark_outline","image_width":"watermark_image_width","image_scale":"watermark_image_scale","image_x":"watermark_image_x","image_y":"watermark_image_y"}
        for src,dst in wm_map.items():
            if src in watermark: setattr(job,dst,watermark[src])
        if "opacity" in watermark:
            try: job.watermark_opacity=float(watermark["opacity"])/100.0
            except Exception: pass
        if "intervals" in watermark: job.watermark_rows=[(float(x.get("start",0)),float(x.get("end",0)),str(x.get("position","Top right"))) for x in watermark.get("intervals") or [] if isinstance(x,dict)]
        enc_map={"output_ext":"output_ext","codec":"codec","quality":"quality_mode","policy":"encoder_policy","speed":"speed_mode","resolution":"resolution","fps":"fps","audio":"audio_mode","encoder":"encoder","custom_bitrate":"custom_bitrate","target_size":"target_size","chapter":"chapter"}
        for src,dst in enc_map.items():
            if src in encoding: setattr(job,dst,encoding[src])
        return job
    def batch_add_recent_project(self, index):
        try:
            projects=self.recents.get("projects",[])
            if index < 0 or index >= len(projects): raise ValueError("Recent project no longer exists")
            job=self.job_from_saved_state(projects[index].get("state") or {})
            self.batch_add_job(job, source_label="recent project")
            return True
        except Exception as exc:
            self.error_ui(f"Could not add recent project: {exc}"); return False
    def batch_add_custom(self, video, subtitle=""):
        try:
            video=Path(str(video)); subtitle=str(subtitle or "").strip()
            if not video.is_file() or video.suffix.casefold() not in VIDEO_EXTS: raise ValueError("Choose an existing supported video file")
            job=BurnJob.from_dict(self.snapshot_job().to_dict());job.video=str(video);job.output_name=safe_filename(video.stem + " - SubBurn")
            if subtitle:
                sp=Path(subtitle)
                if not sp.is_file() or sp.suffix.casefold() not in SUBTITLE_FILE_EXTS: raise ValueError("Choose an existing supported subtitle file")
                job.subtitle_source="External";job.subtitle_file=str(sp);job.embedded_track=""
            else:
                job.subtitle_source="Auto";job.subtitle_file="";job.embedded_track=""
            self.batch_add_job(job, source_label="queue project")
            return True
        except Exception as exc:
            self.error_ui(f"Could not add queue project: {exc}"); return False
    def batch_add_another_video(self):
        video=filedialog.askopenfilename(title="Choose video to add to queue",filetypes=[("Video files"," ".join("*"+x for x in sorted(VIDEO_EXTS))),("All files","*.*")])
        if not video:return False
        subtitle=filedialog.askopenfilename(title="Optional external subtitle for this queue job (Cancel for Auto subtitle selection)",filetypes=[("Subtitle files"," ".join("*"+x for x in sorted(SUBTITLE_FILE_EXTS))),("All files","*.*")])
        return self.batch_add_custom(video,subtitle or "")
    def batch_add_recent_dialog(self):
        projects=self.recents.get("projects",[])
        if not projects:
            self.error_ui("No recent projects are available"); return False
        top=tk.Toplevel(self.root);top.title("Add recent project to queue");top.transient(self.root);top.grab_set();top.geometry("620x360")
        frame=ttk.Frame(top,padding=12);frame.pack(fill="both",expand=True);frame.rowconfigure(1,weight=1);frame.columnconfigure(0,weight=1)
        ttk.Label(frame,text="Choose a recent project to add without changing the currently open project.",wraplength=560).grid(row=0,column=0,sticky="w",pady=(0,8))
        box=tk.Listbox(frame,exportselection=False,bg=self.ui_colors['entry'],fg=self.ui_colors['text'],selectbackground=self.ui_colors['accent_soft'],selectforeground=self.ui_colors['selection_text']);box.grid(row=1,column=0,sticky="nsew")
        for item in projects: box.insert("end",item.get("label") or item.get("video") or "Recent project")
        actions=ttk.Frame(frame);actions.grid(row=2,column=0,sticky="e",pady=(10,0))
        def add_selected():
            sel=box.curselection()
            if not sel:return
            if self.batch_add_recent_project(int(sel[0])):top.destroy()
        ttk.Button(actions,text="Cancel",command=top.destroy).pack(side="right")
        ttk.Button(actions,text="Add to queue",style="Accent.TButton",command=add_selected).pack(side="right",padx=(0,8))
        return True

    def discover_batch_pairs(self, folder):
        folder = Path(folder)
        videos = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.casefold() in VIDEO_EXTS], key=lambda p:p.name.casefold())
        subs = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.casefold() in SUBTITLE_FILE_EXTS and not (p.suffix.casefold() == ".sub" and p.with_suffix(".idx").is_file()) and not (p.suffix.casefold() == ".idx" and not p.with_suffix(".sub").is_file())], key=lambda p:p.name.casefold())
        pairs = []; ambiguous = []; unmatched = []
        for video in videos:
            exact = [s for s in subs if s.stem.casefold() == video.stem.casefold()]
            if len(exact) == 1:
                pairs.append((video, exact[0])); continue
            tagged = [s for s in subs if s.stem.casefold().startswith(video.stem.casefold() + ".")]
            if len(tagged) == 1:
                pairs.append((video, tagged[0])); continue
            if len(exact) > 1 or len(tagged) > 1:
                ambiguous.append((video, exact or tagged))
            else:
                unmatched.append(video)
        return pairs, ambiguous, unmatched
    def batch_add_folder_pairs(self):
        folder = filedialog.askdirectory(title="Choose folder containing videos + matching subtitles")
        if not folder:
            return False
        try:
            pairs, ambiguous, unmatched = self.discover_batch_pairs(folder)
            if not pairs:
                raise ValueError("No unambiguous video/subtitle filename pairs were found")
            base = self.snapshot_job()
            added = []
            for video, sub in pairs:
                job = BurnJob.from_dict(base.to_dict())
                job.video = str(video); job.subtitle_source = "External"; job.subtitle_file = str(sub); job.embedded_track = ""
                job.output_name = safe_filename(video.stem + " - SubBurn")
                added.append(self.batch_store.add(job))
            self.refresh_batch_tree(added[-1].id if added else None)
            self.log_ui(f"Batch folder scan: queued {len(added)} pairs; skipped {len(ambiguous)} ambiguous and {len(unmatched)} unmatched videos")
            if ambiguous:
                self.warning_ui(f"Skipped {len(ambiguous)} videos with multiple possible subtitle files. Pair those manually to avoid burning the wrong subtitles.")
            return True
        except Exception as exc:
            self.error_ui(f"Could not add folder batch: {exc}")
            return False
    def batch_remove_id(self, item_id):
        item_id=str(item_id or "").strip(); item=self.batch_store.get(item_id) if item_id else None
        if not item:
            self.error_ui("Queue item no longer exists"); return False
        if item.state == "running":
            self._batch_delete_after_current = item_id
            self.cancel_encode()
            self.log_ui(f"Batch cancel-and-remove requested: {Path(item.job.video).name}")
            return True
        try:
            self.batch_store.delete(item_id); self.refresh_batch_tree(); self.log_ui(f"Batch removed: {Path(item.job.video).name}"); return True
        except Exception as exc:
            self.error_ui(f"Could not remove queue item: {exc}"); return False
    def batch_remove_ids(self, item_ids):
        ok=True
        for item_id in list(dict.fromkeys(str(x) for x in item_ids if str(x).strip())):
            if not self.batch_remove_id(item_id): ok=False
        self.refresh_batch_tree(); return ok
    def batch_remove_selected(self):
        tree=getattr(self,"batch_tree",None); ids=list(tree.selection()) if tree is not None and tree.winfo_exists() else []
        if not ids:
            self.error_ui("Choose one or more queue items first"); return False
        return self.batch_remove_ids(ids)
    def batch_duplicate_id(self, item_id):
        item = self.batch_store.duplicate(str(item_id or ""))
        if not item:
            self.error_ui("Queue item no longer exists"); return False
        self.refresh_batch_tree(item.id); self.log_ui(f"Batch duplicated: {Path(item.job.video).name}"); return True
    def batch_duplicate_selected(self):
        item_id = self.batch_selected_id()
        if not item_id:
            self.error_ui("Choose a queue item first"); return False
        return self.batch_duplicate_id(item_id)
    def batch_move_selected(self, delta):
        item_id = self.batch_selected_id()
        if not item_id:
            self.error_ui("Choose a queue item first"); return False
        try:
            moved = self.batch_store.move(item_id, delta); self.refresh_batch_tree(item_id); return moved
        except Exception as exc:
            self.error_ui(f"Could not reorder queue item: {exc}"); return False
    def batch_retry_selected(self):
        item_id = self.batch_selected_id()
        if not item_id:
            self.error_ui("Choose a failed/cancelled queue item first"); return False
        if not self.batch_store.retry(item_id):
            self.error_ui("Only failed or cancelled queue items can be retried"); return False
        self.refresh_batch_tree(item_id); return True
    def batch_retry_all_failed(self):
        count = self.batch_store.retry_all_failed(); self.refresh_batch_tree(); self.log_ui(f"Batch requeued {count} failed job(s)"); return count
    def batch_clear_completed(self):
        count = self.batch_store.clear_completed(); self.refresh_batch_tree(); self.log_ui(f"Batch cleared {count} completed job(s)"); return count
    def batch_clear_queued(self):
        count = self.batch_store.clear_queued(); self.refresh_batch_tree(); self.log_ui(f"Batch cleared {count} queued job(s)"); return count
    def batch_is_running(self):
        lock = getattr(self, "batch_runner_lock", None)
        if lock is None:
            return bool(getattr(self, "batch_runner_active", False))
        with lock:
            return bool(getattr(self, "batch_runner_active", False))
    def require_batch_idle(self, action):
        if self.batch_is_running():
            self.error_ui(f"{action} is unavailable while the batch queue is running. Pause the queue after the current job, then try again.")
            return False
        return True
    def batch_resolve_toolset(self, job, cache=None):
        cache = cache if cache is not None else {}
        raw = str(getattr(job, "ffmpeg", "") or "").strip()
        requested = Path(raw) if raw else None
        current = getattr(self, "toolset", None)
        if requested is not None and requested.is_file():
            try:
                key = str(requested.resolve()).casefold()
            except Exception:
                key = str(requested.absolute()).casefold()
            if current is not None:
                try:
                    current_key = str(Path(current.ffmpeg).resolve()).casefold()
                except Exception:
                    current_key = str(Path(current.ffmpeg).absolute()).casefold()
                if current_key == key:
                    return current
            if key not in cache:
                cache[key] = inspect_toolset(requested)
            return cache[key]
        if current is not None:
            return current
        best, _found = best_local_toolset(raw)
        if best is None:
            raise RuntimeError("No compatible FFmpeg/FFprobe toolset is available for this queued job")
        return best
    def batch_start_queue(self):
        if self.active_job_count() > 0:
            self.error_ui("Wait for the current Analyze/Preview/Encode/tool operation to finish before starting the batch queue")
            return False
        with self.batch_runner_lock:
            if self.batch_runner_active:
                self.batch_status_var.set("Queue is already running")
                return False
            if not self.batch_store.list_items({"queued"}):
                self.error_ui("No queued batch jobs to run")
                return False
            self.batch_pause_requested = False
            self.batch_continue_on_error = bool(self.batch_continue_on_error_var.get())
            self.batch_runner_active = True
        try:
            thread = self.start_operation_thread("batch", self.batch_runner_loop)
            self.batch_runner_thread = thread
            self.batch_operation_id = getattr(thread, "subburn_operation_id", None)
            self.refresh_batch_tree()
            return True
        except Exception:
            with self.batch_runner_lock:
                self.batch_runner_active = False
            raise
    def batch_pause_queue(self):
        with self.batch_runner_lock:
            self.batch_pause_requested = True
        self.batch_status_var.set("Queue will pause after the current job")
        return True
    def batch_cancel_current(self):
        if not getattr(self, "batch_current_id", None):
            self.error_ui("No batch job is currently encoding"); return False
        self.cancel_encode(); return True
    def batch_runner_loop(self):
        tool_cache = {}
        try:
            while True:
                with self.batch_runner_lock:
                    if self.batch_pause_requested:
                        break
                queued = self.batch_store.list_items({"queued"})
                if not queued:
                    break
                item = queued[0]
                self.batch_current_id = item.id
                self.batch_store.set_state(item.id, "running", error="", output_path="", started=True)
                self.emit("batch_refresh")
                self.log(f"Batch starting: {Path(item.job.video).name}")
                self.last_output = None
                original_media = getattr(self, "media", None)
                original_toolset = getattr(self, "toolset", None)
                original_help_cache = getattr(self, "help_cache", {})
                original_tuning_cache = getattr(self, "tuning_cache", {})
                self._job_local.job = item.job
                try:
                    video = Path(item.job.video)
                    if not video.is_file():
                        raise RuntimeError(f"Queued video no longer exists: {video}")
                    job_toolset = self.batch_resolve_toolset(item.job, tool_cache)
                    self.toolset = job_toolset
                    if original_toolset is None or ffmpeg_signature(job_toolset) != ffmpeg_signature(original_toolset):
                        self.help_cache = {}
                        self.tuning_cache = {}
                    parent_op_id = self.current_operation_id()
                    self.set_stage("Batch", 2, f"Analyzing {video.name}")
                    self.media = probe_media(job_toolset.ffprobe, video)
                    self.log(f"Batch media: {self.media.width}x{self.media.height} | {self.media.fps:.2f} fps | {fmt_time(self.media.duration)}")
                    child_op_id = self.begin_operation("encode", f"Batch burn: {video.name}", priority=100)
                    self._operation_local.operation_id = child_op_id
                    try:
                        outcome = self.encode_worker()
                        self._finish_operation_from_result(child_op_id, outcome)
                    except Exception as child_exc:
                        self.finish_operation(child_op_id, "failed", error=str(child_exc))
                        raise
                    finally:
                        self._operation_local.operation_id = parent_op_id
                except Exception as exc:
                    outcome = {"status":"failed", "output":"", "error":str(exc)}
                    self.emit("warning", f"Batch job failed: {exc}")
                finally:
                    self.media = original_media
                    self.toolset = original_toolset
                    self.help_cache = original_help_cache
                    self.tuning_cache = original_tuning_cache
                    try:
                        del self._job_local.job
                    except Exception:
                        pass
                outcome = outcome if isinstance(outcome, dict) else {"status":"failed","output":"","error":"Encode worker returned no outcome"}
                status = outcome.get("status")
                delete_after = str(getattr(self, "_batch_delete_after_current", "") or "") == str(item.id)
                if delete_after:
                    self._batch_delete_after_current = None
                    try:
                        self.batch_store.set_state(item.id, "cancelled", error="Removed by user", output_path="", finished=True)
                        self.batch_store.delete(item.id)
                    except Exception as exc:
                        self.log(f"Queue remove-after-cancel cleanup failed: {exc}")
                elif status == "done":
                    self.batch_store.set_state(item.id, "done", error="", output_path=outcome.get("output", ""), finished=True)
                elif status == "cancelled":
                    self.batch_store.set_state(item.id, "cancelled", error="Cancelled by user", output_path="", finished=True)
                else:
                    self.batch_store.set_state(item.id, "failed", error=outcome.get("error") or "Encode failed", output_path="", finished=True)
                    if not self.batch_continue_on_error:
                        with self.batch_runner_lock:
                            self.batch_pause_requested = True
                self.batch_current_id = None
                self.emit("batch_refresh")
                with self.batch_runner_lock:
                    if self.batch_pause_requested:
                        break
            with self.batch_runner_lock:
                paused = bool(self.batch_pause_requested and self.batch_store.list_items({"queued"}))
            return {"status": "paused" if paused else "done"}
        finally:
            self.batch_current_id = None
            with self.batch_runner_lock:
                self.batch_runner_active = False
            self.emit("batch_refresh")
    def batch_ui(self):
        p = self.page_batch; p.columnconfigure(0, weight=1)
        top = ttk.LabelFrame(p, text="Persistent burn queue", padding=10); top.grid(row=0,column=0,sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="Jobs are stored in SQLite and survive restarts. Interrupted running jobs are safely returned to Queued on the next launch. This build runs one encode at a time so global FFmpeg progress/cancellation state cannot cross-contaminate jobs.", wraplength=980).grid(row=0,column=0,columnspan=8,sticky="w")
        buttons=ttk.Frame(top);buttons.grid(row=1,column=0,columnspan=8,sticky="w",pady=(10,0))
        for label,cmd in (("Add current job",self.batch_add_current),("Add another video",self.batch_add_another_video),("Add recent project",self.batch_add_recent_dialog),("Add folder pairs",self.batch_add_folder_pairs),("Duplicate",self.batch_duplicate_selected),("Remove selected",self.batch_remove_selected),("Move up",lambda:self.batch_move_selected(-1)),("Move down",lambda:self.batch_move_selected(1)),("Retry selected",self.batch_retry_selected),("Retry all failed",self.batch_retry_all_failed),("Clear queued",self.batch_clear_queued),("Clear completed",self.batch_clear_completed)):
            ttk.Button(buttons,text=label,command=cmd).pack(side="left",padx=(0,6),pady=2)
        runbar=ttk.Frame(top);runbar.grid(row=2,column=0,columnspan=8,sticky="ew",pady=(10,0));runbar.columnconfigure(5,weight=1)
        ttk.Button(runbar,text="Start / Resume queue",command=self.batch_start_queue).grid(row=0,column=0,padx=(0,6))
        ttk.Button(runbar,text="Pause after current",command=self.batch_pause_queue).grid(row=0,column=1,padx=(0,6))
        ttk.Button(runbar,text="Cancel current",style="Danger.TButton",command=self.batch_cancel_current).grid(row=0,column=2,padx=(0,12))
        ttk.Checkbutton(runbar,text="Continue after failed job",variable=self.batch_continue_on_error_var).grid(row=0,column=3,sticky="w")
        ttk.Label(top,textvariable=self.batch_status_var).grid(row=3,column=0,columnspan=8,sticky="w",pady=(10,4))
        ttk.Progressbar(top,variable=self.batch_progress_var,maximum=100).grid(row=4,column=0,columnspan=8,sticky="ew")
        box=ttk.LabelFrame(p,text="Queue",padding=10);box.grid(row=1,column=0,sticky="nsew",pady=(10,0));box.columnconfigure(0,weight=1)
        self.batch_tree=ttk.Treeview(box,columns=("pos","video","subtitle","state","progress","detail"),show="headings",height=14,selectmode="extended")
        columns=(("pos","#",45),("video","Video",260),("subtitle","Subtitle",230),("state","State",130),("progress","Progress",80),("detail","Output / error",360))
        for key,title,width in columns:
            self.batch_tree.heading(key,text=title);self.batch_tree.column(key,width=width,anchor="w")
        self.batch_tree.grid(row=0,column=0,sticky="nsew")
        bar=ttk.Scrollbar(box,orient="vertical",command=self.batch_tree.yview);bar.grid(row=0,column=1,sticky="ns");self.batch_tree.configure(yscrollcommand=bar.set)
        self.refresh_batch_tree()

    def labeled_entry(self, parent, row, label, var, browse=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        ent = ttk.Entry(parent, textvariable=var)
        ent.grid(row=row, column=1, sticky="ew", pady=4)
        if browse:
            ttk.Button(parent, text="Browse", command=browse).grid(row=row, column=2, padx=(12, 0), pady=4)
        return ent























    def dashboard_ui(self):
        p = self.page_dashboard
        p.columnconfigure(0, weight=1)
        url = f"http://127.0.0.1:{self.dashboard_port}" if self.dashboard_port else "unavailable"
        link = ttk.LabelFrame(p, text="Browser & recovery", padding=10, style="Card.TLabelframe")
        link.grid(row=0, column=0, sticky="ew")
        link.columnconfigure(0, weight=1)
        self.dashboard_url_var = tk.StringVar(value=f"Browser dashboard: {url}")
        ttk.Label(link, textvariable=self.dashboard_url_var, wraplength=760).grid(row=0, column=0, sticky="w")
        actions = ttk.Frame(link)
        actions.grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Open in browser", command=self.open_dashboard_browser, state=("normal" if self.dashboard_port else "disabled")).pack(side="left")
        ttk.Button(actions, text="Copy link", command=lambda: self.copy_text(url), state=("normal" if self.dashboard_port else "disabled")).pack(side="left", padx=(12, 0))
        ttk.Button(actions, text="Browser-only mode", command=self.enter_browser_only, state=("normal" if self.dashboard_port else "disabled")).pack(side="left", padx=(12, 0))
        self.restore_recovery_btn = ttk.Button(actions, text="Restore last autosave", command=self.restore_recovery, state=("normal" if RECOVERY_FILE.is_file() else "disabled"))
        self.restore_recovery_btn.pack(side="left", padx=(12, 0))
    def live_preview_ui(self):
        p = self.page_live
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)
        controls = ttk.LabelFrame(p, text="Seekable rendered-frame preview", padding=10)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.columnconfigure(0, weight=1)
        self.live_seek_scale = ttk.Scale(controls, from_=0, to=1, variable=self.live_seek_var, command=self.update_live_seek_label)
        self.live_seek_scale.grid(row=0, column=0, sticky="ew")
        ttk.Label(controls, textvariable=self.live_seek_text_var, width=14).grid(row=0, column=1, padx=(12, 10))
        ttk.Button(controls, text="Render frame", command=self.live_frame_async).grid(row=0, column=2)
        ttk.Button(controls, text="Play 8s clip", command=self.live_clip_async).grid(row=0, column=3, padx=(12, 0))
        preview_actions = ttk.Frame(controls)
        preview_actions.grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))
        self.preview_btn = ttk.Button(preview_actions, text="Preview", command=self.preview_async)
        self.preview_btn.pack(side="left")
        ttk.Button(preview_actions, text="Compare quality", command=self.compare_preview_async).pack(side="left", padx=(12, 0))
        preview_help = ttk.Label(controls, text="Render frame is exact and interactive. Preview selected boundary moves this seek point to that boundary. In watermark Intervals mode, the Tk Play 8s clip button also snaps to the selected interval so the watermark is actually visible. The clip uses the same subtitle + watermark filter settings as final output; the browser dashboard plays the same clip inline.", style="Muted.TLabel", justify="left", wraplength=820)
        preview_help.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        controls.bind("<Configure>", lambda e, w=preview_help: w.configure(wraplength=max(320, e.width - 24)), add="+")
        frame = ttk.LabelFrame(p, text="Rendered frame", padding=10)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.live_image_label = ttk.Label(frame, text="Analyze a video, seek to a timestamp, then render a frame. Click the rendered frame to move an enabled watermark to the nearest 3x3 position.", anchor="center", cursor="crosshair")
        self.live_image_label.grid(row=0, column=0, sticky="nsew")
        self.live_image_label.bind("<ButtonRelease-1>", self.live_preview_position_click)
        self.live_photo = None
    def update_live_seek_label(self, value=None):
        try:
            seconds = float(self.live_seek_var.get() if value is None else value)
        except Exception:
            seconds = 0.0
        self.live_seek_text_var.set(fmt_time(max(0.0, seconds)))
    def live_timestamp_limit(self):
        if not self.media:
            return 0.0
        duration = max(0.0, float(self.media.duration or 0.0))
        frame_step = 1.0 / self.media.fps if self.media.fps else 0.04
        return max(0.0, duration - max(0.001, frame_step))
    def start_preview_request(self, target, job):
        lock = getattr(self, "_preview_request_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._preview_request_lock = lock
        with lock:
            if getattr(self, "_preview_request_active", False):
                self.emit("warning", "Another Preview/Live Preview operation is still preparing or rendering. Wait for it to finish, or press Cancel before starting a different preview.")
                return None
            self._preview_request_active = True
        def guarded():
            try:
                return target()
            finally:
                with lock:
                    self._preview_request_active = False
        operation_map = {
            "live_frame_worker": "live_frame",
            "live_clip_worker": "live_clip",
            "preview_worker": "preview",
            "compare_preview_worker": "quality_compare",
        }
        try:
            return self.run_job(guarded, job=job, operation_type=operation_map.get(getattr(target, "__name__", ""), "preview"))
        except Exception:
            with lock:
                self._preview_request_active = False
            raise
    def live_frame_async(self, timestamp=None):
        if not self.require_batch_idle("Live frame preview"):
            return None
        if not self.media:
            self.error_ui("Analyze media before rendering a live preview frame")
            return None
        try:
            value = float(self.live_seek_var.get() if timestamp is None else timestamp)
        except Exception:
            self.error_ui("Choose a valid live preview timestamp")
            return None
        value = max(0.0, min(value, self.live_timestamp_limit()))
        self.live_seek_var.set(value)
        self.update_live_seek_label(value)
        self.live_frame_generation += 1
        job = self.snapshot_job()
        job.live_timestamp = value
        job.live_generation = self.live_frame_generation
        return self.start_preview_request(self.live_frame_worker, job)
    def apply_live_frame(self, path, timestamp, generation):
        path = Path(path)
        if generation != self.live_frame_generation:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return
        if not path.is_file() or path.stat().st_size <= 0:
            return
        old = None
        with self.live_frame_lock:
            old = self.latest_live_frame
            self.latest_live_frame = path
            self.latest_live_timestamp = float(timestamp)
            self.live_frame_revision += 1
        if old and Path(old) != path:
            try:
                oldp = Path(old)
                if oldp.parent == PREVIEW_DIR and oldp.name.startswith("SubBurn-live-"):
                    oldp.unlink(missing_ok=True)
            except Exception:
                pass
        try:
            photo = tk.PhotoImage(file=str(path))
            factor = max(1, math.ceil(photo.width() / 900), math.ceil(photo.height() / 520))
            if factor > 1:
                photo = photo.subsample(factor, factor)
            self.live_photo = photo
            self.live_image_label.configure(image=photo, text="")
        except Exception as e:
            self.live_image_label.configure(image="", text=f"Frame rendered at {fmt_time(timestamp)}: {path}\nImage display failed: {e}")
        self.live_seek_var.set(float(timestamp))
        self.update_live_seek_label(timestamp)
        self.status_var.set(f"Live preview frame ready at {fmt_time(timestamp)}")
        self.log_ui(f"Live preview frame ready: {path}")
    def live_clip_async(self, timestamp=None, open_when_ready=True):
        if not self.require_batch_idle("Live playback preview"):
            return None
        if not self.media:
            self.error_ui("Analyze media before rendering a live preview clip")
            return None
        job = self.snapshot_job()
        if timestamp is None and job.watermark_enabled and job.watermark_timing == "Intervals" and getattr(job, "watermark_rows", []):
            self.sync_live_seek_to_boundary(job)
        try:
            value = float(self.live_seek_var.get() if timestamp is None else timestamp)
        except Exception:
            self.error_ui("Choose a valid live preview timestamp")
            return None
        value = max(0.0, min(value, self.live_timestamp_limit()))
        if timestamp is None and value <= 0.001 and not (job.watermark_enabled and job.watermark_timing == "Intervals" and getattr(job, "watermark_rows", [])):
            smart_start, _ = self.preview_range_for_job(job)
            if smart_start > 0.001:
                value = max(0.0, min(float(smart_start), self.live_timestamp_limit()))
                self.live_seek_var.set(value)
                self.update_live_seek_label(value)
                self.log_ui(f"Live playback moved to {fmt_time(value)} so the preview includes an actual subtitle cue")
        duration = min(8.0, max(0.0, float(self.media.duration or 0.0) - value))
        if duration < 0.1:
            self.error_ui("Not enough video remains at this timestamp for playback preview")
            return None
        self.live_clip_generation += 1
        job.live_clip_timestamp = value
        job.live_clip_duration = duration
        job.live_clip_generation = self.live_clip_generation
        job.live_clip_open = bool(open_when_ready)
        return self.start_preview_request(self.live_clip_worker, job)
    def live_proxy_filter(self, filt):
        ops = []
        if self.media and self.media.height > 540:
            ops.append("scale=-2:540:flags=fast_bilinear")
        ops.append("fps=15")
        tail = ",".join(ops)
        out = dict(filt)
        if filt["mode"] == "complex":
            graph = filt["filter"]
            if not graph.endswith("[vout]"):
                raise RuntimeError("Unexpected preview filter graph output")
            out["filter"] = graph[:-6] + "[vfull];[vfull]" + tail + "[vout]"
        else:
            out["filter"] = filt["filter"] + "," + tail
        return out
    def apply_live_clip(self, path, timestamp, duration, generation, open_when_ready):
        path = Path(path)
        if generation != self.live_clip_generation:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return
        if not path.is_file() or path.stat().st_size <= 0:
            return
        with self.live_clip_lock:
            old = self.latest_live_clip
            self.latest_live_clip = path
            self.latest_live_clip_timestamp = float(timestamp)
            self.latest_live_clip_duration = float(duration)
            self.live_clip_revision += 1
        if old and Path(old) != path:
            try:
                oldp = Path(old)
                if oldp.parent == PREVIEW_DIR and oldp.name.startswith("SubBurn-live-clip-"):
                    oldp.unlink(missing_ok=True)
            except Exception:
                pass
        self.status_var.set(f"Live playback clip ready at {fmt_time(timestamp)}")
        self.log_ui(f"Live playback clip ready: {path}")
        if open_when_ready:
            open_path(path)
    def dashboard_live_clip_revision(self):
        with self.live_clip_lock:
            return self.live_clip_revision
    def dashboard_live_clip_info(self, expected_timestamp=None, after_revision=None):
        with self.live_clip_lock:
            path = self.latest_live_clip
            timestamp = self.latest_live_clip_timestamp
            duration = self.latest_live_clip_duration
            revision = self.live_clip_revision
        try:
            if after_revision is not None and revision <= int(after_revision):
                return None
            if expected_timestamp is not None and (timestamp is None or abs(float(timestamp) - float(expected_timestamp)) > 0.001):
                return None
        except Exception:
            return None
        if path and Path(path).is_file():
            return {"path": Path(path), "timestamp": timestamp, "duration": duration, "revision": revision}
        return None
    def queue_dashboard_live_clip(self, timestamp):
        if isinstance(timestamp, bool):
            return False, "Choose a valid live preview timestamp"
        try:
            timestamp = float(timestamp)
        except Exception:
            return False, "Choose a valid live preview timestamp"
        if not math.isfinite(timestamp) or timestamp < 0:
            return False, "Choose a valid live preview timestamp"
        self.events.put(("dashboard_live_clip", (timestamp,)))
        return True, f"Playback preview {fmt_time(timestamp)} queued"
    def apply_dashboard_live_clip(self, timestamp):
        if not self.media:
            self.error_ui("Analyze media before rendering a live preview clip")
            return
        if timestamp > self.live_timestamp_limit() + 0.001:
            self.error_ui("Live preview timestamp is outside the renderable video range")
            return
        self.log_ui(f"Dashboard requested playback preview at {fmt_time(timestamp)}")
        self.live_clip_async(timestamp, open_when_ready=False)
    def apply_live_watermark_position(self, position, timestamp=None, rerender=True):
        if position not in POSITIONS:
            self.error_ui("Invalid watermark preview position")
            return False
        if not self.watermark_enabled_var.get():
            self.error_ui("Enable the watermark before positioning it from Live Preview")
            return False
        try:
            timestamp = float(self.live_seek_var.get() if timestamp is None else timestamp)
        except Exception:
            self.error_ui("Choose a valid live preview timestamp")
            return False
        if self.watermark_timing_var.get() == "Intervals":
            matches = [i for i, (a, b, _pos) in enumerate(self.watermark_rows) if a <= timestamp <= b]
            if not matches:
                self.error_ui("The live preview timestamp is not inside a watermark interval")
                return False
            idx = matches[0]
            a, b, _old = self.watermark_rows[idx]
            self.watermark_rows[idx] = (a, b, position)
            tree = getattr(self, "interval_tree", None)
            if tree is not None and tree.winfo_exists():
                self.refresh_intervals()
            self.log_ui(f"Live Preview moved watermark interval {idx + 1} to {position}")
        else:
            self.watermark_position_var.set(position)
            self.log_ui(f"Live Preview moved watermark to {position}")
        self.autosave_project()
        self.publish_dashboard_controls()
        if rerender:
            self.live_frame_async(timestamp)
        return True
    def live_preview_position_click(self, event):
        photo = getattr(self, "live_photo", None)
        if photo is None:
            return
        try:
            pw, ph = photo.width(), photo.height()
            lw, lh = self.live_image_label.winfo_width(), self.live_image_label.winfo_height()
            left, top = max(0.0, (lw - pw) / 2), max(0.0, (lh - ph) / 2)
            if event.x < left or event.x >= left + pw or event.y < top or event.y >= top + ph:
                return
            x = (event.x - left) / max(1, pw)
            y = (event.y - top) / max(1, ph)
            self.apply_live_watermark_position(grid_position_from_fraction(x, y))
        except Exception as e:
            self.error_ui(f"Live Preview positioning failed: {e}")
    def queue_dashboard_live_position(self, x, y, timestamp):
        try:
            x, y, timestamp = float(x), float(y), float(timestamp)
        except Exception:
            return False, "Choose a valid preview position and timestamp"
        if not all(math.isfinite(v) for v in (x, y, timestamp)) or not (0 <= x <= 1 and 0 <= y <= 1) or timestamp < 0:
            return False, "Choose a valid preview position and timestamp"
        watermark = (self.op_state.control_snapshot().get("watermark") or {}) if hasattr(self, "op_state") else {}
        if watermark and not watermark.get("enabled"):
            return False, "Enable the watermark before positioning it"
        if watermark.get("timing") == "Intervals":
            rows = watermark.get("intervals") or []
            if not any(float(row.get("start", -1)) <= timestamp <= float(row.get("end", -1)) for row in rows):
                return False, "The preview timestamp is not inside a watermark interval"
        position = grid_position_from_fraction(x, y)
        self.events.put(("dashboard_live_position", (position, timestamp)))
        return True, f"Watermark position {position} queued"
    def apply_dashboard_live_position(self, position, timestamp):
        self.log_ui(f"Dashboard requested live watermark position {position} at {fmt_time(timestamp)}")
        self.apply_live_watermark_position(position, timestamp)
    def dashboard_live_frame_revision(self):
        with self.live_frame_lock:
            return self.live_frame_revision
    def dashboard_live_frame_path(self, expected_timestamp=None, after_revision=None):
        with self.live_frame_lock:
            path = self.latest_live_frame
            timestamp = self.latest_live_timestamp
            revision = self.live_frame_revision
        if after_revision is not None:
            try:
                if revision <= int(after_revision):
                    return None
            except Exception:
                return None
        if expected_timestamp is not None:
            try:
                if timestamp is None or abs(float(timestamp) - float(expected_timestamp)) > 0.001:
                    return None
            except Exception:
                return None
        if path and Path(path).is_file():
            return Path(path)
        return None
    def open_dashboard_browser(self):
        if self.dashboard_port:
            open_path(f"http://127.0.0.1:{self.dashboard_port}")
    def enter_browser_only(self, open_browser=True):
        if not self.dashboard_port:
            self.error_ui("Browser dashboard is unavailable")
            return
        if open_browser:
            self.open_dashboard_browser()
        self.browser_only = True
        self.close_when_idle = False
        self.log_ui(f"Browser-only mode active: http://127.0.0.1:{self.dashboard_port}")
        self.root.withdraw()
    def show_desktop_window(self):
        self.browser_only = False
        self.close_when_idle = False
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            return
        self.log_ui("Desktop window restored")
    def request_exit(self):
        self.browser_only = False
        self.close()
    def _set_progressbar_state(self, widget, mode_attr, mode, value_var, value):
        if widget is None or not widget.winfo_exists():
            return
        desired = "indeterminate" if str(mode) == "indeterminate" else "determinate"
        current = getattr(self, mode_attr, None)
        if current != desired:
            try:
                widget.stop()
            except Exception:
                pass
            widget.configure(mode=desired)
            setattr(self, mode_attr, desired)
            if desired == "indeterminate":
                widget.start(80)
        if desired == "determinate":
            value_var.set(max(0.0, min(100.0, float(value or 0.0))))

    def refresh_transcription_progress_ui(self):
        op_id = getattr(self, "transcription_operation_id", None)
        snap = self.op_state.operation_snapshot(op_id) if op_id else None
        if not snap:
            return
        self._set_progressbar_state(getattr(self, "transcription_progress_bar", None), "_transcription_progress_mode", snap.get("mode"), self.transcription_progress_var, snap.get("progress_pct", snap.get("overall_pct", 0.0)))

    def _set_status_metric_visible(self, widget, visible):
        if widget is None:
            return
        try:
            if visible:
                widget.grid()
            else:
                widget.grid_remove()
        except Exception:
            pass

    def tick_dashboard(self):
        try:
            self.publish_dashboard_controls()
            snap = self.op_state.snapshot()
            transfer = snap.get("metric_profile") == "transfer"
            progress_mode = "determinate" if transfer and int(snap.get("bytes_total", 0) or 0) > 0 else snap.get("progress_mode")
            self._set_progressbar_state(getattr(self, "global_progress_bar", None), "_global_progress_mode", progress_mode, self.progress_var, snap.get("progress_pct", snap.get("overall_pct", 0.0)))
            if hasattr(self, "progress_status_var"):
                numeric_known = progress_mode == "determinate"
                if numeric_known:
                    self.progress_status_var.set(("Download: " if transfer else "Progress: ") + f"{float(snap.get('transfer_pct' if transfer else 'progress_pct', 0.0) or 0.0):.1f}%")
                else:
                    self.progress_status_var.set(("Download: " if transfer else "Progress: ") + "-")
            self.fps_status_var.set(f"FPS: {snap.get('fps', '-')}")
            self.speed_status_var.set(("Transfer speed: " if transfer else "Speed: ") + str(snap.get('speed', '-')))
            self.transfer_status_var.set(f"Downloaded: {snap.get('downloaded', '-')}")
            self.eta_var.set(("Remaining: " if transfer else "ETA: ") + str(snap.get('eta', '-')))
            self._set_status_metric_visible(getattr(self, "fps_status_label", None), not transfer and snap.get("fps", "-") != "-")
            self._set_status_metric_visible(getattr(self, "transfer_status_label", None), transfer)
            self._set_status_metric_visible(getattr(self, "speed_status_label", None), transfer or snap.get("speed", "-") != "-")
            self._set_status_metric_visible(getattr(self, "eta_status_label", None), transfer or snap.get("eta", "-") != "-")
            self.refresh_transcription_progress_ui()
            # Legacy dashboard-specific widgets were removed in WIP05. Keep this guarded during
            # migration so older tests/recovery code cannot make the periodic status refresh fail.
            if hasattr(self, "dash_stage_var"):
                self.dash_stage_var.set(snap.get("display_stage") or snap["stage"])
            if hasattr(self, "dash_message_var"):
                self.dash_message_var.set(snap.get("display_stage_message") or snap["stage_message"])
            if hasattr(self, "dash_pct_var"):
                self.dash_pct_var.set(float(snap.get("progress_pct", snap.get("overall_pct", 0.0)) or 0.0))
            if hasattr(self, "dash_elapsed_var"):
                self.dash_elapsed_var.set(f"Elapsed {snap['elapsed']:.0f}s")
            if hasattr(self, "dash_fps_var"):
                self.dash_fps_var.set(f"FPS {snap['fps']}")
            if hasattr(self, "dash_speed_var"):
                self.dash_speed_var.set(f"Speed {snap['speed']}")
            if hasattr(self, "dash_eta_var"):
                self.dash_eta_var.set(f"ETA {snap['eta']}")
            if hasattr(self, "dash_history_list"):
                self.dash_history_list.delete(0, "end")
                for h in snap.get("display_history", snap["history"]):
                    self.dash_history_list.insert("end", f"{h['ts']}  {h['name']}: {h['message']}")
        except Exception:
            pass
        self.root.after(500, self.tick_dashboard)
    def set_stage(self, name, pct, message):
        value = max(0, min(100, float(pct)))
        op_id = self.current_operation_id()
        if op_id:
            self.op_state.stage(op_id, name, value, str(message))
        self.emit("stage", name, value, str(message))
    def apply_stage(self, name, pct, message):
        snap = self.op_state.snapshot()
        self.status_var.set(f"{snap.get('display_stage') or name}: {snap.get('display_stage_message') or message}")
        self.progress_var.set(float(snap.get("progress_pct", snap.get("overall_pct", 0.0)) or 0.0))
    def open_help_manual(self):
        top=tk.Toplevel(self.root);top.title("SubBurn Help Manual");top.geometry("920x720");top.minsize(680,480);top.transient(self.root)
        frame=ttk.Frame(top,padding=12);frame.pack(fill="both",expand=True);frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        text=tk.Text(frame,wrap="word",bg=self.ui_colors['entry'],fg=self.ui_colors['text'],insertbackground=self.ui_colors['text'],selectbackground=self.ui_colors['accent_soft'],selectforeground=self.ui_colors['selection_text'],relief="flat",borderwidth=1,padx=14,pady=12)
        scroll=ttk.Scrollbar(frame,orient="vertical",command=text.yview);text.configure(yscrollcommand=scroll.set);text.grid(row=0,column=0,sticky="nsew");scroll.grid(row=0,column=1,sticky="ns")
        text.insert("1.0",HELP_MANUAL_TEXT);text.configure(state="disabled")
        bar=ttk.Frame(frame);bar.grid(row=1,column=0,columnspan=2,sticky="e",pady=(10,0));ttk.Button(bar,text="Contact Owner on Telegram",command=lambda:open_path(OWNER_TELEGRAM_URL)).pack(side="left",padx=(0,8));ttk.Button(bar,text="Close",command=top.destroy).pack(side="left")

    def runtime_settings_ui(self):
        p = self.page_runtime
        p.columnconfigure(0, weight=1)
        appearance = ttk.LabelFrame(p, text="Appearance", padding=12, style="Card.TLabelframe")
        appearance.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        appearance.columnconfigure(1, weight=1)
        ttk.Label(appearance, text="Theme").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.appearance_combo = ttk.Combobox(appearance, textvariable=self.appearance_var, values=APPEARANCE_MODES, state="readonly", width=18)
        self.appearance_combo.grid(row=0, column=1, sticky="w")
        self.appearance_combo.bind("<<ComboboxSelected>>", self.apply_appearance_from_settings)
        ttk.Label(appearance, text="Dark, Balanced, and Light share the same liquid-glass hierarchy; choose the contrast level you prefer.", style="Muted.TLabel", wraplength=760).grid(row=1, column=0, columnspan=3, sticky="w", pady=(7, 0))
        tools = ttk.LabelFrame(p, text="Runtime & FFmpeg", padding=10, style="Card.TLabelframe")
        tools.grid(row=1, column=0, sticky="ew")
        tools.columnconfigure(1, weight=1)
        self.labeled_entry(tools, 0, "FFmpeg file / folder", self.ffmpeg_var, self.browse_ffmpeg)
        ttk.Button(tools, text="Choose folder", command=self.browse_ffmpeg_folder).grid(row=0, column=3, padx=(12, 0))
        ttk.Button(tools, text="Auto-detect", command=self.discover_tools_async).grid(row=0, column=4, padx=(12, 0))
        ttk.Button(tools, text="Check / install FFmpeg", command=self.download_ffmpeg_async).grid(row=0, column=5, padx=(12, 0))
        ttk.Label(tools, text="Order: PATH/system first → selected file/folder → verified SubBurn runtime. On Windows, a required managed runtime is placed first in your user PATH for reuse without overwriting package-manager/project binaries.", style="Muted.TLabel", wraplength=900).grid(row=1, column=0, columnspan=6, sticky="w", pady=(7, 0))
        ttk.Label(tools, textvariable=self.tool_var, wraplength=900).grid(row=2, column=0, columnspan=6, sticky="w", pady=(5, 0))
        ttk.Label(tools, textvariable=self.dnd_var, wraplength=900).grid(row=3, column=0, columnspan=6, sticky="w", pady=(3, 0))
        help_box=ttk.LabelFrame(p,text="Owner & Help",padding=12,style="Card.TLabelframe");help_box.grid(row=2,column=0,sticky="ew",pady=(12,0));help_box.columnconfigure(0,weight=1)
        ttk.Label(help_box,text=f"Made by: {OWNER_NAME}").grid(row=0,column=0,sticky="w")
        contact=ttk.Label(help_box,text=f"Contact Owner: {OWNER_TELEGRAM} on Telegram",cursor="hand2");contact.grid(row=1,column=0,sticky="w",pady=(4,0));contact.bind("<Button-1>",lambda _e:open_path(OWNER_TELEGRAM_URL))
        ttk.Button(help_box,text="Open Help Manual",command=self.open_help_manual).grid(row=0,column=1,rowspan=2,sticky="e",padx=(16,0))

    def project_ui(self):
        p = self.page_project
        p.columnconfigure(0, weight=1)
        inp = ttk.LabelFrame(p, text="Input", padding=10)
        inp.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        inp.columnconfigure(1, weight=1)
        video_ent = self.labeled_entry(inp, 0, "Video", self.video_var, self.browse_video)
        sub_ent = self.labeled_entry(inp, 2, "External subtitles", self.subtitle_file_var, self.browse_subtitle)
        ttk.Label(inp, textvariable=self.media_var).grid(row=1, column=1, sticky="w")
        ttk.Label(inp, text="Subtitle source").grid(row=3, column=0, sticky="w", pady=4)
        src = ttk.Frame(inp)
        src.grid(row=3, column=1, sticky="w")
        for text in ("Auto", "External", "Embedded"):
            ttk.Radiobutton(src, text=text, variable=self.subtitle_source_var, value=text).pack(side="left", padx=(0, 12))
        ttk.Label(inp, text="Embedded track").grid(row=4, column=0, sticky="w", pady=4)
        self.embedded_combo = ttk.Combobox(inp, textvariable=self.embedded_track_var, state="readonly")
        self.embedded_combo.grid(row=4, column=1, sticky="ew", pady=4)
        self.drop.bind(video_ent, self.drop_video)
        self.drop.bind(sub_ent, self.drop_subtitle)
        out = ttk.LabelFrame(p, text="Output", padding=10)
        out.grid(row=1, column=0, sticky="ew")
        out.columnconfigure(1, weight=1)
        self.labeled_entry(out, 0, "Folder", self.output_dir_var, self.browse_output_dir)
        ttk.Label(out, text="Filename").grid(row=1, column=0, sticky="w", pady=4)
        row = ttk.Frame(out)
        row.grid(row=1, column=1, columnspan=2, sticky="ew")
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.output_name_var).grid(row=0, column=0, sticky="ew")
        ttk.Combobox(row, textvariable=self.output_ext_var, values=OUTPUT_EXTS, state="readonly", width=8).grid(row=0, column=1, padx=(12, 0))
        ttk.Checkbutton(out, text="Use a clean output folder", variable=self.clean_output_var).grid(row=2, column=1, sticky="w")
        self.metadata_toggle_btn = ttk.Button(out, text="Show optional metadata", command=self.toggle_metadata_fields)
        self.metadata_toggle_btn.grid(row=3, column=1, sticky="w", pady=(6, 0))
        meta = ttk.LabelFrame(p, text="Output metadata (optional)", padding=10)
        meta.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        meta.columnconfigure(1, weight=1)
        self.metadata_frame = meta
        self.metadata_visible = False
        for i, (key, label) in enumerate((("title", "Title"), ("artist", "Artist"), ("album", "Album"), ("genre", "Genre"), ("date", "Date"), ("description", "Description"), ("copyright", "Copyright"))):
            ttk.Label(meta, text=label).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Entry(meta, textvariable=self.metadata_vars[key]).grid(row=i, column=1, sticky="ew", pady=2)
        meta.grid_remove()
        recent = ttk.LabelFrame(p, text="Recent projects and folders", padding=10)
        recent.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        recent.columnconfigure(0, weight=1)
        recent.columnconfigure(1, weight=1)
        ttk.Label(recent, text="Projects").grid(row=0, column=0, sticky="w")
        ttk.Label(recent, text="Folders").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.recent_projects_list = tk.Listbox(recent, height=5, exportselection=False, bg=self.ui_colors['entry'], fg=self.ui_colors['text'], selectbackground=self.ui_colors['accent_soft'], selectforeground=self.ui_colors['selection_text'], highlightbackground=self.ui_colors['border_soft'], highlightcolor=self.ui_colors['accent'], relief='flat', borderwidth=1)
        self.recent_projects_list.grid(row=1, column=0, sticky="ew")
        self.recent_folders_list = tk.Listbox(recent, height=5, exportselection=False, bg=self.ui_colors['entry'], fg=self.ui_colors['text'], selectbackground=self.ui_colors['accent_soft'], selectforeground=self.ui_colors['selection_text'], highlightbackground=self.ui_colors['border_soft'], highlightcolor=self.ui_colors['accent'], relief='flat', borderwidth=1)
        self.recent_folders_list.grid(row=1, column=1, sticky="ew", padx=(10, 0))
        project_actions = ttk.Frame(recent)
        project_actions.grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Button(project_actions, text="Restore selected project", command=self.restore_selected_recent_project).pack(side="left")
        ttk.Button(project_actions, text="Clear projects", command=self.clear_recent_projects).pack(side="left", padx=(10, 0))
        folder_actions = ttk.Frame(recent)
        folder_actions.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(6, 0))
        ttk.Button(folder_actions, text="Use selected as output folder", command=self.use_selected_recent_folder).pack(side="left")
        ttk.Button(folder_actions, text="Clear folders", command=self.clear_recent_folders).pack(side="left", padx=(10, 0))
        self.refresh_recents_ui()
    def toggle_metadata_fields(self):
        self.metadata_visible = not bool(getattr(self, "metadata_visible", False))
        if self.metadata_visible:
            self.metadata_frame.grid()
            self.metadata_toggle_btn.configure(text="Hide optional metadata")
        else:
            self.metadata_frame.grid_remove()
            self.metadata_toggle_btn.configure(text="Show optional metadata")
        return self.metadata_visible
    def transcription_ui(self):
        p = self.page_transcription
        p.columnconfigure(0, weight=1)
        intro = ttk.LabelFrame(p, text="Free local automatic transcription", padding=10)
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        intro.columnconfigure(1, weight=1)
        ttk.Label(intro, text="Creates an SRT locally and feeds it straight into SubBurn. No paid API, account, subscription, or token billing. Auto multilingual can follow language changes throughout the same video.", wraplength=980).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(intro, text="Model").grid(row=1, column=0, sticky="w", pady=(10, 4))
        model_combo = ttk.Combobox(intro, textvariable=self.transcription_model_var, values=TRANSCRIPTION_MODELS, state="readonly")
        model_combo.grid(row=1, column=1, sticky="ew", pady=(10, 4))
        ttk.Button(intro, text="Refresh size", command=lambda: self.refresh_transcription_model_metadata_async(True)).grid(row=1, column=2, padx=(12, 0), pady=(10, 4))
        ttk.Label(intro, textvariable=self.transcription_model_info_var, style="Muted.TLabel", wraplength=900, justify="left").grid(row=2, column=1, columnspan=2, sticky="w")
        ttk.Label(intro, text="Language mode").grid(row=3, column=0, sticky="w", pady=(10, 4))
        mode_combo = ttk.Combobox(intro, textvariable=self.transcription_language_mode_var, values=TRANSCRIPTION_LANGUAGE_MODES, state="readonly")
        mode_combo.grid(row=3, column=1, sticky="ew", pady=(10, 4))
        self.transcription_language_picker_label = ttk.Label(intro, text="Choose language")
        self.transcription_language_picker_label.grid(row=4, column=0, sticky="w", pady=4)
        self.transcription_language_picker = ttk.Combobox(intro, textvariable=self.transcription_language_picker_var, values=WHISPER_LANGUAGE_DISPLAY_OPTIONS, state="readonly", width=34)
        self.transcription_language_picker.grid(row=4, column=1, sticky="ew", pady=4)
        self.transcription_language_picker.bind("<<ComboboxSelected>>", lambda _e: self.apply_transcription_language_picker())
        self.transcription_language_label = ttk.Label(intro, text="Selected language codes")
        self.transcription_language_label.grid(row=5, column=0, sticky="w", pady=4)
        self.transcription_language_entry = ttk.Entry(intro, textvariable=self.transcription_language_code_var, width=34)
        self.transcription_language_entry.grid(row=5, column=1, sticky="ew", pady=4)
        self.transcription_language_help = ttk.Label(intro, text="Choose by language name above. Advanced users may also edit the canonical Whisper codes directly. Allowed mode accepts multiple languages.", style="Muted.TLabel", wraplength=850)
        self.transcription_language_help.grid(row=6, column=1, columnspan=2, sticky="w")
        ttk.Label(intro, text="Device").grid(row=7, column=0, sticky="w", pady=(10, 4))
        ttk.Combobox(intro, textvariable=self.transcription_device_var, values=TRANSCRIPTION_DEVICES, state="readonly").grid(row=7, column=1, sticky="w", pady=(10, 4))
        ttk.Label(intro, text="Auto tries CUDA when CTranslate2 can see a CUDA device, otherwise CPU. Auto falls back to CPU if CUDA initialization fails.", style="Muted.TLabel", wraplength=820).grid(row=8, column=1, columnspan=2, sticky="w")
        buttons = ttk.Frame(intro)
        buttons.grid(row=9, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="Prepare model", command=self.prepare_transcription_model_async).pack(side="left")
        ttk.Button(buttons, text="Transcribe current video", command=self.start_transcription_async).pack(side="left", padx=(12, 0))
        ttk.Button(buttons, text="Cancel transcription", style="Danger.TButton", command=self.cancel_transcription).pack(side="left", padx=(12, 0))
        mode_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_transcription_language_state())
        model_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_transcription_model_metadata_async(False))
        status = ttk.LabelFrame(p, text="Transcription status", padding=10)
        status.grid(row=1, column=0, sticky="ew")
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.transcription_status_var).grid(row=0, column=0, sticky="w")
        self.transcription_progress_bar = ttk.Progressbar(status, variable=self.transcription_progress_var, maximum=100, mode="determinate")
        self.transcription_progress_bar.grid(row=1, column=0, sticky="ew", pady=(6, 6))
        self._transcription_progress_mode = "determinate"
        ttk.Label(status, textvariable=self.transcription_result_var, wraplength=980).grid(row=2, column=0, sticky="w")
        ttk.Label(status, text="Word timestamps are preserved in a JSON sidecar for word-timed captions. The generated SRT uses the same universal subtitle renderer as any imported SRT.", style="Muted.TLabel", wraplength=980).grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.refresh_transcription_language_state()
        try:
            self.transcription_model_info_var.set(format_transcription_model_metadata(
                transcription_model_metadata(self.transcription_model_var.get(), online=False)
            ))
        except Exception:
            self.transcription_model_info_var.set("Model size information unavailable")

    def apply_transcription_language_picker(self):
        code = whisper_language_code_from_display(self.transcription_language_picker_var.get())
        if not code:
            return
        mode = str(self.transcription_language_mode_var.get())
        if mode == "Fixed language code":
            self.transcription_language_code_var.set(code)
        elif mode == "Allowed languages (detect changes)":
            current = []
            try:
                current = list(parse_allowed_language_codes(self.transcription_language_code_var.get()))
            except ValueError:
                current = []
            if code not in current:
                current.append(code)
            self.transcription_language_code_var.set(", ".join(current))
        self.transcription_language_picker_var.set(WHISPER_LANGUAGE_PICKER_PROMPT)

    def refresh_transcription_language_state(self):
        entry = getattr(self, "transcription_language_entry", None)
        picker = getattr(self, "transcription_language_picker", None)
        if entry is None:
            return
        mode = str(self.transcription_language_mode_var.get())
        enabled = mode != "Auto multilingual (detect changes)"
        try:
            entry.configure(state="normal" if enabled else "disabled")
            if picker is not None:
                picker.configure(state="readonly" if enabled else "disabled")
                if not enabled:
                    self.transcription_language_picker_var.set(WHISPER_LANGUAGE_PICKER_PROMPT)
            label = getattr(self, "transcription_language_label", None)
            if label is not None:
                label.configure(text="Allowed language codes" if mode == "Allowed languages (detect changes)" else "Selected language code")
        except Exception:
            pass

    def refresh_transcription_model_metadata_async(self, refresh=False):
        model = str(self.transcription_model_var.get()).strip()
        if model not in TRANSCRIPTION_MODELS:
            return None
        # Immediately show cached/offline-safe data, then refresh current repo metadata off-thread.
        try:
            meta = transcription_model_metadata(model, refresh=False, timeout=0.01, online=False)
            self.transcription_model_info_var.set(format_transcription_model_metadata(meta))
        except Exception:
            pass
        def worker():
            try:
                meta = transcription_model_metadata(model, refresh=bool(refresh), timeout=8.0)
                self.emit("transcription_model_metadata", model, meta)
            except Exception as exc:
                self.log(f"Transcription model metadata refresh failed for {model}: {exc}")
        # Metadata lookup is advisory network I/O, not a render/inference operation.  Do not
        # count it as an active job or block Analyze/Preview/Transcribe while it refreshes.
        thread = threading.Thread(target=worker, daemon=True, name="SubBurn-model-metadata")
        thread.start()
        return thread

    def capture_transcription_request(self, allow_model_download=False):
        video = str(self.video_var.get()).strip()
        if not video or not Path(video).is_file():
            raise ValueError("Select a valid video first")
        model = str(self.transcription_model_var.get()).strip()
        if model not in TRANSCRIPTION_MODELS:
            raise ValueError("Choose a supported local transcription model")
        mode = str(self.transcription_language_mode_var.get()).strip()
        if mode not in TRANSCRIPTION_LANGUAGE_MODES:
            raise ValueError("Choose a valid transcription language mode")
        code = str(self.transcription_language_code_var.get()).strip().lower()
        allowed = ()
        if mode == "Fixed language code":
            parsed = parse_allowed_language_codes(code)
            if len(parsed) != 1:
                raise ValueError("Fixed language mode requires exactly one language code such as ar, he, en, nl, or fr")
            code = parsed[0]
        elif mode == "Allowed languages (detect changes)":
            allowed = parse_allowed_language_codes(code)
            if len(allowed) < 2:
                raise ValueError("Allowed languages mode requires at least two language codes, for example: ar, he")
        device = str(self.transcription_device_var.get()).strip()
        if device not in TRANSCRIPTION_DEVICES:
            raise ValueError("Choose Auto, CUDA, or CPU")
        return TranscriptionRequest(video=video, model=model, language_mode=mode, language_code=code, allowed_languages=tuple(allowed), device=device, allow_model_download=bool(allow_model_download))
    def transcription_device_plan(self, request, ct2):
        requested = request.device
        cuda_count = 0
        try:
            cuda_count = int(ct2.get_cuda_device_count())
        except Exception:
            cuda_count = 0
        if requested == "CUDA":
            if cuda_count <= 0:
                raise RuntimeError("CUDA was selected, but CTranslate2 cannot see a CUDA device. Choose Auto or CPU, or repair the NVIDIA CUDA runtime.")
            return "cuda", "float16"
        if requested == "CPU":
            return "cpu", "float32"
        return ("cuda", "float16") if cuda_count > 0 else ("cpu", "float32")
    def load_transcription_model(self, request, allow_install=True, allow_download=False, download_progress=None, cancel_event=None, phase=None):
        WhisperModel, BatchedInferencePipeline, ct2 = ensure_faster_whisper_runtime(allow_install=allow_install)
        TRANSCRIPTION_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        if not transcription_model_ready(request.model):
            if not allow_download:
                raise RuntimeError(f"Model '{request.model}' is not prepared at SubBurn's pinned revision. Use Prepare model first.")
            prepare_transcription_model_snapshot(request.model, progress=download_progress, cancel_event=cancel_event, phase=phase)
        if not transcription_model_ready(request.model):
            raise RuntimeError(f"Model '{request.model}' did not pass SubBurn's provenance/readiness verification")
        model_path = transcription_model_install_dir(request.model)
        device, compute_type = self.transcription_device_plan(request, ct2)
        # Always load the already-pinned local directory.  WhisperModel never gets a model alias
        # or repository ID here, so it cannot silently resolve/download a newer upstream main.
        kwargs = {"device": device, "compute_type": compute_type, "local_files_only": True}
        try:
            model = WhisperModel(str(model_path), **kwargs)
        except Exception as first_exc:
            if request.device == "Auto" and device == "cuda":
                self.log(f"Transcription CUDA initialization failed; falling back to CPU: {first_exc}")
                device, compute_type = "cpu", "float32"
                kwargs.update(device=device, compute_type=compute_type)
                model = WhisperModel(str(model_path), **kwargs)
            else:
                raise
        return model, BatchedInferencePipeline, device, compute_type
    def decode_transcription_audio(self, video, model):
        audio_mod = importlib.import_module("faster_whisper.audio")
        sampling_rate = int(getattr(getattr(model, "feature_extractor", None), "sampling_rate", 16000) or 16000)
        audio = audio_mod.decode_audio(video, sampling_rate=sampling_rate)
        return audio, sampling_rate

    def transcription_vad_chunks(self, audio):
        vad_mod = importlib.import_module("faster_whisper.vad")
        return list(vad_mod.get_speech_timestamps(audio))

    def transcribe_allowed_language_set(self, request, model):
        """Constrain per-context language choices to request.allowed_languages.

        faster-whisper has no native language whitelist. We therefore VAD the source, merge
        tiny speech spans into useful context windows, rank languages for each context, choose
        the best permitted language, and transcribe that window with the language forced.
        Detection retries are strictly bounded.
        """
        allowed = tuple(request.allowed_languages or ())
        if len(allowed) < 2:
            raise RuntimeError("Allowed languages transcription requires at least two language codes")
        audio, sampling_rate = self.decode_transcription_audio(request.video, model)
        try:
            total_duration = float(len(audio)) / float(sampling_rate)
        except Exception:
            total_duration = float(self.media.duration if self.media else 0.0)
        speech_chunks = self.transcription_vad_chunks(audio)
        windows = merge_vad_speech_windows(speech_chunks, sampling_rate, total_duration)
        if not windows:
            raise RuntimeError("Voice activity detection found no speech to transcribe")
        results = []
        detection_records = []
        for wi, (start, end) in enumerate(windows):
            if self.transcription_cancel_event.is_set():
                return [], detection_records, total_duration, True
            a = max(0, int(round(start * sampling_rate)))
            b = min(len(audio), max(a + 1, int(round(end * sampling_rate))))
            chunk_audio = audio[a:b]
            detected = None
            confidence = 0.0
            ranked = ()
            attempts = 0
            context_start, context_end = start, end
            while attempts <= TRANSCRIPTION_ALLOWED_RETRIES:
                if attempts > 0:
                    expansion = TRANSCRIPTION_ALLOWED_WINDOW_TARGET / 2.0
                    context_start = max(0.0, start - expansion)
                    context_end = min(total_duration, end + expansion) if total_duration > 0 else end + expansion
                    ca = max(0, int(round(context_start * sampling_rate)))
                    cb = min(len(audio), max(ca + 1, int(round(context_end * sampling_rate))))
                    detection_audio = audio[ca:cb]
                else:
                    detection_audio = chunk_audio
                try:
                    _raw_lang, _raw_prob, all_probs = model.detect_language(
                        audio=detection_audio, vad_filter=False, language_detection_segments=1,
                        language_detection_threshold=0.0,
                    )
                except TypeError:
                    _raw_lang, _raw_prob, all_probs = model.detect_language(audio=detection_audio, vad_filter=False, language_detection_segments=1)
                detected, confidence, ranked = choose_allowed_language(all_probs, allowed)
                if detected is not None and confidence >= TRANSCRIPTION_ALLOWED_LOW_CONFIDENCE:
                    break
                attempts += 1
            if detected is None:
                raise RuntimeError(f"Could not rank any of the allowed languages ({', '.join(allowed)}) for speech around {start:.1f}s")
            uncertain = confidence < TRANSCRIPTION_ALLOWED_LOW_CONFIDENCE
            detection_records.append({
                "start": start, "end": end, "language": detected, "probability": confidence,
                "uncertain": bool(uncertain), "attempts": min(attempts + 1, TRANSCRIPTION_ALLOWED_RETRIES + 1),
                "alternatives": [{"language": c, "probability": p} for c, p in ranked[:10]],
            })
            self.log(f"Allowed-language context {start:.2f}-{end:.2f}s -> {detected} ({confidence:.3f})" + (" [low confidence]" if uncertain else ""))
            segs, _info = model.transcribe(
                chunk_audio, language=detected, task="transcribe", multilingual=False,
                word_timestamps=True, vad_filter=False, chunk_length=min(30, max(5, int(math.ceil(end - start)))),
                condition_on_previous_text=False, log_progress=False,
            )
            for seg in segs:
                seg_start = start + float(getattr(seg, "start", 0.0) or 0.0)
                seg_end = start + float(getattr(seg, "end", 0.0) or 0.0)
                shifted_words = []
                for word in list(getattr(seg, "words", None) or []):
                    ws = start + float(getattr(word, "start", 0.0) or 0.0)
                    we = start + float(getattr(word, "end", getattr(word, "start", 0.0)) or 0.0)
                    shifted_words.append(SimpleNamespace(
                        start=ws, end=max(ws, we), word=str(getattr(word, "word", "") or ""),
                        probability=float(getattr(word, "probability", 0.0) or 0.0),
                    ))
                results.append(SimpleNamespace(
                    start=seg_start, end=max(seg_start + 0.001, seg_end), text=str(getattr(seg, "text", "") or ""),
                    words=shifted_words, avg_logprob=float(getattr(seg, "avg_logprob", 0.0) or 0.0),
                    language=detected, language_probability=confidence, language_uncertain=bool(uncertain),
                ))
            if total_duration > 0:
                self.emit("transcription_progress", min(98.0, end / total_duration * 100.0))
        results.sort(key=lambda seg: (float(seg.start), float(seg.end)))
        return results, detection_records, total_duration, False

    def _transcription_model_phase_callback(self, model_name):
        def report(message):
            text = str(message or "").strip()
            if not text:
                return
            lower = text.casefold()
            if lower.startswith("downloading"):
                self.set_stage("Model download", 0, text)
            elif lower.startswith("validating"):
                self.set_stage("Model install", 0, text)
            elif lower.startswith("installing"):
                self.set_stage("Model install", 0, text)
            elif "installed and ready" in lower:
                self.set_stage("Model install", 0, text)
            self.emit("transcription_status", text)
            self.emit("log", f"Transcription model {model_name}: {text}")
        return report

    def prepare_transcription_model_async(self):
        if not self.require_batch_idle("Transcription model preparation"):
            return None
        if self.active_job_count() > 0:
            self.error_ui("Wait for the current operation to finish before preparing a transcription model")
            return None
        try:
            request = self.capture_transcription_request(allow_model_download=True)
        except Exception as exc:
            self.error_ui(str(exc)); return None
        self.transcription_cancel_event.clear()
        def worker():
            try:
                was_ready = transcription_model_ready(request.model)
                if was_ready:
                    self.emit("transcription_status", f"Model {request.model} is already installed; no download is needed.")
                else:
                    self.emit("transcription_status", transcription_model_download_message(request.model))
                model, _pipeline, device, compute = self.load_transcription_model(
                    request, allow_install=True, allow_download=True,
                    download_progress=self._transfer_progress_callback(f"{request.model} transcription model"),
                    cancel_event=self.transcription_cancel_event,
                    phase=self._transcription_model_phase_callback(request.model),
                )
                del model
                self.emit("transcription_model_ready", f"Model {request.model} ready locally ({device}/{compute})")
                return {"status": "succeeded"}
            except TranscriptionModelPreparationCancelled:
                self.emit("transcription_status", "Transcription model download cancelled; incomplete staging was discarded")
                return {"status": "cancelled"}
            except Exception as exc:
                self.emit("error", f"Transcription model preparation failed: {exc}")
                self.emit("transcription_status", "Transcription model preparation failed")
                return {"status": "failed", "error": str(exc)}
        self.transcription_thread = self.start_operation_thread("transcription_model_prepare", worker)
        self.transcription_operation_id = getattr(self.transcription_thread, "subburn_operation_id", None)
        self.refresh_transcription_progress_ui()
        return self.transcription_thread
    def start_transcription_async(self):
        if not self.require_batch_idle("Automatic transcription"):
            return None
        if self.active_job_count() > 0:
            self.error_ui("Wait for the current operation to finish before starting transcription")
            return None
        try:
            request = self.capture_transcription_request(allow_model_download=False)
        except Exception as exc:
            self.error_ui(str(exc)); return None
        allow_download = False
        if not transcription_model_ready(request.model):
            meta = transcription_model_metadata(request.model, refresh=False, timeout=0.01, online=False)
            size_text = format_transcription_model_metadata(meta)
            prepare_now = bool(messagebox.askyesno(
                "Prepare transcription model?",
                f"The local model '{request.model}' is not installed yet.\n\n{size_text}\n\nPrepare it now? It is downloaded once and then reused locally.",
                parent=self.root,
            ))
            if not prepare_now:
                self.transcription_status_var.set("Transcription cancelled before model preparation")
                return None
            self.transcription_status_var.set("Preparing the model first. Start Transcribe again when it reports ready.")
            return self.prepare_transcription_model_async()
        self.transcription_cancel_event.clear()
        self.transcription_progress_var.set(0.0)
        self.transcription_status_var.set("Starting local transcription")
        self.transcription_thread = self.start_operation_thread("transcription", lambda: self.transcription_worker(request))
        self.transcription_operation_id = getattr(self.transcription_thread, "subburn_operation_id", None)
        self.refresh_transcription_progress_ui()
        return self.transcription_thread
    def cancel_transcription(self):
        thread = getattr(self, "transcription_thread", None)
        if not thread or not thread.is_alive():
            self.transcription_status_var.set("No transcription is currently running")
            return False
        self.transcription_cancel_event.set()
        op_id = getattr(self, "transcription_operation_id", None)
        op = self.op_state.operation_snapshot(op_id) if op_id else None
        if isinstance(op, dict) and op.get("kind") == "transcription_model_prepare":
            self.transcription_status_var.set("Cancel requested - stopping the model download and discarding incomplete staging")
        else:
            self.transcription_status_var.set("Cancel requested - stopping after the current inference batch")
        return True
    def transcription_worker(self, request):
        try:
            self.emit("transcription_status", f"Loading {request.model} locally")
            model, Pipeline, device, compute = self.load_transcription_model(request, allow_install=True, allow_download=request.allow_model_download)
            if self.transcription_cancel_event.is_set():
                self.emit("transcription_status", "Transcription cancelled")
                return {"status":"cancelled"}
            self.emit("transcription_status", f"Transcribing on {device}/{compute} - {request.language_mode}")
            auto_multi = request.language_mode == "Auto multilingual (detect changes)"
            allowed_multi = request.language_mode == "Allowed languages (detect changes)"
            detection_records = []
            if allowed_multi:
                segments, detection_records, detected_duration, was_cancelled = self.transcribe_allowed_language_set(request, model)
                if was_cancelled:
                    self.emit("transcription_status", "Transcription cancelled")
                    return {"status":"cancelled"}
                info = SimpleNamespace(
                    duration=detected_duration, language=None, language_probability=0.0, all_language_probs=None
                )
            else:
                pipeline = Pipeline(model=model)
                language = None if auto_multi else request.language_code
                segments, info = pipeline.transcribe(
                    request.video,
                    language=language,
                    task="transcribe",
                    multilingual=auto_multi,
                    word_timestamps=True,
                    vad_filter=True,
                    batch_size=4,
                    chunk_length=15 if auto_multi else 30,
                    condition_on_previous_text=False,
                    log_progress=False,
                )
            TRANSCRIPTION_DIR.mkdir(parents=True, exist_ok=True)
            source = Path(request.video)
            srt_path = unique_path(TRANSCRIPTION_DIR / f"{safe_filename(source.stem)}.SubBurn.transcribed.srt")
            words_path = srt_path.with_suffix(".words.json")
            cues = []
            segments_json = []
            combined_text = []
            duration = float(getattr(info, "duration", 0.0) or (self.media.duration if self.media else 0.0) or 0.0)
            last_end = 0.0
            for seg in segments:
                if self.transcription_cancel_event.is_set():
                    self.emit("transcription_status", "Transcription cancelled")
                    return {"status":"cancelled"}
                text = str(getattr(seg, "text", "") or "").strip()
                if not text:
                    continue
                start = max(0.0, float(getattr(seg, "start", last_end) or 0.0))
                end = max(start + 0.001, float(getattr(seg, "end", start + 0.001) or start + 0.001))
                last_end = end
                body = [line.strip() for line in text.splitlines() if line.strip()] or [text]
                cues.append((start, end, body))
                combined_text.append(text)
                words = []
                for word in list(getattr(seg, "words", None) or []):
                    ws = max(start, float(getattr(word, "start", start) or start))
                    we = max(ws, float(getattr(word, "end", ws) or ws))
                    words.append({"start": ws, "end": we, "text": str(getattr(word, "word", "") or ""), "probability": float(getattr(word, "probability", 0.0) or 0.0)})
                segments_json.append({
                    "start": start, "end": end, "text": text, "words": words,
                    "language": getattr(seg, "language", None),
                    "language_probability": float(getattr(seg, "language_probability", 0.0) or 0.0),
                    "language_uncertain": bool(getattr(seg, "language_uncertain", False)),
                    "avg_logprob": float(getattr(seg, "avg_logprob", 0.0) or 0.0),
                })
                if duration > 0:
                    self.emit("transcription_progress", min(99.0, end / duration * 100.0))
            if not cues:
                raise RuntimeError("The transcription engine did not produce any speech segments")
            write_srt_cues(cues, srt_path)
            scripts = detected_unicode_scripts(" ".join(combined_text))
            payload = {
                "schema": 2, "engine": "faster-whisper", "model": request.model,
                "mode": request.language_mode,
                "fixed_language": request.language_code if request.language_mode == "Fixed language code" else None,
                "allowed_languages": list(request.allowed_languages or ()),
                "initial_language": getattr(info, "language", None),
                "initial_language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
                "language_windows": detection_records,
                "device": device, "compute_type": compute, "source": str(source),
                "detected_scripts": scripts, "segments": segments_json,
            }
            tmp = words_path.with_suffix(words_path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, words_path)
            summary = f"{len(cues)} cues" + (f" | scripts: {', '.join(scripts)}" if scripts else "")
            self.emit("transcription_progress", 100)
            self.emit("transcription_done", str(srt_path), str(words_path), summary)
            return {"status":"done", "srt":str(srt_path), "words":str(words_path)}
        except Exception as exc:
            self.emit("error", f"Automatic transcription failed: {exc}")
            self.emit("transcription_status", "Automatic transcription failed")
            return {"status":"failed", "error":str(exc)}
    def apply_transcription_done(self, srt_path, words_path, summary):
        self.latest_transcription_srt = Path(srt_path)
        self.latest_transcription_words = Path(words_path)
        self.subtitle_source_var.set("External")
        self.subtitle_file_var.set(str(srt_path))
        self.transcription_status_var.set("Transcription complete - generated SRT selected for burning")
        self.transcription_result_var.set(f"{summary} | {srt_path}")
        self.log_ui(f"Local transcription ready: {srt_path} ({summary})")
        self.autosave_project()
        self.publish_dashboard_controls()
    def design_ui(self):
        p = self.page_design
        p.columnconfigure(0, weight=1)
        fonts = ttk.LabelFrame(p, text="Fonts", padding=10)
        fonts.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        fonts.columnconfigure(1, weight=1)
        ttk.Label(fonts, text="Subtitle font").grid(row=0, column=0, sticky="w", pady=4)
        self.primary_font_combo = ttk.Combobox(fonts, textvariable=self.primary_font_var, state="readonly")
        self.primary_font_combo.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(fonts, text="Add font", command=self.add_font).grid(row=0, column=2, padx=(12, 0))
        ttk.Button(fonts, text="Refresh", command=self.scan_fonts_async).grid(row=0, column=3, padx=(12, 0))
        ttk.Label(fonts, text="Fallback font").grid(row=1, column=0, sticky="w", pady=4)
        self.fallback_combo = ttk.Combobox(fonts, textvariable=self.fallback_font_var, state="readonly")
        self.fallback_combo.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(fonts, text="Add fallback", command=self.add_fallback).grid(row=1, column=2, padx=(12, 0))
        ttk.Button(fonts, text="Remove fallback", command=self.remove_fallback).grid(row=1, column=3, padx=(12, 0))
        self.fallback_list = tk.Listbox(fonts, height=4, exportselection=False, bg=self.ui_colors['entry'], fg=self.ui_colors['text'], selectbackground=self.ui_colors['accent_soft'], selectforeground=self.ui_colors['selection_text'], highlightbackground=self.ui_colors['border_soft'], highlightcolor=self.ui_colors['accent'], relief='flat', borderwidth=1)
        self.fallback_list.grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)
        stylebox = ttk.LabelFrame(p, text="Subtitle style", padding=10)
        stylebox.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(stylebox, text="Text styling/animated-caption controls apply to text subtitles. PGS/VobSub/DVB bitmap subtitles preserve their original rendered graphics, timing and placement.", style="Muted.TLabel", wraplength=900).grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))
        for i, (label, var) in enumerate([("Font size", self.font_size_var), ("Outline", self.outline_var), ("Bottom margin", self.margin_var), ("Safe area", self.safe_area_var), ("Wrap chars", self.wrap_chars_var), ("Max lines", self.max_lines_var), ("Offset ms", self.subtitle_offset_var), ("Text RGB", self.text_rgb_var), ("Outline RGB", self.outline_rgb_var)]):
            ttk.Label(stylebox, text=label).grid(row=(i // 3) * 2, column=i % 3, sticky="w", padx=(0, 16), pady=(4, 0))
            ttk.Entry(stylebox, textvariable=var, width=16).grid(row=(i // 3) * 2 + 1, column=i % 3, sticky="w", padx=(0, 16), pady=(0, 4))
        ttk.Checkbutton(stylebox, text="Synthetic bold", variable=self.force_bold_var).grid(row=6, column=0, sticky="w")
        advanced_style = ttk.LabelFrame(p, text="Rich ASS styling (same renderer in Preview and Final Encode)", padding=10)
        advanced_style.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        checks = ttk.Frame(advanced_style)
        checks.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))
        ttk.Checkbutton(checks, text="Italic", variable=self.italic_var).pack(side="left")
        ttk.Checkbutton(checks, text="Underline", variable=self.underline_var).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(checks, text="Strikeout", variable=self.strikeout_var).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(checks, text="Background box", variable=self.background_box_var).pack(side="left", padx=(18, 0))
        rich_fields = [
            ("Text opacity %", self.text_opacity_var), ("Outline opacity %", self.outline_opacity_var), ("Shadow px", self.shadow_depth_var),
            ("Shadow RGB", self.shadow_rgb_var), ("Shadow opacity %", self.shadow_opacity_var), ("Letter spacing", self.letter_spacing_var),
            ("Rotation °", self.rotation_angle_var), ("Left margin", self.margin_left_var), ("Right margin", self.margin_right_var),
            ("Background RGB", self.background_rgb_var), ("Background opacity %", self.background_opacity_var), ("Box padding", self.background_padding_var),
        ]
        for i, (label, var) in enumerate(rich_fields):
            row = 1 + (i // 4) * 2; col = i % 4
            ttk.Label(advanced_style, text=label).grid(row=row, column=col, sticky="w", padx=(0, 14), pady=(2, 0))
            ttk.Entry(advanced_style, textvariable=var, width=15).grid(row=row + 1, column=col, sticky="w", padx=(0, 14), pady=(0, 4))
        ttk.Label(advanced_style, text="Alignment").grid(row=7, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(advanced_style, textvariable=self.subtitle_alignment_var, values=SUBTITLE_ALIGNMENT_NAMES, state="readonly", width=18).grid(row=8, column=0, sticky="w")
        ttk.Label(advanced_style, text="Background box uses standard ASS opaque-box mode; when enabled it replaces normal outline/shadow rather than drawing text with a second renderer.", style="Muted.TLabel", wraplength=900).grid(row=9, column=0, columnspan=5, sticky="w", pady=(8, 0))
        animated = ttk.LabelFrame(p, text="Social / animated captions (burned through the same ASS/libass renderer)", padding=10)
        animated.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        animated.columnconfigure(1, weight=1)
        ttk.Label(animated, text="Effect").grid(row=0, column=0, sticky="w")
        ttk.Combobox(animated, textvariable=self.caption_effect_var, values=CAPTION_EFFECT_LABELS, state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 12))
        ttk.Label(animated, text="Highlight RGB").grid(row=0, column=2, sticky="w")
        ttk.Entry(animated, textvariable=self.caption_active_rgb_var, width=12).grid(row=0, column=3, sticky="w", padx=(12, 0))
        ttk.Checkbutton(animated, text="Estimate word timing when no exact transcription timing sidecar exists", variable=self.caption_estimated_timing_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(7, 0))
        ttk.Label(animated, text="When a SubBurn transcription .words.json sidecar is available, its word timestamps are used. Otherwise optional cue-local timing is estimated and logged as approximate. Effects never reorder RTL text; libass/FriBidi keeps logical Arabic/Hebrew shaping/order.", style="Muted.TLabel", wraplength=940).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        safezones = ttk.LabelFrame(p, text="Platform safe-zone guides (preview only - never burned)", padding=10)
        safezones.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        safezones.columnconfigure(1, weight=1)
        ttk.Label(safezones, text="Guide preset").grid(row=0, column=0, sticky="w")
        ttk.Combobox(safezones, textvariable=self.platform_safe_zone_var, values=SAFE_ZONE_PRESET_NAMES, state="readonly").grid(row=0, column=1, sticky="ew", padx=(12, 12))
        ttk.Button(safezones, text="Open safe-zone viewer", command=self.open_platform_safe_zone_viewer).grid(row=0, column=2)
        ttk.Label(safezones, text="Built-in platform presets are conservative guidance because app UI can vary by device, caption length, CTA and placement. Red = likely UI-obscured; green = caption-safe; purple = watermark-safe. Verify with the platform's own preview before publishing.", style="Muted.TLabel", wraplength=940).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.subtitle_advanced_frames = (advanced_style, animated)
        self.subtitle_advanced_visible = False
        for frame in self.subtitle_advanced_frames:
            frame.grid_remove()
        self.subtitle_advanced_toggle_btn = ttk.Button(stylebox, text="Show advanced styling", command=self.toggle_subtitle_advanced)
        self.subtitle_advanced_toggle_btn.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))
        actions = ttk.Frame(p)
        actions.grid(row=5, column=0, sticky="ew")
        ttk.Button(actions, text="Validate subtitles and fonts", command=self.validate_async).pack(side="left")
    def toggle_subtitle_advanced(self):
        self.subtitle_advanced_visible = not bool(getattr(self, "subtitle_advanced_visible", False))
        for frame in getattr(self, "subtitle_advanced_frames", ()):
            if self.subtitle_advanced_visible:
                frame.grid()
            else:
                frame.grid_remove()
        self.subtitle_advanced_toggle_btn.configure(text="Hide advanced styling" if self.subtitle_advanced_visible else "Show advanced styling")
        return self.subtitle_advanced_visible
    def watermark_ui(self):
        # Two-step flow: (1) enable + pick a mode, (2) only that mode's settings appear.
        # Everything below "Step 1" is rebuilt by rebuild_watermark_settings() whenever
        # enabled/timing/type changes, instead of showing every field for every mode at once.
        p = self.page_watermark
        p.columnconfigure(0, weight=1)
        top = ttk.LabelFrame(p, text="Watermark", padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Checkbutton(top, text="Enable watermark", variable=self.watermark_enabled_var).grid(row=0, column=0, sticky="w", pady=4)

        self.watermark_mode_box = ttk.LabelFrame(p, text="Step 1: how should the watermark appear?", padding=10)
        self.watermark_mode_box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Radiobutton(self.watermark_mode_box, text="Full duration - shown for the whole video", variable=self.watermark_timing_var, value="Full duration").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Radiobutton(self.watermark_mode_box, text="Intervals - only shown during specific time ranges", variable=self.watermark_timing_var, value="Intervals").grid(row=1, column=0, sticky="w", pady=2)

        self.watermark_settings_container = ttk.Frame(p)
        self.watermark_settings_container.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.watermark_settings_container.columnconfigure(0, weight=1)

        for var in (self.watermark_enabled_var, self.watermark_timing_var, self.watermark_type_var):
            var.trace_add("write", self.rebuild_watermark_settings)
        self.rebuild_watermark_settings()

    def rebuild_watermark_settings(self, *_args):
        enabled = self.watermark_enabled_var.get()
        if enabled:
            self.watermark_mode_box.grid()
        else:
            self.watermark_mode_box.grid_remove()
        for child in self.watermark_settings_container.winfo_children():
            child.destroy()
        if not enabled:
            return

        timing = self.watermark_timing_var.get()
        wtype = self.watermark_type_var.get()

        box = ttk.LabelFrame(self.watermark_settings_container, text="Step 2: watermark settings", padding=10)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)
        r = 0
        ttk.Label(box, text="Type").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Combobox(box, textvariable=self.watermark_type_var, values=WATERMARK_TYPES, state="readonly").grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        if wtype == "Text":
            self.labeled_entry(box, r, "Text", self.watermark_text_var)
            r += 1
            same_font_cb = ttk.Checkbutton(box, text="Use subtitle font for text watermark", variable=self.same_wm_font_var, command=self.refresh_watermark_font_control_state)
            same_font_cb.grid(row=r, column=1, sticky="w", pady=4)
            r += 1
            ttk.Label(box, text="Watermark font").grid(row=r, column=0, sticky="w", pady=4)
            self.wm_font_combo = ttk.Combobox(box, textvariable=self.wm_font_var, state="readonly")
            if getattr(self, "font_map", None):
                self.wm_font_combo["values"] = list(self.font_map.keys())
            self.wm_font_combo.grid(row=r, column=1, sticky="ew", pady=4)
            self.wm_font_combo.bind("<<ComboboxSelected>>", self.on_watermark_font_selected)
            self.refresh_watermark_font_control_state()
            r += 1
        else:
            img_ent = self.labeled_entry(box, r, "Image", self.watermark_image_var, self.browse_watermark_image)
            self.drop.bind(img_ent, self.drop_watermark)
            r += 1

        if timing == "Full duration":
            ttk.Label(box, text="Position").grid(row=r, column=0, sticky="w", pady=4)
            ttk.Combobox(box, textvariable=self.watermark_position_var, values=POSITIONS, state="readonly").grid(row=r, column=1, sticky="ew", pady=4)
            r += 1
        else:
            ttk.Label(box, text="Position is set per interval below.", style="Muted.TLabel").grid(row=r, column=0, columnspan=2, sticky="w", pady=4)
            r += 1

        grid = ttk.Frame(box)
        grid.grid(row=r, column=0, columnspan=3, sticky="ew", pady=8)
        if wtype == "Text":
            fields = [("Text size", self.watermark_size_var), ("Opacity %", self.watermark_opacity_var), ("Margin", self.watermark_margin_var), ("Text outline", self.watermark_outline_var)]
            for i, (label, var) in enumerate(fields):
                ttk.Label(grid, text=label).grid(row=0, column=i, sticky="w", padx=(0, 14))
                ttk.Entry(grid, textvariable=var, width=12).grid(row=1, column=i, sticky="w", padx=(0, 14))
        else:
            fields = [("Opacity %", self.watermark_opacity_var), ("Margin", self.watermark_margin_var), ("Scale % (100 = natural)", self.watermark_image_scale_var), ("X px", self.watermark_image_x_var), ("Y px", self.watermark_image_y_var)]
            for i, (label, var) in enumerate(fields):
                ttk.Label(grid, text=label).grid(row=0, column=i, sticky="w", padx=(0, 14))
                ttk.Entry(grid, textvariable=var, width=12).grid(row=1, column=i, sticky="w", padx=(0, 14))
            ttk.Label(grid, text="Custom X/Y override the preset Position. Reset layout to return to preset positioning. 100% means the watermark's cropped visible content is used at its natural pixel size.", style="Muted.TLabel").grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 4))
            btns = ttk.Frame(grid)
            btns.grid(row=3, column=0, columnspan=5, sticky="w", pady=(4, 0))
            ttk.Button(btns, text="Open layout editor", command=self.open_watermark_layout_editor).pack(side="left")
            ttk.Button(btns, text="Reset image layout", command=self.reset_watermark_image_layout).pack(side="left", padx=(12, 0))

        if timing == "Intervals":
            interval = ttk.LabelFrame(self.watermark_settings_container, text="Intervals", padding=10)
            interval.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            interval.columnconfigure(0, weight=1)
            self.interval_tree = ttk.Treeview(interval, columns=("start", "end", "position"), show="headings", height=7)
            for col, title in (("start", "Start"), ("end", "End"), ("position", "Position")):
                self.interval_tree.heading(col, text=title)
                self.interval_tree.column(col, width=160)
            self.interval_tree.grid(row=0, column=0, columnspan=5, sticky="ew")
            ttk.Button(interval, text="Add", command=self.add_interval).grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Button(interval, text="Edit", command=self.edit_interval).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Button(interval, text="Delete", command=self.delete_interval).grid(row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0))
            ttk.Button(interval, text="Preview selected boundary", command=self.preview_async).grid(row=1, column=3, sticky="w", padx=(20, 0), pady=(8, 0))
            self.refresh_intervals()
    def encode_ui(self):
        p = self.page_encode
        p.columnconfigure(0, weight=1)
        opts = ttk.LabelFrame(p, text="Encoding", padding=10)
        opts.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        opts.columnconfigure(1, weight=1)
        self.encode_row_widgets = {}
        rows = [("Interface mode", self.mode_var, ["Simple", "Advanced"]), ("Codec", self.codec_var, CODEC_MODES), ("Quality mode", self.quality_mode_var, QUALITY_MODES), ("Encoder policy", self.encoder_policy_var, ENCODER_POLICIES), ("Speed preset", self.speed_mode_var, SPEED_MODES), ("Resolution", self.resolution_var, RESOLUTION_MODES), ("Frame rate", self.fps_var, FPS_MODES), ("Audio", self.audio_mode_var, AUDIO_MODES)]
        for i, (label, var, values) in enumerate(rows):
            lab = ttk.Label(opts, text=label)
            lab.grid(row=i, column=0, sticky="w", pady=4)
            combo = ttk.Combobox(opts, textvariable=var, values=values, state="readonly")
            combo.grid(row=i, column=1, sticky="ew", pady=4)
            self.encode_row_widgets[label] = (lab, combo)
        enc_label = ttk.Label(opts, text="Encoder")
        enc_label.grid(row=8, column=0, sticky="w", pady=4)
        self.encoder_combo = ttk.Combobox(opts, textvariable=self.encoder_var, state="readonly")
        self.encoder_combo.grid(row=8, column=1, sticky="ew", pady=4)
        probe_btn = ttk.Button(opts, text="Quick probe", command=self.probe_encoders_async)
        probe_btn.grid(row=8, column=2, padx=(12, 0))
        benchmark_btn = ttk.Button(opts, text="Benchmark", command=self.benchmark_async)
        benchmark_btn.grid(row=8, column=3, padx=(12, 0))
        self.encoder_manual_widgets = (enc_label, self.encoder_combo, probe_btn, benchmark_btn)
        bitrate_label = ttk.Label(opts, text="Custom bitrate kbps")
        bitrate_label.grid(row=9, column=0, sticky="w", pady=4)
        bitrate_entry = ttk.Entry(opts, textvariable=self.custom_bitrate_var, width=12)
        bitrate_entry.grid(row=9, column=1, sticky="w", pady=4)
        self.bitrate_widgets = (bitrate_label, bitrate_entry)
        target_label = ttk.Label(opts, text="Target size MB")
        target_label.grid(row=10, column=0, sticky="w", pady=4)
        target_entry = ttk.Entry(opts, textvariable=self.target_size_var, width=12)
        target_entry.grid(row=10, column=1, sticky="w", pady=4)
        self.target_size_widgets = (target_label, target_entry)
        self.chapter_widget = ttk.Checkbutton(opts, text="Preserve chapters", variable=self.chapter_var)
        self.chapter_widget.grid(row=11, column=1, sticky="w", pady=4)
        ttk.Label(opts, textvariable=self.estimate_var).grid(row=12, column=1, sticky="w", pady=4)
        self.mode_var.trace_add("write", self.update_encode_visibility)
        self.quality_mode_var.trace_add("write", self.update_encode_visibility)
        self.update_encode_visibility()
        run = ttk.LabelFrame(p, text="Run", padding=10)
        run.grid(row=1, column=0, sticky="ew")
        self.start_btn = ttk.Button(run, text="Burn video", style="Accent.TButton", command=self.start_encode)
        self.start_btn.pack(side="left")
        self.pause_btn = ttk.Button(run, text="Pause", command=self.pause_encode, state="disabled")
        self.pause_btn.pack(side="left", padx=(12, 0))
        self.resume_btn = ttk.Button(run, text="Resume", command=self.resume_encode, state="disabled")
        self.resume_btn.pack(side="left", padx=(12, 0))
        self.cancel_btn = ttk.Button(run, text="Cancel", style="Danger.TButton", command=self.cancel_encode, state="disabled")
        self.cancel_btn.pack(side="left", padx=(12, 0))
        self.open_file_btn = ttk.Button(run, text="Open file", command=self.open_last_output, state="disabled")
        self.open_file_btn.pack(side="right")
        self.open_folder_btn = ttk.Button(run, text="Open folder", command=self.open_last_folder, state="disabled")
        self.open_folder_btn.pack(side="right", padx=(0, 8))
    def update_encode_visibility(self, *_args):
        if not hasattr(self, "encode_row_widgets"):
            return
        advanced = self.mode_var.get() == "Advanced"
        quality = self.quality_mode_var.get()
        groups = [self.encode_row_widgets.get("Encoder policy", ()), self.encode_row_widgets.get("Speed preset", ()), getattr(self, "encoder_manual_widgets", ()), (getattr(self, "chapter_widget", None),)]
        for group in groups:
            for widget in group:
                if widget is None:
                    continue
                if advanced:
                    widget.grid()
                else:
                    widget.grid_remove()
        for widget in getattr(self, "bitrate_widgets", ()):
            if advanced or quality == "Custom bitrate":
                widget.grid()
            else:
                widget.grid_remove()
        for widget in getattr(self, "target_size_widgets", ()):
            if advanced or quality == "Target file size":
                widget.grid()
            else:
                widget.grid_remove()
    def activity_ui(self):
        p = self.page_activity
        p.rowconfigure(0, weight=1)
        p.columnconfigure(0, weight=1)
        self.log_text = tk.Text(p, wrap="word", height=25, bg=self.ui_colors['entry'], fg=self.ui_colors['text'], insertbackground=self.ui_colors['text'], selectbackground=self.ui_colors['accent_soft'], selectforeground=self.ui_colors['selection_text'], highlightbackground=self.ui_colors['border_soft'], highlightcolor=self.ui_colors['accent'], relief='flat', borderwidth=1)
        scroll = ttk.Scrollbar(p, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        bar = ttk.Frame(p)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(bar, text="Export diagnostics", command=self.export_diagnostics).pack(side="left")
        ttk.Button(bar, text="Copy log", command=self.copy_log).pack(side="left", padx=(12, 0))
    def about_ui(self):
        p = self.page_about
        ttk.Label(p, text="SubBurn", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(p, text="Local subtitle rendering, transcription, preview, and export.").pack(anchor="w")
    def current_operation_id(self):
        return getattr(self._operation_local, "operation_id", None)
    def begin_operation(self, kind, label=None, *, priority=None, mode=None):
        return self.op_state.begin(kind, label, priority=priority, mode=mode)
    def finish_operation(self, op_id, state="succeeded", *, error="", result=""):
        return self.op_state.finish(op_id, state, error=error, result=result)
    def _finish_operation_from_result(self, op_id, result):
        if not op_id or self.op_state.state_of(op_id) in OperationState.TERMINAL_STATES:
            return
        state = "succeeded"; error = ""; output = ""
        if isinstance(result, dict):
            raw = str(result.get("status") or "").casefold()
            if raw in {"failed", "error"}:
                state = "failed"; error = str(result.get("error") or "Operation failed")
            elif raw == "paused":
                state = "paused"
            elif raw in {"cancelled", "canceled"}:
                state = "cancelled"
            output = str(result.get("output") or result.get("srt") or "")
        elif result is False:
            state = "cancelled"
        self.finish_operation(op_id, state, error=error, result=output)
    def emit(self, kind, *args):
        op_id = self.current_operation_id()
        if op_id:
            if kind == "progress" and args:
                self.op_state.progress(op_id, args[0], *(list(args[1:4]) + ["-", "-", "-"])[:3])
            elif kind == "transfer_progress" and args:
                self.op_state.transfer(op_id, *(list(args[:6]) + [None] * 6)[:6])
            elif kind == "transcription_progress" and args:
                self.op_state.progress(op_id, args[0], explicit=False)
            elif kind == "error":
                self.finish_operation(op_id, "failed", error=str(args[0]) if args else "Operation failed")
            elif kind == "done":
                self.finish_operation(op_id, "succeeded", result=str(args[0]) if args else "")
            elif kind == "status" and args:
                self.op_state.set_status(str(args[0]))
        self.events.put((kind, args, op_id))
    def drain(self):
        try:
            while True:
                event = self.events.get_nowait()
                if len(event) == 3:
                    kind, args, event_op_id = event
                else:
                    kind, args = event
                    event_op_id = None
                foreground_event = event_op_id is None or self.op_state.is_foreground(event_op_id)
                if kind == "log":
                    self.log_ui(args[0])
                elif kind == "status":
                    if foreground_event:
                        self.status_var.set(args[0])
                elif kind == "tool":
                    self.apply_toolset(args[0], args[1])
                elif kind == "fonts":
                    self.apply_fonts(args[0])
                elif kind == "media":
                    self.apply_media(args[0])
                elif kind == "progress":
                    if foreground_event:
                        self.apply_progress(*args)
                elif kind == "transfer_progress":
                    if foreground_event:
                        self.apply_progress(args[0], "-", self.op_state.snapshot().get("speed", "-"), self.op_state.snapshot().get("eta", "-"))
                elif kind == "stage":
                    if foreground_event:
                        self.apply_stage(*args)
                elif kind == "error":
                    if foreground_event:
                        self.error_ui(args[0])
                    else:
                        self.log_ui("BACKGROUND ERROR: " + str(args[0]))
                elif kind == "warning":
                    if foreground_event:
                        self.warning_ui(args[0])
                    else:
                        self.log_ui("BACKGROUND WARNING: " + str(args[0]))
                elif kind == "done":
                    if foreground_event:
                        self.done_ui(args[0])
                    else:
                        self.log_ui("Background operation completed: " + str(args[0]))
                elif kind == "dashboard_action":
                    self.apply_dashboard_action(args[0])
                elif kind == "dashboard_appearance":
                    self.apply_dashboard_appearance(args[0])
                elif kind == "dashboard_watermark":
                    self.apply_dashboard_watermark(args[0])
                elif kind == "dashboard_encoding":
                    self.apply_dashboard_encoding(args[0])
                elif kind == "dashboard_subtitles":
                    self.apply_dashboard_subtitles(args[0])
                elif kind == "dashboard_project":
                    self.apply_dashboard_project(args[0])
                elif kind == "dashboard_transcription":
                    self.apply_dashboard_transcription(args[0])
                elif kind == "dashboard_queue_action":
                    self.apply_dashboard_queue_action(args[0])
                elif kind == "dashboard_queue_item_action":
                    self.apply_dashboard_queue_item_action(*args)
                elif kind == "dashboard_font_import":
                    self.apply_dashboard_font_import(args[0])
                elif kind == "dashboard_preview_interval":
                    self.apply_dashboard_interval_preview(args[0])
                elif kind == "dashboard_live_frame":
                    self.apply_dashboard_live_frame(args[0])
                elif kind == "dashboard_live_position":
                    self.apply_dashboard_live_position(*args)
                elif kind == "dashboard_live_clip":
                    self.apply_dashboard_live_clip(args[0])
                elif kind == "live_frame":
                    self.apply_live_frame(*args)
                elif kind == "live_clip":
                    self.apply_live_clip(*args)
                elif kind == "recent_project_restore":
                    self.apply_recent_project_restore(args[0])
                elif kind == "clear_recents":
                    self.apply_clear_recents(args[0])
                elif kind == "batch_refresh":
                    self.refresh_batch_tree()
                elif kind == "transcription_status":
                    self.transcription_status_var.set(str(args[0]))
                    self.publish_dashboard_controls()
                elif kind == "transcription_progress":
                    self.refresh_transcription_progress_ui()
                elif kind == "transcription_model_ready":
                    self.transcription_status_var.set(str(args[0]))
                    self.publish_dashboard_controls()
                    self.refresh_transcription_model_metadata_async(False)
                elif kind == "transcription_model_metadata":
                    model, meta = args
                    if str(model) == str(self.transcription_model_var.get()):
                        self.transcription_model_info_var.set(format_transcription_model_metadata(meta))
                        self.publish_dashboard_controls()
                elif kind == "transcription_done":
                    self.apply_transcription_done(*args)
        except queue.Empty:
            pass
        if self.close_when_idle and not self.running and self.active_job_count() == 0:
            self.close_when_idle = False
            self.root.destroy()
            return
        self.root.after(100, self.drain)
    def log(self, text):
        self.emit("log", text)
    def queue_dashboard_action(self, action):
        action = str(action).casefold().strip()
        if action not in {"discover_tools", "download_runtime", "analyze", "validate", "probe", "benchmark", "preview", "compare", "encode", "pause", "resume", "cancel", "refresh_fonts", "diagnostics", "open_file", "open_folder", "restore_recovery", "browser_only", "show_window", "exit_app", "transcription_prepare", "transcription_start", "transcription_cancel"}:
            return False, f"Unknown action: {action or 'empty'}"
        self.events.put(("dashboard_action", (action,)))
        return True, f"{action.capitalize()} request queued"
    def queue_dashboard_interval_preview(self, index):
        if isinstance(index, bool):
            return False, "Choose a valid interval"
        try:
            index = int(index)
        except Exception:
            return False, "Choose a valid interval"
        if index < 0 or index > 9999:
            return False, "Choose a valid interval"
        self.events.put(("dashboard_preview_interval", (index,)))
        return True, f"Boundary preview {index + 1} queued"
    def queue_dashboard_live_frame(self, timestamp):
        if isinstance(timestamp, bool):
            return False, "Choose a valid live preview timestamp"
        try:
            timestamp = float(timestamp)
        except Exception:
            return False, "Choose a valid live preview timestamp"
        if not math.isfinite(timestamp) or timestamp < 0:
            return False, "Choose a valid live preview timestamp"
        self.events.put(("dashboard_live_frame", (timestamp,)))
        return True, f"Live frame {fmt_time(timestamp)} queued"
    def queue_dashboard_font_import(self, raw_path):
        value = str(raw_path).strip()
        if not value or len(value) > 4096:
            return False, "Choose a valid font file"
        p = Path(value)
        if not p.is_file() or p.suffix.casefold() not in {".ttf", ".otf", ".ttc"}:
            return False, "Choose an existing TTF, OTF, or TTC font file"
        self.events.put(("dashboard_font_import", (str(p),)))
        return True, "Font import queued"
    def dashboard_control_snapshot(self):
        return {
            "appearance": {"mode": normalize_appearance_mode(self.appearance_var.get()), "mode_options": list(APPEARANCE_MODES)},
            "watermark": {
                "enabled": bool(self.watermark_enabled_var.get()),
                "timing": self.watermark_timing_var.get(),
                "type": self.watermark_type_var.get(),
                "text": self.watermark_text_var.get(),
                "same_font": bool(self.same_wm_font_var.get()),
                "font": self.wm_font_var.get(),
                "font_options": list(self.font_map.keys()),
                "image": self.watermark_image_var.get(),
                "position": self.watermark_position_var.get(),
                "size": self.watermark_size_var.get(),
                "opacity": self.watermark_opacity_var.get(),
                "margin": self.watermark_margin_var.get(),
                "outline": self.watermark_outline_var.get(),
                "image_width": self.watermark_image_width_var.get(),
                "image_scale": self.watermark_image_scale_var.get(),
                "image_x": self.watermark_image_x_var.get(),
                "image_y": self.watermark_image_y_var.get(),
                "intervals": [{"start": a, "end": b, "position": pos} for a, b, pos in self.watermark_rows],
            },
            "encoding": {
                "mode": self.mode_var.get(), "mode_options": ["Simple", "Advanced"],
                "output_ext": self.output_ext_var.get(), "output_ext_options": OUTPUT_EXTS,
                "codec": self.codec_var.get(), "codec_options": CODEC_MODES,
                "quality": self.quality_mode_var.get(), "quality_options": QUALITY_MODES,
                "policy": self.encoder_policy_var.get(), "policy_options": ENCODER_POLICIES,
                "speed": self.speed_mode_var.get(), "speed_options": SPEED_MODES,
                "resolution": self.resolution_var.get(), "resolution_options": RESOLUTION_MODES,
                "fps": self.fps_var.get(), "fps_options": FPS_MODES,
                "audio": self.audio_mode_var.get(), "audio_options": AUDIO_MODES,
                "encoder": self.encoder_var.get(),
                "encoder_options": ["Auto"] + (list(self.toolset.encoders) if self.toolset else []),
                "custom_bitrate": self.custom_bitrate_var.get(),
                "target_size": self.target_size_var.get(),
                "chapter": bool(self.chapter_var.get()),
            },
            "subtitles": {
                "primary_font": self.primary_font_var.get(),
                "font_options": list(self.font_map.keys()),
                "fallback_fonts": list(self.fallback_list.get(0, "end")) if hasattr(self, "fallback_list") else [],
                "font_size": self.font_size_var.get(),
                "outline": self.outline_var.get(),
                "margin": self.margin_var.get(),
                "safe_area": self.safe_area_var.get(),
                "platform_safe_zone": self.platform_safe_zone_var.get(),
                "platform_safe_zone_options": SAFE_ZONE_PRESET_NAMES,
                "alignment_options": SUBTITLE_ALIGNMENT_NAMES,
                "wrap_chars": self.wrap_chars_var.get(),
                "max_lines": self.max_lines_var.get(),
                "offset_ms": self.subtitle_offset_var.get(),
                "text_rgb": self.text_rgb_var.get(),
                "outline_rgb": self.outline_rgb_var.get(),
                "force_bold": bool(self.force_bold_var.get()),
                "italic": bool(self.italic_var.get()),
                "underline": bool(self.underline_var.get()),
                "strikeout": bool(self.strikeout_var.get()),
                "text_opacity": self.text_opacity_var.get(),
                "outline_opacity": self.outline_opacity_var.get(),
                "shadow_depth": self.shadow_depth_var.get(),
                "shadow_rgb": self.shadow_rgb_var.get(),
                "shadow_opacity": self.shadow_opacity_var.get(),
                "letter_spacing": self.letter_spacing_var.get(),
                "rotation_angle": self.rotation_angle_var.get(),
                "subtitle_alignment": self.subtitle_alignment_var.get(),
                "margin_left": self.margin_left_var.get(),
                "margin_right": self.margin_right_var.get(),
                "background_box": bool(self.background_box_var.get()),
                "background_rgb": self.background_rgb_var.get(),
                "background_opacity": self.background_opacity_var.get(),
                "background_padding": self.background_padding_var.get(),
                "caption_effect_id": CAPTION_EFFECT_LABEL_TO_ID.get(self.caption_effect_var.get(), "none"),
                "caption_effect_params": {"active_rgb": self.caption_active_rgb_var.get().strip().upper(), "allow_estimated_timing": bool(self.caption_estimated_timing_var.get())},
                "caption_effect_options": [{"id": effect_id, "label": label} for label, effect_id in CAPTION_EFFECT_LABEL_TO_ID.items()],
            },
            "project": {
                "ffmpeg": self.ffmpeg_var.get(),
                "video": self.video_var.get(),
                "subtitle_source": self.subtitle_source_var.get(),
                "subtitle_source_options": ["Auto", "External", "Embedded"],
                "subtitle_file": self.subtitle_file_var.get(),
                "embedded_track": self.embedded_track_var.get(),
                "embedded_options": list(self.embedded_combo["values"]) if hasattr(self, "embedded_combo") else [],
                "output_dir": self.output_dir_var.get(),
                "output_name": self.output_name_var.get(),
                "clean_output": bool(self.clean_output_var.get()),
                "metadata": {key: self.metadata_vars[key].get() for key in USER_METADATA_KEYS},
            },
            "transcription": {
                "model": self.transcription_model_var.get(),
                "model_options": list(TRANSCRIPTION_MODELS),
                "language_mode": self.transcription_language_mode_var.get(),
                "language_mode_options": list(TRANSCRIPTION_LANGUAGE_MODES),
                "language_code": self.transcription_language_code_var.get(),
                "language_display_options": [{"code": "", "label": WHISPER_LANGUAGE_PICKER_PROMPT}] + [
                    {"code": code, "label": f"{name} ({code})"}
                    for code, name in sorted(WHISPER_LANGUAGES.items(), key=lambda item: (item[1].casefold(), item[0]))
                ],
                "device": self.transcription_device_var.get(),
                "device_options": list(TRANSCRIPTION_DEVICES),
                "status": self.transcription_status_var.get(),
                "progress": float(self.transcription_progress_var.get()),
                "result": self.transcription_result_var.get(),
                "model_info": self.transcription_model_info_var.get(),
            },
            "recents": {
                "projects": [{"label": x.get("label", ""), "video": x.get("video", ""), "saved_at": x.get("saved_at", 0)} for x in self.recents.get("projects", [])],
                "folders": list(self.recents.get("folders", [])),
            },
        }
    def publish_dashboard_controls(self):
        self.op_state.set_controls(self.dashboard_control_snapshot())
    def dashboard_filesystem_roots(self):
        # The browser picker is deliberately narrower than an OS file manager.  It may browse
        # the user's home/output locations plus folders already selected in the current project,
        # but it never exposes arbitrary filesystem roots merely because the dashboard is open.
        candidates = [Path.home(), SUBBURN_OUTPUT_DIR]
        # HTTP handlers run on worker threads; never read Tk variables here.  Use the
        # thread-safe shared control snapshot published by the main/UI thread.
        snap = self.op_state.control_snapshot()
        project = dict(snap.get("project") or {})
        watermark = dict(snap.get("watermark") or {})
        for raw in (
            project.get("video"), project.get("subtitle_file"), project.get("output_dir"),
            project.get("ffmpeg"), watermark.get("image"),
        ):
            raw = str(raw or "").strip()
            if not raw:
                continue
            try:
                q = Path(raw).expanduser()
                candidates.append(q if q.is_dir() else q.parent)
            except Exception:
                continue
        roots, seen = [], set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                if not resolved.exists() or not resolved.is_dir():
                    continue
                key = os.path.normcase(str(resolved))
            except Exception:
                continue
            if key in seen:
                continue
            seen.add(key); roots.append(resolved)
        return roots

    def dashboard_filesystem_listing(self, raw_path, kind):
        kind = str(kind).casefold().strip()
        if kind not in {"video", "subtitle", "image", "ffmpeg", "folder", "font"}:
            raise ValueError("Unknown file picker type")
        roots = self.dashboard_filesystem_roots()
        if not raw_path:
            return {
                "path": "", "parent": "",
                "entries": [{"name": str(root), "path": str(root), "is_dir": True} for root in roots],
                "truncated": False,
            }
        p = Path(raw_path).expanduser()
        if p.is_file():
            p = p.parent
        if not p.exists() or not p.is_dir():
            raise ValueError("Folder does not exist")
        try:
            p = p.resolve()
        except Exception:
            raise ValueError("Folder cannot be resolved safely")
        if not any(_path_within(p, root) for root in roots):
            raise ValueError("Folder is outside the browser picker's allowed locations")
        def include_file(child):
            if kind == "video":
                return child.suffix.casefold() in VIDEO_EXTS
            if kind == "subtitle":
                return child.suffix.casefold() in SUBTITLE_FILE_EXTS
            if kind == "image":
                return child.suffix.casefold() in IMAGE_EXTS
            if kind == "ffmpeg":
                return child.name.casefold() in {"ffmpeg", "ffmpeg.exe"}
            if kind == "font":
                return child.suffix.casefold() in {".ttf", ".otf", ".ttc"}
            return False
        rows = []
        try:
            children = list(p.iterdir())
        except Exception as e:
            raise ValueError(f"Cannot read folder: {e}")
        def sort_key(x):
            try:
                return (not x.is_dir(), x.name.casefold())
            except Exception:
                return (True, x.name.casefold())
        children.sort(key=sort_key)
        truncated = len(children) > 2000
        for child in children:
            if len(rows) >= 2000:
                break
            try:
                # Resolve each child before exposing it.  This blocks a symlink/junction inside an
                # allowed directory from turning the picker into an escape hatch.
                resolved_child = child.resolve()
                if not any(_path_within(resolved_child, root) for root in roots):
                    continue
                is_dir = resolved_child.is_dir()
                if not is_dir and (kind == "folder" or not include_file(resolved_child)):
                    continue
                rows.append({"name": child.name, "path": str(resolved_child), "is_dir": is_dir})
            except Exception:
                continue
        parent_candidate = p.parent
        parent = ""
        if parent_candidate != p and any(_path_within(parent_candidate, root) for root in roots):
            parent = str(parent_candidate)
        return {"path": str(p), "parent": parent, "entries": rows, "truncated": truncated}
    def normalize_dashboard_watermark(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Watermark settings must be a JSON object")
        allowed = {"enabled", "timing", "type", "text", "same_font", "font", "image", "position", "size", "opacity", "margin", "outline", "image_width", "image_scale", "image_x", "image_y", "intervals"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Unknown watermark setting: " + ", ".join(sorted(unknown)))
        out = {}
        for key in ("enabled", "same_font"):
            if key in payload:
                if not isinstance(payload[key], bool):
                    raise ValueError(f"{key} must be true or false")
                out[key] = payload[key]
        if "timing" in payload:
            if payload["timing"] not in WATERMARK_TIMING:
                raise ValueError("Invalid watermark timing")
            out["timing"] = payload["timing"]
        if "type" in payload:
            if payload["type"] not in WATERMARK_TYPES:
                raise ValueError("Invalid watermark type")
            out["type"] = payload["type"]
        if "position" in payload:
            if payload["position"] not in POSITIONS:
                raise ValueError("Invalid watermark position")
            out["position"] = payload["position"]
        for key, limit in (("text", 4000), ("font", 512), ("image", 4096)):
            if key in payload:
                value = str(payload[key])
                if len(value) > limit:
                    raise ValueError(f"{key} is too long")
                out[key] = value
        numeric = {
            "size": (0.1, 1000.0),
            "opacity": (0.0, 100.0),
            "margin": (0.0, 10000.0),
            "outline": (0.0, 1000.0),
            "image_width": (0.1, 100.0),
            "image_scale": (0.1, 1000.0),
        }
        for key, (lo, hi) in numeric.items():
            if key in payload:
                try:
                    value = float(payload[key])
                except Exception:
                    raise ValueError(f"{key} must be numeric")
                if value < lo or value > hi:
                    raise ValueError(f"{key} must be between {lo:g} and {hi:g}")
                out[key] = str(payload[key]).strip()
        for key in ("image_x", "image_y"):
            if key in payload:
                raw = str(payload[key]).strip()
                if raw == "":
                    out[key] = ""
                    continue
                try:
                    value = float(raw)
                except Exception:
                    raise ValueError(f"{key} must be blank or numeric")
                if value < -100000.0 or value > 100000.0:
                    raise ValueError(f"{key} must be between -100000 and 100000")
                out[key] = raw
        if "intervals" in payload:
            rows = payload["intervals"]
            if not isinstance(rows, list) or len(rows) > 1000:
                raise ValueError("intervals must be a list with at most 1000 rows")
            normalized = []
            for i, row in enumerate(rows, 1):
                if not isinstance(row, dict):
                    raise ValueError(f"Interval {i} must be an object")
                try:
                    start = parse_time_value(row.get("start", ""))
                    end = parse_time_value(row.get("end", ""))
                except Exception:
                    raise ValueError(f"Interval {i} has an invalid time")
                position = row.get("position")
                if position not in POSITIONS:
                    raise ValueError(f"Interval {i} has an invalid position")
                if start < 0 or end <= start:
                    raise ValueError(f"Interval {i} must have end after start")
                normalized.append((start, end, position))
            normalized.sort(key=lambda x: x[0])
            out["intervals"] = normalized
        return out
    def normalize_dashboard_encoding(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Encoding settings must be a JSON object")
        allowed = {"mode", "output_ext", "codec", "quality", "policy", "speed", "resolution", "fps", "audio", "encoder", "custom_bitrate", "target_size", "chapter"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Unknown encoding setting: " + ", ".join(sorted(unknown)))
        out = {}
        enums = {
            "mode": ["Simple", "Advanced"], "output_ext": OUTPUT_EXTS, "codec": CODEC_MODES,
            "quality": QUALITY_MODES, "policy": ENCODER_POLICIES, "speed": SPEED_MODES,
            "resolution": RESOLUTION_MODES, "fps": FPS_MODES, "audio": AUDIO_MODES,
        }
        for key, options in enums.items():
            if key in payload:
                value = normalize_codec_mode(payload[key]) if key == "codec" else payload[key]
                if value not in options:
                    raise ValueError(f"Invalid {key} value")
                out[key] = value
        if "chapter" in payload:
            if not isinstance(payload["chapter"], bool):
                raise ValueError("chapter must be true or false")
            out["chapter"] = payload["chapter"]
        for key, lo, hi in (("custom_bitrate", 1.0, 1000000.0), ("target_size", 0.1, 10000000.0)):
            if key in payload:
                try:
                    value = float(payload[key])
                except Exception:
                    raise ValueError(f"{key} must be numeric")
                if value < lo or value > hi:
                    raise ValueError(f"{key} must be between {lo:g} and {hi:g}")
                out[key] = str(payload[key]).strip()
        if "encoder" in payload:
            value = str(payload["encoder"]).strip()
            if not value:
                raise ValueError("encoder cannot be empty")
            out["encoder"] = value
        snap = self.op_state.control_snapshot().get("encoding") or {}
        ext = out.get("output_ext", snap.get("output_ext", ".mp4"))
        codec = out.get("codec", snap.get("codec", "Match source"))
        if codec != "Match source" and codec not in CONTAINER_CODECS.get(ext, set()):
            raise ValueError(f"Codec '{codec}' is not supported in output container '{ext}'")
        if out.get("encoder"):
            options = snap.get("encoder_options") or ["Auto"]
            if out["encoder"] not in options:
                raise ValueError("Selected encoder is not available")
        return out
    def normalize_dashboard_subtitles(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Subtitle settings must be a JSON object")
        allowed = {"primary_font", "fallback_fonts", "font_size", "outline", "margin", "safe_area", "platform_safe_zone", "wrap_chars", "max_lines", "offset_ms", "text_rgb", "outline_rgb", "force_bold", "italic", "underline", "strikeout", "text_opacity", "outline_opacity", "shadow_depth", "shadow_rgb", "shadow_opacity", "letter_spacing", "rotation_angle", "subtitle_alignment", "margin_left", "margin_right", "background_box", "background_rgb", "background_opacity", "background_padding", "caption_effect_id", "caption_effect_params"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Unknown subtitle setting: " + ", ".join(sorted(unknown)))
        out = {}
        snap = self.op_state.control_snapshot().get("subtitles") or {}
        font_options = snap.get("font_options") or []
        if "primary_font" in payload:
            value = str(payload["primary_font"])
            if value and value not in font_options:
                raise ValueError("Selected primary font is not available")
            out["primary_font"] = value
        if "fallback_fonts" in payload:
            rows = payload["fallback_fonts"]
            if not isinstance(rows, list) or len(rows) > 64:
                raise ValueError("fallback_fonts must be a list with at most 64 fonts")
            clean = []
            for value in rows:
                value = str(value)
                if value not in font_options:
                    raise ValueError(f"Fallback font is not available: {value}")
                if value not in clean:
                    clean.append(value)
            out["fallback_fonts"] = clean
        numeric = {
            "font_size": (0.1, 1000.0), "outline": (0.0, 1000.0), "margin": (0.0, 10000.0),
            "safe_area": (0.0, 10000.0), "wrap_chars": (0.0, 10000.0), "max_lines": (0.0, 1000.0),
            "offset_ms": (-1000000000.0, 1000000000.0),
            "text_opacity": (0.0, 100.0), "outline_opacity": (0.0, 100.0),
            "shadow_depth": (0.0, 1000.0), "shadow_opacity": (0.0, 100.0),
            "letter_spacing": (-1000.0, 1000.0), "rotation_angle": (-36000.0, 36000.0),
            "margin_left": (0.0, 10000.0), "margin_right": (0.0, 10000.0),
            "background_opacity": (0.0, 100.0), "background_padding": (0.0, 1000.0),
        }
        for key, (lo, hi) in numeric.items():
            if key in payload:
                try:
                    value = float(payload[key])
                except Exception:
                    raise ValueError(f"{key} must be numeric")
                if value < lo or value > hi:
                    raise ValueError(f"{key} must be between {lo:g} and {hi:g}")
                out[key] = str(payload[key]).strip()
        if "platform_safe_zone" in payload:
            value = str(payload["platform_safe_zone"]).strip()
            if value not in SAFE_ZONE_PRESETS:
                raise ValueError("Unknown platform safe-zone preset")
            out["platform_safe_zone"] = value
        if "subtitle_alignment" in payload:
            value = str(payload["subtitle_alignment"]).strip()
            if value not in SUBTITLE_ALIGNMENT_MAP:
                raise ValueError("Unknown subtitle alignment")
            out["subtitle_alignment"] = value
        for key in ("text_rgb", "outline_rgb", "shadow_rgb", "background_rgb"):
            if key in payload:
                value = str(payload[key]).strip().lstrip("#").lstrip("＃")
                if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
                    raise ValueError(f"{key} must be a 6-digit RGB hex color")
                out[key] = value.upper()
        for key in ("force_bold", "italic", "underline", "strikeout", "background_box"):
            if key in payload:
                if not isinstance(payload[key], bool):
                    raise ValueError(f"{key} must be true or false")
                out[key] = payload[key]
        current_effect = str(payload.get("caption_effect_id", snap.get("caption_effect_id", "none")))
        if "caption_effect_id" in payload:
            if current_effect not in CAPTION_EFFECT_ID_TO_LABEL:
                raise ValueError("Unknown caption effect")
            out["caption_effect_id"] = current_effect
        if "caption_effect_params" in payload:
            spec = CaptionEffectSpec(current_effect, payload["caption_effect_params"])
            out["caption_effect_params"] = spec.params
        return out
    def normalize_dashboard_project(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Project settings must be a JSON object")
        allowed = {"ffmpeg", "video", "subtitle_source", "subtitle_file", "embedded_track", "output_dir", "output_name", "clean_output", "metadata"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Unknown project setting: " + ", ".join(sorted(unknown)))
        out = {}
        for key, limit in (("ffmpeg", 4096), ("video", 4096), ("subtitle_file", 4096), ("embedded_track", 2000), ("output_dir", 4096), ("output_name", 512)):
            if key in payload:
                value = str(payload[key]).strip()
                if len(value) > limit:
                    raise ValueError(f"{key} is too long")
                out[key] = value
        if "subtitle_source" in payload:
            if payload["subtitle_source"] not in {"Auto", "External", "Embedded"}:
                raise ValueError("Invalid subtitle source")
            out["subtitle_source"] = payload["subtitle_source"]
        if "clean_output" in payload:
            if not isinstance(payload["clean_output"], bool):
                raise ValueError("clean_output must be true or false")
            out["clean_output"] = payload["clean_output"]
        if "metadata" in payload:
            metadata = payload["metadata"]
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be a JSON object")
            unknown_metadata = set(metadata) - set(USER_METADATA_KEYS)
            if unknown_metadata:
                raise ValueError("Unknown metadata field: " + ", ".join(sorted(unknown_metadata)))
            clean_metadata = {}
            for key in USER_METADATA_KEYS:
                if key in metadata:
                    value = str(metadata[key]).strip()
                    if len(value) > 2000 or "\x00" in value:
                        raise ValueError(f"Metadata {key} is invalid or too long")
                    clean_metadata[key] = value
            out["metadata"] = clean_metadata
        if out.get("ffmpeg") and not Path(out["ffmpeg"]).is_file():
            raise ValueError("FFmpeg path does not exist")
        if out.get("video"):
            p = Path(out["video"])
            if not p.is_file() or p.suffix.casefold() not in VIDEO_EXTS:
                raise ValueError("Video path is not a supported video file")
        if out.get("subtitle_file"):
            p = Path(out["subtitle_file"])
            if not p.is_file() or p.suffix.casefold() not in SUBTITLE_FILE_EXTS:
                raise ValueError("Subtitle path is not a supported subtitle file")
            if p.suffix.casefold() == ".idx" and not p.with_suffix(".sub").is_file():
                raise ValueError("VobSub IDX requires its paired .sub bitmap file")
        snap = self.op_state.control_snapshot().get("project") or {}
        source = out.get("subtitle_source", snap.get("subtitle_source", "Auto"))
        track = out.get("embedded_track", snap.get("embedded_track", ""))
        if source == "Embedded":
            options = snap.get("embedded_options") or []
            if not track or track not in options:
                raise ValueError("Select an available embedded subtitle track")
        return out
    def queue_dashboard_settings(self, panel, payload):
        try:
            if panel == "appearance":
                if not isinstance(payload, dict) or set(payload) - {"mode"}:
                    raise ValueError("Appearance settings must contain only mode")
                mode=normalize_appearance_mode(payload.get("mode"))
                self.events.put(("dashboard_appearance", ({"mode":mode},)))
                return True, "Appearance queued"
            if panel == "watermark":
                settings = self.normalize_dashboard_watermark(payload)
                if settings.get("font"):
                    options = (self.op_state.control_snapshot().get("watermark") or {}).get("font_options") or []
                    if settings["font"] not in options:
                        return False, "Selected watermark font is not available"
                self.events.put(("dashboard_watermark", (settings,)))
                return True, "Watermark settings queued"
            if panel == "encoding":
                settings = self.normalize_dashboard_encoding(payload)
                self.events.put(("dashboard_encoding", (settings,)))
                return True, "Encoding settings queued"
            if panel == "subtitles":
                settings = self.normalize_dashboard_subtitles(payload)
                self.events.put(("dashboard_subtitles", (settings,)))
                return True, "Subtitle settings queued"
            if panel == "project":
                settings = self.normalize_dashboard_project(payload)
                self.events.put(("dashboard_project", (settings,)))
                return True, "Project settings queued"
            if panel == "transcription":
                settings = self.normalize_dashboard_transcription(payload)
                self.events.put(("dashboard_transcription", (settings,)))
                return True, "Transcription settings queued"
            return False, f"Unknown settings panel: {panel}"
        except Exception as e:
            return False, str(e)
    def normalize_dashboard_transcription(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Transcription settings must be a JSON object")
        allowed = {"model", "language_mode", "language_code", "device"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Unknown transcription setting: " + ", ".join(sorted(unknown)))
        out = {}
        if "model" in payload:
            value = str(payload["model"]).strip()
            if value not in TRANSCRIPTION_MODELS:
                raise ValueError("Choose a supported transcription model")
            out["model"] = value
        if "language_mode" in payload:
            value = str(payload["language_mode"]).strip()
            if value not in TRANSCRIPTION_LANGUAGE_MODES:
                raise ValueError("Choose a supported language mode")
            out["language_mode"] = value
        if "device" in payload:
            value = str(payload["device"]).strip()
            if value not in TRANSCRIPTION_DEVICES:
                raise ValueError("Choose Auto, CUDA, or CPU")
            out["device"] = value
        if "language_code" in payload:
            value = str(payload["language_code"]).strip().lower()
            if len(value) > 256 or "\x00" in value:
                raise ValueError("Language setting is invalid or too long")
            out["language_code"] = value
        snap = self.op_state.control_snapshot().get("transcription") or {}
        mode = out.get("language_mode", snap.get("language_mode", TRANSCRIPTION_LANGUAGE_MODES[0]))
        code = out.get("language_code", snap.get("language_code", ""))
        if mode == "Fixed language code":
            parsed = parse_allowed_language_codes(code)
            if len(parsed) != 1:
                raise ValueError("Fixed language mode requires exactly one language code")
            out["language_code"] = parsed[0]
        elif mode == "Allowed languages (detect changes)":
            parsed = parse_allowed_language_codes(code)
            if len(parsed) < 2:
                raise ValueError("Allowed languages mode requires at least two language codes")
            out["language_code"] = ", ".join(parsed)
        return out

    def apply_dashboard_appearance(self, settings):
        self.appearance_var.set(normalize_appearance_mode((settings or {}).get("mode")))
        self.apply_appearance(persist=True)
        self.log_ui(f"Dashboard changed appearance to {self.appearance_var.get()}")

    def apply_dashboard_transcription(self, settings):
        if "model" in settings:
            self.transcription_model_var.set(settings["model"])
        if "language_mode" in settings:
            self.transcription_language_mode_var.set(settings["language_mode"])
        if "language_code" in settings:
            self.transcription_language_code_var.set(settings["language_code"])
        if "device" in settings:
            self.transcription_device_var.set(settings["device"])
        self.refresh_transcription_language_state()
        self.publish_dashboard_controls()
        self.log_ui("Dashboard updated transcription settings")

    def dashboard_queue_snapshot(self):
        items = [queue_item_to_dict(x) for x in self.batch_store.list_items()]
        current_id = str(getattr(self, "batch_current_id", "") or "")
        op = self.op_state.snapshot()
        running = self.batch_is_running()
        paused = bool(getattr(self, "batch_pause_requested", False))
        for item in items:
            if item.get("state") == "done":
                item["progress"] = 100.0
            elif item.get("state") == "running" and str(item.get("id")) == current_id:
                # During batch work the canonical foreground may be either the parent batch
                # operation or its active encode child. Both expose truthful monotonic progress.
                item["progress"] = float(op.get("overall_pct", 0.0) or 0.0)
            else:
                item["progress"] = 0.0
        recents = [{"label": x.get("label", ""), "video": x.get("video", ""), "saved_at": x.get("saved_at", 0)} for x in self.recents.get("projects", [])]
        return {"ok": True, "items": items, "running": running, "paused": paused, "current_id": current_id, "recents": recents}

    def queue_dashboard_queue_action(self, action):
        action = str(action or "").casefold().strip()
        if action not in {"add_current", "start", "pause", "cancel_current", "retry_all", "clear_completed", "clear_queued"}:
            return False, "Unknown queue action"
        self.events.put(("dashboard_queue_action", (action,)))
        return True, f"Queue {action.replace('_', ' ')} request queued"

    def apply_dashboard_queue_action(self, action):
        if action == "add_current":
            self.batch_add_current()
        elif action == "start":
            self.batch_start_queue()
        elif action == "pause":
            self.batch_pause_queue()
        elif action == "cancel_current":
            self.batch_cancel_current()
        elif action == "retry_all":
            self.batch_retry_all_failed()
        elif action == "clear_completed":
            self.batch_clear_completed()
        elif action == "clear_queued":
            self.batch_clear_queued()
        self.publish_dashboard_controls()

    def queue_dashboard_queue_item_action(self, action, payload):
        payload = payload if isinstance(payload, dict) else {}
        action = str(action or "").casefold().strip()
        if action == "add_recent":
            try:
                index = int(payload.get("index"))
            except Exception:
                return False, "Choose a valid recent project"
            if index < 0 or index >= len(self.recents.get("projects", [])):
                return False, "Recent project no longer exists"
            self.events.put(("dashboard_queue_item_action", (action, {"index": index})))
            return True, "Recent project queued for addition"
        if action == "add_custom":
            video = str(payload.get("video") or "").strip()
            subtitle = str(payload.get("subtitle") or "").strip()
            if not video or len(video) > 4096 or not Path(video).is_file() or Path(video).suffix.casefold() not in VIDEO_EXTS:
                return False, "Choose an existing supported video file"
            if subtitle and (len(subtitle) > 4096 or not Path(subtitle).is_file() or Path(subtitle).suffix.casefold() not in SUBTITLE_FILE_EXTS):
                return False, "Choose an existing supported subtitle file or leave it blank"
            self.events.put(("dashboard_queue_item_action", (action, {"video": video, "subtitle": subtitle})))
            return True, "Project queued for addition"
        if action in {"delete", "duplicate"}:
            item_id = str(payload.get("id") or "").strip()
            if not item_id or not self.batch_store.get(item_id):
                return False, "Queue item no longer exists"
            self.events.put(("dashboard_queue_item_action", (action, {"id": item_id})))
            return True, "Queue item action queued"
        if action == "delete_many":
            ids = [str(x).strip() for x in (payload.get("ids") or []) if str(x).strip()]
            if not ids or len(ids) > 500:
                return False, "Choose one or more queue items"
            self.events.put(("dashboard_queue_item_action", (action, {"ids": ids})))
            return True, f"Removal queued for {len(ids)} item(s)"
        return False, "Unknown queue item action"

    def apply_dashboard_queue_item_action(self, action, payload):
        payload = payload if isinstance(payload, dict) else {}
        if action == "add_recent":
            self.batch_add_recent_project(int(payload["index"]))
        elif action == "add_custom":
            self.batch_add_custom(payload.get("video", ""), payload.get("subtitle", ""))
        elif action == "delete":
            self.batch_remove_id(payload.get("id", ""))
        elif action == "delete_many":
            self.batch_remove_ids(payload.get("ids") or [])
        elif action == "duplicate":
            self.batch_duplicate_id(payload.get("id", ""))
        self.publish_dashboard_controls()

    def apply_dashboard_watermark(self, settings):
        if "timing" in settings:
            self.watermark_timing_var.set(settings["timing"])
        if "type" in settings:
            self.watermark_type_var.set(settings["type"])
        if "enabled" in settings:
            self.watermark_enabled_var.set(settings["enabled"])
        if "text" in settings:
            self.watermark_text_var.set(settings["text"])
        if "same_font" in settings:
            self.same_wm_font_var.set(settings["same_font"])
        if "font" in settings and (not settings["font"] or settings["font"] in self.font_map):
            self.wm_font_var.set(settings["font"])
        if "image" in settings:
            self.watermark_image_var.set(settings["image"])
        if "position" in settings:
            self.watermark_position_var.set(settings["position"])
        var_map = {
            "size": self.watermark_size_var,
            "opacity": self.watermark_opacity_var,
            "margin": self.watermark_margin_var,
            "outline": self.watermark_outline_var,
            "image_width": self.watermark_image_width_var,
            "image_scale": self.watermark_image_scale_var,
            "image_x": self.watermark_image_x_var,
            "image_y": self.watermark_image_y_var,
        }
        for key, var in var_map.items():
            if key in settings:
                var.set(settings[key])
        if "intervals" in settings:
            self.watermark_rows = list(settings["intervals"])
            tree = getattr(self, "interval_tree", None)
            if tree is not None and tree.winfo_exists():
                self.refresh_intervals()
        self.autosave_project()
        self.publish_dashboard_controls()
        self.log_ui("Dashboard updated watermark settings")
    def apply_dashboard_encoding(self, settings):
        var_map = {
            "mode": self.mode_var, "output_ext": self.output_ext_var, "codec": self.codec_var,
            "quality": self.quality_mode_var, "policy": self.encoder_policy_var, "speed": self.speed_mode_var,
            "resolution": self.resolution_var, "fps": self.fps_var, "audio": self.audio_mode_var,
            "encoder": self.encoder_var, "custom_bitrate": self.custom_bitrate_var, "target_size": self.target_size_var,
        }
        for key, var in var_map.items():
            if key in settings:
                var.set(settings[key])
        if "chapter" in settings:
            self.chapter_var.set(settings["chapter"])
        self.update_estimate()
        self.save_settings()
        self.publish_dashboard_controls()
        self.log_ui("Dashboard updated encoding settings")
    def apply_dashboard_subtitles(self, settings):
        var_map = {
            "primary_font": self.primary_font_var, "font_size": self.font_size_var, "outline": self.outline_var,
            "margin": self.margin_var, "safe_area": self.safe_area_var, "platform_safe_zone": self.platform_safe_zone_var, "wrap_chars": self.wrap_chars_var,
            "max_lines": self.max_lines_var, "offset_ms": self.subtitle_offset_var, "text_rgb": self.text_rgb_var,
            "outline_rgb": self.outline_rgb_var, "text_opacity": self.text_opacity_var, "outline_opacity": self.outline_opacity_var,
            "shadow_depth": self.shadow_depth_var, "shadow_rgb": self.shadow_rgb_var, "shadow_opacity": self.shadow_opacity_var,
            "letter_spacing": self.letter_spacing_var, "rotation_angle": self.rotation_angle_var, "subtitle_alignment": self.subtitle_alignment_var,
            "margin_left": self.margin_left_var, "margin_right": self.margin_right_var, "background_rgb": self.background_rgb_var,
            "background_opacity": self.background_opacity_var, "background_padding": self.background_padding_var,
        }
        for key, var in var_map.items():
            if key in settings:
                var.set(settings[key])
        bool_map = {"force_bold": self.force_bold_var, "italic": self.italic_var, "underline": self.underline_var, "strikeout": self.strikeout_var, "background_box": self.background_box_var}
        for key, var in bool_map.items():
            if key in settings:
                var.set(settings[key])
        if "caption_effect_id" in settings:
            self.caption_effect_var.set(CAPTION_EFFECT_ID_TO_LABEL.get(settings["caption_effect_id"], "None"))
        if "caption_effect_params" in settings:
            spec = CaptionEffectSpec(settings.get("caption_effect_id", CAPTION_EFFECT_LABEL_TO_ID.get(self.caption_effect_var.get(), "none")), settings["caption_effect_params"])
            self.caption_active_rgb_var.set(spec.params["active_rgb"])
            self.caption_estimated_timing_var.set(bool(spec.params["allow_estimated_timing"]))
        if "fallback_fonts" in settings and hasattr(self, "fallback_list"):
            self.fallback_list.delete(0, "end")
            for label in settings["fallback_fonts"]:
                self.fallback_list.insert("end", label)
        self.save_settings()
        self.publish_dashboard_controls()
        self.log_ui("Dashboard updated subtitle settings")
    def apply_dashboard_project(self, settings):
        old_video = self.video_var.get()
        old_ffmpeg = self.ffmpeg_var.get()
        if "ffmpeg" in settings:
            self.ffmpeg_var.set(settings["ffmpeg"])
        if "video" in settings:
            self.video_var.set(settings["video"])
            if settings["video"] != old_video and "output_name" not in settings and settings["video"]:
                self.output_name_var.set(safe_filename(Path(settings["video"]).stem + " - SubBurn"))
        if "subtitle_source" in settings:
            self.subtitle_source_var.set(settings["subtitle_source"])
        if "subtitle_file" in settings:
            self.subtitle_file_var.set(settings["subtitle_file"])
        if "embedded_track" in settings:
            self.embedded_track_var.set(settings["embedded_track"])
        if "output_dir" in settings:
            self.output_dir_var.set(settings["output_dir"])
        if "output_name" in settings:
            self.output_name_var.set(settings["output_name"])
        if "clean_output" in settings:
            self.clean_output_var.set(settings["clean_output"])
        if "metadata" in settings:
            for key in USER_METADATA_KEYS:
                self.metadata_vars[key].set(settings["metadata"].get(key, ""))
        self.autosave_project()
        self.save_settings()
        self.publish_dashboard_controls()
        self.log_ui("Dashboard updated project settings")
        if settings.get("video") and settings["video"] != old_video:
            self.analyze_async()
        if settings.get("ffmpeg") and settings["ffmpeg"] != old_ffmpeg:
            path = settings["ffmpeg"]
            def worker():
                try:
                    caps = inspect_toolset(Path(path))
                    self.emit("tool", caps, [caps])
                except Exception as e:
                    self.emit("error", f"FFmpeg inspection failed: {e}")
            self.start_operation_thread("ffmpeg_inspect", worker)
    def apply_dashboard_action(self, action):
        if action == "discover_tools":
            self.log_ui("Dashboard requested FFmpeg auto-detect")
            self.discover_tools_async()
        elif action == "download_runtime":
            self.log_ui("Dashboard requested compatible runtime download")
            self.download_ffmpeg_async()
        elif action == "analyze":
            self.log_ui("Dashboard requested media analysis")
            self.analyze_async()
        elif action == "validate":
            self.log_ui("Dashboard requested subtitle/font validation")
            self.validate_async()
        elif action == "probe":
            self.log_ui("Dashboard requested quick encoder probe")
            self.probe_encoders_async()
        elif action == "benchmark":
            self.log_ui("Dashboard requested encoder benchmark")
            self.benchmark_async()
        elif action == "preview":
            self.log_ui("Dashboard requested preview")
            self.preview_async()
        elif action == "compare":
            self.log_ui("Dashboard requested quality comparison")
            self.compare_preview_async()
        elif action == "encode":
            self.log_ui("Dashboard requested encode")
            if self.running:
                self.log_ui("Encode request ignored: an encode is already running")
            else:
                self.start_encode()
        elif action == "pause":
            self.log_ui("Dashboard requested pause")
            self.pause_encode()
        elif action == "resume":
            self.log_ui("Dashboard requested resume")
            self.resume_encode()
        elif action == "cancel":
            self.log_ui("Dashboard requested cancel")
            self.cancel_encode()
        elif action == "batch_start":
            self.log_ui("Automation requested batch start/resume")
            self.batch_start_queue()
        elif action == "batch_pause":
            self.log_ui("Automation requested batch pause")
            self.batch_pause_queue()
        elif action == "batch_cancel":
            self.log_ui("Automation requested current batch cancellation")
            self.batch_cancel_current()
        elif action == "transcription_prepare":
            self.log_ui("Dashboard requested transcription model preparation")
            self.prepare_transcription_model_async()
        elif action == "transcription_start":
            self.log_ui("Dashboard requested transcription")
            self.start_transcription_async()
        elif action == "transcription_cancel":
            self.log_ui("Dashboard requested transcription cancellation")
            self.cancel_transcription()
        elif action == "refresh_fonts":
            self.log_ui("Dashboard requested font refresh")
            self.scan_fonts_async()
        elif action == "diagnostics":
            self.log_ui("Dashboard requested diagnostics export")
            self.export_diagnostics()
        elif action == "open_file":
            self.log_ui("Dashboard requested last output file")
            self.open_last_output()
        elif action == "open_folder":
            self.log_ui("Dashboard requested last output folder")
            self.open_last_folder()
        elif action == "restore_recovery":
            self.log_ui("Dashboard requested last autosave restore")
            self.restore_recovery()
        elif action == "browser_only":
            self.enter_browser_only(open_browser=False)
        elif action == "show_window":
            self.show_desktop_window()
        elif action == "exit_app":
            self.log_ui("Dashboard requested SubBurn exit")
            self.root.after(0, self.request_exit)
    def apply_dashboard_live_frame(self, timestamp):
        if not self.media:
            self.error_ui("Analyze media before rendering a live preview frame")
            return
        if timestamp > self.live_timestamp_limit() + 0.001:
            self.error_ui("Live preview timestamp is outside the renderable video range")
            return
        self.log_ui(f"Dashboard requested live frame at {fmt_time(timestamp)}")
        self.live_frame_async(timestamp)
    def apply_dashboard_interval_preview(self, index):
        if not self.watermark_enabled_var.get() or self.watermark_timing_var.get() != "Intervals":
            self.error_ui("Boundary preview requires watermark Intervals mode")
            return
        if index < 0 or index >= len(self.watermark_rows):
            self.error_ui("Selected watermark interval no longer exists")
            return
        self.log_ui(f"Dashboard requested boundary preview for interval {index + 1}")
        self.preview_interval_async(index)
    def apply_dashboard_font_import(self, raw_path):
        try:
            self.import_font_path(raw_path)
        except Exception as e:
            self.error_ui(f"Font import failed: {e}")
    def log_ui(self, text):
        line = f"[{time.strftime('%H:%M:%S')}] {text}\n"
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.op_state.add_log(text)
    def error_ui(self, text):
        self.log_ui("ERROR: " + text)
        self.status_var.set("Error")
        self.op_state.set_status("Error")
    def warning_ui(self, text):
        self.log_ui("WARNING: " + text)
        self.status_var.set("Warning: " + str(text))
        self.op_state.set_status("Warning: " + str(text))
    def emit_missing_glyph_warning(self, missing):
        if not missing:
            return
        sample = ", ".join(f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNKNOWN')}" for ch in missing[:8])
        more = f" +{len(missing) - 8} more" if len(missing) > 8 else ""
        self.emit("warning", f"Missing glyphs in the selected font/fallback chain ({len(missing)}): {sample}{more}. Add a fallback font that contains these characters.")
    def apply_progress(self, pct, fps, speed, eta):
        snap = self.op_state.snapshot()
        transfer = snap.get("metric_profile") == "transfer"
        progress_mode = "determinate" if transfer and int(snap.get("bytes_total", 0) or 0) > 0 else snap.get("progress_mode")
        self._set_progressbar_state(getattr(self, "global_progress_bar", None), "_global_progress_mode", progress_mode, self.progress_var, snap.get("progress_pct", snap.get("overall_pct", 0.0)))
        if hasattr(self, "progress_status_var"):
            numeric_known = progress_mode == "determinate"
            if numeric_known:
                self.progress_status_var.set(("Download: " if transfer else "Progress: ") + f"{float(snap.get('transfer_pct' if transfer else 'progress_pct', 0.0) or 0.0):.1f}%")
            else:
                self.progress_status_var.set(("Download: " if transfer else "Progress: ") + "-")
        self.fps_status_var.set(f"FPS: {snap.get('fps', fps)}")
        self.speed_status_var.set(("Transfer speed: " if transfer else "Speed: ") + str(snap.get('speed', speed)))
        self.transfer_status_var.set(f"Downloaded: {snap.get('downloaded', '-')}")
        self.eta_var.set(("Remaining: " if transfer else "ETA: ") + str(snap.get('eta', eta)))
        if getattr(self, "batch_current_id", None):
            self.refresh_batch_tree()
    def copy_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
    def copy_log(self):
        self.copy_text(self.log_text.get("1.0", "end").strip())
    def load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        keys = {"ffmpeg": self.ffmpeg_var, "appearance": self.appearance_var, "output_dir": self.output_dir_var, "output_ext": self.output_ext_var, "font": self.primary_font_var, "mode": self.mode_var, "codec": self.codec_var, "quality": self.quality_mode_var, "speed": self.speed_mode_var, "audio": self.audio_mode_var}
        for k, var in keys.items():
            if k in data:
                try:
                    value = normalize_codec_mode(data[k]) if k == "codec" else (normalize_appearance_mode(data[k]) if k == "appearance" else data[k])
                    if k == "output_dir":
                        raw = str(value or "").strip()
                        legacy_default = str(Path.home() / "Videos")
                        if not raw or os.path.normcase(os.path.normpath(raw)) == os.path.normcase(os.path.normpath(legacy_default)):
                            value = str(SUBBURN_OUTPUT_DIR)
                    var.set(value)
                except Exception:
                    pass
    def save_settings(self):
        data = {"ffmpeg": self.ffmpeg_var.get(), "appearance": normalize_appearance_mode(self.appearance_var.get()), "output_dir": self.output_dir_var.get(), "output_ext": self.output_ext_var.get(), "font": self.primary_font_var.get(), "mode": self.mode_var.get(), "codec": self.codec_var.get(), "quality": self.quality_mode_var.get(), "speed": self.speed_mode_var.get(), "audio": self.audio_mode_var.get()}
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, SETTINGS_FILE)
    def load_recents(self):
        try:
            data = json.loads(RECENTS_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError
            projects = data.get("projects") if isinstance(data.get("projects"), list) else []
            folders = data.get("folders") if isinstance(data.get("folders"), list) else []
            projects = [x for x in projects if isinstance(x, dict) and isinstance(x.get("state"), dict)][:12]
            folders = [str(x) for x in folders if str(x).strip()][:20]
            return {"projects": projects, "folders": folders}
        except Exception:
            return {"projects": [], "folders": []}
    def save_recents(self):
        RECENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = RECENTS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.recents, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, RECENTS_FILE)
    def record_recent_state(self, state):
        project = state.get("project") or {}
        video = str(project.get("video") or "").strip()
        if video:
            key = video.casefold()
            existing = [x for x in self.recents.get("projects", []) if str(x.get("video", "")).casefold() != key]
            label = str(project.get("output_name") or Path(video).stem or Path(video).name)
            entry = {"label": label, "video": video, "saved_at": state.get("saved_at", time.time()), "state": state}
            self.recents["projects"] = [entry] + existing[:11]
        folders = list(self.recents.get("folders", []))
        candidates = []
        for key in ("video", "subtitle_file"):
            raw = str(project.get(key) or "").strip()
            if raw:
                candidates.append(str(Path(raw).parent))
        raw_out = str(project.get("output_dir") or "").strip()
        if raw_out:
            candidates.append(raw_out)
        for folder in reversed(candidates):
            folders = [x for x in folders if x.casefold() != folder.casefold()]
            folders.insert(0, folder)
        self.recents["folders"] = folders[:20]
        self.save_recents()
        self.refresh_recents_ui()
    def refresh_recents_ui(self):
        if hasattr(self, "recent_projects_list"):
            self.recent_projects_list.delete(0, "end")
            for item in self.recents.get("projects", []):
                self.recent_projects_list.insert("end", item.get("label") or item.get("video") or "Recent project")
        if hasattr(self, "recent_folders_list"):
            self.recent_folders_list.delete(0, "end")
            for folder in self.recents.get("folders", []):
                self.recent_folders_list.insert("end", folder)
    def clear_recent_projects(self):
        self.recents["projects"] = []
        self.save_recents(); self.refresh_recents_ui(); self.publish_dashboard_controls()
        self.log_ui("Recent projects cleared")
    def clear_recent_folders(self):
        self.recents["folders"] = []
        self.save_recents(); self.refresh_recents_ui(); self.publish_dashboard_controls()
        self.log_ui("Recent folders cleared")
    def queue_clear_recents(self, kind):
        kind = str(kind or "").casefold().strip()
        if kind not in {"projects", "folders"}:
            return False, "Choose projects or folders"
        self.events.put(("clear_recents", (kind,)))
        return True, f"Clear recent {kind} queued"
    def apply_clear_recents(self, kind):
        if kind == "projects": self.clear_recent_projects()
        elif kind == "folders": self.clear_recent_folders()
    def restore_selected_recent_project(self):
        if not hasattr(self, "recent_projects_list"):
            return
        sel = self.recent_projects_list.curselection()
        if sel:
            self.apply_recent_project_restore(int(sel[0]))
    def use_selected_recent_folder(self):
        if not hasattr(self, "recent_folders_list"):
            return
        sel = self.recent_folders_list.curselection()
        if sel:
            self.output_dir_var.set(self.recents.get("folders", [])[int(sel[0])])
    def queue_recent_project_restore(self, index):
        if isinstance(index, bool):
            return False, "Choose a valid recent project"
        try:
            index = int(index)
        except Exception:
            return False, "Choose a valid recent project"
        if index < 0 or index >= len(self.recents.get("projects", [])):
            return False, "Recent project no longer exists"
        self.events.put(("recent_project_restore", (index,)))
        return True, f"Recent project {index + 1} restore queued"
    def apply_recent_project_restore(self, index):
        projects = self.recents.get("projects", [])
        if index < 0 or index >= len(projects):
            self.error_ui("Recent project no longer exists")
            return False
        self.log_ui(f"Restoring recent project: {projects[index].get('label') or projects[index].get('video')}")
        return self.restore_recovery(projects[index].get("state"))
    def recovery_payload(self):
        snap = self.dashboard_control_snapshot()
        allowed = {
            "project": {"ffmpeg", "video", "subtitle_source", "subtitle_file", "embedded_track", "output_dir", "output_name", "clean_output", "metadata"},
            "watermark": {"enabled", "timing", "type", "text", "same_font", "font", "image", "position", "size", "opacity", "margin", "outline", "image_width", "image_scale", "image_x", "image_y", "intervals"},
            "encoding": {"mode", "output_ext", "codec", "quality", "policy", "speed", "resolution", "fps", "audio", "encoder", "custom_bitrate", "target_size", "chapter"},
            "subtitles": {"primary_font", "fallback_fonts", "font_size", "outline", "margin", "safe_area", "platform_safe_zone", "wrap_chars", "max_lines", "offset_ms", "text_rgb", "outline_rgb", "force_bold", "italic", "underline", "strikeout", "text_opacity", "outline_opacity", "shadow_depth", "shadow_rgb", "shadow_opacity", "letter_spacing", "rotation_angle", "subtitle_alignment", "margin_left", "margin_right", "background_box", "background_rgb", "background_opacity", "background_padding", "caption_effect_id", "caption_effect_params"},
        }
        data = {"schema": 4, "saved_at": time.time()}
        for panel, keys in allowed.items():
            source = snap.get(panel) or {}
            data[panel] = {key: source[key] for key in keys if key in source}
        return data
    def install_autosave_traces(self):
        vars_to_watch = [
            self.ffmpeg_var, self.video_var, self.subtitle_source_var, self.subtitle_file_var, self.embedded_track_var,
            self.output_dir_var, self.output_name_var, self.output_ext_var, self.clean_output_var, self.primary_font_var,
            self.same_wm_font_var, self.wm_font_var, self.font_size_var, self.force_bold_var, self.italic_var, self.underline_var, self.strikeout_var,
            self.text_opacity_var, self.outline_opacity_var, self.shadow_depth_var, self.shadow_rgb_var, self.shadow_opacity_var,
            self.letter_spacing_var, self.rotation_angle_var, self.subtitle_alignment_var, self.margin_left_var, self.margin_right_var,
            self.background_box_var, self.background_rgb_var, self.background_opacity_var, self.background_padding_var, self.caption_effect_var, self.caption_active_rgb_var, self.caption_estimated_timing_var, self.outline_var,
            self.margin_var, self.text_rgb_var, self.outline_rgb_var, self.safe_area_var, self.platform_safe_zone_var, self.wrap_chars_var,
            self.max_lines_var, self.subtitle_offset_var, self.watermark_enabled_var, self.watermark_type_var,
            self.watermark_text_var, self.watermark_image_var, self.watermark_timing_var, self.watermark_position_var,
            self.watermark_size_var, self.watermark_opacity_var, self.watermark_margin_var, self.watermark_outline_var,
            self.watermark_image_width_var, self.watermark_image_scale_var, self.watermark_image_x_var, self.watermark_image_y_var, self.codec_var, self.quality_mode_var, self.speed_mode_var,
            self.encoder_policy_var, self.encoder_var, self.custom_bitrate_var, self.target_size_var, self.resolution_var,
            self.fps_var, self.audio_mode_var, self.chapter_var, self.mode_var,
        ]
        vars_to_watch.extend(self.metadata_vars.values())
        for var in vars_to_watch:
            var.trace_add("write", self.schedule_autosave)
    def schedule_autosave(self, *_args):
        try:
            if self._autosave_after is not None:
                self.root.after_cancel(self._autosave_after)
            self._autosave_after = self.root.after(400, self.autosave_project)
        except Exception:
            self._autosave_after = None
    def autosave_project(self):
        self._autosave_after = None
        data = self.recovery_payload()
        RECOVERY_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = RECOVERY_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, RECOVERY_FILE)
        self.record_recent_state(data)
        if hasattr(self, "restore_recovery_btn"):
            try:
                self.restore_recovery_btn.configure(state="normal")
            except Exception:
                pass
    def read_recovery_payload(self):
        raw = json.loads(RECOVERY_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Autosave is not a JSON object")
        if raw.get("schema") in {2, 3, 4} and all(isinstance(raw.get(x), dict) for x in ("project", "watermark", "encoding", "subtitles")):
            return raw
        project = {key: raw[key] for key in ("video", "subtitle_source", "subtitle_file", "embedded_track", "output_dir", "output_name") if key in raw}
        rows = []
        for row in raw.get("watermark_rows") or []:
            if isinstance(row, (list, tuple)) and len(row) == 3:
                rows.append({"start": row[0], "end": row[1], "position": row[2]})
        return {"schema": 1, "saved_at": 0, "project": project, "watermark": {"intervals": rows}, "encoding": {}, "subtitles": {}}
    def restore_recovery(self, data=None):
        try:
            if data is None:
                data = self.read_recovery_payload()
            self.publish_dashboard_controls()
            project = dict(data.get("project") or {})
            for key in ("ffmpeg", "video", "subtitle_file"):
                value = project.get(key)
                if value and not Path(value).is_file():
                    self.log_ui(f"Recovery skipped missing {key}: {value}")
                    project.pop(key, None)
            if project.get("subtitle_source") == "Embedded":
                options = (self.op_state.control_snapshot().get("project") or {}).get("embedded_options") or []
                if project.get("embedded_track") not in options:
                    project["subtitle_source"] = "Auto"
                    project.pop("embedded_track", None)
            if project:
                self.apply_dashboard_project(self.normalize_dashboard_project(project))
            self.publish_dashboard_controls()
            subtitles = dict(data.get("subtitles") or {})
            font_options = list(self.font_map.keys())
            if subtitles.get("primary_font") and subtitles["primary_font"] not in font_options:
                subtitles.pop("primary_font", None)
            if "fallback_fonts" in subtitles:
                subtitles["fallback_fonts"] = [x for x in subtitles["fallback_fonts"] if x in font_options]
            if subtitles:
                self.apply_dashboard_subtitles(self.normalize_dashboard_subtitles(subtitles))
            self.publish_dashboard_controls()
            watermark = dict(data.get("watermark") or {})
            if int(data.get("schema") or 0) < 3 and "opacity" in watermark:
                try:
                    legacy_opacity = float(watermark["opacity"])
                    if 0.0 <= legacy_opacity <= 1.0:
                        watermark["opacity"] = f"{legacy_opacity * 100:g}"
                except Exception:
                    pass
            if int(data.get("schema") or 0) < 4 and watermark.get("type") == "Image":
                watermark.setdefault("image_scale", "100")
                watermark.setdefault("image_x", "")
                watermark.setdefault("image_y", "")
            if watermark.get("font") and watermark["font"] not in self.font_map:
                watermark.pop("font", None)
            if watermark.get("type") == "Image" and watermark.get("image") and not Path(watermark["image"]).is_file():
                self.log_ui(f"Recovery disabled missing watermark image: {watermark['image']}")
                watermark["enabled"] = False
                watermark["image"] = ""
            if watermark:
                self.apply_dashboard_watermark(self.normalize_dashboard_watermark(watermark))
            self.publish_dashboard_controls()
            encoding = dict(data.get("encoding") or {})
            available_encoders = (self.op_state.control_snapshot().get("encoding") or {}).get("encoder_options") or ["Auto"]
            if encoding.get("encoder") not in available_encoders:
                encoding["encoder"] = "Auto"
            if encoding:
                self.apply_dashboard_encoding(self.normalize_dashboard_encoding(encoding))
            self.publish_dashboard_controls()
            self.autosave_project()
            self.log_ui("Last autosave restored")
            return True
        except Exception as e:
            self.error_ui(f"Recovery restore failed: {e}")
            return False
    def _inspect_selected_ffmpeg_async(self, selected_path):
        selected_path = str(selected_path or "").strip()
        if not selected_path:
            return False
        self.ffmpeg_var.set(selected_path)
        def worker():
            try:
                scan = scan_local_toolsets(selected_path)
                caps = scan.get("usable")
                if caps is None:
                    rejected = list(scan.get("rejected") or [])
                    detail = rejected[0][1] if rejected else "no compatible FFmpeg/FFprobe pair found"
                    raise RuntimeError(detail)
                self.emit("tool", caps, list(scan.get("usable_candidates") or [caps]))
            except Exception as e:
                self.emit("error", f"FFmpeg inspection failed: {e}")
        self.start_operation_thread("ffmpeg_inspect", worker)
        return True
    def browse_ffmpeg(self):
        if not self.require_batch_idle("FFmpeg selection"):
            return False
        p = filedialog.askopenfilename(title="Select FFmpeg executable", filetypes=[("FFmpeg", "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"), ("All files", "*.*")])
        return self._inspect_selected_ffmpeg_async(p) if p else False
    def browse_ffmpeg_folder(self):
        if not self.require_batch_idle("FFmpeg selection"):
            return False
        p = filedialog.askdirectory(title="Select FFmpeg folder")
        return self._inspect_selected_ffmpeg_async(p) if p else False
    def snapshot_job(self):
        job = BurnJob()
        job.ffmpeg = self.ffmpeg_var.get()
        job.primary_font = self.primary_font_var.get()
        job.same_wm_font = self.same_wm_font_var.get()
        job.wm_font = self.wm_font_var.get()
        job.video = self.video_var.get()
        job.embedded_track = self.embedded_track_var.get()
        job.subtitle_file = self.subtitle_file_var.get()
        job.subtitle_offset = self.subtitle_offset_var.get()
        job.subtitle_source = self.subtitle_source_var.get()
        job.watermark_enabled = self.watermark_enabled_var.get()
        job.watermark_image = self.watermark_image_var.get()
        job.watermark_text = self.watermark_text_var.get()
        job.watermark_type = self.watermark_type_var.get()
        job.font_size = self.font_size_var.get()
        job.force_bold = self.force_bold_var.get()
        job.italic = self.italic_var.get()
        job.underline = self.underline_var.get()
        job.strikeout = self.strikeout_var.get()
        job.text_opacity = self.text_opacity_var.get()
        job.outline_opacity = self.outline_opacity_var.get()
        job.shadow_depth = self.shadow_depth_var.get()
        job.shadow_rgb = self.shadow_rgb_var.get()
        job.shadow_opacity = self.shadow_opacity_var.get()
        job.letter_spacing = self.letter_spacing_var.get()
        job.rotation_angle = self.rotation_angle_var.get()
        job.subtitle_alignment = self.subtitle_alignment_var.get()
        job.margin_left = self.margin_left_var.get()
        job.margin_right = self.margin_right_var.get()
        job.background_box = self.background_box_var.get()
        job.background_rgb = self.background_rgb_var.get()
        job.background_opacity = self.background_opacity_var.get()
        job.background_padding = self.background_padding_var.get()
        job.caption_effect_id = CAPTION_EFFECT_LABEL_TO_ID.get(self.caption_effect_var.get(), "none")
        job.caption_effect_params = CaptionEffectSpec(job.caption_effect_id, {"active_rgb": self.caption_active_rgb_var.get(), "allow_estimated_timing": self.caption_estimated_timing_var.get()}).params
        job.fps = self.fps_var.get()
        job.margin = self.margin_var.get()
        job.outline_rgb = self.outline_rgb_var.get()
        job.outline = self.outline_var.get()
        job.resolution = self.resolution_var.get()
        job.safe_area = self.safe_area_var.get()
        job.text_rgb = self.text_rgb_var.get()
        job.watermark_image_width = self.watermark_image_width_var.get()
        job.watermark_image_scale = self.watermark_image_scale_var.get()
        job.watermark_image_x = self.watermark_image_x_var.get().strip()
        job.watermark_image_y = self.watermark_image_y_var.get().strip()
        job.watermark_margin = self.watermark_margin_var.get()
        opacity_percent = float(self.watermark_opacity_var.get())
        if opacity_percent < 0.0 or opacity_percent > 100.0:
            raise RuntimeError("Watermark opacity must be between 0% and 100%")
        job.watermark_opacity = opacity_percent / 100.0
        job.watermark_outline = self.watermark_outline_var.get()
        job.watermark_position = self.watermark_position_var.get()
        job.watermark_size = self.watermark_size_var.get()
        job.watermark_timing = self.watermark_timing_var.get()
        job.audio_mode = self.audio_mode_var.get()
        job.custom_bitrate = self.custom_bitrate_var.get()
        job.quality_mode = self.quality_mode_var.get()
        job.target_size = self.target_size_var.get()
        job.codec = normalize_codec_mode(self.codec_var.get())
        job.output_ext = self.output_ext_var.get()
        job.speed_mode = self.speed_mode_var.get()
        job.encoder_policy = self.encoder_policy_var.get()
        job.encoder = self.encoder_var.get()
        job.clean_output = self.clean_output_var.get()
        job.output_dir = self.output_dir_var.get()
        job.output_name = self.output_name_var.get()
        job.metadata = {key: self.metadata_vars[key].get().strip() for key in USER_METADATA_KEYS}
        job.chapter = self.chapter_var.get()
        job.wrap_chars = self.wrap_chars_var.get()
        job.max_lines = self.max_lines_var.get()
        job.fallback_labels = list(self.fallback_list.get(0, "end")) if hasattr(self, "fallback_list") else []
        job.watermark_rows = [tuple(row) for row in self.watermark_rows]
        tree = getattr(self, "interval_tree", None)
        if tree is not None and tree.winfo_exists():
            sel = tree.selection()
            job.selected_interval_idx = int(tree.item(sel[0], "tags")[0]) if sel else None
        else:
            job.selected_interval_idx = None
        return job
    def run_job(self, target, job=None, *, operation_type="generic", operation_label=None, priority=None, mode=None):
        if job is None:
            job = self.snapshot_job()
        op_id = self.begin_operation(operation_type, operation_label, priority=priority, mode=mode)
        def worker():
            self._job_local.job = job
            self._operation_local.operation_id = op_id
            result = None
            try:
                result = target()
                return result
            except Exception as exc:
                self.finish_operation(op_id, "failed", error=str(exc))
                raise
            finally:
                self._finish_operation_from_result(op_id, result)
                try:
                    del self._job_local.job
                except Exception:
                    pass
                try:
                    del self._operation_local.operation_id
                except Exception:
                    pass
        try:
            thread = self.start_tracked_thread(worker)
            thread.subburn_operation_id = op_id
            return thread
        except Exception as exc:
            self.finish_operation(op_id, "failed", error=str(exc))
            raise
    def start_operation_thread(self, kind, target, *, label=None, priority=None, mode=None):
        op_id = self.begin_operation(kind, label, priority=priority, mode=mode)
        def worker():
            self._operation_local.operation_id = op_id
            result = None
            try:
                result = target()
                return result
            except Exception as exc:
                self.finish_operation(op_id, "failed", error=str(exc))
                raise
            finally:
                self._finish_operation_from_result(op_id, result)
                try:
                    del self._operation_local.operation_id
                except Exception:
                    pass
        try:
            thread = self.start_tracked_thread(worker)
            thread.subburn_operation_id = op_id
            return thread
        except Exception as exc:
            self.finish_operation(op_id, "failed", error=str(exc))
            raise
    def active_job_count(self):
        with self.active_jobs_lock:
            return self.active_jobs
    def start_tracked_thread(self, target):
        with self.active_jobs_lock:
            self.active_jobs += 1
        def runner():
            try:
                target()
            finally:
                with self.active_jobs_lock:
                    self.active_jobs = max(0, self.active_jobs - 1)
        thread = threading.Thread(target=runner, daemon=True)
        try:
            thread.start()
        except Exception:
            with self.active_jobs_lock:
                self.active_jobs = max(0, self.active_jobs - 1)
            raise
        return thread
    def _transfer_progress_callback(self, label):
        started = time.monotonic()
        last_done = 0
        last_time = started
        last_emit_at = -1e9
        last_emit_done = -1
        ema_rate = 0.0
        origin_done = 0
        phase_name = "Model download" if "model" in str(label).casefold() else "FFmpeg download"
        def report(done, total):
            nonlocal started, last_done, last_time, last_emit_at, last_emit_done, ema_rate, origin_done
            now = time.monotonic()
            done = max(0, int(done or 0)); total = max(0, int(total or 0))
            if done < last_done:
                started = now; last_time = now; last_done = 0; origin_done = done; ema_rate = 0.0
                last_emit_at = -1e9; last_emit_done = -1
            dt = max(1e-6, now - last_time)
            delta = max(0, done - last_done)
            instant = float(delta) / dt if delta > 0 else 0.0
            transfer_elapsed = max(0.0, now - started)
            if instant > 0:
                ema_rate = instant if ema_rate <= 0 else (0.20 * instant + 0.80 * ema_rate)
            stable_rate = ema_rate if transfer_elapsed >= 0.75 else 0.0
            if transfer_elapsed >= 1.5 and done > origin_done:
                average_rate = float(done - origin_done) / transfer_elapsed
                stable_rate = average_rate if stable_rate <= 0 else (0.55 * stable_rate + 0.45 * average_rate)
            pct = (min(100.0, float(done) * 100.0 / float(total)) if total > 0 else None)
            eta = ((total - done) / stable_rate) if total > done and stable_rate > 0 else (0.0 if total > 0 and done >= total else None)
            if total > 0:
                message = f"Downloading {label} - {human_bytes(done)} of {human_bytes(total)} downloaded."
            else:
                message = f"Downloading {label} - {human_bytes(done)} downloaded."

            # urlretrieve can invoke reporthook thousands of times for one archive.  Queueing two
            # Tk events per 8 KiB block made the displayed progress minutes behind reality.
            # Keep rate estimation at source cadence but publish UI state at <= 8 Hz, plus the
            # first and final observations.
            terminal = total > 0 and done >= total
            first = last_emit_done < 0
            should_emit = first or terminal or (now - last_emit_at) >= 0.125
            if should_emit:
                op_id = self.current_operation_id()
                if op_id:
                    self.op_state.stage(op_id, phase_name, pct or 0.0, message)
                self.emit("transfer_progress", pct, done, total, stable_rate, eta, message)
                last_emit_at = now; last_emit_done = done
            last_done, last_time = done, now
        return report

    def _runtime_phase_callback(self):
        def report(message):
            text = str(message or "").strip()
            if text:
                lower = text.casefold()
                if lower.startswith("checking the publisher sha-256"):
                    self.set_stage("FFmpeg download", 0, text)
                elif lower.startswith("downloading one verified ffmpeg"):
                    self.set_stage("FFmpeg download", 0, text)
                elif "download verified" in lower:
                    self.set_stage("FFmpeg install", 0, text)
                elif lower.startswith("extracting"):
                    self.set_stage("FFmpeg install", 20, text)
                elif lower.startswith("installing"):
                    self.set_stage("FFmpeg install", 70, text)
                elif "installed and ready" in lower:
                    self.set_stage("FFmpeg install", 99, text)
                self.emit("status", text)
                self.emit("log", text)
        return report

    def _resolve_ffmpeg(self, *, allow_managed_install=True, explicit_install=False, saved_path=""):
        """Return a usable FFmpeg toolset without racing UI event application.

        All automatic discovery/download paths share this boundary.  The in-process lock prevents
        startup discovery and Analyze from independently deciding that FFmpeg is missing; the
        installer itself also has a cross-process lock and re-checks the installed runtime after
        acquiring it.
        """
        with self.ffmpeg_setup_lock:
            job = self._job
            saved = str(saved_path or (getattr(job, "ffmpeg", "") if job is not None else "") or "")
            best, found, rejected = scan_local_toolsets(saved)
            if best is not None:
                if IS_WINDOWS:
                    try:
                        if Path(best.ffmpeg).resolve() == managed_ffmpeg_executable().resolve():
                            promote_managed_ffmpeg_to_user_path(best)
                            self.emit("log", "Reused verified managed FFmpeg/FFprobe and promoted it to the front of the Windows user PATH.")
                    except Exception as path_exc:
                        self.emit("warning", f"Managed FFmpeg is reusable, but Windows PATH could not be updated automatically: {path_exc}")
                return best, found, False
            if rejected:
                for path, reason in rejected:
                    self.emit("log", f"FFmpeg candidate rejected: {path} - {reason}")
            if not allow_managed_install:
                raise RuntimeError("No compatible FFmpeg with subtitle rendering support is available")
            if not explicit_install and self._automatic_ffmpeg_install_attempted:
                raise RuntimeError("No compatible FFmpeg is ready. Automatic managed-runtime installation was already attempted this session; use Settings to retry explicitly.")
            if not explicit_install:
                self._automatic_ffmpeg_install_attempted = True
            if found:
                primary = str(found[0].ffmpeg)
                detail = "required subtitle/libass rendering support is missing"
                reason = "Your installed FFmpeg cannot render subtitles, so SubBurn is downloading a verified FFmpeg Essentials runtime once (~100 MB)."
                log_reason = f"FFmpeg candidate needs managed fallback: {primary} - {detail}. {reason}"
            elif rejected:
                primary, detail = rejected[0]
                reason = "Your installed FFmpeg is incompatible, so SubBurn is downloading a verified FFmpeg Essentials runtime once (~100 MB)."
                log_reason = f"FFmpeg candidate rejected: {primary} - {detail}. {reason}"
            else:
                reason = "No compatible FFmpeg was found, so SubBurn is downloading a verified FFmpeg Essentials runtime once (~100 MB) for subtitle rendering."
                log_reason = reason + " Searched PATH/system locations first, then the user-selected location, then the previously managed runtime."
            self.set_stage("FFmpeg download", 0, reason)
            self.emit("status", reason)
            self.emit("log", log_reason)
            caps = download_private_ffmpeg(
                self._transfer_progress_callback("FFmpeg runtime"),
                phase=self._runtime_phase_callback(),
            )
            if IS_WINDOWS:
                try:
                    promote_managed_ffmpeg_to_user_path(caps)
                    self.emit("log", "Verified SubBurn FFmpeg/FFprobe runtime promoted to the front of the Windows user PATH; existing package-manager/project binaries were left intact.")
                except Exception as path_exc:
                    self.emit("warning", f"FFmpeg is installed and SubBurn will use it, but Windows PATH could not be updated automatically: {path_exc}")
            merged = list(found)
            if not any(str(x.ffmpeg) == str(caps.ffmpeg) for x in merged):
                merged.append(caps)
            return caps, merged, True

    def discover_tools_async(self):
        if not self.require_batch_idle("FFmpeg discovery"):
            return None
        return self.run_job(self.discover_tools, operation_type="tool_discovery")
    def discover_tools(self):
        try:
            self.set_stage("Tools", 10, "Checking installed FFmpeg")
            self.emit("status", "Checking installed FFmpeg")
            best, found, installed = self._resolve_ffmpeg(allow_managed_install=True, explicit_install=False)
            message = "Managed FFmpeg installed and ready" if installed else "Using installed compatible FFmpeg"
            self.set_stage("Tools", 100, message)
            self.emit("status", message)
            self.emit("tool", best, found)
            return best
        except Exception as e:
            self.emit("error", f"FFmpeg setup failed: {e}")
            return None
    def download_ffmpeg_async(self):
        if not self.require_batch_idle("FFmpeg runtime download"):
            return None
        saved_path = str(self.ffmpeg_var.get() or "")
        return self.start_operation_thread("runtime_download", lambda: self.download_ffmpeg_worker(saved_path))
    def download_ffmpeg_worker(self, saved_path=""):
        try:
            caps, found, installed = self._resolve_ffmpeg(allow_managed_install=True, explicit_install=True, saved_path=saved_path)
            message = "Managed FFmpeg installed and ready" if installed else "Compatible FFmpeg is already installed; no download was needed"
            self.emit("status", message)
            self.emit("log", message)
            self.emit("tool", caps, found)
            return caps
        except Exception as e:
            self.emit("error", f"Runtime setup failed: {e}")
            return None
    def apply_toolset(self, caps, found):
        self.toolset = caps
        self.local_toolsets = found
        self.ffmpeg_var.set(str(caps.ffmpeg))
        self.help_cache.clear()
        self.benchmark_scores.clear()
        self.tuning_cache.clear()
        values = ["Auto"] + caps.encoders
        self.encoder_combo["values"] = values
        if self.encoder_var.get() not in values:
            self.encoder_var.set("Auto")
        flags = []
        for name in ("subtitles", "drawtext", "overlay", "colorchannelmixer"):
            flags.append(f"{name} {'yes' if name in caps.filters else 'no'}")
        self.tool_var.set(f"{caps.version} | " + " | ".join(flags) + f" | encoders {len(caps.encoders)}")
        selected_path = Path(caps.ffmpeg)
        managed_path = managed_ffmpeg_executable()
        try:
            is_managed = selected_path.resolve() == managed_path.resolve()
        except Exception:
            is_managed = str(selected_path).casefold() == str(managed_path).casefold()
        saved = str(getattr(self._job, "ffmpeg", "") or "") if self._job is not None else ""
        try:
            selected_key = str(selected_path.resolve()).casefold() if IS_WINDOWS else str(selected_path.resolve())
            system_keys = {(str(x.resolve()).casefold() if IS_WINDOWS else str(x.resolve())) for x in _system_ffmpeg_paths()}
            user_keys = {(str(x.resolve()).casefold() if IS_WINDOWS else str(x.resolve())) for x in _dedupe_existing_ffmpeg_paths(_ffmpeg_paths_from_location(saved))}
        except Exception:
            selected_key = str(selected_path).casefold() if IS_WINDOWS else str(selected_path)
            system_keys, user_keys = set(), set()
        if is_managed:
            source = "managed SubBurn runtime"
        elif selected_key in system_keys:
            source = "system/PATH FFmpeg"
        elif selected_key in user_keys:
            source = "user-selected FFmpeg"
        else:
            source = "local FFmpeg"
        self.log(f"Selected FFmpeg: {caps.ffmpeg}")
        self.log(f"FFmpeg source: {source} | persistent PATH change this selection: {'managed runtime is promoted on Windows' if is_managed and IS_WINDOWS else 'none'}")
        for c in found:
            self.log(f"Tool candidate score={c.score}: {c.ffmpeg} | filters={','.join(sorted(c.filters & {'ass','subtitles','drawtext','overlay','colorchannelmixer'}))} | encoders={len(c.encoders)}")
        self.status_var.set("Toolset ready")
        # Dynamic capability changes must be published immediately. Validators for the browser,
        # presets and recovery use the canonical control snapshot and must never depend on the
        # next periodic dashboard tick to see current encoder options.
        self.publish_dashboard_controls()
    def scan_fonts_async(self):
        if not self.require_batch_idle("Font rescan"):
            return None
        return self.start_operation_thread("font_scan", self.scan_fonts_worker)
    def scan_fonts_worker(self):
        try:
            fonts = scan_fonts()
            self.emit("fonts", fonts)
        except Exception as e:
            self.emit("error", f"Font scan failed: {e}")
    def apply_fonts(self, fonts):
        self.fonts = fonts
        self.font_map = {}
        labels = []
        counts = {}
        for f in fonts:
            counts[f.label] = counts.get(f.label, 0) + 1
        used = {}
        for f in fonts:
            label = f.label
            if counts[label] > 1:
                used[label] = used.get(label, 0) + 1
                label = f"{label} ({f.source} {used[label]})"
            self.font_map[label] = f
            labels.append(label)
        combos = [self.primary_font_combo, self.fallback_combo]
        if hasattr(self, "wm_font_combo") and self.wm_font_combo.winfo_exists():
            combos.append(self.wm_font_combo)
        for combo in combos:
            combo["values"] = labels
        if labels and self.primary_font_var.get() not in self.font_map:
            preferred = next((x for x in labels if "qatar" in x.casefold()), None) or next((x for x in labels if x.casefold().startswith("arial")), None) or labels[0]
            self.primary_font_var.set(preferred)
        if labels and self.fallback_font_var.get() not in self.font_map:
            self.fallback_font_var.set(labels[0])
        if labels and self.wm_font_var.get() not in self.font_map:
            self.wm_font_var.set(self.primary_font_var.get())
        self.log(f"Fonts loaded: {len(fonts)}")
        # Publish atomically after rebuilding font labels/options. Without this, a preset or
        # browser save issued immediately after a font scan can reject a font SubBurn just chose.
        self.publish_dashboard_controls()
    def add_font(self):
        p = filedialog.askopenfilename(title="Add font", filetypes=[("Fonts", "*.ttf *.otf *.ttc"), ("All files", "*.*")])
        if not p:
            return
        self.import_font_path(p)
    def import_font_path(self, p):
        src = Path(p)
        if not src.is_file() or src.suffix.casefold() not in {".ttf", ".otf", ".ttc"}:
            raise RuntimeError("Choose an existing TTF, OTF, or TTC font file")
        FONT_DIR.mkdir(parents=True, exist_ok=True)
        dst = unique_path(FONT_DIR / src.name)
        shutil.copy2(src, dst)
        self.log(f"Added font: {dst.name}")
        self.scan_fonts_async()
        return dst
    def add_fallback(self):
        label = self.fallback_font_var.get()
        if label and label in self.font_map:
            existing = list(self.fallback_list.get(0, "end"))
            if label not in existing:
                self.fallback_list.insert("end", label)
    def remove_fallback(self):
        sel = self.fallback_list.curselection()
        for i in reversed(sel):
            self.fallback_list.delete(i)
    def refresh_watermark_font_control_state(self):
        combo = getattr(self, "wm_font_combo", None)
        if combo is None:
            return
        try:
            combo.configure(state="disabled" if self.same_wm_font_var.get() else "readonly")
        except Exception:
            pass
    def on_watermark_font_selected(self, _event=None):
        # An explicit watermark-font choice is user intent.  Do not silently ignore it because
        # "Use subtitle font" happened to remain checked from a previous project/default.
        if self.wm_font_var.get():
            self.same_wm_font_var.set(False)
        self.refresh_watermark_font_control_state()
        self.autosave_project()
    def selected_font(self, watermark=False):
        label = self._job.primary_font
        if watermark and not self._job.same_wm_font:
            label = self._job.wm_font
        font_map=dict(getattr(self, "font_map", {}) or {})
        if label not in font_map:
            raise RuntimeError("Select a font")
        return font_map[label]
    def fallback_fonts(self):
        out = [];font_map=dict(getattr(self, "font_map", {}) or {})
        for label in getattr(self._job, "fallback_labels", []):
            if label in font_map:
                out.append(font_map[label])
        return out
    def browse_video(self):
        p = filedialog.askopenfilename(title="Select video", filetypes=[("Video", "*.mp4 *.mkv *.mov *.webm *.avi *.m4v *.ts *.m2ts"), ("All files", "*.*")])
        if p:
            self.drop_video(p)
    def drop_video(self, p):
        p = str(p)
        self.video_var.set(p)
        self.output_name_var.set(safe_filename(Path(p).stem + " - SubBurn"))
        self.analyze_async()
        self.autosave_project()
    def browse_subtitle(self):
        p = filedialog.askopenfilename(title="Select subtitles", filetypes=[("Subtitles", "*.srt *.ass *.ssa *.vtt *.sub *.sup *.idx"), ("All files", "*.*")])
        if p:
            self.drop_subtitle(p)
    def drop_subtitle(self, p):
        self.subtitle_file_var.set(str(p))
        self.subtitle_source_var.set("External")
        self.autosave_project()
    def drop_watermark(self, p):
        self.watermark_image_var.set(str(p))
        self.watermark_type_var.set("Image")
        self.watermark_enabled_var.set(True)
        self.autosave_project()
    def browse_watermark_image(self):
        p = filedialog.askopenfilename(title="Select watermark image", filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")])
        if p:
            self.drop_watermark(p)
    def browse_output_dir(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.output_dir_var.set(p)
            self.update_estimate()
            self.autosave_project()
    def analyze_async(self):
        if not self.require_batch_idle("Analyze"):
            return None
        return self.run_job(self.analyze_worker, operation_type="media_analysis")
    def analyze_worker(self):
        try:
            toolset = self.toolset
            if toolset is None:
                toolset, found, _installed = self._resolve_ffmpeg(allow_managed_install=True, explicit_install=False)
                self.emit("tool", toolset, found)
            video = Path(self._job.video)
            if not video.is_file():
                raise RuntimeError("Video file not found")
            self.set_stage("Media", 10, "Reading media streams and metadata")
            self.emit("status", "Analyzing media")
            info = probe_media(toolset.ffprobe, video)
            self.set_stage("Media", 95, "Media analysis complete")
            self.emit("media", info)
        except Exception as e:
            self.emit("error", f"Media analysis failed: {e}")
    def apply_media(self, info):
        self.media = info
        self.media_var.set(f"{info.width}x{info.height} | {info.fps:.2f} fps | {fmt_time(info.duration)} | {human_bitrate(info.video_bitrate)} | audio {len(info.audio_streams)} | subs {len(info.subtitle_streams)}")
        labels = []
        for s in info.subtitle_streams:
            labels.append(f"stream {s['index']} | {s['codec']} | {s.get('language') or 'und'} | {s.get('title') or 'untitled'}")
        self.embedded_combo["values"] = labels
        if labels and not self.embedded_track_var.get():
            self.embedded_track_var.set(labels[0])
        if labels and not self.subtitle_file_var.get():
            self.subtitle_source_var.set("Embedded")
        self.update_estimate()
        self.status_var.set("Media ready")
        self.log(self.media_var.get())
        self.op_state.set_job(Path(self.video_var.get()).name)
        self.op_state.set_media({"width": info.width, "height": info.height, "fps": round(info.fps, 3), "duration": round(info.duration, 3), "video_codec": info.video_codec, "video_bitrate": info.video_bitrate, "audio_streams": len(info.audio_streams), "subtitle_streams": len(info.subtitle_streams)})
        if hasattr(self, "live_seek_scale"):
            self.live_seek_scale.configure(to=max(0.001, self.live_timestamp_limit()))
            if self.live_seek_var.get() > self.live_timestamp_limit():
                self.live_seek_var.set(0.0)
            self.update_live_seek_label()
        # Embedded-track choices and media-dependent controls are part of the canonical browser
        # snapshot. Publish them immediately instead of waiting for the dashboard timer.
        self.publish_dashboard_controls()
    def embedded_index(self):
        m = re.match(r"stream\s+(\d+)", self._job.embedded_track)
        if not m:
            raise RuntimeError("No embedded subtitle track selected")
        return int(m.group(1))
    def subtitle_source_decision(self):
        """Resolve the subtitle source, allowing visual-only jobs with no subtitles."""
        mode = str(getattr(self._job, "subtitle_source", "") or "")
        if mode == "External":
            if self._job.subtitle_file and Path(self._job.subtitle_file).is_file():
                return "external"
            if self._job.embedded_track:
                return "embedded"
            return "none"
        if mode == "Embedded":
            if self._job.embedded_track:
                return "embedded"
            if self._job.subtitle_file and Path(self._job.subtitle_file).is_file():
                return "external"
            return "none"
        if self._job.subtitle_file and Path(self._job.subtitle_file).is_file():
            return "external"
        if self._job.embedded_track:
            return "embedded"
        return "none"
    def selected_embedded_subtitle_record(self):
        try:
            idx = self.embedded_index()
        except Exception:
            return None
        for record in list(getattr(self.media, "subtitle_streams", []) or []):
            try:
                if int(record.get("index")) == int(idx):
                    return record
            except Exception:
                continue
        return None
    def subtitle_kind(self):
        job = self._job
        if job is None or not hasattr(job, "subtitle_source"):
            return "text"
        source = self.subtitle_source_decision()
        if source == "none":
            return "none"
        if source == "embedded":
            record = self.selected_embedded_subtitle_record()
            codec = str((record or {}).get("codec") or "").casefold()
            return "bitmap" if codec in BITMAP_SUBTITLE_CODECS else "text"
        path = Path(str(getattr(self._job, "subtitle_file", "") or ""))
        ext = path.suffix.casefold()
        if ext in BITMAP_SUB_EXTS:
            return "bitmap"
        if ext == ".sub" and path.with_suffix(".idx").is_file():
            return "bitmap"
        return "text"
    def bitmap_subtitle_codec(self):
        source = self.subtitle_source_decision()
        if source == "embedded":
            record = self.selected_embedded_subtitle_record() or {}
            codec = str(record.get("codec") or "").casefold()
            return codec or "bitmap"
        path = Path(str(getattr(self._job, "subtitle_file", "") or ""))
        if path.suffix.casefold() == ".sup":
            return "hdmv_pgs_subtitle"
        if path.suffix.casefold() == ".idx" or (path.suffix.casefold() == ".sub" and path.with_suffix(".idx").is_file()):
            return "dvd_subtitle"
        return "bitmap"
    def bitmap_subtitle_input_plan(self, preview_offset=0.0):
        if self.subtitle_kind() != "bitmap":
            return None
        source = self.subtitle_source_decision()
        codec = self.bitmap_subtitle_codec()
        if source == "embedded":
            idx = self.embedded_index()
            return {"stream": f"0:{idx}", "extra": [], "codec": codec, "external": False, "input_index": 0}
        path = Path(str(getattr(self._job, "subtitle_file", "") or ""))
        if not path.is_file():
            raise RuntimeError("Bitmap subtitle file not found")
        if path.suffix.casefold() == ".idx" and not path.with_suffix(".sub").is_file():
            raise RuntimeError("VobSub requires both the .idx index and its paired .sub bitmap file")
        if path.suffix.casefold() == ".sub" and path.with_suffix(".idx").is_file():
            path = path.with_suffix(".idx")
        extra = []
        if float(preview_offset or 0.0) > 0:
            extra += ["-ss", f"{float(preview_offset):.6f}"]
        if self.media and self.media.width and self.media.height:
            dw = int(self.media.display_width or self.media.width)
            dh = int(self.media.display_height or self.media.height)
            extra += ["-canvas_size", f"{dw}x{dh}"]
        extra += ["-i", str(path)]
        return {"stream": "1:s:0", "extra": extra, "codec": codec, "external": True, "input_index": 1}
    def bitmap_primary_input_options(self):
        """Input options required by the selected embedded bitmap subtitle decoder."""
        try:
            if self.subtitle_kind() == "bitmap" and self.subtitle_source_decision() == "embedded" and self.bitmap_subtitle_codec() == "dvb_subtitle":
                # DVB subtitle packet durations are often approximate; FFmpeg documents
                # -fix_sub_duration for this exact case. Keep it scoped to DVB only.
                return ["-fix_sub_duration", "1"]
        except Exception:
            pass
        return []

    def prepare_subtitles(self, td, start=None, duration=None):
        kind = self.subtitle_kind()
        if kind == "bitmap":
            placeholder = Path(td) / "bitmap_subtitle_placeholder.srt"
            placeholder.write_text("", encoding="utf-8")
            return placeholder
        if kind == "none":
            placeholder = Path(td) / "no_subtitles.srt"
            placeholder.write_text("", encoding="utf-8")
            return placeholder
        raw = td / "subtitle_raw.srt"
        final = td / "subtitle.srt"
        source = self.subtitle_source_decision()
        if source == "external":
            p = Path(self._job.subtitle_file)
            if not p.is_file():
                if self._job.embedded_track:
                    source = "embedded"
                else:
                    raise RuntimeError("External subtitle file not found")
        if source == "embedded":
            idx = self.embedded_index()
            rc, out = run_capture([self.toolset.ffmpeg, "-hide_banner", "-y", "-i", self._job.video, "-map", f"0:{idx}", "-c:s", "srt", raw], timeout=180)
            if rc != 0 or not raw.exists():
                raise RuntimeError("Embedded subtitle extraction failed: " + out[-2000:])
        else:
            p = Path(self._job.subtitle_file)
            if p.suffix.casefold() == ".srt":
                shutil.copy2(p, raw)
            else:
                rc, out = run_capture([self.toolset.ffmpeg, "-hide_banner", "-y", "-i", p, "-c:s", "srt", raw], timeout=120)
                if rc != 0 or not raw.exists():
                    raise RuntimeError("Subtitle conversion failed: " + out[-2000:])
        cleaned = td / "subtitle_clean.srt"
        sanitize_srt_file(raw, cleaned)
        offset_ms = float(self._job.subtitle_offset or 0)
        if offset_ms:
            shifted = []
            for a, b, body in read_srt_cues(cleaned):
                shifted.append((max(0, a + offset_ms / 1000), max(0.001, b + offset_ms / 1000), body))
            write_srt_cues(shifted, cleaned)
        if start is not None and duration is not None:
            crop_shift_srt(cleaned, final, start, duration)
        else:
            shutil.copy2(cleaned, final)
        return final
    def prepared_font_path(self, rec):
        src = Path(rec.path)
        st = src.stat()
        stat_key = (str(src.resolve()).casefold(), st.st_size, int(st.st_mtime_ns))
        cache = getattr(self, "_font_cache_keys", None)
        if cache is None:
            cache = {}
            self._font_cache_keys = cache
        digest = cache.get(stat_key)
        if digest is None:
            digest = hashlib.sha256(b"SubBurn-font-preserve-exact-v2\0" + src.read_bytes()).hexdigest()
            cache[stat_key] = digest
        PREPARED_FONT_DIR.mkdir(parents=True, exist_ok=True)
        dst = PREPARED_FONT_DIR / f"{digest}{src.suffix.lower()}"
        if dst.is_file() and dst.stat().st_size > 0:
            return dst
        tmp = PREPARED_FONT_DIR / f".{digest}-{os.getpid()}-{threading.get_ident()}{src.suffix.lower()}.tmp"
        try:
            shutil.copy2(src, tmp)
            if not tmp.is_file() or tmp.stat().st_size <= 0:
                raise RuntimeError("Prepared font is empty")
            os.replace(tmp, dst)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        return dst
    def copy_fonts(self, td):
        fonts_dir = td / "fonts"
        fonts_dir.mkdir()
        kind = self.subtitle_kind()
        if kind == "bitmap":
            return fonts_dir, None, []
        if kind == "none" and not (self._job.watermark_enabled and self._job.watermark_type == "Text"):
            return fonts_dir, None, []
        primary_source = self.selected_font(bool(kind == "none" and not self._job.same_wm_font))
        records = [primary_source] + self.fallback_fonts()
        copied = []
        seen = set()
        for i, rec in enumerate(records):
            key = str(rec.path.resolve()).casefold()
            if key in seen:
                continue
            seen.add(key)
            prepared = self.prepared_font_path(rec)
            dst = fonts_dir / f"font{i}{rec.path.suffix.lower()}"
            shutil.copy2(prepared, dst)
            runtime_rec = FontRecord(rec.label, rec.path, rec.full_name, rec.family, rec.source, rec.coverage)
            runtime_rec.runtime_name = rec.full_name or rec.family or rec.label
            copied.append(runtime_rec)
        if not copied:
            raise RuntimeError("No runtime subtitle font could be prepared")
        return fonts_dir, copied[0], copied
    def validate_glyphs(self, subtitle_path, fonts):
        kind = self.subtitle_kind()
        if kind == "bitmap":
            return [], [f"Bitmap subtitles: {self.bitmap_subtitle_codec()} | font/glyph validation not applicable"]
        if kind == "none":
            return [], ["Subtitles: none | subtitle font/glyph validation not applicable"]
        chars = subtitle_characters(subtitle_path)
        covered = set()
        report = []
        for f in fonts:
            coverage = self.font_coverage_for(f)
            covered |= set(chr(x) for x in coverage)
            report.append(f"font {f.full_name}: cmap glyphs {len(coverage or [])}")
        configured_missing = sorted(ch for ch in chars if ch not in covered and unicodedata.category(ch) != "Cf")
        unresolved = []
        planned = {}
        candidates = self.render_font_candidates(fonts)
        for ch in configured_missing:
            chosen = None
            if ch.isspace() or unicodedata.category(ch).startswith("Z"):
                for rec in candidates:
                    if self.font_is_safe_whitespace(rec, ch):
                        chosen = rec
                        break
            else:
                for rec in candidates:
                    if self.font_covers_unit(rec, ch):
                        chosen = rec
                        break
            if chosen is None:
                unresolved.append(ch)
            else:
                planned.setdefault(self.ass_font_name(chosen), set()).add(ord(ch))
        if planned:
            report.append("automatic font fallback available: " + " | ".join(f"{name} [{', '.join(f'U+{cp:04X}' for cp in sorted(cps)[:16])}]" for name, cps in sorted(planned.items())))
        if unresolved:
            names = ", ".join(f"U+{ord(ch):04X} {unicodedata.name(ch, 'UNKNOWN')}" for ch in unresolved[:40])
            report.append("unresolved glyphs: " + names)
        else:
            report.append("font coverage/fallback plan resolves all visible subtitle codepoints; glyph-outline safety is validated during render planning")
        try:
            primary = fonts[0] if fonts else None
            if primary and 0x20 in self.font_coverage_for(primary):
                ink = self.font_glyph_has_ink(primary, 0x20)
                if ink is True:
                    report.append(f"font safety warning: {self.ass_font_name(primary)} draws visible ink for U+0020 SPACE; renderer will replace whitespace runs with a safe fallback")
        except Exception:
            pass
        return unresolved, report
    def validate_common(self):
        if not self.toolset:
            raise RuntimeError("FFmpeg is not ready")
        if not Path(self._job.video).is_file():
            raise RuntimeError("Select a video")
        if not self.media:
            self.media = probe_media(self.toolset.ffprobe, Path(self._job.video))
        self.subtitle_source_decision()
        kind = self.subtitle_kind()
        needs_ass = kind == "text" or (self._job.watermark_enabled and self._job.watermark_type == "Text")
        if needs_ass and "ass" not in self.toolset.filters:
            raise RuntimeError("The selected FFmpeg lacks the dedicated ASS/libass renderer required for text subtitle/watermark shaping")
        if kind == "text":
            self.selected_font(False)
        elif kind == "bitmap":
            if "overlay" not in self.toolset.filters:
                raise RuntimeError("The selected FFmpeg cannot overlay bitmap subtitles")
            decoder_name = {"hdmv_pgs_subtitle": "pgssub", "dvd_subtitle": "dvdsub", "dvb_subtitle": "dvbsub"}.get(self.bitmap_subtitle_codec())
            available_decoders = set(getattr(self.toolset, "decoders", set()) or set())
            if decoder_name and available_decoders and decoder_name not in available_decoders:
                raise RuntimeError(f"The selected FFmpeg lacks the {decoder_name} decoder required for this bitmap subtitle track")
            if self.subtitle_source_decision() == "external":
                p = Path(str(getattr(self._job, "subtitle_file", "") or ""))
                if not p.is_file() or (p.suffix.casefold() not in BITMAP_SUB_EXTS and not (p.suffix.casefold() == ".sub" and p.with_suffix(".idx").is_file())):
                    raise RuntimeError("Select a valid PGS/SUP or VobSub IDX subtitle file")
                if p.suffix.casefold() == ".idx" and not p.with_suffix(".sub").is_file():
                    raise RuntimeError("VobSub requires both the .idx index and its paired .sub bitmap file")
        if self._job.watermark_enabled:
            if self._job.watermark_type == "Text":
                if not self._job.watermark_text:
                    raise RuntimeError("Watermark text is empty")
                self.selected_font(True if not self._job.same_wm_font else False)
            else:
                if "overlay" not in self.toolset.filters:
                    raise RuntimeError("The selected FFmpeg cannot overlay image watermarks")
                img = Path(self._job.watermark_image)
                if not img.is_file() or img.suffix.casefold() not in IMAGE_EXTS:
                    raise RuntimeError("Select a valid watermark image")
    def subtitle_style_from_job(self, job=None):
        job = job or self._job
        def number(name, default, lo, hi):
            raw = getattr(job, name, default)
            try:
                value = float(raw)
            except Exception:
                raise RuntimeError(f"Subtitle style {name.replace('_', ' ')} must be numeric")
            if not math.isfinite(value) or value < lo or value > hi:
                raise RuntimeError(f"Subtitle style {name.replace('_', ' ')} must be between {lo:g} and {hi:g}")
            return value
        alignment_name = str(getattr(job, "subtitle_alignment", "Bottom center") or "Bottom center")
        if alignment_name not in SUBTITLE_ALIGNMENT_MAP:
            raise RuntimeError("Choose a valid subtitle alignment")
        margin_v = number("margin", "24", 0, 10000) + number("safe_area", "8", 0, 10000)
        return SubtitleStyle(
            font_size=number("font_size", "28", .1, 1000),
            bold=bool(getattr(job, "force_bold", False)),
            italic=bool(getattr(job, "italic", False)),
            underline=bool(getattr(job, "underline", False)),
            strikeout=bool(getattr(job, "strikeout", False)),
            text_rgb=str(getattr(job, "text_rgb", "FFFFFF")),
            text_opacity=number("text_opacity", "100", 0, 100),
            outline_rgb=str(getattr(job, "outline_rgb", "000000")),
            outline_opacity=number("outline_opacity", "100", 0, 100),
            outline_width=number("outline", "2", 0, 1000),
            shadow_rgb=str(getattr(job, "shadow_rgb", "000000")),
            shadow_opacity=number("shadow_opacity", "100", 0, 100),
            shadow_depth=number("shadow_depth", "0", 0, 1000),
            spacing=number("letter_spacing", "0", -1000, 1000),
            angle=number("rotation_angle", "0", -36000, 36000),
            alignment=SUBTITLE_ALIGNMENT_MAP[alignment_name],
            margin_l=int(round(number("margin_left", "10", 0, 10000))),
            margin_r=int(round(number("margin_right", "10", 0, 10000))),
            margin_v=int(round(margin_v)),
            background_box=bool(getattr(job, "background_box", False)),
            background_rgb=str(getattr(job, "background_rgb", "000000")),
            background_opacity=number("background_opacity", "65", 0, 100),
            background_padding=number("background_padding", "4", 0, 1000),
        )
    def rgb_to_ass(self, s):
        s = str(s).strip().lstrip("＃")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
            raise RuntimeError("Invalid RGB color")
        return s[4:6] + s[2:4] + s[0:2]
    def ass_escape(self, s):
        return str(s).replace("\\", r"\\").replace("'", r"\'").replace(",", r"\,")
    def wrap_srt_for_render(self, path):
        max_chars = int(float(self._job.wrap_chars or 0))
        max_lines = int(float(self._job.max_lines or 0))
        if max_chars <= 0 and max_lines <= 0:
            return
        cues = []
        impossible = 0
        for a, b, body in read_srt_cues(path):
            text = " ".join(body)
            lines = []
            if max_chars > 0:
                words = text.split()
                line = ""
                for w in words:
                    if not line:
                        line = w
                    elif len(line) + 1 + len(w) <= max_chars:
                        line += " " + w
                    else:
                        lines.append(line)
                        line = w
                if line:
                    lines.append(line)
            else:
                lines = list(body)
            if max_lines > 0 and len(lines) > max_lines:
                words = text.split()
                if words:
                    total_chars = sum(len(w) for w in words) + max(0, len(words) - 1)
                    target = max(1, int(math.ceil(total_chars / max_lines)))
                    balanced = []
                    pos = 0
                    for line_idx in range(max_lines):
                        if pos >= len(words):
                            break
                        if line_idx == max_lines - 1:
                            balanced.append(" ".join(words[pos:]))
                            pos = len(words)
                            break
                        remaining_lines = max_lines - line_idx - 1
                        current = words[pos]
                        pos += 1
                        while pos < len(words):
                            words_after = len(words) - (pos + 1)
                            if words_after < remaining_lines:
                                break
                            candidate = current + " " + words[pos]
                            if len(candidate) > target:
                                break
                            current = candidate
                            pos += 1
                        balanced.append(current)
                    lines = balanced
                else:
                    lines = lines[:max_lines]
                if max_chars > 0 and any(len(line) > max_chars for line in lines):
                    impossible += 1
            cues.append((a, b, lines))
        write_srt_cues(cues, path)
        if impossible and hasattr(self, "log"):
            self.log(f"Subtitle layout warning: {impossible} cue(s) cannot satisfy both Wrap chars={max_chars} and Max lines={max_lines} without dropping text; lines were balanced instead")
    def ass_timestamp(self, seconds):
        seconds = max(0.0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        sec = seconds % 60
        return f"{h}:{m:02d}:{sec:05.2f}"
    def ass_font_name(self, rec):
        name = getattr(rec, "runtime_name", None) or rec.full_name or rec.family or rec.label or Path(rec.path).stem
        return str(name).replace("{", "").replace("}", "").replace("\\", "")
    def font_coverage_for(self, rec):
        if rec.coverage is not None:
            return rec.coverage
        cache = getattr(self, "_glyph_coverage_cache", None)
        if cache is None:
            cache = {}
            self._glyph_coverage_cache = cache
        try:
            st = Path(rec.path).stat()
            key = (str(Path(rec.path).resolve()).casefold(), st.st_size, int(st.st_mtime_ns))
        except Exception:
            key = str(rec.path)
        if key in cache:
            rec.coverage = cache[key]
            return rec.coverage
        coverage = read_cmap_coverage(rec.path)
        if not coverage:
            try:
                TTFont, _ = ensure_fonttools_runtime()
                kwargs = {"fontNumber": 0} if Path(rec.path).suffix.casefold() in {".ttc", ".otc"} else {}
                font = TTFont(rec.path, lazy=True, **kwargs)
                cmap = font.getBestCmap() or {}
                coverage = set(cmap)
                font.close()
            except Exception:
                coverage = set()
        cache[key] = coverage
        rec.coverage = coverage
        return coverage
    def font_glyph_has_ink(self, rec, cp):
        cache = getattr(self, "_glyph_ink_cache", None)
        if cache is None:
            cache = {}
            self._glyph_ink_cache = cache
        try:
            st = Path(rec.path).stat()
            key = (str(Path(rec.path).resolve()).casefold(), st.st_size, int(st.st_mtime_ns), int(cp))
        except Exception:
            key = (str(rec.path), int(cp))
        if key in cache:
            return cache[key]
        result = None
        try:
            TTFont, _ = ensure_fonttools_runtime()
            from fontTools.pens.recordingPen import RecordingPen
            kwargs = {"fontNumber": 0} if Path(rec.path).suffix.casefold() in {".ttc", ".otc"} else {}
            font = TTFont(rec.path, lazy=True, **kwargs)
            cmap = font.getBestCmap() or {}
            glyph_name = cmap.get(int(cp))
            if glyph_name is None or glyph_name == ".notdef":
                result = None
            else:
                glyph = font.getGlyphSet()[glyph_name]
                pen = RecordingPen()
                glyph.draw(pen)
                result = bool(pen.value)
            font.close()
        except Exception:
            result = None
        cache[key] = result
        return result
    def font_is_safe_whitespace(self, rec, ch):
        cp = ord(ch)
        if cp not in self.font_coverage_for(rec):
            return False
        return self.font_glyph_has_ink(rec, cp) is False
    def render_font_candidates(self, configured):
        out = []
        seen = set()
        for rec in list(configured) + list(getattr(self, "fonts", []) or []):
            try:
                key = str(Path(rec.path).resolve()).casefold()
            except Exception:
                key = str(rec.path).casefold()
            if key in seen or not Path(rec.path).is_file():
                continue
            seen.add(key)
            out.append(rec)
        configured_count = len({str(Path(x.path).resolve()).casefold() for x in configured if Path(x.path).is_file()})
        head = out[:configured_count]
        tail = out[configured_count:]
        def score(rec):
            name = (rec.full_name + " " + rec.family + " " + rec.label).casefold()
            if "noto" in name:
                return 0
            if "segoe ui" in name:
                return 1
            if "arial" in name:
                return 2
            if "dejavu sans" in name:
                return 3
            if "tahoma" in name:
                return 4
            return 20
        tail.sort(key=lambda r: (score(r), (r.full_name or r.label).casefold()))
        return head + tail
    def text_font_units(self, text):
        # Font fallback must never insert an ASS \fn override inside an extended grapheme
        # cluster.  Use Unicode UAX #29 segmentation rather than hand-maintained script/emoji
        # heuristics so Indic conjuncts, regional-indicator flags, ZWJ emoji, combining marks,
        # variation selectors, and future Unicode additions stay indivisible.
        value = str(text)
        if not value:
            return []
        pattern = ensure_grapheme_pattern()
        return pattern.findall(value)
    def renderable_codepoints(self, text):
        cps = []
        for ch in str(text):
            cp = ord(ch)
            cat = unicodedata.category(ch)
            if ch.isspace() or cat.startswith("Z") or cat == "Cf" or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
                continue
            cps.append(cp)
        return cps
    def font_covers_unit(self, rec, text):
        coverage = self.font_coverage_for(rec)
        return all(cp in coverage for cp in self.renderable_codepoints(text))
    def copy_render_font(self, rec, fonts_dir):
        prepared = self.prepared_font_path(rec)
        try:
            digest = hashlib.sha256((str(Path(rec.path).resolve()).casefold() + "\0" + str(Path(rec.path).stat().st_size)).encode("utf-8", errors="replace")).hexdigest()[:16]
        except Exception:
            digest = hashlib.sha256(str(rec.path).encode("utf-8", errors="replace")).hexdigest()[:16]
        suffix = Path(rec.path).suffix.casefold() or ".ttf"
        dst = Path(fonts_dir) / f"fallback_{digest}{suffix}"
        if not dst.exists():
            shutil.copy2(prepared, dst)
        return dst
    def new_font_render_context(self, configured, fonts_dir):
        # The long-form renderer can process tens of thousands of grapheme clusters.  Building
        # and sorting the full system-font candidate list for every cluster made a 50-minute SRT
        # appear frozen for minutes.  Resolve candidates once per render and memoize each unique
        # grapheme/whitespace decision.  This preserves the exact fallback semantics while making
        # runtime proportional to the number of *unique* clusters rather than total characters.
        candidates = self.render_font_candidates(configured)
        primary = candidates[0] if candidates else None
        return {
            "candidates": candidates,
            "unit_cache": {},
            "text_cache": {},
            "whitespace_cache": {},
            "primary": primary,
            "primary_coverage": self.font_coverage_for(primary) if primary is not None else set(),
            "fonts_dir": Path(fonts_dir),
        }
    def _record_font_resolution_usage(self, rec, idx, unit, usage):
        if idx <= 0:
            return
        cps = self.renderable_codepoints(unit)
        if not cps and len(unit) == 1:
            cps = [ord(unit)]
        for cp in cps:
            usage.setdefault(self.ass_font_name(rec), set()).add(cp)
    def choose_font_for_unit(self, unit, configured, fonts_dir, usage, render_context=None):
        context = render_context if isinstance(render_context, dict) else None
        cache = context.setdefault("unit_cache", {}) if context is not None else None
        if cache is not None and unit in cache:
            rec, display, idx = cache[unit]
            self._record_font_resolution_usage(rec, idx, unit, usage)
            return rec, display
        candidates = context.get("candidates") if context is not None else self.render_font_candidates(configured)
        if not candidates:
            raise RuntimeError("No fonts are available for subtitle rendering")
        display = unit
        chosen = None
        chosen_idx = -1
        if len(unit) == 1 and (unit.isspace() or unicodedata.category(unit).startswith("Z")):
            for idx, rec in enumerate(candidates):
                if self.font_is_safe_whitespace(rec, unit):
                    chosen, chosen_idx = rec, idx
                    break
            if chosen is None and unit != " ":
                for idx, rec in enumerate(candidates):
                    if self.font_is_safe_whitespace(rec, " "):
                        chosen, chosen_idx, display = rec, idx, " "
                        break
            if chosen is None:
                raise RuntimeError(f"No available font has a non-drawing whitespace glyph for U+{ord(unit):04X}")
        else:
            for idx, rec in enumerate(candidates):
                if self.font_covers_unit(rec, unit):
                    chosen, chosen_idx = rec, idx
                    break
            if chosen is None:
                cps = self.renderable_codepoints(unit)
                sample = ", ".join(f"U+{cp:04X} {unicodedata.name(chr(cp), 'UNKNOWN')}" for cp in cps[:12])
                raise RuntimeError("No configured or system font can render subtitle cluster: " + sample)
        self.copy_render_font(chosen, fonts_dir)
        if cache is not None:
            cache[unit] = (chosen, display, chosen_idx)
        self._record_font_resolution_usage(chosen, chosen_idx, unit, usage)
        return chosen, display
    def caption_effect_spec_from_job(self, job=None):
        job = job or self._job
        effect_id = str(getattr(job, "caption_effect_id", "none") or "none")
        params = getattr(job, "caption_effect_params", None) or {"active_rgb": "FFD400", "allow_estimated_timing": True}
        return CaptionEffectSpec(effect_id, params)
    def caption_word_chunks(self, body):
        chunks = []
        lines = list(body or [])
        for line_index, line in enumerate(lines):
            matches = list(re.finditer(r"(\S+)([ \t]*)", str(line)))
            for i, match in enumerate(matches):
                chunks.append({
                    "word": match.group(1),
                    "suffix": match.group(2),
                    "line_break": bool(line_index < len(lines) - 1 and i == len(matches) - 1),
                })
            if not matches and line_index < len(lines) - 1 and chunks:
                chunks[-1]["line_break"] = True
        return chunks
    def load_caption_sidecar_words(self, preview_offset=0.0):
        raw = str(getattr(self._job, "subtitle_file", "") or "").strip()
        if not raw:
            return None
        subtitle_path = Path(raw)
        sidecar = subtitle_path.with_suffix(".words.json")
        if not sidecar.is_file():
            return None
        st = sidecar.stat()
        cache = getattr(self, "_caption_words_cache", None)
        if cache is None:
            cache = {}
            self._caption_words_cache = cache
        # Sidecars are small and directly alter animated-caption pixels/timing.  Content hash
        # prevents same-size/same-mtime replacement from returning stale word timings.
        key = (str(sidecar.resolve()), int(st.st_size), full_file_sha256(sidecar))
        payload = cache.get(key)
        if payload is None:
            try:
                payload = json.loads(sidecar.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Could not read animated-caption word timing sidecar: {exc}")
            if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
                raise RuntimeError("Animated-caption word timing sidecar has an invalid schema")
            cache.clear()
            cache[key] = payload
        try:
            offset = float(getattr(self._job, "subtitle_offset", 0) or 0) / 1000.0
        except Exception:
            offset = 0.0
        shift = offset - float(preview_offset or 0.0)
        words = []
        for seg in payload.get("segments") or []:
            if not isinstance(seg, dict):
                continue
            for word in seg.get("words") or []:
                if not isinstance(word, dict):
                    continue
                text_value = str(word.get("text", "") or "").strip()
                if not text_value:
                    continue
                try:
                    start = float(word.get("start", seg.get("start", 0.0))) + shift
                    end = float(word.get("end", start)) + shift
                except Exception:
                    continue
                if not math.isfinite(start) or not math.isfinite(end):
                    continue
                words.append({"start": max(0.0, start), "end": max(max(0.0, start), end), "text": text_value})
        words.sort(key=lambda x: (x["start"], x["end"]))
        return words
    def estimated_caption_word_times(self, chunks, start, end):
        if not chunks:
            return []
        duration = max(0.001, float(end) - float(start))
        # Grapheme-weighted allocation keeps long words from receiving the same duration as a
        # one-character word, while remaining language-agnostic. It is explicitly approximate.
        weights = [max(1, len(self.text_font_units(chunk["word"]))) for chunk in chunks]
        total = max(1, sum(weights))
        out = []
        cursor = float(start)
        for i, weight in enumerate(weights):
            next_cursor = float(end) if i == len(weights) - 1 else cursor + duration * weight / total
            out.append({"start": cursor, "end": max(cursor + 0.001, next_cursor), "text": chunks[i]["word"]})
            cursor = next_cursor
        return out
    def caption_word_times_for_cue(self, chunks, start, end, sidecar_words, allow_estimated):
        exact = []
        if sidecar_words is not None:
            for word in sidecar_words:
                # Use overlap rather than strict containment because SRT boundaries can be rounded
                # independently from word timestamps.
                if word["end"] > float(start) - 0.08 and word["start"] < float(end) + 0.08:
                    exact.append(word)
            if len(exact) == len(chunks) and exact:
                return exact, "exact"
        if allow_estimated:
            return self.estimated_caption_word_times(chunks, start, end), "estimated"
        if sidecar_words is None:
            raise RuntimeError("Animated captions require word timestamps. Generate subtitles with SubBurn transcription or enable estimated word timing.")
        raise RuntimeError("The transcription word timings do not align with this subtitle cue. Enable estimated word timing or regenerate the transcription sidecar.")
    @staticmethod
    def ass_override_rgb(rgb):
        value = str(rgb).strip().lstrip("#").lstrip("＃")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
            raise RuntimeError("Animated-caption RGB must use six hexadecimal digits")
        return value[4:6].upper() + value[2:4].upper() + value[0:2].upper()
    @staticmethod
    def ass_override_alpha(opacity):
        opacity = max(0.0, min(100.0, float(opacity)))
        return f"{255 - int(round(opacity / 100.0 * 255)):02X}"
    def build_animated_caption_event(self, start, end, body, configured, fonts_dir, usage, style, spec, sidecar_words, render_context=None):
        chunks = self.caption_word_chunks(body)
        if not chunks:
            return None
        words, timing_source = self.caption_word_times_for_cue(chunks, start, end, sidecar_words, spec.params["allow_estimated_timing"])
        event_start = max(float(start), min(float(end) - 0.001, float(words[0]["start"]))) if timing_source == "exact" else float(start)
        starts = [max(event_start, min(float(end), float(w["start"]))) for w in words]
        # Force monotonic starts after timestamp rounding/noise.
        for i in range(1, len(starts)):
            starts[i] = max(starts[i], starts[i - 1])
        durations_cs = []
        for i, word_start in enumerate(starts):
            next_start = starts[i + 1] if i + 1 < len(starts) else float(end)
            durations_cs.append(max(1, int(round(max(0.01, next_start - word_start) * 100.0))))
        base_bgr = self.ass_override_rgb(style.text_rgb)
        active_bgr = self.ass_override_rgb(spec.params["active_rgb"])
        alpha = self.ass_override_alpha(style.text_opacity)
        if spec.effect_id == "karaoke_progress":
            prefix = "{\\1c&H" + active_bgr + "&\\2c&H" + base_bgr + "&\\1a&H" + alpha + "&\\2a&H" + alpha + "&}"
        elif spec.effect_id == "word_reveal":
            prefix = "{\\1c&H" + base_bgr + "&\\2c&H" + base_bgr + "&\\1a&H" + alpha + "&\\2a&HFF&}"
        else:
            raise RuntimeError("Unsupported animated caption effect")
        pieces = [prefix]
        for chunk, duration_cs in zip(chunks, durations_cs):
            pieces.append("{\\k" + str(duration_cs) + "}")
            pieces.append(self.ass_font_run_text(chunk["word"], configured, fonts_dir, usage, render_context))
            if chunk["suffix"]:
                pieces.append(self.ass_font_run_text(chunk["suffix"], configured, fonts_dir, usage, render_context))
            if chunk["line_break"]:
                pieces.append(r"\N")
        return event_start, float(end), "".join(pieces), timing_source
    def ass_escape_visible_text(self, text):
        return str(text).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
    def ass_font_run_text(self, text, configured, fonts_dir, usage, render_context=None):
        value = str(text)
        context = render_context if isinstance(render_context, dict) else None
        text_cache = context.setdefault("text_cache", {}) if context is not None else None
        if text_cache is not None and value in text_cache:
            return text_cache[value]
        # Fast path learned from the 4x subtitle burner: when the selected primary font can
        # render the whole line safely, do not segment the line into graphemes at all.  Emit one
        # font override and the escaped text.  Full grapheme-safe fallback remains available only
        # for lines that actually need it, so optional complexity has zero cost on the common path.
        if context is not None:
            primary = context.get("primary")
            coverage = context.get("primary_coverage") or set()
            whitespace_cache = context.setdefault("whitespace_cache", {})
            if primary is not None:
                primary_ok = True
                for ch in value:
                    cp = ord(ch); cat = unicodedata.category(ch)
                    if ch.isspace() or cat.startswith("Z"):
                        safe = whitespace_cache.get(ch)
                        if safe is None:
                            safe = bool(self.font_is_safe_whitespace(primary, ch))
                            whitespace_cache[ch] = safe
                        if not safe:
                            primary_ok = False; break
                    elif cat == "Cf" or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
                        continue
                    elif cp not in coverage:
                        primary_ok = False; break
                if primary_ok:
                    rendered = "{\\fn" + self.ass_font_name(primary) + "}" + self.ass_escape_visible_text(value)
                    if text_cache is not None:
                        text_cache[value] = rendered
                    return rendered
        parts = []
        current_name = None
        for unit in self.text_font_units(value):
            rec, display = self.choose_font_for_unit(unit, configured, fonts_dir, usage, context)
            name = self.ass_font_name(rec)
            if name != current_name:
                parts.append("{\\fn" + name + "}")
                current_name = name
            parts.append(self.ass_escape_visible_text(display))
        rendered = "".join(parts)
        if text_cache is not None:
            text_cache[value] = rendered
        return rendered
    def source_display_dimensions(self):
        if not self.media:
            return 0, 0
        return (int(getattr(self.media, "display_width", 0) or self.media.width or 0),
                int(getattr(self.media, "display_height", 0) or self.media.height or 0))

    def prepare_universal_ass(self, td, subtitle_file, fonts_dir, primary, preview_offset=0.0):
        self.wrap_srt_for_render(subtitle_file)
        cues = read_srt_cues(subtitle_file)
        if not cues:
            return None
        configured = [primary]
        for rec in self.fallback_fonts():
            if all(str(Path(rec.path)) != str(Path(x.path)) for x in configured):
                configured.append(rec)
        for rec in configured:
            self.copy_render_font(rec, fonts_dir)
        usage = {}
        render_context = self.new_font_render_context(configured, fonts_dir)
        primary_space_ink = self.font_glyph_has_ink(primary, 0x20) if 0x20 in self.font_coverage_for(primary) else None
        subtitle_style = self.subtitle_style_from_job(self._job)
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {self.source_display_dimensions()[0]}",
            f"PlayResY: {self.source_display_dimensions()[1]}",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            subtitle_style.ass_style_line("Default", self.ass_font_name(primary)),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        caption_spec = self.caption_effect_spec_from_job(self._job)
        sidecar_words = self.load_caption_sidecar_words(preview_offset) if caption_spec.effect_id != "none" else None
        timing_sources = set()
        total_cues = len(cues)
        report_every = max(1, total_cues // 50)
        started = time.monotonic()
        for cue_index, (a, b, body) in enumerate(cues, 1):
            if cue_index == 1 or cue_index == total_cues or cue_index % report_every == 0:
                elapsed = max(0.0, time.monotonic() - started)
                self.set_stage("Filters", cue_index / max(1, total_cues) * 100.0, f"Building subtitle font runs - {cue_index}/{total_cues} cues ({elapsed:.1f}s)")
            if caption_spec.effect_id == "none":
                rendered_lines = [self.ass_font_run_text(line, configured, fonts_dir, usage, render_context) for line in body]
                event_text = r"\N".join(rendered_lines)
                lines.append(f"Dialogue: 0,{self.ass_timestamp(a)},{self.ass_timestamp(b)},Default,,0,0,0,,{event_text}")
            else:
                animated = self.build_animated_caption_event(a, b, body, configured, fonts_dir, usage, subtitle_style, caption_spec, sidecar_words, render_context)
                if animated is None:
                    continue
                event_start, event_end, event_text, timing_source = animated
                timing_sources.add(timing_source)
                lines.append(f"Dialogue: 0,{self.ass_timestamp(event_start)},{self.ass_timestamp(event_end)},Default,,0,0,0,,{event_text}")
        if caption_spec.effect_id != "none":
            label = CAPTION_EFFECT_ID_TO_LABEL.get(caption_spec.effect_id, caption_spec.effect_id)
            if timing_sources == {"exact"}:
                timing_label = "exact transcription word timestamps"
            elif "estimated" in timing_sources:
                timing_label = "cue-local estimated word timing (approximate)"
            else:
                timing_label = "word timing"
            self.log(f"Animated captions: {label} | {timing_label}")
        path = Path(td) / "subtitle_render.ass"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        used = []
        for name, cps in sorted(usage.items()):
            labels = ", ".join(f"U+{cp:04X}" for cp in sorted(cps)[:16])
            used.append(f"{name} [{labels}]")
        if primary_space_ink is True:
            self.log(f"Font safety: {self.ass_font_name(primary)} has visible ink in U+0020 SPACE; whitespace is forced to a safe fallback font")
        if used:
            self.log("Font fallback runs: " + " | ".join(used))
        self.log("Subtitle renderer: libass + HarfBuzz/FriBidi + deterministic per-run font fallback")
        self.log(f"Subtitle style: alignment={getattr(self._job, 'subtitle_alignment', 'Bottom center')} | opacity={subtitle_style.text_opacity:g}% | spacing={subtitle_style.spacing:g} | rotation={subtitle_style.angle:g}° | background={'box' if subtitle_style.background_box else 'off'}")
        return path
    def prepare_universal_text_watermark_ass(self, td, fonts_dir, primary, preview_offset=0.0):
        text = sanitize_subtitle_text(normalize_render_text(self._job.watermark_text))
        if not text:
            return None
        configured = [primary]
        for rec in self.fallback_fonts():
            if all(str(Path(rec.path)) != str(Path(x.path)) for x in configured):
                configured.append(rec)
        for rec in configured:
            self.copy_render_font(rec, fonts_dir)
        usage = {}
        render_context = self.new_font_render_context(configured, fonts_dir)
        rendered = self.ass_font_run_text(text, configured, fonts_dir, usage, render_context)
        opacity = max(0.0, min(1.0, float(self._job.watermark_opacity)))
        alpha = 255 - int(round(opacity * 255))
        color = f"&H{alpha:02X}FFFFFF"
        outline_color = f"&H{alpha:02X}000000"
        alignments = {"Bottom left": 1, "Bottom center": 2, "Bottom right": 3, "Middle left": 4, "Center": 5, "Middle right": 6, "Top left": 7, "Top center": 8, "Top right": 9}
        duration = max(0.001, float(self.media.duration or 24 * 3600))
        events = []
        if self._job.watermark_timing == "Intervals":
            for row in getattr(self._job, "watermark_rows", []):
                start = max(0.0, float(row[0]) - float(preview_offset))
                end = max(0.0, float(row[1]) - float(preview_offset))
                if end <= 0 or end <= start:
                    continue
                events.append((start, end, row[2]))
        else:
            events.append((0.0, max(0.001, duration - float(preview_offset)), self._job.watermark_position))
        if not events:
            return None
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {self.source_display_dimensions()[0]}",
            f"PlayResY: {self.source_display_dimensions()[1]}",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            f"Style: Watermark,{self.ass_font_name(primary)},{float(self._job.watermark_size):g},{color},&H000000FF,{outline_color},&H00000000,0,0,0,0,100,100,0,0,1,{float(self._job.watermark_outline):g},0,2,{int(float(self._job.watermark_margin))},{int(float(self._job.watermark_margin))},{int(float(self._job.watermark_margin))},1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        for start, end, position in events:
            alignment = alignments.get(position, 9)
            lines.append(f"Dialogue: 0,{self.ass_timestamp(start)},{self.ass_timestamp(end)},Watermark,,0,0,0,,{{\\an{alignment}}}{rendered}")
        path = Path(td) / "watermark_text_render.ass"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.log(f"Text watermark font: requested={getattr(self._job, 'wm_font', '') if not getattr(self._job, 'same_wm_font', True) else getattr(self._job, 'primary_font', '')} | primary={self.ass_font_name(primary)} | use subtitle font={'yes' if getattr(self._job, 'same_wm_font', True) else 'no'}")
        if usage:
            self.log("Text watermark fallback runs: " + " | ".join(f"{name} [{', '.join(f'U+{cp:04X}' for cp in sorted(cps)[:16])}]" for name, cps in sorted(usage.items())))
        self.log("Text watermark renderer: libass + HarfBuzz/FriBidi + deterministic per-run font fallback")
        return path
    def merge_text_ass_layers(self, td, subtitle_ass, watermark_ass):
        """Combine subtitle and text-watermark ASS into one libass pass."""
        if subtitle_ass is None:
            return watermark_ass
        if watermark_ass is None:
            return subtitle_ass
        sub_lines = Path(subtitle_ass).read_text(encoding="utf-8").splitlines()
        wm_lines = Path(watermark_ass).read_text(encoding="utf-8").splitlines()
        wm_styles = [line for line in wm_lines if line.startswith("Style: Watermark,")]
        wm_events = [line for line in wm_lines if line.startswith("Dialogue:")]
        if not wm_styles or not wm_events:
            return subtitle_ass
        try:
            events_index = sub_lines.index("[Events]")
        except ValueError as exc:
            raise RuntimeError("Subtitle ASS is missing its Events section") from exc
        existing_styles = set(line for line in sub_lines if line.startswith("Style:"))
        for style in reversed(wm_styles):
            if style not in existing_styles:
                sub_lines.insert(events_index, style)
        sub_lines.extend(wm_events)
        out = Path(td) / "subburn_text_layers.ass"
        out.write_text("\n".join(sub_lines) + "\n", encoding="utf-8")
        self.log("Render optimization: subtitle and text watermark combined into one libass pass")
        return out

    def output_dimensions_for_job(self, job=None):
        job = job or self._job
        source_w, source_h = self.source_display_dimensions()
        out_w, out_h = int(source_w), int(source_h)
        if getattr(job, "resolution", "Original") != "Original":
            out_h = int(str(job.resolution).rstrip("p"))
            out_w = int(round(source_w * out_h / max(1, source_h) / 2) * 2)
        return out_w, out_h
    def preset_overlay_xy(self, pos, margin, out_w, out_h, wm_w, wm_h):
        xs = {"left": int(margin), "center": int(round((out_w - wm_w) / 2)), "right": int(out_w - wm_w - int(margin))}
        ys = {"top": int(margin), "middle": int(round((out_h - wm_h) / 2)), "bottom": int(out_h - wm_h - int(margin))}
        table = {
            "Top left": (xs["left"], ys["top"]), "Top center": (xs["center"], ys["top"]), "Top right": (xs["right"], ys["top"]),
            "Middle left": (xs["left"], ys["middle"]), "Center": (xs["center"], ys["middle"]), "Middle right": (xs["right"], ys["middle"]),
            "Bottom left": (xs["left"], ys["bottom"]), "Bottom center": (xs["center"], ys["bottom"]), "Bottom right": (xs["right"], ys["bottom"]),
        }
        x, y = table.get(pos, table["Top right"])
        return max(0, x), max(0, y)
    def watermark_image_render_box(self, job=None):
        job = job or self._job
        geom = self.watermark_image_geometry(job.watermark_image)
        crop = geom.get("crop")
        source_w, source_h = int(geom["width"]), int(geom["height"])
        content_w, content_h = (int(crop[0]), int(crop[1])) if crop else (source_w, source_h)
        out_w, out_h = self.output_dimensions_for_job(job)
        try:
            scale_pct = float(getattr(job, "watermark_image_scale", "100") or 100.0)
        except Exception:
            scale_pct = 100.0
        if not math.isfinite(scale_pct) or scale_pct <= 0:
            scale_pct = 100.0
        render_w = max(1, int(round(content_w * scale_pct / 100.0)))
        render_h = max(1, int(round(content_h * scale_pct / 100.0)))
        fit_w = max(1, int(out_w * 0.95))
        fit_h = max(1, int(out_h * 0.95))
        fit_ratio = min(fit_w / render_w if render_w > fit_w else 1.0, fit_h / render_h if render_h > fit_h else 1.0)
        capped = fit_ratio < 0.999999
        if capped:
            render_w = max(1, int(round(render_w * fit_ratio)))
            render_h = max(1, int(round(render_h * fit_ratio)))
        try:
            custom_x = float(getattr(job, "watermark_image_x", "")) if str(getattr(job, "watermark_image_x", "")).strip() != "" else None
        except Exception:
            custom_x = None
        try:
            custom_y = float(getattr(job, "watermark_image_y", "")) if str(getattr(job, "watermark_image_y", "")).strip() != "" else None
        except Exception:
            custom_y = None
        margin = int(float(getattr(job, "watermark_margin", 20) or 20))
        if custom_x is not None and custom_y is not None:
            x = int(round(max(0.0, min(custom_x, max(0, out_w - render_w)))))
            y = int(round(max(0.0, min(custom_y, max(0, out_h - render_h)))))
            custom = True
        else:
            x, y = self.preset_overlay_xy(getattr(job, "watermark_position", "Top right"), margin, out_w, out_h, render_w, render_h)
            custom = False
        return {"source_w": source_w, "source_h": source_h, "content_w": content_w, "content_h": content_h, "crop": crop, "out_w": out_w, "out_h": out_h, "scale_pct": scale_pct, "render_w": render_w, "render_h": render_h, "fit_capped": capped, "fit_ratio": fit_ratio, "x": x, "y": y, "custom": custom}
    def reset_watermark_image_layout(self):
        self.watermark_image_scale_var.set("100")
        self.watermark_image_x_var.set("")
        self.watermark_image_y_var.set("")
        self.log_ui("Watermark image layout reset to preset positioning at 100% natural size")
        self.autosave_project()
        self.publish_dashboard_controls()
    def render_watermark_layout_preview(self, job, target_dir):
        ffmpeg = Path(getattr(self.toolset, "ffmpeg", getattr(job, "ffmpeg", "ffmpeg")))
        info = self.watermark_image_render_box(job)
        src = Path(job.watermark_image)
        out = Path(target_dir) / "wm_layout_preview.png"
        vf = []
        crop = info.get("crop")
        if crop and (crop[0] != info["source_w"] or crop[1] != info["source_h"] or crop[2] or crop[3]):
            vf.append(f"crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]}")
        vf.append(f"scale={info['render_w']}:-2:flags=lanczos")
        opacity = max(0.0, min(1.0, float(job.watermark_opacity)))
        if opacity < 0.999:
            vf.append(f"colorchannelmixer=aa={opacity:.3f}")
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-vf", ",".join(vf), "-frames:v", "1", out]
        rc, out_text = run_capture(cmd, timeout=30)
        if rc != 0 or not out.is_file():
            raise RuntimeError("Could not render watermark layout preview: " + out_text[-800:])
        return out, info
    def selected_safe_zone_preset(self):
        name = str(self.platform_safe_zone_var.get() or "Off")
        return SAFE_ZONE_PRESETS.get(name)
    def draw_platform_safe_zone_guides(self, canvas, frame_left, frame_top, disp_w, disp_h, preset=None):
        canvas.delete("platform_safe_zone")
        preset = preset if preset is not None else self.selected_safe_zone_preset()
        if preset is None:
            return 0
        created = 0
        for rect in preset.obscured:
            x1, y1, x2, y2 = rect.display_box(frame_left, frame_top, disp_w, disp_h)
            canvas.create_rectangle(x1, y1, x2, y2, fill="#8a2525", stipple="gray25", outline="#ff6b6b", width=2, tags=("platform_safe_zone", "obscured_zone"))
            if rect.label:
                canvas.create_text(x1 + 5, y1 + 5, text=rect.label.upper(), anchor="nw", fill="#ffaaaa", font=("TkDefaultFont", 8, "bold"), tags=("platform_safe_zone", "obscured_zone"))
            created += 1
        for rect, color, tag, label in ((preset.caption_safe, "#61d879", "caption_safe_zone", "CAPTION SAFE"), (preset.watermark_safe, "#bd8cff", "watermark_safe_zone", "WATERMARK SAFE")):
            x1, y1, x2, y2 = rect.display_box(frame_left, frame_top, disp_w, disp_h)
            canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(8, 5), tags=("platform_safe_zone", tag))
            canvas.create_text(x1 + 5, y1 + 5, text=label, anchor="nw", fill=color, font=("TkDefaultFont", 8, "bold"), tags=("platform_safe_zone", tag))
            created += 1
        return created
    def safe_zone_display_dimensions(self, max_w=900, max_h=560):
        if not self.media or not self.media.width or not self.media.height:
            raise RuntimeError("Analyze a video before opening platform safe-zone guides")
        source_w, source_h = self.source_display_dimensions()
        out_w, out_h = source_w, source_h
        try:
            if self.resolution_var.get() != "Original":
                out_h = int(self.resolution_var.get().rstrip("p"))
                out_w = int(round(source_w * out_h / max(1, source_h) / 2) * 2)
        except Exception:
            pass
        factor = min(1.0, float(max_w) / max(1, out_w), float(max_h) / max(1, out_h))
        return out_w, out_h, max(1, int(round(out_w * factor))), max(1, int(round(out_h * factor)))
    def open_platform_safe_zone_viewer(self):
        try:
            preset = self.selected_safe_zone_preset()
            if preset is None:
                self.error_ui("Choose a platform safe-zone guide first")
                return
            out_w, out_h, disp_w, disp_h = self.safe_zone_display_dimensions()
            pad = 34
            top = tk.Toplevel(self.root)
            top.title(f"Platform Safe Zones - {preset.name}")
            top.transient(self.root)
            top.columnconfigure(0, weight=1)
            ttk.Label(top, text=f"{preset.name}  |  video/output frame {out_w}x{out_h}  |  aspect hint {preset.aspect_hint}", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
            ttk.Label(top, text="Guide only - nothing shown here is burned. Red = likely platform UI; green = caption-safe; purple = watermark-safe.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", padx=10)
            ttk.Label(top, text=preset.note, style="Muted.TLabel", wraplength=920).grid(row=2, column=0, sticky="w", padx=10, pady=(2, 6))
            canvas = tk.Canvas(top, width=disp_w + pad * 2, height=disp_h + pad * 2, bg="#303030", highlightthickness=0)
            canvas.grid(row=3, column=0, padx=10, pady=6)
            left = top_px = pad
            canvas.create_rectangle(left, top_px, left + disp_w, top_px + disp_h, fill="#0d0d0d", outline="#f2f2f2", width=3, tags=("video_edge",))
            self.draw_platform_safe_zone_guides(canvas, left, top_px, disp_w, disp_h, preset)
            canvas.create_text(left, top_px - 10, text="TOP-LEFT (0,0)", anchor="sw", fill="#f2f2f2", tags=("frame_label",))
            canvas.create_text(left + disp_w, top_px + disp_h + 10, text=f"BOTTOM-RIGHT ({out_w},{out_h})", anchor="ne", fill="#f2f2f2", tags=("frame_label",))
            ttk.Button(top, text="Close", command=top.destroy).grid(row=4, column=0, sticky="e", padx=10, pady=(4, 10))
            self._safe_zone_viewer = top
            self._safe_zone_viewer_canvas = canvas
        except Exception as exc:
            self.error_ui(f"Safe-zone viewer failed: {exc}")
    def open_watermark_layout_editor(self):
        try:
            if not self.media:
                self.error_ui("Analyze a video before opening the watermark layout editor")
                return
            if not self.watermark_enabled_var.get() or self.watermark_type_var.get() != "Image":
                self.error_ui("Enable an image watermark first")
                return
            if self.watermark_timing_var.get() != "Full duration":
                self.error_ui("The layout editor currently supports Full duration image watermarks")
                return
            image_path = Path(self.watermark_image_var.get().strip())
            if not image_path.is_file():
                self.error_ui("Select a valid watermark image")
                return
            job = self.snapshot_job()
            if getattr(self, "_wm_layout_window", None) is not None:
                try:
                    if self._wm_layout_window.winfo_exists():
                        self._wm_layout_window.destroy()
                except Exception:
                    pass
            td = Path(tempfile.mkdtemp(prefix="subburn-wm-layout-"))
            img_path, info = self.render_watermark_layout_preview(job, td)
            factor = min(1.0, 900.0 / info["out_w"], 520.0 / info["out_h"])
            disp_w = max(1, int(round(info["out_w"] * factor)))
            disp_h = max(1, int(round(info["out_h"] * factor)))
            workspace_pad = 34
            top = tk.Toplevel(self.root)
            top.title("Watermark Layout Editor")
            top.transient(self.root)
            top.grab_set()
            self._wm_layout_window = top
            top.columnconfigure(0, weight=1)
            ttk.Label(top, text=f"Video {info['out_w']}x{info['out_h']}  |  watermark visible source {info['content_w']}x{info['content_h']}  |  100% = natural visible size", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
            ttk.Label(top, text="Gray area = outside the video. White border = exact video edge. Dashed box = current margin. Crosshair = exact center.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
            guidebar = ttk.Frame(top)
            guidebar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))
            guidebar.columnconfigure(1, weight=1)
            ttk.Label(guidebar, text="Platform guide").grid(row=0, column=0, sticky="w")
            platform_combo = ttk.Combobox(guidebar, textvariable=self.platform_safe_zone_var, values=SAFE_ZONE_PRESET_NAMES, state="readonly")
            platform_combo.grid(row=0, column=1, sticky="ew", padx=(12, 0))
            ttk.Label(guidebar, text="Guide only; never burned", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(12, 0))
            canvas = tk.Canvas(top, width=disp_w + workspace_pad * 2, height=disp_h + workspace_pad * 2, bg="#303030", highlightthickness=0)
            canvas.grid(row=3, column=0, padx=10, pady=6)
            frame_left = workspace_pad
            frame_top = workspace_pad
            frame_right = workspace_pad + disp_w
            frame_bottom = workspace_pad + disp_h
            canvas.create_rectangle(frame_left, frame_top, frame_right, frame_bottom, fill="#0d0d0d", outline="#f2f2f2", width=3, tags=("layout_guide", "video_edge"))
            margin_px = max(0, int(round(float(self.watermark_margin_var.get() or 0))))
            margin_disp = min(int(round(margin_px * factor)), max(0, (min(disp_w, disp_h) // 2) - 2))
            if margin_disp > 0:
                canvas.create_rectangle(frame_left + margin_disp, frame_top + margin_disp, frame_right - margin_disp, frame_bottom - margin_disp, outline="#f0b74a", width=2, dash=(7, 5), tags=("layout_guide", "margin_guide"))
                canvas.create_text(frame_left + margin_disp + 6, frame_top + margin_disp + 6, text=f"MARGIN {margin_px}px", anchor="nw", fill="#f0b74a", font=("TkDefaultFont", 9, "bold"), tags=("layout_guide", "margin_guide"))
            center_x_disp = frame_left + disp_w / 2
            center_y_disp = frame_top + disp_h / 2
            canvas.create_line(center_x_disp, frame_top, center_x_disp, frame_bottom, fill="#69c7ff", width=1, dash=(5, 5), tags=("layout_guide", "center_guide"))
            canvas.create_line(frame_left, center_y_disp, frame_right, center_y_disp, fill="#69c7ff", width=1, dash=(5, 5), tags=("layout_guide", "center_guide"))
            canvas.create_oval(center_x_disp - 6, center_y_disp - 6, center_x_disp + 6, center_y_disp + 6, outline="#69c7ff", width=2, tags=("layout_guide", "center_guide"))
            canvas.create_line(center_x_disp - 11, center_y_disp, center_x_disp + 11, center_y_disp, fill="#69c7ff", width=2, tags=("layout_guide", "center_guide"))
            canvas.create_line(center_x_disp, center_y_disp - 11, center_x_disp, center_y_disp + 11, fill="#69c7ff", width=2, tags=("layout_guide", "center_guide"))
            canvas.create_text(center_x_disp + 10, center_y_disp - 10, text="CENTER", anchor="sw", fill="#69c7ff", font=("TkDefaultFont", 9, "bold"), tags=("layout_guide", "center_guide"))
            canvas.create_text(frame_left, frame_top - 10, text="TOP-LEFT  (0,0)", anchor="sw", fill="#f2f2f2", font=("TkDefaultFont", 8), tags=("layout_guide",))
            canvas.create_text(frame_right, frame_bottom + 10, text=f"BOTTOM-RIGHT  ({info['out_w']},{info['out_h']})", anchor="ne", fill="#f2f2f2", font=("TkDefaultFont", 8), tags=("layout_guide",))
            self.draw_platform_safe_zone_guides(canvas, frame_left, frame_top, disp_w, disp_h)
            controls = ttk.Frame(top)
            controls.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
            controls.columnconfigure(1, weight=1)
            scale_var = tk.DoubleVar(value=float(job.watermark_image_scale or 100.0))
            snap_center_var = tk.BooleanVar(value=True)
            coord_var = tk.StringVar()
            photo = tk.PhotoImage(file=str(img_path))
            item = canvas.create_image(frame_left + int(round(info['x'] * factor)), frame_top + int(round(info['y'] * factor)), anchor='nw', image=photo, tags=("watermark_item",))
            state = {"job": job, "tmpdir": td, "canvas": canvas, "factor": factor, "photo": photo, "item": item, "top": top, "x": int(info['x']), "y": int(info['y']), "render_w": int(info['render_w']), "render_h": int(info['render_h']), "out_w": int(info['out_w']), "out_h": int(info['out_h']), "scale_var": scale_var, "coord_var": coord_var, "frame_left": frame_left, "frame_top": frame_top, "snap_x": False, "snap_y": False, "snap_center_var": snap_center_var}
            self._wm_layout_state = state
            canvas.tag_raise(item)
            def redraw_platform_guides(_event=None):
                self.draw_platform_safe_zone_guides(canvas, frame_left, frame_top, disp_w, disp_h)
                canvas.tag_raise(item)
            platform_combo.bind("<<ComboboxSelected>>", redraw_platform_guides)
            def refresh_coords():
                center_dx = int(round((state['x'] + state['render_w'] / 2) - state['out_w'] / 2))
                center_dy = int(round((state['y'] + state['render_h'] / 2) - state['out_h'] / 2))
                snap_bits = []
                if state.get('snap_x'):
                    snap_bits.append('horizontal center')
                if state.get('snap_y'):
                    snap_bits.append('vertical center')
                snap_text = f"   |   SNAPPED: {' + '.join(snap_bits)}" if snap_bits else ""
                coord_var.set(f"X={state['x']} px   Y={state['y']} px   Size={state['render_w']}x{state['render_h']} px   Scale={float(scale_var.get()):g}%   |   center offset ΔX={center_dx}, ΔY={center_dy}{snap_text}")
            def place_item():
                canvas.coords(item, state['frame_left'] + int(round(state['x'] * factor)), state['frame_top'] + int(round(state['y'] * factor)))
                canvas.tag_raise(item)
            def refresh_image(*_args):
                try:
                    state['job'].watermark_image_scale = f"{float(scale_var.get()):g}"
                    state['job'].watermark_image_x = str(state['x'])
                    state['job'].watermark_image_y = str(state['y'])
                    imgp, inf = self.render_watermark_layout_preview(state['job'], td)
                    state['photo'] = tk.PhotoImage(file=str(imgp))
                    canvas.itemconfigure(item, image=state['photo'])
                    state['render_w'] = int(inf['render_w'])
                    state['render_h'] = int(inf['render_h'])
                    state['out_w'] = int(inf['out_w'])
                    state['out_h'] = int(inf['out_h'])
                    state['x'] = max(0, min(state['x'], state['out_w'] - state['render_w']))
                    state['y'] = max(0, min(state['y'], state['out_h'] - state['render_h']))
                    state['snap_x'] = False
                    state['snap_y'] = False
                    place_item()
                    refresh_coords()
                except Exception as e:
                    self.error_ui(f"Layout preview failed: {e}")
            ttk.Label(controls, text="Scale %").grid(row=0, column=0, sticky="w")
            sc = ttk.Scale(controls, from_=1, to=300, variable=scale_var, orient='horizontal', command=lambda *_: refresh_image())
            sc.grid(row=0, column=1, sticky='ew', padx=(12, 12))
            ttk.Checkbutton(controls, text="Snap to center while dragging", variable=snap_center_var).grid(row=0, column=2, sticky="w", padx=(12, 0))
            ttk.Label(controls, textvariable=coord_var).grid(row=1, column=0, columnspan=3, sticky='w', pady=(8, 0))
            drag = {"dx": 0, "dy": 0}
            def on_press(ev):
                cx, cy = canvas.coords(item)
                drag['dx'] = ev.x - cx
                drag['dy'] = ev.y - cy
            def on_move(ev):
                nx = int(round((ev.x - drag['dx'] - state['frame_left']) / factor))
                ny = int(round((ev.y - drag['dy'] - state['frame_top']) / factor))
                nx = max(0, min(nx, state['out_w'] - state['render_w']))
                ny = max(0, min(ny, state['out_h'] - state['render_h']))
                state['snap_x'] = False
                state['snap_y'] = False
                if snap_center_var.get():
                    center_x = max(0, int(round((state['out_w'] - state['render_w']) / 2)))
                    center_y = max(0, int(round((state['out_h'] - state['render_h']) / 2)))
                    snap_threshold = max(4, int(round(14 / max(0.001, factor))))
                    if abs(nx - center_x) <= snap_threshold:
                        nx = center_x
                        state['snap_x'] = True
                    if abs(ny - center_y) <= snap_threshold:
                        ny = center_y
                        state['snap_y'] = True
                state['x'], state['y'] = nx, ny
                place_item()
                refresh_coords()
            state["on_press"] = on_press
            state["on_move"] = on_move
            canvas.tag_bind(item, '<ButtonPress-1>', on_press)
            canvas.tag_bind(item, '<B1-Motion>', on_move)
            btns = ttk.Frame(controls)
            btns.grid(row=2, column=0, columnspan=3, sticky='w', pady=(10, 0))
            def center():
                state['x'] = max(0, int(round((state['out_w'] - state['render_w']) / 2)))
                state['y'] = max(0, int(round((state['out_h'] - state['render_h']) / 2)))
                state['snap_x'] = True
                state['snap_y'] = True
                place_item()
                refresh_coords()
            def reset():
                scale_var.set(100.0)
                state['x'], state['y'] = self.preset_overlay_xy(self.watermark_position_var.get(), int(float(self.watermark_margin_var.get() or 20)), state['out_w'], state['out_h'], state['render_w'], state['render_h'])
                state['snap_x'] = False
                state['snap_y'] = False
                refresh_image()
            def use_preset():
                scale_var.set(100.0)
                state['job'].watermark_image_x = ""
                state['job'].watermark_image_y = ""
                state['x'], state['y'] = self.preset_overlay_xy(self.watermark_position_var.get(), int(float(self.watermark_margin_var.get() or 20)), state['out_w'], state['out_h'], state['render_w'], state['render_h'])
                state['snap_x'] = False
                state['snap_y'] = False
                refresh_image()
            def apply_close():
                self.watermark_image_scale_var.set(f"{float(scale_var.get()):g}")
                self.watermark_image_x_var.set(str(state['x']))
                self.watermark_image_y_var.set(str(state['y']))
                self.autosave_project()
                self.publish_dashboard_controls()
                self.log_ui(f"Watermark layout saved: scale {float(scale_var.get()):g}% at X={state['x']}, Y={state['y']}")
                top.destroy()
            ttk.Button(btns, text='Center now', command=center).pack(side='left')
            ttk.Button(btns, text='Reset to 100%', command=reset).pack(side='left', padx=(12, 0))
            ttk.Button(btns, text='Use preset position', command=use_preset).pack(side='left', padx=(12, 0))
            ttk.Button(btns, text='Apply', command=apply_close).pack(side='left', padx=(16, 0))
            ttk.Button(btns, text='Cancel', command=top.destroy).pack(side='left', padx=(12, 0))
            refresh_coords()
        except Exception as e:
            self.error_ui(f"Layout editor failed: {e}")
    def watermark_image_geometry(self, image_path):
        image_path = Path(image_path)
        st = image_path.stat()
        cache = getattr(self, "_watermark_image_probe_cache", None)
        if cache is None:
            cache = {}
            self._watermark_image_probe_cache = cache
        toolset = getattr(self, "toolset", None)
        raw_ffmpeg = str(toolset.ffmpeg) if toolset is not None else str(getattr(self._job, "ffmpeg", "") or "")
        if not raw_ffmpeg:
            raw_ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        ffmpeg = Path(raw_ffmpeg)
        if toolset is not None:
            ffprobe = Path(toolset.ffprobe)
        else:
            ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.casefold() == ".exe" else "ffprobe")
            if not ffprobe.is_file():
                found_probe = shutil.which("ffprobe")
                if found_probe:
                    ffprobe = Path(found_probe)
        key = (str(image_path.resolve()), int(st.st_size), int(st.st_mtime_ns), str(ffmpeg))
        if key in cache:
            return cache[key]
        rc, out = run_capture([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,pix_fmt", "-of", "json", image_path], timeout=15)
        if rc != 0:
            raise RuntimeError("Could not inspect watermark image: " + out[-1200:])
        try:
            stream = (json.loads(out).get("streams") or [{}])[0]
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            pix_fmt = str(stream.get("pix_fmt") or "").casefold()
        except Exception as exc:
            raise RuntimeError(f"Could not read watermark image dimensions: {exc}")
        if width <= 0 or height <= 0:
            raise RuntimeError("Watermark image has invalid dimensions")
        alpha = ("rgba" in pix_fmt or "bgra" in pix_fmt or "argb" in pix_fmt or "abgr" in pix_fmt or pix_fmt.startswith("yuva") or pix_fmt.startswith("gbrap") or pix_fmt.startswith("ya"))
        crop = None
        if alpha:
            rc2, out2 = run_capture([ffmpeg, "-hide_banner", "-loglevel", "info", "-i", image_path, "-vf", "alphaextract,bbox", "-frames:v", "1", "-an", "-f", "null", "-"], timeout=20)
            matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", out2)
            if matches:
                cw, ch, cx, cy = map(int, matches[-1])
                if cw > 0 and ch > 0:
                    crop = (cw, ch, cx, cy)
            elif rc2 == 0:
                raise RuntimeError("Watermark image is fully transparent")
            else:
                self.log("Watermark alpha-content detection unavailable; using the full image canvas")
        result = {"width": width, "height": height, "pix_fmt": pix_fmt, "crop": crop}
        cache[key] = result
        return result
    def build_bitmap_filter(self, td, fonts_dir, preview_offset=0.0):
        plan = self.bitmap_subtitle_input_plan(preview_offset)
        if not plan:
            raise RuntimeError("Bitmap subtitle render plan is unavailable")
        codec = plan["codec"]
        graph_parts = ["[0:v]setpts=PTS-STARTPTS[v0]"]
        # FFmpeg's current documented compatibility path accepts a bitmap subtitle stream as
        # overlay's second input and internally converts it to an alpha video stream. Burn at
        # source resolution first so original subtitle placement scales together with the video.
        graph_parts.append(f"[v0][{plan['stream']}]overlay=eof_action=pass[vsub]")
        current = "vsub"
        watermark_renderer = None
        watermark_active = False
        tail = []
        if self._job.watermark_enabled and self._job.watermark_type == "Text":
            wm_font = self.selected_font(True if not self._job.same_wm_font else False)
            wm_ass = self.prepare_universal_text_watermark_ass(td, fonts_dir, wm_font, preview_offset=preview_offset)
            if wm_ass is not None:
                tail.append(f"ass={wm_ass.name}:fontsdir={Path(fonts_dir).name}")
                watermark_renderer = "libass/HarfBuzz/FriBidi + font runs"
                watermark_active = True
        if self._job.resolution != "Original":
            h = int(self._job.resolution.rstrip("p"))
            tail.append(f"scale=-2:{h}:flags=lanczos")
        if self._job.fps != "Original":
            tail.append(f"fps={self._job.fps}")
        if tail:
            graph_parts.append(f"[{current}]" + ",".join(tail) + "[vbase]")
            current = "vbase"
        extra = list(plan["extra"])
        if self._job.watermark_enabled and self._job.watermark_type == "Image":
            opacity = max(0.0, min(1.0, float(self._job.watermark_opacity)))
            margin = int(float(self._job.watermark_margin))
            rows = getattr(self._job, "watermark_rows", []) if self._job.watermark_timing == "Intervals" else []
            img = Path(self._job.watermark_image)
            local_img = Path(td) / ("watermark" + img.suffix.lower())
            shutil.copy2(img, local_img)
            box = self.watermark_image_render_box(self._job)
            if rows:
                x = dynamic_axis(rows, margin, "image", "x", preview_offset)
                y = dynamic_axis(rows, margin, "image", "y", preview_offset)
                enable = interval_enable(rows, preview_offset)
            else:
                if box["custom"]:
                    x, y = str(box["x"]), str(box["y"])
                else:
                    x, y = position_expr(self._job.watermark_position, margin, "image")
                enable = None
            crop = box.get("crop")
            source_w, source_h = int(box["source_w"]), int(box["source_h"])
            content_w, content_h = int(box["content_w"]), int(box["content_h"])
            scale_w, scale_h = int(box["render_w"]), int(box["render_h"])
            if crop and (content_w != source_w or content_h != source_h or crop[2] or crop[3]):
                image_chain = f"crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]},scale={scale_w}:-2:flags=lanczos,format=rgba"
            else:
                image_chain = f"scale={scale_w}:-2:flags=lanczos,format=rgba"
            if opacity < 0.999:
                image_chain += f",colorchannelmixer=aa={opacity:.3f}"
            wm_input = 2 if plan["external"] else 1
            extra += ["-loop", "1", "-i", str(local_img)]
            graph_parts.append(f"[{wm_input}:v]{image_chain}[wm]")
            overlay = f"[{current}][wm]overlay=x={x}:y={y}:eof_action=repeat:repeatlast=1:shortest=1"
            if enable:
                overlay += f":enable='{enable}'"
            overlay += "[vout]"
            graph_parts.append(overlay)
            watermark_renderer = "overlay"
            watermark_active = True
        else:
            graph_parts.append(f"[{current}]null[vout]")
        self.log(f"Bitmap subtitle renderer: {codec} -> FFmpeg bitmap overlay | source={'external' if plan['external'] else 'embedded'}")
        return {
            "mode": "complex", "filter": ";".join(graph_parts), "extra": extra, "map": "[vout]",
            "subtitle_renderer": f"bitmap/{codec} overlay", "watermark_renderer": watermark_renderer,
            "watermark_active": watermark_active, "bitmap_subtitles": True,
        }
    def build_filter(self, td, subtitle_file, fonts_dir, primary, preview_offset=0.0, raster_subtitles=None):
        if self.subtitle_kind() == "bitmap":
            return self.build_bitmap_filter(td, fonts_dir, preview_offset=preview_offset)
        subtitle_cues = read_srt_cues(subtitle_file)
        subtitle_ass = self.prepare_universal_ass(td, subtitle_file, fonts_dir, primary, preview_offset=preview_offset) if subtitle_cues else None
        subtitle_renderer = "libass/HarfBuzz/FriBidi + font runs" if subtitle_ass is not None else "none (no cue in window)"
        watermark_renderer = None
        watermark_active = False
        wm_ass = None
        if self._job.watermark_enabled and self._job.watermark_type == "Text":
            wm_font = self.selected_font(True if not self._job.same_wm_font else False)
            wm_ass = self.prepare_universal_text_watermark_ass(td, fonts_dir, wm_font, preview_offset=preview_offset)
            if wm_ass is not None:
                watermark_renderer = "libass/HarfBuzz/FriBidi + font runs"
                watermark_active = True
        text_ass = self.merge_text_ass_layers(td, subtitle_ass, wm_ass)
        # Keep the one-pass architecture of the fast SubBurn 4x burner. A normal final render
        # with unchanged geometry/FPS and ASS text layers needs one libass filter and no setpts.
        direct_text_path = bool(
            text_ass is not None
            and (not self._job.watermark_enabled or self._job.watermark_type == "Text")
            and self._job.resolution == "Original"
            and self._job.fps == "Original"
            and abs(float(preview_offset or 0.0)) < 1e-9
        )
        chain = [] if direct_text_path else ["setpts=PTS-STARTPTS"]
        if text_ass is not None:
            chain.append(f"ass={text_ass.name}:fontsdir={Path(fonts_dir).name}")
        post = []
        if self._job.resolution != "Original":
            h = int(self._job.resolution.rstrip("p"))
            post.append(f"scale=-2:{h}:flags=lanczos")
        if self._job.fps != "Original":
            post.append(f"fps={self._job.fps}")
        if post:
            chain.extend(post)
        current_chain = ",".join(chain)
        if not self._job.watermark_enabled or self._job.watermark_type == "Text":
            return {"mode": "vf", "filter": current_chain, "extra": [], "map": None, "subtitle_renderer": subtitle_renderer, "watermark_renderer": watermark_renderer, "watermark_active": watermark_active}
        opacity = max(0.0, min(1.0, float(self._job.watermark_opacity)))
        margin = int(float(self._job.watermark_margin))
        rows = getattr(self._job, "watermark_rows", []) if self._job.watermark_timing == "Intervals" else []
        img = Path(self._job.watermark_image)
        local_img = td / ("watermark" + img.suffix.lower())
        shutil.copy2(img, local_img)
        box = self.watermark_image_render_box(self._job)
        if rows:
            x = dynamic_axis(rows, margin, "image", "x", preview_offset)
            y = dynamic_axis(rows, margin, "image", "y", preview_offset)
            enable = interval_enable(rows, preview_offset)
        else:
            if box["custom"]:
                x, y = str(box["x"]), str(box["y"])
            else:
                x, y = position_expr(self._job.watermark_position, margin, "image")
            enable = None
        crop = box.get("crop")
        source_w, source_h = int(box["source_w"]), int(box["source_h"])
        content_w, content_h = int(box["content_w"]), int(box["content_h"])
        scale_w, scale_h = int(box["render_w"]), int(box["render_h"])
        if crop and (content_w != source_w or content_h != source_h or crop[2] or crop[3]):
            image_chain = f"crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]},scale={scale_w}:-2:flags=lanczos,format=rgba"
            self.log(f"Watermark image: source {source_w}x{source_h} | visible alpha content {content_w}x{content_h} at {crop[2]},{crop[3]} | scaled visible content about {scale_w}x{scale_h} ({float(box['scale_pct']):g}% natural size)")
        else:
            image_chain = f"scale={scale_w}:-2:flags=lanczos,format=rgba"
            self.log(f"Watermark image: source/content {source_w}x{source_h} | scaled about {scale_w}x{scale_h} ({float(box['scale_pct']):g}% natural size)")
        if box.get("fit_capped"):
            self.log(f"Watermark fit cap applied to keep the image inside the video frame ({box['out_w']}x{box['out_h']})")
        if opacity < 0.999:
            image_chain += f",colorchannelmixer=aa={opacity:.3f}"
        poslog = f"custom X={box['x']}, Y={box['y']}" if box.get("custom") and not rows else self._job.watermark_position
        self.log(f"Watermark image opacity {opacity * 100:.0f}% | position {poslog} | timing {self._job.watermark_timing}")
        extra = ["-loop", "1", "-i", str(local_img)]
        graph_parts = [f"[0:v]{current_chain}[base]", f"[1:v]{image_chain}[wm]"]
        overlay = f"[base][wm]overlay=x={x}:y={y}:eof_action=repeat:repeatlast=1:shortest=1"
        if enable:
            overlay += f":enable='{enable}'"
        overlay += "[vout]"
        graph_parts.append(overlay)
        return {"mode": "complex", "filter": ";".join(graph_parts), "extra": extra, "map": "[vout]", "subtitle_renderer": subtitle_renderer, "watermark_renderer": "overlay", "watermark_active": True}
    def verify_preview_filter_parity(self, filt, start, duration, label):
        rendered = str(filt.get("filter") or "")
        subtitle_renderer = str(filt.get("subtitle_renderer") or "libass/HarfBuzz/FriBidi + font runs")
        if subtitle_renderer.startswith("bitmap/"):
            if "overlay=" not in rendered:
                raise RuntimeError(f"{label} is missing the bitmap subtitle overlay filter")
        elif subtitle_renderer != "none (no cue in window)":
            subtitle_ass_present = (
                "ass=subtitle_render.ass" in rendered
                or (self._job.watermark_enabled and self._job.watermark_type == "Text" and "ass=subburn_text_layers.ass" in rendered)
            )
            if not subtitle_ass_present:
                raise RuntimeError(f"{label} is missing the subtitle render filter")
        if subtitle_renderer == "none (no cue in window)":
            self.log(f"{label}: no subtitle cue overlaps this preview window; rendering video/watermark without a subtitle filter")
        if not self._job.watermark_enabled:
            self.log(f"{label} parity: subtitles={subtitle_renderer} | watermark=disabled")
            return
        watermark_renderer = str(filt.get("watermark_renderer") or ("libass/HarfBuzz/FriBidi + font runs" if self._job.watermark_type == "Text" else "overlay"))
        active = bool(filt.get("watermark_active", self._job.watermark_type == "Image"))
        if self._job.watermark_timing == "Intervals":
            end = start + duration
            overlaps = [(a, b, pos) for a, b, pos in getattr(self._job, "watermark_rows", []) if b > start and a < end]
            if not overlaps:
                self.emit("warning", f"{label} window {fmt_time(start)}–{fmt_time(end)} does not overlap any enabled watermark interval, so the watermark will not be visible in this clip.")
                return
        if self._job.watermark_type == "Text":
            watermark_ass_present = (
                "ass=watermark_text_render.ass" in rendered
                or "ass=subburn_text_layers.ass" in rendered
            )
            if not active or not watermark_ass_present:
                raise RuntimeError(f"{label} is missing the enabled text watermark filter")
        elif "overlay=" not in rendered:
            raise RuntimeError(f"{label} is missing the enabled image watermark filter")
        if self._job.watermark_timing == "Intervals":
            self.log(f"{label} parity: subtitles={subtitle_renderer} | watermark={self._job.watermark_type.lower()} ({watermark_renderer}) | interval overlap={len(overlaps)}")
        else:
            self.log(f"{label} parity: subtitles={subtitle_renderer} | watermark={self._job.watermark_type.lower()} ({watermark_renderer}) | full duration")












    def audio_args(self, source_index=0):
        m=self._job.audio_mode;idx=int(source_index)
        if m=="No audio":return ["-an"]
        if m=="Copy first audio":return ["-map",f"{idx}:a:0?","-c:a","copy"]
        if m=="AAC 192k":return ["-map",f"{idx}:a:0?","-c:a","aac","-b:a","192k"]
        if m=="Opus 160k":return ["-map",f"{idx}:a:0?","-c:a","libopus","-b:a","160k"]
        return ["-map",f"{idx}:a?","-c:a","copy"]
    def output_audio_bitrate(self, job=None):
        job = job or self._job
        streams = list(self.media.audio_streams) if self.media else []
        mode = job.audio_mode
        if mode == "No audio" or not streams:
            return 0
        if mode == "AAC 192k":
            return 192000
        if mode == "Opus 160k":
            return 160000
        if mode == "Copy first audio":
            return int(streams[0].get("bitrate") or 128000)
        return sum(int(st.get("bitrate") or 128000) for st in streams)
    def target_container_overhead(self, total_bps):
        return max(8000, int(float(total_bps) * 0.005))
    def target_bitrate(self, job=None):
        job = job or self._job
        if not self.media:
            raise RuntimeError("Media not analyzed")
        mode = job.quality_mode
        if mode == "Custom bitrate":
            return max(20000, int(float(job.custom_bitrate) * 1000))
        if mode == "Target file size":
            mb = float(job.target_size)
            total_bps = mb * 1024 * 1024 * 8 / max(1, self.media.duration)
            audio = self.output_audio_bitrate(job)
            overhead = self.target_container_overhead(total_bps)
            video = total_bps - audio - overhead
            if video < 50000:
                minimum_mb = (audio + overhead + 50000) * max(1, self.media.duration) / 8 / 1024 / 1024
                raise RuntimeError(f"Target file size is too small for the selected audio mode. Use at least about {minimum_mb:.1f} MB or reduce/remove audio.")
            return int(video)
        if mode == "Match source size":
            return max(50000, self.media.video_bitrate)
        return max(100000, int(self.media.video_bitrate * 1.5))
    def codec_groups(self):
        groups = compatible_groups(self._job.output_ext, self._job.codec, self.media)
        if not groups:
            raise RuntimeError(
                f"Codec '{self._job.codec}' is not supported in output container "
                f"'{self._job.output_ext}'. Pick a different codec or output extension."
            )
        return groups
    def candidate_encoders(self):
        if not self.toolset:
            return []
        detected = set(self.toolset.encoders)
        out = []
        for group in self.codec_groups():
            for enc in AUTO_ENCODERS.get(group, []):
                if enc in detected:
                    out.append(enc)
        return out
    @staticmethod
    def output_attribution_args():
        return ["-metadata", f"{OUTPUT_MARKER_KEY}={OUTPUT_MARKER_VALUE}"]
    def encoder_test_cmd(self, enc, td, filt, args, seconds, use_full_filter, n):
        out_file = td / f"probe_{safe_filename(enc)}_{n}.mkv"
        out_file.unlink(missing_ok=True)
        cmd = [self.toolset.ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", "0", "-t", str(seconds), *self.bitmap_primary_input_options(), "-i", self._job.video]
        if use_full_filter:
            cmd += filt["extra"]
            if filt["mode"] == "complex":
                cmd += ["-filter_complex", filt["filter"], "-map", filt["map"]]
            else:
                cmd += ["-map", "0:v:0", "-vf", filt["filter"]]
        else:
            cmd += ["-map", "0:v:0", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]
        cmd += ["-an", "-sn", "-dn", "-c:v", enc, *args, "-b:v", str(self.target_bitrate()), *pixfmt_args(enc), *self.output_attribution_args(), "-f", "matroska", out_file]
        return cmd, out_file
    def test_encoder(self, enc, td, filt, seconds=1.25, full_filter=True):
        tuning = tuning_args(self.toolset.ffmpeg, enc, self._job.speed_mode, self.help_cache)
        attempts = []
        if tuning:
            attempts.append(tuning)
        attempts.append([])
        if enc == "libx264":
            attempts.append(["-preset", "ultrafast"] )
        filters = [True, False] if full_filter else [False]
        last = ""
        n = 0
        for use_full_filter in filters:
            for args in attempts:
                n += 1
                cmd, out_file = self.encoder_test_cmd(enc, td, filt, args, seconds, use_full_filter, n)
                start = time.monotonic()
                try:
                    rc, out = run_capture(cmd, cwd=td, timeout=max(20, int(seconds * 12)))
                except subprocess.TimeoutExpired:
                    rc, out = 124, "timeout"
                elapsed = max(0.001, time.monotonic() - start)
                if rc == 0 and out_file.exists() and out_file.stat().st_size > 0:
                    out_file.unlink(missing_ok=True)
                    self.tuning_cache[enc] = args
                    speed = seconds / elapsed
                    self.benchmark_scores[enc] = speed
                    if self.toolset:
                        encoder_cache_put(self.encoder_cache, ffmpeg_signature(self.toolset), enc, True, speed, args)
                    self.log(f"encoder probe pass: {enc} | {speed:.2f}x | tuning {args or 'default'} | filter {'full' if use_full_filter else 'basic'}")
                    return speed, args, ""
                last = out[-2500:] if out else "encoder failed without output"
                out_file.unlink(missing_ok=True)
                compact = " | ".join(x.strip() for x in last.splitlines() if x.strip())[:500]
                self.log(f"encoder probe fail: {enc} | tuning {args or 'default'} | filter {'full' if use_full_filter else 'basic'} | {compact}")
        if self.toolset:
            encoder_cache_put(self.encoder_cache, ffmpeg_signature(self.toolset), enc, False, 0, [])
        return 0, [], last[-2000:]
    def hardware_first_candidates(self):
        detected = set(self.toolset.encoders if self.toolset else [])
        out = []
        for group in self.codec_groups():
            for enc in AUTO_ENCODERS.get(group, []):
                if enc in detected and enc not in out:
                    out.append(enc)
        return out
    def software_candidates(self):
        detected = set(self.toolset.encoders if self.toolset else [])
        out = []
        for group in self.codec_groups():
            for enc in SOFTWARE_ENCODERS.get(group, []):
                if enc in detected and enc not in out:
                    out.append(enc)
        return out
    def cached_working_encoder(self, candidates):
        if not self.toolset:
            return None
        sig = ffmpeg_signature(self.toolset)
        best = None
        for enc in candidates:
            entry = encoder_cache_get(self.encoder_cache, sig, enc)
            if entry and entry.get("ok"):
                if best is None or entry.get("speed", 0) > best[1]:
                    best = (enc, entry.get("speed", 0), entry.get("args", []))
        if best:
            enc, speed, args = best
            self.tuning_cache[enc] = args
            return enc
        return None
    def choose_encoder(self, td, filt, for_preview=False):
        selected = self._job.encoder
        if selected != "Auto":
            cached = encoder_cache_get(self.encoder_cache, ffmpeg_signature(self.toolset), selected) if self.toolset else None
            if cached and cached.get("ok"):
                self.tuning_cache[selected] = cached.get("args", [])
                self.set_stage("Encoder", 100, f"Using {selected} (cached)")
                return selected
            self.set_stage("Encoder", 20, f"Testing {selected}")
            score, args, err = self.test_encoder(selected, td, filt, seconds=0.35 if for_preview else 0.55, full_filter=False)
            if score <= 0:
                raise RuntimeError(f"Selected encoder failed: {err}")
            self.set_stage("Encoder", 100, f"Using {selected}")
            return selected
        policy = self._job.encoder_policy
        hw = self.hardware_first_candidates()
        sw = self.software_candidates()
        if policy == "Best CPU quality":
            ordered = sw
        else:
            ordered = hw + [e for e in sw if e not in hw]
        if policy == "Fastest measured":
            sig = ffmpeg_signature(self.toolset) if self.toolset else None
            measured = [(e, encoder_cache_get(self.encoder_cache, sig, e)) for e in ordered] if sig else []
            measured = [(e, entry) for e, entry in measured if entry and entry.get("ok")]
            if measured:
                measured.sort(key=lambda x: x[1].get("speed", 0), reverse=True)
                enc, entry = measured[0]
                self.tuning_cache[enc] = entry.get("args", [])
                self.log(f"encoder selected (fastest measured, cached): {enc}")
                self.set_stage("Encoder", 100, f"Using {enc}")
                return enc
        cached = self.cached_working_encoder(ordered)
        if cached:
            self.log(f"encoder selected from cache: {cached}")
            self.set_stage("Encoder", 100, f"Using {cached} (cached)")
            return cached
        if not ordered:
            raise RuntimeError(
                f"No compatible video encoder was detected for codec '{self._job.codec}' "
                f"and output container '{self._job.output_ext}'. Check the selected FFmpeg build or choose another codec."
            )
        sig = ffmpeg_signature(self.toolset) if self.toolset else None
        def known_bad(enc):
            if not sig:
                return False
            entry = encoder_cache_get(self.encoder_cache, sig, enc)
            return bool(entry) and not entry.get("ok")
        all_known_bad_at_start = all(known_bad(enc) for enc in ordered)
        self.log("encoder candidates: " + ", ".join(ordered))
        self.set_stage("Encoder", 15, "Probing encoders")
        probe_seconds = 0.25 if for_preview else 0.35
        untested = [enc for enc in ordered if not known_bad(enc)]
        probe_pool = untested[:2] if for_preview else untested[:6]
        tried = set()
        for i, enc in enumerate(probe_pool):
            tried.add(enc)
            self.set_stage("Encoder", 20 + i * 10, f"Testing {enc}")
            score, args, err = self.test_encoder(enc, td, filt, seconds=probe_seconds, full_filter=False)
            if score > 0:
                self.set_stage("Encoder", 100, f"Using {enc}")
                return enc
        if policy != "Best CPU quality":
            for enc in sw:
                if enc in tried or known_bad(enc):
                    continue
                tried.add(enc)
                self.set_stage("Encoder", 90, f"Testing fallback {enc}")
                score, args, err = self.test_encoder(enc, td, filt, seconds=probe_seconds, full_filter=False)
                if score > 0:
                    self.set_stage("Encoder", 100, f"Using {enc} (fallback)")
                    return enc
        if all_known_bad_at_start:
            enc = ordered[0]
            self.set_stage("Encoder", 95, f"Re-checking {enc}")
            score, args, err = self.test_encoder(enc, td, filt, seconds=probe_seconds, full_filter=False)
            if score > 0:
                self.set_stage("Encoder", 100, f"Using {enc}")
                return enc
            raise RuntimeError(
                "No encoder initialized successfully. All compatible encoders were previously cached as failed "
                f"for this FFmpeg build; {enc} was re-tested once and still failed. "
                "Use Quick probe or Benchmark to force a fresh full re-test, or check GPU drivers/FFmpeg compatibility."
            )
        tried_text = ", ".join(tried) if tried else "none"
        raise RuntimeError(
            "No encoder initialized successfully. Encoders tested this run: " + tried_text + ". "
            "Use Quick probe or Benchmark for a full re-test, or check GPU drivers/FFmpeg compatibility."
        )
    def validate_async(self):
        if not self.require_batch_idle("Validate"):
            return None
        return self.run_job(self.validate_worker, operation_type="validation")
    def validate_worker(self):
        try:
            self.validate_common()
            with tempfile.TemporaryDirectory(prefix="SubBurn_validate_") as t:
                td = Path(t)
                self.set_stage("Subtitles", 30, "Preparing subtitles")
                sub = self.prepare_subtitles(td)
                self.set_stage("Fonts", 50, "Preparing runtime fonts")
                fonts_dir, primary, fonts = self.copy_fonts(td)
                self.set_stage("Glyphs", 40, "Checking glyph coverage")
                missing, report = self.validate_glyphs(sub, fonts)
                for line in report:
                    self.log(line)
                self.emit_missing_glyph_warning(missing)
                raster = None
                self.set_stage("Filters", 25, "Building validation render")
                filt = self.build_filter(td, sub, fonts_dir, primary, raster_subtitles=raster)
                self.set_stage("Filters", 60, "Testing subtitle renderer")
                if filt["mode"] == "complex":
                    cmd = [self.toolset.ffmpeg, "-hide_banner", "-loglevel", "verbose", "-t", "1", *self.bitmap_primary_input_options(), "-i", self._job.video] + filt["extra"] + ["-filter_complex", filt["filter"], "-map", filt["map"], "-frames:v", "1", "-an", "-f", "null", "NUL" if IS_WINDOWS else "/dev/null"]
                else:
                    cmd = [self.toolset.ffmpeg, "-hide_banner", "-loglevel", "verbose", "-f", "lavfi", "-i", "color=c=black:s=640x360:r=25:d=1", "-vf", filt["filter"], "-frames:v", "1", "-an", "-f", "null", "NUL" if IS_WINDOWS else "/dev/null"]
                rc, out = run_capture(cmd, cwd=td, timeout=40)
                for line in out.splitlines():
                    if "fontselect" in line.casefold():
                        self.log("font renderer: " + line.strip())
                if rc != 0:
                    raise RuntimeError(out[-2000:])
            self.emit("status", "Validation passed")
        except Exception as e:
            self.emit("error", f"Validation failed: {e}")
    def probe_encoders_async(self):
        if not self.require_batch_idle("Encoder probe"):
            return None
        return self.run_job(self.probe_encoders_worker, operation_type="encoder_probe")
    def probe_encoders_worker(self):
        try:
            self.validate_common()
            with tempfile.TemporaryDirectory(prefix="SubBurn_probe_") as t:
                td = Path(t)
                sub = self.prepare_subtitles(td, 0, 1)
                fonts_dir, primary, fonts = self.copy_fonts(td)
                filt = self.build_filter(td, sub, fonts_dir, primary)
                candidates = self.candidate_encoders()
                if not candidates:
                    raise RuntimeError("No compatible encoders were detected for the selected format")
                op_id = self.current_operation_id()
                for i, enc in enumerate(candidates):
                    self.set_stage("Encoder", 0, f"Testing {enc} ({i + 1}/{len(candidates)})")
                    score, args, err = self.test_encoder(enc, td, filt, seconds=0.5)
                    self.log(f"probe {enc}: {'pass' if score > 0 else 'fail'} {score:.2f}x")
                    if op_id:
                        self.op_state.set_overall(op_id, min(99.0, (i + 1) / len(candidates) * 99.0), f"Tested {i + 1}/{len(candidates)} encoders")
                self.set_stage("Encoder", 0, "Encoder test complete")
            self.emit("status", "Probe complete")
        except Exception as e:
            self.emit("error", f"Probe failed: {e}")
    def benchmark_async(self):
        if not self.require_batch_idle("Encoder benchmark"):
            return None
        return self.run_job(self.benchmark_worker, operation_type="encoder_benchmark")
    def benchmark_worker(self):
        try:
            self.validate_common()
            with tempfile.TemporaryDirectory(prefix="SubBurn_bench_") as t:
                td = Path(t)
                sub = self.prepare_subtitles(td, 0, 2)
                fonts_dir, primary, fonts = self.copy_fonts(td)
                filt = self.build_filter(td, sub, fonts_dir, primary)
                results = []
                candidates = self.candidate_encoders()
                if not candidates:
                    raise RuntimeError("No compatible encoders were detected for the selected format")
                op_id = self.current_operation_id()
                for i, enc in enumerate(candidates):
                    self.set_stage("Encoder", 0, f"Benchmarking {enc} ({i + 1}/{len(candidates)})")
                    score, args, err = self.test_encoder(enc, td, filt, seconds=2)
                    if score > 0:
                        results.append((enc, score))
                        self.log(f"benchmark {enc}: {score:.2f}x")
                    else:
                        self.log(f"benchmark {enc}: failed")
                    if op_id:
                        self.op_state.set_overall(op_id, min(99.0, (i + 1) / len(candidates) * 99.0), f"Benchmarked {i + 1}/{len(candidates)} encoders")
                self.set_stage("Encoder", 0, "Benchmark complete")
            results.sort(key=lambda x: x[1], reverse=True)
            self.log("benchmark ranking: " + ", ".join(f"{a} {b:.2f}x" for a, b in results))
            self.emit("status", "Benchmark complete")
        except Exception as e:
            self.emit("error", f"Benchmark failed: {e}")
    def live_clip_worker(self):
        out = None
        try:
            self.validate_common()
            if "libx264" not in self.toolset.encoders:
                raise RuntimeError("Playback preview requires an FFmpeg build with libx264")
            start = float(getattr(self._job, "live_clip_timestamp", 0.0))
            duration = float(getattr(self._job, "live_clip_duration", 8.0))
            generation = int(getattr(self._job, "live_clip_generation", 0))
            open_when_ready = bool(getattr(self._job, "live_clip_open", False))
            self.set_stage("Preview", 8, f"Preparing playback preview at {fmt_time(start)}")
            PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            out = PREVIEW_DIR / f"SubBurn-live-clip-{int(time.time() * 1000)}-{generation}.mp4"
            with tempfile.TemporaryDirectory(prefix="SubBurn_live_clip_") as t:
                td = Path(t)
                sub = self.prepare_subtitles(td, start, duration)
                fonts_dir, primary, fonts = self.copy_fonts(td)
                missing, report = self.validate_glyphs(sub, fonts)
                for line in report:
                    self.log(line)
                self.emit_missing_glyph_warning(missing)
                raster = None
                filt = self.live_proxy_filter(self.build_filter(td, sub, fonts_dir, primary, preview_offset=start, raster_subtitles=raster))
                self.verify_preview_filter_parity(filt, start, duration, "Live playback")
                cmd = [self.toolset.ffmpeg, "-hide_banner", "-loglevel", "verbose", "-y", "-ss", f"{start:.6f}", "-t", f"{duration:.6f}", *self.bitmap_primary_input_options(), "-i", self._job.video]
                cmd += filt["extra"]
                if filt["mode"] == "complex":
                    cmd += ["-filter_complex", filt["filter"], "-map", filt["map"]]
                else:
                    cmd += ["-map", "0:v:0", "-vf", filt["filter"]]
                cmd += ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "96k", "-sn", "-dn", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-pix_fmt", "yuv420p", "-t", f"{duration:.6f}", *self.output_attribution_args(), "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(out)]
                self.set_stage("Preview", 0, f"Rendering {duration:.1f}s playback preview")
                # Fixed-duration playback previews have a real denominator. Ask FFmpeg for
                # machine-readable progress so both UIs report truthful percentage/FPS/speed/ETA.
                proc = subprocess.Popen([str(x) for x in cmd], cwd=str(td), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1, creationflags=CREATE_NO_WINDOW)
                self.register_render_process(proc, "live_clip")
                lines=[]; current=0.0; fps="-"; speed="-"
                timed_out=threading.Event()
                def _live_clip_timeout():
                    if proc.poll() is None:
                        timed_out.set()
                        try: proc.kill()
                        except Exception: pass
                timeout_timer=threading.Timer(75.0,_live_clip_timeout); timeout_timer.daemon=True; timeout_timer.start()
                try:
                    assert proc.stdout is not None
                    for raw in proc.stdout:
                        line=raw.rstrip(); lines.append(line)
                        if "fontselect" in line.casefold():
                            self.log("Live playback " + line.strip())
                        if "=" not in line:
                            continue
                        key,value=line.split("=",1)
                        if key in {"out_time_us","out_time_ms"}:
                            try: current=int(value)/1000000.0
                            except Exception: pass
                        elif key=="fps": fps=value.strip() or "-"
                        elif key=="speed": speed=value.strip() or "-"
                        elif key=="progress":
                            pct=min(100.0,max(0.0,current/max(duration,0.001)*100.0))
                            try: factor=float(speed.rstrip("x"))
                            except Exception: factor=0.0
                            eta=(duration-current)/factor if factor>0 and duration>current else (0.0 if current>=duration else None)
                            self.set_stage("Preview", pct, f"Rendering playback preview {pct:.1f}%")
                            self.emit("progress", pct, fps, speed, fmt_time(eta))
                    rc=proc.wait()
                    if timed_out.is_set():
                        raise RuntimeError("Playback preview timed out after 75 seconds: " + "\n".join(lines)[-1800:])
                    cancelled=self.process_was_cancelled(proc)
                    text="\n".join(lines)
                finally:
                    timeout_timer.cancel()
                    self.unregister_render_process(proc)
                if cancelled:
                    out.unlink(missing_ok=True)
                    self.emit("status", "Playback preview cancelled")
                    return False
                if rc != 0 or not out.is_file() or out.stat().st_size <= 0:
                    raise RuntimeError((text or "")[-2500:] or f"FFmpeg exited with code {rc}")
            self.set_stage("Preview", 100, f"Playback preview ready at {fmt_time(start)}")
            self.emit("live_clip", out, start, duration, generation, open_when_ready)
            return True
        except Exception as e:
            if out:
                try:
                    out.unlink(missing_ok=True)
                except Exception:
                    pass
            self.emit("error", f"Playback preview failed: {e}")
            return False
    def live_frame_worker(self):
        out = None
        try:
            self.validate_common()
            timestamp = float(getattr(self._job, "live_timestamp", 0.0))
            generation = int(getattr(self._job, "live_generation", 0))
            self.set_stage("Preview", 10, f"Preparing frame at {fmt_time(timestamp)}")
            PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            out = PREVIEW_DIR / f"SubBurn-live-{int(time.time() * 1000)}-{generation}.png"
            with tempfile.TemporaryDirectory(prefix="SubBurn_live_") as t:
                td = Path(t)
                sub = self.prepare_subtitles(td, timestamp, 1.0)
                fonts_dir, primary, fonts = self.copy_fonts(td)
                missing, report = self.validate_glyphs(sub, fonts)
                for line in report:
                    self.log(line)
                self.emit_missing_glyph_warning(missing)
                raster = None
                filt = self.build_filter(td, sub, fonts_dir, primary, preview_offset=timestamp, raster_subtitles=raster)
                cmd = [self.toolset.ffmpeg, "-hide_banner", "-y", "-ss", f"{timestamp:.6f}", *self.bitmap_primary_input_options(), "-i", self._job.video]
                cmd += filt["extra"]
                if filt["mode"] == "complex":
                    cmd += ["-filter_complex", filt["filter"], "-map", filt["map"]]
                else:
                    cmd += ["-map", "0:v:0", "-vf", filt["filter"]]
                cmd += ["-an", "-sn", "-dn", "-frames:v", "1", "-c:v", "png", "-f", "image2", "-update", "1", str(out)]
                self.set_stage("Preview", 45, f"Rendering frame at {fmt_time(timestamp)}")
                proc = subprocess.Popen([str(x) for x in cmd], cwd=str(td), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW)
                self.register_render_process(proc, "live_frame")
                try:
                    try:
                        text, _ = proc.communicate(timeout=30)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        text, _ = proc.communicate()
                        raise RuntimeError("Live preview frame timed out after 30 seconds: " + (text or "")[-1800:])
                    cancelled = self.process_was_cancelled(proc)
                    rc = proc.returncode
                finally:
                    self.unregister_render_process(proc)
                if cancelled:
                    out.unlink(missing_ok=True)
                    self.emit("status", "Live preview cancelled")
                    return False
                if rc != 0 or not out.is_file() or out.stat().st_size <= 0:
                    raise RuntimeError((text or "")[-2500:] or f"FFmpeg exited with code {rc}")
            self.set_stage("Preview", 100, f"Frame ready at {fmt_time(timestamp)}")
            self.emit("live_frame", out, timestamp, generation)
            return True
        except Exception as e:
            if out:
                try:
                    out.unlink(missing_ok=True)
                except Exception:
                    pass
            self.emit("error", f"Live preview failed: {e}")
            return False
    def bitmap_first_timestamp_for_job(self, job):
        """Return the first packet timestamp for a selected bitmap subtitle stream, if cheaply available."""
        mode = str(getattr(job, "subtitle_source", "Auto") or "Auto")
        subtitle_path = Path(str(getattr(job, "subtitle_file", "") or ""))
        external_bitmap = subtitle_path.is_file() and (
            subtitle_path.suffix.casefold() in BITMAP_SUB_EXTS
            or (subtitle_path.suffix.casefold() == ".sub" and subtitle_path.with_suffix(".idx").is_file())
        )
        if mode == "External" or (mode == "Auto" and external_bitmap):
            if not external_bitmap:
                return None
            path = subtitle_path.with_suffix(".idx") if subtitle_path.suffix.casefold() == ".sub" and subtitle_path.with_suffix(".idx").is_file() else subtitle_path
            selector = "s:0"
        else:
            m = re.match(r"stream\s+(\d+)", str(getattr(job, "embedded_track", "") or ""))
            if not m or not self.media:
                return None
            global_index = int(m.group(1))
            subtitle_rows = list(getattr(self.media, "subtitle_streams", []) or [])
            ordinal = None
            codec = ""
            for i, row in enumerate(subtitle_rows):
                try:
                    if int(row.get("index")) == global_index:
                        ordinal = i
                        codec = str(row.get("codec") or "").casefold()
                        break
                except Exception:
                    continue
            if ordinal is None or codec not in BITMAP_SUBTITLE_CODECS:
                return None
            path = Path(str(getattr(job, "video", "") or ""))
            if not path.is_file():
                return None
            selector = f"s:{ordinal}"
        toolset = getattr(self, "toolset", None)
        ffprobe = Path(toolset.ffprobe) if toolset is not None else None
        if ffprobe is None or not ffprobe.is_file():
            raw_ffmpeg = Path(str(getattr(job, "ffmpeg", "") or ""))
            candidate = raw_ffmpeg.with_name("ffprobe.exe" if raw_ffmpeg.suffix.casefold() == ".exe" else "ffprobe") if raw_ffmpeg.name else Path()
            if candidate.is_file():
                ffprobe = candidate
            else:
                found = shutil.which("ffprobe")
                ffprobe = Path(found) if found else None
        if ffprobe is None:
            return None
        try:
            st = path.stat()
            cache = getattr(self, "_bitmap_first_timestamp_cache", None)
            if cache is None:
                cache = {}
                self._bitmap_first_timestamp_cache = cache
            key = (str(path.resolve()), int(st.st_size), int(st.st_mtime_ns), selector, str(ffprobe))
            if key in cache:
                return cache[key]
            cmd = [
                ffprobe, "-v", "error", "-select_streams", selector,
                "-read_intervals", "%+#1", "-show_packets",
                "-show_entries", "packet=pts_time,dts_time", "-of", "json", path,
            ]
            rc, out = run_capture(cmd, timeout=15)
            value = None
            if rc == 0:
                packets = (json.loads(out).get("packets") or [])
                for packet in packets:
                    raw = packet.get("pts_time", packet.get("dts_time"))
                    try:
                        ts = float(raw)
                    except Exception:
                        continue
                    if math.isfinite(ts):
                        value = max(0.0, ts)
                        break
            cache[key] = value
            if value is not None:
                self.log(f"Bitmap subtitle first cue packet: {fmt_time(value)}")
            return value
        except Exception as exc:
            self.log(f"Bitmap subtitle smart preview timestamp unavailable: {exc}")
            return None

    def preview_range_for_job(self, job):
        rows = getattr(job, "watermark_rows", [])
        if job.watermark_enabled and job.watermark_timing == "Intervals" and rows:
            idx = job.selected_interval_idx if job.selected_interval_idx is not None else 0
            idx = min(max(0, int(idx)), len(rows) - 1)
            start = max(0, rows[idx][0] - 3)
            return start, 6
        subtitle_path = Path(getattr(job, "subtitle_file", "") or "")
        is_external_bitmap = subtitle_path.is_file() and (
            subtitle_path.suffix.casefold() in BITMAP_SUB_EXTS
            or (subtitle_path.suffix.casefold() == ".sub" and subtitle_path.with_suffix(".idx").is_file())
        )
        embedded_bitmap = False
        if str(getattr(job, "subtitle_source", "Auto")) != "External" and self.media:
            m = re.match(r"stream\s+(\d+)", str(getattr(job, "embedded_track", "") or ""))
            if m:
                idx = int(m.group(1))
                embedded_bitmap = any(
                    int(row.get("index", -1)) == idx and str(row.get("codec") or "").casefold() in BITMAP_SUBTITLE_CODECS
                    for row in list(getattr(self.media, "subtitle_streams", []) or [])
                )
        if is_external_bitmap or embedded_bitmap:
            first_bitmap = self.bitmap_first_timestamp_for_job(job)
            if first_bitmap is not None:
                return max(0.0, first_bitmap - 1.0), 6
        if subtitle_path.is_file() and str(getattr(job, "subtitle_source", "Auto")) != "Embedded" and not is_external_bitmap:
            try:
                cues = read_srt_cues(subtitle_path)
                if cues:
                    offset = float(getattr(job, "subtitle_offset", 0) or 0) / 1000.0
                    first = max(0.0, float(cues[0][0]) + offset)
                    return max(0.0, first - 1.0), 6
            except Exception:
                pass
        return 0, 6
    def sync_live_seek_to_boundary(self, job):
        if not (job.watermark_enabled and job.watermark_timing == "Intervals" and getattr(job, "watermark_rows", [])):
            return
        start, _ = self.preview_range_for_job(job)
        self.live_seek_var.set(start)
        self.update_live_seek_label(start)
    def preview_range(self):
        return self.preview_range_for_job(self._job)
    def preview_async(self):
        if not self.require_batch_idle("Preview"):
            return None
        job = self.snapshot_job()
        self.sync_live_seek_to_boundary(job)
        return self.start_preview_request(self.preview_worker, job)
    def preview_interval_async(self, index):
        if not self.require_batch_idle("Interval preview"):
            return None
        job = self.snapshot_job()
        job.selected_interval_idx = int(index)
        self.sync_live_seek_to_boundary(job)
        return self.start_preview_request(self.preview_worker, job)
    def preview_worker(self):
        try:
            self.validate_common()
            self.set_stage("Preview", 5, "Preparing preview window")
            start, dur = self.preview_range()
            PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            out = unique_path(PREVIEW_DIR / f"SubBurn-preview-{int(time.time())}.mp4")
            with tempfile.TemporaryDirectory(prefix="SubBurn_preview_") as t:
                td = Path(t)
                prep0 = time.monotonic()
                self.set_stage("Subtitles", 40, "Preparing preview subtitles")
                sub = self.prepare_subtitles(td, start, dur)
                prep1 = time.monotonic()
                self.set_stage("Fonts", 60, "Preparing runtime fonts")
                fonts_dir, primary, fonts = self.copy_fonts(td)
                prep2 = time.monotonic()
                self.set_stage("Glyphs", 70, "Checking preview glyph coverage")
                missing, report = self.validate_glyphs(sub, fonts)
                for line in report:
                    self.log(line)
                self.emit_missing_glyph_warning(missing)
                prep3 = time.monotonic()
                self.set_stage("Subtitles", 80, "Preparing universal font-run renderer")
                raster = None
                prep35 = time.monotonic()
                self.set_stage("Filters", 50, "Building preview filters")
                filt = self.build_filter(td, sub, fonts_dir, primary, preview_offset=start, raster_subtitles=raster)
                self.verify_preview_filter_parity(filt, start, dur, "Boundary preview")
                prep4 = time.monotonic()
                self.log(f"Preview prep timings: subtitles {prep1-prep0:.2f}s | fonts {prep2-prep1:.2f}s | glyphs {prep3-prep2:.2f}s | font runs {prep35-prep3:.2f}s | filters {prep4-prep35:.2f}s")
                enc = self.choose_encoder(td, filt, for_preview=True)
                tuning = tuning_args(self.toolset.ffmpeg, enc, "Fastest", self.help_cache) or self.tuning_cache.get(enc, [])
                cmd = [self.toolset.ffmpeg, "-hide_banner", "-loglevel", "verbose", "-y", "-ss", str(start), "-t", str(dur), *self.bitmap_primary_input_options(), "-i", self._job.video]
                cmd += filt["extra"]
                if filt["mode"] == "complex":
                    cmd += ["-filter_complex", filt["filter"], "-map", filt["map"]]
                else:
                    cmd += ["-map", "0:v:0", "-vf", filt["filter"]]
                preview_video_args = ["-crf", "23"] if enc == "libx264" else ["-b:v", str(self.target_bitrate())]
                cmd += ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "128k", "-sn", "-dn", "-c:v", enc, *tuning, *preview_video_args, *pixfmt_args(enc), *self.output_attribution_args(), "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", out]
                self.set_stage("Preview", 35, "Rendering preview")
                self.log("Preview encoder: " + enc)
                self.emit("progress", 0, "-", "-", "-")
                lines_tail = []
                proc = subprocess.Popen([str(x) for x in cmd], cwd=str(td), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1, creationflags=CREATE_NO_WINDOW)
                self.register_render_process(proc, "preview")
                stall_timeout = 20.0
                last_activity = time.monotonic()
                current = 0.0
                fps = "-"
                speed = "-"
                finished = False
                cancelled = False
                try:
                    def watchdog():
                        while proc.poll() is None:
                            if time.monotonic() - last_activity > stall_timeout:
                                proc.kill()
                                return
                            time.sleep(0.5)
                    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
                    watchdog_thread.start()
                    assert proc.stdout is not None
                    for raw in proc.stdout:
                        last_activity = time.monotonic()
                        line = raw.rstrip()
                        if "fontselect" in line.casefold():
                            self.log("Boundary preview " + line.strip())
                        lines_tail.append(line)
                        if len(lines_tail) > 60:
                            lines_tail.pop(0)
                        if "=" in line:
                            k, v = line.split("=", 1)
                            if k in {"out_time_us", "out_time_ms"}:
                                try:
                                    current = int(v) / 1000000
                                except Exception:
                                    pass
                            elif k == "fps":
                                fps = v.strip()
                            elif k == "speed":
                                speed = v.strip()
                            elif k == "progress":
                                pct = min(100, max(0, current / dur * 100)) if dur else 0
                                self.set_stage("Preview", 35 + pct * 0.6, f"Rendering preview {pct:.0f}%")
                                self.emit("progress", pct, fps, speed, fmt_time(max(0, dur - current)))
                                if v.strip() == "end":
                                    finished = True
                    rc = proc.wait()
                    cancelled = self.process_was_cancelled(proc)
                finally:
                    self.unregister_render_process(proc)
                if cancelled:
                    self.set_stage("Preview", 0, "Preview cancelled")
                    self.emit("status", "Preview cancelled")
                    return False
                stalled = not finished and time.monotonic() - last_activity <= 1.0 and rc != 0 and rc < 0
                if rc != 0 or not out.exists() or out.stat().st_size == 0:
                    tail = "\n".join(x for x in lines_tail if x.strip())[-2500:]
                    if stalled or (rc < 0 and not finished):
                        raise RuntimeError(f"Preview stalled: no FFmpeg output for {stall_timeout:.0f}s and was killed. Last output:\n{tail}")
                    raise RuntimeError(tail or f"FFmpeg exited with code {rc}")
            self.last_output = out
            self.set_stage("Preview", 100, "Preview ready")
            self.log(f"Preview created: {out}")
            self.emit("status", "Preview ready")
            self.emit("progress", 100, fps, speed, "00:00")
            open_path(out)
            return True
        except Exception as e:
            self.emit("error", f"Preview failed: {e}")
            return False
    def compare_preview_async(self):
        if not self.require_batch_idle("Quality comparison preview"):
            return None
        job = self.snapshot_job()
        return self.start_preview_request(self.compare_preview_worker, job)
    def compare_preview_worker(self):
        original = self._job.quality_mode
        op_id = self.current_operation_id()
        modes = ["Preserve visual quality", "Match source size"]
        try:
            for i, mode in enumerate(modes):
                if op_id:
                    self.op_state.set_overall(op_id, i * 50.0, f"Rendering comparison {i + 1} of {len(modes)}: {mode}")
                self._job.quality_mode = mode
                if not self.preview_worker():
                    return False
                if op_id:
                    self.op_state.set_overall(op_id, (i + 1) * 49.0, f"Comparison {i + 1} ready")
            return True
        finally:
            self._job.quality_mode = original
    def final_output_path_for_job(self, job):
        root=Path(job.output_dir)
        if job.clean_output:root=root/"SubBurned"
        root.mkdir(parents=True,exist_ok=True)
        return unique_path(root/f"{safe_filename(job.output_name)}{job.output_ext}")
    def final_output_path(self):
        return self.final_output_path_for_job(self._job)
    def build_video_quality_args(self, enc):
        mode = self._job.quality_mode
        e = enc.casefold()
        if mode == "Preserve visual quality":
            if enc == "libx264":
                return ["-crf", "18"]
            if enc == "libx265":
                return ["-crf", "21"]
            if enc == "libsvtav1":
                return ["-crf", "24"]
            if "_nvenc" in e:
                return ["-b:v", str(self.target_bitrate()), "-maxrate:v", str(max(self.target_bitrate() * 3, self.target_bitrate() + 200000)), "-bufsize:v", str(max(self.target_bitrate() * 6, 1000000))]
        return ["-b:v", str(self.target_bitrate())]
    def run_encode_command(self, cmd, td, log, progress_base=0.0, progress_span=100.0, progress_label="Encode"):
        current = 0.0
        fps = "-"
        speed = "-"
        errors = []
        proc = subprocess.Popen([str(x) for x in cmd], cwd=str(td), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1, creationflags=CREATE_NO_WINDOW)
        self.register_render_process(proc, "encode")
        cancelled = False
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.rstrip()
                log.add(line)
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k in {"out_time_us", "out_time_ms"}:
                        try:
                            current = int(v) / 1000000
                        except Exception:
                            pass
                    elif k == "fps":
                        fps = v.strip()
                    elif k == "speed":
                        speed = v.strip()
                    elif k == "progress":
                        dur = self.media.duration if self.media else 0
                        local_pct = min(100, max(0, current / dur * 100)) if dur else 0
                        pct = min(100, progress_base + local_pct * progress_span / 100)
                        try:
                            factor = float(speed.rstrip("x"))
                        except Exception:
                            factor = 0
                        eta = (dur - current) / factor if dur and factor > 0 else None
                        self.set_stage("Encode", pct, f"{progress_label} {local_pct:.1f}%")
                        self.emit("progress", pct, fps, speed, fmt_time(eta))
                else:
                    low = line.casefold()
                    if any(x in low for x in ("error", "failed", "invalid", "unable")):
                        errors.append(line)
            rc = proc.wait()
            cancelled = self.process_was_cancelled(proc)
        finally:
            self.unregister_render_process(proc)
        return rc, cancelled, errors, fps, speed
    def start_encode(self):
        if not self.require_batch_idle("Manual encode"):
            return None
        if self.running:
            return None
        self.running = True
        try:
            return self.run_job(self.encode_worker, operation_type="encode")
        except Exception:
            self.running = False
            raise
    def encode_worker(self):
        part = None
        log = JobLog(LOG_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}.log")
        try:
            self.validate_common()
            self.set_stage("Encode", 3, "Starting job")
            self.running = True
            self.paused = False
            self.buttons_running(True)
            self.emit("status", "Preparing")
            final = self.final_output_path()
            part = final.with_name(final.stem + ".part" + final.suffix)
            part.unlink(missing_ok=True)
            with tempfile.TemporaryDirectory(prefix="SubBurn_encode_") as t:
                td = Path(t)
                self.set_stage("Subtitles", 30, "Preparing subtitles")
                sub = self.prepare_subtitles(td)
                self.set_stage("Fonts", 50, "Preparing runtime fonts")
                fonts_dir, primary, fonts = self.copy_fonts(td)
                self.set_stage("Glyphs", 40, "Checking glyph coverage")
                missing, report = self.validate_glyphs(sub, fonts)
                for line in report:
                    self.log(line)
                    log.add(line)
                self.emit_missing_glyph_warning(missing)
                self.set_stage("Glyphs", 100, "Glyph check complete")
                self.set_stage("Subtitles", 75, "Preparing universal font-run renderer")
                raster = None
                self.set_stage("Filters", 40, "Building render filters")
                filt = self.build_filter(td, sub, fonts_dir, primary, raster_subtitles=raster)
                self.set_stage("Filters", 100, "Filters ready")
                enc = self.choose_encoder(td, filt, for_preview=False)
                tuning = self.tuning_cache.get(enc, tuning_args(self.toolset.ffmpeg, enc, self._job.speed_mode, self.help_cache))
                cmd_prefix = [self.toolset.ffmpeg, "-hide_banner", "-y", *self.bitmap_primary_input_options(), "-i", self._job.video]
                cmd_prefix += filt["extra"]
                if filt["mode"] == "complex":
                    cmd_prefix += ["-filter_complex", filt["filter"], "-map", filt["map"]]
                else:
                    cmd_prefix += ["-map", "0:v:0", "-vf", filt["filter"]]
                quality_args = self.build_video_quality_args(enc)
                two_pass = self._job.quality_mode == "Target file size" and enc == "libx264"
                passlog = td / "subburn-2pass"
                if two_pass:
                    first_cmd = list(cmd_prefix)
                    first_cmd += ["-an", "-sn", "-dn", "-c:v", enc, *tuning, *quality_args, *pixfmt_args(enc), "-pass", "1", "-passlogfile", passlog, "-progress", "pipe:1", "-nostats", "-f", "null", os.devnull]
                    first_safe = [str(x) for x in first_cmd]
                    self.set_stage("Encode", 10, "Target size pass 1 of 2")
                    self.log("Encoder: " + enc + " (target-size two-pass)")
                    self.log("Pass 1 command: " + subprocess.list2cmdline(first_safe))
                    log.add("Encoder: " + enc + " (target-size two-pass)")
                    log.add("Pass 1 command: " + subprocess.list2cmdline(first_safe))
                    rc1, cancelled1, errors1, fps, speed = self.run_encode_command(first_cmd, td, log, 0, 45, "Pass 1/2")
                    if cancelled1:
                        part.unlink(missing_ok=True)
                        self.emit("status", "Cancelled")
                        return {"status": "cancelled", "output": "", "error": ""}
                    if rc1 != 0:
                        raise RuntimeError(f"FFmpeg target-size pass 1 exited with code {rc1}: " + " | ".join(errors1[-8:]))
                cmd = list(cmd_prefix)
                cmd += self.audio_args()
                cmd += ["-sn", "-dn", "-c:v", enc, *tuning, *quality_args, *pixfmt_args(enc)]
                if two_pass:
                    cmd += ["-pass", "2", "-passlogfile", passlog]
                if self._job.chapter:
                    cmd += ["-map_chapters", "0"]
                else:
                    cmd += ["-map_chapters", "-1"]
                cmd += ["-map_metadata", "0"]
                for key in USER_METADATA_KEYS:
                    value = str(getattr(self._job, "metadata", {}).get(key, "")).strip()
                    if value:
                        cmd += ["-metadata", f"{key}={value}"]
                cmd += self.output_attribution_args()
                if final.suffix.casefold() in {".mp4", ".mov"}:
                    cmd += ["-movflags", "+faststart"]
                cmd += ["-progress", "pipe:1", "-nostats", part]
                safe_cmd = [str(x) for x in cmd]
                self.set_stage("Encode", 45 if two_pass else 10, "Target size pass 2 of 2" if two_pass else "Launching FFmpeg")
                if not two_pass:
                    self.log("Encoder: " + enc)
                    log.add("Encoder: " + enc)
                self.log(("Pass 2 command: " if two_pass else "Command: ") + subprocess.list2cmdline(safe_cmd))
                log.add(("Pass 2 command: " if two_pass else "Command: ") + subprocess.list2cmdline(safe_cmd))
                rc, cancelled, errors, fps, speed = self.run_encode_command(cmd, td, log, 45 if two_pass else 0, 55 if two_pass else 100, "Pass 2/2" if two_pass else "Encode")
            log.save()
            if cancelled:
                part.unlink(missing_ok=True)
                self.emit("status", "Cancelled")
                return {"status": "cancelled", "output": "", "error": ""}
            if rc != 0 or not part.exists():
                part.unlink(missing_ok=True)
                raise RuntimeError(f"FFmpeg exited with code {rc}: " + " | ".join(errors[-8:]))
            if self._job.quality_mode == "Target file size":
                target_bytes = float(self._job.target_size) * 1024 * 1024
                actual_bytes = part.stat().st_size
                delta_pct = (actual_bytes - target_bytes) / target_bytes * 100 if target_bytes else 0
                result_line = f"Target size result: requested {human_bytes(target_bytes)}, actual {human_bytes(actual_bytes)} ({delta_pct:+.1f}%)"
                self.log(result_line)
                log.add(result_line)
                if abs(delta_pct) > 12:
                    self.log("Target size warning: this encoder/content combination could not closely match the requested size")
            self.set_stage("Verify", 35, "Verifying output")
            self.verify_output(part)
            self.set_stage("Verify", 100, "Output verified")
            os.replace(part, final)
            self.last_output = final
            self.log(f"Complete: {final}")
            self.emit("progress", 100, fps, speed, "00:00")
            self.emit("done", final)
            return {"status": "done", "output": str(final), "error": ""}
        except Exception as e:
            if part:
                part.unlink(missing_ok=True)
            try:
                log.save()
            except Exception:
                pass
            with self.process_lock:
                self.current_process = None
            self.emit("error", f"Encode failed: {e}")
            return {"status": "failed", "output": "", "error": str(e)}
        finally:
            self.running = False
            self.paused = False
            self.buttons_running(False)
    def verify_output(self, path, toolset=None):
        verify_tool=toolset or self.toolset
        if verify_tool is None:raise RuntimeError("Output verification runtime is unavailable")
        rc, out = run_capture([verify_tool.ffprobe, "-v", "error", "-show_entries", "stream=codec_type:format_tags", "-of", "json", path], timeout=45)
        if rc != 0:
            raise RuntimeError("Output verification failed")
        data = json.loads(out)
        types = [x.get("codec_type") for x in data.get("streams") or []]
        if "video" not in types:
            raise RuntimeError("Output has no video")
        if "subtitle" in types:
            raise RuntimeError("Output contains embedded subtitle stream")
        tags = (data.get("format") or {}).get("tags") or {}
        marker_value = next((v for k, v in tags.items() if str(k).casefold() == OUTPUT_MARKER_KEY), None)
        if marker_value != OUTPUT_MARKER_VALUE:
            raise RuntimeError("Output verification failed: SubBurn output marker is missing or incorrect")
        if self._job.clean_output:
            nearby = [p.name for p in Path(path).parent.iterdir() if p.is_file() and p.suffix.casefold() in SUBTITLE_FILE_EXTS]
            if nearby:
                raise RuntimeError("Clean output folder contains subtitle files")
    def register_render_process(self, proc, role):
        with self.process_lock:
            self.active_processes[proc] = role
            self.cancelled_processes.discard(proc)
            if role == "encode":
                self.current_process = proc
        self.refresh_process_buttons()
    def process_was_cancelled(self, proc):
        with self.process_lock:
            return proc in self.cancelled_processes
    def unregister_render_process(self, proc):
        with self.process_lock:
            self.active_processes.pop(proc, None)
            self.cancelled_processes.discard(proc)
            if self.current_process is proc:
                self.current_process = None
        self.refresh_process_buttons()
    def refresh_process_buttons(self):
        if not all(hasattr(self, name) for name in ("root", "start_btn", "pause_btn", "resume_btn", "cancel_btn")):
            return
        with self.process_lock:
            active = any(p.poll() is None for p in self.active_processes)
            encode = self.current_process
            encode_active = bool(encode and encode.poll() is None)
        def apply():
            try:
                self.start_btn.configure(state="disabled" if self.running else "normal")
                self.pause_btn.configure(state="normal" if encode_active and not self.paused else "disabled")
                self.resume_btn.configure(state="normal" if encode_active and self.paused else "disabled")
                self.cancel_btn.configure(state="normal" if active else "disabled")
            except Exception:
                pass
        try:
            self.root.after(0, apply)
        except Exception:
            pass
    def buttons_running(self, running):
        self.refresh_process_buttons()
    def pause_encode(self):
        with self.process_lock:
            p = self.current_process
        if p and p.poll() is None:
            suspend_pid(p.pid)
            self.paused = True
            self.buttons_running(True)
            self.status_var.set("Paused")
    def resume_encode(self):
        with self.process_lock:
            p = self.current_process
        if p and p.poll() is None:
            resume_pid(p.pid)
            self.paused = False
            self.buttons_running(True)
            self.status_var.set("Encoding")
    def cancel_encode(self):
        with self.process_lock:
            active = [p for p in self.active_processes if p.poll() is None]
            encode = self.current_process
            if encode and encode.poll() is None and encode not in active:
                active.append(encode)
            for p in active:
                self.cancelled_processes.add(p)
        if encode in active and self.paused:
            try:
                resume_pid(encode.pid)
            except Exception:
                pass
        cancelled = 0
        for p in active:
            try:
                if p.poll() is None:
                    p.terminate()
                    cancelled += 1
            except Exception:
                pass
        if cancelled:
            self.status_var.set("Cancelling")
    def done_ui(self, final):
        self.status_var.set("Complete")
        self.op_state.set_status("Complete")
        self.open_file_btn.configure(state="normal")
        self.open_folder_btn.configure(state="normal")
        top = tk.Toplevel(self.root)
        top.title("Output complete")
        frm = ttk.Frame(top, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Output complete", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(frm, text=str(final), wraplength=700).pack(anchor="w", pady=(8, 12))
        buttons = ttk.Frame(frm)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Open file", command=lambda: open_path(final)).pack(side="left")
        ttk.Button(buttons, text="Open folder", command=lambda: open_path(Path(final).parent)).pack(side="left", padx=(12, 0))
        ttk.Button(buttons, text="OK", command=top.destroy).pack(side="right")
    def add_interval(self):
        self.interval_dialog(None)
    def edit_interval(self):
        sel = self.interval_tree.selection()
        if sel:
            self.interval_dialog(int(self.interval_tree.item(sel[0], "tags")[0]))
    def interval_dialog(self, idx):
        top = tk.Toplevel(self.root)
        top.title("Watermark interval")
        frm = ttk.Frame(top, padding=14)
        frm.pack(fill="both", expand=True)
        start = tk.StringVar()
        end = tk.StringVar()
        pos = tk.StringVar(value="Top right")
        if idx is not None:
            a, b, p = self.watermark_rows[idx]
            start.set(fmt_time(a))
            end.set(fmt_time(b))
            pos.set(p)
        ttk.Label(frm, text="Start").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=start).grid(row=0, column=1, pady=4)
        ttk.Label(frm, text="End").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=end).grid(row=1, column=1, pady=4)
        ttk.Label(frm, text="Position").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(frm, textvariable=pos, values=POSITIONS, state="readonly").grid(row=2, column=1, pady=4)
        def save():
            try:
                a = parse_time_value(start.get())
                b = parse_time_value(end.get())
                if b <= a:
                    raise ValueError("End must be after start")
                row = (a, b, pos.get())
                if idx is None:
                    self.watermark_rows.append(row)
                else:
                    self.watermark_rows[idx] = row
                self.watermark_rows.sort(key=lambda x: x[0])
                self.refresh_intervals()
                self.autosave_project()
                top.destroy()
            except Exception as e:
                messagebox.showerror("SubBurn", str(e), parent=top)
        ttk.Button(frm, text="Save", command=save).grid(row=3, column=1, sticky="e", pady=(8, 0))
    def delete_interval(self):
        sel = self.interval_tree.selection()
        if not sel:
            return
        idx = int(self.interval_tree.item(sel[0], "tags")[0])
        del self.watermark_rows[idx]
        self.refresh_intervals()
        self.autosave_project()
    def refresh_intervals(self):
        for item in self.interval_tree.get_children():
            self.interval_tree.delete(item)
        for i, (a, b, pos) in enumerate(self.watermark_rows):
            self.interval_tree.insert("", "end", values=(fmt_time(a), fmt_time(b), pos), tags=(str(i),))
    def update_estimate(self, *args):
        if not self.media:
            return
        try:
            snap = self.snapshot_job()
            video = self.target_bitrate(snap)
            audio = self.output_audio_bitrate(snap)
            overhead = 0
            if snap.quality_mode == "Target file size":
                total_bps = float(snap.target_size) * 1024 * 1024 * 8 / max(1, self.media.duration)
                overhead = self.target_container_overhead(total_bps)
            size = (video + audio + overhead) * self.media.duration / 8
            self.estimate_var.set("Estimated size: " + human_bytes(size))
        except Exception:
            pass
    def export_diagnostics(self):
        try:
            DIAG_DIR.mkdir(parents=True, exist_ok=True)
            report = DIAG_DIR / f"SubBurn-diagnostics-{time.strftime('%Y%m%d-%H%M%S')}.txt"
            lines = []
            lines.append("SubBurn")
            lines.append(f"Python {sys.version.split()[0]}")
            lines.append(f"OS {sys.platform}")
            ffmpeg_raw = str(self.ffmpeg_var.get() or "").strip()
            lines.append("FFmpeg " + (Path(ffmpeg_raw).name if ffmpeg_raw else "not selected"))
            if self.toolset:
                lines.append(redact_sensitive_text(self.toolset.version))
                lines.append("Filters " + ",".join(sorted(self.toolset.filters)))
                lines.append("Encoders " + ",".join(self.toolset.encoders))
                managed_root = RUNTIME_DIR / "ffmpeg"
                if _path_within(self.toolset.ffmpeg, managed_root):
                    ff_manifest = read_managed_ffmpeg_manifest(managed_root)
                    if ff_manifest:
                        lines.append("Managed FFmpeg provider " + str(ff_manifest.get("provider") or "unknown"))
                        lines.append("Managed FFmpeg archive SHA-256 " + str(ff_manifest.get("archive_sha256") or "unknown"))
            try:
                model_source = transcription_model_source(self.transcription_model_var.get())
                lines.append("Transcription model source " + model_source["repo"] + "@" + model_source["revision"])
                lines.append("Transcription model license " + model_source["license"])
                lines.append("Transcription model ready " + ("yes" if transcription_model_ready(self.transcription_model_var.get()) else "no"))
            except Exception:
                pass
            video_raw = str(self.video_var.get() or "").strip()
            lines.append("Video " + (Path(video_raw).name if video_raw else "not selected"))
            lines.append("Subtitle source " + self.subtitle_source_var.get())
            lines.append("Log (sanitized)")
            lines.append(redact_sensitive_text(self.log_text.get("1.0", "end")))
            report.write_text("\n".join(lines), encoding="utf-8")
            open_path(report.parent)
            self.log(f"Diagnostics exported: {report}")
        except Exception as e:
            self.error_ui(f"Diagnostics export failed: {e}")
    def open_last_output(self):
        if self.last_output and Path(self.last_output).exists():
            open_path(self.last_output)
    def open_last_folder(self):
        if self.last_output and Path(self.last_output).exists():
            open_path(Path(self.last_output).parent)
    def close(self):
        # Closing the window must not kill an in-progress job or the dashboard server.
        # It only tears down the Tkinter GUI; main() decides when the process actually exits.
        try:
            self.save_settings()
            self.autosave_project()
        except Exception:
            pass
        if self.running or self.active_job_count() > 0:
            self.close_when_idle = True
            self.log_ui("Window hidden while work is running - it will keep running in the background."
                        + (f" Dashboard: http://127.0.0.1:{self.dashboard_port}" if self.dashboard_port else ""))
            self.root.withdraw()
            return
        self.root.destroy()



def main():
    root = create_root()
    app = SubBurnApp(root)
    for var in (app.quality_mode_var, app.custom_bitrate_var, app.target_size_var, app.audio_mode_var, app.output_ext_var):
        var.trace_add("write", app.update_estimate)
    root.mainloop()
    # The Tk window is gone. If a job was still running when it was closed, don't kill the
    # process out from under it - wait for it to actually finish (dashboard stays reachable
    # in the meantime since its server thread is untouched), then shut down cleanly.
    if app.running or app.active_job_count() > 0:
        print(f"SubBurn window closed - job still running in background."
              + (f" Dashboard: http://127.0.0.1:{app.dashboard_port}" if app.dashboard_port else ""))
        while app.running or app.active_job_count() > 0:
            time.sleep(0.5)
        print("Background job finished. Exiting.")
    if app.dashboard_server:
        try:
            app.dashboard_server.shutdown()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        p = LOG_DIR / f"crash-{time.strftime('%Y%m%d-%H%M%S')}.log"
        p.write_text(redact_sensitive_text(traceback.format_exc()), encoding="utf-8")
        raise
