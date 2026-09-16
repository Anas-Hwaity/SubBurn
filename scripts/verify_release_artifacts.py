from __future__ import annotations

import argparse
from email.parser import BytesParser
from email.policy import default
import hashlib
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

FORBIDDEN_SUFFIXES = {'.exe', '.dll', '.so', '.dylib', '.bin', '.onnx', '.pt', '.pth', '.safetensors'}
FORBIDDEN_NAMES = {'ffmpeg', 'ffprobe', 'ffmpeg.exe', 'ffprobe.exe'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f'artifact verification failed: {message}')


def forbidden(name: str) -> bool:
    p = PurePosixPath(name)
    return p.name.casefold() in FORBIDDEN_NAMES or p.suffix.casefold() in FORBIDDEN_SUFFIXES


def verify_wheel(root: Path, wheel: Path) -> None:
    source = (root / 'src/subburn/app.py').read_bytes()
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
        if any(forbidden(n) for n in names):
            fail('wheel contains a forbidden bundled runtime/model binary')
        required_payload = {'subburn/__init__.py', 'subburn/__main__.py', 'subburn/app.py'}
        if not required_payload.issubset(names):
            fail(f'wheel missing package files: {sorted(required_payload - set(names))}')
        if sha(z.read('subburn/app.py')) != sha(source):
            fail('wheel app.py does not match repository source bytes')
        licenses = [n for n in names if '.dist-info/licenses/' in n]
        for base in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md'):
            if not any(n.endswith('/' + base) for n in licenses):
                fail(f'wheel missing installed legal file: {base}')
        metadata_names = [n for n in names if n.endswith('.dist-info/METADATA')]
        if len(metadata_names) != 1:
            fail('wheel must contain exactly one METADATA file')
        meta = BytesParser(policy=default).parsebytes(z.read(metadata_names[0]))
        if meta['Name'] != 'subburn' or meta['Version'] != '2.8.0.dev0':
            fail(f'unexpected wheel identity: {meta["Name"]} {meta["Version"]}')
        if meta['License-Expression'] != 'Apache-2.0':
            fail(f'unexpected license expression: {meta["License-Expression"]}')
        if meta['Requires-Python'] != '<3.14,>=3.10':
            fail(f'unexpected Requires-Python: {meta["Requires-Python"]}')
        reqs = meta.get_all('Requires-Dist') or []
        if not any(r.startswith('fonttools') for r in reqs) or not any(r.startswith('regex') for r in reqs):
            fail('wheel runtime dependency metadata is incomplete')
        entry_names = [n for n in names if n.endswith('.dist-info/entry_points.txt')]
        if len(entry_names) != 1:
            fail('wheel must contain exactly one entry_points.txt')
        entry_text = z.read(entry_names[0]).decode('utf-8', errors='replace')
        if '[gui_scripts]' not in entry_text or 'subburn = subburn.app:main' not in entry_text:
            fail('wheel GUI entry point is missing or incorrect')
        if '[console_scripts]' in entry_text:
            fail('wheel must not expose a console/CLI launcher')


def verify_sdist(root: Path, sdist: Path, epoch: int | None) -> None:
    source = (root / 'src/subburn/app.py').read_bytes()
    with tarfile.open(sdist, 'r:gz') as t:
        members = t.getmembers()
        if not members:
            fail('empty sdist')
        top = members[0].name.split('/')[0]
        by_name = {m.name: m for m in members}
        required = [
            'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md', 'README.md', 'pyproject.toml', 'MANIFEST.in',
            'docs/dependencies.md', 'docs/compatibility.md', 'docs/distribution.md', 'docs/performance.md', 'docs/assets/subburn-desktop-home.png',
            'packaging/windows/README.md', 'packaging/windows/SubBurn.iss.in',
            'scripts/check_release_tree.py', 'scripts/check_dependency_lock.py', 'scripts/check_source_secrets.py',
            'scripts/check_distribution_contract.py', 'scripts/runtime_provenance_inventory.py', 'scripts/render_windows_installer.py',
            'scripts/canonicalize_sdist.py', 'scripts/verify_release_artifacts.py', 'scripts/run_linux_smoke.py', 'scripts/run_browser_e2e.py',
            'tests/browser_harness.py', 'tests/playwright_support.py', 'tests/make_fixture.py', 'tests/test_dependency_lock_contract.py',
            'tests/test_source_secret_scan.py', 'tests/test_distribution_contract.py', 'tests/test_runtime_provenance_inventory.py',
            'tests/test_release_workflow_contract.py', 'tests/test_windows_installer_renderer.py', 'tests/test_transcription_model_cancel.py',
            'tests/test_runtime_transfer_truth.py', 'tests/test_runtime_download_localhost.py', 'tests/test_burn_performance_contract.py', 'src/subburn/app.py',
            '.github/workflows/ci.yml', '.github/workflows/release-candidate.yml',
        ]
        missing = [rel for rel in required if f'{top}/{rel}' not in by_name]
        if missing:
            fail(f'sdist missing files: {missing}')
        if any(forbidden(m.name) for m in members if m.isfile()):
            fail('sdist contains a forbidden bundled runtime/model binary')
        app_member = by_name[f'{top}/src/subburn/app.py']
        stream = t.extractfile(app_member)
        if stream is None or sha(stream.read()) != sha(source):
            fail('sdist app.py does not match repository source bytes')
        if epoch is not None:
            for m in members:
                if int(m.mtime) != int(epoch):
                    fail(f'non-canonical sdist mtime: {m.name} -> {m.mtime}')
                if m.uid != 0 or m.gid != 0 or m.uname or m.gname:
                    fail(f'non-canonical sdist ownership metadata: {m.name}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--sdist', type=Path, required=True)
    parser.add_argument('--epoch', type=int)
    args = parser.parse_args()
    verify_wheel(args.root.resolve(), args.wheel.resolve())
    verify_sdist(args.root.resolve(), args.sdist.resolve(), args.epoch)
    print('release artifact verification: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
