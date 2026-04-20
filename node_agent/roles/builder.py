"""
Neural Forge — Autonomous Builder Role (Phase 4)
Uses the official Claude CLI + wexpect to build projects autonomously.
"""

# --- Windows Encoding Fix ---
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
# ----------------------------

import wexpect
import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime

# Configuration from Environment
TASK_ID = os.environ.get("TASK_ID", "unknown")
TITLE = os.environ.get("TASK_TITLE", "Unknown Build Task")
DESCRIPTION = os.environ.get("TASK_DESCRIPTION", "")
ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "."))
WORK_DIR = Path(os.environ.get("WORK_DIR", "."))
# Connect to our local bridge
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")
BRIDGE_URL = os.environ.get("ANTHROPIC_BASE_URL", f"{SERVER_URL}/v1")

def generate_instructions():
    """Create a CLAUDE_INSTRUCTIONS.md for the CLI tool to read."""
    instructions_path = WORK_DIR / "CLAUDE_INSTRUCTIONS.md"
    content = (
        f"# Neural Forge Build Instructions\n"
        f"**Task ID:** {TASK_ID}\n"
        f"**Objective:** {TITLE}\n\n"
        f"## Requirement Description:\n"
        f"{DESCRIPTION}\n\n"
        f"## Rules:\n"
        f"1. Stay within the current directory.\n"
        f"2. Build the project completely (code, tests, docs).\n"
        f"3. Do not ask for permissions, complete the goal autonomously.\n"
    )
    instructions_path.write_text(content, encoding="utf-8")
    print(f"[INFO] Generated {instructions_path.name}")
    return instructions_path

def main():
    print(f"[INFO] Neural Forge Autonomous Builder started for task {TASK_ID}")
    start_time = time.time()
    
    # Pre-flight: Instructions
    generate_instructions()
    
    # ── STEP 1: Resolve Claude Path & Spawn ──
    import shutil
    claude_path = shutil.which("claude") or "claude"

    # Command construction
    cmd = (
        'READ TASK_PLAN.md for the step-by-step instructions. '
        'READ ARCHITECTURE.md for the project directory tree and tech stack. '
        'ADHERE STRICTLY to RULES.md for design constraints. '
        'Execute the entire plan autonomously starting with Step 1: Create the physical directory structure.'
    )
    
    # Extra protection: log to persistent artifact dir immediately
    diag_log = ARTIFACT_DIR / "builder_diagnostic.log"
    with open(diag_log, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] Resolving claude: {claude_path}\n")
        f.write(f"[{datetime.now().isoformat()}] Command: {cmd}\n")

    print(f"[INFO] Spawning Claude CLI ({claude_path}): {cmd}")
    # Note: on Windows, wexpect.spawn is used. 
    import wexpect
    try:
        child = wexpect.spawn(f'cmd.exe /c {claude_path} -p "{cmd}"', 
                              timeout=300, cwd=str(WORK_DIR.absolute()))
        
        with open(diag_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] Spawn SUCCESS (PID: {getattr(child, 'pid', 'unknown')})\n")
        print(f"[ARTIFACT] builder_diagnostics|{diag_log}")
        
        # Patterns to monitor
        patterns = [
            r"Do you want to proceed\?", 
            r"\[y/n\]", 
            r"Create this file\?", 
            r"Modify this file\?",
            r"Allow\?",
            wexpect.EOF,
            wexpect.TIMEOUT
        ]

        while True:
            index = child.expect(patterns)
            
            # Extract and print output for streaming support
            # child.before contains text since last match
            output = child.before + (child.after if isinstance(child.after, str) else "")
            
            # Print to stdout so agent.py can capture it
            for line in output.splitlines():
                if line.strip():
                    print(line.strip())

            if index == len(patterns) - 2: # EOF (Finished)
                print("[INFO] Claude CLI finished successfully.")
                break
            
            if index == len(patterns) - 1: # TIMEOUT
                print("[ERROR] Claude CLI timed out during autonomous session.")
                break
            
            # Confirmation prompt detected
            print("[INFO] [NEXUS: AUTO-ACK] 'y' sent to CLI.")
            child.sendline('y')
            time.sleep(1) # Small pause for terminal sync

    except Exception as e:
        print(f"[ERROR] wexpect session failed: {e}")

    # ── STEP 2: No-Op and Artifact Verification ──
    duration = round(time.time() - start_time, 2)
    
    # Check for tangible work (Did any files change?)
    # For a build task, we expect at least one non-blueprint file (app.py, main.py, etc.)
    blueprints = {"TASK_PLAN.md", "ARCHITECTURE.md", "RULES.md", "CLAUDE_INSTRUCTIONS.md", "builder_diagnostic.log"}
    all_files = {f.name for f in WORK_DIR.iterdir() if f.is_file()}
    new_work = all_files - blueprints
    
    status = "completed"
    if not new_work and duration < 20: # 20 seconds is threshold for a real Claude session
        print(f"[ERROR] [BUILDER] No-Op Detect: No new files created after {duration}s. Failing task.")
        status = "failed"

    result_file = ARTIFACT_DIR / "result.json"
    result = {
        "task_id": TASK_ID,
        "status": status,
        "duration_s": duration,
        "mode": "autonomous-cli",
        "work_dir": str(WORK_DIR)
    }
    result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[ARTIFACT] build_result|{result_file}")
    
    # Optional: If app.py was created, register it as artifact
    app_file = WORK_DIR / "app.py"
    if app_file.exists():
        print(f"[ARTIFACT] built_app|{app_file}")

    print(f"[INFO] Builder finalized in {duration}s with status: {status}")

if __name__ == "__main__":
    main()
