# ADR 0003: Tool Architecture

## Status

Accepted — 2026-07-27

## Context

Sprint 4 introduces the first real external tool (RSS) into the system. Before writing any code, the project's discipline calls for answering what a Tool actually *is*, why RSS doesn't belong inside Retrieval directly, and why the Planner should stay ignorant of it — since these decisions determine how `app/tools/rss.py`, `app/services/retrieval.py`, and the Article domain model get designed in the tickets that follow.

## Decision

**1. A Tool is code that talks to something outside our own process, and does so without making any judgment calls.** The test: does this code perform real I/O against an external system (network call, API, file system)? And does it do so mechanically — given a request, perform the I/O, hand back a result in our own internal shape — without deciding whether to be called, when to be called, or what the result means? The moment code starts making a judgment (is this result good enough, which of several sources to use, does this data matter), it has stopped being a Tool and become a Service or an Agent.

**2. RSS logic does not live inside `retrieval.py`, because Retrieval and a Tool have genuinely different responsibilities.** Retrieval (a Deterministic node, per ADR 0001) decides *what* needs retrieving and assembles it for the graph; RSS-fetching is only one mechanism for accomplishing that. Embedding RSS directly in Retrieval would: couple Retrieval's code to RSS's specific parsing quirks (the same leak `LLMClient` was built in Sprint 3 to avoid); make Retrieval's own assembly logic untestable without exercising real RSS I/O; and mean swapping RSS for a different source later requires rewriting Retrieval itself, rather than swapping an implementation underneath a stable interface — defeating the exact pattern Sprint 3 proved works for the Summarizer.

**3. The Planner does not know RSS exists.** Per ADR 0001, the Planner produces a plan (an intention — "retrieve, then summarize") and never executes anything itself. If it knew about RSS specifically, adding a second source later would require touching Planner's logic even though Planner's actual job — deciding *that* retrieval is needed — never changed. This would also blur reasoning (Planner's real responsibility) with infrastructure detail (which library/API is actually hit), which belongs entirely to a lower layer.

**4. A Tool's responsibility, synthesized:**
- Know how to talk to **one specific** external system.
- Own that system's low-level reliability concerns (timeouts, retries for its own transient failures).
- **Normalize** whatever comes back into our internal domain shape (e.g. `Article`) before returning — nothing downstream ever sees the external system's native format.
- Surface unrecoverable failures as its own clean, typed exception (e.g. `RSSToolError`) — never leak the underlying library's raw exception type, mirroring `LLMError` from ADR 0002.

A Tool must never: decide whether or when it's called, filter or rank by any judgment, combine multiple sources, or reason about what the data means. Those are Service or Agent responsibilities.

## Consequences

- `app/tools/rss.py` (TOOL-003) will normalize internally and return `Article` objects, never raw feed data — `retrieval.py` never learns RSS's specific shape.
- `retrieval.py` (TOOL-004) depends on a Tool *interface*, not `RSSTool` by name — adding a second source later (Google News, etc.) means writing a new class satisfying the same interface, not modifying Retrieval's own code.
- The Planner's plan stays at the level of intention ("retrieve") — it never needs updating when tools are added, removed, or swapped.
- Retry/timeout ownership (TOOL-005) belongs to the Tool itself, matching how `LLMClient` owns its own retry logic — not pushed up into Retrieval.
