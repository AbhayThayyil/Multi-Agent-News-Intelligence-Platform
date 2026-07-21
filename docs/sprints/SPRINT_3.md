# Sprint 3 — AI Infrastructure

**Status:** Design approved (via pre-sprint design review) — awaiting AI-001 implementation.

Goal: introduce a real LLM into the system in a clean, production-ready way, **without changing the orchestration architecture** built in Sprint 2. By the end of this sprint, exactly one node — Summarizer — uses a real LLM. Planner and Retrieval remain mocked.

Reference: [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md), [`CLAUDE.md`](../../CLAUDE.md), [`ADR 0002 — AI Infrastructure Layer`](../ADR/0002-ai-infrastructure-layer.md)

A ticket is only checked off once the implementation works, follows the layering/engineering principles in `CLAUDE.md`, and can be explained line-by-line (per the project's Definition of Done).

---

## Design Review (completed before AI-001)

Per the project's new pre-sprint discipline, five design questions were answered before any Sprint 3 code was written — full reasoning in [`ADR 0002`](../ADR/0002-ai-infrastructure-layer.md):

1. Is `app/llm/client.py` the right abstraction? → Yes, a new top-level `app/llm/` folder — it's infrastructure every AI node depends on, not an optional tool like `app/tools/`.
2. Plain strings, Python modules, or template files for prompts? → Python modules in `app/prompts/` — template engines are premature for one prompt.
3. Where do retries live? → Inside `app/llm/client.py` (via LiteLLM's own retry support), never inside node functions.
4. What if we replace LiteLLM later? → Only `app/llm/client.py`'s internals change, provided its public interface never leaks LiteLLM-specific types.
5. How does Summarizer depend on an interface, not an implementation? → It never imports `litellm` directly, only `app.llm.client` — same shape as `get_settings()`.

---

## Learning Objectives

By the end of this sprint, you should be able to explain:

* Why LiteLLM, and why not couple the application directly to a provider SDK.
* Why OpenRouter as the provider.
* Prompt engineering fundamentals, and why prompts live outside business logic.
* Why the LLM client is its own layer (Dependency Injection, service abstraction).
* Configuration management for AI (env vars, API keys).
* Error handling around LLMs — timeouts, invalid keys, rate limits, provider unavailability.
* Why only one node was replaced this sprint.
* How state flows through the graph after the Summarizer executes.

---

## Tickets

- [x] **AI-001 — Choose and configure the LLM provider**
  Choose OpenRouter, integrate LiteLLM, add environment variables, verify a simple completion **outside the graph** (no LangGraph changes). Learning goals: why not call OpenAI directly, what LiteLLM abstracts, why provider abstraction matters.

- [x] **AI-002 — Create an LLM service layer**
  New folder `app/llm/`, containing `client.py`. Initializes LiteLLM, exposes one clean interface, hides provider details. Must not know anything about LangGraph, Summarizer, or Planner. Learning goals: Dependency Injection, service abstraction, clean architecture.

- [x] **AI-003 — Prompt management**
  Move prompts into `app/prompts/`, e.g. `summarizer.py`. The Summarizer must not contain a giant inline prompt. Learning goals: prompt versioning, maintainability, separation of concerns.

- [ ] **AI-004 — Replace mock Summarizer**
  Replace the hardcoded summary with a real LLM call. Input: `articles`. Output: `summary`. Planner and Retrieval stay mocked; graph structure stays identical (`Planner (Mock) → Retrieval (Mock) → Summarizer (LLM) → Response Composer → END`).

- [ ] **AI-005 — LLM error handling**
  Handle timeout, invalid API key, rate limit, provider unavailable. Discussion required: should the graph fail, retry, or return partial results on each failure mode — this ticket is about understanding the trade-offs, not just writing `try/except`.

- [ ] **AI-006 — End-to-end verification**
  Run the graph (`Planner (Mock) → Retrieval (Mock) → Summarizer (Real) → Response Composer`) and verify: state evolution, summary quality, logging, error handling.

---

## Out of Scope

Sprint 3 must **not** introduce: RSS, Web Search, real Planner reasoning, dynamic/conditional routing, RAG, PostgreSQL, Redis, authentication, or conversation history. One sprint, one concept.

---

## Sprint Exit Criteria

- LiteLLM configured.
- OpenRouter configured.
- One successful real LLM call, verified.
- Summarizer uses the LLM.
- Planner remains mocked.
- Retrieval remains mocked.
- Response Composer unchanged from Sprint 2.
- The graph still functions end-to-end.
- State flow after the Summarizer executes is understood and can be explained.
