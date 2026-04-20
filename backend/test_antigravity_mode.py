import os
import json
import time
from pathlib import Path

# --- ABSOLUTE PROJECT PATHS ---
PROJECT_ROOT = r"c:\Users\doganay\.gemini\antigravity\scratch\neural_forge_command_center"
BRIDGE_DIR = Path(PROJECT_ROOT) / ".nexus" / "rules"

class StandaloneAntigravityProvider:
    """Self-contained version of the provider for verification."""
    def __init__(self, bridge_dir: Path):
        self.bridge_dir = bridge_dir
        self.request_file = bridge_dir / "ANTIGRAVITY_REQUEST.json"
        self.response_file = bridge_dir / "ANTIGRAVITY_RESPONSE.json"

    def complete(self, prompt: str):
        # Ensure bridge_dir exists
        print(f"[*] Ensuring bridge directory exists: {self.bridge_dir}")
        self.bridge_dir.mkdir(parents=True, exist_ok=True)

        # Cleanup old response
        if self.response_file.exists():
            self.response_file.unlink()

        # Write request
        payload = {
            "task_id": f"ide-{int(time.time())}",
            "prompt": prompt,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        print(f"[*] Writing synthesis request to: {self.request_file}")
        self.request_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print("[WAIT] Waiting for ANTIGRAVITY_RESPONSE.json...")
        start_time = time.time()
        while time.time() - start_time < 300:
            if self.response_file.exists():
                try:
                    data = json.loads(self.response_file.read_text(encoding="utf-8"))
                    text = data.get("text", "")
                    print("[SUCCESS] Received response from Antigravity Agent!")
                    # Cleanup
                    self.request_file.unlink(missing_ok=True)
                    self.response_file.unlink(missing_ok=True)
                    return text
                except json.JSONDecodeError:
                    pass
            time.sleep(2)
        return "Timeout waiting for agent."

def run_standalone_test():
    print(f"\n{'='*50}")
    print("STANDALONE ANTIGRAVITY BRIDGE HANDSHAKE VERIFICATION")
    print(f"{'='*50}")
    
    provider = StandaloneAntigravityProvider(BRIDGE_DIR)
    
    test_prompt = "Generate a Python script that prints 'Neural Forge Standalone Handshake Successful'."
    print(f"[*] Sending test prompt: {test_prompt}")
    
    result = provider.complete(test_prompt)
    
    print("\n" + "-"*20)
    print("FINAL RESULT FROM BRIDGE:")
    print(result)
    print("-" * 20)

if __name__ == "__main__":
    run_standalone_test()
