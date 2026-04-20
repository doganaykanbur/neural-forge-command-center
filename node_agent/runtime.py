"""
Neural Forge — RuntimeManager
Abstraction layer for worker execution. Currently uses subprocess;
swap to docker-py by reimplementing this single class.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import threading
import time
import zipfile
import requests
import docker
from pathlib import Path
from typing import Callable, Optional

# Base directory for artifacts
ARTIFACTS_BASE = Path(__file__).parent.parent / "artifacts"


class RuntimeManager:
    """
    Manages isolated execution of worker role scripts.
    
    Current backend: subprocess (child Python process)
    Future backend:  docker-py (container)
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        ARTIFACTS_BASE.mkdir(parents=True, exist_ok=True)

    def download_workspace(self, parent_task_id: str, dest_dir: Path, on_log) -> None:
        on_log("info", f"Downloading workspace from task {parent_task_id}...")
        try:
            resp = requests.get(f"{self.server_url}/api/tasks/{parent_task_id}/workspace/download", timeout=60)
            if resp.status_code == 200:
                zip_path = dest_dir / "workspace.zip"
                zip_path.write_bytes(resp.content)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_dir)
                zip_path.unlink()
                on_log("info", "Workspace downloaded and extracted successfully.")
            else:
                on_log("warn", f"Failed to download workspace. Status: {resp.status_code}")
        except Exception as e:
            on_log("warn", f"Failed to download workspace: {e}")

    def upload_workspace(self, task_id: str, source_dir: Path, on_log) -> None:
        on_log("info", f"Uploading workspace for task {task_id} to vault...")
        try:
            zip_path = source_dir.parent / f"{task_id}_upload.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
                        
            with open(zip_path, 'rb') as f:
                resp = requests.post(f"{self.server_url}/api/tasks/{task_id}/workspace/upload", files={"file": f}, timeout=60)
                
            zip_path.unlink()
            if resp.status_code == 200:
                on_log("info", "Workspace uploaded successfully.")
            else:
                on_log("warn", f"Workspace upload failed. Status: {resp.status_code}")
        except Exception as e:
            on_log("warn", f"Failed to upload workspace: {e}")

    def _setup_node_venv(self, on_log: Callable) -> str:
        """Create or ensure a persistent global virtual environment for the node."""
        venv_dir = Path(__file__).parent / ".venv_node"
        
        # Determine python path
        if os.name == 'nt':
            bin_python = venv_dir / "Scripts" / "python.exe"
        else:
            bin_python = venv_dir / "bin" / "python"

        # Check if venv already exists
        if venv_dir.exists() and bin_python.exists():
            return str(bin_python)

        on_log("info", f"Setup: Initializing node-level virtual environment at {venv_dir} (ONE-TIME SETUP)...")
        try:
            # 1. Create venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, capture_output=True)
            
            # 2. Install CORE node_agent requirements
            core_reqs = Path(__file__).parent / "requirements.txt"
            if core_reqs.exists():
                on_log("info", "Setup: Installing core dependencies (requests, wexpect, etc.)...")
                # Use Popen to stream output for real-time visibility
                proc = subprocess.Popen(
                    [str(bin_python), "-m", "pip", "install", "--upgrade", "pip"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        on_log("info", f"  [PIP] {line.strip()}")
                proc.wait()

                proc = subprocess.Popen(
                    [str(bin_python), "-m", "pip", "install", "-r", str(core_reqs)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        on_log("info", f"  [PIP] {line.strip()}")
                proc.wait()
            
            return str(bin_python)
        except Exception as e:
            on_log("warn", f"Setup: Persistent venv creation failed ({e}). Falling back to system python.")
            return sys.executable

    def _install_task_requirements(self, bin_python: str, work_dir: Path, on_log: Callable):
        """Install task-specific requirements into the global node venv."""
        req_file = work_dir / "requirements.txt"
        if req_file.exists():
            on_log("info", "Setup: Installing task-specific requirements.txt...")
            try:
                proc = subprocess.Popen(
                    [bin_python, "-m", "pip", "install", "-r", str(req_file)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        on_log("info", f"  [PIP] {line.strip()}")
                proc.wait()
            except Exception as e:
                on_log("warn", f"Setup: Task requirements failed: {e}")

    def execute(
        self,
        task: dict,
        on_log: Callable[[str, str], None],   # (level, message)
        on_artifact: Callable[[str, str], None],  # (name, path)
    ) -> tuple[str, dict]:
        """
        Execute a task using the appropriate role script.
        """
        task_id = task["task_id"]
        task_type = task.get("task_type", "build")
        
        # Create task-specific artifact directory
        artifact_dir = ARTIFACTS_BASE / task_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary working directory
        work_dir = Path(tempfile.mkdtemp(prefix=f"nf_{task_type}_"))
        
        on_log("info", f"RuntimeManager: starting '{task_type}' worker")

        # ─── Phase 6: Download Parent/Dependency Workspace ───
        source_task_id = task.get("parent_task_id") or task.get("depends_on")
        if source_task_id:
            self.download_workspace(source_task_id, work_dir, on_log)

        try:
            # Resolve role script
            script_map = {
                "review": "reviewer.py",
                "build": "builder.py",
                "test": "tester.py",
                "execute": "executor.py",
                "architect": "architect.py",
            }
            script_name = script_map.get(task_type, f"{task_type}.py")
            role_script = Path(__file__).parent / "roles" / script_name

            if not role_script.exists():
                on_log("error", f"Role script not found: {role_script}")
                return "failed", {"error": f"Unknown role: {task_type}"}

            # Phase 16: Workspace Isolation / Sandboxing
            # Force Docker for potentially destructive tasks
            use_docker = task.get("use_docker", True)
            if task_type in ("test", "execute"):
                on_log("info", f"Sandboxing: Enforcing Docker Isolation for '{task_type}' task.")
                use_docker = True

            if use_docker:
                try:
                    client = docker.from_env()
                except Exception as e:
                    if task_type in ("test", "execute"):
                        on_log("error", "Docker is REQUIRED for this task but daemon is unavailable. Halting for safety.")
                        return "failed", {"error": "Docker unavailable for sandboxed task"}
                    on_log("warn", f"Docker daemon unavailable ({e}). Falling back to Native Execution.")
                    use_docker = False

            output_lines = []

            def _handle_log_line(line_str: str):
                output_lines.append(line_str)
                if line_str.startswith("[ERROR]"):
                    on_log("error", line_str[7:].strip())
                elif line_str.startswith("[WARN]"):
                    on_log("warn", line_str[6:].strip())
                elif line_str.startswith("[ARTIFACT]"):
                    parts = line_str[10:].strip().split("|", 1)
                    if len(parts) == 2:
                        host_path = str(artifact_dir / Path(parts[1].strip()).name)
                        on_artifact(parts[0].strip(), host_path)
                else:
                    on_log("info", line_str.lstrip("[INFO] "))

            if use_docker:
                # Docker Execution logic remains same...
                docker_server_url = self.server_url
                if "localhost" in docker_server_url or "127.0.0.1" in docker_server_url:
                    docker_server_url = docker_server_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")

                env = {
                    "TASK_ID": task_id,
                    "TASK_TYPE": task_type,
                    "TASK_TITLE": task.get("title", ""),
                    "TASK_DESCRIPTION": task.get("description", ""),
                    "ARTIFACT_DIR": "/app/artifacts",
                    "WORK_DIR": "/app/workspace",
                    "SERVER_URL": docker_server_url,
                }
                roles_dir = Path(__file__).parent / "roles"
                volumes = {
                    str(work_dir.absolute()): {'bind': '/app/workspace', 'mode': 'rw'},
                    str(artifact_dir.absolute()): {'bind': '/app/artifacts', 'mode': 'rw'},
                    str(roles_dir.absolute()): {'bind': '/app/roles', 'mode': 'ro'},
                }
                command = f"python /app/roles/{script_name}"
                on_log("info", f"Spawning Docker Container: python:3.11-slim")
                
                container = None
                try:
                    container = client.containers.run(
                        image="python:3.11-slim",
                        command=command,
                        environment=env,
                        volumes=volumes,
                        detach=True,
                        working_dir="/app/workspace"
                    )
                    for line in container.logs(stream=True, follow=True):
                        _handle_log_line(line.decode('utf-8', errors='replace').rstrip("\n"))
                    result = container.wait()
                    exit_code = result.get('StatusCode', 1)
                finally:
                    if container:
                        try:
                            container.remove(force=True)
                            on_log("info", "Container destroyed.")
                        except Exception: pass

            else:
                # ── Native Subprocess Execution with VENV Resolver ──
                # Phase 16: Setup Virtual Environment (Persistent Node Venv)
                bin_python = self._setup_node_venv(on_log)
                # Phase 17: Install task-specific requirements (into the node venv)
                self._install_task_requirements(bin_python, work_dir, on_log)
                
                env = {
                    **os.environ,
                    "TASK_ID": task_id,
                    "TASK_TYPE": task_type,
                    "TASK_TITLE": task.get("title", ""),
                    "TASK_DESCRIPTION": task.get("description", ""),
                    "ARTIFACT_DIR": str(artifact_dir.absolute()),
                    "WORK_DIR": str(work_dir.absolute()),
                    "VENV_PYTHON": str(bin_python), # Pass project venv to role script
                    "SERVER_URL": self.server_url,
                    "ANTHROPIC_BASE_URL": os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:8000/v1"),
                    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "dummy-nexus-key"),
                }
                on_log("info", f"Spawning Role Script with Host Python: {sys.executable}")
                
                proc = subprocess.Popen(
                    [sys.executable, str(role_script.absolute())],
                    env=env,
                    cwd=str(work_dir.absolute()),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    universal_newlines=True
                )
                
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        if not line: break
                        _handle_log_line(line.rstrip("\n"))
                
                proc.wait()
                exit_code = proc.returncode

            # Save full log as artifact
            log_file = artifact_dir / "execution.log"
            log_file.write_text("\n".join(output_lines), encoding="utf-8")
            on_artifact("execution_log", str(log_file))

            if exit_code == 0:
                on_log("info", f"Worker exited successfully (code 0)")
                result_file = artifact_dir / "result.json"
                if result_file.exists():
                    result = json.loads(result_file.read_text(encoding="utf-8"))
                else:
                    result = {"exit_code": 0, "output": "\n".join(output_lines[-10:])}
                return "completed", result
            else:
                on_log("error", f"Worker exited with code {exit_code}")
                return "failed", {
                    "exit_code": exit_code,
                    "output": "\n".join(output_lines[-20:]),
                }

        except Exception as e:
            on_log("error", f"RuntimeManager error: {e}")
            return "failed", {"error": str(e)}
        
        finally:
            self.upload_workspace(task_id, work_dir, on_log)
            # Clean up work dir (keep artifacts)
            shutil.rmtree(work_dir, ignore_errors=True)
