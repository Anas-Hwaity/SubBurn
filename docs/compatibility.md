# Compatibility and acceptance status

SubBurn separates **targeted support** from **acceptance evidence**. A platform is not called supported merely because Python/Tk or FFmpeg can theoretically run there.

| Area | Status in this rebuild | Evidence / blocker |
|---|---|---|
| Linux/X11 source install | Engineering-tested | Linux/Xvfb regression matrix, real FFmpeg A/B/C + Batch, clean wheel install/startup |
| Windows source/desktop target | Targeted; native acceptance pending | Distribution architecture is selected (PyInstaller one-folder + per-user Inno Setup), but clean-machine installer/DPI/non-admin/hardware tests remain required |
| macOS | Candidate target; not yet advertised as accepted | macOS path/font/runtime branches exist; real clean-machine acceptance remains required |
| Python 3.10–3.13 | Declared source range | Package metadata; hosted/native matrix still required before stable release |
| CPU FFmpeg encode | Engineering-tested on current Linux runner | Real libx264 workflow and software fallback paths |
| NVIDIA / Intel / AMD hardware encode | Capability-driven, acceptance pending | Probe/fallback logic tested; representative physical hardware matrix remains open |
| Browser dashboard | HTTP/security/action contracts tested | Chromium loopback DOM/visual E2E is blocked by the current execution environment |
| Local transcription | Controlled-simulation tested | Real pinned-model download + CPU/GPU transcription acceptance remains open |
| Managed FFmpeg download | Integrity/rollback logic tested | Live Windows publisher download/install/upgrade/rollback acceptance remains open |

## Compatibility rule

README/package classifiers describe intended product targets, not proof of stable support. Before a stable release, every platform advertised as supported must have a clean-machine acceptance record tied to the exact release candidate.
