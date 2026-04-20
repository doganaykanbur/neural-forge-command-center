import requests
import json
import time
import os

URL = "http://localhost:8000"

def run_visual_build_test():
    print("==================================================")
    print("   NEURAL FORGE — VISUAL BUILD TEST SCRIPT         ")
    print("==================================================")
    
    # 1. CREATE A SINGLE BUILD TASK
    # We bypass the complex pipeline and create a 'build' task directly
    task_payload = {
        "title": "Visual Factory Test: Hello Minecraft",
        "description": "Create a python script hello.py that prints 'Visual Factory Active'. Use colors stone:#555555 and grass:#4DA227.",
        "task_type": "build",
        "priority": 5
    }
    
    print("[*] Creating direct BUILD task...")
    try:
        resp = requests.post(f"{URL}/api/tasks/create", json=task_payload)
        resp.raise_for_status()
        task = resp.json()["task"]
        task_id = task["task_id"]
        print(f"[SUCCESS] Task Created! ID: {task_id[:8]}")
        
        print("\n[*] INSTRUCTIONS FOR YOU:")
        print("1. Make sure 'python node_agent/agent.py' is running in another terminal.")
        print("2. I (the AI) will now see the synthesis request and provide the code.")
        print("3. Watch your desktop: A folder window should open automatically!")
        
        # 2. POLL FOR STATUS
        print("\n[*] Monitoring task status...")
        while True:
            t_resp = requests.get(f"{URL}/api/tasks/{task_id}")
            if t_resp.status_code == 200:
                t_data = t_resp.json()
                status = t_data["status"]
                print(f"    Current Status: [{status.upper()}]", end="\r")
                
                if status == "completed":
                    print(f"\n\n[🎉] TEST COMPLETE: Task marked as COMPLETED.")
                    print("[!] If no folder opened, check if 'agent.py' is running in NATIVE mode (No Docker).")
                    break
                elif status == "failed":
                    print(f"\n\n[❌] TEST FAILED: Check backend/worker logs.")
                    break
            
            time.sleep(3)
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    # Check if server is up
    try:
        requests.get(URL, timeout=2)
    except:
        print(f"[!] Backend is NOT running at {URL}. Please start 'python main.py' first.")
        exit(1)
        
    run_visual_build_test()
