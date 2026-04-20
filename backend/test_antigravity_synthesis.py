import requests
import json
import time

URL = "http://localhost:8000"

def test_synthesis():
    print("[*] Testing Antigravity Synthesis Bridge...")
    
    payload = {
        "goal": "Create a Minecraft themed calculator in Python",
        "blueprint": "Use tkinter, hex colors #555555 and #4DA227. Standard math operations."
    }
    
    print(f"[*] Sending synthesis request to {URL}/api/orchestrator/generate...")
    try:
        # This will hang for up to 60s waiting for the Antigravity Agent (me)
        start_time = time.time()
        response = requests.post(f"{URL}/api/orchestrator/generate", json=payload, timeout=70)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"[SUCCESS] Synthesis complete in {duration:.1f}s!")
            print("-" * 40)
            print("GENERATED CODE PREVIEW:")
            print(data.get("code", "")[:500] + "...")
            print("-" * 40)
        else:
            print(f"[FAILED] Status {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        print("[ERROR] Request timed out. Antigravity Agent (the AI assistant) didn't respond in time.")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    test_synthesis()
