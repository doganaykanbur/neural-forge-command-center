import asyncio
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Neural Forge - Advisor Demo System")

# Enable CORS for the static HTML dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════
# Models
# ═════════════════════════════════════════════

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class TaskData(BaseModel):
    task_id: str
    title: str
    description: str
    task_type: str
    priority: int
    status: str
    assigned_to_name: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    logs: List[LogEntry] = []
    artifacts: List[dict] = []
    retry_count: int = 0
    duration_ms: int = 0

class PipelineRequest(BaseModel):
    goal: str

# ═════════════════════════════════════════════
# Mock Database State
# ═════════════════════════════════════════════

db = {
    "nodes": [
        {
            "node_id": "demo-node-1",
            "desktop_name": "PRESENTATION-PC",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "system_info": {"cpu": "Core i7", "ram": "16GB", "gpu": "RTX 3060 Mobile"},
            "live_metrics": {"cpu_percent": 12.5, "ram_percent": 45.0, "gpu_percent": 2.0, "current_task": None},
            "status": "online",
            "assigned_roles": ["architect", "build", "test", "review", "execute"],
            "autopilot_enabled": True
        }
    ],
    "tasks": {},
    "stats": {
        "nodes_total": 1,
        "nodes_online": 1,
        "tasks_total": 0,
        "tasks_queued": 0,
        "tasks_running": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
        "queue_depth": 0
    }
}

# ═════════════════════════════════════════════
# Helper Functions
# ═════════════════════════════════════════════

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _add_log(task_id: str, message: str, level: str = "info"):
    if task_id in db["tasks"]:
        db["tasks"][task_id].logs.append(LogEntry(
            timestamp=_now_iso(),
            level=level,
            message=message
        ))

# ═════════════════════════════════════════════
# Simulation Logic
# ═════════════════════════════════════════════

async def simulate_task_lifecycle(task_id: str, duration_sec: int):
    if task_id not in db["tasks"]: return
    task = db["tasks"][task_id]
    
    # Precise technical sub-steps for each task type
    SUB_STEPS = {
        "architect": [
            "Parsing user goal into technical requirements...",
            "Consulting Neural Forge domain knowledge...",
            "Synthesizing ARCHITECTURE.md blueprint...",
            "Defining TASK_PLAN.md atomic tickets...",
            "Architect review: Blueprints validated for consistency."
        ],
        "build": [
            "Reading Task ID: #SYNTH-42...",
            "Synthesizing modular components in /src...",
            "Applying SOLID principles to class structures...",
            "Generating boilerplate and core logic...",
            "Build complete: Artifacts ready for validation."
        ],
        "test": [
            "Initializing unit test environment...",
            "Running 42 automated assertions...",
            "Checking edge-case coverage (>85%)...",
            "Fuzz testing API endpoints...",
            "Test results: [42 PASS | 0 FAIL]"
        ],
        "review": [
            "Performing Deepmind strategic quality audit...",
            "Checking for architectural drift...",
            "OWASP Top 10 security scan: PASS.",
            "Reviewer Decision: GO to Deployment."
        ],
        "execute": [
            "Packaging artifacts for edge deployment...",
            "Injecting environment variables...",
            "Final health checkpoint sequence...",
            "System online: Objective complete."
        ]
    }

    await asyncio.sleep(1)
    task.status = "running"
    task.assigned_to_name = "PRESENTATION-PC"
    db["stats"]["tasks_running"] += 1
    db["stats"]["tasks_queued"] = max(0, db["stats"]["tasks_queued"] - 1)
    
    steps = SUB_STEPS.get(task.task_type, ["Processing...", "Validating...", "Finishing..."])
    for step in steps:
        await asyncio.sleep(duration_sec / len(steps))
        _add_log(task_id, f"[SYNC] {step}")

    task.status = "completed"
    task.completed_at = _now_iso()
    task.duration_ms = duration_sec * 1000
    db["stats"]["tasks_running"] = max(0, db["stats"]["tasks_running"] - 1)
    db["stats"]["tasks_completed"] += 1
    _add_log(task_id, f"PHASE [PASSED]: {task.task_type.upper()} verification successful.", "success")

async def run_pipeline_demo(goal: str):
    STAGES = [
        ("architect", f"Architecture Blueprint: {goal}"),
        ("build", f"Code Synthesis: Core Logic"),
        ("test", f"Validation: Unit Tests"),
        ("review", f"Quality Audit: Static Analysis"),
        ("execute", f"Deployment: production-v1")
    ]
    
    for t_type, title in STAGES:
        task_id = str(uuid.uuid4())
        task = TaskData(
            task_id=task_id,
            title=title,
            description=f"Demo task: {goal}",
            task_type=t_type,
            priority=5,
            status="queued",
            created_at=_now_iso()
        )
        db["tasks"][task_id] = task
        db["stats"]["tasks_total"] += 1
        db["stats"]["tasks_queued"] += 1
        
        durations = {"architect": 3, "build": 6, "test": 4, "review": 3, "execute": 2}
        await simulate_task_lifecycle(task_id, duration_sec=durations.get(t_type, 4))
        await asyncio.sleep(0.5)

# ═════════════════════════════════════════════
# API Endpoints
# ═════════════════════════════════════════════

@app.get("/api/nodes")
def get_nodes():
    return db["nodes"]

@app.get("/api/tasks")
def get_tasks():
    return sorted(db["tasks"].values(), key=lambda x: x.created_at, reverse=True)

@app.post("/api/orchestrator/pipeline/execute")
async def start_demo_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline_demo, req.goal)
    return {"success": True, "message": "Pipeline initiated."}

@app.delete("/api/tasks")
def clear_tasks():
    db["tasks"] = {}
    db["stats"].update({"tasks_total": 0, "tasks_queued": 0, "tasks_running": 0, "tasks_completed": 0, "tasks_failed": 0})
    return {"success": True}

# --- Mock Routes for 1:1 Parity ---

@app.get("/api/orchestrator/info")
def get_orch_info():
    return {"success": True, "provider": "Neural Forge Brain (Demo)", "model": "mistral-nemo:12b"}

@app.get("/api/orchestrator/usage")
def get_orch_usage():
    return {
        "global": {
            "total_tokens": 124500, "token_limit": 1000000,
            "models": {"mistral-nemo:12b": {"total": 124500}}
        }
    }

@app.get("/api/nexus/decisions")
def get_nexus_decisions():
    return {"success": True, "decisions": "DECISION[DEMO]: Optimized architecture for presentation. Safety audit: PASS."}

@app.get("/api/dashboard")
def get_dashboard_full():
    return db["stats"]

@app.get("/api/settings")
def get_settings():
    return {"use_docker": True, "autopilot_global": True}

@app.get("/api/stats")
def get_stats():
    return db["stats"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
