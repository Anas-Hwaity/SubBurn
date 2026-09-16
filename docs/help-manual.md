# SubBurn Help Manual

**Made by:** Anas Al Hwaity  
**Contact Owner:** [@ANAS12RM on Telegram](https://t.me/ANAS12RM)

This is the repository copy of the Help Manual available directly inside SubBurn Settings.

## Quick start

1. Open a video on Home.
2. Choose external/embedded subtitles or transcribe locally.
3. Configure subtitle style and optional watermarking.
4. Render an exact frame or short clip on Preview.
5. Choose Simple or Advanced encoding settings.
6. Burn the video and verify the output.

## Home

Choose the video, subtitle source, output folder, output filename, and container. Optional metadata fields include title, artist, album, genre, date, description, and copyright.

SubBurn adds the standard video metadata comment `Created by SubBurn.` to video outputs produced by its video-rendering paths.

Recent projects preserve the project state needed to restore prior work. Recent folders provide quick output-folder reuse. Clearing those lists removes only SubBurn history entries, not the underlying media files.

## Subtitles

Choose the primary subtitle font and zero or more fallback fonts. Fallback fonts are used only when required glyphs are unavailable in the primary font.

Subtitle controls include:

- size;
- bold, italic, underline, strikeout;
- text/outline colors and opacity;
- outline width;
- shadow depth, color, and opacity;
- letter spacing and rotation;
- alignment and margins;
- background box;
- wrapping and line limits;
- timing offset;
- safe areas;
- caption effects.

Arabic and Hebrew rendering uses libass with HarfBuzz/FriBidi and deterministic font fallback planning.

## Watermark

SubBurn supports text and image watermarks.

Text watermark controls include independent font selection, optional reuse of the subtitle font, size, outline, opacity, position, and timing.

Image watermark controls include source image, scale/width, opacity, coordinates, grid position, and timing.

Watermark timing may cover the full duration or explicit intervals.

## Transcribe

Local transcription uses the selected Faster-Whisper/CTranslate2 model. Choose the model, language mode, canonical language codes, and device. Model assets are downloaded only when required and are cached for reuse.

## Preview

**Render frame** creates an exact still at the selected timestamp.

**Play 8 seconds inline/clip** creates a short rendered preview using the same subtitle/watermark filter planning as final output.

The rendered frame can also be used to place enabled watermarks interactively.

## Burn and encoding

Simple mode exposes common choices. Advanced mode adds:

- container;
- codec;
- quality mode;
- encoder policy;
- speed preset;
- resolution;
- frame rate;
- audio handling;
- explicit encoder;
- custom bitrate;
- target size;
- chapter preservation.

When Auto selection is used, SubBurn tests compatible encoders and can cache the fastest measured usable encoder. If you explicitly choose an encoder or quality setting, that choice remains authoritative.

## Queue

The queue persists in SQLite across restarts.

You can:

- add the currently open project;
- add another video without changing the current project;
- add a recent saved project;
- add matching video/subtitle pairs from a folder;
- duplicate intentionally;
- reorder;
- remove one or multiple jobs;
- cancel and remove a running job;
- retry failed jobs;
- clear queued jobs;
- clear completed jobs;
- pause after the current job;
- resume later.

Exact accidental duplicate additions are blocked; use Duplicate when you intentionally need another identical queue entry.

## Settings

### Appearance

Choose Dark, Balanced, or Light. Desktop and browser use the same persisted appearance state.

### Runtime and FFmpeg

Discovery order:

1. system/PATH FFmpeg;
2. user-selected FFmpeg executable/folder;
3. managed verified SubBurn runtime.

SubBurn validates FFmpeg/FFprobe compatibility and required filters before using a candidate.

### Recovery and diagnostics

Export diagnostics when reporting difficult failures. Recovery can restore the last autosaved project after interruption.

## Progress and reporting

SubBurn uses one canonical progress engine for Tkinter and the browser dashboard.

Rules:

- percentage is determinate only when a real denominator exists;
- unknown preparation work stays indeterminate;
- download percentage, transferred bytes, speed, and ETA are separate values;
- encode percentage, FPS, encode speed, ETA, and elapsed time are separate values;
- operation metrics freeze when the operation reaches a terminal state;
- background/stale operations cannot overwrite a newer foreground operation;
- failure and cancellation cannot masquerade as success;
- 100% is reserved for verified completion.
