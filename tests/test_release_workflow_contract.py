from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
wf = (ROOT / '.github/workflows/release-candidate.yml').read_text(encoding='utf-8')
ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
required = (
    'check_release_tree.py',
    'check_public_repo.py --publication',
    'check_source_secrets.py',
    'check_distribution_contract.py',
    'check_dependency_lock.py',
    'uv lock --check',
    'cyclonedx1.5',
    'runtime-provenance.json',
    'release-manifest.json',
    'SHA256SUMS',
    'sbom-path: dist/subburn.cdx.json',
)
for token in required:
    assert token in wf, token
# The candidate workflow is intentionally non-publishing and must not request release-writing content scope.
assert 'contents: write' not in wf
for forbidden in ('gh release create', 'softprops/action-gh-release', 'ncipollo/release-action'):
    assert forbidden not in wf
# All external actions stay immutable-SHA pinned.
for use in re.findall(r'^\s*-?\s*uses:\s*([^\s#]+)', wf, flags=re.M):
    assert re.fullmatch(r'[^@\s]+@[0-9a-fA-F]{40}', use), use
assert 'browser-loopback-e2e:' in ci and 'python scripts/run_browser_e2e.py' in ci
assert 'playwright==1.57.0' in ci
print('RELEASE WORKFLOW CONTRACT PASS')
