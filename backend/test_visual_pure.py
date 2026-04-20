import json
import time
import os
import subprocess
import sys
from pathlib import Path

# Config - Direct Bridge Path (No Backend Needed)
RULES_DIR = Path(os.getcwd()).parent / ".nexus" / "rules"
RULES_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_FILE = RULES_DIR / "ANTIGRAVITY_REQUEST.json"
RESPONSE_FILE = RULES_DIR / "ANTIGRAVITY_RESPONSE.json"
TEMP_WORK_DIR = Path(os.getcwd()) / "pure_visual_test"
TEMP_WORK_DIR.mkdir(exist_ok=True)

def run_pure_visual_test():
    print("==================================================")
    print("   NEURAL FORGE — PURE VISUAL TEST (NO BACKEND)   ")
    print("==================================================")
    
    # 1. CLEAN UP PREVIOUS
    if REQUEST_FILE.exists(): REQUEST_FILE.unlink()
    if RESPONSE_FILE.exists(): RESPONSE_FILE.unlink()
    
    # 2. WRITE REQUEST DIRECTLY TO BRIDGE
    payload = {
        "task_id": "pure-test-" + str(int(time.time())),
        "prompt": "Create a Minecraft themed python script 'pure_hello.py' that prints 'Neural Forge Pure Test Successful'. Hex: stone:#555555, grass:#4DA227.",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    print(f"[*] Writing request to Bridge: {REQUEST_FILE.name}")
    REQUEST_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    
    print("\n[!] STANDBY: Waiting for AI Assistant (Antigravity) to write response...")
    print("[!] (I am watching the file now. I will provide code in the chat sidebar.)")
    
    # 3. POLL FOR RESPONSE
    start_time = time.time()
    code = None
    while time.time() - start_time < 120:
        if RESPONSE_FILE.exists():
            try:
                data = json.loads(RESPONSE_FILE.read_text(encoding="utf-8"))
                code = data.get("text", "")
                if code:
                    print(f"\n[SUCCESS] Response received in {time.time() - start_time:.1f}s!")
                    break
            except json.JSONDecodeError:
                pass
        print("    Waiting for ANTIGRAVITY_RESPONSE.json...", end="\r")
        time.sleep(2)
    
    if not code:
        print("\n[❌] Timeout: Antigravity did not respond in 120s.")
        return

    # 4. SAVE AND TRIGGER VISUAL ACTION
    test_file = TEMP_WORK_DIR / "pure_hello.py"
    test_file.write_text(code, encoding="utf-8")
    print(f"[*] Code saved to: {test_file}")
    
    print("\n[*] --- EXECUTING VISUAL ACTIONS ---")
    print(f"[*] Opening folder: {TEMP_WORK_DIR}")
    
    if os.name == 'nt':
        # Open folder
        subprocess.Popen(["start", ".", "/B"], shell=True, cwd=str(TEMP_WORK_DIR))
        # Launch app window
        print("[*] Launching app in new window...")
        subprocess.Popen(["start", "cmd", "/c", sys.executable, str(test_file)], shell=True, cwd=str(TEMP_WORK_DIR))
    else:
        subprocess.Popen(["open", "."], cwd=str(TEMP_WORK_DIR))
        
    print("\n[🎉] TEST COMPLETE! Folder and Console window should be visible.")

if __name__ == "__main__":
    run_pure_visual_test()
