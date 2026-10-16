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

def main():
    port = int(os.getenv("PORT", 8000))
    server_url = f"http://127.0.0.1:{port}"

    # 1. Start server in a background daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. Ensure server is online
    if not wait_for_server(server_url):
        print(f"Error: Server failed to start at {server_url}", file=sys.stderr)
        sys.exit(1)

    print(f"Ultron Core running at {server_url}. Launching native desktop window...")

    # 3. Create native standalone desktop window via pywebview with WebKitGTK media permissions
    import webview
    
    # Patch WebKitGTK backend to automatically grant microphone & camera permissions
    try:
        from webview.platforms import gtk as webview_gtk
        _orig_browser_view_init = webview_gtk.BrowserView.__init__

        def _patched_browser_view_init(self, window):
            _orig_browser_view_init(self, window)
            try:
                settings = self.webview.get_settings()
                settings.set_enable_media_stream(True)
                settings.set_enable_mediasource(True)
                settings.set_enable_webaudio(True)
                settings.set_enable_webrtc(True)
                settings.set_media_playback_requires_user_gesture(False)
            except Exception as e:
                print(f"[WebKit Settings Info]: {e}")

            def on_permission_request(web_view, request):
                try:
                    # Automatically grant microphone, camera, and device access
                    request.allow()
                    return True
                except Exception as e:
                    print(f"[Permission Grant Error]: {e}")
                    return False

            self.webview.connect("permission-request", on_permission_request)

        webview_gtk.BrowserView.__init__ = _patched_browser_view_init
    except Exception as ex:
        print(f"[WebKitGTK Permission Hook Info]: {ex}")

    # Configure pywebview window
    window = webview.create_window(
        title="ULTRON // Synthetic Command Matrix",
        url=server_url,
        width=1320,
        height=840,
        min_size=(980, 650),
        background_color="#050507",
        text_select=False,
    )

    # Start native GUI loop
    webview.start(gui="gtk", debug=False)

if __name__ == "__main__":
    main()
