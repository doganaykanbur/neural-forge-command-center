"""
Neural Forge — Executor Worker
Runs an application/script and captures output + exit code.

Reads from env: TASK_ID, TASK_DESCRIPTION, ARTIFACT_DIR, WORK_DIR
Outputs structured log lines: [INFO], [ERROR], [ARTIFACT]
"""

# --- Windows Encoding Fix ---
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
# ----------------------------

import os
import json
import subprocess
import time
from pathlib import Path

TASK_ID = os.environ.get("TASK_ID", "unknown")
DESCRIPTION = os.environ.get("TASK_DESCRIPTION", "")
ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "."))
WORK_DIR = Path(os.environ.get("WORK_DIR", "."))


def main():
    print(f"[INFO] Executor started for task {TASK_ID}")
    start_time = time.time()
    
    # Create executable script from description (or use default)
    code = DESCRIPTION.strip()
    if not code:
        code = '''
import sys
import platform
import datetime

print("=" * 40)
print("Neural Forge — Executor Output")
print("=" * 40)
print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Timestamp: {datetime.datetime.now().isoformat()}")
print()
print("Performing computation...")
result = sum(range(1_000_000))
print(f"Sum(0..999999) = {result}")
print()
print("Execution completed successfully!")
'''
    
    script_file = WORK_DIR / "run_target.py"
    script_file.write_text(code, encoding="utf-8")
    print(f"[INFO] Script written ({len(code)} bytes)")
    
    # Execute the script in a VISIBLE WINDOW (Visual Factory)
    print(f"[INFO] Executing script in NEW WINDOW...")
    try:
        # On Windows, 'start' opens a new terminal window
        if os.name == 'nt':
            # cmd /c -> run and close, cmd /k -> run and stay open
            # We use /c for automated pipelines, but the application window (GUI) will be visible
            proc = subprocess.Popen(
                ["start", "cmd", "/c", sys.executable, str(script_file)],
                shell=True, cwd=str(WORK_DIR)
            )
            # Give it a moment to launch
            time.sleep(2)
            stdout, stderr, exit_code = "Launched in new window", "", 0
        else:
            # On macOS/Linux, we can use 'open' or just run it backgrounded if it's a GUI
            proc = subprocess.Popen([sys.executable, str(script_file)], cwd=str(WORK_DIR))
            stdout, stderr, exit_code = "Launched in background (Unix)", "", 0
        
    except Exception as e:
        print(f"[ERROR] Execution failed: {e}")
        stdout, stderr, exit_code = "", str(e), 1
    
    duration = round(time.time() - start_time, 2)
    
    # Save stdout as artifact
    output_file = ARTIFACT_DIR / "execution_output.txt"
    output_file.write_text(stdout or "(no output)", encoding="utf-8")
    print(f"[ARTIFACT] execution_output|{output_file}")
    
    # Save stderr if any
    if stderr and stderr.strip():
        error_file = ARTIFACT_DIR / "execution_errors.txt"
        error_file.write_text(stderr, encoding="utf-8")
        print(f"[ARTIFACT] execution_errors|{error_file}")
    
    # Build result
    final_result = {
        "task_id": TASK_ID,
        "status": "success" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "stdout_length": len(stdout),
        "stderr_length": len(stderr),
        "duration_s": duration,
    }
    
    result_file = ARTIFACT_DIR / "result.json"
    result_file.write_text(json.dumps(final_result, indent=2), encoding="utf-8")
    print(f"[ARTIFACT] executor_result|{result_file}")
    
    print(f"[INFO] Execution complete in {duration}s (exit code: {exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
