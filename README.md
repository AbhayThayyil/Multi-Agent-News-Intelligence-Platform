# Multi-Agent News Intelligence Platform

> **An AI-powered News Intelligence Platform that goes beyond summarization to deliver structured analysis, insights, and reasoning using a collaborative multi-agent architecture.**

---

## Vision

Most AI news assistants answer questions.

This platform aims to answer a much more valuable question:

> **"What does this news actually mean?"**

Instead of acting as another chatbot, this project is designed to function as an **AI News Intelligence Platform** capable of:

* Understanding user intent
* Planning execution strategies
* Retrieving information from multiple sources
* Analyzing news
* Comparing events
* Detecting trends
* Generating insights
* Producing structured, explainable responses

The long-term vision is:

> **Perplexity × Bloomberg Terminal × Research Analyst**

---

# Why This Project Exists

Modern AI applications are moving beyond single-prompt chatbots toward **agentic systems** where multiple specialized AI agents collaborate to solve complex tasks.

This project explores that architecture from first principles.

Rather than relying on one large prompt, the system is designed around specialized agents with clear responsibilities. LangGraph owns workflow execution; the Planner Agent produces an execution plan, and LangGraph routes between agent nodes to carry it out.

The objective is to learn and demonstrate:

* Multi-Agent Systems
* Agent Orchestration
* Tool Calling
* Retrieval-Augmented Generation (RAG)
* Memory
* Evaluation
* Production Engineering
* Modern Backend Architecture

---

# MVP (Version 1)

The first milestone focuses on a minimal but production-ready architecture.

Workflow:

User

↓

Planner Agent

↓

Information Retrieval Agent

↓

Summarizer Agent

↓

Response Composer

↓

User

The emphasis is on building a strong architectural foundation before expanding into more advanced capabilities.

---

# Planned Features

## Current

* Planner Agent
* Information Retrieval Agent
* Summarizer Agent
* Response Composer
* React Frontend
* FastAPI Backend
* Dockerized Development Environment

## Future

* Timeline Agent
* Comparison Agent
* Insight Agent
* Trend Analysis
* Fact Checker
* Bias Detection
* Credibility Scoring
* Memory
* RAG
* Vector Search
* Streaming Responses
* Evaluation Framework
* Monitoring & Observability

---

# High-Level Architecture

```text
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
Frontend
```

LangGraph owns workflow execution. The Planner Agent produces an execution plan; LangGraph executes that plan by routing between agent nodes.

As the project evolves, additional specialized agents will be integrated without changing the overall architecture.

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

# Repository Structure

```text
Multi-Agent-News-Intelligence-Platform/

backend/

frontend/

docs/

README.md

PROJECT_CONTEXT.md

CLAUDE.md

LEARNING_JOURNAL.md
```

---

# Project Documentation

The repository contains detailed design documents covering the complete engineering process.

* [Product Requirements Document (PRD)](docs/PRD.md)
* [High-Level Design (HLD)](docs/HLD.md)
* [Low-Level Design (LLD)](docs/LLD.md)
* [Architecture Decision Records (ADR)](docs/ADR)
* [Learning Journal](LEARNING_JOURNAL.md)

These documents are intentionally maintained alongside the implementation to demonstrate engineering decisions rather than only the final code.

---

# Current Status

**Sprint 1 — Project Bootstrap: Complete**

Delivered: repository structure, FastAPI backend with a config layer and health endpoint, React + TypeScript frontend proving live backend connectivity, and a Dockerized dev environment (`docker-compose up` runs the whole stack). See [`docs/sprints/SPRINT_1.md`](docs/sprints/SPRINT_1.md) for the full ticket log.

**Sprint 2 — Execution Engine: Complete**

Delivered: a real LangGraph workflow (`START → Planner → Retrieval → Summarizer → Response Composer → END`) with fully mocked node logic — zero LLM calls, zero real tool calls. Proves the orchestration engine itself works before any real intelligence is introduced. See [`ADR 0001`](docs/ADR/0001-langgraph-execution-engine.md) for the design rationale and [`docs/sprints/SPRINT_2.md`](docs/sprints/SPRINT_2.md) for the full ticket log.

No business logic (real reasoning, real tool calls, persistence) has been implemented yet — that remains intentional. Sprint 3's scope is not yet planned; it'll be designed next, replacing mocked node logic with real implementations without changing the graph's structure.

---

# Learning Objectives

This project is being built as a learning journey to gain practical experience with:

* Agentic AI Systems
* Multi-Agent Orchestration
* Backend Architecture
* FastAPI
* React
* Docker
* CI/CD
* System Design
* Software Engineering Best Practices

Every major architectural decision is documented before implementation.

---

# Contributing

This project is currently under active development.

Suggestions, discussions, and architecture reviews are always welcome.

---

# License

This project will be released under the MIT License.
