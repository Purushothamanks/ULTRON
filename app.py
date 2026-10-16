#!/usr/bin/env python3
"""
ULTRON // Native Synthetic Command Matrix
Standalone native desktop application powered by pywebview & FastAPI.
"""

import os
import sys
import time
import threading
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def run_server():
    """Runs the FastAPI server in background."""
    import uvicorn
    from server import app
    port = int(os.getenv("PORT", 8000))
    host = "127.0.0.1"
    uvicorn.run(app, host=host, port=port, log_level="warning")

def wait_for_server(url: str, timeout: int = 15):
    """Waits until the backend server is accepting HTTP connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/status", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False

def is_server_online(url: str) -> bool:
    """Checks if server is already running."""
    try:
        with urllib.request.urlopen(f"{url}/api/status", timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False

def main():
    port = int(os.getenv("PORT", 8000))
    server_url = f"http://127.0.0.1:{port}"

    # 1. Start server in a background daemon thread only if not already online
    if not is_server_online(server_url):
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # 2. Ensure server is online
        if not wait_for_server(server_url):
            print(f"Error: Server failed to start at {server_url}", file=sys.stderr)
            sys.exit(1)

    print(f"Ultron Core running at {server_url}. Launching native desktop window...")

    # 3. Create native standalone desktop window via direct GTK3 & WebKit2
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk, WebKit2, Gdk

    Gtk.init_check(None)

    win = Gtk.Window(title="ULTRON // Synthetic Command Matrix")
    win.set_default_size(1320, 840)
    win.set_size_request(980, 650)
    win.set_position(Gtk.WindowPosition.CENTER)

    # Apply dark theme styling
    try:
        css = b"window { background-color: #050507; }"
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    except Exception:
        pass

    webview = WebKit2.WebView()

    s = webview.get_settings()
    s.set_enable_media_stream(True)
    s.set_enable_mediasource(True)
    s.set_enable_webaudio(True)
    s.set_enable_webrtc(True)
    s.set_media_playback_requires_user_gesture(False)
    s.set_enable_write_console_messages_to_stdout(True)

    def on_permission_request(web_view, request):
        # Straight permanent hardware permission grant for microphone & camera
        print(f"[ULTRON HARDWARE PERMISSION]: Auto-granted access for {request}")
        try:
            request.allow()
            return True
        except Exception as ex:
            print(f"[ULTRON PERMISSION ERROR]: {ex}")
            return False

    webview.connect("permission-request", on_permission_request)

    win.add(webview)
    win.connect("destroy", Gtk.main_quit)

    win.show_all()
    webview.load_uri(server_url)

    # Start native Gtk event loop
    Gtk.main()

if __name__ == "__main__":
    main()
