import subprocess
import threading
import sys
import os
import signal
import time

# Force UTF-8 for console output to prevent UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def log_reader(pipe, prefix, color_code):
    """Prefixed log reader for stdout/stderr."""
    if not pipe:
        return
    for line in iter(pipe.readline, b""):
        try:
            msg = line.decode(errors='replace').strip()
            # Sanitize for Windows CP1252 console safety
            safe_msg = msg.encode('ascii', 'replace').decode()
            sys.stdout.write(f"\x1b[{color_code}m[{prefix}]\x1b[0m {safe_msg}\n")
            sys.stdout.flush()
        except Exception:
            pass
    pipe.close()

def ignition():
    print("\x1b[95m[LAUNCH] Neural Forge NEXUS v2.3 --- \"VISIBLE MODE\" Bootloader starting...\x1b[0m")
    processes = []
    
    # Common Env for all processes
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["NERVE_CENTER_URL"] = "http://localhost:8001"
    env["ANTHROPIC_BASE_URL"] = "http://localhost:8000/v1"
    env["ANTHROPIC_API_KEY"] = "dummy-nexus-key"

    # Flag for new console on Windows
    create_win = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0

    # 1. Start Nexus Bridge (Mock API) - Port 8000
    print("\x1b[96m[*] [BRIDGE] Launching Nexus Mock Bridge in NEW window...\x1b[0m")
    bridge_cmd = [sys.executable, "backend/nexus_bridge.py"]
    
    try:
        bridge_p = subprocess.Popen(
            bridge_cmd,
            cwd=".",
            env=env,
            creationflags=create_win
        )
        processes.append(("BRIDGE", bridge_p))
    except Exception as e:
        print(f"\x1b[91m[!] Failed to start Nexus Bridge: {e}\x1b[0m")
        return

    # 2. Start Backend (Nerve Center) - Port 8001
    print("\x1b[94m[*] [BACKEND] Launching FastAPI Core in NEW window...\x1b[0m")
    backend_cmd = [sys.executable, "backend/main.py"]
    
    try:
        backend_p = subprocess.Popen(
            backend_cmd,
            cwd=".",
            env=env,
            creationflags=create_win
        )
        processes.append(("BACKEND", backend_p))
    except Exception as e:
        print(f"\x1b[91m[!] Failed to start Backend: {e}\x1b[0m")
        return

    # 3. Start Frontend (3000)
    print("\x1b[92m[*] [FRONTEND] Launching Next.js UI in NEW window...\x1b[0m")
    frontend_cmd = ["npm.cmd" if os.name == 'nt' else "npm", "run", "dev"]
    
    try:
        frontend_p = subprocess.Popen(
            frontend_cmd,
            cwd="admin-panel",
            shell=True if os.name == 'nt' else False,
            env=env,
            creationflags=create_win
        )
        processes.append(("FRONTEND", frontend_p))
        time.sleep(2)
    except Exception as e:
        print(f"\x1b[91m[!] Failed to start Frontend: {e}\x1b[0m")
        return

    # 4. Start Agent (Worker) - Connects to 8001
    print("\x1b[95m[*] [AGENT] Launching Node Agent in NEW window...\x1b[0m")
    agent_cmd = [sys.executable, "node_agent/agent.py"]
    
    try:
        agent_p = subprocess.Popen(
            agent_cmd,
            cwd=".",
            env=env,
            creationflags=create_win
        )
        processes.append(("AGENT", agent_p))
    except Exception as e:
        print(f"\x1b[91m[!] Failed to start Agent: {e}\x1b[0m")

    # In Visible Mode, we don't need log_reader threads because windows are independent.
    # However, we still monitor for process death.
    print("\x1b[93m[!] [VISIBLE SYSTEM] All services popped up. Monitor individual windows for logs.\x1b[0m")
    print("\x1b[93m[!] [URLS] Frontend: http://localhost:3000 | Backend: http://localhost:8001 | Bridge: http://localhost:8000 | Agent: Active\x1b[0m")
    
    try:
        startup_grace_period = time.time() + 15
        while True:
            for label, p in processes:
                if time.time() > startup_grace_period:
                    if p.poll() is not None:
                        print(f"\n\x1b[91m[!] {label} window closed or terminated unexpectedly (Exit Code: {p.poll()}).\x1b[0m")
                        raise KeyboardInterrupt
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\x1b[91m[!] [SHUTDOWN] Terminating all Neural Forge processes...\x1b[0m")
        for label, p in processes:
            print(f"[-] Stopping {label} (PID: {p.pid})...")
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                p.terminate()
                p.wait()
        print("\x1b[32m[OK] Neural Forge is safely offline. Goodbye.\x1b[0m")

if __name__ == "__main__":
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
    
    ignition()

if __name__ == "__main__":
    # Ensure color codes work on Windows
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
    
    ignition()
