import os
import signal
import psutil

def cleanup_backend():
    print("[*] Searching for redundant 'main.py' processes...")
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('main.py' in part for part in cmdline):
                pid = proc.info['pid']
                if pid != current_pid:
                    print(f"[!] Found zombie backend: PID {pid}. Terminating...")
                    proc.terminate() # Graceful
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        print(f"[!!] Force killing PID {pid}...")
                        proc.kill() # Force
                    print(f"[x] PID {pid} killed.")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

if __name__ == "__main__":
    cleanup_backend()
    print("[✓] Environment consolidated.")
