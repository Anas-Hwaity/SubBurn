#!/usr/bin/env python3
"""Run the real dashboard through Chromium against SubBurn's live loopback server."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable


def main() -> int:
    xvfb=shutil.which('xvfb-run')
    if os.name != 'nt' and sys.platform != 'darwin' and not xvfb:
        raise SystemExit('xvfb-run is required for the Tk dashboard harness on headless Linux')
    with tempfile.TemporaryDirectory(prefix='subburn-browser-e2e-') as td:
        sandbox=Path(td)
        fixture=sandbox/'fixture'
        subprocess.run([PY,str(ROOT/'tests/make_fixture.py'),str(fixture)],cwd=ROOT,check=True)
        portfile=sandbox/'port.txt';callsfile=sandbox/'calls.json'
        env=os.environ.copy();env.update({
            'SUBBURN_TEST_WORK':str(fixture),
            'SUBBURN_PORT_FILE':str(portfile),
            'SUBBURN_CALLS_FILE':str(callsfile),
            'XDG_CONFIG_HOME':str(sandbox/'config'),
            'XDG_DATA_HOME':str(sandbox/'data'),
            'XDG_CACHE_HOME':str(sandbox/'cache'),
            'XDG_STATE_HOME':str(sandbox/'state'),
        })
        harness_cmd=[PY,str(ROOT/'tests/browser_harness.py')]
        if xvfb and os.name != 'nt' and sys.platform != 'darwin':
            harness_cmd=[xvfb,'-a',*harness_cmd]
        with tempfile.TemporaryFile(mode='w+b') as harness_log:
            proc=subprocess.Popen(harness_cmd,cwd=ROOT,env=env,stdout=harness_log,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+30
                while time.monotonic()<deadline and not portfile.is_file():
                    if proc.poll() is not None:
                        harness_log.flush();harness_log.seek(0)
                        raise RuntimeError('dashboard harness exited before publishing its port:\n'+harness_log.read().decode('utf-8',errors='replace')[-8000:])
                    time.sleep(0.1)
                if not portfile.is_file():
                    raise RuntimeError('dashboard harness did not publish a loopback port within 30 seconds')
                test=subprocess.run([PY,str(ROOT/'tests/test_browser_playwright.py')],cwd=ROOT,env=env,text=True)
                if test.returncode != 0:
                    raise SystemExit(test.returncode)
                print('LIVE LOOPBACK BROWSER E2E PASS')
                return 0
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill();proc.wait(timeout=5)

if __name__ == '__main__':
    raise SystemExit(main())
