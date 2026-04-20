import json
import os
import threading
import time
import platform
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Native UI Automation
try:
    from pywinauto import Desktop, Application
except ImportError:
    pass

# Config
PORT = 9888
# Using a file as a state bridge between the Node Agent and the Browser Driver
STATE_FILE = Path(os.environ.get("TEMP", ".")) / "nf_autopilot_state.json"

class AutopilotBridge(BaseHTTPRequestHandler):
    """
    Headless bridge between Neural Forge Admin Panel and Antigravity UI.
    """
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        """
        Poll for pending UI actions.
        Used by the autopilot_driver.js running in the browser.
        """
        if self.path == "/status":
            self._set_headers()
            if STATE_FILE.exists():
                try:
                    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    self.wfile.write(json.dumps(state).encode())
                    # Consumption logic: if an action is polled, we clear it after a short delay
                    # or the Node Agent clears it. For now, we just report.
                    return
                except Exception:
                    pass
            self.wfile.write(json.dumps({"action": "none"}).encode())
        else:
            self._set_headers(404)

    def do_POST(self):
        """
        Authorize and click buttons in the Antigravity App.
        Called by the Node Agent during tasks.
        """
        if self.path == "/authorize":
            length = int(self.headers.get('content-length'))
            data = json.loads(self.rfile.read(length))
            action = data.get("action", "click_accept")
            
            # Execute Native Click
            success = self._click_native(action)
            
            self._set_headers()
            self.wfile.write(json.dumps({"success": success}).encode())
        else:
            self._set_headers(404)

    def _click_native(self, action: str) -> bool:
        """Find Antigravity window and click buttons."""
        if platform.system() != "Windows":
            return False
            
        try:
            print(f"[Autopilot] Attempting native click: {action}")
            # 1. Broadly find Antigravity windows
            desks = Desktop(backend="uia").windows()
            antigravity_win = None
            for w in desks:
                if "antigravity" in w.window_text().lower():
                    antigravity_win = w
                    break
            
            if not antigravity_win:
                print("[Autopilot] Could not find Antigravity window.")
                return False

            # Translate action to button names
            # 'click_all' will cycle through major interactions
            button_targets = []
            if action == "click_accept": button_targets = ["Accept"]
            elif action == "click_run": button_targets = ["Run"]
            elif action == "click_all": button_targets = ["Accept", "Run", "Deploy"]

            found_any = False
            for target in button_targets:
                try:
                    # Find and click
                    btn = antigravity_win.child_window(title_re=f".*{target}.*", control_type="Button")
                    if btn.exists():
                        print(f"[Autopilot] Found button '{target}', clicking...")
                        btn.click_input()
                        found_any = True
                except Exception:
                    pass
            
            return found_any
        except Exception as e:
            print(f"[Autopilot] Native click error: {e}")
            return False

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), AutopilotBridge)
    print(f"[Autopilot Bridge] Listening on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
