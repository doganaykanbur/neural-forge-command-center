import wexpect
import sys
import os
import time

# ═════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════

# The command to launch the Claude CLI
# -p flag passes a prompt to the CLI
CLAUDE_COMMAND = 'cmd.exe /c claude -p "Read CLAUDE_INSTRUCTIONS.md and build the project."'

# Environment instructions for the user:
# set ANTHROPIC_BASE_URL=http://localhost:8000
# set ANTHROPIC_API_KEY=dummy-key-for-local-bridge

def run_autonomous_builder():
    print("\n" + "="*60)
    print("  NEURAL FORGE - AUTONOMOUS CLAUDE BUILDER v1.0")
    print("="*60)
    
    # Verify environment
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    if not base_url or "localhost:8000" not in base_url:
        print("[!] WARNING: ANTHROPIC_BASE_URL is not set to http://localhost:8000")
        print("[!] The CLI might connect to the real Anthropic API instead of Ollama.")
        # We continue anyway, but the user should be aware.

    print(f"[*] Spawning: {CLAUDE_COMMAND}")
    
    try:
        # wexpect.spawn is the Windows equivalent of pexpect.spawn
        child = wexpect.spawn(CLAUDE_COMMAND, timeout=300)
        
        # Patterns to look for in the CLI output
        # These are common confirmation prompts from Claude Code CLI
        prompts = [
            r"Do you want to proceed\?", 
            r"\[y/n\]", 
            r"Create this file\?", 
            r"Modify this file\?",
            r"Allow\?",
            wexpect.EOF,
            wexpect.TIMEOUT
        ]

        while True:
            # We use index to identify which pattern was matched
            index = child.expect(prompts)
            
            # Print whatever was received since the last match
            # child.before contains the text before the matched pattern
            # child.after contains the matched pattern itself
            output = child.before + (child.after if isinstance(child.after, str) else "")
            sys.stdout.write(output)
            sys.stdout.flush()

            if index == len(prompts) - 2: # EOF
                print("\n[√] Claude CLI finished execution (EOF).")
                break
            
            if index == len(prompts) - 1: # TIMEOUT
                print("\n[!] Error: CLI operation timed out.")
                break
            
            # If we hit one of the confirmation prompts
            print("\n[NEXUS: AUTO-ACK] 'y' sent to confirm operation.")
            child.sendline('y')
            # Small sleep to avoid flooding
            time.sleep(0.5)

    except Exception as e:
        print(f"\n[!] Unexpected Error: {e}")
    
    print("\n" + "="*60)
    print("  BUILDER SESSION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    run_autonomous_builder()
