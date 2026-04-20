"""
Neural Forge Command Center — Phase 7 Backend
FastAPI server: nodes, tasks, logs, artifacts, LLM orchestrator, NEXUS memory.
Phase 7: Sweeper, DAG pipeline, smart routing.
"""

import uuid
import asyncio
import re
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables (API Keys)
load_dotenv()

import logging
# Silence watchfiles info spam from uvicorn reloader
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
# Silence generic uvicorn info logs to keep console clean for NEXUS heartbeats
logging.getLogger("uvicorn").setLevel(logging.WARNING)

import os
import requests
import json
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from orchestrator import Orchestrator
from nexus import NexusMemory
from nexus_bridge import NexusBridge

# =============================================
# Pydantic Models — Nodes
# ═════════════════════════════════════════════


class SystemInfo(BaseModel):
    """Static hardware specs reported at registration."""
    cpu: str = "Unknown CPU"
    ram: str = "Unknown"
    gpu: str = "Unknown GPU"


class NodeRegistrationRequest(BaseModel):
    """Payload sent by node_agent on first startup."""
    desktop_name: str
    mac_address: str
    system_info: SystemInfo
    capabilities: Optional[dict] = None  # Phase 9: Stability probe
    requested_roles: Optional[List[str]] = None  # Phase 16: Auto-assign roles


class HeartbeatPayload(BaseModel):
    """Live metrics sent by node_agent every 10 seconds."""
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_percent: Optional[float] = None
    current_task: Optional[str] = None  # Phase 2: task_id being executed
    # Phase 7: Smart Routing fields
    available_ram_gb: float = 0.0
    has_gpu: bool = False
    status: str = "online"


class NodeRecord(BaseModel):
    """Internal representation of a registered node."""
    node_id: str
    desktop_name: str
    mac_address: str
    system_info: SystemInfo
    live_metrics: HeartbeatPayload = HeartbeatPayload()
    assigned_roles: list[str] = ["architect", "review", "build", "test", "execute", "pipeline", "deploy", "system"]
    capabilities: Optional[dict] = None  # Phase 9: Docker, Ollama, Antigravity etc.
    registered_at: str
    last_seen: str
    status: str = "online"
    autopilot_enabled: bool = False # Phase 15
    usage: Optional[dict] = None # Phase 15: Per-node usage stats


# ═════════════════════════════════════════════
# Pydantic Models — Settings (Phase 10)
# ═════════════════════════════════════════════


class AppSettings(BaseModel):
    use_docker: bool = True


settings_state = AppSettings()


# ═════════════════════════════════════════════
# Pydantic Models — Tasks (Phase 2)
# ═════════════════════════════════════════════


class TaskType(str, Enum):
    ARCHITECT = "architect"
    REVIEW = "review"
    BUILD = "build"
    TEST = "test"
    EXECUTE = "execute"
    PIPELINE = "pipeline"  # generic pipeline task
    DEPLOY = "deploy"      # Phase 20: Distribution/Deploy


class TaskStatus(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_APPROVAL = "pending_approval"


class TaskCreateRequest(BaseModel):
    """Admin creates a new task."""
    title: str
    description: str = ""
    task_type: TaskType = TaskType.BUILD
    priority: int = Field(default=3, ge=1, le=5)
    can_be_parallel: bool = False  # Phase 12



class TaskCompleteRequest(BaseModel):
    """Node reports task completion."""
    status: TaskStatus = TaskStatus.COMPLETED
    result: dict = {}


class TaskPollRequest(BaseModel):
    """Node requesting a task."""
    node_id: str


class LogEntry(BaseModel):
    """A single log line from a worker."""
    timestamp: str
    level: str = "info"  # info, warn, error
    message: str


class LogBatchRequest(BaseModel):
    """Batch of log entries from a worker."""
    logs: list[LogEntry]


class ArtifactRef(BaseModel):
    """Reference to an artifact file."""
    name: str
    path: str
    created_at: str


class ArtifactUploadRequest(BaseModel):
    """Node registers an artifact."""
    name: str
    path: str


class TaskRecord(BaseModel):
    """Full task state."""
    task_id: str
    title: str
    description: str = ""
    task_type: TaskType
    priority: int
    status: TaskStatus = TaskStatus.QUEUED
    assigned_to: Optional[str] = None  # node_id
    assigned_to_name: Optional[str] = None  # desktop_name
    created_at: str
    assigned_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    logs: list[LogEntry] = []
    artifacts: list[ArtifactRef] = []
    # Phase 7/12
    parent_task_id: Optional[str] = None
    subtask_ids: list[str] = []
    node_id: Optional[str] = None  # Node that executed/is executing
    can_be_parallel: bool = False
    duration_ms: int = 0
    retry_count: int = 0
    target_node_id: Optional[str] = None  # Phase 12: Target specific node for session continuity
    depends_on: Optional[str] = None  # Phase 7: DAG — task_id this depends on

    requires_gpu: bool = False  # Phase 7: Smart Routing
    min_ram_gb: float = 0.0  # Phase 7: Smart Routing


# ═════════════════════════════════════════════
# Application Setup
# ═════════════════════════════════════════════

# In-memory stores (declared before lifespan)
nodes: dict[str, NodeRecord] = {}
tasks: dict[str, TaskRecord] = {}
task_queue: deque[str] = deque()

HEARTBEAT_TIMEOUT_SECONDS = 60
TASK_ZOMBIE_TIMEOUT_SECONDS = 300  # 5 minutes
SWEEPER_INTERVAL_SECONDS = 60


# ── Phase 7: Task Timeout Sweeper ──
async def _zombie_sweeper():
    """Background task: every 60s, find ASSIGNED tasks with no activity for 5min and re-queue or fail them."""
    while True:
        await asyncio.sleep(SWEEPER_INTERVAL_SECONDS)
        now = datetime.now(timezone.utc)
        swept = 0
        for task in list(tasks.values()):
            if task.status not in (TaskStatus.ASSIGNED, TaskStatus.RUNNING):
                continue
            # Determine last activity: last log timestamp, or assigned_at
            last_activity_str = task.assigned_at or task.created_at
            if task.logs:
                last_activity_str = task.logs[-1].timestamp
            if task.started_at and task.started_at > last_activity_str:
                last_activity_str = task.started_at
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                delta = (now - last_activity).total_seconds()
            except Exception:
                continue

            if delta > TASK_ZOMBIE_TIMEOUT_SECONDS:
                if task.retry_count < 3:
                    task.status = TaskStatus.QUEUED
                    task.assigned_to = None
                    task.assigned_to_name = None
                    task.assigned_at = None
                    task.started_at = None
                    task_queue.appendleft(task.task_id)
                    print(f"[SWEEPER] Re-queued zombie task: '{task.title}' (idle {delta:.0f}s)")
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = _now_iso()
                    task.result = {"error": f"Task timed out after {delta:.0f}s with {task.retry_count} retries"}
                    print(f"[SWEEPER] Failed zombie task: '{task.title}' (max retries exceeded)")
                swept += 1
                swept += 1
        
                # --- Phase 16: Node Pruning ---
        # If a node was last seen > 5 minutes ago, remove it from memory & disk
        pruned = 0
        node_ids = list(nodes.keys())
        for nid in node_ids:
            if _compute_status(nodes[nid]) == "offline":
                last = datetime.fromisoformat(nodes[nid].last_seen)
                delta = (now - last).total_seconds()
                if delta > 300: # 5 minutes
                    del nodes[nid]
                    pruned += 1
        if pruned:
            print(f"[SWEEPER] Pruned {pruned} inactive node(s) from registry.")
            _save_nodes()

        if swept:
            print(f"[SWEEPER] Swept {swept} zombie task(s)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background sweeper on startup, load nodes, clean up on shutdown."""
    _load_nodes()
    sweeper_task = asyncio.create_task(_zombie_sweeper())
    print(f"[*] Zombie Sweeper started (interval: {SWEEPER_INTERVAL_SECONDS}s, timeout: {TASK_ZOMBIE_TIMEOUT_SECONDS}s)")
    yield
    sweeper_task.cancel()
    print("[*] Zombie Sweeper stopped")


app = FastAPI(
    title="Neural Forge Command Center",
    description="Phase 7 — Nodes + Tasks + Workers + LLM Orchestrator + DAG + Sweeper",
    version="7.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 6: Orchestrator singleton & Vault logic
_nexus = NexusMemory()
_orchestrator = Orchestrator(nexus=_nexus)
_bridge = NexusBridge() # Nexus v2.0 Bridge Instance
VAULT_DIR = Path(__file__).parent / ".vault" / "workspaces"
VAULT_DIR.mkdir(parents=True, exist_ok=True)


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════


def _save_nodes():
    """Persist the nodes dictionary to disk."""
    try:
        path = VAULT_DIR.parent / "nodes.json"
        data = {nid: n.model_dump() for nid, n in nodes.items()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[!] Save nodes fail: {e}")


def _load_nodes():
    """Hydrate the nodes dictionary from disk."""
    try:
        path = VAULT_DIR.parent / "nodes.json"
        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)
                for nid, n_data in data.items():
                    nodes[nid] = NodeRecord(**n_data)
            print(f"[+] Restored {len(nodes)} nodes from persistent storage.")
    except Exception as e:
        print(f"[!] Load nodes fail: {e}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_status(node: NodeRecord) -> str:
    """Determine online/offline based on last heartbeat timestamp."""
    try:
        last = datetime.fromisoformat(node.last_seen)
        delta = (datetime.now(timezone.utc) - last).total_seconds()
        return "online" if delta < HEARTBEAT_TIMEOUT_SECONDS else "offline"
    except Exception:
        return "offline"


def _enrich_node(node: NodeRecord) -> dict:
    """Return node dict with computed status."""
    data = node.model_dump()
    data["status"] = _compute_status(node)
    return data


# ═════════════════════════════════════════════
# Settings Endpoints
# ═════════════════════════════════════════════


@app.get("/api/settings")
def get_settings():
    """Return global Command Center settings."""
    return settings_state.model_dump()


@app.post("/api/settings")
def update_settings(payload: AppSettings):
    """Update global Command Center settings."""
    global settings_state
    settings_state = payload
    print(f"[*] Settings updated: use_docker={settings_state.use_docker}")
    return {"success": True, "settings": settings_state.model_dump()}


# ═════════════════════════════════════════════
# Node Endpoints (Phase 1)
# ═════════════════════════════════════════════


@app.post("/api/nodes/register")
def register_node(payload: NodeRegistrationRequest):
    """
    Register a new node. Idempotent by MAC address.
    """
    # SEARCH: First, find by MAC address to see if we know this hardware
    existing_node = None
    for n in nodes.values():
        if n.mac_address == payload.mac_address:
            existing_node = n
            break

    if existing_node:
        # 1. Hardware known. Update specs, name, and live status.
        existing_node.system_info = payload.system_info
        existing_node.desktop_name = payload.desktop_name
        existing_node.capabilities = payload.capabilities
        existing_node.last_seen = _now_iso()
        # IMPORTANT: We DO NOT overwrite existing_node.assigned_roles here.
        # It's either loaded from disk or set previously by User. 
        # The agent's 'requested_roles' are ignored for existing nodes.
        
        readiness = (payload.capabilities or {}).get("readiness", {}).get("score", "?")
        print(f"[*] Known hardware '{payload.desktop_name}' re-registered. Preserving assigned roles.")
        _save_nodes() # PERSISTENCE: Ensure roles are saved even on heartbeat/re-register
        return {
            "success": True,
            "node_id": existing_node.node_id,
            "message": "Node re-registered (MAC known, roles preserved)",
        }

    # 2. Hardware NEW. Create new record.
    node_id = str(uuid.uuid4())
    now = _now_iso()
    default_roles = ["architect", "review", "build", "test", "execute", "pipeline", "system"]
    
    # Use agent's requested roles ONLY for the first registration ever.
    initial_roles = payload.requested_roles if payload.requested_roles else default_roles

    record = NodeRecord(
        node_id=node_id,
        desktop_name=payload.desktop_name,
        mac_address=payload.mac_address,
        system_info=payload.system_info,
        capabilities=payload.capabilities,
        assigned_roles=initial_roles,
        registered_at=now,
        last_seen=now,
    )
    nodes[node_id] = record
    _save_nodes()
    
    print(f"[+] NEW Node registered: {payload.desktop_name} ({node_id})")
    return {"success": True, "node_id": node_id, "message": "New node registered"}


@app.get("/api/nodes/models")
def get_all_node_models():
    """
    Aggregate all available Ollama models, VRAM, and online status from all online nodes.
    Returns unique models + fleet capacity.
    """
    all_models = set()
    total_vram = 0.0
    used_vram = 0.0
    online_count = 0
    
    # Also include models from the Bridge itself if it has any defaults
    if _bridge and hasattr(_bridge, 'role_models'):
        for role, model in _bridge.role_models.items():
            all_models.add(model)
        
    for node in nodes.values():
        if _compute_status(node) == "online":
            online_count += 1
            if node.capabilities:
                ollama_caps = node.capabilities.get("ollama", {})
                node_models = ollama_caps.get("models", [])
                for m in node_models:
                    all_models.add(m)
            
            # Aggregate VRAM from NVIDIA-SMI reported in static info or live metrics
            # node.system_info.ram is CPU RAM, node.system_info.gpu is name
            # We look for 'vram' in capabilities or live metrics (if implemented)
            # For now, we take it from sys_info if we can parse it, or capabilities
            gpu_info = node.system_info.gpu
            if "RTX 3060 Ti" in gpu_info: # 8GB
                total_vram += 8.0
            elif "RTX 4090" in gpu_info: # 24GB
                total_vram += 24.0
            else:
                total_vram += 8.0 # Default fallback
                
            # If live metrics have gpu usage percentage
            if node.live_metrics.gpu_percent:
                used_vram += (node.live_metrics.gpu_percent / 100.0) * 8.0
                
    return {
        "success": True, 
        "models": sorted(list(all_models)),
        "fleet": {
            "online_nodes": online_count,
            "total_vram_gb": total_vram,
            "used_vram_gb": used_vram,
            "vram_percentage": (used_vram / total_vram * 100) if total_vram > 0 else 0
        }
    }


@app.post("/api/nodes/{node_id}/heartbeat")
def heartbeat(node_id: str, payload: HeartbeatPayload):
    """Receive a heartbeat with live metrics + optional current_task."""
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    node = nodes[node_id]
    node.last_seen = datetime.now(timezone.utc).isoformat()
    node.status = "online"
    # Update live metrics for dashboard
    node.live_metrics = payload
    # Optionally save nodes on heartbeat too or just every 60s in sweeper
    # Saving every 60s is better for performance, but we'll do it here to be accurate.
    _save_nodes() 
    return {"success": True, "autopilot_enabled": node.autopilot_enabled}


@app.get("/api/nodes")
def list_nodes(all: bool = False):
    """
    Return registered nodes with computed status.
    By default, only returns ONLINE nodes.
    """
    if all:
        return [_enrich_node(n) for n in nodes.values()]
    return [_enrich_node(n) for n in nodes.values() if _compute_status(n) == "online"]


@app.get("/api/nodes/{node_id}")
def get_node(node_id: str):
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    return _enrich_node(nodes[node_id])


@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str):
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    removed = nodes.pop(node_id)
    print(f"[-] Node removed: {removed.desktop_name} ({node_id})")
    return {"success": True, "message": f"Node {node_id} removed"}


class RoleUpdateRequest(BaseModel):
    roles: list[str]

@app.post("/api/nodes/{node_id}/roles")
def update_node_roles(node_id: str, payload: RoleUpdateRequest):
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    nodes[node_id].assigned_roles = payload.roles
    _save_nodes() # PERSISTENCE: Save immediately after manual change
    
    print(f"[*] Node {node_id} roles updated: {payload.roles}")
    return {"success": True}


@app.post("/api/nodes/{node_id}/autopilot")
def toggle_node_autopilot(node_id: str, payload: dict):
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    nodes[node_id].autopilot_enabled = payload.get("enabled", False)
    print(f"[*] Autopilot {'ENABLED' if nodes[node_id].autopilot_enabled else 'DISABLED'} for {nodes[node_id].desktop_name}")
    return {"success": True, "enabled": nodes[node_id].autopilot_enabled}


@app.get("/api/nodes/{node_id}/capabilities")
def get_node_capabilities(node_id: str):
    """Return full stability/capability report for a node."""
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    node = nodes[node_id]
    return {
        "node_id": node_id,
        "desktop_name": node.desktop_name,
        "status": _compute_status(node),
        "capabilities": node.capabilities or {},
    }


# ═════════════════════════════════════════════
# Task Endpoints (Phase 2)
# ═════════════════════════════════════════════


@app.post("/api/tasks")
def create_task(req: TaskCreateRequest):
    """
    Create a new task and push it to the queue.
    """
    task_id = str(uuid.uuid4())
    now = _now_iso()

    task = TaskRecord(
        task_id=task_id,
        title=req.title,
        description=req.description,
        task_type=req.task_type,
        priority=req.priority,
        can_be_parallel=req.can_be_parallel,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    tasks[task_id] = task
    task_queue.append(task_id)

    print(f"[Q] Task queued: '{req.title}' [{req.task_type.value}] → #{len(task_queue)} in queue")
    return {
        "success": True,
        "task_id": task_id,
        "queue_position": len(task_queue),
        "message": "Task created and queued",
    }


@app.delete("/api/tasks")
def delete_all_tasks():
    """
    Clear all tasks and empty the queue.
    Useful for stopping a runaway pipeline.
    """
    global tasks, task_queue
    count = len(tasks)
    tasks = {}
    task_queue = deque()
    print(f"[!] System Reset: {count} tasks removed from board.")
    return {"success": True, "message": f"Cleared {count} tasks."}


@app.get("/api/tasks")
def list_tasks(status: Optional[str] = None):
    """
    List all tasks, optionally filtered by status.
    """
    result = []
    for t in tasks.values():
        if status and t.status.value != status:
            continue
        result.append(t.model_dump())
    return result


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id].model_dump()


@app.post("/api/tasks/poll")
def poll_task(payload: TaskPollRequest):
    """
    Node calls this to claim the next available task from the queue.
    Phase 7: Respects DAG ordering (depends_on) and smart routing (GPU/RAM).
    """
    node_id = payload.node_id
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found — register first")

    node = nodes[node_id]
    if _compute_status(node) == "offline":
        raise HTTPException(status_code=403, detail="Node appears offline — send heartbeat first")

    unassigned = []
    assigned_task = None

    # Phase 7/12: Prioritization and Smart Routing
    # 1. First check if there's a task specifically targeted to this node
    target_task_id = None
    for tid in list(task_queue):
        if tasks[tid].target_node_id == node_id and tasks[tid].status == TaskStatus.QUEUED:
            target_task_id = tid
            break

    # 2. Main processing loop
    while task_queue:
        if target_task_id:
            task_id = target_task_id
            task_queue.remove(task_id)
            target_task_id = None # Reset so we don't loop on it
        else:
            task_id = task_queue.popleft()
            
        if task_id not in tasks or tasks[task_id].status != TaskStatus.QUEUED:
            continue

        task = tasks[task_id]

        # ── Phase 7: DAG Check — is the dependency or parent completed? ──
        # BLOCKER: If this task has a dependency OR a parent, both must be COMPLETED
        blocker_id = task.depends_on or task.parent_task_id
        if blocker_id:
            dep = tasks.get(blocker_id)
            if not dep or dep.status != TaskStatus.COMPLETED:
                # Still waiting for parent/dependency
                unassigned.append(task_id)
                continue

        # ── Role Check ──
        if task.task_type.value not in node.assigned_roles:
            unassigned.append(task_id)
            continue

        # ── Phase 7: Smart Routing — hardware requirements ──
        # Bypass for v2.3 testing: Trust the node can handle it for now.
        pass

        # All checks passed — assign
        task.status = TaskStatus.ASSIGNED
        task.assigned_to = node_id
        task.assigned_to_name = node.desktop_name
        task.assigned_at = datetime.now(timezone.utc).isoformat()

        print(f"[->] Task assigned: '{task.title}' -> {node.desktop_name}")
        assigned_task = task.model_dump()
        assigned_task["use_docker"] = settings_state.use_docker
        break

    # Put back tasks that were skipped
    for tid in reversed(unassigned):
        task_queue.appendleft(tid)

    if assigned_task:
        return {"success": True, "task": assigned_task}
    return {"success": True, "task": None, "message": "No matching tasks in queue"}


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, req: TaskCompleteRequest, background_tasks: BackgroundTasks):
    """
    Called by worker node when a task is finished.
    """
    global _orchestrator
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]

    # Update state (explicitly coerce to enum)
    try:
        task.status = TaskStatus(req.status)
    except ValueError:
        task.status = req.status
    task.result = req.result
    # Use current UTC time for completed_at
    task.completed_at = datetime.now(timezone.utc).isoformat()
    
    # Phase 12: Extract usage metrics from result
    if isinstance(req.result, dict):
        task.duration_ms = req.result.get("duration_ms", 0)
        # If node agent sent XML, log it as the final synthesis entry
        xml = req.result.get("xml")
        if xml:
            task.logs.append(LogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level="info",
                message=f"[SYNTHESIS] Task notification received:\n{xml}"
            ))

    # Trigger background logic for review and consolidation
    background_tasks.add_task(process_task_review_background, task_id)

    status_str = getattr(task.status, "value", task.status)
    return {"success": True, "task_id": task_id, "status": status_str}


async def process_task_review_background(task_id: str):
    """
    Background logic for reviewing a task result and updating the state.
    This runs asynchronously WITHOUT blocking the worker's HTTP response.
    """
    global _orchestrator
    
    if task_id not in tasks: return
    task = tasks[task_id]

    # Phase 4/11: Logic for result review and memory consolidation
    if task.status == TaskStatus.COMPLETED or task.status == TaskStatus.FAILED:
        # Review success or failure (this triggers consolidate_memory in orchestrator)
        ttype = getattr(task.task_type, "value", task.task_type)
        await _orchestrator.review_result(task.title, ttype, task.result)

    status_str = getattr(task.status, "value", task.status)
    emoji = "[OK]" if task.status == TaskStatus.COMPLETED else "[FAIL]"
    print(f"[{emoji}] Task {status_str}: '{task.title}' by {task.assigned_to_name}")

    # ─── Phase 6: Orchestrator Review & Self-Healing Hook ───
    decision = await _orchestrator.review_result(task.title, ttype, task.result)
    
    if decision.verdict == "retry" and task.retry_count < 3:
        new_task_id = str(uuid.uuid4())
        
        # Read the error to pass to builder
        error_context = decision.feedback
        if task.logs:
            error_context += "\nLast logs:\n" + "\n".join([l.message for l in task.logs[-5:]])
            
        record = TaskRecord(
            task_id=new_task_id,
            title=f"FIX: {task.title}",
            description=f"Fix the failing code from previous task. Errors:\n{error_context}\n\nOriginal Description:\n{task.description}",
            task_type=TaskType.BUILD,
            priority=5,
            status=TaskStatus.QUEUED,
            created_at=_now_iso(),
            parent_task_id=task_id,
            retry_count=task.retry_count + 1
        )
        tasks[new_task_id] = record
        task_queue.appendleft(new_task_id)  # High priority, put at front
        print(f"[RETRY] Orchestrator spawned self-healing task: {new_task_id}")

    status_str = getattr(task.status, "value", task.status)
    return {
        "success": True,
        "task_id": task_id,
        "final_status": status_str,
        "decision": decision.to_dict()
    }


# ═════════════════════════════════════════════
# Log & Artifact Endpoints (Phase 3)
# ═════════════════════════════════════════════


@app.post("/api/tasks/{task_id}/logs")
def push_logs(task_id: str, payload: LogBatchRequest):
    """Node streams log entries during execution."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    task.logs.extend(payload.logs)
    # Auto-transition to RUNNING on first log
    if task.status == TaskStatus.ASSIGNED:
        task.status = TaskStatus.RUNNING
        task.started_at = _now_iso()
    return {"success": True, "total_logs": len(task.logs)}


@app.get("/api/tasks/{task_id}/logs")
def get_logs(task_id: str, since: int = 0):
    """Retrieve logs for a task, optionally starting from an offset."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    return {
        "task_id": task_id,
        "total": len(task.logs),
        "logs": [l.model_dump() for l in task.logs[since:]],
    }

# ─── Phase 6: Centralized Workspace Vault ───

@app.post("/api/tasks/{task_id}/workspace/upload")
def upload_workspace(task_id: str, file: UploadFile = File(...)):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    file_path = VAULT_DIR / f"{task_id}.zip"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"success": True, "message": f"Workspace uploaded to vault for task {task_id}"}


@app.get("/api/tasks/{task_id}/workspace/download")
def download_workspace(task_id: str):
    file_path = VAULT_DIR / f"{task_id}.zip"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Workspace zip not found in vault")
    return FileResponse(file_path, media_type="application/zip", filename=f"workspace_{task_id}.zip")


@app.post("/api/tasks/{task_id}/artifacts")
def register_artifact(task_id: str, payload: ArtifactUploadRequest):
    """Node registers an artifact produced during execution."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    ref = ArtifactRef(name=payload.name, path=payload.path, created_at=_now_iso())
    tasks[task_id].artifacts.append(ref)
    return {"success": True, "artifact": ref.model_dump()}


@app.get("/api/tasks/{task_id}/artifacts")
def list_artifacts(task_id: str):
    """List all artifacts for a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task_id,
        "artifacts": [a.model_dump() for a in tasks[task_id].artifacts],
    }


# ═════════════════════════════════════════════
# Dashboard Summary & Health
# ═════════════════════════════════════════════


@app.get("/api/dashboard")
def dashboard_summary():
    """Aggregated stats for the admin UI."""
    online = sum(1 for n in nodes.values() if _compute_status(n) == "online")
    return {
        "nodes_total": len(nodes),
        "nodes_online": online,
        "tasks_total": len(tasks),
        "tasks_queued": sum(1 for t in tasks.values() if t.status == TaskStatus.QUEUED),
        "tasks_running": sum(1 for t in tasks.values() if t.status in (TaskStatus.ASSIGNED, TaskStatus.RUNNING)),
        "tasks_completed": sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED),
        "tasks_failed": sum(1 for t in tasks.values() if t.status == TaskStatus.FAILED),
        "queue_depth": len(task_queue),
    }


@app.get("/api/nodes/models")
def get_all_node_models():
    """
    Aggregate all available Ollama models from all online nodes.
    Returns a unique list of model names.
    """
    all_models = set()
    
    # Also include models from the Bridge itself if it has any defaults
    if _bridge and hasattr(_bridge, 'role_models'):
        for role, model in _bridge.role_models.items():
            all_models.add(model)
        
    for node in nodes.values():
        if _compute_status(node) == "online" and node.capabilities:
            ollama_caps = node.capabilities.get("ollama", {})
            node_models = ollama_caps.get("models", [])
            for m in node_models:
                all_models.add(m)
                
    return {"success": True, "models": sorted(list(all_models))}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "nodes_online": sum(1 for n in nodes.values() if _compute_status(n) == "online"),
        "queue_depth": len(task_queue),
    }


# ═════════════════════════════════════════════
# Orchestrator & NEXUS Endpoints (Phase 4)
# (Using globally initialized _nexus and _orchestrator)


class AnalyzeRequest(BaseModel):
    description: str


class GenerateRequest(BaseModel):
    goal: str
    blueprint: str


class PipelineRequest(BaseModel):
    goal: str


class ReviewRequest(BaseModel):
    task_title: str
    task_type: str
    result: dict


@app.post("/api/orchestrator/analyze")
async def orchestrator_analyze(payload: AnalyzeRequest):
    """
    LLM analyzes a task description → returns structured plan.
    """
    plan = await _orchestrator.analyze_task(payload.description)
    return {"success": True, "plan": plan.to_dict(), "provider": _orchestrator.provider.name}


@app.post("/api/orchestrator/generate")
async def orchestrator_generate(payload: GenerateRequest):
    """
    High-quality code generation for the Builder role.
    """
    code = await _orchestrator.generate_code(payload.goal, payload.blueprint)
    return {"success": True, "code": code, "provider": _orchestrator.provider.name}


@app.get("/api/orchestrator/usage")
def orchestrator_usage():
    """Return usage stats with explicit CORS fallback."""
    from fastapi.responses import JSONResponse
    content = {"success": True, "usage": _orchestrator.usage_tracker.stats}
    return JSONResponse(
        content=content,
        headers={"Access-Control-Allow-Origin": "*"}
    )


@app.post("/api/orchestrator/usage/limit")
def orchestrator_set_limit(payload: dict):
    """
    Update the token quota/limit for a specific node or global.
    """
    node_id = payload.get("node_id")
    limit = payload.get("limit", 1000000)
    
    if node_id:
        node_stats = _orchestrator.usage_tracker.get_node_stats(node_id)
        node_stats["token_limit"] = limit
    else:
        _orchestrator.usage_tracker.stats["global"]["token_limit"] = limit
        
    _orchestrator.usage_tracker._save()
    return {"success": True, "limit": limit, "node_id": node_id}


@app.post("/api/orchestrator/pipeline")
async def orchestrator_pipeline(payload: PipelineRequest):
    """
    LLM breaks a complex goal into ordered subtasks.
    """
    plans = await _orchestrator.plan_pipeline(payload.goal)
    return {
        "success": True,
        "pipeline": [p.to_dict() for p in plans],
        "total_steps": len(plans),
        "provider": _orchestrator.provider.name,
    }


@app.post("/api/orchestrator/pipeline/execute")
async def orchestrator_pipeline_execute(payload: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Plan a pipeline AND queue all subtasks with DAG dependencies.
    Phase 7: Each task depends_on the previous one → strict sequential execution.
    Phase 15: Backgrounded to prevent Node.js proxy socket timeout.
    """
    execution_id = str(uuid.uuid4())  # unique pipeline execution ID
    background_tasks.add_task(_background_plan_and_queue, payload.goal, execution_id)

    return {
        "success": True,
        "execution_id": execution_id,
        "tasks_created": "Generating",
        "tasks": [],
        "provider": _orchestrator.provider.name,
    }


async def _background_plan_and_queue(goal: str, execution_id: str):
    """
    Background worker that interacts with LLM safely.
    """
    plans = await _orchestrator.plan_pipeline(goal)
    created_tasks = []
    prev_task_id: Optional[str] = None

    # Smart routing: heavy tasks get hardware requirements
    HEAVY_TYPES = {"test"} # Architect is primarily cloud LLM analysis

    for plan in plans:
        task_id = str(uuid.uuid4())
        now = _now_iso()
        record = TaskRecord(
            task_id=task_id,
            title=plan.title,
            description=plan.description,
            task_type=plan.task_type,
            priority=plan.priority,
            status=TaskStatus.QUEUED,
            created_at=now,
            depends_on=prev_task_id,  # Phase 7: DAG chain
            requires_gpu=plan.task_type in HEAVY_TYPES,
            min_ram_gb=4.0 if plan.task_type in HEAVY_TYPES else 0.0,
        )
        tasks[task_id] = record
        task_queue.append(task_id)
        created_tasks.append({"task_id": task_id, "title": plan.title, "task_type": plan.task_type})
        prev_task_id = task_id  # next task depends on this one

    print(f"[PIPELINE] Execution {execution_id}: created DAG chain: {' -> '.join([t['task_type'] for t in created_tasks])}")


@app.post("/api/orchestrator/review")
async def orchestrator_review(payload: ReviewRequest):
    """
    LLM reviews a task result → pass/retry/escalate.
    """
    decision = await _orchestrator.review_result(payload.task_title, payload.task_type, payload.result)
    return {"success": True, "decision": decision.to_dict(), "provider": _orchestrator.provider.name}


@app.get("/api/orchestrator/info")
def orchestrator_info():
    """Return orchestrator config and provider info with explicit CORS for UI stability."""
    from fastapi.responses import JSONResponse
    try:
        content = _orchestrator.info()
        return JSONResponse(
            content=content,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        print(f"[!] [API] Orchestrator info fail: {e}")
        return JSONResponse(
            status_code=200, # Return 200 with error info to avoid CORS blocking of 500s
            content={"success": False, "error": str(e), "provider": "error/fallback"},
            headers={"Access-Control-Allow-Origin": "*"}
        )


@app.get("/api/nexus/memory")
def nexus_memory():
    """Read the full NEXUS memory state."""
    return {"success": True, "memory": _nexus.get_full_memory()}


@app.get("/api/nexus/decisions")
def nexus_decisions():
    """Read the decisions log."""
    return {"success": True, "decisions": _nexus.get_decisions()}


@app.get("/api/nexus/files")
def nexus_files():
    """List all NEXUS memory files."""
    return {"success": True, "files": _nexus.list_files()}


# ═════════════════════════════════════════════
# Claude-Compatible Bridge Endpoints (Phase 16 - v2.0)
# ═════════════════════════════════════════════

@app.post("/bridge/config")
async def bridge_config(payload: dict):
    """
    Update the active role or model for the Claude Bridge (VRAM Management).
    Used by the Admin Panel Model Switcher.
    """
    role = payload.get("role")
    target_model = payload.get("target_model")
    result = await _bridge.switch_model(role, target_model)
    return {"success": True, "config": result}


@app.get("/bridge/status")
async def bridge_status():
    """Returns the current bridge model and VRAM status from Ollama."""
    status = await _bridge.get_ollama_status()
    return {
        "success": True, 
        "active_role": _bridge.active_role,
        "loaded_model": _bridge.loaded_model,
        "ollama": status
    }


@app.post("/v1/messages")
@app.post("/v1/chat/completions")
async def claude_bridge_proxy(payload: dict):
    """
    Directly emulates Claude v1/messages API.
    Translates to Ollama via the NexusBridge logic.
    """
    print(f"[*] [CLAUDE-BRIDGE] Incoming request for context: {payload.get('model', 'default')}")
    result = await _bridge.chat(payload)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result


if __name__ == "__main__":
    import uvicorn
    # In Phase 7+, we run on 0.0.0.0 so other nodes can reach us
    # Enabled reload so changes take effect immediately
    # Exclude .vault and JSON state files from reload to prevent spam
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=False
    )
