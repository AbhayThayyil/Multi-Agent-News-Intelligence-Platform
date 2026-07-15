# ADR 0001: LangGraph as Execution Engine, with a Mock-First Sprint

## Status

Accepted — 2026-07-13

## Context

Sprint 1 built the project's scaffolding (FastAPI, React, Docker) but introduced no orchestration at all. Per `PROJECT_CONTEXT.md`, the architecture calls for LangGraph to own workflow execution, with the Planner Agent producing an execution plan that LangGraph routes between agent nodes — agents never call each other directly.

Sprint 2 is the first sprint to actually introduce LangGraph. Before writing any real AI or tool logic, we need confidence that the orchestration layer itself — state passing, node sequencing, conditional plans — works correctly. If real components (an LLM call, an RSS fetch) are wired in from the start and something breaks, it's ambiguous whether the graph, the prompt, the API key, or the network call is at fault.

## Decision

**1. Classify every node by whether it reasons:**

- **AI nodes** (need an LLM call): Planner, Summarizer.
- **Deterministic nodes** (plain Python, no reasoning): Retrieval, Response Composer.
- **Hybrid nodes** (future — combine deterministic logic with an LLM call): Timeline, Trend Analysis, Fact Checker, Deduplication. Not built in Sprint 2.

This mirrors the layering already in `PROJECT_CONTEXT.md` (Tools/Services never reason; the AI layer does) but applies it specifically to LangGraph node design.

**2. The Planner plans; it does not execute.** A node's only job is to read state and write to it. The Planner writes `execution_plan` (a list of node names to run); LangGraph — not the Planner — routes execution based on that list. Changing what a query needs (e.g. adding a timeline) means the Planner returns a different list, not a rewritten graph.

**3. Sprint 2 mocks every node's actual logic.** The Planner returns a hardcoded `execution_plan`, Retrieval returns a hardcoded article list, Summarizer returns a hardcoded string — no LLM calls, no RSS/web search calls anywhere in Sprint 2. Only the graph's structure (state, nodes, edges, START/END) is real.

**4. Graph code lives in a new `app/graph/` folder**, separate from `app/agents/` — `app/graph/state.py` defines the shared state shape, `app/graph/workflow.py` wires nodes into a `StateGraph`. This keeps "the engine that connects nodes" separate from "a node's own implementation," matching the Planner-plans/LangGraph-executes split above.

## Consequences

- If Sprint 2 fails, the failure is isolated to LangGraph/orchestration — not an LLM provider, a prompt, an external API, or Docker. One sprint, one concept, per the project's learning-first philosophy.
- Sprint 3 replaces mocked logic with real implementations (real Planner reasoning, real RSS tool, real LLM summarization) without changing the graph's structure — the architecture doesn't change, only what's inside each node does.
- Node classification (AI / Deterministic / Hybrid) becomes a standing question for every future node: which category does it belong to, and does that change where its code lives or how it's tested.
