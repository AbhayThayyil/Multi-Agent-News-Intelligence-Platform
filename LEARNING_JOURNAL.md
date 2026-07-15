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

### T1.5 — CORS configuration

**Date:** 2026-07-13

**What was done:** Registered FastAPI's `CORSMiddleware` in `app/main.py`, using `settings.cors_origins` (from T1.3) as the allowlist, with `allow_credentials=False` (no cookie/session auth exists yet — Sprint 1 is stateless).

**Why:** Browsers block a page from reading a cross-origin response unless the server explicitly allows it via CORS headers. The frontend (`http://localhost:5173`) and backend (`http://localhost:8000`) are different origins, so without this, T2.3's frontend health-check call would fail *only in the browser* — a classic trap since `curl`/Postman never enforce CORS, only real browser JS does.

**Problem it solved:** Without CORS configured, the backend works fine standalone but silently blocks the frontend once it exists.

**Verification:** started the server and sent requests with different `Origin` headers — `http://localhost:5173` got back `access-control-allow-origin: http://localhost:5173` (browser would allow reading the response); `http://evil.com` got no such header (browser would block it), even though the server answered both with `200 OK` — CORS is enforced client-side, not by refusing the request.

**Node/Express equivalent:** the `cors` npm package — `app.use(cors({ origin: allowedOrigins, credentials: false }))`. Same concept, same beginner trap (CORS errors only show up in the browser console, never in `curl`).

---

## Sprint 1 — Frontend

### T2.1 — Initialize Vite + React + TypeScript

**Date:** 2026-07-13

**What was done:** Scaffolded `frontend/` with `npm create vite@latest . -- --template react-ts`. Installed and wired up `nvm` (present via Homebrew but never sourced in `~/.zshrc`), installed Node 22 LTS through it, and added `frontend/.nvmrc` pinning this project to Node 22 — same role as `backend/.python-version`, one file per ecosystem.

**Why:** Vite + React + TypeScript was the already-agreed frontend stack. `nvm` was needed once Node itself became the blocker (below), so this project can use a modern Node version without changing the one global Node install other projects on this machine depend on.

**Gotcha encountered (the real story):** The scaffolded Vite 8 defaults to **Rolldown**, a new Rust-based bundler, which needs a native platform binary (`@rolldown/binding-darwin-arm64`) as an optional dependency. On the machine's existing Node (`v20.15.1`, installed as a single global binary with no version manager), that binary silently failed to install — a known npm bug with optional dependencies, not a problem in our code. Node 20 was also already past its end-of-life support window, so patching around the symptom (e.g. pinning to an older Vite) would have left the project on an unmaintained runtime. Root-caused it to Node itself, then fixed it properly: installed `nvm`, installed Node 22 LTS through it (leaving the original `/usr/local/bin/node` untouched for other projects), and confirmed the native binding installed and `npm run dev` served successfully on the new version.

**Problem it solved:** Frontend tooling now runs on a supported Node version, isolated per-project via `.nvmrc`, instead of silently depending on a shared, outdated global Node install.

**Verification:** clean install (`rm -rf node_modules package-lock.json && npm install`) showed no engine warnings, `node_modules/@rolldown/binding-darwin-arm64` was present, and `npm run dev` served `200 OK` on a test port.

**Node/Express comparison:** `.nvmrc` is itself a Node-ecosystem concept — no separate translation needed — but it plays the exact same role as `backend/.python-version`: one small file, read automatically by the version manager (`nvm` vs `uv`), so every contributor (and CI, later) runs the same runtime version without manual coordination.

### Pulled forward: Python cache rules in `.gitignore` (originally T4.1)

**Date:** 2026-07-13

**What/why:** `__pycache__/` directories (holding `.pyc` — compiled Python bytecode, auto-regenerated on every run) started showing up as untracked in `git status`. Root `.gitignore` was deliberately left minimal after T1.3 (just `.env` rules), with full Python/Node coverage deferred to T4.1. Rather than let cache clutter accumulate for several more tickets, pulled forward just the Python rules (`__pycache__/`, `*.pyc`, `.venv/`) now — same reasoning as pulling forward the `.env` rule earlier. `.venv/` here is a harmless backstop; `uv` already self-ignores it via a nested `.gitignore`.

### T2.2 — Basic frontend folder structure

**Date:** 2026-07-13

**What was done:** Created `frontend/src/api/` and `frontend/src/components/`, each holding a `.gitkeep` placeholder (empty otherwise).

**Why / the git quirk behind it:** Git only tracks files, never directories — an empty folder isn't something git can commit at all. That's different from the backend's T1.2, where `__init__.py` gave every empty layer folder real substance from day one. `.gitkeep` is purely a developer convention (not a git feature) — an empty file whose name signals "this folder is intentional," which incidentally makes the folder exist in git too.

**Problem it solved:** Makes the frontend's folder decision (where API code vs. components live) visible and committable on its own, rather than being an invisible side effect of wherever T2.3's first file happens to land.

**Node/Express equivalent:** Same convention shows up in Express projects too — a `routes/` or `controllers/` folder with a `.gitkeep` before the first route file exists, for the identical reason (npm/git don't track empty directories either).

### T2.3 — Health-check page

**Date:** 2026-07-13

**What was done:** `src/api/health.ts` (typed `fetchHealth()`), `src/components/HealthStatus.tsx` (loading/error/success rendering via `useEffect`+`useState`), `App.tsx` rewritten to render it. Removed now-dead template files (`App.css`, template assets) since nothing imports them anymore. Added `.env.example` for `VITE_API_BASE_URL`.

**Why:** `BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'` mirrors `settings.py`'s pattern exactly — a default baked into code, `.env` only needed to override it, so the frontend runs with zero setup. Plain `useEffect`/`useState` instead of a data-fetching library, matching the earlier decision to keep the stack minimal for one API call.

**Problem it solved:** First concrete, browser-verified proof that the full chain works: React → `fetch()` → CORS-approved cross-origin request → FastAPI → Pydantic-validated response → rendered DOM. Backend and frontend existed independently before this; now they're actually connected.

**Concept worth remembering — `import.meta.env` vs Node's `process.env`:** Vite's env system, not the same mechanism as Node. (1) Only `VITE_`-prefixed vars are exposed to browser code at all — a deliberate boundary so non-prefixed secrets never leak into client-side JS. (2) Values are baked in at **build time**, not read live at runtime — changing `.env` requires restarting the dev server, unlike `process.env` in a running Express process.

**Gotcha encountered during verification:** CORS failed on first browser test — looked like a bug, wasn't. Default port `5173` was already occupied by an unrelated process on this machine, so the frontend was tested on `5183` instead, but the backend's CORS allowlist (from T1.3) only had `5173`. Fixed by temporarily widening the backend's `.env` for the test only — same "environment collision produces a false signal" class of issue as the port-8000 conflict in T1.4.

**Verification:** ran both servers, opened the actual page in a browser (not just `curl`) — rendered `"Backend status: ok (development)"`, confirmed via screenshot and network tab (`GET /api/health` → `200`).

**Node/Express equivalent:** `useEffect` calling `fetch()` on mount ≈ any client-side fetch-on-load pattern in a React frontend served by an Express backend — same idea regardless of framework. `import.meta.env` has no Express equivalent since Express is server-only and reads `process.env` directly at runtime; the build-time/browser split is specific to frontend bundlers like Vite.

---

## Sprint 1 — Docker

### T3.1 — Backend Dockerfile

**Date:** 2026-07-13

**What was done:** `backend/Dockerfile` (base image `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`, dependencies installed before app code copied, `uv run uvicorn ... --reload`) and `backend/.dockerignore` (excludes `.venv`, `__pycache__`, `.env`, `.git` from the build context).

**Why:**
- Dependencies (`pyproject.toml`/`uv.lock`) are copied and `uv sync` run *before* `COPY app ./app`, exploiting Docker's layer caching — if only app code changes, Docker reuses the cached dependency-install layer instead of reinstalling on every rebuild.
- `--host 0.0.0.0` (not the uvicorn default `127.0.0.1`) is required for the container's port mapping to actually reach the app from outside — binding to `127.0.0.1` inside a container makes it unreachable even with `-p` port mapping.
- `--reload` matches Sprint 1's framing as a dev environment; it only sees file changes inside the container's own filesystem, so it needs a volume mount (coming in T3.3) to be useful for local development.

**Problem it solved:** The backend can now run identically anywhere Docker is available, without Python/`uv`/dependencies installed on the host at all.

**Verification:** built the image (`docker build`), ran it with port mapping (`-p 8020:8000`), and confirmed `GET /api/health` returned the expected JSON through the container — not just that the build succeeded.

**Node/Express equivalent:** Structurally identical to a Node Dockerfile — `COPY package.json package-lock.json ./` + `RUN npm ci` *before* `COPY . .`, for the exact same layer-caching reason. `.dockerignore` excluding `.venv` here ≈ excluding `node_modules` there — both are large, platform-specific, and get reinstalled inside the container regardless.

**Concept worth remembering — how this differs from "running locally":** every prior verification (T1.4, T1.5, T2.3) ran `uv run uvicorn ...` directly on the host Mac, using its own Python/`.venv`/OS — if a teammate's machine differs (Python patch version, OS, missing system library), behavior can differ ("works on my machine"). `docker build` instead constructs a completely separate, isolated Linux filesystem from scratch (starting from the `ghcr.io/astral-sh/uv:...` base image, not from anything on the Mac), copies in only what the Dockerfile specifies, and installs dependencies inside *that* filesystem. The result — an **image** — is a frozen template; `docker run` starts an actual running instance of it (a **container**), using the Python/dependencies that live inside the container, not the host's. `-p 8020:8000` is a port-mapping tunnel — the container's network is walled off by default, and this forwards traffic from a host port into the container's internal port. Payoff: the same image runs identically on any machine with Docker installed, no local Python/`uv`/dependency setup required at all. Not Python-specific — the same pattern applies to any backend language.

### T3.2 — Frontend Dockerfile

**Date:** 2026-07-13

**What was done:** `frontend/Dockerfile` (base image `node:22-slim`, `npm ci` before app code copied, runs `npm run dev -- --host 0.0.0.0`) and `frontend/.dockerignore` (excludes `node_modules`, `dist`, `.env`, `.git`).

**Why `node:22-slim` over `node:22-alpine`:** Alpine uses `musl` libc instead of glibc, which has a real history of missing prebuilt native bindings for certain npm packages — the *exact* class of bug hit and fixed on the host in T2.1 (Rolldown's native binding failing to install). Chose `slim` specifically to avoid re-triggering that inside the container; confirmed by a clean build with no missing-binding errors.

**Problem it solved:** Frontend now runs in an isolated, portable environment too, matching what T3.1 gave the backend — no local Node/npm setup required on any machine with Docker.

**Verification:** built the image, ran it with `-p 5193:5173`, confirmed the container log shows Vite bound to `0.0.0.0`, and the root page returned `200` through the mapped port.

### T3.3 — docker-compose.yml

**Date:** 2026-07-13

**What was done:** Root-level `docker-compose.yml` building and running both `backend` and `frontend` services together, each with a bind-mounted source volume (for live-reload) plus an **anonymous volume** protecting `.venv`/`node_modules` from being overwritten by the mount.

**Why the anonymous volume matters:** `volumes: [./backend:/app, /app/.venv]` — the first line bind-mounts host code into the container (enabling hot-reload); the second, with no host path before the colon, tells Docker to carve that specific subfolder back out and let the container manage it independently. Without it, the host's macOS-built `.venv`/`node_modules` would overwrite the container's own Linux-built copies — the exact same root cause as the Rolldown/musl native-binding failures from T2.1/T3.2, just triggered a different way (host binaries inside a Linux container instead of the wrong libc).

**Problem it solved:** One command (`docker compose up`) now builds and runs the whole stack with correct networking/ports, instead of manually running `docker build`/`docker run` twice and keeping them in sync by hand.

**Verification (beyond "it built"):**
1. `docker compose up -d --build` — both containers started.
2. `curl` confirmed both the backend health endpoint and frontend root page respond through mapped ports.
3. Explicitly checked *inside* both containers (`docker compose exec ... ls .venv/...` / `node_modules/.bin`) that real dependencies were present — confirming the anonymous-volume protection actually worked, not just assuming it.
4. **Touched a backend file on the host** and watched the container's own logs show `uvicorn`'s reloader restart on its own — proving the full T3.1/T3.2/T3.3 hot-reload chain works end-to-end, not just in theory.

**Practical note:** verified using a temporary, uncommitted `docker-compose.override.yml` with alternate ports (`8030`/`5193`), since the standard `8000`/`5173` are occupied on this host by an unrelated project. The committed file uses the standard ports — running it while those other processes are up will hit the same "address already in use" error seen earlier.

**Node/Express equivalent:** No translation needed — Compose files are language-agnostic. The `node_modules` anonymous-volume trick shown here is a very common pattern in any dockerized Node dev setup, for the identical reason.

---

## Sprint 1 — Repo Hygiene

### T4.1 — Root .gitignore

**Date:** 2026-07-13

**What was done:** Most substance was already pulled forward earlier (`.env` rules in T1.3, Python cache rules mid-Sprint). What was actually missing at the root: OS junk files (`.DS_Store`, `Thumbs.db`), editor folders (`.vscode/`, `.idea/`), and defensive Node coverage (`node_modules/`, `dist/`) in case anything outside `frontend/` ever needs it — `frontend/.gitignore` already scopes Node artifacts correctly on its own.

**Decision — what was deliberately left out:** cache directories for tools not yet introduced (`.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`) were skipped, per the project's "add only when a real requirement exists" principle — they'll get added in whichever ticket actually introduces those tools.

**Verification:** created test `.DS_Store` files at root and inside `backend/`, confirmed `git check-ignore -v` matched both against the new root rule, then removed the test files.

---

## Sprint 1 — Closeout Retrospective

**Date:** 2026-07-13

**Gotcha from the final verification pass — Docker Compose merges `ports:` lists, it doesn't replace them.** Tried to verify the Sprint Exit Criteria using a `docker-compose.override.yml` with alternate ports (to avoid touching the host's other project occupying 8000/5173). Compose merges list-type fields like `ports:` by *concatenation*, not override — so both the base file's `8000:8000` and the override's alternate mapping ended up active simultaneously, briefly making our backend container reachable on port 8000 too (the same port the host's unrelated `akamai-cdn-billing-backend` project was using). No lasting harm — the other project's process was never killed, just temporarily shadowed at the network layer — but this is a real Compose behavior worth remembering: **to fully override a port mapping, edit the value directly (or use `${VAR:-default}` substitution), not an override file's `ports:` list.**

**Second layer of that same lesson:** once ports were remapped correctly, the frontend still failed — its `VITE_API_BASE_URL` fallback default (`http://localhost:8000`, baked in during T2.3) didn't know about the remap, and separately, once that was fixed too, the backend's CORS allowlist (fixed default `http://localhost:5173`, from T1.5) rejected the remapped frontend's origin. Each fix surfaced the next mismatch — a good concrete illustration of how many independent pieces (compose ports, frontend's default API URL, backend's CORS allowlist) all have to agree, and how remapping one without the others just shifts the failure point rather than fixing anything. The actual committed configuration was correct throughout; every failure was self-inflicted by test-only port substitutions.

**Final verification, done properly:** waited for the host's other project to free ports 8000/5173, ran `docker compose up` with the real committed config (no overrides at all), and confirmed in an actual browser that `http://localhost:5173` rendered "Backend status: ok (development)" — the genuine, unmodified proof of the Sprint Exit Criteria.

**What Sprint 1 actually built:** a layered FastAPI backend (config → API → schemas) and a React+TypeScript frontend, each independently Dockerized, wired together via `docker-compose.yml` with working hot-reload in both directions. No business logic, LangGraph, or persistence — exactly as scoped, avoiding the over-engineering the project explicitly warns against.

**Recurring theme across the whole sprint:** most real gotchas were environment/tooling issues, not application logic bugs — `uv`/Homebrew permission failures, Rolldown's native-binding failure on outdated Node, Alpine vs. slim libc differences, and this Compose port-merging behavior. The application code itself (settings, health endpoint, CORS, the React health-check page) worked essentially as designed once written. Worth remembering going into Sprint 2: budget time for environment surprises, not just feature logic.

---

## Sprint 2 — Execution Engine

### ENGINE-001 — Learn LangGraph concepts

**Date:** 2026-07-15

**Understanding, in my own words (corrected after a first pass):**

1. **State** — a shared dict-like object that carries the accumulated results of every node. It starts with just `{query}`; after each node runs, whatever new field(s) that node produced get merged into it. Crucially, a node never refers to *another node* — it only ever reads and writes **fields in the shared state**. Retrieval doesn't know Planner exists; it just reads `query` and `execution_plan`. The state object is the *only* thing connecting nodes — this is exactly the "agents don't call each other directly" rule from `PROJECT_CONTEXT.md`, made concrete.

2. **Nodes** — units of work. Plain functions that look at the current state and do whatever their one job is, then return the new field(s) they're contributing.

3. **Edges** — **not** decided by the node itself. My first instinct was wrong here: I thought a node's function could decide which edge to take next. Actually, for Sprint 2, edges are fixed connections wired up when *building* the graph (e.g. `graph.add_edge("planner", "retrieval")`), completely independent of what the node returns — the node's job ends the moment it returns its state update. Real state-driven branching exists (**conditional edges** — a separate routing function attached to the edge, which inspects state and picks the next node from several options), but that's a distinct piece of graph-wiring code, not the node deciding anything. Deliberately deferring conditional edges to a later sprint — Sprint 2 uses only fixed edges (`Planner → Retrieval → Summarizer → Response Composer`, always in that order, no branching), per the "one sprint, one concept" mock-first approach in ADR 0001.

4. **START / END** — not states themselves, just markers. `START` is the entry point where the initial `{query}` enters the graph; `END` is the exit point where LangGraph hands back whatever the final accumulated state contains.

**Problem this ticket solved:** forced actually understanding LangGraph's mental model — state as the only channel between nodes, edges as fixed graph-wiring rather than node-level decisions — before writing any graph code in ENGINE-002+. The edges misunderstanding in particular would have led to writing routing logic *inside* node functions later, which contradicts the Planner-plans/LangGraph-executes split the whole architecture is built on.

### ENGINE-002 — Define shared state

**Date:** 2026-07-15

**What was done:** Added `langgraph` as a dependency; created `app/graph/state.py` with a `GraphState(TypedDict, total=False)` holding `query`, `execution_plan`, `articles`, `summary`, `response`.

**Decisions made:**
- **`TypedDict` over Pydantic** for graph state — LangGraph's own docs/ecosystem are built primarily around `TypedDict`; using it avoids learning two libraries' semantics simultaneously while still learning LangGraph's actual mechanics. Tradeoff: no runtime validation — a node could return a wrong-shaped value and nothing would catch it until a type-checker or a later bug surfaced it. Acceptable for now since every node's output is hand-written/mocked this sprint.
- **`total=False`** — makes every field optional, since the real state genuinely doesn't have all five fields until the graph finishes; only `query` exists at `START`.
- **`articles`/`response` left loosely typed (`list[dict]`, `dict`)** rather than given dedicated schemas — their real shape isn't known until Sprint 3's real Retrieval/Response Composer logic exists.

**Verification:** didn't just check the file imports cleanly — actually constructed `StateGraph(GraphState)` from LangGraph and confirmed it accepts the type without error, and built a partial state (`{"query": "..."}`) to confirm the "not all fields present yet" case works as intended.

**Node/Express equivalent:** closest analogy is a shared TypeScript `interface` with optional fields (`query?: string`) passed through a pipeline — same compile-time-only guarantee as `TypedDict`; nothing stops a JS function at runtime from returning the wrong shape without an added validator like `zod`.

### ENGINE-003 — Planner node (mock)

**Date:** 2026-07-15

**What was done:** `app/agents/planner.py` — `planner_node(state: GraphState) -> GraphState` returning a hardcoded `{"execution_plan": ["retrieve", "summarize"]}`. Not connected to an LLM.

**Decision — didn't fake-read `query`:** the ticket description says the Planner "reads query from state," but the function doesn't actually reference `state["query"]` anywhere, since the mock's output is fully hardcoded regardless of input. Wrote it honestly instead of adding an unused `query = state["query"]` line just to match the ticket's wording — dead code with no real justification. The function still accepts `state` (required for the node interface), it just doesn't need any particular field yet.

**Problem it solved:** proves a node function can be written, registered, and invoked inside LangGraph's actual execution engine — the mechanical piece Sprint 2 exists to validate — before any real reasoning exists.

**Verification (two layers, not just "it runs"):**
1. Direct function call: `planner_node({"query": "..."})` returns exactly `{"execution_plan": ["retrieve", "summarize"]}`.
2. Built a real minimal single-node graph (`START → planner → END`) with LangGraph's actual `StateGraph`/`.compile()`/`.invoke()`, and confirmed the final state contained **both** `query` (from the input) and `execution_plan` (from the node's return) — concrete, first-hand proof of ENGINE-001's "LangGraph automatically merges a node's partial return into the accumulated state" concept, not just a claim from the docs.
