from __future__ import annotations

import hashlib
import http.server
import importlib.util
import os
import pathlib
import socketserver
import sys
import tempfile
import threading
import time

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "subburn" / "app.py"
spec = importlib.util.spec_from_file_location("subburn_runtime_download_localhost", SRC)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

# Deterministic ~5 MiB payload. Throttle the response enough for the real rate/ETA estimator to
# leave its anti-spike warm-up window.
PAYLOAD = (bytes(range(256)) * (5 * 1024 * 1024 // 256 + 1))[: 5 * 1024 * 1024]
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path.endswith(".sha256"):
            body = (DIGEST + "  ffmpeg.zip\n").encode("ascii")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.endswith("ffmpeg.zip"):
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            chunk = 64 * 1024
            for i in range(0, len(PAYLOAD), chunk):
                self.wfile.write(PAYLOAD[i:i+chunk])
                self.wfile.flush()
                time.sleep(0.012)
            return
        self.send_error(404)


class FakeApp:
    def __init__(self):
        self.op_state = mod.OperationState()
        self.op_id = self.op_state.begin("runtime_download")
        self.snapshots = []
        self._operation_local = threading.local()
        self._operation_local.operation_id = self.op_id

    def current_operation_id(self):
        return self.op_id

    def set_stage(self, name, pct, message):
        self.op_state.stage(self.op_id, name, pct, message)
        self.snapshots.append(self.op_state.snapshot())

    def emit(self, kind, *args):
        if kind == "transfer_progress":
            self.op_state.transfer(self.op_id, *(list(args[:6]) + [None] * 6)[:6])
            self.snapshots.append(self.op_state.snapshot())


with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    app = FakeApp()
    app.set_stage("FFmpeg download", 0, "Checking publisher checksum")
    progress = mod.SubBurnApp._transfer_progress_callback(app, "FFmpeg runtime")
    with tempfile.TemporaryDirectory(prefix="subburn-local-runtime-") as td:
        dest = pathlib.Path(td) / "ffmpeg.zip"
        result = mod._download_verified_archive(
            f"http://127.0.0.1:{port}/ffmpeg.zip",
            dest,
            progress,
            checksum_url=f"http://127.0.0.1:{port}/ffmpeg.zip.sha256",
            require_checksum=True,
            phase=lambda text: app.set_stage("FFmpeg download", 0, text) if "download" in text.casefold() else None,
            reuse_cache=False,
        )
        assert dest.is_file() and dest.read_bytes() == PAYLOAD
        assert result["sha256"] == DIGEST
    server.shutdown()
    thread.join(timeout=2)

transfer_snaps = [s for s in app.snapshots if s.get("metric_profile") == "transfer"]
assert transfer_snaps, "no transfer snapshots captured"
assert any(s.get("bytes_total") == len(PAYLOAD) and s.get("bytes_done") == 0 for s in transfer_snaps), transfer_snaps[:5]
assert any(0 < s.get("bytes_done", 0) < len(PAYLOAD) for s in transfer_snaps), "no intermediate byte progress"
assert any(s.get("speed") not in {"-", "0 B/s"} for s in transfer_snaps), "no stabilized transfer speed"
assert any(s.get("eta") != "-" and 0 < s.get("bytes_done", 0) < len(PAYLOAD) for s in transfer_snaps), "no transfer ETA"
final = transfer_snaps[-1]
assert final["transfer_pct"] == 100.0, final
assert final["progress_pct"] == 99.0, final
assert final["bytes_done"] == len(PAYLOAD) and final["bytes_total"] == len(PAYLOAD), final
assert final["downloaded"] == "5.0 MiB / 5.0 MiB", final
print("REAL LOCALHOST RUNTIME DOWNLOAD TELEMETRY PASS")
