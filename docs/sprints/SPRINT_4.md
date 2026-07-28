# Sprint 4 — Tool Infrastructure

**Status:** Design approved (via pre-sprint design review) — TOOL-001 complete, awaiting TOOL-002.

Goal: introduce the first real external tool into the system and learn how AI systems interact with the outside world, **without changing the graph or the Planner**. This sprint is not about planning, and not about RAG — it's about designing Tools correctly.

Reference: [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md), [`CLAUDE.md`](../../CLAUDE.md), [`ADR 0002 — AI Infrastructure Layer`](../ADR/0002-ai-infrastructure-layer.md) (the precedent this sprint's Tool design follows), [`ADR 0003 — Tool Architecture`](../ADR/0003-tool-architecture.md) (TOOL-001's deliverable).

A ticket is only checked off once the implementation works, follows the layering/engineering principles in `CLAUDE.md`, and can be explained line-by-line (per the project's Definition of Done).

---

## Design Review (completed before TOOL-001)

Five design questions answered before any Sprint 4 code was written:

1. Raw feed objects or normalized `Article` objects from the RSS parser? → Normalized `Article` objects — the Tool itself normalizes, matching `LLMClient.complete()`'s "never leak the provider's shape" precedent from Sprint 3.
2. Where do retries live? → Inside `rss.py` (the Tool), matching AI-005's precedent — but likely via a shared retry library (e.g. `tenacity`) rather than hand-rolled, since this is now the second place needing retry logic.
3. Exceptions or typed failure objects? → Exceptions (`RSSToolError`, mirroring `LLMError`) — consistent with the codebase's existing error-handling idiom, not a second competing paradigm.
4. Adding a second news source without touching `retrieval.py`? → A shared Tool interface (`typing.Protocol`, one method: `fetch() -> list[Article]`); `retrieval.py` depends on the interface, injected via a factory function, never on `RSSTool` by name.
5. Which layer decides which tool(s) to invoke, once there are two? → A future Planning decision, not a Tool or Retrieval-Service decision — out of scope until Sprint 4 has a second tool to actually choose between.

---

## Learning Objectives

By the end of this sprint, you should be able to explain:

* What a Tool actually is, and why Tools are different from Services.
* How external APIs are abstracted behind a clean interface.
* Error handling, timeouts, and retry strategy for external systems.
* Data normalization — why external data gets converted to an internal domain model before going anywhere else.
* Tool interfaces and Dependency Injection for tools.
* Testing external dependencies.
* Why RSS is a Tool instead of a Service.
* Why Retrieval stays deterministic even once it's doing something real.
* Why Planner doesn't know RSS exists.
* Where retries should live.
* What an internal domain model is, and why normalize before passing data downstream.
* How you'd swap RSS for Google News without changing the graph.

---

## Architectural Goal

**Current:** `Retrieval (Mock) → [Mock Articles]`

**Target:** `Retrieval Service → RSS Tool → RSS Feed → Normalized Articles → Retrieval returns articles`

Retrieval stays deterministic throughout — only the implementation changes, not its role in the graph.

---

## Tickets

- [x] **TOOL-001 — Tool architecture review**
  Answer before writing code: what makes something a Tool? Why isn't RSS inside Retrieval? Why shouldn't Planner know RSS exists? What is a Tool's responsibility? Deliverable: a short ADR explaining Tool architecture. See [`ADR 0003`](../ADR/0003-tool-architecture.md).

- [x] **TOOL-002 — Design the Article domain model**
  Replace the current `[{"title": "..."}]` shape with a real internal representation (`title`, `content`, `published_at`, `source`, `url`). Decide together: Pydantic model, dataclass, or dict.

- [x] **TOOL-003 — Build the RSS Tool**
  New file `app/tools/rss.py`. Responsibilities: fetch RSS, parse the feed, normalize output to `Article` objects. Must **not** summarize, filter, think, or rank — pure retrieval.

- [ ] **TOOL-004 — Replace mock Retrieval**
  Swap `return MOCK_ARTICLES` for `rss_tool.fetch() → articles`. Planner remains mocked; Summarizer remains real.

- [ ] **TOOL-005 — Retry & timeout strategy**
  Architecture discussion first: if RSS times out, do we retry? How many times? At which layer (Tool, Service, middleware)? Then implement.

- [ ] **TOOL-006 — Data validation**
  If RSS returns an entry with no date, a broken link, or no content — does Retrieval return it as-is? Does the Tool filter it? Does another layer validate it? This ticket is about ownership of that decision, not just code.

- [ ] **TOOL-007 — End-to-end verification**
  Graph becomes `Planner (Mock) → Retrieval (Real) → RSS Tool → RSS Feed → Articles → Summarizer (Real) → Response Composer`. The application is now consuming live data. No graph changes, no Planner changes.

---

## Folder Changes

```text
app/
    tools/
        rss.py
    models/          (or schemas/)
        article.py
    services/
        retrieval.py
    config/
```

No graph changes. No Planner changes.

---

## Out of Scope

Sprint 4 must **not** include: Web Search, Google News API, deduplication, ranking, Planner reasoning, Timeline, PostgreSQL, Redis, or Memory. One sprint, one responsibility.

---

## Sprint Exit Criteria

- RSS Tool exists.
- Retrieval uses the RSS Tool.
- Articles are normalized.
- Timeout handling exists.
- Retry strategy implemented.
- Summarizer receives real articles.
- Graph unchanged.
- Response returned successfully.
