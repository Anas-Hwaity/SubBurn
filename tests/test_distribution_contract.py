from __future__ import annotations
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_distribution_contract', ROOT/'scripts/check_distribution_contract.py')
mod = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
errors = mod.check(ROOT)
assert errors == [], errors
print('DISTRIBUTION CONTRACT PASS')
