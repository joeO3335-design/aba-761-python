"""Desktop entry point for the Repertiores Suite (Repertiores + FBA Tracker).

Launches BOTH Streamlit apps as child processes (headless, loopback-only) and a
tiny landing "chooser" page, all inside one native macOS window (pywebview).

  ┌── pywebview window ──────────────────────────────┐
  │  landing chooser  (http://127.0.0.1:<landing>)   │
  │     ├─▶ Programming — Repertiores  :<rep>         │
  │     └─▶ Assessment  — FBA Tracker  :<fba>         │
  └──────────────────────────────────────────────────┘

Each app gets a "⌂ Suite Home" link back to the chooser via the SWITCH_URL env
var (so the apps don't need to know each other's ports). Ports are chosen
dynamically and injected, so nothing is hard-coded.

Streamlit owns its process's main thread (signal handlers); pywebview owns THIS
process's main thread (Cocoa loop) — hence the apps run as subprocesses.
"""

import atexit
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve(app_bundle_name, *dev_relpath):
    """Find an app file in the bundle layout (next to this file) or dev layout."""
    bundled = os.path.join(HERE, app_bundle_name)
    if os.path.exists(bundled):
        return bundled
    return os.path.abspath(os.path.join(HERE, *dev_relpath))


# Bundle ships repertiores_app.py / fba_app.py beside this file; dev uses the
# real source locations.
REP_APP = _resolve("repertiores_app.py", "app.py")
FBA_APP = _resolve("fba_app.py", "..", "fba_tracker\U0001F4F1", "app.py")


def free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_streamlit(app_file, port, extra_env):
    env = os.environ.copy()
    env.update(extra_env)
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_file,
        "--server.address", "127.0.0.1",
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    return subprocess.Popen(cmd, cwd=os.path.dirname(app_file) or HERE, env=env)


def wait_until_up(port, proc, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


def _landing_html(rep_url, fba_url):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Repertiores Suite</title>
<style>
  html,body{{height:100%;margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);}}
  .wrap{{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px;}}
  h1{{font-size:30px;font-weight:800;color:#111827;margin:0;}}
  .sub{{color:#6b7280;font-size:15px;margin-top:-16px;}}
  .cards{{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;}}
  a.card{{text-decoration:none;width:280px;background:#fff;border-radius:18px;padding:28px 26px;
    border:2px solid #e5e7eb;box-shadow:0 4px 16px rgba(0,0,0,.06);transition:all .15s;display:block;}}
  a.card:hover{{transform:translateY(-3px);box-shadow:0 10px 28px rgba(0,0,0,.12);}}
  a.rep:hover{{border-color:#2563eb;}} a.fba:hover{{border-color:#16a34a;}}
  .emoji{{font-size:40px;}}
  .title{{font-size:20px;font-weight:800;margin:14px 0 6px;color:#111827;}}
  .rep .title{{color:#1d4ed8;}} .fba .title{{color:#15803d;}}
  .desc{{font-size:13px;color:#6b7280;line-height:1.5;}}
</style></head><body><div class="wrap">
  <h1>🧩 Repertiores Suite</h1>
  <div class="sub">Choose a tool — both share the same learners.</div>
  <div class="cards">
    <a class="card fba" href="{fba_url}" target="_self">
      <div class="emoji">📋</div>
      <div class="title">Assessment</div>
      <div class="desc">FBA Tracker — ABC data, indirect assessments, and functional analysis.</div>
    </a>
    <a class="card rep" href="{rep_url}" target="_self">
      <div class="emoji">🎯</div>
      <div class="title">Programming</div>
      <div class="desc">Repertiores — VB-MAPP, EFL, cold-probe targets, and mastery tracking.</div>
    </a>
  </div>
</div></body></html>"""


def start_landing_server(rep_url, fba_url, port):
    html = _landing_html(rep_url, fba_url).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, *args):
            pass  # quiet

    server = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    landing_port = free_port()
    rep_port = free_port()
    fba_port = free_port()
    landing_url = f"http://127.0.0.1:{landing_port}"

    # Shared roster + Repertiores data; FBA keeps its own files in a subdir so the
    # two students.json schemas never collide.
    rep_data = os.environ.get("REPERTIORES_DATA_DIR")
    fba_data = os.environ.get("FBA_DATA_DIR")

    common = {"SWITCH_URL": landing_url}
    rep_env = dict(common)
    fba_env = dict(common)
    if rep_data:
        rep_env["REPERTIORES_DATA_DIR"] = rep_data
        fba_env["REPERTIORES_DATA_DIR"] = rep_data  # FBA reads the shared roster
    if fba_data:
        fba_env["FBA_DATA_DIR"] = fba_data

    rep_proc = start_streamlit(REP_APP, rep_port, rep_env)
    fba_proc = start_streamlit(FBA_APP, fba_port, fba_env)
    procs = [rep_proc, fba_proc]

    def _shutdown():
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    atexit.register(_shutdown)

    rep_ok = wait_until_up(rep_port, rep_proc)
    fba_ok = wait_until_up(fba_port, fba_proc)
    if not (rep_ok and fba_ok):
        sys.stderr.write(f"Suite: a server failed to start (rep={rep_ok} fba={fba_ok}).\n")
        _shutdown()
        sys.exit(1)

    rep_url = f"http://127.0.0.1:{rep_port}"
    fba_url = f"http://127.0.0.1:{fba_port}"
    # Bind the landing server on the SAME port we already advertised via
    # SWITCH_URL, so each app's "Suite Home" link resolves.
    start_landing_server(rep_url, fba_url, landing_port)

    if os.environ.get("REPERTIORES_SMOKE_TEST"):
        sys.stdout.write(f"SMOKE_OK landing={landing_port} rep={rep_port} fba={fba_port}\n")
        sys.stdout.flush()
        _shutdown()
        return

    import webview
    webview.create_window(
        "Repertiores Suite",
        landing_url,
        width=1380,
        height=900,
        min_size=(1000, 680),
    )
    try:
        webview.start(gui="cocoa")
    except Exception:
        import traceback
        traceback.print_exc()
    _shutdown()


if __name__ == "__main__":
    main()
