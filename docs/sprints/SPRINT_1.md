# Sprint 1 — Project Bootstrap

**Status:** Design approved — implementation in progress.

Goal: build a production-ready project foundation. No business logic, no LangGraph, no persistence — pure scaffolding.

Reference: [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md), [`CLAUDE.md`](../../CLAUDE.md)

A ticket is only checked off once the implementation works, follows the layering/engineering principles in `CLAUDE.md`, and can be explained line-by-line (per the project's Definition of Done).

---

## Backend

- [x] **T1.1 — Initialize backend project with `uv`**
  `pyproject.toml`, virtual env, lockfile. No app code yet — just a working `uv run` environment.

- [x] **T1.2 — Create backend folder structure**
  `app/{api,agents,tools,prompts,services,schemas,models,config}`, each with an empty `__init__.py`. Skeleton only, no logic.

- [x] **T1.3 — Config layer**
  `app/config` using `pydantic-settings`, reading from `.env` (e.g. `APP_ENV`, allowed CORS origins).

- [x] **T1.4 — Health endpoint**
  `GET /api/health` in `app/api`, returns a Pydantic-typed response (`{"status": "ok", "environment": ...}`). Pure API layer, zero business logic.

- [x] **T1.5 — CORS configuration**
  Allow the Vite dev server origin so the frontend can call the backend locally.

## Frontend

- [x] **T2.1 — Initialize Vite + React + TypeScript project** in `frontend/`.

- [x] **T2.2 — Basic frontend folder structure**
  e.g. `src/components`, `src/api` — just enough to hold the health-check call cleanly.

- [x] **T2.3 — Health-check page**
  A minimal page/component that calls `GET /api/health` and renders the result. This is the concrete proof of React ↔ FastAPI communication.

## Docker

- [x] **T3.1 — Backend Dockerfile** (using `uv`).

- [x] **T3.2 — Frontend Dockerfile** (dev mode, Vite).

- [ ] **T3.3 — `docker-compose.yml`**
  Wires both services together with one command to run the whole stack.

## Repo Hygiene

- [ ] **T4.1 — Root `.gitignore`** covering Python + Node artifacts.

- [ ] **T4.2 — `.env.example`** documenting required backend config vars.

- [ ] **T4.3 — First commit**
  Scaffold committed once T1–T3 are done and verified working end-to-end.

---

## Sprint Exit Criteria

- `docker-compose up` runs backend + frontend together.
- Visiting the frontend shows a live health status fetched from `GET /api/health`.
- Folder structure matches `PROJECT_CONTEXT.md`.
- No business logic, LangGraph, or persistence has been introduced.
