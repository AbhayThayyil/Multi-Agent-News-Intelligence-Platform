# Learning Journal

This document records what was learned while implementing each ticket — the reasoning and problems solved, not just a changelog of what was built. Entries are grouped by sprint.

---

## Sprint 1 — Project Bootstrap

### T1.1 — Initialize backend project with `uv`

**Date:** 2026-07-13

**What was done:**
- Installed `uv` and initialized `backend/` as a `uv`-managed Python project pinned to Python 3.12.
- This generated `pyproject.toml` (project metadata + dependencies), `.python-version` (pins the interpreter version), and — on first `uv run` — `.venv` (isolated environment) and `uv.lock` (locked, reproducible dependency versions).
- Verified the environment end-to-end with `uv run main.py`, which downloaded CPython 3.12 and executed successfully.
- Removed the placeholder `main.py` `uv init` generates by default — it's flat boilerplate that doesn't match the layered `app/` structure planned for T1.2.

**Why:**
`uv` was chosen over `pip + requirements.txt` / Poetry because it's a single tool for both interpreter version management and dependency resolution, and it produces a lockfile. Reproducibility matters for a project that explicitly aims to be production-quality, not a script that only runs on one machine. This had to be the first backend ticket because every later piece (FastAPI app, health endpoint, Docker image) depends on having a working, pinned Python environment underneath it.

**Problem it solved:**
`backend/` was an empty folder with no way to install or pin dependencies. Now every dependency added in later tickets resolves into `uv.lock`, so the environment stays reproducible across machines instead of drifting.

**Gotchas encountered:**
- Homebrew failed to install `uv` because `/usr/local/bin` and `/usr/local/lib` weren't writable by the user (would have required `sudo chown` on shared system directories). Used `pip install --user uv` instead — installs to the user's own site-packages, no sudo needed.
- The `pip --user` install location (`~/Library/Python/3.14/bin`) isn't on `PATH` by default — had to add `export PATH="$HOME/Library/Python/3.14/bin:$PATH"` to `~/.zshrc`.
- The coding sandbox's Bash tool runs non-interactive shells that don't source `.zshrc`, so commands during the session had to reference `uv`'s full path directly. This is a sandbox quirk only — the user's actual terminal picks up the `PATH` change normally.

### T1.3 — Config layer (`pydantic-settings`)

**Date:** 2026-07-13

**What was done:**
- Added `pydantic-settings` as a dependency and created `app/config/settings.py`: a `Settings(BaseSettings)` class (`app_env`, `cors_origins`) plus a `get_settings()` function wrapped in `@lru_cache`.
- Added `backend/.env.example` and a root `.gitignore` (currently just `.env` / `.env.*`, keeping `.env.example` un-ignored).

**Why:**
- `get_settings()` wrapped in `lru_cache`, rather than a plain module-level `Settings()` instance, so FastAPI routes can depend on it via `Depends(get_settings)` later — real Dependency Injection instead of importing a global object directly, per the DI principle in `CLAUDE.md`.

**Decisions made (with reasoning):**
1. **List-typed env vars use JSON array syntax** — e.g. `CORS_ORIGINS=["http://localhost:5173"]` — because that's `pydantic-settings`'s native parsing for `list[str]` fields, avoiding a hand-written comma-split validator for one field. Trade-off: slightly unusual to hand-type compared to a comma-separated string.
2. **Pulled `.gitignore` (`.env` only) and `.env.example` forward from their originally-planned tickets (T4.1/T4.2)** rather than waiting, because T1.3 introduces `.env`-file reading — without an ignore rule in place first, a real `.env` created for local testing could get committed by accident. `.gitignore` will still be expanded to full Python/Node coverage at T4.1.

**Problem it solved:**
- Config values (environment, CORS origins, and future settings like LLM API keys) now have one typed, validated source of truth instead of scattered `os.getenv()` calls, and are safely overridable per-environment via `.env` without risking that file ever being committed.

**Verification:** confirmed `get_settings()` returns correct defaults with no `.env` present, and correctly picks up overrides (`APP_ENV=staging`, multi-origin `CORS_ORIGINS`) from an actual `.env` file (created temporarily for the test, then removed).

**Usage pattern (how this gets consumed later, e.g. in T1.4's health endpoint):**
```python
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)

@app.get("/api/health")
def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "environment": settings.app_env}
```
`get_settings()` is called once at startup (CORS setup) and again per-request (`Depends` injection) — `@lru_cache` guarantees both return the same object, no re-parsing.

**Why not just `os.getenv()` everywhere:** without `pydantic-settings`, you'd also need `load_dotenv()` (from `python-dotenv`) explicitly called before anything reads `.env` — `os.getenv()` alone only sees real environment variables, never a `.env` file on its own. You'd also have to hand-parse `CORS_ORIGINS` with `json.loads()` in every file that needs it, with no shared validation — a malformed value would crash wherever it's first read, instead of failing clearly at startup. `pydantic-settings` centralizes both the `.env` loading and the parsing/validation into one object everyone shares.

**Node/Express equivalent:** the raw `os.getenv()` version above is the same shape as `process.env.CORS_ORIGINS` + manual `JSON.parse()` + `require('dotenv').config()` in Express — `settings.py` plays the role of a shared, validated `config.js`/`config.ts` that every route imports instead of reading `process.env` directly.

### T1.4 — Health endpoint

**Date:** 2026-07-13

**What was done:**
- `app/schemas/health.py` — `HealthResponse` Pydantic model (`status`, `environment`).
- `app/api/health.py` — `APIRouter(prefix="/api")` with `GET /health`, using `Depends(get_settings)` to include the current `app_env` in the response.
- `app/main.py` — the actual FastAPI app instance (`app = FastAPI(...)`), mounting the health router. First real entrypoint the project has.
- Added `fastapi` and `uvicorn[standard]` as dependencies.

**Why:**
- Response goes through a Pydantic model (`HealthResponse`) rather than a raw dict, so FastAPI validates the shape and auto-generates OpenAPI docs from it — matches the project-wide rule that Pydantic defines all request/response contracts.
- The route lives in its own `APIRouter` file rather than directly in `main.py`, so `app/api` scales cleanly as more endpoints (planner, retrieval, etc.) are added later — each gets its own file/router, all mounted onto one `app`.
- Response includes `environment` (beyond the ticket's original minimal `{"status": "ok"}`) specifically to exercise T1.3's config layer with something real and testable, rather than leaving it unused until a later ticket.

**Problem it solved:**
- Gives the project its first actual running server and a concrete way to verify frontend↔backend connectivity once the frontend exists (T2.3) — before this, there was no entrypoint at all.

**Gotcha encountered:** local verification on port 8000 initially failed silently — `curl` returned `{"status":"ok"}` (no `environment` field), which looked like a bug in the new code. The real cause: an unrelated project's `uvicorn` server (`akamai-cdn-billing-backend`) was already bound to port 8000, and `curl` was hitting *that* server, not this one — the new server had actually failed to start (`address already in use`). Always check the server's own startup log, not just the HTTP response, when behavior doesn't match the code. Verified correctly afterward on port 8010.

**Node/Express equivalent:** `APIRouter` ≈ `express.Router()` mounted via `app.use('/api', router)`; `app/main.py` ≈ Express's `server.js`/`app.js` — the one file that creates the app and wires every router together. The Pydantic response validation doesn't have a built-in Express equivalent — closest comparison is manually validating a response with `zod` before sending it.
