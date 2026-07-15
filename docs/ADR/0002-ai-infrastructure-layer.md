# ADR 0002: AI Infrastructure Layer (LiteLLM + OpenRouter)

## Status

Accepted — 2026-07-15

## Context

Sprint 3 introduces the first real LLM call into the system — the Summarizer node stops being mocked. This requires deciding, before any code is written: how the app talks to an LLM provider, where that code lives, how prompts are managed, where retry/error handling lives, and how AI nodes stay decoupled from any specific provider implementation. These decisions were made via an explicit design review (five questions, answered below) before AI-001 was implemented, per the project's new pre-sprint design review discipline.

## Decision

**1. Provider: OpenRouter, accessed through LiteLLM — never a direct provider SDK.** LiteLLM gives a single, unified interface across many LLM providers; OpenRouter gives access to many models through one API key/endpoint. Together they avoid coupling the application to one vendor's SDK/API shape.

**2. A new top-level `app/llm/` folder — not nested under `app/tools/`.** `tools/` holds things a node *optionally chooses* to call as part of a plan (RSS, web search). The LLM client is different: every AI node depends on it unconditionally to reason at all — it's infrastructure, not a selectable tool. `app/llm/client.py` exposes one minimal interface (e.g. `complete(prompt: str) -> str`) that accepts and returns plain Python types only, **never** LiteLLM-specific response objects — this is what actually keeps the provider swappable later, not just the folder boundary.

**3. Prompts live in `app/prompts/` as plain Python modules** (e.g. `summarizer.py`), each exposing a function that builds a prompt string from structured input — not external template files (Jinja2, `.txt`, etc.). Templating engines are deferred until a real need appears (non-engineers editing prompts, hot-reload without redeploy, many prompt variants) — introducing one now for a single prompt would be premature.

**4. Retries and timeouts live inside `app/llm/client.py`, never inside node functions** — ideally configured through LiteLLM's own retry/fallback support rather than hand-rolled. This is a reliability concern about talking to an external system, not a reasoning concern; every future AI node would otherwise need to duplicate it.

**5. AI nodes depend only on `app/llm/client.py`'s interface — never import `litellm` directly themselves.** Same shape as `get_settings()` from Sprint 1: one injectable seam other code depends on. Enforced by convention and code review at this project's size, not by tooling (e.g. import-linting) — that would be over-engineering for a one-node sprint.

## Consequences

- Exactly one node (Summarizer) becomes LLM-backed in Sprint 3. Planner and Retrieval remain mocked; `app/graph/workflow.py`'s structure does not change.
- Swapping LLM providers later touches only the inside of `app/llm/client.py`.
- Prompt changes are isolated to `app/prompts/`, reviewable independently of node logic.
- Nothing currently prevents a stray direct `import litellm` elsewhere in the codebase — acceptable now; revisit only if the codebase grows enough to justify enforcement tooling.
