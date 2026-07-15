# Sprint 2 — Execution Engine

**Status:** Complete — all tickets (ENGINE-001–007) implemented and verified; Sprint Exit Criteria confirmed end-to-end on a clean `main` (2026-07-15).

Goal: prove the LangGraph orchestration engine works — state, nodes, edges, conditional plans — using **entirely mocked node logic**. Zero LLM calls, zero real tool calls (RSS, web search). If something breaks in Sprint 2, it's the engine, not an LLM provider, a prompt, or an external API.

Reference: [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md), [`CLAUDE.md`](../../CLAUDE.md), [`ADR 0001 — LangGraph as Execution Engine`](../ADR/0001-langgraph-execution-engine.md)

A ticket is only checked off once the implementation works, follows the layering/engineering principles in `CLAUDE.md`, and can be explained line-by-line (per the project's Definition of Done).

---

## Node Classification (per ADR 0001)

| Node | Type | Reasoning? |
|---|---|---|
| Planner | 🟢 AI | Yes — decides the execution plan |
| Retrieval | 🔵 Deterministic | No — executes what the plan says |
| Summarizer | 🟢 AI | Yes — produces the summary |
| Response Composer | 🔵 Deterministic | No — formats the final response |
| Timeline / Trend / Fact Checker / Deduplication | 🟡 Hybrid (future) | Combines Python + AI — not built this sprint |

---

## Tickets

- [x] **ENGINE-001 — Learn LangGraph concepts**
  Understand `State`, `Nodes`, `Edges`, `START`, `END` before writing any code. Deliverable: a short written summary of these four concepts in `LEARNING_JOURNAL.md`, in your own words, before ENGINE-002 starts.

- [x] **ENGINE-002 — Define shared state**
  Add `langgraph` as a backend dependency. Create `app/graph/state.py` defining one shared state shape: `query`, `execution_plan`, `articles`, `summary`, `response`. Nothing else yet.

- [x] **ENGINE-003 — Planner node (mock)**
  Reads `query` from state, returns a **hardcoded** `execution_plan: ["retrieve", "summarize"]`. Not connected to an LLM. We're testing the graph, not AI.

- [x] **ENGINE-004 — Retrieval node (mock)**
  Reads `execution_plan` from state, returns a hardcoded `articles` list (e.g. one mock article, mock source). No RSS, no web search, no real tool calls.

- [x] **ENGINE-005 — Summarizer node (mock)**
  Reads `articles` from state, returns a hardcoded `summary` string. No LLM call.

- [x] **ENGINE-006 — Response Composer**
  Reads `summary` (and `articles` as sources) from state, formats the final `response` (e.g. `{"answer": "...", "sources": [...]}`). Deterministic — belongs in the Service layer's spirit (no reasoning), even though it runs as a graph node.

- [x] **ENGINE-007 — Connect the complete graph**
  Wire `START → Planner → Retrieval → Summarizer → Response Composer → END` in `app/graph/workflow.py` using LangGraph's `StateGraph`. Invoke it end-to-end with a sample `{"query": "..."}` and confirm the final state contains all five fields, fully mocked.

---

## Sprint Exit Criteria

- Invoking the compiled graph with `{"query": "What happened in AI this week?"}` returns a final state containing `query`, `execution_plan`, `articles`, `summary`, and `response`.
- Every node's logic is hardcoded/mocked — zero LLM calls, zero real RSS/web search calls anywhere in the sprint.
- Node classification (AI / Deterministic / Hybrid) is documented per ADR 0001.
- The graph's structure (not its node contents) is what Sprint 3 will build on unchanged — replacing mocks with real Planner reasoning, a real RSS tool, and real LLM summarization without touching `app/graph/workflow.py`'s wiring.
