"""Desktop entry point for Repertiores.

Starts the Streamlit server as a child process (headless, loopback-only) and
shows it inside a native macOS window (WebKit via pywebview) — no terminal, no
browser tab. This is what the bundled Repertiores.app launches.

Streamlit must own its process's main thread (it installs signal handlers), and
pywebview must own *this* process's main thread (the Cocoa event loop), so the
two can't share one process — Streamlit runs as a subprocess.
"""

import atexit
import os
import socket
import subprocess
import sys
import time
from contextlib import closing

HERE = os.path.dirname(os.path.abspath(__file__))
APP_FILE = os.path.join(HERE, "app.py")


def find_free_port(preferred=8701):
    """Use the preferred port if free, otherwise let the OS pick one."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s2:
                s2.bind(("127.0.0.1", 0))
                return s2.getsockname()[1]


def start_streamlit(port):
    """Launch `streamlit run app.py` as a child process bound to loopback."""
    cmd = [
        sys.executable, "-m", "streamlit", "run", APP_FILE,
        "--server.address", "127.0.0.1",
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    return subprocess.Popen(cmd, cwd=HERE, env=os.environ.copy())


def wait_until_up(port, proc, timeout=40.0):
    """Block until the server accepts connections, or the child dies/times out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False  # Streamlit exited before binding the port
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


def main():
    port = find_free_port()
    proc = start_streamlit(port)

    def _shutdown():
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    atexit.register(_shutdown)

    if not wait_until_up(port, proc):
        sys.stderr.write("Repertiores: Streamlit server failed to start.\n")
        _shutdown()
        sys.exit(1)

    # Smoke-test hook: confirm the server came up, then exit without opening the
    # native window (used by build verification; no effect in normal launches).
    if os.environ.get("REPERTIORES_SMOKE_TEST"):
        sys.stdout.write(f"SMOKE_OK port={port}\n")
        _shutdown()
        return

    import webview

    webview.create_window(
        "Repertiores",
        f"http://127.0.0.1:{port}",
        width=1380,
        height=900,
        min_size=(1000, 680),
    )
    # Force the Cocoa backend: pywebview's auto-detection can fail when the app
    # is launched from the .app bundle (start() then returns instantly without
    # showing a window). Naming it explicitly keeps the window up.
    try:
        webview.start(gui="cocoa")   # blocks until the window is closed
    except Exception:
        import traceback
        traceback.print_exc()        # surfaced in the launch log
    _shutdown()                      # then stop the Streamlit child


if __name__ == "__main__":
    main()
