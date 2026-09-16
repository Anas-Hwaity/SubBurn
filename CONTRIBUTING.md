# Contributing to SubBurn

SubBurn accepts focused, testable changes. The project values correctness, recovery behavior, privacy, and evidence over feature count.

## Before opening a change

- Search existing issues and pull requests.
- For security-sensitive findings, follow `SECURITY.md` instead of opening a public issue.
- Keep changes scoped. Avoid unrelated cleanup in the same pull request.
- Do not add runtime downloads, network calls, bundled binaries, fonts, models, telemetry, or new dependencies without provenance/license/privacy analysis.
- Do not weaken validation or tests to make a failing change pass.

## Development setup

Supported source-development Python versions are 3.10–3.13.

```bash
python -m venv .venv
# activate .venv
python -m pip install -e .
```

Optional capabilities:

```bash
python -m pip install -e '.[dragdrop]'
python -m pip install -e '.[transcription]'
```

FFmpeg is an external runtime boundary. Tests that exercise rendering require a compatible `ffmpeg`/`ffprobe` pair.

## Required checks

Run at minimum:

```bash
python scripts/check_release_tree.py
python scripts/check_public_repo.py
python -m compileall -q src scripts tests
python tests/test_progress_engine.py
python tests/test_control_contract.py
python tests/test_ui_structure.py
```

On Linux with FFmpeg, Xvfb and fixture dependencies available:

```bash
python scripts/run_linux_smoke.py
```

Changes affecting packaging must also rebuild and verify wheel/sdist artifacts using the repository release scripts.

## Tests and defect scope

A bug report is evidence of a defect class, not permission for a one-line symptom patch. Fix the shared boundary, audit sibling paths, and add a regression test that would have caught the original issue.

For UI changes, preserve the control contract and test both Tkinter and browser-facing state/action paths. For progress changes, preserve monotonicity, terminal-state, stale-event and foreground/background invariants.

## Dependencies

`pyproject.toml` is the public dependency declaration. A reviewed lockfile is still a release blocker and must be generated in a trusted network-capable environment; do not fabricate lock content from guesses or a partial environment.

Any dependency change must document:

- why the dependency is necessary;
- exact distribution/source;
- license;
- whether it is bundled or downloaded;
- security/provenance implications;
- removal/fallback behavior where applicable.

## Pull requests

Pull requests should explain the problem, the architectural boundary changed, test evidence, risk/rollback considerations, and user-visible behavior. Screenshots are useful for UI changes but do not replace tests.

Write documentation and UI copy in direct, concrete English. Avoid promotional wording, filler, stock assistant phrases, and inflated claims.
