"""
Local dashboard server for IPO Monitor.

Run:  python scripts/local_server.py
Then: http://localhost:8080
Click "🤖 生成完整版" to run generate.py locally.
"""
import http.server
import json
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

PORT = 8080
ROOT = Path(__file__).parent.parent  # repo root

_state = {"running": False, "log": ""}


def _run_generate():
    _state["running"] = True
    _state["log"] = "Running..."
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
            env=env,
        )
        _state["log"] = (result.stdout + result.stderr).strip()
    except Exception as e:
        _state["log"] = str(e)
    finally:
        _state["running"] = False


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "docs"), **kwargs)

    def do_GET(self):
        if self.path == "/status":
            body = json.dumps(_state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/run-generate":
            if _state["running"]:
                self._json(409, {"error": "Already running"})
                return
            threading.Thread(target=_run_generate, daemon=True).start()
            self._json(200, {"started": True})
            return
        self._json(404, {"error": "Not found"})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # silence request logs


if __name__ == "__main__":
    os.chdir(ROOT)
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"[local_server] Dashboard: {url}")
    print(f"[local_server] Press Ctrl+C to stop")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[local_server] Stopped.")
