# Release process

SubBurn uses evidence-gated releases. A successful build is not sufficient.

## 1. Freeze release candidate

- Choose the release commit and version.
- Require a clean repository tree.
- Confirm the dependency lock is present, current, structurally validated, `uv lock --check` clean, and human-reviewed.
- Confirm third-party notices/provenance match the exact dependency/runtime/model set.
- Complete platform acceptance for every platform advertised in the README/package metadata.

## 2. Run acceptance gates

- repository/public-readiness checks;
- high-confidence source-secret scan;
- distribution-contract validation;
- deterministic non-Python runtime/model provenance inventory;
- source CI matrix;
- security/dependency review;
- real FFmpeg smoke and batch E2E;
- applicable real transcription/model/runtime/hardware tests;
- deterministic wheel + canonical sdist two-build comparison;
- clean install and startup from the exact built artifacts.

## 3. Build release candidate in GitHub Actions

Use the manual `Release candidate` workflow. It validates publication placeholders, the source-secret and distribution contracts, the frozen lock, exports an all-extras CycloneDX SBOM, emits deterministic runtime/model provenance, builds and verifies artifacts, creates `SHA256SUMS`, emits a machine-readable release manifest, uploads the candidate bundle, creates build-provenance attestations, and separately attests the SBOM. It deliberately does **not** publish a GitHub Release.

## 4. Human review

Review:

- release manifest and checksums;
- CI logs;
- dependency/provenance diff;
- SECURITY/README/CHANGELOG/release notes;
- exact installer/signing results if a desktop installer is being released (Windows architecture is documented in `docs/distribution.md`);
- known limitations and compatibility table.

## 5. Publication

Only after all release blockers are closed should a signed/attested release be published. Never replace or silently mutate a published version; issue a new version for corrections.
