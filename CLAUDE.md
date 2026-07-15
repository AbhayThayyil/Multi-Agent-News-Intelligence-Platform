# CLAUDE.md

This file governs how Claude Code should operate inside this repository. It is derived from `PROJECT_CONTEXT.md` — read that file for the full vision and reasoning; this file is the condensed, actionable ruleset.

---

## Role

Act as a **senior software engineer collaborating with the user**, not an autonomous code generator. The user is learning system design and AI engineering through this project — the goal is understanding, not throughput.

---

## Working Agreement (non-negotiable)

1. **Do not write implementation code until the approach has been discussed and explicitly approved.** Docs, scaffolding discussions, and design come first.
2. Workflow for every feature:
   1. Understand the concept.
   2. Discuss and approve the architecture.
   3. Design the solution.
   4. Implement — only once the design is approved.
   5. User reviews every generated file.
   6. Refactor where necessary.
   7. Document what was learned (`LEARNING_JOURNAL.md`).
3. **Never produce code that can't be explained.** If asked "why does this line exist," there must be a real answer.
4. When scope or design is ambiguous, ask — don't assume.

---

## Architecture Rules

- **Layering:** API (no business logic) → AI/Agents (reasoning) → Tools (I/O only, no reasoning) → Services (deterministic logic) → Persistence → Infrastructure.
- **Orchestration:** LangGraph owns workflow execution. The Planner Agent produces an execution plan; LangGraph routes between agent nodes based on that plan. Agents do not call or orchestrate other agents directly.
- **Tools never reason.** They only communicate with external systems (RSS, web search, etc.).
- **Deterministic code first.** Use plain Python for anything that doesn't require reasoning (formatting, validation, retries, sorting, parsing). Reach for an LLM only when reasoning is actually required.
- **Dependency Injection** throughout the backend — components receive dependencies, they don't construct them internally.
- **Pydantic** defines all request/response contracts.

---

## Current Scope — Sprint 1: Project Bootstrap

Building now:
- Repository structure
- FastAPI scaffold
- React scaffold
- Docker
- Health endpoint
- React ↔ FastAPI communication

Explicitly **not yet**: business logic, PostgreSQL, Redis, persistence, conversation memory, RAG, streaming, and any agent beyond Planner / Information Retrieval / Summarizer.

---

## Avoid Over-Engineering

Add a new agent, tool, or infrastructure component only when a real, current requirement justifies it. Everything in `PROJECT_CONTEXT.md`'s Future Roadmap (Timeline Agent, Comparison Agent, Fact Checker, Bias Detection, RAG, Memory, Vector Search, Streaming, Evaluation, Monitoring, etc.) is deferred until then — and gets an ADR when it's actually introduced.

---

## Folder Structure

```text
backend/
    app/
        api/        # HTTP layer — no business logic
        agents/     # AI nodes — Planner, Summarizer (reasoning)
        graph/      # LangGraph state + workflow wiring
        tools/      # External I/O — no reasoning
        prompts/
        services/   # Deterministic nodes/logic — Retrieval, Response Composer
        schemas/    # Pydantic contracts
        models/
        config/
frontend/
docs/
```

Node classification (AI / Deterministic / Hybrid — see [`ADR 0001`](docs/ADR/0001-langgraph-execution-engine.md)) determines the folder: `agents/` for reasoning, `services/` for deterministic logic, regardless of a node's role in the graph.

---

## Tech Stack

**Current:** FastAPI, LangGraph, LiteLLM, React, Docker
**Future (not wired up yet):** PostgreSQL, Redis

---

## Documentation Map

- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — vision, philosophy, architecture reasoning (read first)
- [`docs/PRD.md`](docs/PRD.md) — product requirements
- [`docs/HLD.md`](docs/HLD.md) — high-level design
- [`docs/LLD.md`](docs/LLD.md) — low-level design
- [`docs/ADR/`](docs/ADR) — architecture decision records
- [`LEARNING_JOURNAL.md`](LEARNING_JOURNAL.md) — what was learned, sprint by sprint

---

## Commands

No build, test, or lint commands yet — Sprint 1 scaffolding hasn't been implemented. This section gets filled in once the FastAPI and React scaffolds exist.
