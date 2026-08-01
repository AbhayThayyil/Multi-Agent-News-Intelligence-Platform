# ADR 0004: Planner Responsibilities

## Status

Accepted — 2026-07-29

## Context

Sprint 5 replaces the mocked Planner with a real reasoning node, and introduces the first conditional routing in the graph since Sprint 2. Before writing any code, the project's discipline calls for answering what a Planner actually *is*, which decisions belong to it, and which must never belong to it — since these decisions determine the shape of `ExecutionPlan` (PLAN-002), how the real Planner is implemented (PLAN-003), and how the graph routes on its output (PLAN-005).

## Decision

**1. A Planner is an AI node whose only output is structured data describing what the user needs — never an action, never a mechanism.** It sits at the boundary between unstructured human intent and a machine-readable decision the rest of the system can route on. Everything downstream operates on that structured plan; nothing downstream re-interprets the user's raw wording again.

**2. Decisions that belong to the Planner:** classifying intent, deciding which of the system's known, fixed capabilities are needed to satisfy that intent (e.g. `requires_timeline`), and optional generation hints (tone/style) for later nodes. All of these require actual language understanding — that is the entire justification for using an LLM here at all, unlike Retrieval or Response Composer.

**3. Decisions that must never belong to the Planner:** anything that is implementation rather than intent. Concretely — which tool fetches data (Retrieval Service's call, per ADR 0003), which LLM/provider generates a summary (`app/llm/client.py`'s concern, per ADR 0002), execution *order* (LangGraph's conditional routing, per ADR 0001 — the plan is data, the graph interprets it), retry/error handling for any downstream call (each Tool/Client already owns its own), and final response formatting (Response Composer's job). The dividing line: if it's about *what the user wants*, it's the Planner's; if it's about *how the system technically does it*, it belongs to whichever lower layer actually does that work.

**4. The Planner does not know RSS exists**, for the same reason established in ADR 0003: if it did, adding or swapping a news source later would mean touching the Planner's prompt even though the user's actual intent-classification task never changed — breaking the exact swappability ADR 0003 protects. The Planner reasons only about "retrieval is needed" as an abstract capability.

**5. The Planner does not know LiteLLM exists**, even though it is itself implemented as an LLM call (via `app/llm/client.py`, the same abstraction Summarizer already uses — no new mechanism introduced). That is an implementation detail of the *node*, never something that leaks into the *plan it produces*. `ExecutionPlan` describes capabilities needed, never "use LiteLLM" or "call OpenRouter" — if the underlying LLM mechanism changed entirely, every past and future plan stays valid, because the plan's shape was never coupled to how the Planner itself reasons.

**6. The Planner's raw output is untrusted data crossing a trust boundary, exactly like RSS feed content (ADR 0003).** It gets no special trust for having come from "our own" AI node. PLAN-004's validation treats it with the same rigor `Article` validation already gets — invalid JSON, missing fields, and unknown/extra fields must all be caught before the graph ever sees them.

## Consequences

- `ExecutionPlan` (PLAN-002) encodes only capabilities/intent — never tool or provider specifics.
- The real Planner (PLAN-003) reuses `app/llm/client.py` — no new LLM-calling mechanism is invented for it.
- Validation (PLAN-004) treats the Planner's output with the same "don't trust it" rigor as external API data, not as inherently reliable because it came from inside the system.
- Conditional routing logic (PLAN-005) lives entirely in `app/graph/workflow.py`, reading the validated plan's fields — the Planner never touches routing code.
- Adding a future capability (Trend Analysis, Fact Checking, etc.) means three separate, layer-appropriate changes: teach the Planner's prompt about the new intent, add a field to `ExecutionPlan`, add routing logic in `workflow.py` — never one node reaching into another's responsibility.
