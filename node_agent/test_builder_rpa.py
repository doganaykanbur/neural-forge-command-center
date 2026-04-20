import os
import sys
import shutil
import tempfile
import time
from pathlib import Path

# Fix encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# --- Configuration ---
NODE_AGENT_DIR = Path(__file__).parent.absolute()
BUILDER_SCRIPT = NODE_AGENT_DIR / "roles" / "builder.py"
IDE_PATH = r"C:\Users\doganay\AppData\Local\Programs\antigravity\Antigravity.exe"

def setup_mock_workspace(work_dir):
    """Create AGENTS.md and requirements.txt in work_dir."""
    agents_md = work_dir / "AGENTS.md"
    content = """# Neural Forge Architecture Blueprint
## Tech Stack
Python 3.11, Tkinter
## Dependencies
- tkinter
## Atomic Execution Plan
### Task 1: Minecraft Calculator
Build a Minecraft-themed graphical calculator with blocky design.
"""
    agents_md.write_text(content, encoding="utf-8")
    
def run_builder_simulation():
    # 1. CLEANUP PREVIOUS INSTANCES
    print("[*] Performing Deep Clean: Terminating existing Antigravity instances...")
    try:
        import subprocess
        subprocess.run(["taskkill", "/F", "/IM", "Antigravity.exe"], capture_output=True)
        time.sleep(2)
    except:
        pass

    # 2. Create a fresh temp directory
    base_tmp = Path(os.environ.get("LOCALAPPDATA", "C:\\Temp")) / "nf_builder_test_v6"
    if base_tmp.exists():
        try:
            shutil.rmtree(base_tmp, ignore_errors=True)
        except:
            pass
    base_tmp.mkdir(parents=True, exist_ok=True)
    
    setup_mock_workspace(base_tmp)
    
    # 3. Prepare Environment
    env = {
        **os.environ,
        "TASK_ID": "test-builder-rpa-v6",
        "TASK_TITLE": "Minecraft Calculator (Deep Clean Synthesis)",
        "TASK_DESCRIPTION": "Build a Minecraft themed graphical calculator using Python and Tkinter with blocky UI colors.",
        "WORK_DIR": str(base_tmp),
        "ARTIFACT_DIR": str(base_tmp),
        "ANTIGRAVITY_IDE_PATH": IDE_PATH,
        "SERVER_URL": "http://localhost:8000"
    }

    print("=" * 60)
    print(" STARTING BUILDER RPA TEST (Deep Clean / Port 9005) ")
    print("=" * 60)
    print(f"  Role   : Builder")
    print(f"  IDE    : {IDE_PATH}")
    print(f"  WorkDir: {base_tmp}")
    
    # Run Role
    try:
        import subprocess
        subprocess_cmd = [sys.executable, str(BUILDER_SCRIPT)]
        process = subprocess.run(
            subprocess_cmd, 
            env=env, 
            cwd=str(base_tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        print("--- BUILDER STDOUT ---")
        print(process.stdout)
        print("--- BUILDER STDERR ---")
        print(process.stderr)
        
        # Verify result
        app_py = base_tmp / "app.py"
        if app_py.exists():
            print("\n TEST SUCCESS: app.py generated!")
        else:
            py_files = list(base_tmp.glob("*.py"))
            print(f"\n Test finished. Found files: {[f.name for f in py_files]}")
                
    except Exception as e:
        print(f"  [!] Simulation Error: {e}")

if __name__ == "__main__":
    run_builder_simulation()
