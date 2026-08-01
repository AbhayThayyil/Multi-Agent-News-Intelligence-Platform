# Sprint 5 — Intelligent Planning

**Status:** Design approved (via pre-sprint design review) — PLAN-001 complete, awaiting PLAN-002.

Goal: replace the mocked Planner with a real reasoning node that produces a structured execution plan, and let the graph route dynamically based on it. This is the sprint that turns an AI workflow into an **agentic** one — the workflow starts adapting to what the user actually asked for, instead of always doing the same fixed sequence.

Not in scope: Timeline (real), Trend Analysis, Fact Checking. This sprint teaches the system how to *think about* the workflow, not adds new analysis capabilities.

Reference: [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md), [`CLAUDE.md`](../../CLAUDE.md), [`ADR 0001`](../ADR/0001-langgraph-execution-engine.md) (conditional edges were named as a future capability there, back in Sprint 2 — this is that future), [`ADR 0004 — Planner Responsibilities`](../ADR/0004-planner-responsibilities.md) (PLAN-001's deliverable).

A ticket is only checked off once the implementation works, follows the layering/engineering principles in `CLAUDE.md`, and can be explained line-by-line (per the project's Definition of Done).

---

## Design notes from pre-sprint discussion (to be finalized at the relevant ticket)

**Execution plan schema (PLAN-002) — a minimal capability description, not a step sequence:**
```python
class ExecutionPlan(BaseModel):
    intent: str                      # human-readable label (logging/debugging only, doesn't drive routing)
    requires_timeline: bool = False  # the one field that actually drives conditional routing this sprint
    response_style: str = "neutral"  # a hint passed to the Summarizer's prompt, doesn't affect routing
```
Explicit typed fields, not a generic `capabilities: dict[str, bool]` — a dict would let the LLM invent a capability name that doesn't exist, exactly what PLAN-004 needs to catch. Retrieval and summarization aren't toggleable in Sprint 5 (every query needs both), so they don't need flags — only `requires_timeline` is a real sometimes-skip decision. New capabilities (Trend Analysis, Fact Checking, etc.) earn their own field only when they're actually built, not before.

**Timeline routing (PLAN-005) — sequential, not parallel:** `Retrieval → Timeline (mock, when `requires_timeline`) → Summarizer`. Timeline runs after Retrieval, using retrieved articles, and writes to its own new state field that Summarizer does **not** read — consistent with the exit criteria that Summarizer stays unchanged. Timeline's presence affects *routing* this sprint, not summary content — that's a later sprint's job, once Timeline is real.

**Structured output mechanism (PLAN-003/004):** try requesting JSON mode from the LLM (LiteLLM's `response_format={"type": "json_object"}`, if the current free model supports it) as a best-effort nudge toward valid syntax — but validate via Pydantic regardless, every time, as the real gate. JSON-mode support isn't guaranteed on free-tier models; this needs live verification, not an assumption, when PLAN-003 is actually implemented.

**Failure strategy (PLAN-006) — two different failure modes, two different responses:**
- **Malformed output** (invalid JSON, or JSON that fails `ExecutionPlan` validation): the LLM responded, just not usefully. Retry the Planner call a small number of times (a different sampling may produce valid output), then fall back to a safe default plan (`requires_timeline=False`, plain retrieve+summarize) rather than failing the whole request — matches the ticket's own framing, "fail safely."
- **Genuine LLM infrastructure failure** (timeout, auth, rate limit — `LLMError` from AI-005): still fails loudly, propagating uncaught, same as every other sprint so far. A real infra failure isn't something a default plan should paper over.

---

## Learning Objectives

By the end of this sprint, you should be able to explain:

* Intent classification and structured outputs from an LLM.
* JSON schemas for LLMs, and why validating LLM output matters before it drives application flow.
* Guardrails and recovering from malformed LLM output.
* Conditional routing and dynamic graph execution in LangGraph.
* Prompt design for reasoning (vs. prompt design for summarization, which is a different task).
* Why planning is separate from execution.
* Why deterministic nodes should not make reasoning decisions.
* Why the Planner is intentionally unaware of implementation details (RSS, LiteLLM, specific providers).

---

## Tickets

- [x] **PLAN-001 — Planner design review**
  Answer before writing code: what is a Planner? What decisions belong to it, and which must never belong to it? Why doesn't it know RSS exists? Why doesn't it know LiteLLM exists? Deliverable: an ADR explaining Planner responsibilities. See [`ADR 0004`](../ADR/0004-planner-responsibilities.md).

- [x] **PLAN-002 — Design the execution plan schema**
  Replace the hardcoded `execution_plan = ["retrieve", "summarize"]` list with a typed model. See the design note above for the proposed minimal shape — finalize at this ticket.

- [ ] **PLAN-003 — Build the real Planner**
  Replace the mock return with `User Query → Planner Prompt → LLM → Structured Execution Plan`. The Planner only outputs the plan — it never executes it.

- [ ] **PLAN-004 — Structured output validation**
  The Planner returns JSON; it can't be trusted as-is. Handle: invalid JSON, missing fields, unknown/extra fields. The graph must never receive malformed state.

- [ ] **PLAN-005 — Conditional routing**
  The first graph change since Sprint 2. Wire a real conditional edge: route to Timeline (mock) when `requires_timeline` is true, straight to Summarizer otherwise. This is about proving routing works, not building real timeline analysis.

- [ ] **PLAN-006 — Failure strategy**
  Architecture discussion first (retry vs. fallback vs. fail-request), then implementation. See the design note above for the proposed direction.

- [ ] **PLAN-007 — End-to-end verification**
  Run several distinct queries ("Summarize AI news," "Show a timeline," "Latest NVIDIA news," etc.) and observe different execution plans. Verify state evolution, conditional routing, Planner reasoning, and graph stability. Note: queries implying capabilities Sprint 5 doesn't build yet (e.g. "Compare X and Y" — Trend/Comparison is out of scope) are expected to still route through the same retrieve+summarize path; only the *content* differs, not the plan — don't mistake that for a bug.

---

## Architectural Change

The first sprint where the graph itself evolves since Sprint 2 — but only *routing* changes, not the nodes:

```text
Old:                          New:
START                         START
  │                             │
Planner (Mock)                Planner (LLM)
  │                             │
Retrieval                  Conditional Edge (on requires_timeline)
  │                        ┌────┴────┐
Summarizer                 │         │
  │                     Retrieval    │
Response Composer           │        │
  │                     Timeline (Mock, if requires_timeline)
END                         │        │
                            └────┬───┘
                             Summarizer
                                 │
                          Response Composer
                                 │
                                END
```

Retrieval, Summarizer, and Response Composer are not rewritten — only the Planner (now real) and the graph's routing logic change.

---

## Out of Scope

Sprint 5 must **not** implement: Trend Analysis, Bias Detection, Fact Checking, Memory, PostgreSQL, Redis, RAG, multiple planners, or reflection loops. This sprint is about planning, not analysis.

---

## Sprint Exit Criteria

- Planner uses a real LLM.
- Planner returns validated structured output.
- Invalid Planner output is handled safely (retry, then safe fallback plan).
- Graph routes dynamically based on the execution plan.
- Timeline node exists (mock implementation is fine).
- Retrieval, Summarizer, and Response Composer remain unchanged.
- Multiple distinct user queries produce different execution paths.
