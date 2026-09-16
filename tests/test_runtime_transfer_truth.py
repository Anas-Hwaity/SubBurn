from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "subburn" / "app.py"
spec = importlib.util.spec_from_file_location("subburn_runtime_transfer_truth", SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class RuntimeTransferTruthTests(unittest.TestCase):
    def test_download_display_starts_at_true_zero_and_exposes_transfer_fields(self):
        state = mod.OperationState()
        op = state.begin("runtime_download")
        # Discovery may have completed internally, but once the real download phase starts the
        # visible progress must reflect bytes, not the old 5% setup weight.
        state.stage(op, "Tools", 100, "Local candidates checked")
        state.stage(op, "FFmpeg download", 0, "Checking publisher checksum")
        snap = state.snapshot()
        self.assertEqual(snap["metric_profile"], "transfer")
        self.assertEqual(snap["transfer_pct"], 0.0)
        self.assertEqual(snap["progress_pct"], 0.0)
        self.assertEqual(snap["downloaded"], "0.0 B / -")

        total = 106 * 1024 * 1024
        state.transfer(op, 0.0, 0, total, 0.0, None, "Download connected")
        snap = state.snapshot()
        self.assertEqual(snap["progress_pct"], 0.0)
        self.assertIn("0.0 B / 106.0 MiB", snap["downloaded"])
        self.assertEqual(snap["speed"], "-")

        done = 53 * 1024 * 1024
        state.transfer(op, 50.0, done, total, 14 * 1024 * 1024, 53 / 14, "Downloading")
        snap = state.snapshot()
        self.assertEqual(snap["progress_pct"], 50.0)
        self.assertEqual(snap["transfer_pct"], 50.0)
        self.assertEqual(snap["speed"], "14.0 MiB/s")
        self.assertIn("53.0 MiB / 106.0 MiB", snap["downloaded"])
        self.assertNotEqual(snap["eta"], "-")

    def test_transfer_metric_may_be_100_but_operation_bar_waits_for_success(self):
        state = mod.OperationState()
        op = state.begin("runtime_download")
        state.stage(op, "FFmpeg download", 0, "Downloading")
        state.transfer(op, 100.0, 100, 100, 10.0, 0.0, "Archive received")
        snap = state.snapshot()
        self.assertEqual(snap["transfer_pct"], 100.0)
        self.assertEqual(snap["progress_pct"], 99.0)
        self.assertEqual(snap["overall_pct"], 99.0)
        self.assertEqual(snap["operation_state"], "running")
        state.stage(op, "FFmpeg install", 20, "Extracting")
        self.assertEqual(state.snapshot()["progress_pct"], 99.0)
        state.finish(op, "succeeded")
        self.assertEqual(state.snapshot()["progress_pct"], 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
