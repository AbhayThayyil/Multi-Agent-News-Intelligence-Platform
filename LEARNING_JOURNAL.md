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
