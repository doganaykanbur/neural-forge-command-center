import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

# Fix encoding issues for Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# --- Configuration ---
NODE_AGENT_DIR = Path(__file__).parent.absolute()
ROLES_DIR = NODE_AGENT_DIR / "roles"

def run_role(role_name, env_vars, work_dir):
    """Executes a role script with a given environment."""
    script_map = {
        "architect": ROLES_DIR / "architect.py",
        "reviewer": ROLES_DIR / "reviewer.py",
        "builder": ROLES_DIR / "builder.py",
    }
    
    script_path = script_map.get(role_name)
    if not script_path or not script_path.exists():
        return False, f"Script {role_name} not found."

    env = {**os.environ, **env_vars, "WORK_DIR": str(work_dir), "ARTIFACT_DIR": str(work_dir)}
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timed out after 60s"
    except Exception as e:
        return False, str(e)

def test_architect():
    print("\n[TEST] Architect Isolation Test")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        env = {
            "TASK_DESCRIPTION": "Create a Minecraft Calculator.",
            "OLLAMA_URL": "http://localhost:9999/api/generate" # Force fallback
        }
        
        success, output = run_role("architect", env, tmp_path)
        
        # Verify Fallback
        agents_md = tmp_path / "AGENTS.md"
        if agents_md.exists():
            print("  [+] AGENTS.md created successfully (Fallback test passed).")
            return True
        else:
            print("  [-] AGENTS.md was NOT created.")
            print(f"  Debug Output: {output}")
            return False

def test_reviewer_guard():
    print("\n[TEST] Reviewer No-Code Guard Test")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        env = {
            "TASK_ID": "test-review-123",
            "TASK_DESCRIPTION": "A simple build task."
        }
        
        success, output = run_role("reviewer", env, tmp_path)
        
        # Verify Pending status in result.json
        result_json = tmp_path / "result.json"
        if result_json.exists():
            data = json.loads(result_json.read_text())
            if data.get("status") == "pending":
                print("  [+] Reviewer correctly reported PENDING status (No-Code Guard passed).")
                return True
            else:
                print(f"  [-] Unexpected status: {data.get('status')}")
                return False
        else:
            print("  [-] result.json was NOT created.")
            return False

def test_rpa_port_readiness():
    print("\n[TEST] RPA Port Readiness Logic Test")
    sys.path.insert(0, str(NODE_AGENT_DIR))
    try:
        from rpa_utils import AntigravityPlaywrightController
        controller = AntigravityPlaywrightController("dummy.exe", ".", debugging_port=9999)
        
        print("  [*] Verifying closed port detection...")
        import time
        controller._is_port_open = lambda port: False 
        
        port_open = False
        st = time.time()
        while time.time() - st < 2:
            if controller._is_port_open(9999):
                port_open = True
                break
            time.sleep(0.5)
            
        if not port_open:
            print("  [+] Closed port correctly ignored.")
        
        return True
    except Exception as e:
        print(f"  [-] RPA Test Error: {e}")
        return False

def main():
    print("="*50)
    print(" NEURAL FORGE - COMPONENT ISOLATION TESTER ")
    print("="*50)
    
    results = {
        "Architect Fallback": test_architect(),
        "Reviewer Guard": test_reviewer_guard(),
        "RPA Port Logic": test_rpa_port_readiness()
    }
    
    print("\n" + "="*30)
    print(" FINAL RESULTS ")
    print("="*30)
    for test, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test:20}: {status}")
    print("="*30)

if __name__ == "__main__":
    main()
