"""
Neural Forge — End-to-End Pipeline Test
Triggers a real pipeline via the orchestrator and monitors the full lifecycle.
"""
import requests
import time
import json

SERVER = "http://localhost:8001"

def main():
    print("=" * 60)
    print("  NEURAL FORGE — END-TO-END PIPELINE TEST")
    print("=" * 60)
    
    # Step 1: Verify services
    print("\n[1/5] Verifying services...")
    try:
        nodes = requests.get(f"{SERVER}/api/nodes?all=true", timeout=3).json()
        print(f"  [OK] Backend online. Nodes registered: {len(nodes)}")
        if not nodes:
            print("  [FAIL] No nodes registered! Agent not connected.")
            return
        
        node = nodes[0]
        print(f"  [OK] Agent: {node['desktop_name']} (ID: {node['node_id'][:8]}...)")
        print(f"  [OK] Roles: {node.get('assigned_roles', [])}")
    except Exception as e:
        print(f"  [FAIL] Backend not reachable: {e}")
        return

    # Step 2: Verify Bridge
    print("\n[2/5] Verifying Nexus Bridge...")
    try:
        health = requests.get("http://localhost:8000/health", timeout=3).json()
        print(f"  [OK] Bridge online. Ollama status: {health.get('status')}")
        print(f"  [OK] Loaded models: {health.get('loaded_models', [])}")
    except Exception as e:
        print(f"  [FAIL] Bridge not reachable: {e}")
        return
    
    # Step 3: Trigger the FULL pipeline
    goal = "Build a simple Python CLI calculator app with add, subtract, multiply, divide functions"
    print(f"\n[3/5] Triggering pipeline: '{goal}'")
    
    try:
        resp = requests.post(
            f"{SERVER}/api/orchestrator/pipeline/execute",
            json={"goal": goal},
            timeout=10
        )
        data = resp.json()
        print(f"  [OK] Pipeline triggered! Execution ID: {data.get('execution_id', 'N/A')[:8]}...")
        print(f"  [OK] Provider: {data.get('provider')}")
    except Exception as e:
        print(f"  [FAIL] Pipeline trigger failed: {e}")
        return
    
    # Step 4: Wait for tasks to appear in queue
    print("\n[4/5] Waiting for DAG tasks to be created...")
    time.sleep(5)  # Give orchestrator time to plan
    
    try:
        all_tasks = requests.get(f"{SERVER}/api/tasks", timeout=3).json()
        print(f"  [OK] Total tasks in system: {len(all_tasks)}")
        for t in all_tasks:
            dep = t.get('depends_on', 'none')
            dep_str = f" (depends: {dep[:8]}...)" if dep else ""
            print(f"      [{t['status']:>10}] {t['task_type']:>10} | {t['title'][:50]}{dep_str}")
    except Exception as e:
        print(f"  [WARN] Could not fetch tasks: {e}")
    
    # Step 5: Monitor execution
    print("\n[5/5] Monitoring task execution (120s max)...")
    start = time.time()
    last_states = {}
    
    while time.time() - start < 120:
        try:
            all_tasks = requests.get(f"{SERVER}/api/tasks", timeout=3).json()
            
            for t in all_tasks:
                tid = t['task_id']
                status = t['status']
                
                if last_states.get(tid) != status:
                    elapsed = int(time.time() - start)
                    print(f"  [{elapsed:3d}s] {t['task_type']:>10} | {status:>10} | {t['title'][:50]}")
                    last_states[tid] = status
                    
                    # Print logs if task has them
                    if status in ("completed", "failed"):
                        try:
                            logs = requests.get(f"{SERVER}/api/tasks/{tid}/logs", timeout=3).json()
                            if logs:
                                print(f"        Last 3 logs:")
                                for log in logs[-3:]:
                                    print(f"          [{log.get('level', '?')}] {log.get('message', '')[:80]}")
                        except:
                            pass
            
            # Check if all done
            statuses = [t['status'] for t in all_tasks]
            if all_tasks and all(s in ('completed', 'failed') for s in statuses):
                print(f"\n  [DONE] All {len(all_tasks)} tasks finished!")
                break
                
        except Exception as e:
            print(f"  [WARN] Monitor error: {e}")
        
        time.sleep(3)
    
    # Final summary
    print("\n" + "=" * 60)
    print("  FINAL STATUS")
    print("=" * 60)
    try:
        all_tasks = requests.get(f"{SERVER}/api/tasks", timeout=3).json()
        completed = sum(1 for t in all_tasks if t['status'] == 'completed')
        failed = sum(1 for t in all_tasks if t['status'] == 'failed')
        queued = sum(1 for t in all_tasks if t['status'] in ('queued', 'assigned'))
        print(f"  Completed: {completed} | Failed: {failed} | Pending: {queued}")
        print(f"  Total: {len(all_tasks)} tasks in DAG")
    except:
        pass

if __name__ == "__main__":
    main()
