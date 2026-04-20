import requests
import json
import time
import uuid

URL = "http://localhost:8000"

def run_task_demo():
    print("==================================================")
    print("      NEURAL FORGE — FULL TASK CYCLE DEMO         ")
    print("==================================================")
    
    # 1. DEFINE PROJECT GOAL
    goal = "Create a hello_world.py script with Minecraft theme colors in the comments."
    print(f"[*] Goal: {goal}")
    
    # 2. TRIGGER PIPELINE EXECUTION
    # This creates a sequence of tasks (e.g., design -> build -> review)
    print("\n[STEP 1] Planning & Queuing Pipeline...")
    try:
        resp = requests.post(f"{URL}/api/orchestrator/pipeline/execute", json={"goal": goal})
        resp.raise_for_status()
        data = resp.json()
        pipeline_tasks = data.get("tasks", [])
        print(f"[SUCCESS] Created {len(pipeline_tasks)} tasks in the pipeline.")
        for t in pipeline_tasks:
            print(f"  - [{t['task_type'].upper()}] {t['title']} (ID: {t['task_id'][:8]})")
            
        # 3. MONITOR THE 'BUILD' TASK
        # We look for the 'build' type task to demonstrate synthesis
        build_task = next((t for t in pipeline_tasks if t['task_type'] == 'build'), None)
        if not build_task:
            print("[!] No 'build' task found in pipeline. Using the first task.")
            build_task = pipeline_tasks[0]
            
        print(f"\n[STEP 2] Simulating Synthesis for Task: {build_task['title']}")
        print(f"[*] Endpoint: {URL}/api/orchestrator/generate")
        
        # This is where the Antigravity Bridge will be triggered
        # The backend will write to ANTIGRAVITY_REQUEST.json and WAIT
        print("[*] Requesting synthesis... (Waiting for Antigravity Agent to respond)")
        
        gen_payload = {
            "goal": build_task['title'],
            "blueprint": "Minecraft theme colors: stone:#555555, grass:#4DA227."
        }
        
        start_time = time.time()
        # High timeout because I (the AI) need to see and respond to the file
        gen_resp = requests.post(f"{URL}/api/orchestrator/generate", json=gen_payload, timeout=75)
        
        if gen_resp.status_code == 200:
            gen_data = gen_resp.json()
            print(f"\n[SUCCESS] Synthesis received in {time.time() - start_time:.1f}s!")
            print("-" * 50)
            print("GENERATED CONTENT:")
            print(gen_data.get("code", "No code returned."))
            print("-" * 50)
            
            # 4. FINALIZE TASK (Optional callback to backend)
            print("\n[STEP 3] Finalizing Task Status...")
            complete_payload = {
                "status": "completed",
                "result": {"output": "Code synthesized successfully via Antigravity Bridge."}
            }
            requests.post(f"{URL}/api/tasks/{build_task['task_id']}/complete", json=complete_payload)
            print(f"[DONE] Task {build_task['task_id'][:8]} marked as COMPLETED.")
            
        else:
            print(f"[FAILED] Synthesis failed with status {gen_resp.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Demo failed: {e}")

if __name__ == "__main__":
    run_task_demo()
