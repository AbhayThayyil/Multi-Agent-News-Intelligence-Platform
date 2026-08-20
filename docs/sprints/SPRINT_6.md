# Sprint 6 — Hybrid Timeline

**Status:** Design proposed by Claude, pending your review — TIMELINE-001 complete, awaiting TIMELINE-002.

Goal: replace the mocked Timeline node with a real **hybrid** implementation — the first node in the project combining deterministic Python and LLM reasoning within one graph node. Deterministic code handles validation, date normalization, capping, and chronological ordering; the LLM is used only for the one thing that genuinely requires interpretation — extracting a concise event description per article. Reuses the existing `LLMClient`. Preserves the Planner's conditional routing and `workflow.py`'s wiring exactly as PLAN-005 built them. Keeps `articles` immutable.

Reference: [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md), [`CLAUDE.md`](../../CLAUDE.md), [`ADR 0001`](../ADR/0001-langgraph-execution-engine.md) (defines the Hybrid category this sprint finally builds), [`ADR 0003`](../ADR/0003-tool-architecture.md) and [`ADR 0004`](../ADR/0004-planner-responsibilities.md) (the ownership-and-validation discipline this sprint continues), [`ADR 0005 — Hybrid Node Design`](../ADR/0005-hybrid-node-design.md) (TIMELINE-001's deliverable).

A ticket is only checked off once the implementation works, follows the layering/engineering principles in `CLAUDE.md`, and can be explained line-by-line (per the project's Definition of Done).

---

## Design decisions made during planning (to be finalized/confirmed at the relevant ticket)

**Hybrid split:** deterministic logic (validation, date normalization, article capping, sorting) lives in `app/services/timeline.py` — matching `CLAUDE.md`'s existing definition of `services/`. The graph node itself (`app/agents/timeline.py`) becomes a thin orchestrator: call the deterministic service, then call the LLM only for event extraction, then assemble the result. Same shape every existing node already uses — a thin function delegating to a client/tool — Timeline is just the first to delegate to two different kinds.

**Batched LLM call, not per-article — revised after hitting a real rate limit in Sprint 5.** One call per article (30+ articles per fetch, per TOOL-004/006/007) would multiply the exact problem that already occurred this session. One batched call, structured output (`json_mode=True`, same mechanism `Planner` already uses), asking for an array of `{index, event}` pairs mapped back to a capped, sorted article list by position — not by title, since titles aren't guaranteed unique or stable through the LLM.

**A deterministic article cap, before anything reaches the LLM.** Not ranking (still out of scope) — a plain "most recent N articles, after sorting" cutoff. Real evidence from TOOL-004/006/007 already showed summary quality degrading on 30+ unrelated real articles; a 30-entry timeline built from one LLM call over that much content is the same problem in a more expensive shape. Proposed default: cap at 10 articles, finalized at TIMELINE-003.

**Dateless articles are dropped from the timeline, logged.** A timeline entry with no date isn't really a timeline entry (same ownership-of-validation reasoning as `TOOL-006`). Revisit at TIMELINE-003 if this turns out too strict.

**Immutability is an implementation rule, not just a verification step.** `state["articles"]` is a plain `list[dict]`, fully mutable. TIMELINE-003 must use `sorted()` (returns a new list) rather than `.sort()` (mutates in place), and must never write back into an article dict. Stated explicitly in TIMELINE-001's ADR, not left to be caught after the fact by TIMELINE-007.

**Summarizer and Response Composer remain unchanged this sprint** — my call, stated explicitly rather than left ambiguous. The Sprint 6 goal says Timeline should "produce a new `timeline` field in `GraphState`," the same wording Sprint 5's mock already satisfied; it doesn't ask for that field to reach the user-visible response. Every prior "replace mock with real" sprint (AI-004, TOOL-004, this pattern) only ever touched the one node being made real — surfacing `timeline` through Summarizer/Response Composer would be a genuinely new scope addition to those files, not a Hybrid-node concern, and deserves its own future ticket rather than being folded in silently here. Flagging this clearly in case you actually want it wired through this sprint — easy to add as an explicit ticket if so.

---

## Learning Objectives

By the end of this sprint, you should be able to explain:

* What actually makes a node "Hybrid," distinct from a pure AI node or a pure Deterministic one.
* Why deterministic work (sorting, capping, date normalization) should never be delegated to an LLM, even inside a node that also reasons.
* Why a single batched structured-output call is preferable to N per-item calls once real cost/rate-limit evidence exists — not as a default assumption.
* Why immutability of shared state matters once multiple nodes may read the same field, and how to actually enforce it in Python (not just claim it).
* Ownership of validation decisions (which layer decides what to do with unusable data) — continuing the pattern from `TOOL-006`.
* Why `workflow.py`'s structure doesn't need to change even for a fundamentally new *kind* of node.

---

## Tickets

- [x] **TIMELINE-001 — Hybrid node design review**
  Before writing code: what makes a node Hybrid? Where does deterministic vs. LLM logic live within one? How is "LLM only where reasoning is genuinely required" enforced, not just claimed? Why must `articles` stay immutable, and how is that actually guaranteed in code? Deliverable: ADR 0005.
  *Depends on:* nothing.

- [x] **TIMELINE-002 — Design the Timeline schema**
  `app/schemas/timeline.py`: `TimelineEntry` (`date: datetime`, `event: str`, `source_title: str`, `source_url: HttpUrl | None`) and `Timeline` (`entries: list[TimelineEntry]`), mirroring `Article`/`ExecutionPlan`'s validation rigor. Also defines the lightweight schema the batched LLM call itself returns (index + event pairs), separate from the final assembled `TimelineEntry`.
  *Depends on:* TIMELINE-001.

- [ ] **TIMELINE-003 — Deterministic validation, capping, and chronological ordering**
  Pure Python, zero LLM calls. Given `state["articles"]`: drop articles with no usable `published_at` (logged), normalize dates to one consistent timezone-aware form, sort chronologically via `sorted()` (never mutate the original list), cap to the most recent N (proposed default: 10).
  *Depends on:* TIMELINE-002.

- [ ] **TIMELINE-004 — LLM-based event extraction (batched)**
  `app/prompts/timeline.py` + the LLM-calling logic, reusing `get_llm_client()` — no new LLM-calling mechanism. One batched, structured (`json_mode=True`) call over the capped/sorted article list, returning event descriptions mapped back to articles by position.
  *Depends on:* TIMELINE-002.

- [ ] **TIMELINE-005 — Wire the real Timeline node**
  `app/agents/timeline.py` rewritten: call TIMELINE-003, then TIMELINE-004, assemble into `Timeline`, write to state. Acceptance criteria: `workflow.py` shows zero diff — `route_after_retrieval` and the conditional edge stay exactly as PLAN-005 built them.
  *Depends on:* TIMELINE-003, TIMELINE-004.

- [ ] **TIMELINE-006 — Error handling & partial-failure strategy**
  Discussion first, then implementation. The batched call is more all-or-nothing than per-article calls were going to be — if it fails validation, retry a small number of times (mirroring `PLANNER_MAX_ATTEMPTS`), then fall back to a fully deterministic timeline (raw article titles as event text) rather than an empty one. Genuine `LLMError` infra failures still propagate uncaught, same as every prior sprint.
  *Depends on:* TIMELINE-005.

- [ ] **TIMELINE-007 — End-to-end verification**
  Real queries triggering `requires_timeline=True`, run through the full graph. Verify: chronological ordering is actually correct (not just "some order"), `articles` are provably unmutated (identity/deep-equality check against a pre-call snapshot, not just "it didn't crash"), the cap is respected, batch-failure fallback behaves per TIMELINE-006, `workflow.py` untouched across the whole sprint. Also updates `CLAUDE.md`'s stale `agents/` folder comment and Sprint-1-era "Current Scope" section to reflect where the project actually is.
  *Depends on:* everything above.

---

## Architectural Note

No change to `workflow.py`'s structure — only `app/agents/timeline.py`'s internals change, plus two new files (`app/services/timeline.py`, `app/prompts/timeline.py`) and one new schema. Same principle every prior "replace mock with real" ticket has proven: swap the implementation, not the architecture. What's new this sprint isn't the graph — it's that, for the first time, one node's implementation is expected to contain *both* deterministic and AI logic, cleanly separated rather than blended.

---

## Out of Scope

Sprint 6 must **not** introduce: new agents, RAG, memory, persistence, ranking/ordering by relevance (only chronological order), deduplication, Summarizer/Response Composer changes (see design decision above), or any other capability from `PROJECT_CONTEXT.md`'s Future Roadmap.

---

## Verification Strategy

Every ticket verified against real data where the thing being tested actually needs real variance (LLM event extraction quality, batched-call behavior), and against controlled/constructed inputs where only a deterministic mechanism is under test (date normalization, capping, sort order, immutability) — same split established in PLAN-005 when the free-tier rate limit made blanket "always use the real API" impractical. Real end-to-end runs reserved for TIMELINE-007, using single, deliberate queries rather than repeated back-to-back calls, given this session's own rate-limit history.

---

## Sprint Exit Criteria

- Timeline node uses a real, deterministic + LLM hybrid implementation — no mock data remains.
- `Timeline`/`TimelineEntry` schemas exist and validate real data (not just accept anything).
- Chronological ordering is deterministic and independently verifiable.
- Articles are provably immutable after Timeline processing.
- The article cap is enforced before any LLM call.
- Batched extraction failure is handled safely (retry, then deterministic fallback) rather than crashing the request.
- `workflow.py` remains unchanged from PLAN-005 — conditional routing untouched.
- Summarizer and Response Composer remain unchanged (per this sprint's scope decision).
