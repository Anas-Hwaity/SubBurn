from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
from types import SimpleNamespace

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "subburn" / "app.py"
spec = importlib.util.spec_from_file_location("subburn_burn_performance_contract", SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def app_shell(job):
    app = object.__new__(mod.SubBurnApp)
    app._job_local = mod.threading.local()
    app._job = job
    app.subtitle_kind = lambda: "text"
    app.prepare_universal_ass = lambda td, subtitle_file, fonts_dir, primary, preview_offset=0.0: pathlib.Path("subtitles.ass")
    app.log = lambda *args, **kwargs: None
    return app


with tempfile.TemporaryDirectory(prefix="subburn-perf-contract-") as td_raw:
    td = pathlib.Path(td_raw)
    srt = td / "input.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    fonts = td / "fonts"
    fonts.mkdir()

    plain = SimpleNamespace(
        watermark_enabled=False, watermark_type="Text", resolution="Original", fps="Original",
    )
    app = app_shell(plain)
    filt = mod.SubBurnApp.build_filter(app, td, srt, fonts, "Primary", preview_offset=0.0)
    assert filt["mode"] == "vf", filt
    assert filt["filter"].startswith("ass=subtitles.ass:fontsdir=fonts"), filt
    assert "," not in filt["filter"], filt
    assert "setpts" not in filt["filter"], filt
    assert "scale=" not in filt["filter"] and "fps=" not in filt["filter"], filt

    scaled = SimpleNamespace(
        watermark_enabled=False, watermark_type="Text", resolution="720p", fps="Original",
    )
    app2 = app_shell(scaled)
    filt2 = mod.SubBurnApp.build_filter(app2, td, srt, fonts, "Primary", preview_offset=0.0)
    assert "ass=subtitles.ass:fontsdir=fonts" in filt2["filter"], filt2
    assert "scale=-2:720:flags=lanczos" in filt2["filter"], filt2

# Automatic selection must keep compatible hardware candidates ahead of software unless the user
# explicitly asks for the CPU-quality policy. Explicit encoder selections bypass auto substitution.
job = SimpleNamespace(output_ext=".mp4", codec="H.264", encoder="Auto", encoder_policy="Balanced")
app = object.__new__(mod.SubBurnApp)
app._job_local = mod.threading.local(); app._job = job
app.media = SimpleNamespace(video_codec="h264")
app.toolset = SimpleNamespace(encoders=["h264_nvenc", "h264_qsv", "libx264"], ffmpeg="ffmpeg")
app.tuning_cache = {}; app.help_cache = {}; app.benchmark_scores = {}; app.encoder_cache = {}
hw = mod.SubBurnApp.hardware_first_candidates(app)
sw = mod.SubBurnApp.software_candidates(app)
assert hw and hw[0] in {"h264_nvenc", "h264_qsv"}, (hw, sw)
assert "libx264" in sw, (hw, sw)

# Speed presets are a direct user choice and map deterministically for software encoders.
cache = {}
old_help = mod.encoder_help
mod.encoder_help = lambda ffmpeg, enc, cache: ""
try:
    expected = {
        "Fastest": "ultrafast",
        "Fast": "veryfast",
        "Balanced": "medium",
        "Quality": "slow",
        "Maximum": "veryslow",
    }
    for speed, preset in expected.items():
        assert mod.tuning_args("ffmpeg", "libx264", speed, cache) == ["-preset", preset]
finally:
    mod.encoder_help = old_help

print("BURN PERFORMANCE / SETTINGS-PRESERVATION CONTRACT PASS")
