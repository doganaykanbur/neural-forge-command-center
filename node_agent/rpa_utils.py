import subprocess
import time
import os
import sys
import re
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    # Handle environment where playwright is not yet installed
    sync_playwright = None

class AntigravityPlaywrightController:
    """
    CDP-based Automation Controller for Antigravity (Electron IDE).
    Uses Playwright to connect over Chrome DevTools Protocol.
    """

    def __init__(self, exe_path: str, workspace_path: str, debugging_port: int = 9005):
        self.exe_path = Path(exe_path)
        self.workspace_path = Path(workspace_path)
        self.debugging_port = debugging_port
        self.browser = None
        self.context = None
        self.page = None
        self.playwright_instance = None

    def _is_port_open(self, port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def launch_ide(self):
        """Launch Antigravity with Remote Debugging enabled."""
        try:
            print(f"[RPA] Launching Antigravity IDE on port {self.debugging_port}...")
            cmd = [
                str(self.exe_path),
                str(self.workspace_path),
                f"--remote-debugging-port={self.debugging_port}"
            ]
            subprocess.Popen(cmd)
            
            # Wait for port to open instead of fixed sleep
            print(f"[RPA] Waiting for port {self.debugging_port} to become active...")
            start_time = time.time()
            timeout = 20 # 20 seconds for launch
            while time.time() - start_time < timeout:
                if self._is_port_open(self.debugging_port):
                    print(f"[RPA] Port {self.debugging_port} is OPEN.")
                    time.sleep(2) # Final buffer for Electron to bind CDP
                    return True
                time.sleep(1)
            
            print(f"[RPA] Timeout waiting for port {self.debugging_port}")
            return False
        except Exception as e:
            print(f"[RPA] Target launch failed: {e}")
            return False

    def connect_cdp(self):
        """Connect Playwright to the running Electron app via CDP."""
        if not sync_playwright:
             print("[RPA] Error: Playwright not installed.")
             return False
             
        try:
            print(f"[RPA] Connecting to CDP: http://127.0.0.1:{self.debugging_port}")
            self.playwright_instance = sync_playwright().start()
            
            # Retry loop for CDP connection
            max_retries = 10
            connected = False
            for attempt in range(max_retries):
                try:
                    self.browser = self.playwright_instance.chromium.connect_over_cdp(f"http://127.0.0.1:{self.debugging_port}")
                    connected = True
                    break
                except Exception as e:
                    print(f"[RPA] CDP connection attempt {attempt+1} failed ({str(e)[:50]}). Retrying in 3s...")
                    time.sleep(3)
                    
            if not connected:
                print("[RPA] CDP Connection failed completely.")
                return False
            
            # Find the MOST RELEVANT page (the editor/chat window)
            timeout = 20
            start_time = time.time()
            while time.time() - start_time < timeout:
                for context in self.browser.contexts:
                    for page in context.pages:
                        try:
                            title = page.title().lower()
                            print(f"[RPA] Candidate Page: '{page.title()}'")
                            # Look for Antigravity or Architect related titles
                            if "antigravity" in title or "untitled" in title or "workspace" in title:
                                self.page = page
                                self.context = context
                                print(f"[RPA] Hooked into relevant page: {page.title()}")
                                # Ensure it's ready
                                self.page.wait_for_load_state("domcontentloaded")
                                return True
                        except:
                            continue
                time.sleep(2)
            
            # Fallback to absolute first page if nothing found but we have pages
            print("[RPA] Specific page title not found. Attempting fallback to first visible page...")
            for context in self.browser.contexts:
                for page in context.pages:
                    if page.url.startswith("http") or page.url.startswith("file"):
                         self.page = page
                         self.context = context
                         print(f"[RPA] Fallback success: Hooked into {page.title()} ({page.url})")
                         return True

            return False
        except Exception as e:
            print(f"[RPA] CDP Connection failed: {e}")
            return False

    def autonomous_synthesis(self, prompt_text: str):
        """Perform the full Inject -> Accept -> Run cycle using Semantic Locators."""
        if not self.page:
            print("[RPA] ERROR: Page not connected.")
            return False

        try:
            # 1. Karanlığı Aydınlat (DOM Dump Hack)
            print(f"[RPA] Dumping DOM to antigravity_debug_dom.html for selector discovery...")
            html_content = self.page.content()
            debug_dom_path = self.workspace_path / "antigravity_debug_dom.html"
            debug_dom_path.write_text(html_content, encoding="utf-8")
            print(f"[+] DOM mapped to: {debug_dom_path}")
            
            # Additional debug artifacts
            try:
                self.page.screenshot(path=str(self.workspace_path / "antigravity_debug_view.png"))
            except:
                pass
            
            # 2. Görsel Seçicilerden Vazgeç, Semantik (Text/Role) Seçicilere Geç
            print(f"[RPA] DEBUG: Prompt Injection Phase. Port: {self.debugging_port}")
            if os.environ.get("NF_DEBUG_RPA") == "true":
                print("[RPA] DEBUG: page.pause() triggered. Please inspect the UI via Playwright Inspector.")
                self.page.pause()

            print(f"[RPA] Locating input area (Semantic Search)...")
            # Try role-based first (AI Chat usually is a textbox or textarea)
            prompt_input = self.page.get_by_role("textbox").first
            if not prompt_input.is_visible(timeout=3000):
                 print("[RPA] get_by_role('textbox') not found. Trying generic 'textarea' locator...")
                 prompt_input = self.page.locator("textarea").first
            
            prompt_input.wait_for(state="visible", timeout=10000)
            
            # Precise injection using click + keyboard.type (Electron friendly)
            print(f"[RPA] Injecting prompt via keyboard emulation...")
            prompt_input.click() 
            time.sleep(0.5)
            self.page.keyboard.type(prompt_text, delay=10) # Human-like typing
            time.sleep(1)
            self.page.keyboard.press("Enter") 
            print("[+] Prompt submitted.")

            # 3. Wait and Click 'Accept' / 'Run' using Text-based Regex
            print("[RPA] Waiting for AI synthesis & Accept/Apply button...")
            
            # Using Regex to find buttons with "Accept" or "Run" text, ignoring case
            # This is more robust than CSS selectors if IDs are obfuscated
            button_regex = re.compile("Accept|Apply|Use|Run|Execute", re.IGNORECASE)
            
            try:
                # Wait for any button that matches our synthesis-complete labels
                accept_btn = self.page.get_by_role("button", name=button_regex).first
                accept_btn.wait_for(state="visible", timeout=60000) # Long timeout for LLM generation
                
                print(f"[RPA] Found Button: '{accept_btn.inner_text().strip()}'. Clicking (Force=True)...")
                accept_btn.click(force=True)
                print("[+] Action button clicked.")
                
                # If there's a multi-step process (Accept -> Run), try one more time
                time.sleep(3)
                run_btn = self.page.get_by_role("button", name=re.compile("Run|Execute", re.IGNORECASE)).first
                if run_btn.is_visible(timeout=5000):
                    print(f"[RPA] Found subsequent 'Run' button. Finalizing...")
                    run_btn.click(force=True)
                    print("[+] Final execution triggered.")
                
                return True
                
            except Exception as e:
                print(f"[ERROR] Button interaction failed or timed out: {e}")
                # Last ditch: Save another DOM dump to see why it failed
                self.workspace_path.joinpath("rpa_timeout_dump.html").write_text(self.page.content(), encoding="utf-8")
                return False

        except Exception as e:
            print(f"[RPA] Automation cycle failed: {e}")
            return False

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright_instance:
            self.playwright_instance.stop()
