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
from pathlib import Path

def main():
    task_title = os.environ.get("TASK_TITLE", "Unknown Pipeline Task")
    task_desc = os.environ.get("TASK_DESCRIPTION", "")
    work_dir = Path(os.environ.get("WORK_DIR", "."))
    artifact_dir = Path(os.environ.get("ARTIFACT_DIR", "."))

    print(f"[INFO] Pipeline role starting for task: {task_title}")
    print(f"[INFO] Goal: {task_desc}")

    # A generic pipeline task typically sets up the environment or summarizes the plan.
    # We will simply log the start of the execution sequence.
    
    summary = f"""# Execution Log: {task_title}
Task Description: {task_desc}
Status: In Progress
Time: {os.environ.get("TASK_ID", "unknown")}
"""
    
    execution_log = work_dir / "execution_log.md"
    try:
        execution_log.write_text(summary, encoding="utf-8")
        print(f"[INFO] Execution log initialized at {execution_log}")
    except Exception as e:
        print(f"[ERROR] Failed to write log: {e}")
        return 1

    # Save a success result
    result = {
        "status": "completed",
        "output": f"Task '{task_title}' started. Progress recorded in execution_log.md",
        "log_file": str(execution_log)
    }
    
    res_file = artifact_dir / "result.json"
    res_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[ARTIFACT] execution_log|result.json")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
