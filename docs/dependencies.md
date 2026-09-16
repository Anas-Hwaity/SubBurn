# Dependency and provenance policy

## Direct Python dependencies

The public source package keeps the always-needed dependency set small:

- `fonttools>=4.63.0,<5`
- `regex>=2026.5.9,<2027`

Optional features are separated:

- drag/drop: `tkinterdnd2>=0.6.3,<0.7`
- transcription: `faster-whisper==1.2.1`, `ctranslate2==4.8.2`, `huggingface-hub==1.31.0`

`pyproject.toml` describes compatibility intent. A dependency lock has **not** been committed yet because the WIP11 build environment could not resolve PyPI. Generating, reviewing, and committing that lock from a controlled networked environment is a release blocker; no stable release may claim a locked dependency graph before that happens.

## FFmpeg

SubBurn does not ship FFmpeg inside its Python source distribution. The in-app managed runtime currently points to Gyan's release Essentials ZIP and requires publisher SHA-256 verification before extraction. Gyan states its static builds are GPLv3. SubBurn records the downloaded archive hash, publisher hash, FFmpeg version, and build configuration in its runtime manifest.

Because FFmpeg build licensing depends on configuration and enabled libraries, any future decision to bundle an FFmpeg binary in a SubBurn installer must trigger a new exact-build license review rather than relying on a generic FFmpeg statement.

`python scripts/runtime_provenance_inventory.py` emits a deterministic `runtime-provenance.json` describing the managed FFmpeg source/checksum contract and all six pinned model repository/revision/license tuples. It complements the Python CycloneDX SBOM; it is not a substitute for the final locked Python dependency graph.

## Transcription models

Every supported model maps to an immutable repository/revision pair in application source. SubBurn downloads only the allowlisted CTranslate2 files for that exact revision into a staging directory, validates the snapshot, then atomically installs it. Inference is local-only from that prepared directory.

The currently audited model pins are:

| Model | Repository | Immutable revision | License recorded by SubBurn |
|---|---|---|---|
| large-v3 | `Systran/faster-whisper-large-v3` | `edaa852ec7e145841d8ffdb056a99866b5f0a478` | MIT |
| turbo | `dropbox-dash/faster-whisper-large-v3-turbo` | `0c94664816ec82be77b20e824c8e8675995b0029` | MIT |
| medium | `Systran/faster-whisper-medium` | `7832330bcea9a8d5fd6d6637c49fe5d256e98277` | MIT |
| small | `Systran/faster-whisper-small` | `536b0662742c02347bc0e980a01041f333bce120` | MIT |
| base | `Systran/faster-whisper-base` | `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66` | MIT |
| tiny | `Systran/faster-whisper-tiny` | `d90ca5fe260221311c53c58e660288d3deb8d356` | MIT |

Model weights are not included in the SubBurn source or wheel.

## Python/Tk packaging

A standalone executable can bundle CPython, Tcl/Tk, TkDND, CTranslate2, PyAV/FFmpeg libraries and other transitive dependencies. The executable is therefore a different distribution artifact from the Python wheel and requires an artifact-specific SBOM/notices pass before publication.


## Reproducible build environment

WIP11 reproducibility was validated with Python 3.13, `setuptools==82.0.1`, and `uv 0.10.0` in the local runner. The build-system requirement pins setuptools to the version actually tested. CI installs a pinned uv release separately and must rerun the deterministic artifact comparison before a release.
