# Release readiness

This repository is still a pre-release engineering build. Passing CI is necessary but is not, by itself, permission to call SubBurn stable.

## Proven in the current rebuild

- Source tree contains no bundled FFmpeg runtime or transcription model weights.
- CLI and the former Maximum Compression subsystem are absent.
- Canonical operation progress is regression-tested.
- Browser dashboard security has adversarial HTTP tests for session, Host/Origin, request size and filesystem confinement.
- GitHub CI now contains a dedicated live Chromium-to-loopback dashboard E2E job with a portable system/Playwright Chromium launcher; it remains unproven until the workflow runs on a hosted runner.
- Real FFmpeg smoke tests exercise analyze, validation, live frame/clip, preview, comparison, encoder probe/benchmark, text/image/interval watermarking, final hard-burn verification and persistent batch execution.
- Wheel and canonicalized sdist can be rebuilt byte-identically in the tested pinned build environment.
- A canonical sdist rebuilds the identical wheel.
- Tkinter workflow pages passed headless visual QA at the supported 980×680 minimum and increased Tk scaling; a visual contract checks navigation state, action roles, shortcuts and containment.
- Existing compatible FFmpeg is a tested startup invariant: a real application instance with system FFmpeg present is forbidden from invoking the managed downloader. Discovery now enforces **PATH/system → user-selected file/folder → managed runtime**, evaluates all candidates inside each stage instead of trusting only the first hit, and has controlled Windows-user-PATH promotion coverage for a verified managed pair.
- The managed-runtime transfer UI adapter has a regression test for the exact argument-shape failure observed on Windows, in addition to byte/speed/ETA and terminal-state progress contracts.
- Managed-runtime download presentation is byte-truthful: entering the download phase displays 0.0% before the first byte, downloaded/total bytes become visible as soon as Content-Length is known, stabilized transfer speed and ETA are separate metrics, and exact transfer 100% cannot make the operation itself claim 100% before verification/install completes. A real throttled localhost archive/checksum transfer exercises the urllib path end-to-end.
- Plain text-subtitle-only final burns use a one-filter `ass=...`/libass graph when watermarking, scaling and FPS conversion are not requested. This preserves the lean path from the earlier SubBurn 4x subtitle burner without changing the selected codec, encoder, quality, speed, audio, resolution/FPS or other requested settings. Hardware-first Auto selection and speed-preset preservation are release contracts; native GPU benchmarking remains external acceptance.
- Managed FFmpeg install-once/recovery tests cover concurrent callers, verified cache reuse, corrupt cache rejection, post-download retry, and suppression of repeated automatic attempts after a same-session install failure.
- All six built-in pinned transcription models have controlled install-once/concurrency/recovery/progress/restart stress coverage. A fresh interpreter pointed at an already prepared model store must reuse every model with networking hard-disabled.
- Model-preparation cancellation now uses a killable downloader helper process; controlled acceptance proves prompt termination, incomplete-stage cleanup, no false ready marker, and lock recovery for a waiting sibling prepare. Real upstream cancellation still requires a network-enabled run.
- Transcription language entry validates against the 100-language Whisper table and fails early on unsupported pseudo-country codes.
- WIP18 visual QA covers all eight Tkinter pages and all three appearance modes at representative desktop/minimum scaling, while static Chromium coverage renders all eight browser pages at desktop, compact desktop, and mobile-like widths across Dark/Balanced/Light. Live Chromium-to-loopback remains externally blocked in this container.
- User-facing product branding is `SubBurn` without the development version in window/browser titles or diagnostics. Internal package/build versioning remains release metadata.


## Additional release hardening prepared after WIP19

- A high-confidence source-secret scanner now rejects private-key material and common credential/token formats in public-tree text before CI/release proceeds.
- A deterministic `runtime-provenance.json` generator records the managed FFmpeg source/checksum contract and all six immutable transcription-model repository/revision/license tuples. Release checksums/manifests include this runtime inventory separately from the Python SBOM.
- The end-user Windows distribution architecture is now decided: PyInstaller one-folder application wrapped by a per-user, non-admin Inno Setup installer. FFmpeg and model weights remain on-demand and are not bundled.
- Package metadata now exposes `subburn` as a GUI launcher rather than a console script; artifact verification rejects any `[console_scripts]` regression.
- The committed installer template contains no signing credentials and no FFmpeg/model payload. Stable Windows publication still fails closed until the exact native package is Authenticode-signed and accepted on real Windows.
- A fresh WIP20 network probe still cannot resolve `pypi.org`, `huggingface.co`, or `www.gyan.dev`; `uv lock` therefore remains impossible here and no synthetic lock/SBOM has been substituted.

## Public-repository hardening added in WIP12

- Security policy directs sensitive reports to GitHub private vulnerability reporting.
- Contributor, pull-request and structured issue contracts are committed.
- Dependabot is configured for Python and GitHub Actions.
- Dependency-review workflow uses an immutable action SHA.
- Repository readiness checks reject unpinned Actions, missing governance/security files and sensitive-looking file types.
- Manual release-candidate workflow builds, verifies, checksums and attests artifacts but does not publish a GitHub Release.
- Release-candidate workflow fails closed while the reviewed `uv.lock` is absent.
- GitHub publication settings are documented separately in `docs/github-security-settings.md`.


## Lock/SBOM hardening prepared in WIP14

- A committed lock will be rejected if direct dependencies are absent, exact pins drift, direct sources are mutable/non-registry, or direct registry packages lack SHA-256 artifact integrity.
- Release-candidate validation will also require `uv lock --check`.
- The frozen all-extras lock will export CycloneDX 1.5, which must contain components before release proceeds.
- The SBOM will be checksummed, included in the release manifest, uploaded with the candidate, and separately attested against the wheel/sdist.
- The lock itself is still unavailable in this container: the WIP18 `uv lock` retry again failed at PyPI DNS resolution (`pypi.org`), so no synthetic or unverifiable lock was committed.

## Release blockers still open
- Replace the intentional `OWNER/REPOSITORY` security-reporting placeholder after the final GitHub repository identity is known.
- After repository creation, enable/verify CodeQL default setup, secret scanning/push protection where available, Dependabot security features, private vulnerability reporting and the default-branch ruleset described in `docs/github-security-settings.md`.
- Run the committed CI/dependency-review/release-candidate workflows on GitHub-hosted runners; local validation does not prove GitHub repository settings or hosted-runner behavior.

- Generate and review a committed dependency lock from a networked controlled environment; this container could not resolve PyPI when WIP11 was prepared.
- Run clean-machine acceptance on supported Windows and macOS systems, not only Linux/Xvfb.
- In a network-enabled clean environment, download each intended built-in pinned transcription model at least once and run representative real inference (tiny first for smoke, then the larger models as storage/time permits). Current container DNS cannot resolve Hugging Face; controlled tests therefore prove orchestration/reuse/recovery, not upstream multi-GB transfer or model accuracy.
- Exercise the managed Gyan FFmpeg checksum/archive download, extraction, restart/retry and reuse against the live publisher endpoint on Windows. Current container DNS cannot resolve the publisher, so real upstream transfer remains unproven here.
- Complete representative NVIDIA, Intel and AMD hardware-encoder acceptance; unsupported hardware must continue to fall back safely.
- Run browser DOM E2E in an environment that permits Chromium to access loopback. The current execution environment blocks loopback Chromium before it reaches SubBurn; authenticated HTTP/action coverage exists as compensation, but this is not equivalent to browser acceptance.
- Complete DPI/accessibility/keyboard checks on real desktop environments.
- Build and test the decided Windows distribution format (PyInstaller one-folder + per-user Inno Setup), then Authenticode-sign the exact executable/installer. The architecture is decided; native packaging/signing acceptance remains open.
- Final secret/privacy/license/SBOM review must be performed on the exact release artifact.

## Deferred feature

Online subtitle search is intentionally postponed until the hardened public core is complete. It requires a separate provider/legal/privacy/rate-limit design before implementation.
