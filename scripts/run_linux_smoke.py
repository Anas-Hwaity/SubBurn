from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'
FAST = [
    'test_progress_engine.py', 'test_control_contract.py', 'test_ui_structure.py',
    'test_storage_runtime_hygiene.py', 'test_dependency_provenance.py',
    'test_runtime_transcription_sim.py', 'test_dashboard_api_smoke.py',
    'test_browser_security.py', 'test_browser_action_dispatch.py',
    'test_preset_recovery_smoke.py', 'test_process_controls_smoke.py',
]


def command_for(test: Path) -> list[str]:
    xvfb = shutil.which('xvfb-run')
    base = [sys.executable, str(test)]
    return [xvfb, '-a', *base] if xvfb else base


def isolated_env(base: Path, name: str, fixture: Path) -> dict[str, str]:
    home = base / ('home-' + name)
    env = os.environ.copy()
    for key, leaf in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:
        path = home / leaf; path.mkdir(parents=True, exist_ok=True); env[key] = str(path)
    out = home / 'output'; out.mkdir(parents=True, exist_ok=True); env['SUBBURN_OUTPUT_HOME'] = str(out)
    env['SUBBURN_TEST_WORK'] = str(fixture)
    env['PYTHONUNBUFFERED'] = '1'
    return env


def run_test(base: Path, fixture: Path, name: str, test: str, extra: dict[str,str] | None = None, timeout: int = 120) -> None:
    env = isolated_env(base, name, fixture)
    if extra: env.update(extra)
    print(f'== {name} ==', flush=True)
    subprocess.run(command_for(TESTS / test), cwd=ROOT, env=env, check=True, timeout=timeout)


def main() -> int:
    if sys.platform != 'linux':
        raise SystemExit('run_linux_smoke.py is intentionally Linux-only')
    with tempfile.TemporaryDirectory(prefix='subburn-ci-') as td:
        base = Path(td); fixture = base / 'fixture'
        subprocess.run([sys.executable, str(TESTS / 'make_fixture.py'), str(fixture)], cwd=ROOT, check=True)
        for test in FAST:
            run_test(base, fixture, test.removeprefix('test_').removesuffix('.py'), test)
        migration = base / 'legacy-home'; migration.mkdir()
        env = os.environ.copy(); env['SUBBURN_MIGRATION_HOME'] = str(migration); env['PYTHONUNBUFFERED'] = '1'
        subprocess.run(command_for(TESTS / 'test_legacy_storage_migration.py'), cwd=ROOT, env=env, check=True, timeout=60)
        for group in ('A','B','C'):
            work = base / f'e2e-{group}'; shutil.copytree(fixture, work)
            run_test(base, work, f'e2e-{group}', 'test_core_e2e_group.py', {'SUBBURN_E2E_GROUP': group}, 120)
        batch_work = base / 'batch'; shutil.copytree(fixture, batch_work)
        run_test(base, batch_work, 'batch', 'test_batch_e2e.py', timeout=120)
    print('LINUX SMOKE MATRIX PASS')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
