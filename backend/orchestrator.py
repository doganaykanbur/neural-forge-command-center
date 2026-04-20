"""
Neural Forge — LLM Orchestrator
Provider-agnostic AI orchestrator with Mistral/Ollama/Mock backends.
Analyzes tasks, plans pipelines, reviews results, and learns from decisions.
"""

import os
import json
import time
import re
import requests
import asyncio
import httpx
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from nexus import NexusMemory

# ═════════════════════════════════════════════
# Data Structures
# ═════════════════════════════════════════════


class TaskPlan:
    """Structured output from task analysis."""
    def __init__(
        self,
        task_type: str,
        priority: int,
        title: str,
        description: str = "",
        estimated_seconds: int = 30,
        rationale: str = "",
        subtasks: list[dict] | None = None,
        can_be_parallel: bool = False,
    ):
        self.task_type = task_type
        self.priority = priority
        self.title = title
        self.description = description
        self.estimated_seconds = estimated_seconds
        self.rationale = rationale
        self.subtasks = subtasks or []
        self.can_be_parallel = can_be_parallel

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "estimated_seconds": self.estimated_seconds,
            "rationale": self.rationale,
            "subtasks": self.subtasks,
            "can_be_parallel": self.can_be_parallel,
        }


class ReviewDecision:
    """Output from result review."""
    def __init__(self, verdict: str, feedback: str = "", retry: bool = False):
        self.verdict = verdict  # "pass", "retry", "escalate"
        self.feedback = feedback
        self.retry = retry

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "feedback": self.feedback, "retry": self.retry}


# ═════════════════════════════════════════════
# LLM Provider Abstraction
# ═════════════════════════════════════════════


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "", temperature: float = 0.3) -> tuple[str, dict]:
        """Send prompt to LLM and return (response_text, usage_dict)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class MistralProvider(LLMProvider):
    """Mistral AI API provider."""

    def __init__(self, api_key: str, model: str = "mistral-small-latest"):
        self.api_key = api_key
        self.model = model

    @property
    def name(self) -> str:
        return f"mistral/{self.model}"

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.3) -> tuple[str, dict]:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": messages, "temperature": temperature},
                    timeout=httpx.Timeout(30.0, connect=60.0),
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return text, usage
        except Exception as e:
            return f"[Mistral API error: {e}]", {}


class OllamaProvider(LLMProvider):
    """Local Ollama provider."""

    def __init__(self, model: str = "mistral:latest", url: str = "http://localhost:11434"):
        self.model = model
        self.url = url

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.3) -> tuple[str, dict]:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": temperature},
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.url}/api/generate", json=payload, timeout=httpx.Timeout(60.0, connect=60.0))
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "")
                return text, {}
        except Exception as e:
            return f"[Ollama error: {e}]", {}




class AntigravityProvider(LLMProvider):
    """Bridge provider that delegates synthesis to the IDE Agent via files."""

    def __init__(self, nexus_dir: Path):
        # 1. Respect the passed dir
        self.nexus_dir = nexus_dir
        
        # 2. Hardcoded fallback for isolated environments (Neural Forge Root)
        NF_ROOT = Path(r"c:\Users\doganay\.gemini\antigravity\scratch\neural_forge_command_center\.nexus\rules")
        if not self.nexus_dir.exists() and NF_ROOT.exists():
            self.nexus_dir = NF_ROOT

        self.request_file = self.nexus_dir / "ANTIGRAVITY_REQUEST.json"
        self.response_file = self.nexus_dir / "ANTIGRAVITY_RESPONSE.json"

    @property
    def name(self) -> str:
        return "antigravity/ide-bridge"

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.3) -> tuple[str, dict]:
        """Write request and wait for the agent to respond asynchronously."""
        try:
            # Ensure directory exists
            self.nexus_dir.mkdir(parents=True, exist_ok=True)

            # Clean up old response
            if self.response_file.exists():
                self.response_file.unlink()

            # Write request
            payload = {
                "task_id": "ide-" + str(int(time.time())),
                "prompt": prompt,
                "system": system,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            print(f"DEBUG: Writing request to: {self.request_file.absolute()}")
            self.request_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"[*] [ANTIGRAVITY] Request written to {self.request_file.name}. Waiting for agent...")

            # Poll for response (max 120 seconds for web safety during chat)
            start_time = time.time()
            while time.time() - start_time < 120:
                if self.response_file.exists():
                    try:
                        data = json.loads(self.response_file.read_text(encoding="utf-8"))
                        text = data.get("text", "")
                        usage = data.get("usage", {"total_tokens": 0})
                        # Cleanup
                        self.request_file.unlink(missing_ok=True)
                        self.response_file.unlink(missing_ok=True)
                        return text, usage
                    except json.JSONDecodeError:
                        pass # Wait for file to be fully written
                
                # Non-blocking await for the sync bridge
                await asyncio.sleep(2)
            
            return "[Error: Antigravity Agent did not respond within 120s]", {}
        except Exception as e:
            return f"[Antigravity Bridge Error: {e}]", {}


class UsageTracker:
    """Persistent token usage tracking, now node-aware."""
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path / "usage.json"
        self.stats = self._load()

    def _get_defaults(self) -> dict:
        return {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "token_limit": 1000000,
            "models": {}
        }

    def _load(self) -> dict:
        root_defaults = {
            "global": self._get_defaults(),
            "nodes": {} # node_id -> stats
        }
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                # Migration: if it's the old flat structure, move it to "global"
                if "total_tokens" in data and "global" not in data:
                    return {"global": data, "nodes": {}}
                
                # Merge missing root keys
                for k, v in root_defaults.items():
                    if k not in data:
                        data[k] = v
                return data
            except Exception:
                pass
        return root_defaults

    def get_node_stats(self, node_id: str) -> dict:
        if node_id not in self.stats["nodes"]:
            self.stats["nodes"][node_id] = self._get_defaults()
        return self.stats["nodes"][node_id]

    def record(self, node_id: str | None, model_name: str, usage: dict):
        if not usage: return
        
        # Update Global
        self._update_dict(self.stats["global"], model_name, usage)
        
        # Update Node-specific if provided
        if node_id:
            node_stats = self.get_node_stats(node_id)
            self._update_dict(node_stats, model_name, usage)
        
        self._save()

    def _update_dict(self, d: dict, model_name: str, usage: dict):
        d["total_prompt_tokens"] += usage.get("prompt_tokens", 0)
        d["total_completion_tokens"] += usage.get("completion_tokens", 0)
        d["total_tokens"] += usage.get("total_tokens", 0)
        
        if "models" not in d: d["models"] = {}
        if model_name not in d["models"]:
            d["models"][model_name] = {"prompt": 0, "completion": 0, "total": 0}
            
        m = d["models"][model_name]
        m["prompt"] += usage.get("prompt_tokens", 0)
        m["completion"] += usage.get("completion_tokens", 0)
        m["total"] += usage.get("total_tokens", 0)

    def _save(self):
        try:
            self.storage_path.write_text(json.dumps(self.stats, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] Failed to save usage: {e}")


class MockProvider(LLMProvider):
    """Fallback mock provider for logic testing."""

    @property
    def name(self) -> str:
        return "mock/rule-engine"

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.3) -> tuple[str, dict]:
        # Realistic mock for a calculator if that's the goal
        if "calculator" in prompt.lower():
             return """import tkinter as tk
from tkinter import messagebox

class MinecraftCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("MINECRAFT CALCULATOR")
        self.root.geometry("300x400")
        self.root.configure(bg="#3c3c3c") # Minecraft Gray
        
        self.result_var = tk.StringVar()
        self.entry = tk.Entry(root, textvariable=self.result_var, font=("Courier", 24), bg="#1e1e1e", fg="#3fb33f", bd=10, insertwidth=4, width=14, borderwidth=4)
        self.entry.grid(row=0, column=0, columnspan=4, pady=20)
        
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            'C', '0', '=', '+'
        ]
        
        row = 1
        col = 0
        for button in buttons:
            action = lambda x=button: self.on_button_click(x)
            tk.Button(root, text=button, width=5, height=2, font=("Courier", 14), bg="#5a5a5a", fg="white", command=action).grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def on_button_click(self, char):
        if char == '=':
            try:
                self.result_var.set(eval(self.result_var.get()))
            except:
                messagebox.showerror("Error", "Invalid Input")
        elif char == 'C':
            self.result_var.set("")
        else:
            self.result_var.set(self.result_var.get() + str(char))

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftCalculator(root)
    root.mainloop()
""", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return '{"task_type": "build", "priority": 3, "rationale": "Mock response"}', {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


# ═════════════════════════════════════════════
# Orchestrator
# ═════════════════════════════════════════════


class Orchestrator:
    """
    AI-powered task orchestrator.
    Uses LLM (or mock rules) + NEXUS memory for intelligent task management.
    """

    # Keywords for mock task classification
    TYPE_KEYWORDS = {
        "review": ["review", "check", "lint", "analyze", "quality", "audit", "inspect", "static"],
        "build": ["build", "compile", "install", "deploy", "package", "setup", "create", "scaffold"],
        "test": ["test", "verify", "validate", "assert", "unittest", "pytest", "spec", "qa"],
        "execute": ["run", "execute", "start", "launch", "script", "compute", "process"],
    }

    PRIORITY_KEYWORDS = {
        5: ["critical", "urgent", "asap", "hotfix", "emergency", "blocker"],
        4: ["important", "high", "security", "production", "breaking"],
        3: ["normal", "standard", "feature", "enhancement"],
        2: ["low", "minor", "cosmetic", "refactor"],
        1: ["trivial", "documentation", "comment", "typo"],
    }

    def __init__(self, nexus: NexusMemory | None = None):
        self.nexus = nexus or NexusMemory()
        self.usage_tracker = UsageTracker(self.nexus.nexus_dir)
        # Global fallback provider
        self.default_provider = self._auto_detect_provider()
        self.is_mock = isinstance(self.default_provider, MockProvider)

    @property
    def provider(self) -> LLMProvider:
        """Alias for the core/default provider."""
        return self.default_provider

    def get_provider(self, task_type: str | None = None) -> LLMProvider:
        """Get the best provider for a specific task type (Neural Forge v2.0)."""
        if self.is_mock:
            return self.default_provider
            
        # Neural Forge v2.0 Role-to-Brain Mapping
        # Architect & Reviewer -> mistral-nemo:12b (Strategic Logic)
        # Build & Test -> qwen2.5-coder:7b (Coding Expert)
        
        if task_type in ("architect", "review"):
            return OllamaProvider(model="qwen2.5-coder:7b")
        elif task_type in ("build", "test"):
            return OllamaProvider(model="qwen2.5-coder:7b")
        
        return self.default_provider

    def _auto_detect_provider(self) -> LLMProvider:
        """
        Auto-detect the best available LLM provider.
        Prioritizes: Antigravity (IDE) -> Mock.
        """
        if os.environ.get("USE_ANTIGRAVITY") == "true":
            return AntigravityProvider(self.nexus.nexus_dir)

        # Fallback to local Ollama if available
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=1.0)
            if resp.status_code == 200:
                print("[*] Falling back to local Ollama (Mistral)")
                return OllamaProvider(model="qwen2.5-coder:7b")
        except Exception:
            pass

        return MockProvider()

    # ─── Core Methods ────────────────────────────

    async def analyze_task(self, description: str) -> TaskPlan:
        """
        Analyze a task description and return a structured plan.
        """
        if self.is_mock:
            return self._mock_analyze(description)

        context = self.nexus.get_context("general")
        prompt = f"""Analyze this task and return a JSON object with these fields:
- task_type: one of "review", "build", "test", "execute"
- priority: integer 1-5 (5=critical)
- title: short title for the task
- estimated_seconds: estimated execution time
- rationale: why you chose this classification

Context from NEXUS memory:
{context}

Task description:
{description}

Respond with ONLY valid JSON."""

        provider = self.get_provider(plan.task_type if 'plan' in locals() else None)
        response, usage = await provider.complete(prompt, system=self.nexus.get_core())
        self.usage_tracker.record(None, provider.name, usage)
        
        plan = self._parse_plan_response(response, description)

        # Stop Hook: log the decision
        self.nexus.record_decision(
            f"Analyzed task as '{plan.task_type}' (P{plan.priority}): {plan.title}",
            plan.rationale
        )
        return plan

    async def plan_pipeline(self, goal: str) -> list[TaskPlan]:
        """
        Break a complex goal into an ordered sequence of subtasks.
        """
        if self.is_mock:
            return self._mock_pipeline(goal)

        context = self.nexus.get_context("build")
        prompt = f"""Break this goal into an ordered pipeline of subtasks.
Return a JSON array where each item has: task_type, priority, title, description, estimated_seconds, can_be_parallel.

- ARCHITECT-FIRST RULE: Every pipeline MUST start with an 'architect' task to generate the AGENTS.md/TASK_PLAN/ARCHITECTURE/RULES blueprints. No 'build' task should exist without an 'architect' parent.
- PARALLELISM IS YOUR SUPERPOWER. Workers are async. Launch independent workers concurrently whenever possible (can_be_parallel: true).
- Independent tasks like "Research module A" and "Research module B" or "Verify UI" and "Verify API" should be parallel.
- Write-heavy tasks (implementation) should usually be sequential (can_be_parallel: false) per file set.
- SYNTHESIS: Every prompt you write for a subtask must be self-contained. Include file paths, line numbers, and exact technical specs. 
- Never say "based on previous research" - provide the research findings directly in the subtask description.

Goal: {goal}

Context:
{context}

Respond ONLY with a valid JSON array of TaskPlan objects."""

        provider = self.get_provider("architect")
        response, usage = await provider.complete(prompt, system=self.nexus.get_core())
        self.usage_tracker.record(None, provider.name, usage)
        plans = self._parse_pipeline_response(response, goal)

        # Stop Hook
        titles = [p.title for p in plans]
        self.nexus.record_decision(
            f"Planned pipeline ({len(plans)} tasks) for: {goal[:80]}",
            f"Subtasks: {', '.join(titles)}"
        )
        return plans

    async def review_result(self, task_title: str, task_type: str, result: dict) -> ReviewDecision:
        """
        Review a task result and decide: pass, retry, or escalate.
        """
        if self.is_mock:
            return self._mock_review(task_title, task_type, result)

        context = self.nexus.get_context("review")
        prompt = f"""Review this task result and decide: "pass", "retry", or "escalate".
Return JSON with: verdict, feedback, retry (boolean).

### CRITICAL SUCCESS CRITERIA:
1.  **Differentiate Goals**: This is a {task_type} task. DO NOT give a "pass" just because the old blueprints (ARCHITECTURE.md, TASK_PLAN.md, RULES.md) exist.
2.  **Verify New Work**: If the task was "Install dependencies", check the Result for logs like "Successfully installed" or a "requirements.txt" change.
3.  **Detect No-Ops**: If the task was meant to "Build" or "Code" something and the Result shows NO new files or code changes, it is a FAIL (retry).
4.  **Check Output**: Analyze the provided logs for errors or successful completion indicators.

Context:
{context}

Task: {task_title} (type: {task_type})
Result: {json.dumps(result, indent=2)}

Respond with ONLY valid JSON."""

        provider = self.get_provider("review")
        response, usage = await provider.complete(prompt, system=self.nexus.get_core())
        self.usage_tracker.record(None, provider.name, usage)
        decision = self._parse_review_response(response, result)

        # Phase 11/12: Memory Consolidation
        if decision.verdict == "pass":
            await self.consolidate_memory(task_title, result)

        # Enforce Security Stop Hook: if result explicitly flagged a violation, override LLM
        if result.get("security_violation"):
            report = result.get("report", "Unknown security vulnerability detected.")
            self.nexus.record_threat(f"Task '{task_title}' reported: {report}")
            decision.verdict = "escalate"
            decision.feedback = f"SECURITY VIOLATION DETECTED. Pipeline Halted. Threat recorded to memory: {report}"
            decision.retry = False

        # Stop Hook
        self.nexus.record_decision(
            f"Reviewed '{task_title}' → {decision.verdict}",
            decision.feedback
        )
        return decision

    # ─── Mock Implementations ────────────────────

    def _mock_analyze(self, description: str) -> TaskPlan:
        """Rule-based task analysis using keyword matching."""
        desc_lower = description.lower()

        # Classify task type
        task_type = "build"  # default
        max_score = 0
        for ttype, keywords in self.TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in desc_lower)
            if score > max_score:
                max_score = score
                task_type = ttype

        # Classify priority
        priority = 3  # default
        for prio, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                priority = prio
                break

        # Generate title
        words = description.split()[:8]
        title = " ".join(words)
        if len(description) > 50:
            title = title + "..."

        # Estimate time
        time_map = {"review": 15, "build": 45, "test": 30, "execute": 20}
        estimated = time_map.get(task_type, 30)

        plan = TaskPlan(
            task_type=task_type,
            priority=priority,
            title=title,
            description=description,
            estimated_seconds=estimated,
            rationale=f"Mock analysis: matched '{task_type}' keywords ({max_score} hits), priority {priority}",
        )

        self.nexus.record_decision(
            f"[MOCK] Analyzed as '{task_type}' (P{priority}): {title}",
            f"Keyword matching ({max_score} hits)"
        )
        return plan

    def _mock_pipeline(self, goal: str) -> list[TaskPlan]:
        """Rule-based pipeline generation."""
        goal_lower = goal.lower()
        plans = []

        # Always start with architect (Enforced for v2.3 blueprints)
        plans.append(TaskPlan(
            task_type="architect",
            priority=5,
            title=f"Architect Blueprinting: {goal[:40]}",
            description=f"Synthesize high-fidelity multi-file blueprints (TASK_PLAN, ARCHITECTURE, RULES) for: {goal}",
            estimated_seconds=20,
            rationale="Phase 4.1: Production line starts with strategic architecture files.",
        ))

        # Build step
        plans.append(TaskPlan(
            task_type="build",
            priority=5,
            title=f"Build: {goal[:40]}",
            description=f"Build and install dependencies for: {goal}",
            estimated_seconds=45,
            rationale="Build is the core step",
        ))

        # Followed by review
        if any(kw in goal_lower for kw in ["code", "app", "api", "service", "module", "function"]):
            plans.append(TaskPlan(
                task_type="review",
                priority=4,
                title=f"Review: {goal[:40]}",
                description=f"Static analysis of code for: {goal}",
                estimated_seconds=15,
                rationale="Review code according to AGENTS.md",
            ))

        # Test step
        plans.append(TaskPlan(
            task_type="test",
            priority=4,
            title=f"Test: {goal[:40]}",
            description=f"Run tests for: {goal}",
            estimated_seconds=30,
            rationale="Verify correctness after build",
        ))

        # Execute if deployment-related
        if any(kw in goal_lower for kw in ["deploy", "run", "launch", "start", "execute"]):
            plans.append(TaskPlan(
                task_type="execute",
                priority=3,
                title=f"Execute: {goal[:40]}",
                description=f"Run and verify: {goal}",
                estimated_seconds=20,
                rationale="Final execution step",
            ))

        self.nexus.record_decision(
            f"[MOCK] Planned {len(plans)}-step pipeline for: {goal[:60]}",
            "Rule-based pipeline generation"
        )
        return plans

    def _mock_review(self, task_title: str, task_type: str, result: dict) -> ReviewDecision:
        """Rule-based result review."""
        status = result.get("status", "")
        exit_code = result.get("exit_code", None)
        error = result.get("error", "")

        if status in ("success", "all_passed", "pass") or exit_code == 0:
            decision = ReviewDecision(
                verdict="pass",
                feedback=f"Task '{task_title}' completed successfully. Output looks valid.",
                retry=False,
            )
        elif status in ("some_failed",) or (exit_code is not None and exit_code != 0):
            decision = ReviewDecision(
                verdict="retry",
                feedback=f"Task '{task_title}' had failures. Recommend retry with fixes.",
                retry=True,
            )
        elif error:
            decision = ReviewDecision(
                verdict="escalate",
                feedback=f"Task '{task_title}' encountered error: {error[:200]}. Needs human review.",
                retry=False,
            )
        else:
            decision = ReviewDecision(
                verdict="pass",
                feedback=f"Task '{task_title}' result appears acceptable.",
                retry=False,
            )

        # Enforce Security Stop Hook in Mock as well
        if result.get("security_violation"):
            report = result.get("report", "Unknown security vulnerability detected.")
            self.nexus.record_threat(f"Task '{task_title}' reported: {report}")
            decision = ReviewDecision(
                verdict="escalate",
                feedback=f"SECURITY VIOLATION DETECTED. Pipeline Halted. Threat recorded to memory: {report}",
                retry=False,
            )

        self.nexus.record_decision(
            f"[MOCK] Reviewed '{task_title}' → {decision.verdict}",
            decision.feedback[:100]
        )
        return decision

    # ─── Response Parsers ────────────────────────

    def _extract_and_save_memory(self, data: dict | list):
        """Extract 'update_memory' from JSON dict and save it."""
        # If it's a list (from plan_pipeline), check each item
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "update_memory" in item:
                    self._extract_and_save_memory(item)
            return

        if isinstance(data, dict) and "update_memory" in data:
            mem = data["update_memory"]
            target_file = mem.get("file")
            content = mem.get("content")
            if target_file and content:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                self.nexus._append_file(target_file, f"- [{now} MID-SESSION] {content}")
                self.nexus.record_decision(f"Stop Hook: Auto-updated {target_file}", content[:100])

    def _parse_plan_response(self, response: str, description: str) -> TaskPlan:
        """Parse LLM response into TaskPlan (or list), with fallback."""
        try:
            # Faz 3: LLM RAW LOGGING
            print(f"\n[ORCHESTRATOR-RAW] >>>\n{response}\n<<< [/ORCHESTRATOR-RAW]\n")

            # Handle both JSON array and single JSON object
            match = re.search(r'[\[\{].*[\]\}]', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                # If it's a list, we either need a specialized list parser or we pick the first
                if isinstance(data, list):
                    self._extract_and_save_memory(data)
                    if not data: return TaskPlan(task_type="build", priority=3, title=description[:50], description=description)
                    item = data[0]
                    return TaskPlan(
                        task_type=item.get("task_type", "build"),
                        priority=item.get("priority", 3),
                        title=item.get("title", description[:50]),
                        description=item.get("description", description),
                        estimated_seconds=item.get("estimated_seconds", 60),
                        rationale=item.get("rationale", "Followed LLM plan list"),
                        can_be_parallel=item.get("can_be_parallel", False)
                    )

                self._extract_and_save_memory(data)
                return TaskPlan(
                    task_type=data.get("task_type", "build"),
                    priority=data.get("priority", 3),
                    title=data.get("title", description[:50]),
                    description=description,
                    estimated_seconds=data.get("estimated_seconds", 30),
                    rationale=data.get("rationale", "LLM analysis"),
                )
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[!] [ORCHESTRATOR] JSON Parse Error: {e}")
            pass
        # Fallback to mock
        return self._mock_analyze(description)

    def _parse_pipeline_response(self, response: str, goal: str) -> list[TaskPlan]:
        """Parse LLM response into list of TaskPlans, with fallback."""
        try:
            # Faz 3: LLM RAW LOGGING
            if "[ORCHESTRATOR-RAW]" not in response: # Prevent double logging if already logged
                 print(f"\n[ORCHESTRATOR-PIPELINE-RAW] >>>\n{response}\n<<< [/ORCHESTRATOR-PIPELINE-RAW]\n")

            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                self._extract_and_save_memory(data)
                return [
                    TaskPlan(
                        task_type=item.get("task_type", "build"),
                        priority=item.get("priority", 3),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        estimated_seconds=item.get("estimated_seconds", 30),
                    )
                    for item in data
                ]
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[!] [ORCHESTRATOR] Pipeline JSON Error: {e}")
            pass
        return self._mock_pipeline(goal)

    def _parse_review_response(self, response: str, result: dict) -> ReviewDecision:
        """Parse LLM response into ReviewDecision."""
        try:
            # Faz 3: LLM RAW LOGGING
            print(f"\n[ORCHESTRATOR-REVIEW-RAW] >>>\n{response}\n<<< [/ORCHESTRATOR-REVIEW-RAW]\n")

            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return ReviewDecision(
                    verdict=data.get("verdict", "pass"),
                    feedback=data.get("feedback", ""),
                    retry=data.get("retry", False),
                )
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[!] [ORCHESTRATOR] Review JSON Error: {e}")
            pass
        return ReviewDecision(verdict="pass", feedback="Fallback pass")

    async def consolidate_memory(self, task_title: str, result: dict) -> None:
        """
        Analyze a successful task result and extract lessons for NEXUS.
        """
        if self.is_mock:
            return

        prompt = f"""Analyze the outcome of this task: "{task_title}".
Identify any reusable patterns, coding standards, or lessons learned that should be stored in the Corporate Memory.
Format your response as a single concise bullet point starting with "LESSON:".

Task Result:
{json.dumps(result, indent=2)}
"""
        response, usage = await self.provider.complete(prompt, system="You are the Neural Forge Corporate Memory Distiller.")
        self.usage_tracker.record(None, self.provider.name, usage)
        
        match = re.search(r"LESSON:\s*(.*)", response, re.IGNORECASE)
        if match:
            lesson = match.group(1).strip()
            # Default to preferences.md for general lessons
            self.nexus.record_lesson(lesson, "preferences.md")
            print(f"[Orchestrator] Consolidated memory: {lesson}")

    # ─── Info ────────────────────────────────────

    def info(self) -> dict:
        """Return orchestrator configuration info."""
        return {
            "provider": self.default_provider.name,
            "is_mock": self.is_mock,
            "nexus_dir": str(self.nexus.nexus_dir),
            "memory_files": self.nexus.list_files(),
        }

    # ─── Code Generation & Synthesis ────────────────

    async def generate_code(self, goal: str, blueprint: str = "", task_type: str = "build") -> str:
        """
        High-quality code generation for the Builder or Architect roles.
        If task_type is 'architect', it forces the use of Ollama for strategic design.
        """
        # Enforce User Preference: Architect tasks must use Ollama
        provider = self.provider
        if task_type == "architect":
            # Force detect/use Ollama if available
            try:
                # Try to use a dedicated Ollama instance for architect tasks
                # Using a local instance for the strategic design documentation
                from .orchestrator import OllamaProvider
                provider = OllamaProvider(model="mistral:latest")
                print(f"[*] [ORCHESTRATOR] Routing Architect task to {provider.name}")
            except Exception:
                 # If local import or initialization fails, fallback to current
                print(f"[WARN] Ollama not found for Architect task, falling back to {provider.name}")

        if task_type == "architect":
            system = "You are the Lead Project Architect. Your goal is to design a high-quality, secure, and modular project structure."
            prompt = f"""Generate a comprehensive set of project-level documentation files for this goal: {goal}
            
            You MUST return a JSON object with a 'files' key. Each key in 'files' is a filename, and the value is the content.
            Required files:
            1. AGENTS.md: Technical contract, dependencies, and build/test commands.
            2. SECURITY.md: Risk assessment, zero-trust rules, and error handling standards.
            3. CLAUDE.md (or ARCHITECTURE.md): Folder structure, module boundaries, and type definitions.

            Return ONLY valid JSON in this format:
            {{
              "files": {{
                "AGENTS.md": "...",
                "SECURITY.md": "...",
                "ARCHITECTURE.md": "..."
              }}
            }}
            """
        else:
            system = "You are an expert software developer. Write clean, modular, and optimized code."
            prompt = f"""Generate the complete implementation for this goal: {goal}
            
            Strictly follow this architectural blueprint:
            {blueprint}
            
            Requirements:
            - Write the full code into a single file if possible.
            - Include all necessary imports.
            - Add a # FILE: filename.ext comment at the very top.
            - Follow the standards in AGENTS.md and SECURITY.md if provided.
            """

        response, usage = await provider.complete(prompt, system=system, temperature=0.2)
        self.usage_tracker.record(None, provider.name, usage)
        
        # If it's an architect task, we want the raw JSON for the worker to parse
        return response
