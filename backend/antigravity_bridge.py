import os
import time
import subprocess
from pathlib import Path
from pywinauto import Application, Desktop
from pywinauto.timings import TimeoutError as PyWinTimeoutError

class AntigravityController:
    """
    RPA Controller for Antigravity IDE using Windows UIAutomation (UIA).
    Designed for background/autonomous execution without pixel matching.
    """
    
    def __init__(self, exe_path: str, workspace_path: str = None):
        self.exe_path = Path(exe_path)
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.app = None
        self.main_window = None
        
        # Selectors (Replaceable via Microsoft Inspect tool)
        self.selectors = {
            "window_title_re": ".*Antigravity.*",
            "prompt_box": {"title": "Prompt", "control_type": "Edit"},
            "accept_btn": {"title": "Accept", "control_type": "Button"},
            "run_btn": {"title": "Run", "control_type": "Button"}
        }

    def launch(self):
        """
        Launch the Antigravity IDE with the specified workspace.
        """
        try:
            print(f"[*] Launching Antigravity: {self.exe_path}")
            args = [str(self.exe_path)]
            if self.workspace_path:
                args.append(str(self.workspace_path))
            
            # Start process natively
            subprocess.Popen(args)
            
            # Wait for window to appear and connect
            return self.connect()
        except Exception as e:
            print(f"[!] Launch failed: {e}")
            return False

    def connect(self, timeout=20):
        """
        Hook into the already running Antigravity process.
        Using 'uia' backend for modern Electron/Desktop apps.
        """
        try:
            print("[*] Connecting to Antigravity window...")
            self.app = Application(backend="uia").connect(title_re=self.selectors["window_title_re"], timeout=timeout)
            self.main_window = self.app.window(title_re=self.selectors["window_title_re"])
            
            # Wait for window to be ready
            self.main_window.wait("ready", timeout=timeout)
            print("[+] Successfully hooked into Antigravity main window.")
            return True
        except PyWinTimeoutError:
            print("[!] Connection timeout: Window not found.")
            return False
        except Exception as e:
            print(f"[!] Hook failed: {e}")
            return False

    def inject_prompt(self, prompt_text: str):
        """
        Directly inject text into the prompt TextBox without keyboard simulation.
        """
        if not self.main_window:
            print("[!] ERROR: Not connected to any window.")
            return False
            
        try:
            print("[*] Injecting prompt text...")
            # Find the edit control
            prompt_box = self.main_window.child_window(**self.selectors["prompt_box"])
            
            if prompt_box.exists(timeout=5):
                # Set text directly (works even if backgrounded)
                prompt_box.set_text(prompt_text)
                print("[+] Prompt text injected.")
                return True
            else:
                print("[!] Could not find Prompt TextBox.")
                return False
        except Exception as e:
            print(f"[!] Injection failed: {e}")
            return False

    def click_action(self, action_type: str = "accept"):
        """
        Find and click 'Accept' or 'Run' buttons.
        """
        if not self.main_window:
            return False
            
        target = "accept_btn" if action_type == "accept" else "run_btn"
        try:
            print(f"[*] Attempting to click: {action_type.upper()}")
            btn = self.main_window.child_window(**self.selectors[target])
            
            if btn.exists(timeout=5):
                # Click event (native message, doesn't need mouse focus)
                btn.click()
                print(f"[+] Button '{action_type}' clicked.")
                return True
            else:
                print(f"[!] Button '{action_type}' not found.")
                return False
        except Exception as e:
            print(f"[!] Click failed: {e}")
            return False

    def autonomous_cycle(self, prompt: str):
        """
        High-level wrapper for a full automated cycle.
        """
        if not self.main_window and not self.connect(timeout=5):
            if not self.launch():
                return False
        
        # 1. Inject
        if self.inject_prompt(prompt):
            time.sleep(1) # Safety buffer
            # 2. Accept
            if self.click_action("accept"):
                time.sleep(2)
                # 3. Run
                return self.click_action("run")
        
        return False

# --- Example Usage ---
if __name__ == "__main__":
    # Settings
    IDE_PATH = r"C:\Path\To\Antigravity.exe" # User must provide actual path
    WORKSPACE = r"C:\Users\doganay\.gemini\antigravity\scratch\neural_forge_command_center"
    
    controller = AntigravityController(IDE_PATH, WORKSPACE)
    
    # Test Prompt
    test_prompt = "Create a hello.py that says Neural Forge RPA is Active."
    
    success = controller.autonomous_cycle(test_prompt)
    if success:
        print("\n[🎉] RPA Workflow Finished Successfully.")
    else:
        print("\n[❌] RPA Workflow Failed.")
