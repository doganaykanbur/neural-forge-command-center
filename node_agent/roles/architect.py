"""
Neural Forge — Phase 4.1 Industrial Architect (v2.3)
Strategically designs projects using Mistral-Nemo via Nexus Bridge.
Features: Nexus Memory Injection, XML Fail-Safe Retry Loop, Scaffolding Delegation.
"""

import os
import json
import requests
import time
import re
import sys
from pathlib import Path
from datetime import datetime

# --- Neural Forge Environment Patching ---
# Ensure we can import from the backend module for Memory Injection
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "backend"))

try:
    from nexus import NexusMemory
except ImportError:
    # Fallback if isolation is too strict
    class NexusMemory:
        def __init__(self): pass
        def get_context(self, topic): return "No memory available."

# --- Windows Encoding Fix ---
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
# ----------------------------

class NeuralForgeArchitect:
    """
    Lead AI Architect for Neural Forge (v2.3).
    """

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        self.bridge_url = os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:8000/v1")
        if not self.bridge_url.endswith("/messages"):
             self.bridge_url = self.bridge_url.rstrip("/") + "/messages"
             
        self.task_id = os.environ.get("TASK_ID", "unknown")
        # Initialize Memory
        nexus_dir = PROJECT_ROOT / ".nexus" / "rules"
        self.memory = NexusMemory(nexus_dir=nexus_dir)

    def _get_injected_prompt(self, user_goal: str):
        """Fetch global preferences and past decisions to maintain design consistency."""
        context = self.memory.get_context("architect")
        
        system_prompt = (
            "ROLE: LEAD_SYSTEM_ARCHITECT\n"
            "You turn high-level goals into production-grade blueprints. Adhere strictly to the following formatting standards:\n\n"
            "--- SYSTEM MEMORY & PREFERENCES ---\n"
            f"{context}\n"
            "------------------------------------\n\n"
            "INSTRUCTIONS:\n"
            "1. Output exactly THREE distinct sections wrapped in these XML tags:\n"
            "   <task_plan> [TASK_PLAN.md content here] </task_plan>\n"
            "   <architecture> [ARCHITECTURE.md content here] </architecture>\n"
            "   <rules> [RULES.md content here] </rules>\n"
            "2. Within these tags, use EXCLUSIVELY Markdown (Headers, Lists, Code Blocks). DO NOT use internal XML-style tags for parameters.\n"
            "3. ARCHITECTURE.md REQUIREMENTS:\n"
            "   - Must include a 'Dependencies' list.\n"
            "   - Must include a 'Module Breakdown' section with descriptions.\n"
            "   - Must include a 'Data Flow' section explaining interactions.\n"
            "4. RULES.md REQUIREMENTS:\n"
            "   - Must define coding conventions and anti-patterns directly.\n"
            "5. NO conversational filler. NO generic placeholder Task IDs. This is for the Neural Forge Visible Factory."
        )
        return system_prompt

    def _call_bridge(self, system_prompt: str, user_content: str):
        """Strategic reasoning call via Nexus Bridge."""
        payload = {
            "model": "qwen2.5-coder:7b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 4096
        }
        
        try:
            print(f"[*] [ARCHITECT] Consulting Neural Forge Brain...")
            headers = {"x-api-key": "dummy-nexus-key", "Content-Type": "application/json"}
            response = requests.post(self.bridge_url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            print(f"[ERROR] [ARCHITECT] Bridge Error: {e}")
            return None

    def parse_blueprint(self, raw_output: str):
        """Split content by XML tags into separate documentation files."""
        tags = ["task_plan", "architecture", "rules"]
        file_map = {"task_plan": "TASK_PLAN.md", "architecture": "ARCHITECTURE.md", "rules": "RULES.md"}
        
        results = {}
        for tag in tags:
            pattern = rf"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, raw_output, re.DOTALL)
            if match:
                results[tag] = match.group(1).strip()
        
        return results

    def run(self, user_goal: str):
        """Full lifecycle with 3-Try XML Fail-Safe."""
        print(f"\n[PHASE: ARCHITECT] Production Line Ignition for: \"{user_goal}\"")
        
        system_prompt = self._get_injected_prompt(user_goal)
        current_user_content = f"Architect the following project: {user_goal}"
        
        # ─── FAIL-SAFE RETRY LOOP ───
        for attempt in range(1, 4):
            print(f"[*] [ARCHITECT] Synthesis Attempt {attempt}/3...")
            raw_design = self._call_bridge(system_prompt, current_user_content)
            
            if not raw_design:
                continue
                
            blueprint_parts = self.parse_blueprint(raw_design)
            missing_tags = [t for t in ["task_plan", "architecture", "rules"] if t not in blueprint_parts]
            
            if not missing_tags:
                # SUCCESS! Write files and exit loop
                print("[✔] [ARCHITECT] Valid blueprint received. Deploying files...")
                for tag, content in blueprint_parts.items():
                    filename = {"task_plan": "TASK_PLAN.md", "architecture": "ARCHITECTURE.md", "rules": "RULES.md"}[tag]
                    file_path = self.workspace / filename
                    file_path.write_text(content, encoding="utf-8")
                    print(f"[ARTIFACT] {tag}|{file_path}")
                
                # Final result registration (REFINED)
                res_path = self.workspace / "result.json"
                metadata = {
                    "source_goal": user_goal,
                    "blueprint_timestamp": datetime.now().isoformat(),
                    "artifacts_deployed": list(blueprint_parts.keys()),
                    "status": "ready_for_build",
                    "blueprint_version": "2.3-Industrial"
                }
                res_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                print(f"[ARTIFACT] architect_metadata|{res_path}")
                return True
            else:
                # FAIL-SAFE: Ask to repair specifically what is missing
                print(f"[!] [ARCHITECT] Missing tags: {missing_tags}. Requesting autonomous repair...")
                current_user_content = (
                    f"Your previous response was incomplete. You missed the following tags: {missing_tags}. "
                    "Please regenerate the ENTIRE blueprint including ALL three tags: <task_plan>, <architecture>, and <rules>."
                )
                time.sleep(1) # Cool down
        
        print("[ERROR] [ARCHITECT] Failed to generate valid blueprint after 3 attempts.")
        return False

if __name__ == "__main__":
    WORKSPACE = os.environ.get("WORK_DIR", os.getcwd())
    GOAL = os.environ.get("TASK_DESCRIPTION", "Unknown Goal")
    
    architect = NeuralForgeArchitect(WORKSPACE)
    if architect.run(GOAL):
        sys.exit(0)
    else:
        sys.exit(1)
