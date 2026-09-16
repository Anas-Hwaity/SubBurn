# Third-Party Notices

SubBurn does not relicense third-party software. This file records direct runtime dependencies and separately downloaded components known to the application. Final release packaging must regenerate and verify this inventory against the exact lockfile/artifact.

| Component | Role | Distribution relationship | License / terms |
|---|---|---|---|
| fontTools | Font inspection/preparation | Python dependency | MIT |
| regex | Grapheme segmentation | Python dependency | Apache-2.0 AND CNRI-Python |
| tkinterdnd2 | Optional native drag/drop wrapper | Optional Python dependency; may include TkDND binaries | MIT |
| TkDND | Native drag/drop extension used by tkinterdnd2 | Transitive binary/source component when drag/drop is packaged | TkDND `license.terms` permissive notice license; notice must be retained |
| faster-whisper | Optional local transcription engine | Optional Python dependency | MIT |
| CTranslate2 | Inference runtime | Optional direct/transitive Python dependency | MIT |
| huggingface_hub | Pinned model retrieval | Optional Python dependency | Apache-2.0 |
| Whisper CTranslate2 model snapshots | Local transcription model weights | Downloaded on explicit user request; not bundled in source package | MIT on the pinned model repositories currently used by SubBurn |
| Gyan FFmpeg Essentials | Video/subtitle rendering and encoding runtime | Downloaded on explicit user request; not bundled in source package | GPLv3 build; exact build configuration recorded after installation |

## Important packaging boundary

The SubBurn source/wheel must not include FFmpeg binaries or model weights. A future standalone desktop binary may include Python/Tk/runtime dependencies; that artifact requires a fresh license inventory and notices generated from the exact bundled contents before release.
