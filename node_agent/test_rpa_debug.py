import time
from pathlib import Path
from rpa_utils import AntigravityPlaywrightController

def debug_rpa():
    # Attempt to connect to an ALREADY RUNNING Antigravity on port 9004
    print("[DEBUG] Attempting to connect to running IDE on port 9004...")
    controller = AntigravityPlaywrightController("dummy.exe", ".", debugging_port=9004)
    
    if not controller.connect_cdp():
        print("[ERROR] Could not connect to CDP. Is Antigravity running with --remote-debugging-port=9004?")
        return

    try:
        page = controller.page
        print(f"[DEBUG] Connected! Page Title: {page.title()}")
        
        # 1. Check for Input
        selectors = ['#prompt-input', '.ai-chat-input', 'textarea', '[placeholder*="Ask"]']
        found_input = False
        for sel in selectors:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                print(f"[DEBUG] Found AI Input via: {sel}")
                found_input = True
                break
        
        if not found_input:
            print("[DEBUG] AI Input NOT found.")

        # 2. Check for Accept/Run buttons (if they're visible)
        print("[DEBUG] Searching for buttons...")
        buttons = page.locator("button").all()
        for i, btn in enumerate(buttons):
            try:
                text = btn.inner_text().strip()
                if text:
                    print(f"  - Button {i}: '{text}'")
            except:
                continue

    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")
    finally:
        controller.close()

if __name__ == "__main__":
    debug_rpa()
