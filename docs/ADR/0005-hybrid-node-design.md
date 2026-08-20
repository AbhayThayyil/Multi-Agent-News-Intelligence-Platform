# ADR 0005: Hybrid Node Design

## Status

Accepted — 2026-08-19

## Context

Sprint 6 replaces the mocked Timeline node with a real implementation — the first node in the project to fall into the "Hybrid" category `ADR 0001` defined (combines Python + AI) but never built. Before writing any code, the project's discipline calls for answering what actually makes a node Hybrid, where its deterministic and LLM logic each live, how "use the LLM only where reasoning is genuinely required" is enforced rather than just claimed, and why `articles` must stay immutable through this node — since these decisions determine the shape of `app/services/timeline.py`, `app/schemas/timeline.py`, and `app/agents/timeline.py` in the tickets that follow.

## Decision

**1. A Hybrid node is one whose *correct* behavior genuinely requires both deterministic computation and LLM reasoning — not one that merely happens to touch an LLM somewhere.** This is a different category from the two already in use: AI nodes (Planner, Summarizer) have no significant deterministic sub-task that could stand alone; Deterministic nodes (Retrieval, Response Composer) have zero reasoning requirement anywhere. Timeline genuinely needs both — chronological ordering is pure computation (sort by a date field, zero interpretation), while turning an article's prose into a concise event statement genuinely requires language understanding no deterministic function can replicate.

**2. Deterministic logic lives in `app/services/timeline.py`; LLM-calling logic lives in the node's own orchestration; the graph node itself (`app/agents/timeline.py`) is a thin orchestrator.** Same shape every existing node already uses — a thin function delegating to a client/tool — Timeline is simply the first to delegate to two different kinds. **Deterministic work always runs first**, gating and shaping what reaches the LLM, never the reverse. The LLM never sees raw, unvalidated data; the deterministic layer establishes the quality gate before reasoning is applied.

**3. "LLM only where reasoning is genuinely required" is enforced by structure, not left as a convention to remember.** Two concrete mechanisms: (a) the deterministic service module (`app/services/timeline.py`) never imports `app.llm.client` at all — not "shouldn't call it," structurally cannot, since the capability isn't present in that file, the same enforcement-by-structure pattern `RSSTool` uses (normalize before returning) and `ExecutionPlan` uses (`extra="forbid"`); (b) the LLM-extraction function only ever receives already-validated, capped, sorted data — it has no opportunity to re-derive dates or re-sort, because that work is already finished by the time it's called and it is never given the raw input to redo it.

**4. `articles` must stay immutable through Timeline, for a concrete reason specific to this graph's wiring, not an abstract one.** Timeline sits between Retrieval and Summarizer (per `PLAN-005`'s conditional edge). Summarizer also reads `state["articles"]` (via `build_summarizer_prompt`), and Response Composer copies them into `response["sources"]`. If Timeline mutated the shared list or its dicts, Summarizer and Response Composer — neither of which changed anything — would see corrupted data purely because they happen to run after Timeline in the same request.

**5. Immutability is guaranteed in code, not just documented as an expectation.** `sorted()` (returns a new list) is used, never `.sort()` (mutates in place); no line ever writes `article["field"] = ...` — any derived value is built into a new object; capping is done by slicing the new sorted list, never the original. `TIMELINE-007` verifies this against a real pre-call snapshot of `articles`, not an assumption that the rule was followed.

## Consequences

- `app/services/timeline.py` (TIMELINE-003) contains zero LLM imports, by construction — a stray `import app.llm.client` there would be an immediate, visible violation of this ADR, not a subtle one.
- `app/schemas/timeline.py` (TIMELINE-002) defines the boundary between the two halves — the deterministic layer's output shape is exactly what the LLM-extraction function is allowed to receive, nothing more.
- `app/agents/timeline.py` (TIMELINE-005) never contains business logic of its own — if it starts accumulating real logic beyond "call deterministic step, call LLM step, assemble," that's a signal the split has drifted and needs revisiting.
- Verification (TIMELINE-007) must include an explicit before/after check on `articles`, not just "the graph didn't crash" — the risk this ADR names (Summarizer/Response Composer silently receiving corrupted data) would not be caught by a crash-only test.
