import uiautomation as auto
import time
import sys
import os
import argparse
from datetime import datetime

# --- CONFIGURATION ---
TARGET_BUTTONS = ["Accept All", "Always Allow", "Allow this conversation", "Run", "Execute", "Apply", "Approve"]
SCAN_INTERVAL = 0.5  # Seconds
WINDOW_CLASS = "Chrome_WidgetWin_1" # Standard for Electron/VSCode forks

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [GUI-SENTRY] {message}")

def run_sentry(dry_run=False):
    log("Neural Forge GUI Sentry started.")
    log(f"Watching for buttons: {', '.join(TARGET_BUTTONS)}")
    if dry_run:
        log("DRY RUN MODE: Will not actually click.")

    while True:
        try:
            # 1. Find the Antigravity window
            # We search for the main Electron window class
            win = auto.WindowControl(searchDepth=1, ClassName=WINDOW_CLASS)
            
            if win.Exists(0):
                # 2. Find all buttons in the window
                # Note: deep search might be needed if buttons are nested in webviews
                for btn in win.ButtonControl(searchDepth=15).GetChildren():
                    name = btn.Name.strip()
                    
                    # 3. Match against our targets
                    is_match = any(target.lower() in name.lower() for target in TARGET_BUTTONS)
                    
                    if is_match and btn.IsEnabled:
                        log(f"Detected target button: '{name}'")
                        
                        if dry_run:
                            log(f"Found match: '{name}' (skipping click due to dry-run)")
                        else:
                            log(f"EXUTING AUTO-CLICK: '{name}'")
                            btn.Click(simulateMove=False)
                            # Wait briefly to avoid double-clicks
                            time.sleep(1)
            
        except Exception as e:
            # Silently handle transient errors (e.g. window closing)
            pass
            
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neural Forge GUI Sentry")
    parser.add_argument("--dry-run", action="store_true", help="Don't click, just log")
    args = parser.parse_args()
    
    try:
        run_sentry(dry_run=args.dry_run)
    except KeyboardInterrupt:
        log("Sentry stopped by user.")
        sys.exit(0)
