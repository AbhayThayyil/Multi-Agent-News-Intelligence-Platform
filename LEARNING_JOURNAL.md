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

### ENGINE-004 — Retrieval node (mock)

**Date:** 2026-07-15

**What was done:** `app/services/retrieval.py` — `retrieval_node(state) -> GraphState` returning a hardcoded `articles` list (one mock article/source). No RSS, no web search, no real tool calls.

**Decision — folder placement (`app/services/`, not `app/agents/`):** Retrieval is classified as a **Deterministic** node per ADR 0001 (no reasoning), but Sprint 1's original `CLAUDE.md` folder comment grouped "Planner, Retrieval, Summarizer" together under `agents/`. Chose to follow `CLAUDE.md`'s actual layering principle instead (deterministic logic → Services, AI reasoning → Agents) over the stale folder comment, which was updated to match. This means graph nodes are split across folders by *what kind of logic they contain*, not by "is this a node in the graph" — `app/graph/workflow.py` (ENGINE-007) will import from both `agents/` and `services/` when wiring the graph together.

**Consistent with ENGINE-003:** didn't fake-read `execution_plan` even though the ticket text says the node "reads" it — the mock's output doesn't depend on its content yet, so referencing it would be unused/dead code. Same reasoning as the Planner mock.

**Verification:** direct function call, plus chaining `planner_node` → `retrieval_node` in a real two-node LangGraph graph and confirming the final state accumulated all three fields (`query`, `execution_plan`, `articles`) correctly across both nodes — not just that each node works in isolation.

### ENGINE-005 — Summarizer node (mock)

**Date:** 2026-07-15

**What was done:** `app/agents/summarizer.py` — `summarizer_node(state) -> GraphState` returning a hardcoded `{"summary": "Mock Summary"}`. No LLM call.

**Folder placement:** `app/agents/`, not `app/services/` — Summarizer is an **AI node** per ADR 0001 (it's meant to reason over articles once real), unlike Retrieval which went to `services/` in ENGINE-004. Same rule applied consistently: folder is decided by node classification, not by "does this run inside the graph."

**Consistent with ENGINE-003/004:** didn't fake-read `articles` — output is fully hardcoded regardless of input at this mock stage.

**Verification:** direct function call, plus chaining `planner_node → retrieval_node → summarizer_node` in a real three-node LangGraph graph, confirming the final state accumulated all four fields (`query`, `execution_plan`, `articles`, `summary`) correctly in sequence.

### ENGINE-006 — Response Composer

**Date:** 2026-07-15

**What was done:** `app/services/response_composer.py` — `response_composer_node(state) -> GraphState` reading `state["summary"]` and `state["articles"]` and composing `{"response": {"answer": ..., "sources": ...}}`.

**Different from ENGINE-003/004/005:** this is the first node that genuinely reads its input fields, rather than avoiding "dead code" by ignoring unused state. Response Composer's formatting logic is deterministic *permanently* — it's not a placeholder standing in for future AI reasoning like Planner/Retrieval/Summarizer's mocks are. So actually using `summary`/`articles` here is real logic, not something to defer.

**Folder placement:** `app/services/`, matching Retrieval (ENGINE-004) — Deterministic per ADR 0001.

**Verification — a milestone:** direct function call, plus building the **complete four-node chain** (`planner → retrieval → summarizer → response_composer`) in a throwaway test graph and confirming the final state contains exactly the five fields the Sprint Exit Criteria calls for (`query`, `execution_plan`, `articles`, `summary`, `response`) — the whole mocked pipeline works end-to-end, even before ENGINE-007 formally commits the graph wiring as its own file.

### ENGINE-007 — Connect the complete graph

**Date:** 2026-07-15

**What was done:** `app/graph/workflow.py` — `build_graph() -> CompiledStateGraph`, wiring `START → planner → retrieval → summarizer → response_composer → END` via LangGraph's `StateGraph`, importing each node from its actual home (`app.agents.*` for AI nodes, `app.services.*` for deterministic ones).

**Problem it solved:** this is the ticket that turns five previously-independent pieces (state shape, four separate node files) into one real, committed, invokable graph — the actual deliverable ADR 0001 was written to justify, and the concrete answer to "does the orchestration layer work" independent of any real AI or tool logic.

**Verification (two layers, not one):**
1. Imported `build_graph` from the real committed module (not a copy-pasted test script like ENGINE-006 used) and confirmed `graph.invoke({"query": "..."})` produces the exact final state the Sprint Exit Criteria specifies.
2. Invoked it again with a **different** query — one that literally says "Show me a timeline" — and confirmed `execution_plan` and every other field stayed identical. This concretely proves the mocks are fully input-independent right now, and sets up the exact contrast Sprint 3 will demonstrate: a real Planner would change `execution_plan` for that query, while the graph's structure (this file) wouldn't need to change at all.

**Sprint 2 Exit Criteria: met.** All ENGINE-001–007 tickets complete.

---

## Sprint 2 — Closeout Retrospective

**Date:** 2026-07-15

**Re-verified fresh on a clean `main`** (not just trusting each ticket's individual verification): `build_graph()` invoked with `{"query": "What happened in AI this week?"}` produced exactly the final state the Sprint Exit Criteria specifies. Also confirmed `backend/pyproject.toml` contains only `fastapi`, `langgraph`, `pydantic-settings`, `uvicorn` — no LLM SDK, no RSS/search library — genuinely zero AI or tool dependencies snuck in anywhere, not just "we didn't call one."

**What Sprint 2 actually built:** a real, running LangGraph graph — `START → Planner → Retrieval → Summarizer → Response Composer → END` — with every node's logic fully hardcoded. Five files total (`app/graph/state.py`, `app/graph/workflow.py`, `app/agents/planner.py`, `app/agents/summarizer.py`, `app/services/retrieval.py`, `app/services/response_composer.py` — six, correcting the count), each verified individually *and* in combination as they were chained together ticket by ticket (two-node, then three-node, then four-node graphs before the final committed version).

**A recurring engineering lesson, made concrete this sprint:** the "don't fake-read unused state fields" rule that came up in ENGINE-003/004/005 (Planner/Retrieval/Summarizer never touch fields their hardcoded logic doesn't need) versus ENGINE-006 genuinely needing to read `summary`/`articles` because Response Composer's formatting logic is real and permanent, not a stand-in for future AI. Same principle — "don't write code you can't explain" — produced two different-looking outcomes depending on whether the underlying logic was a temporary mock or genuinely finished work. Worth remembering in Sprint 3: as mocks get replaced with real logic, several of those "don't touch this field" lines will become real reads, and that's expected, not a sign the earlier code was wrong.

**Folder-placement decision (ENGINE-004) held up across the whole sprint:** classifying nodes as AI (`app/agents/`) vs. Deterministic (`app/services/`) per ADR 0001, rather than grouping all graph nodes together, meant `app/graph/workflow.py` imports from both folders — a small but real test of whether the layering principle from `CLAUDE.md` actually works in practice, not just on paper. It did, cleanly.

**What Sprint 3 will actually change:** per ADR 0001's whole premise, none of `app/graph/workflow.py`'s wiring should need to change — only what's *inside* `planner_node`, `retrieval_node`, and `summarizer_node` gets replaced (real reasoning, a real RSS tool, real LLM summarization). If Sprint 3 ends up needing to touch the graph's structure itself, that's a signal Sprint 2's design had a gap worth understanding, not just a normal next step.

---

## Sprint 3 — AI Infrastructure

### AI-001 — Choose and configure the LLM provider

**Date:** 2026-07-17

**What was done:** Added `litellm` as a dependency. Extended `Settings` with `openrouter_api_key` (required, validated to reject blank values, not just missing ones) and `llm_model` (defaulted to a real, verified-working free model). Verified a real completion through LiteLLM + OpenRouter, using `Settings`' actual committed default — no LangGraph changes anywhere.

**Decision — extra validation on the API key:** plain `str` typing only rejects a field that's *completely absent* — an empty `OPENROUTER_API_KEY=` line in `.env` satisfies `str` just fine and would have loaded silently as `''`. Verified this directly (it did load silently before the fix). Added a `field_validator` to explicitly reject blank/whitespace-only values too, so a forgotten key fails loudly and clearly at settings-load time, not later as a confusing error from OpenRouter itself several layers away from the real mistake.

**Gotcha — my first two guessed free-model names were both stale.** Initially proposed `meta-llama/llama-3.3-70b-instruct:free` based on general knowledge of OpenRouter's catalog — it had been retired to a paid-only model by the time we actually tested. Guessed five more candidates from memory; all failed the same way (`"This model is unavailable for free"` or `"No endpoints found"`). Stopped guessing and queried OpenRouter's live `/api/v1/models` endpoint directly instead, which returned the actual current list of free-suffixed models — `openai/gpt-oss-20b:free` from that real list worked on the first try. **Lesson: OpenRouter's free-tier catalog changes often enough that any specific model name (including ones in this journal) should be treated as unverified until re-checked against the live API** — this is precisely the kind of churn the LiteLLM/OpenRouter abstraction (ADR 0002) is meant to absorb: swapping the model was a one-line config change, not a rewrite, exactly as designed.

**Verification:** confirmed three separate `Settings` validation paths (blank key rejected, fully-absent key rejected, real key accepted), then ran an actual completion call through `get_settings().llm_model` and `.openrouter_api_key` (not hardcoded test values) and got back a real model response — proving the *actual committed configuration*, not just "some code that looks like it," works end-to-end.

**Handling the real API key safely:** the key value only ever flowed through `Settings` (read from the gitignored `.env`); it was never typed inline into a script or command, to avoid it appearing anywhere in this conversation more than once.

### AI-002 — Create an LLM service layer

**Date:** 2026-07-17

**What was done:** `app/llm/client.py` — `LLMClient` class with one method, `complete(prompt: str) -> str`, plus a cached `get_llm_client()` factory (same `@lru_cache` shape as `get_settings()`).

**Decision — constructor injection over reach-in-every-call:** `LLMClient.__init__` receives `api_key`/`model` once at construction; `.complete()` itself never calls `get_settings()`. Chose this over a simpler plain function that reads global config on every call, specifically because this ticket names Dependency Injection as an explicit learning goal — constructor injection is the real version of that; a function reaching for global config on each call would only look like it.

**Why the return type matters:** `.complete()` returns `response.choices[0].message.content` — a plain `str` — never LiteLLM's raw response object. This is the actual mechanism that makes the abstraction from ADR 0002 real: any future caller (the Summarizer, in AI-004) only ever sees plain Python types, so swapping LiteLLM out later wouldn't leak into caller code.

**Problem it solved:** before this, any code wanting an LLM response would need to know LiteLLM's `completion()` signature, the `model="openrouter/..."` string format, and how to unwrap its response object. Now that's sealed inside one file.

**Verification:** ran a real completion through `get_llm_client().complete(...)` and got back an actual model response (plain string, confirmed via `isinstance`). Confirmed `get_llm_client()` caching behaves identically to `get_settings()` — called it twice, same object identity both times (`is`, not just `==`). Also confirmed via `grep` on the file's own imports — not just by assumption — that `client.py` imports nothing beyond `functools`, `litellm`, and `app.config.settings`: zero coupling to LangGraph, agents, or graph state, exactly as the ticket requires.

### AI-003 — Prompt management

**Date:** 2026-07-20

**What was done:** `app/prompts/summarizer.py` — `SUMMARIZER_INSTRUCTIONS` (a module-level constant, the fixed instruction text) plus `build_summarizer_prompt(articles: list[dict]) -> str` (per-call formatting, inserting real article data).

**Decision — constant + function, not one inline string:** separates the part you'd actually tune/version over time (`SUMMARIZER_INSTRUCTIONS`) from the part that just formats per-call data. Directly serves this ticket's named "prompt versioning" learning goal — the instructions are the one thing you'd expect to see change in `git log` over time, distinct from formatting logic that shouldn't.

**A real, useful finding from verification:** ran the built prompt through the actual AI-002 `LLMClient` (not a hypothetical check) using Sprint 2's mock article shape (`{"title": "Mock Article", "source": "Mock RSS"}`). The model correctly replied that it didn't have enough information to summarize — which is the *right* behavior, not a bug: a title and source alone genuinely isn't enough content to summarize, and a well-behaved model saying so (rather than hallucinating a fake summary from nothing) is a good sign the prompt is working as intended. **Flagging forward:** this means once Retrieval becomes real (a future sprint), articles will need an actual body/content field, not just title/source — the mock shape from Sprint 2 won't be sufficient for AI-004's real Summarizer to produce a meaningful summary from mock data alone. Worth keeping in mind when AI-004 decides what mock article content to test against.

**Verification:** confirmed `build_summarizer_prompt()` correctly interpolates article data into the expected format, then ran the actual output through the real LLM client end-to-end — an early integration check across AI-002 and AI-003 together, ahead of AI-004 wiring this into the graph.

### AI-004 — Replace mock Summarizer

**Date:** 2026-07-20

**What was done:** `app/agents/summarizer.py` now builds a prompt (`build_summarizer_prompt`), calls the real LLM (`get_llm_client().complete(prompt)`), and returns the actual response as `summary` — no more hardcoded string. Also enriched `retrieval_node`'s mock articles with a `content` field (still 100% fake/hardcoded, no RSS, no network call) and updated `build_summarizer_prompt` to actually include that content in the formatted output — both necessary once AI-003's finding (title/source alone isn't enough to summarize) needed addressing for real.

**Problem it solved:** this is the ticket ADR 0002's entire premise was building toward — proving that swapping mocked logic for real logic touches *only* the inside of the node function, never `app/graph/workflow.py`'s wiring.

**Verification (the one that mattered most):** ran `build_graph()` — completely untouched since Sprint 2 — end-to-end, and confirmed: Planner still returns its hardcoded plan, Retrieval still returns hardcoded (now richer) mock data, Summarizer produces a genuinely real, LLM-generated summary of that mock content, and Response Composer correctly threads it into the final response — all without a single line of `workflow.py` changing. This is the concrete proof of the architecture holding up under real replacement, not just a claim.

**Observed model-output quirk (not a code bug):** the real response included a stray trailing fragment (`...reasoning benchmarks.parks`) — a generation artifact from this particular free model, not something in our code. Noted for AI-006's "verify summary quality" criterion rather than something to chase down now.

### AI-005 — LLM error handling

**Date:** 2026-07-20

**Discussion, decided before implementing:** retry policy isn't one rule — it's per-error-type. Timeout and rate limit are transient (worth automatic retry); invalid API key and a genuinely nonexistent model are permanent (retrying wastes time on something retrying can never fix). LiteLLM already makes this judgment internally; our job is to configure it (`timeout=30`, `num_retries=2`), not reimplement it. Decided the graph should **fail loudly** rather than return partial results — Response Composer's job is formatting a *real* summary, and there's no API layer yet that would know how to sensibly display a degraded result, so building a partial-result path now would be unused abstraction.

**What was done:** `app/llm/client.py` wraps the LiteLLM call in `try/except`, translating every LiteLLM/OpenRouter exception into our own `LLMError` — callers only ever need to catch one exception type, never a LiteLLM-specific one.

**Verification — three of four failure modes triggered for real, not assumed:**
- **Invalid key:** constructed a client with a fake key, confirmed `LLMError` raised and — via `isinstance()` — confirmed the real `litellm.AuthenticationError` never escapes to the caller.
- **Model unavailable:** a bogus model string surfaced `litellm.BadRequestError`, not the `NotFoundError` I'd expected based on AI-001's retired-model experience (which *was* a `NotFoundError`). Real, first-hand evidence that "model unavailable" isn't one exception type — added an explicit `BadRequestError` branch once this showed up, rather than assuming my first guess covered it.
- **Timeout:** monkey-patched a 0.001-second timeout for one call, confirmed `LLMError` raised with a clear message.
- **Rate limit: not empirically triggered** — reliably forcing a real 429 means hammering the API with rapid requests, wasteful and unkind to a free tier. Implemented following the identical pattern as the three verified branches, but honestly flagging this one as code-reviewed, not proven live.
- **Regression check:** confirmed the real success path (valid key, valid model) still works unchanged.

**Problem it solved:** without this, any LLM failure would surface as a raw LiteLLM exception with LiteLLM-specific types and messages — a real leak of ADR 0002's "hide provider details" promise at exactly the moment (a failure) it matters most.

### AI-006 — End-to-end verification

**Date:** 2026-07-20

**Gap found before verifying:** zero logging existed anywhere in the codebase — `grep` for `import logging`/`logger.` across `backend/app/` found nothing. Since this ticket explicitly asks to verify logging, added minimal logging to `app/llm/client.py` first (model called, success/failure, rough duration) so there was something real to check, rather than reporting a gap on the sprint's own closing ticket.

**Verified all four dimensions through the real compiled graph** (`build_graph().invoke()`), not isolated pieces:

1. **State evolution:** all five fields (`query`, `execution_plan`, `articles`, `summary`, `response`) accumulated correctly in order; `response.answer` matches `summary` exactly, confirming Response Composer still wires correctly with a real Summarizer in place.
2. **Summary quality:** this run produced a clean, coherent summary with no artifacts — confirming AI-004's `.parks` glitch was one-off model variance (a real free model producing slightly different output run to run), not a systematic bug in our code.
3. **Logging:** both our own log lines (`Calling LLM model=...`, `LLM call succeeded model=... duration=...`) and LiteLLM's own internal logging appeared correctly, including the `ERROR` line firing on the deliberate failure test below.
4. **Error handling — through the full graph, not just the isolated client (new for this ticket):** monkey-patched the Summarizer's `get_llm_client()` to return a client with an invalid key, then called `graph.invoke()` directly. Confirmed `LLMError` propagated all the way out of `.invoke()` uncaught — exactly the "fail loudly" design decided in AI-005's discussion, now proven through the actual graph path, not just the client in isolation.

**A real correction to something claimed in AI-005's discussion:** the error-handling test's logs showed LiteLLM attempted the call **3 times** (1 initial + our configured `num_retries=2`) before raising the authentication error — meaning it retried an invalid API key, a permanent failure, exactly as many times as a transient one. AI-005's discussion had assumed LiteLLM's `num_retries` was smart enough to skip retrying non-retryable errors like bad credentials; this is first-hand evidence that assumption doesn't hold for the simple `completion(..., num_retries=2)` usage implemented here — it retries blindly regardless of error type. **Flagging as a known limitation, not silently fixing it now:** a proper fix likely means checking LiteLLM's more advanced per-error retry-policy features (or a custom retry policy object), which is a reasonable candidate for a future hardening pass rather than scope-creeping Sprint 3's closing ticket.

**Sprint 3 Exit Criteria: met**, with the one honest caveat above carried forward.

---

## Sprint 3 — Closeout Retrospective

**Date:** 2026-07-20

**Re-verified fresh on a clean `main`:** ran `build_graph().invoke(...)` again after pulling the merged AI-006 PR, got a clean, coherent real summary, and confirmed the same five-field state shape. Also checked `backend/pyproject.toml` (only `fastapi`, `langgraph`, `litellm`, `pydantic-settings`, `uvicorn` — nothing from the explicit Out of Scope list snuck in) and `git log -- backend/app/graph/workflow.py` — **exactly one commit in its entire history, ENGINE-007 from Sprint 2.** That's not an assumption or a claim taken on faith; it's direct evidence that six tickets of real AI integration work never needed to touch the orchestration engine's wiring, which was the whole premise ADR 0002 was written to test.

**What Sprint 3 actually built:** `app/llm/client.py` (LiteLLM + OpenRouter behind one interface, `complete(prompt: str) -> str`), `app/prompts/summarizer.py` (versioned instructions separate from formatting), a real Summarizer node, and error handling that translates every LLM failure into one exception type (`LLMError`) instead of leaking LiteLLM/OpenRouter specifics.

**The recurring pattern this sprint, more than any other so far: assumptions correcting themselves against real evidence, not staying assumptions.**
- AI-001: assumed a specific free model name was current — it had been retired by the time of testing. Fixed by querying OpenRouter's live API instead of guessing again.
- AI-003: assumed title/source was enough content to summarize — the LLM correctly said otherwise, which was a good sign, not a failure.
- AI-005: assumed "model unavailable" was always a `NotFoundError` — a malformed model name surfaced `BadRequestError` instead.
- AI-006: assumed LiteLLM's retry logic was smart enough to skip retrying permanent failures like a bad API key — log evidence showed it retried 3 times regardless of error type.

None of these were caught by reasoning ahead of time — every one required actually running the code and reading what came back. Worth carrying into future sprints as a working principle, not just a one-off lesson: **when integrating a real external system, assume your first mental model of its behavior is incomplete, and verify against its actual behavior before writing it down as settled.**

**Known limitations carried forward, not fixed in Sprint 3 (deliberately, to stay scoped):** LiteLLM's retry doesn't yet distinguish permanent from transient failures in our configuration; rate-limit handling was implemented but never triggered live; there's still no automated test suite (flagged back in Sprint 2, still true); Planner and Retrieval remain fully mocked, with real reasoning/RSS/web-search intentionally deferred to a future sprint.

---

## Sprint 4 — Tool Infrastructure

### TOOL-001 — Tool architecture review

**Date:** 2026-07-27

**What was done:** Answered four architecture questions before writing any Sprint 4 code, written up as [`ADR 0003`](../docs/ADR/0003-tool-architecture.md).

**Core distinction, in my own words:** a Tool is code that does real I/O against something outside our process, and does so *without making any judgment call* — it doesn't decide whether/when to be called, and it doesn't decide what the result means. The instant code starts judging (is this good enough, which source should I use), it's stopped being a Tool and become a Service or an Agent. This is the same line Sprint 3 already drew for `LLMClient` (a Tool-like abstraction, even though it lives in `app/llm/` rather than `app/tools/` per ADR 0002's earlier reasoning) — ADR 0003 just makes the general principle explicit for the first time, ahead of building a second thing (RSS) that needs to follow it.

**Why this matters concretely for Sprint 4:** RSS logic normalizes to `Article` objects *inside* the Tool (not in `retrieval.py`), and the Planner never learns RSS exists — both direct consequences of the same idea: nothing downstream of a Tool should ever need to know the specific external system's shape or even that it exists, only that "articles can be retrieved."

**Problem it solved:** without this reviewed and written down first, TOOL-003/004 risked repeating the exact anti-pattern Sprint 3 was built to avoid — the RSS parser's provider-specific quirks (feed format, field names) leaking into Retrieval's own logic, and Retrieval becoming hard to swap for a different source later.

### TOOL-002 — Design the Article domain model

**Date:** 2026-07-27

**What was done:** `app/schemas/article.py` — `Article(BaseModel)` with `title`/`source` required, `content`/`published_at`/`url` optional (`| None = None`).

**Decision — Pydantic over dataclass or dict:** Article represents data crossing a trust boundary (RSS is external, untrusted, and messy — TOOL-006 exists specifically because entries can be missing dates/content/links). A `dataclass` gives structure with zero enforcement; a `dict` gives neither. Pydantic validates at the exact point external data enters the system, and it was already a dependency (via `pydantic-settings`/`fastapi`) — no new cost. Also matches the existing pattern (`Settings`, `HealthResponse`) rather than introducing a third convention for structured data.

**Decision — which fields are optional:** deliberately did *not* make every field required. Real RSS feeds legitimately omit `content`, `published_at`, or `url` sometimes — forcing them required would just mean validation failures on realistic data. The *policy* question (should Retrieval accept an article missing content, should something filter it) is left to TOOL-006, not baked into the model's shape.

**Decision — `app/schemas/`, not `app/models/`:** matches `CLAUDE.md`'s already-documented purpose for `schemas/` ("Pydantic contracts") and where `HealthResponse` already lives; `app/models/` has no defined purpose yet and often implies DB-mapped ORM classes elsewhere, which Article isn't.

**Verification — confirmed real validation, not just construction:** built a fully-populated `Article`, a minimal one (confirming optional fields default to `None`), then deliberately fed it a malformed date string and a missing required field — both correctly raised `ValidationError`. Bonus finding: Pydantic didn't just validate the ISO date string, it auto-parsed it into a real `datetime` object.

### TOOL-003 — Build the RSS Tool

**Date:** 2026-07-28

**What was done:** `app/tools/rss.py` — `RSSTool` (constructor-injected `feed_url`/`source`, matching `LLMClient`'s shape), with `fetch() -> list[Article]` splitting HTTP fetching (`httpx`) from feed parsing (`feedparser`), normalizing every entry into an `Article` before returning. Errors wrapped in a new `RSSToolError`, mirroring `LLMError`.

**Gotcha found while verifying, before writing the final module — real, not hypothetical:** the very first test call against BBC's feed URL returned **zero entries**, which looked like a parsing bug. Root cause: `httpx` doesn't follow redirects by default, and BBC's `http://` feed URL 302-redirects to `https://`. The first request silently got a redirect response with no RSS content in it, and `feedparser` correctly found zero entries in *that*. Confirmed the diagnosis directly (checked the 302 status and `Location` header) before fixing it — `follow_redirects=True` is now a deliberate, evidence-based choice, not a guess, and worth remembering as a general httpx gotcha for any future tool that fetches URLs.

**Decision — fetch/parse split, not `feedparser.parse(url)` doing both:** `feedparser.parse()` can take a URL directly, but its internal fetching is harder to control (no clean timeout parameter, `urllib`-based). Splitting so `httpx` does the fetch means real timeout control now, and gives TOOL-005 a natural place to add retry logic — wrapping the `httpx.get()` call specifically, not the whole fetch-and-parse pipeline.

**Verification — proved the "pure retrieval, no judgment" requirement from ADR 0003, not just asserted it:** fetched the real BBC feed (34 entries), and separately parsed the same raw feed content directly with `feedparser` to get its raw entry count — **confirmed the two counts matched exactly**, concrete evidence nothing is being filtered or dropped. Also triggered both error paths for real: a nonexistent domain (network failure → `RSSToolError`) and a non-RSS URL (`example.com`'s HTML → `feedparser`'s `bozo` flag catches it → `RSSToolError`).

### TOOL-004 — Replace mock Retrieval

**Date:** 2026-07-28

**What was done:** `app/tools/base.py` — a `NewsSourceTool` `Protocol` (`fetch() -> list[Article]`), for documentation/type-checking, not full DI. `app/tools/rss.py` gained `get_rss_tool()` (cached factory, config from new `Settings.rss_feed_url`/`rss_source_name` fields). `retrieval_node` now calls `get_rss_tool().fetch()` and converts each `Article` to a dict (`.model_dump()`) before returning, keeping `GraphState.articles`'s existing `list[dict]` contract untouched.

**Decision — Protocol for documentation, not full dependency injection:** without a DI framework (LangGraph nodes are plain functions), true swappability without touching `retrieval.py` at all would require changing how nodes are registered in `workflow.py` — directly conflicting with Sprint 4's "no graph changes" constraint. So `retrieval_node` still directly imports `get_rss_tool`, matching AI-004's exact precedent (`summarizer_node` importing `get_llm_client`) — the `Protocol` documents the contract a future second tool must satisfy, it doesn't eliminate the import.

**Decision — dicts, not `Article` objects, in `GraphState`:** `GraphState.articles` stayed `list[dict]` rather than being upgraded to `list[Article]`, keeping this ticket's ripple contained to `retrieval.py` + `tools/` — `app/prompts/summarizer.py` and `response_composer.py` needed zero changes, since `.model_dump()`'s keys match what they already expected. Upgrading state to carry real domain objects is left as its own explicit future decision, not folded into "swap mock retrieval for real retrieval."

**A real, honest finding from full end-to-end verification:** ran the complete graph against the live BBC feed (34 real articles) — it worked, `workflow.py` genuinely never changed (confirmed via `git diff`, zero output), but the summary quality was noticeably worse than earlier mock-based runs: several garbled fragments (`"Bruxost village"`, `"Booker Prize Bung longlist"`, a stray `"sig·systems"`). The free model clearly handles synthesizing one focused article much better than 34 unrelated real stories at once. Not something to fix in this ticket — filtering/ranking/deduplication are explicitly out of Sprint 4's scope — but worth naming honestly as a real limitation surfaced by using genuinely live data, rather than only reporting the happy path.

**Verification:** direct call confirmed real, correctly-shaped article dicts (34 articles, `source` correctly overridden to `"BBC News"`); full graph invocation confirmed all five state fields populate correctly with live data, Planner's `execution_plan` unchanged (still mocked), and `git diff` on `workflow.py` showed zero changes.

### TOOL-005 — Retry & timeout strategy

**Date:** 2026-07-28

**Discussion, decided before implementing:** same per-error-type judgment as AI-005, applied to HTTP. Timeouts/connection errors and HTTP 5xx are transient — worth retrying. HTTP 4xx (e.g. 404 — wrong/gone URL) and feed parse failures (`bozo`) are permanent — retrying accomplishes nothing, so they fail immediately instead. Retry logic lives inside `rss.py` (the Tool), matching ADR 0003 and AI-005's precedent — not in `retrieval.py`.

**Decision — `tenacity`, not a hand-rolled retry loop:** unlike Sprint 3, where LiteLLM already had retry built in, `httpx`/`feedparser` have no built-in retry mechanism — this is a genuine need, not reaching for a library where one wasn't necessary. `tenacity` turned out to already be a transitive dependency (via `litellm`), so promoting it to direct cost nothing new to install.

**What was done:** wrapped only the HTTP fetch (`_fetch_with_retry`, a separate method from parsing) in `@retry`, using a custom predicate (`_is_retryable`) since `httpx.HTTPStatusError` covers both 4xx and 5xx and needed distinguishing by status code, not just exception type. 3 attempts total, exponential backoff (1s → 2s → 4s, capped at 8s). Parsing/`bozo` checks stay entirely outside the retry scope — a malformed feed won't get a different result on a second try.

**Verification — proved all four behaviors concretely, not just by code review:**
1. Regression: real fetch against the live BBC feed still works.
2. Monkey-patched `httpx.get` to fail twice with a simulated timeout then succeed — confirmed it actually retried and succeeded on attempt 3.
3. Simulated a persistent 404 — confirmed it failed after **exactly 1 attempt**, no wasted retries on a permanent error.
4. Simulated a persistent 503 — confirmed it retried the full 3 attempts before giving up, proving the retry budget is respected for genuinely transient-looking failures too.

**Problem it solved:** before this, any network hiccup (a dropped packet, a momentarily slow server) would fail the entire graph on the first blip; now transient failures get a real second chance, while permanent ones (wrong URL, malformed feed) fail fast instead of wasting time on retries that could never succeed.

### TOOL-006 — Data validation

**Date:** 2026-07-29

**Discussion, decided before implementing — the ownership model:** three layers, each owning a different question. The `Article` model owns *structural* validity (is this even well-formed). The RSS Tool owns *construction failures* (what happens when one entry can't become a valid `Article`). Retrieval Service owns *usefulness* (is a structurally-valid-but-sparse article actually worth keeping) — deliberately not the Tool's call, per ADR 0003 ("Tools never filter/judge").

**A real gap found and fixed, same class of bug as AI-001's API key loophole:** `Article.title: str` had no `min_length`, so an empty string satisfied it silently — a missing title would become `""`, not a validation error. Fixed with `Field(min_length=1)`, identical fix to `openrouter_api_key`'s.

**What was done:**
- `Article.title` now requires at least 1 character; `Article.url` upgraded from plain `str | None` to `HttpUrl | None` — catches malformed URLs for free, with zero network cost (format only, never checks reachability — verifying a link is actually *live* would mean a second request per article, slow and unreliable, and not really "retrieval").
- `RSSTool.fetch()` now builds articles in a loop instead of a list comprehension, catching `pydantic.ValidationError` per entry — one malformed entry gets skipped and logged as a warning, the rest of the fetch still succeeds. Also normalizes a blank `<link>` tag to `None` rather than letting it hit `HttpUrl` validation and skip an otherwise-good article over nothing.
- `retrieval_node` now drops articles with no `content` before returning — the "usefulness" judgment call, correctly placed in the Service layer, not the Tool.
- Switched `article.model_dump()` to `article.model_dump(mode="json")` — necessary once `url` became `HttpUrl` (a Pydantic-specific type); `mode="json"` serializes it back to a plain string so downstream dict consumers see exactly what they did before.

**Verification, each layer tested in isolation before the full regression:**
1. `Article` directly: empty title rejected, malformed URL rejected, valid URL accepted and typed as `HttpUrl`, missing URL still fine (optional).
2. `RSSTool.fetch()` against a synthetic mix of entries (good/titleless/bad-URL): confirmed exactly the 2 malformed ones were skipped with warning logs, the 2 good ones kept.
3. `retrieval_node` against synthetic articles with/without content: confirmed only the one with real content survived, both `None` and empty-string content correctly dropped.
4. Full graph against the real live BBC feed: 33/33 articles usable this run (none needed dropping), summary produced successfully, `url` confirmed to come out as a plain `str` in the final dict (not a leaked `HttpUrl` object), and `workflow.py` confirmed untouched via `git diff`.

### TOOL-007 — End-to-end verification

**Date:** 2026-07-29

**Verified fresh, mirroring AI-006's role in Sprint 3 — one deliberate closing pass, not trusting the sum of individual ticket verifications:**

1. **`workflow.py`'s entire git history across *both* Sprint 3 and Sprint 4** is still the single `ENGINE-007` commit from Sprint 2 — 13 tickets of real AI and Tool integration, zero changes to the graph's wiring.
2. **Dependencies stayed exactly in scope:** `fastapi`, `feedparser`, `langgraph`, `litellm`, `pydantic-settings`, `tenacity`, `uvicorn` — nothing from Sprint 4's explicit out-of-scope list (no Google News client, no ranking/dedup library, no persistence driver).
3. **Error propagation through the full graph — new for this ticket, not covered by TOOL-005's isolated Tool test:** pointed `retrieval_node` at a genuinely nonexistent domain and confirmed `RSSToolError` propagates uncaught out of `graph.invoke()` itself — the same "fail loudly" design AI-006 proved for LLM errors, now proven for the Tool infrastructure path too.
4. **Full state evolution** against the real live feed: all five `GraphState` fields correct, `execution_plan` confirming Planner is still genuinely mocked, all 33 returned articles have content (the TOOL-006 filter holding), and `response.answer` matching `summary` exactly.

**One more honest quality finding, not hidden:** the summary contained a stray Devanagari word (`"उल्लेखित"`, roughly "mentioned") injected mid-sentence — another real generation artifact from this free model synthesizing many diverse real stories, same category as AI-004's `.parks` and TOOL-004's "Bruxost village" glitches. A recurring, now well-established pattern across both Sprint 3 and Sprint 4: **quality degrades when this particular free model has to synthesize many unrelated real stories at once** — worth carrying forward as a known, named limitation rather than three separate one-off surprises.

**Sprint 4 Exit Criteria: met.** All TOOL-001–007 tickets complete.

---

## Sprint 4 — Closeout Retrospective

**Date:** 2026-07-29

**Re-verified fresh on a clean `main`:** ran `build_graph().invoke(...)` again after pulling the merged TOOL-007 PR — real BBC feed, 33 usable articles, coherent summary, all Exit Criteria fields present. Re-confirmed `git log -- backend/app/graph/workflow.py` shows exactly one commit (`ENGINE-007`, Sprint 2) across **both** Sprint 3 and Sprint 4 combined — 13 tickets of real AI and Tool integration, zero changes to the orchestration engine's wiring. Dependencies (`fastapi`, `feedparser`, `langgraph`, `litellm`, `pydantic-settings`, `tenacity`, `uvicorn`) stayed exactly within the sprint's declared scope.

**What Sprint 4 actually built:** `ADR 0003` (Tool architecture — what makes something a Tool, why RSS isn't inside Retrieval, why Planner doesn't know it exists), a real `Article` domain model with genuine validation (not just structure), `RSSTool` with retry/timeout handling via `tenacity`, and `retrieval_node` now calling live data instead of returning mocks — all without `app/graph/workflow.py` ever changing.

**The recurring pattern this sprint, continuing Sprint 3's theme:** real, first-hand corrections that only surfaced by running the code, not by reasoning ahead of time.
- TOOL-003: assumed BBC's feed URL would just work — `httpx` doesn't follow redirects by default, and the URL silently returned zero entries until this was caught and fixed.
- TOOL-006: found the *exact same class of bug* as Sprint 3's `openrouter_api_key` gap — `Article.title: str` accepted an empty string silently, requiring the identical `min_length=1` fix.
- TOOL-004/006/007: real, diverse news data repeatedly exposed summary-quality degradation (`.parks`, "Bruxost village", a stray Devanagari word) that mock data never could have surfaced, since mock articles were always small and focused.

**Known limitations carried forward, not fixed in Sprint 4 (deliberately, to stay scoped):** the free LLM's summary quality degrades when synthesizing many unrelated real stories at once — a real, named limitation now, not three separate surprises. LiteLLM's retry still doesn't distinguish permanent from transient failures (Sprint 3's finding, unchanged). There's still no automated test suite (flagged since Sprint 2). No second news source exists yet to actually prove the `NewsSourceTool` Protocol's swappability claim — it's designed for that, but untested against a real second implementation. Article count per fetch isn't capped or ranked — Retrieval currently passes everything usable to the Summarizer regardless of volume, which is *why* the quality-degradation pattern above exists; deliberately not fixed here since ranking/filtering-by-relevance is explicitly out of Sprint 4's scope.

---

## Sprint 5 — Intelligent Planning

### PLAN-001 — Planner design review

**Date:** 2026-07-29

**What was done:** Answered five architecture questions before writing any Sprint 5 code, written up as [`ADR 0004`](../docs/ADR/0004-planner-responsibilities.md) — mirroring TOOL-001's role for Sprint 4.

**Core distinction, in my own words:** the Planner's job is entirely about *what the user wants*, never *how the system technically fulfills it*. Every "must never belong to the Planner" item (which tool, which LLM provider, execution order, retry handling, formatting) is implementation detail that already has an owner elsewhere in the architecture — the Planner doesn't need to know those owners exist, only that the capability itself does.

**The subtlest point, worth remembering:** the Planner not knowing RSS exists (ADR 0003's principle, reapplied) is a different kind of statement than the Planner not knowing LiteLLM exists — because the Planner *is* an LLM call itself. The distinction is: using an LLM to reason is the node's own implementation detail; the *plan it outputs* must never encode anything about that mechanism. Same LLM-calling machinery as Summarizer (`app/llm/client.py`), zero mechanism-awareness leaking into the actual plan data.

**Also established:** the Planner's raw output is untrusted data crossing a trust boundary — the same category as RSS feed content in ADR 0003, not specially trusted for being "our own" AI node's output. This directly sets up PLAN-004's validation requirement before any code exists to enforce it.

**Problem it solved:** without this reviewed and written down first, PLAN-002/003 risked either over-loading the Planner's prompt with implementation knowledge it doesn't need, or under-specifying what `ExecutionPlan` should and shouldn't encode — repeating, in a new context, exactly the kind of coupling ADR 0003 was written to prevent for Tools.

### PLAN-002 — Design the execution plan schema

**Date:** 2026-07-29

**What was done:** `app/schemas/execution_plan.py` — `ExecutionPlan(BaseModel)` with `intent: Literal["summary", "timeline"]`, `requires_timeline: bool = False`, `response_style: Literal["neutral", "technical", "casual"] = "neutral"`, and `model_config = ConfigDict(extra="forbid")`. Upgraded `GraphState.execution_plan` from `list[str]` to `ExecutionPlan`. Updated the still-mocked `planner_node` to return a real `ExecutionPlan` instance instead of the old list, so the graph keeps working correctly until PLAN-003 makes the Planner itself real.

**Refinement beyond the pre-sprint sketch — constrained `Literal` types, not free strings:** the planning-stage design had `intent: str` and `response_style: str`. Tightened both to small closed `Literal` sets specifically because PLAN-004 (structured output validation) needs real teeth — an unconstrained string field would let a malformed LLM response like `"intent": "banana"` pass Pydantic validation as a perfectly valid string, silently defeating the whole point of validating Planner output. `extra="forbid"` was added for the same reason, directly at the schema level, rather than left to be caught by separate validation logic later.

**Decision — upgrading `GraphState.execution_plan`'s type, unlike `articles`:** `articles` stayed `list[dict]` in TOOL-004 specifically to avoid rippling into `summarizer.py`/`response_composer.py`, which already consumed it via dict access. Checked here first: **nothing currently reads `execution_plan`'s contents at all** (Retrieval/Summarizer never touch it, matching the established "don't fake-read unused fields" pattern) — so there was no ripple to avoid, and PLAN-005 is about to need real structured access (`.requires_timeline`) for routing. Upgraded the type now rather than deferring.

**Verification:** confirmed all three `Literal`/`extra="forbid"` constraints reject invalid values (bad `intent`, bad `response_style`, unexpected extra field) while defaults apply correctly for a minimal valid plan. Then ran the full graph end-to-end and confirmed `execution_plan` flows through as a real typed `ExecutionPlan` object, not a raw dict or list — regression-free.

### PLAN-003 — Build the real Planner

**Date:** 2026-07-29

**What was done:** `app/prompts/planner.py` (instructions + `build_planner_prompt(query)`, matching the Summarizer's constant+function pattern from AI-003). `LLMClient.complete()` extended with an optional `json_mode: bool = False` parameter, passing `response_format={"type": "json_object"}` to LiteLLM when set — backward-compatible, Summarizer's existing call site untouched. `planner_node` rewritten: real LLM call → `json.loads()` → `ExecutionPlan(**parsed)`. Deliberately happy-path only — no error handling yet, matching AI-004's precedent (build the real call first, AI-005 layered error handling after; PLAN-004 is next here).

**Verified `json_mode` live, not assumed:** requested a raw completion with `json_mode=True` and got back clean JSON (`'{"intent":"timeline","requires_timeline":true,"response_style":"neutral"}'`) — no markdown fences, no extra commentary, correctly classifying "Show me a timeline of the AI industry this year" as a timeline request on the first try. This specific free model (`openai/gpt-oss-20b:free`) does honor `response_format`.

**Verified actual reasoning quality across diverse real queries**, not just one lucky case:
- "Summarize the latest AI news" → `summary`/neutral
- "What is happening with NVIDIA lately" → `summary`/casual
- "Give me a casual rundown of tech news" → `summary`/casual
- "Show me a chronological history of OpenAI" → `timeline`/`True`/neutral

All four correct — the model picked up both the intent distinction (timeline vs. summary) and informal-phrasing cues for `response_style`, without either being spelled out in examples in the prompt.

**Problem it solved:** the Planner now genuinely reasons about user intent instead of returning a hardcoded plan — the first real "understand what the user wants" capability in the whole system. Note this doesn't change routing *yet* — `workflow.py` still runs the same fixed path regardless of the plan's contents; PLAN-005 is what makes the graph actually act on `requires_timeline`.

**Full graph regression:** confirmed end-to-end with the real Planner wired in — Planner call succeeded in 4.86s, correctly threaded into the existing Retrieval → Summarizer → Response Composer path, no regressions.

### PLAN-004 — Structured output validation

**Date:** 2026-07-29

**What was done:** `PlannerOutputError` + `parse_execution_plan(raw_output: str) -> ExecutionPlan`, both added to `app/agents/planner.py` — co-located with the node that uses them, matching where `LLMError` lives in `client.py` and `RSSToolError` lives in `rss.py`. Catches `json.JSONDecodeError` (invalid syntax) and `pydantic.ValidationError` (missing/unknown/extra fields — already enforced by PLAN-002's `Literal`/`extra="forbid"` design, just not caught until now), both wrapped into one clear exception type.

**A real edge case caught by thinking through failure modes, not just the four named in the ticket:** valid JSON that isn't a JSON *object* — e.g. the model outputs a bare string or array instead of `{...}`. `ExecutionPlan(**parsed)` would raise a confusing `TypeError` in that case, not a clean `ValidationError`, since you can't `**`-unpack a string or list as keyword arguments. Added an explicit `isinstance(parsed, dict)` check before attempting construction, so this case gets the same clean `PlannerOutputError` as every other malformed-output case, not a different, uglier crash.

**Verification — all cases tested directly, not assumed:** ran eight cases through `parse_execution_plan` — valid output (regression), invalid JSON syntax, markdown-fenced JSON, missing required field, unknown intent value, extra field, and both non-object JSON shapes (array, bare string). All seven malformed cases correctly raised `PlannerOutputError`; the valid case parsed correctly. Then monkey-patched the Planner's LLM client to return genuinely malformed output and confirmed `PlannerOutputError` propagates uncaught through the full `graph.invoke()` — same "fail loudly for now" pattern as every prior error-handling ticket (AI-005, TOOL-005) before its recovery-policy sibling (PLAN-006, next) layers retry/fallback on top.

### PLAN-005 — Conditional routing

**Date:** 2026-07-29

**What was done:** the first change to `app/graph/workflow.py` since Sprint 2's `ENGINE-007` — this is the actual realization of the "conditional edges" concept discussed hypothetically all the way back in ENGINE-001's journal entry. Added `route_after_retrieval(state) -> str`, checking `state["execution_plan"].requires_timeline`, wired via `builder.add_conditional_edges("retrieval", route_after_retrieval, {"timeline": "timeline", "summarizer": "summarizer"})`, replacing the old fixed `retrieval → summarizer` edge. Added a fully mocked `timeline_node` (`app/agents/timeline.py`, classified as an AI node — a real timeline will likely need narrative/grouping judgment later, not just mechanical sorting) and a new `timeline` field in `GraphState` that Summarizer never reads, per the design note from Sprint 5 planning.

**A genuine, honest complication during verification — hit OpenRouter's free-tier rate limit for real.** After the cumulative volume of real LLM calls across PLAN-002 through PLAN-005 today, both the two-query test and a conservative single-query retry hit `LLMError: Rate limit exceeded, even after automatic retries` on the Summarizer call. This is `LLMError` and the retry logic (AI-005) working exactly as designed — not a bug — just inconvenient timing. Rather than keep hammering a rate-limited API, verified what PLAN-005 is actually responsible for — **routing mechanics**, not Planner classification quality (already proven with four real diverse queries in PLAN-003) — by monkey-patching only the LLM-dependent pieces (Planner's raw output, Summarizer's completion) while keeping the real graph (`add_conditional_edges`, `route_after_retrieval`, real RSS fetch in both runs) fully exercised.

**Verification:**
1. Controlled plan with `requires_timeline=False` → confirmed `timeline` key absent from final state, routed straight to `summarizer`.
2. Controlled plan with `requires_timeline=True` → confirmed `timeline` key present with the mock content, routed through `timeline` before `summarizer`.
3. `git diff --stat` on `retrieval.py`, `summarizer.py`, `response_composer.py` — zero output, confirming all three remain genuinely untouched, per the exit criteria.

**Problem it solved:** the graph now actually adapts its execution path based on what the Planner decided — the first real behavioral difference between two different user requests anywhere in this project. Everything before this sprint always ran the identical fixed sequence regardless of what was asked.
