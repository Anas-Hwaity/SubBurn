from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'
PY = sys.executable
XVFB = shutil.which('xvfb-run')


def run(cmd: list[str], env: dict[str, str], label: str) -> None:
    print(f'\n=== {label} ===', flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def py_test(name: str, env: dict[str, str], *, gui: bool = False, label: str | None = None) -> None:
    cmd = [PY, str(TESTS / name)]
    if gui and XVFB:
        cmd = [XVFB, '-a', *cmd]
    run(cmd, env, label or name)


def make_env(root: Path) -> tuple[dict[str, str], Path]:
    fixture = root / 'fixture'
    subprocess.run([PY, str(TESTS / 'make_fixture.py'), str(fixture)], cwd=ROOT, check=True)
    if not (fixture / 'input.mp4').is_file() or not (fixture / 'input.srt').is_file():
        raise RuntimeError('fixture generator did not create required input.mp4/input.srt')
    env = os.environ.copy()
    env.update({
        'SUBBURN_TEST_WORK': str(fixture),
        'XDG_CONFIG_HOME': str(root / 'config'),
        'XDG_DATA_HOME': str(root / 'data'),
        'XDG_CACHE_HOME': str(root / 'cache'),
        'XDG_STATE_HOME': str(root / 'state'),
    })
    return env, fixture


def run_fast() -> None:
    with tempfile.TemporaryDirectory(prefix='subburn-accept-fast-') as td:
        sandbox = Path(td)
        env, _fixture = make_env(sandbox)
        py_test('test_progress_engine.py', env, gui=True)
        py_test('test_progress_reporting_matrix.py', env)
        py_test('test_terminal_elapsed_freeze.py', env)
        py_test('test_progress_event_pressure.py', env)
        py_test('test_progress_ui_surfaces.py', env, gui=True)
        py_test('test_control_contract.py', env, gui=True)
        py_test('test_ui_structure.py', env, gui=True)
        py_test('test_visual_contract.py', env, gui=True)
        py_test('test_appearance_contract.py', env)
        py_test('test_browser_static_visual.py', env)
        py_test('test_browser_fallback_font_ui.py', env)
        py_test('test_browser_transcription_language_picker.py', env)
        py_test('test_existing_ffmpeg_startup.py', env, gui=True)
        py_test('test_ffmpeg_discovery.py', env)
        py_test('test_ffmpeg_priority_and_path.py', env)
        py_test('test_ffmpeg_windows_path_promotion.py', env)
        py_test('test_ffmpeg_filter_probe.py', env)
        py_test('test_download_reporting.py', env)
        py_test('test_runtime_transfer_truth.py', env)
        py_test('test_runtime_download_localhost.py', env)
        py_test('test_burn_performance_contract.py', env)
        py_test('test_font_render_cache_long_srt.py', env)
        py_test('test_watermark_font_intent.py', env)
        py_test('test_text_watermark_single_pass.py', env)
        py_test('test_output_attribution_contract.py', env)
        py_test('test_recents_clear.py', env)
        py_test('test_runtime_install_once.py', env)
        py_test('test_transcription_model_stress.py', env)
        py_test('test_transcription_model_cancel.py', env)
        py_test('test_transcription_language_codes.py', env)
        py_test('test_transcription_language_picker_ui.py', env, gui=True)
        py_test('test_tk_combobox_and_preview_layout.py', env, gui=True)
        py_test('test_dependency_provenance.py', env)
        py_test('test_storage_runtime_hygiene.py', env)
        py_test('test_dashboard_api_smoke.py', env, gui=True)
        py_test('test_browser_security.py', env, gui=True)
        py_test('test_browser_action_dispatch.py', env, gui=True)
        py_test('test_wip24_final_polish.py', env, gui=True)
        py_test('test_runtime_transcription_sim.py', env, gui=True)
        py_test('test_preset_recovery_smoke.py', env, gui=True)
        py_test('test_process_controls_smoke.py', env, gui=True)
        migration_env = env.copy()
        migration_env['SUBBURN_MIGRATION_HOME'] = str(sandbox / 'migration-home')
        py_test('test_legacy_storage_migration.py', migration_env)
        py_test('test_source_secret_scan.py', env)
        py_test('test_runtime_provenance_inventory.py', env)
        py_test('test_distribution_contract.py', env)
        py_test('test_windows_installer_renderer.py', env)
        py_test('test_release_workflow_contract.py', env)
        py_test('test_public_repo_contract.py', env)
        py_test('test_writing_style_contract.py', env)
        py_test('test_release_manifest.py', env)
        py_test('test_dependency_lock_contract.py', env)


def run_e2e_group(group: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f'subburn-accept-e2e-{group.lower()}-') as td:
        env, _fixture = make_env(Path(td))
        env['SUBBURN_E2E_GROUP'] = group
        py_test('test_core_e2e_group.py', env, gui=True, label=f'core E2E group {group}')


def run_batch() -> None:
    with tempfile.TemporaryDirectory(prefix='subburn-accept-batch-') as td:
        env, _fixture = make_env(Path(td))
        py_test('test_batch_e2e.py', env, gui=True, label='persistent batch E2E')


def main() -> int:
    ap = argparse.ArgumentParser(description='Run SubBurn local acceptance gates with isolated fixtures/state.')
    ap.add_argument('--phase', choices=['fast', 'A', 'B', 'C', 'batch', 'all'], default='fast')
    args = ap.parse_args()
    if args.phase in {'fast', 'all'}:
        run_fast()
    if args.phase in {'A', 'B', 'C'}:
        run_e2e_group(args.phase)
    elif args.phase == 'all':
        for group in ('A', 'B', 'C'):
            run_e2e_group(group)
        run_batch()
    elif args.phase == 'batch':
        run_batch()
    print(f'\nSUBBURN ACCEPTANCE {args.phase}: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
