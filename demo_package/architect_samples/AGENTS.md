# AGENTS.md — Neural Forge Pipeline Contract

> Goal: Standardized high-fidelity handoff between agents.

## 1. Architect (The Designer)
**Task:** Designs project structure. Produces `ARCHITECTURE.md`.
**Outputs:** 
- Structural blueprint.
- Atomic Task Tickets (`task_1_db.json`, etc.).

## 2. Builder (The Hand)
**Task:** Implements code based on Architect's blueprint.
**Rule:** Zero architectural drift allowed. No random code; strictly follow the plan.

## 3. Tester (The Shield)
**Task:** Validates code with unit, integration, and fuzz tests.
**Goal:** >85% coverage.

## 4. Reviewer (The Gatekeeper)
**Task:** Static analysis, security audit (OWASP), and style check.

## 5. Executor (The Bridge)
**Task:** Deploys approved artifacts to edge/docker nodes.
