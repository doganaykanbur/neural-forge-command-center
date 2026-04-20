import subprocess
import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

class AntigravityPlaywrightController:
    """
    CDP-based Automation Controller for Antigravity (Electron IDE).
    Uses Playwright to connect over Chrome DevTools Protocol.
    """

    def __init__(self, exe_path: str, workspace_path: str, debugging_port: int = 9004):
        self.exe_path = Path(exe_path)
        self.workspace_path = Path(workspace_path)
        self.debugging_port = debugging_port
        self.browser = None
        self.context = None
        self.page = None

    def launch_ide(self):
        """
        Launch Antigravity with Remote Debugging enabled.
        """
        try:
            print(f"[*] Launching Antigravity IDE on port {self.debugging_port}...")
            # Use --remote-debugging-port to unlock CDP access
            cmd = [
                str(self.exe_path),
                str(self.workspace_path),
                f"--remote-debugging-port={self.debugging_port}"
            ]
            subprocess.Popen(cmd)
            print("[+] Process started. Waiting for CDP to initialize...")
            time.sleep(5) # Delay for debugger startup
            return True
        except Exception as e:
            print(f"[!] Target launch failed: {e}")
            return False

    def connect_cdp(self):
        """
        Connect Playwright to the running Electron app via CDP.
        """
        try:
            print(f"[*] Connecting to CDP: http://localhost:{self.debugging_port}")
            self.playwright = sync_playwright().start()
            # Connect over existing debugger
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{self.debugging_port}")
            
            # Electron apps usually have one browser context and one main window
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0]
            
            # Wait for the main UI to be visible
            self.page.wait_for_load_state("networkidle")
            print(f"[+] Successfully hooked into Antigravity (Title: {self.page.title()})")
            return True
        except Exception as e:
            print(f"[!] CDP Connection failed: {e}. Check if port {self.debugging_port} is open.")
            return False

    def autonomous_synthesis(self, prompt_text: str):
        """
        Perform the full Inject -> Accept -> Run cycle.
        """
        if not self.page:
            print("[!] ERROR: No active page detected.")
            return False

        try:
            print(f"[*] Injecting Prompt: '{prompt_text[:30]}...'")
            
            # 1. FIND PROMPT INPUT (Placeholder Selectors)
            # You can find these IDs/Classes using Chrome DevTools (Ctrl+Shift+I in the app)
            prompt_input = self.page.locator('#prompt-input, .ai-chat-input, [placeholder*="Ask"]')
            prompt_input.wait_for(state="visible", timeout=10000)
            prompt_input.fill(prompt_text)
            print("[+] Prompt text filled.")

            # 2. CLICK 'ACCEPT' (Generic text-based locator)
            print("[*] Clicking 'Accept'...")
            accept_btn = self.page.get_by_role("button", name="Accept").or_(self.page.locator("button:has-text('Accept')"))
            accept_btn.click()
            print("[+] 'Accept' button clicked.")

            # 3. CLICK 'RUN'
            time.sleep(1) # Small buffer for UI transitions
            print("[*] Clicking 'Run'...")
            run_btn = self.page.get_by_role("button", name="Run").or_(self.page.locator("button:has-text('Run')"))
            run_btn.click()
            print("[+] 'Run' button clicked.")

            return True
        except Exception as e:
            print(f"[!] Automation cycle failed: {e}")
            return False

    def close(self):
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

# --- Execution Example ---
if __name__ == "__main__":
    # CONFIGURATION
    IDE_BINARY = r"C:\Users\doganay\AppData\Local\Programs\antigravity\Antigravity.exe"
    WORKSPACE_DIR = r"C:\Users\doganay\.gemini\antigravity\scratch\neural_forge_command_center"
    
    # 1. Initialize
    controller = AntigravityPlaywrightController(IDE_BINARY, WORKSPACE_DIR)
    
    try:
        # 2. Start & Connect
        if controller.launch_ide() and controller.connect_cdp():
            
            # 3. Run Synthesis Task
            test_prompt = "Build a Minecraft themed logic gate simulation in Python."
            controller.autonomous_synthesis(test_prompt)
            
            print("\n[🎉] Neural Forge Playwright RPA Cycle Finished.")
        else:
            print("\n[❌] Could not establish link with Antigravity.")
    finally:
        # Optional: controller.close() - Keep open if you want to see the results
        pass
