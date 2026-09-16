from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
proc = subprocess.run(
    [sys.executable, str(ROOT / 'scripts' / 'check_writing_style.py')],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
assert proc.returncode == 0, proc.stdout
print('WRITING STYLE CONTRACT PASS')
