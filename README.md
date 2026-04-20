<![CDATA[<div align="center">

# ⚙️ Neural Forge — Command Center

**Autonomous AI Software Factory**

An end-to-end orchestration platform that coordinates AI agents to architect, build, test, review, and deploy software — entirely offline, using local LLMs.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-FF6F00?style=flat-square)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 🏭 What is Neural Forge?

Neural Forge is an **autonomous software development pipeline** that treats AI agents like factory workers on a production line. You give it a goal (e.g., *"Build a Python CLI calculator"*), and a team of specialized AI agents handles the rest:

```
[Architect] → [Builder] → [Reviewer] → [Tester] → [Executor]
```

Each agent has a specific role, defined by the **AGENTS.md** contract. The pipeline enforces strict one-way flow with automatic retry and rollback capabilities.

### Key Principles

- **🔒 Fully Offline** — All LLM inference runs locally via Ollama. Zero data leaves your machine.
- **🧠 NEXUS Memory** — Persistent memory system that learns from past decisions, errors, and successes.
- **🏗️ Multi-Node Fleet** — Distribute workloads across multiple machines on your network.
- **🛡️ Workspace Isolation** — Each build runs in isolated virtual environments or Docker containers.
- **👁️ Human-in-the-Loop** — Critical pipeline stages require explicit approval via the Admin Panel.

---

## 📐 Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    ADMIN PANEL (Next.js)                      │
│         Real-time dashboard, pipeline viz, log viewer         │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST / WebSocket
┌────────────────────────▼─────────────────────────────────────┐
│              NERVE CENTER (FastAPI Backend)                    │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │Orchestr- │  │ Task Queue & │  │   NEXUS Memory        │   │
│  │ator +LLM │  │ DAG Engine   │  │   (Rules + Lessons)   │   │
│  └──────────┘  └──────────────┘  └───────────────────────┘   │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP Polling
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Node    │    │ Node    │    │ Node    │
    │ Agent 1 │    │ Agent 2 │    │ Agent N │
    │ (Python)│    │ (Python)│    │(Node.js)│
    └─────────┘    └─────────┘    └─────────┘
```

---

## 🗂️ Project Structure

```
neural-forge-command-center/
├── backend/                    # FastAPI server (Nerve Center)
│   ├── main.py                 # Core API: nodes, tasks, queue, DAG
│   ├── orchestrator.py         # LLM-powered task planning & review
│   ├── nexus.py                # NEXUS persistent memory system
│   ├── nexus_bridge.py         # Bridge for role-based model routing
│   ├── builder.py              # Builder role logic
│   └── requirements.txt        # Python dependencies
│
├── admin-panel/                # Next.js frontend dashboard
│   └── src/
│       ├── app/page.tsx        # Main dashboard UI
│       └── components/         # React components
│           ├── PipelineVisualizer.tsx
│           ├── WorkerNode.tsx
│           ├── LiveLogViewer.tsx
│           ├── ModelManager.tsx
│           └── FocusPipelineGraph.tsx
│
├── node_agent/                 # Python worker agent
│   ├── agent.py                # Heartbeat + task execution loop
│   ├── runtime.py              # Sandboxed execution (venv/Docker)
│   └── roles/                  # Role-specific execution handlers
│       ├── architect.py
│       ├── builder.py
│       ├── reviewer.py
│       ├── tester.py
│       └── executor.py
│
├── neural-forge-core/          # Node.js worker (experimental)
│   └── index.js                # JS agent with open-multi-agent lib
│
├── demo_package/               # Standalone demo (no backend needed)
│   ├── index.html              # Static dashboard mockup
│   ├── demo_server.py          # Lightweight demo API
│   └── architect_samples/      # Sample blueprint outputs
│
├── AGENTS.md                   # Pipeline contract & role definitions
├── NEURAL_FORGE_ARCHITECTURE_REPORT.md
├── start_NEXUS.bat             # Quick-start: backend
├── start_FRONTEND.bat          # Quick-start: admin panel
├── start_WORKER.bat            # Quick-start: node agent
└── .gitignore
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** with `pip`
- **Node.js 18+** with `npm`
- **Ollama** (recommended) — [Install Ollama](https://ollama.com/download)
- **Docker** (optional) — for sandboxed execution

### 1. Clone & Setup Backend

```bash
git clone https://github.com/doganaykanbur/neural-forge-command-center.git
cd neural-forge-command-center

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Pull an Ollama Model

```bash
ollama pull qwen2.5-coder:7b
```

### 3. Start the Nerve Center

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Start the Admin Panel

```bash
cd admin-panel
npm install
npm run dev
```

### 5. Launch a Node Agent

```bash
cd node_agent
pip install -r requirements.txt
python agent.py
```

The agent will auto-register with the backend and begin polling for tasks.

---

## 🎮 Usage

1. Open the **Admin Panel** at `http://localhost:3000`
2. Enter a goal in the **Cognitive Core** input (e.g., *"Build a Python REST API for user management"*)
3. Click **DISTILL** — the Orchestrator will decompose it into a pipeline
4. Watch the **DAG visualization** as agents process each stage
5. Monitor real-time logs in the **Activity Feed**

---

## 🧠 The AGENTS.md Contract

Neural Forge enforces a strict **5-stage pipeline** defined in `AGENTS.md`:

| Stage | Role | Responsibility |
|-------|------|----------------|
| 1 | **Architect** | Generates blueprints (ARCHITECTURE.md, task plans) |
| 2 | **Builder** | Writes code strictly following the blueprint |
| 3 | **Reviewer** | Static analysis: OWASP, type safety, secrets scan |
| 4 | **Tester** | Unit tests, integration tests, fuzz testing |
| 5 | **Executor** | Deploys to container with health checks |

> The Builder **never** makes autonomous decisions — it only follows the Architect's blueprint. If it detects a `BLUEPRINT_ERROR`, it halts the pipeline and requests a revision.

---

## ⚡ Key Features

### Smart Model Routing
The Orchestrator selects the optimal LLM for each task type:
- **Architect & Reviewer** → Strategic models (e.g., `mistral-nemo:12b`)
- **Builder & Tester** → Code-specialized models (e.g., `qwen2.5-coder:7b`)

### DAG Pipeline Engine
Tasks are organized as a Directed Acyclic Graph with dependency tracking. The Sweeper daemon automatically detects and recycles zombie tasks after 5 minutes of inactivity.

### Fleet Scaling
Run `python agent.py` on any machine in your network to add it to the fleet. Each agent performs a full capability probe (Docker, Ollama, GPU, disk space) and reports readiness.

### Workspace Isolation
- **venv**: Every build gets an isolated Python virtual environment
- **Docker**: Test and Execute stages run in sandboxed containers

### Antigravity Bridge
An experimental IDE integration that allows the pipeline to delegate synthesis to an IDE-based agent (e.g., Claude in VS Code), enabling hybrid local+cloud workflows.

---

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key (optional) | — |
| `MISTRAL_API_KEY` | Mistral API key (optional) | — |
| `USE_ANTIGRAVITY` | Enable IDE bridge mode | `false` |
| `NERVE_CENTER_URL` | Backend URL for agents | `http://localhost:8001` |

---

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, Pydantic, uvicorn |
| **Frontend** | Next.js 16, React 19, TailwindCSS 4, Framer Motion |
| **LLM** | Ollama (Qwen2.5-Coder, Mistral, Llama) |
| **Agent Runtime** | Custom RuntimeManager with venv/Docker isolation |
| **Node.js Worker** | open-multi-agent, systeminformation |
| **Visualization** | @xyflow/react (pipeline DAG), Lucide icons |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ⚡ by <a href="https://github.com/<your-username>">Neural Forge Team</a></sub>
</div>
]]>
