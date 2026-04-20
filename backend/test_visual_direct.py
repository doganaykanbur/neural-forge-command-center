import requests
import json
import time
import os
import subprocess
import sys
from pathlib import Path

# Config
URL = "http://localhost:8000"
WORK_DIR = Path(os.getcwd()) / "visual_test_temp"
WORK_DIR.mkdir(exist_ok=True)

def run_direct_visual_test():
    print("==================================================")
    print("   NEURAL FORGE — DIRECT VISUAL TEST (NO WORKER)    ")
    print("==================================================")
    
    # 1. TRIGGER SYNTHESIS VIA BACKEND
    # Instead of creating a task, we call the synthesis endpoint directly
    # This simulates what the builder role would do.
    
    payload = {
        "goal": "Create a Minecraft themed hello script.",
        "blueprint": "Colors: stone:#555555, grass:#4DA227."
    }
    
    print("[*] Requesting synthesis from Antigravity Bridge...")
    print("[!] (Waiting for AI Assistant — me — to respond in the chat...)")
    
    try:
        # High timeout because I need to see and respond to the file
        resp = requests.post(f"{URL}/api/orchestrator/generate", json=payload, timeout=120)
        resp.raise_for_status()
        
        data = resp.json()
        code = data.get("code", "")
        
        if not code or code.startswith("[Error"):
            print(f"\n[❌] Synthesis failed: {code}")
            return

        # 2. SAVE THE RESULT
        test_file = WORK_DIR / "visual_hello.py"
        test_file.write_text(code, encoding="utf-8")
        print(f"\n[SUCCESS] Synthesis received! Code written to: {test_file.name}")
        
        # 3. OPEN THE WINDOW (THE VISUAL PART)
        print("\n[*] TRIGGERING VISUAL ACTIONS...")
        print(f"[*] Opening folder: {WORK_DIR}")
        
        if os.name == 'nt':
            # This is the command I added to the builder role
            subprocess.Popen(["start", ".", "/B"], shell=True, cwd=str(WORK_DIR))
            
            # Launch the script in a new window (This is the executor part)
            print("[*] Launching app in new window...")
            subprocess.Popen(["start", "cmd", "/c", sys.executable, str(test_file)], shell=True, cwd=str(WORK_DIR))
        else:
            subprocess.Popen(["open", "."], cwd=str(WORK_DIR))
            
        print("\n[🎉] TEST COMPLETE! Did a folder and a black terminal window open?")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    run_direct_visual_test()
