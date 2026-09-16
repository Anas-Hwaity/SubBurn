# Burn performance policy

SubBurn optimizes the render architecture, not the user's quality choices.

For a normal text-subtitle-only final burn where watermarking is disabled and both resolution and frame rate are left at **Original**, SubBurn emits one direct `ass=...`/libass video filter. It does not insert timestamp reset, scale, FPS conversion, watermark, or other video filters that the job did not request. This preserves the lean render path used by the earlier `SubBurn_4x_Subtitles_Only_RTL_FIX_v2.py` tool.

Encoder behavior remains controlled by the selected settings:

- an explicitly selected encoder is never silently replaced for speed;
- **Auto** keeps compatible hardware encoders ahead of software fallbacks unless the user selects the CPU-quality policy;
- the selected speed preset is passed through the encoder-specific tuning map;
- CRF/quality mode, target bitrate/size, output codec/container, resolution, frame rate, pixel format, subtitle styling, watermarking, chapters, metadata, and audio mode are not weakened or removed by the fast path;
- if a requested feature needs additional filtering, the fast path disengages rather than dropping that feature.

Performance claims must compare the same input with the same encoder, codec, quality, speed preset, pixel format, audio behavior, and requested filters. Native Windows/GPU benchmarks remain part of pre-release acceptance because Linux software-encoder measurements do not predict all target hardware.
