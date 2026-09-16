
## WIP24 final polish

- Fixed browser rendered-frame display by allowing the dashboard's same-session blob image URL under the Content Security Policy and adding decode/error handling.
- Reworked Queue so users can add another video without changing the open project, add a recent project, remove one or multiple items, explicitly duplicate jobs, clear queued jobs, and clear completed jobs.
- Added exact accidental-duplicate protection for queue additions.
- Added owner/contact presentation and an in-app Help Manual in Settings.
- Added repository Help Manual and support documentation.

## WIP21

- Corrected managed-FFmpeg transfer presentation so the visible download begins at true 0%, reports downloaded/total bytes, transfer speed and ETA immediately, and never leaks the internal 5% discovery weight into the transfer bar.
- Exact transfer progress may reach 100%, while the canonical operation bar remains capped at 99% until checksum/extraction/install succeeds; installation cannot make the visible bar move backward.
- Added a real localhost archive/checksum transfer acceptance test in addition to mocked runtime tests.
- Added a subtitle-only performance path that emits one direct libass filter when no watermark/resolution/FPS transform is requested, preserving every selected codec/encoder/quality/audio setting.
- Added burn-performance contracts for hardware-first Auto selection and exact user speed-preset preservation, plus controlled same-settings benchmark evidence.

# Changelog

SubBurn uses a curated changelog. Development checkpoint numbers are engineering history, not public semantic versions.

## Unreleased

### Changed

- Rebuilt the application around one canonical operation/progress model shared by Tkinter and the browser dashboard.
- Simplified desktop/browser workflows around Home, Subtitles, Watermark, Transcribe, Preview, Burn, Queue and Settings.
- Hardened loopback dashboard authentication, origin/host validation, request limits, filesystem confinement and diagnostics redaction.
- Added a portable Chromium launcher plus a GitHub-hosted live-loopback browser E2E job so the current container-specific localhost block can be closed on a normal hosted runner instead of being silently waived.
- Separated platform-appropriate config/data/cache/state locations and added legacy-state migration.
- Added pinned transcription-model provenance and verified FFmpeg runtime provenance.
- Added reproducible wheel/canonical-sdist tooling and clean-artifact verification.
- Added a modernized Tkinter visual system with explicit navigation, action roles, minimum-size/high-scaling visual QA, and Ctrl+1–8 workflow shortcuts.
- Added fail-closed dependency-lock review rules and a frozen-lock CycloneDX SBOM/attestation release path.
- Reworked FFmpeg discovery and managed-runtime behavior around the explicit priority **PATH/system → user-selected file/folder → verified managed runtime**; all candidates in each stage are inspected before falling through, concurrent installs serialize, verified archives are cached for retry, and failed automatic install attempts cannot loop-download in one session.
- On Windows, a required verified managed FFmpeg/FFprobe pair is promoted to the front of the persistent user PATH and immediately to the current process PATH, avoiding destructive overwrites of package-manager shims or unrelated project binaries.
- Fixed the real managed-download progress adapter arity defect that could abort setup with `OperationState.transfer() ... 9 were given`; regression coverage now exercises the UI-event adapter boundary itself.
- Added concise download explanations and byte/speed/ETA telemetry for FFmpeg and pinned transcription models, with technical rejection details retained in logs.
- Stress-tested all six built-in transcription models for install-once, concurrency, interrupted staging, retry, progress monotonicity, model switching, and cross-process restart reuse without network.
- Made transcription-model preparation cancellation real: the in-flight Hugging Face downloader runs in a killable helper process, cancellation discards staging without a ready marker, and a waiting sibling prepare can recover cleanly after the cancelled owner releases the install lock.
- Validated transcription language input against Whisper's supported language-code table, including explicit `zh` (Chinese/Mandarin) and `yue` (Cantonese) guidance.
- Upgraded the shared visual system toward liquid-glass/glassmorphism: browser surfaces use layered translucent gradients, backdrop blur, luminous edge highlights and restrained ambient depth; Tkinter mirrors the hierarchy with native opaque layered surfaces where true backdrop blur is unavailable.
- Added synchronized **Dark**, **Balanced**, and **Light** appearance modes in Settings for both the desktop UI and browser dashboard.
- Reworked runtime telemetry so managed downloads expose a dedicated download phase and percentage, hide irrelevant FPS data, separate downloaded bytes / stabilized transfer speed / remaining time, and keep extraction/install distinct from transfer progress.
- Made the browser dashboard launcher prominent in the desktop navigation (with `Ctrl+B`), increased inter-control gutters, and improved desktop glass-like depth with brighter edge highlights plus best-effort Windows 11 Acrylic/Mica backdrop integration.
- Fixed browser select/dropdown readability across Dark/Balanced/Light by explicitly theming option menus and applying the requested subtle dark edge treatment only to text inside boxed controls; ordinary labels/headings are left un-stroked.
- Strengthened Tkinter combobox/read-only/dropdown contrast and theme mapping across all three appearance modes.
- Removed visible development-version text from the desktop title, browser title, and exported diagnostics; user-facing branding is simply `SubBurn`.
- Added release hardening for public distribution: high-confidence source-secret scanning, deterministic FFmpeg/model runtime provenance, release-manifest coverage for that provenance artifact, and fail-closed CI/release workflow checks.
- Changed the installed `subburn` launcher from a console script to a GUI script so the packaged application does not reintroduce a CLI/console surface on Windows.
- Chose the Windows distribution architecture as a non-admin PyInstaller one-folder application wrapped by Inno Setup; FFmpeg and transcription model weights remain verified/on-demand rather than bundled.

### Removed

- CLI control surface.
- Maximum Compression subsystem (preserved separately for a future standalone project).

### Deferred

- Online subtitle search remains intentionally deferred until provider/legal/privacy/rate-limit design is completed.
