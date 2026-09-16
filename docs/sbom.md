# SBOM policy

SubBurn will not publish a decorative or knowingly incomplete SBOM.

The final release SBOM must be generated from the **reviewed locked release environment**, not only from direct requirements in `pyproject.toml`. It must include transitive Python packages and the exact versions used to build/test the release. Separately downloaded FFmpeg runtimes and transcription models must remain represented in provenance/runtime manifests even when they are not Python packages.

Until the dependency lock is generated and reviewed in a network-capable controlled environment, SBOM generation remains a release blocker. No partial direct-dependency SBOM is accepted.

Once the reviewed `uv.lock` exists, the manual release-candidate workflow:

1. validates the lock with `scripts/check_dependency_lock.py`;
2. requires `uv lock --check`;
3. exports the frozen all-extras graph as CycloneDX 1.5 (`dist/subburn.cdx.json`);
4. rejects an empty/malformed CycloneDX document;
5. includes the SBOM in release checksums and the machine-readable release manifest; and
6. creates a dedicated GitHub SBOM attestation for the wheel and sdist.

Separately downloaded FFmpeg runtimes and model snapshots remain represented by their own provenance manifests because they are not Python-package components of the wheel.

The release candidate also emits a deterministic `runtime-provenance.json` directly from the application source. It records the managed FFmpeg provider/source/checksum contract and every built-in model's immutable repository revision, license metadata, download policy and allowlisted files. `release_manifest.py` includes this file in `SHA256SUMS` and the machine-readable artifact manifest, and the release workflow includes it in build provenance attestation. This inventory complements-but never replaces-the locked CycloneDX Python SBOM.
