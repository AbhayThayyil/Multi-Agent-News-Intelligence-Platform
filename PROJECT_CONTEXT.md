# PROJECT_CONTEXT.md

# Multi-Agent News Intelligence Platform

## Purpose

This document serves as the primary project context for all development work.

Every implementation, architecture decision, and feature should align with the principles documented here.

Before writing code, contributors (human or AI) should understand this document to ensure consistency throughout the project.

---

# Project Vision

The goal of this project is **not** to build another AI chatbot.

The goal is to build an **AI News Intelligence Platform** capable of analyzing, organizing, and explaining news through collaboration between specialized AI agents.

Instead of simply answering:

> "What happened?"

The platform should answer questions like:

* What happened?
* Why did it happen?
* What does it mean?
* What trends are emerging?
* How do different companies compare?
* What is the likely future impact?

Long-term vision:

> **Perplexity × Bloomberg Terminal × Research Analyst**

---

# Learning Philosophy

This project is primarily a learning project.

The objective is to understand modern AI system design and software engineering rather than relying on AI-generated code.

Claude Code acts as a **Senior Software Engineer**, not as an autonomous code generator.

For every feature, the workflow is:

1. Understand the concept.
2. Discuss and approve the architecture.
3. Design the solution.
4. Ask Claude Code to implement the approved design.
5. Review every generated file.
6. Refactor where necessary.
7. Document what was learned.

**Rule:**

> Never merge code that cannot be explained.

---

# Engineering Philosophy

This project follows several core engineering principles.

## Separation of Concerns

Every component should have one clear responsibility.

Examples:

* Planner → orchestration
* Retrieval Agent → retrieve information
* Summarizer → summarize
* Tools → communicate with external systems
* Services → business logic
* API → receive and return HTTP requests

---

## Single Responsibility Principle

Each component should solve one problem well.

Avoid combining unrelated responsibilities into one class or module.

---

## Loose Coupling

Components should depend on abstractions rather than concrete implementations.

Changing one component should require minimal changes elsewhere.

---

## Dependency Injection

Dependencies should be provided to components rather than created internally.

This improves:

* maintainability
* testing
* flexibility
* extensibility

---

## Deterministic Code First

Use Python code whenever reasoning is unnecessary.

Examples:

* formatting
* validation
* retries
* sorting
* parsing

Only use an LLM when reasoning is required.

---

# Current MVP Scope

Version 1 intentionally keeps the architecture small.

Current agents:

* Planner Agent
* Information Retrieval Agent
* Summarizer Agent

Current tools:

* RSS Tool
* Web Search Tool

Current functions:

* Response Composer
* Retry Logic
* Markdown Formatter

Future agents will only be added when a real product requirement justifies them.

Avoid over-engineering.

Each agent/node is classified as **AI** (needs reasoning), **Deterministic** (plain Python, no reasoning), or **Hybrid** (combines both — none built yet). See [`ADR 0001`](docs/ADR/0001-langgraph-execution-engine.md) for the full rationale.

---

# High-Level Architecture

```text
User
    │
    ▼
React Frontend
    │
    ▼
FastAPI Backend
    │
    ▼
Planner Agent
    │
    ▼
Information Retrieval Agent
    │
    ▼
Summarizer Agent
    │
    ▼
Response Composer
    │
    ▼
React Frontend
```

LangGraph owns workflow execution.

Planner is responsible for producing an execution plan.

LangGraph executes that plan by routing between agent nodes.

For now, the Planner produces a **fixed** execution plan (always Retrieval → Summarizer). Dynamic, query-dependent branching is a future capability, not part of the current design.

Sprint 1 is **stateless**: each request is handled independently, with no conversation memory or session state.

---

# Backend Architecture

The backend follows a layered architecture.

## API Layer

Responsible for:

* receiving HTTP requests
* validating requests
* returning responses

Does **not** contain business logic.

---

## AI Layer

Responsible for:

* reasoning
* planning
* orchestration
* summarization

Contains:

* Planner Agent
* Information Retrieval Agent
* Summarizer Agent

---

## Tool Layer

Responsible for communicating with external systems.

Examples:

* RSS
* Web Search

Tools do not perform reasoning.

---

## Service Layer

Responsible for deterministic business operations.

Examples:

* persistence
* conversation management
* caching

---

## Persistence Layer

Responsible for storing data.

Examples:

* PostgreSQL
* Redis

---

## Infrastructure Layer

Responsible for running the application.

Examples:

* Docker
* configuration
* logging
* CI/CD

---

# Current Folder Structure

```text
backend/

    app/

        api/

        agents/

        tools/

        prompts/

        services/

        schemas/

        models/

        config/

frontend/

docs/
```

Each folder exists because it owns a specific responsibility.

---

# Technology Stack

## Current

* FastAPI
* LangGraph
* LiteLLM
* React
* Docker

## Future

* PostgreSQL
* Redis

---

# Current Sprint

## Sprint 1 — Project Bootstrap (Complete)

Goal: build a production-ready project foundation (repository structure, FastAPI scaffold, React scaffold, Docker, health endpoint, React ↔ FastAPI communication). Business logic, LangGraph, and persistence intentionally postponed.

**Status:** Complete. All tickets (T1.1–T4.3) implemented and verified; Sprint Exit Criteria confirmed end-to-end. See [`docs/sprints/SPRINT_1.md`](docs/sprints/SPRINT_1.md) for the full ticket log.

## Sprint 2 — Execution Engine (Complete)

Goal: prove the LangGraph orchestration engine — state, nodes, edges, conditional plans — using entirely mocked node logic. Zero LLM calls, zero real tool calls. See [`ADR 0001`](docs/ADR/0001-langgraph-execution-engine.md) for the rationale and [`docs/sprints/SPRINT_2.md`](docs/sprints/SPRINT_2.md) for the ticket breakdown (ENGINE-001–007).

**Status:** Complete. All tickets implemented and verified; `build_graph()` runs `START → Planner → Retrieval → Summarizer → Response Composer → END` end-to-end with fully mocked node logic — confirmed on a clean `main`.

## Sprint 3 — AI Infrastructure

Goal: introduce a real LLM into the system in a clean, production-ready way, without changing the orchestration architecture — by the end of this sprint, exactly one node (Summarizer) uses a real LLM; Planner and Retrieval remain mocked. See [`ADR 0002`](docs/ADR/0002-ai-infrastructure-layer.md) for the design rationale (LiteLLM/OpenRouter, the `app/llm/` service layer, prompt management, retry placement, interface-only dependency) and [`docs/sprints/SPRINT_3.md`](docs/sprints/SPRINT_3.md) for the ticket breakdown (AI-001–006).

**Status:** Design approved via pre-sprint design review — awaiting AI-001 implementation.

---

# Architecture Decisions

Current decisions:

* Monorepo architecture.
* LangGraph owns workflow execution; Planner produces the execution plan.
* Sprint 1 is stateless — no conversation memory or session persistence yet.
* Planner produces a fixed execution plan for now; dynamic plan branching is a future capability.
* PostgreSQL and Redis are deferred to a later sprint, not Sprint 1.
* Specialized agents have a single responsibility.
* Tools never perform reasoning.
* API layer contains no business logic.
* Dependency Injection will be used throughout the backend.
* Pydantic will define all request and response contracts.
* Docker will be introduced from the beginning.
* LangGraph will be introduced early to avoid architectural rewrites.

Future decisions should be documented through Architecture Decision Records (ADR).

---

# Definition of Done

A feature is considered complete only if:

* implementation works
* architecture follows project principles
* code is understandable
* tests pass (where applicable)
* documentation is updated
* architectural decisions are preserved

---

# Future Roadmap

Planned additions include:

* Timeline Agent
* Comparison Agent
* Trend Analysis Agent
* Insight Agent
* Fact Checker
* Bias Detection
* Credibility Scoring
* RAG
* Memory
* Vector Search
* Streaming Responses
* Evaluation Framework
* Monitoring
* Production Deployment

These features should be introduced incrementally and only when supported by product requirements.

---

# Project Principle

This project prioritizes understanding over speed.

Every architectural decision should be explainable.

Every component should exist because a real requirement justifies it.

The objective is not merely to build software.

The objective is to learn how to design and engineer production-quality AI systems.
