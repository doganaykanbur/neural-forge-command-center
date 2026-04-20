"""
Neural Forge — Phase 3 Node Agent
Python agent with heartbeat + real task execution via RuntimeManager.

Usage:
    python agent.py
    NERVE_CENTER_URL=http://192.168.1.10:8000 python agent.py
"""

import os
import sys
import time
import signal
import socket
import platform
import threading
import traceback
import subprocess
import uuid as uuid_lib
from pathlib import Path
from datetime import datetime, timezone

import psutil
import requests

# ═════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════

SERVER_URL = os.environ.get("NERVE_CENTER_URL", "http://localhost:8001").strip()
HEARTBEAT_INTERVAL = 10
POLL_INTERVAL = 5
API_TIMEOUT = 5

# ═════════════════════════════════════════════
# System Info (unchanged from Phase 2)
# ═════════════════════════════════════════════


def get_mac_address() -> str:
    mac_int = uuid_lib.getnode()
    return ":".join(f"{(mac_int >> (8 * (5 - i))) & 0xFF:02X}" for i in range(6))


def get_gpu_name() -> str:
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].name
    except Exception:
        pass
    if platform.system() == "Windows":
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and l.strip() != "Name"]
            if lines:
                return lines[0]
        except Exception:
            pass
    return "Unknown GPU"


def get_gpu_percent() -> float | None:
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].load * 100.0
    except Exception:
        pass
    return None


def collect_static_info() -> dict:
    total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3))
    cpu_name = platform.processor() or "Unknown CPU"
    if platform.system() == "Windows":
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and l.strip() != "Name"]
            if lines:
                cpu_name = lines[0]
        except Exception:
            pass
    return {
        "desktop_name": socket.gethostname(),
        "mac_address": get_mac_address(),
        "system_info": {
            "cpu": cpu_name,
            "ram": f"{total_ram_gb} GB",
            "gpu": get_gpu_name(),
        },
        "capabilities": collect_capabilities(),
        "requested_roles": ["architect", "review", "build", "test", "execute", "pipeline", "system"],
    }


# ═════════════════════════════════════════════
# Stability / Capability Probe
# ═════════════════════════════════════════════


def _check_command(cmd: list[str], timeout: int = 5) -> str | None:
    """Run a command and return stdout, or None on failure."""
    try:
        import subprocess
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def collect_capabilities() -> dict:
    """
    Probe the worker machine for installed tools, LLM availability,
    IDE presence, and system readiness. Sent at registration + heartbeat.
    """
    caps = {}

    # ── Docker ──
    docker_version = _check_command(["docker", "--version"])
    caps["docker"] = {
        "installed": docker_version is not None,
        "version": docker_version.split(",")[0].replace("Docker version ", "") if docker_version else None,
        "status": "ready" if docker_version else "missing",
    }
    # Check if Docker daemon is actually running
    if caps["docker"]["installed"]:
        docker_info = _check_command(["docker", "info", "--format", "{{.ServerVersion}}"])
        if docker_info:
            caps["docker"]["daemon_running"] = True
            caps["docker"]["status"] = "ready"
        else:
            caps["docker"]["daemon_running"] = False
            caps["docker"]["status"] = "daemon_offline"

    # ── Ollama (LLM) ──
    ollama_version = _check_command(["ollama", "--version"])
    caps["ollama"] = {
        "installed": ollama_version is not None,
        "version": ollama_version if ollama_version else None,
        "status": "checking",
        "models": [],
    }
    if caps["ollama"]["installed"]:
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                caps["ollama"]["models"] = models
                caps["ollama"]["status"] = "ready" if models else "no_models"
            else:
                caps["ollama"]["status"] = "api_error"
        except Exception:
            try:
                models_output = _check_command(["ollama", "list"])
                if models_output:
                    model_lines = [l.split()[0] for l in models_output.strip().split("\n")[1:] if l.strip()]
                    caps["ollama"]["models"] = model_lines
                    caps["ollama"]["status"] = "ready" if model_lines else "no_models"
                else:
                    caps["ollama"]["status"] = "service_offline"
            except Exception:
                caps["ollama"]["status"] = "service_offline"

    # ── Antigravity IDE (Optimized Check) ──
    antigravity_found = False
    antigravity_paths = []
    
    # Common installation locations on Windows
    possible_paths = [
        os.path.join(os.path.expanduser("~"), ".gemini", "antigravity"),
    ]
    
    if platform.system() == "Windows":
        local_app = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        possible_paths.extend([
            os.path.join(local_app, "Programs", "antigravity"),
            os.path.join(prog_files, "antigravity"),
            "C:\\antigravity",
        ])
    else:
        possible_paths.extend([
            "/usr/local/bin/antigravity",
            "/opt/antigravity",
        ])

    for p in possible_paths:
        if os.path.exists(p):
            antigravity_found = True
            antigravity_paths.append(p)

    caps["antigravity"] = {
        "installed": antigravity_found,
        "paths": antigravity_paths[:3],
        "status": "ready" if antigravity_found else "missing",
    }

    # ── Python ──
    caps["python"] = {
        "version": platform.python_version(),
        "executable": sys.executable,
        "status": "ready",
    }

    # ── Key Pip Packages ──
    import importlib.metadata
    important_packages = ["docker", "requests", "psutil", "httpx", "GPUtil", "flask", "fastapi"]
    installed_pkgs = {}
    for pkg in important_packages:
        try:
            ver = importlib.metadata.version(pkg)
            installed_pkgs[pkg] = ver
        except importlib.metadata.PackageNotFoundError:
            installed_pkgs[pkg] = None
    caps["pip_packages"] = installed_pkgs

    # ── Disk Space ──
    try:
        disk = psutil.disk_usage("/") if platform.system() != "Windows" else psutil.disk_usage("C:\\")
        caps["disk"] = {
            "total_gb": round(disk.total / (1024 ** 3), 1),
            "free_gb": round(disk.free / (1024 ** 3), 1),
            "percent_used": disk.percent,
            "status": "ok" if disk.percent < 90 else "low" if disk.percent < 95 else "critical",
        }
    except Exception:
        caps["disk"] = {"status": "unknown"}

    # ── Network (backend reachability) ──
    caps["network"] = {
        "hostname": socket.gethostname(),
        "ip": _get_local_ip(),
        "status": "ready",
    }

    # ── Overall Readiness Score ──
    checks = [
        caps["docker"]["status"] == "ready",
        caps["python"]["status"] == "ready",
        caps["disk"].get("status") in ("ok", "low"),
    ]
    optional_checks = [
        caps["ollama"]["status"] == "ready",
        caps["antigravity"]["installed"],
    ]
    required_score = sum(checks)
    optional_score = sum(optional_checks)
    total = required_score + optional_score
    max_total = len(checks) + len(optional_checks)

    caps["readiness"] = {
        "score": f"{total}/{max_total}",
        "required_ok": required_score == len(checks),
        "status": "ready" if required_score == len(checks) else "degraded" if required_score >= 2 else "not_ready",
    }

    return caps


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def collect_live_metrics(current_task_id: str | None = None) -> dict:
    mem = psutil.virtual_memory()
    available_ram_gb = round(mem.available / (1024 ** 3), 1)
    has_gpu = get_gpu_percent() is not None
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": mem.percent,
        "gpu_percent": get_gpu_percent(),
        "current_task": current_task_id,
        # Phase 7: Smart Routing
        "available_ram_gb": available_ram_gb,
        "has_gpu": has_gpu,
    }


# ═════════════════════════════════════════════
# API Client
# ═════════════════════════════════════════════


def api_register(info: dict) -> str | None:
    try:
        resp = requests.post(f"{SERVER_URL}/api/nodes/register", json=info, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["node_id"] if data.get("success") else None
    except requests.ConnectionError:
        print(f"[!] Cannot reach server at {SERVER_URL}")
    except Exception as e:
        print(f"[!] Registration error: {e}")
    return None


def api_heartbeat(node_id: str, metrics: dict) -> bool:
    try:
        resp = requests.post(f"{SERVER_URL}/api/nodes/{node_id}/heartbeat", json=metrics, timeout=API_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def api_poll_task(node_id: str) -> dict | None:
    try:
        resp = requests.post(f"{SERVER_URL}/api/tasks/poll", json={"node_id": node_id}, timeout=API_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("task"):
                return data["task"]
    except Exception:
        pass
    return None


def api_push_logs(task_id: str, logs: list[dict]) -> bool:
    """Stream log batch to backend."""
    try:
        resp = requests.post(
            f"{SERVER_URL}/api/tasks/{task_id}/logs",
            json={"logs": logs},
            timeout=API_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return False


def api_register_artifact(task_id: str, name: str, path: str) -> bool:
    """Register an artifact with the backend."""
    try:
        resp = requests.post(
            f"{SERVER_URL}/api/tasks/{task_id}/artifacts",
            json={"name": name, "path": path},
            timeout=API_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return False


def api_complete_task(task_id: str, status: str, result: dict) -> bool:
    try:
        resp = requests.post(
            f"{SERVER_URL}/api/tasks/{task_id}/complete",
            json={"status": status, "result": result},
            timeout=API_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return False


# ═════════════════════════════════════════════
# Worker Threads
# ═════════════════════════════════════════════

_running = True
_node_id: str | None = None
_current_task_id: str | None = None
_current_task_lock = threading.Lock()
_autopilot_enabled = False
_sentry_process = None

def _start_gui_sentry():
    """Launch the local GUI Sentry daemon to auto-click IDE buttons."""
    global _sentry_process
    try:
        # Use sys.executable to run the sentry sub-process
        script_path = Path(__file__).parent / "nf_gui_sentry.py"
        _sentry_process = subprocess.Popen([sys.executable, str(script_path)], 
                                            stdout=subprocess.DEVNULL, 
                                            stderr=subprocess.DEVNULL)
        print(f"  [SENTRY] Neural Forge GUI Sentry started (PID: {_sentry_process.pid})")
    except Exception as e:
        print(f"  [!] Failed to start GUI Sentry: {e}")



def _handle_shutdown(signum, frame):
    global _running
    _running = False
    print("\n[*] Shutting down gracefully...")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def janitor_cleanup():
    """Startup Janitor: Purge zombie nf_* work directories from %TEMP%."""
    import tempfile
    import shutil
    temp_dir = Path(tempfile.gettempdir())
    print(f"[*] Janitor: Scanning {temp_dir} for zombie workspaces...")
    count = 0
    try:
        # Match nf_architect_*, nf_build_*, etc.
        for p in temp_dir.glob("nf_*"):
            if p.is_dir():
                try:
                    # Check if it's actually a Neural Forge temp dir (contains result.json or md files)
                    # For safety, we just rely on the prefix nf_
                    shutil.rmtree(p, ignore_errors=True)
                    count += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"  [!] Janitor Error: {e}")
    
    if count > 0:
        print(f"  [✔] Janitor: Purged {count} zombie directories from previous sessions.")
    else:
        print("  [*] Janitor: Workspace is clean.")


def heartbeat_loop():
    """Heartbeat thread: sends metrics every HEARTBEAT_INTERVAL seconds."""
    global _running, _current_task_id, _node_id
    fail_count = 0

    while _running:
        if _node_id is None:
            time.sleep(2)
            continue

        node_id = _node_id
        with _current_task_lock:
            task_id = _current_task_id

        metrics = collect_live_metrics(task_id)
        try:
            ok_res = requests.post(f"{SERVER_URL}/api/nodes/{node_id}/heartbeat", json=metrics, timeout=API_TIMEOUT)
            
            if ok_res.status_code == 200:
                data = ok_res.json()
                global _autopilot_enabled
                _autopilot_enabled = data.get("autopilot_enabled", False)
                
                fail_count = 0
            elif ok_res.status_code == 404:
                print(f"  [!] Backend lost registration for node {node_id}. Resetting...")
                _node_id = None
                fail_count += 1
            else:
                fail_count += 1
                if fail_count <= 3 or fail_count % 10 == 0:
                    print(f"  [!] Heartbeat failed (Status {ok_res.status_code}): {ok_res.text}")
        except Exception as e:
            fail_count += 1
            if fail_count <= 3 or fail_count % 10 == 0:
                print(f"  [!] Heartbeat exception: {e}")

        time.sleep(HEARTBEAT_INTERVAL)


def task_worker_loop():
    """Task worker thread: polls, executes via RuntimeManager, streams logs."""
    global _running, _current_task_id, _node_id
    
    # Import RuntimeManager
    from runtime import RuntimeManager
    runtime = RuntimeManager(SERVER_URL)

    while _running:
        if _node_id is None:
            time.sleep(POLL_INTERVAL)
            continue
        
        node_id = _node_id
        task = api_poll_task(node_id)

        if task:
            task_id = task["task_id"]
            print(f"\n  +--------------------------------------")
            print(f"  | TASK RECEIVED: {task['title']}")
            print(f"  |    Type: {task['task_type']} | Priority: {task['priority']}")
            print(f"  |    ID: {task_id}")
            print(f"  +--------------------------------------")

            with _current_task_lock:
                _current_task_id = task_id

            # Log buffer for batching
            log_buffer = []
            log_buffer_lock = threading.Lock()

            def on_log(level: str, message: str):
                """Callback: buffer log, print, and flush to server periodically."""
                entry = {"timestamp": _now_iso(), "level": level, "message": message}
                prefix = {"info": "  │", "warn": "  │ ⚠", "error": "  │ ✗"}.get(level, "  │")
                print(f"{prefix} {message}")
                with log_buffer_lock:
                    log_buffer.append(entry)
                    if len(log_buffer) >= 5:
                        batch = list(log_buffer)
                        log_buffer.clear()
                        api_push_logs(task_id, batch)

            def on_artifact(name: str, path: str):
                """Callback: register artifact with server."""
                api_register_artifact(task_id, name, path)

            # Execute via RuntimeManager
            start_time = time.time()

            try:
                status, raw_result = runtime.execute(task, on_log, on_artifact)
            except Exception as e:
                traceback.print_exc()
                status = "failed"
                raw_result = {"error": str(e)}
            
            duration_ms = int((time.time() - start_time) * 1000)

            # Flush remaining logs
            with log_buffer_lock:
                if log_buffer:
                    api_push_logs(task_id, list(log_buffer))
                    log_buffer.clear()

            # Phase 12: Wrap result in <task-notification> XML for Orchestrator Synthesis
            result_text = raw_result.get("output", raw_result.get("error", "No output provided."))
            summary = "completed" if status == "completed" else f"failed: {raw_result.get('error', 'unknown error')}"
            
            xml_notification = f"""<task-notification>
<task-id>{task_id}</task-id>
<status>{status}</status>
<summary>Agent "{task['title']}" {summary}</summary>
<result>{result_text}</result>
<usage>
  <duration_ms>{duration_ms}</duration_ms>
</usage>
</task-notification>"""

            final_result = {
                "xml": xml_notification,
                "raw": raw_result,
                "duration_ms": duration_ms
            }

            # Report completion
            ok = api_complete_task(task_id, status, final_result)
            emoji = "[OK]" if status == "completed" else "[FAIL]"
            report_str = "reported" if ok else "REPORT FAILED"
            print(f"  {emoji} Task {status} ({duration_ms}ms) --- {report_str}")
            print()

            with _current_task_lock:
                _current_task_id = None

        time.sleep(POLL_INTERVAL)


# ═════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════


def main():
    global _running, _node_id

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    print("\n" + "=" * 50)
    print("  NEURAL FORGE — NODE AGENT v4.0 (Autonomous)")
    print("=" * 50)
    print(f"  Server : {SERVER_URL}")
    print()

    print("[*] Probing system capabilities...")
    info = collect_static_info()
    caps = info.get("capabilities", {})
    
    print()
    print("─── System Info ───")
    print(f"    Hostname : {info['desktop_name']}")
    print(f"    MAC      : {info['mac_address']}")
    print(f"    CPU      : {info['system_info']['cpu']}")
    print(f"    RAM      : {info['system_info']['ram']}")
    print(f"    GPU      : {info['system_info']['gpu']}")
    print()
    
    print("─── Readiness Check ───")
    r_score = caps.get("readiness", {}).get("score", "?")
    r_status = caps.get("readiness", {}).get("status", "unknown")
    print(f"    Score    : [{r_score}] --- Status: {r_status.upper()}")
    print(f"    Docker   : {'[OK]' if caps.get('docker',{}).get('status') == 'ready' else '[FAIL]'}")
    print(f"    Python   : {'[OK]' if caps.get('python',{}).get('status') == 'ready' else '[FAIL]'} ({caps.get('python',{}).get('version')})")
    print(f"    Ollama   : {'[OK]' if caps.get('ollama',{}).get('status') == 'ready' else '[WARN]'} ({len(caps.get('ollama',{}).get('models',[]))} models)")
    print(f"    IDE      : {'[OK]' if caps.get('antigravity',{}).get('installed') else '[WARN]'} (Antigravity)")
    print(f"    Disk     : {'[OK]' if caps.get('disk',{}).get('status') in ('ok','low') else '[WARN]'} ({caps.get('disk',{}).get('free_gb')} GB free)")
    print()

    # Startup Hygiene
    janitor_cleanup()

    # Start sidecar services
    _start_gui_sentry()

    # Start task threads (these watch for _node_id globally)
    threading.Thread(target=heartbeat_loop, daemon=True, name="heartbeat").start()
    threading.Thread(target=task_worker_loop, daemon=True, name="task-worker").start()

    print("[*] Entering Autonomous Handshake Loop...")
    while _running:
        if _node_id is None:
            ts = time.strftime("%H:%M:%S")
            print(f"  [{ts}] [!] Not registered. Attempting handshake...")
            new_id = api_register(info)
            if new_id:
                _node_id = new_id
                print(f"  [{ts}] [+] Handshake successful! Node ID: {_node_id}")
                print(f"  [{ts}] [⏳] Agent is IDLE and waiting for new tasks from Orchestrator...")
            else:
                time.sleep(10)
                continue
        
        time.sleep(5)

    print("[*] Agent shutdown complete.")


if __name__ == "__main__":
    main()
