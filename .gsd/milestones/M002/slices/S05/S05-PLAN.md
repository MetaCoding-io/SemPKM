# S05: Dependency Pinning & Cleanup

**Goal:** All Python dependencies are pinned with compatible-release constraints, Docker builds use the lockfile for reproducible installs, and the event log N+1 user lookup is batched.
**Demo:** `uv lock --check` passes, `docker compose build backend` completes using uv with frozen lockfile, and the event log endpoint issues one SQL query for user names regardless of how many distinct users appear.

## Must-Haves

- All 25 runtime deps in `pyproject.toml` use `~=X.Y.Z` compatible-release pins (DEP-01)
- `uv.lock` is regenerated (includes `slowapi` and `http-message-signatures`) and passes `uv lock --check` (DEP-02)
- Dockerfile uses `uv sync --frozen --no-dev` instead of `pip install .` (DEP-02)
- `.dockerignore` excludes `.venv/`, `__pycache__/`, `.git/`, `tests/` from build context (DEP-02)
- Event log user lookup uses a single `WHERE id IN (...)` query instead of N individual queries (PERF-01)

## Proof Level

- This slice proves: contract + operational
- Real runtime required: yes (Docker build must succeed; lockfile check must pass)
- Human/UAT required: no

## Verification

- `cd backend && uv lock --check` — exits 0 (lockfile matches pyproject.toml)
- `docker compose build backend` — completes successfully with uv-based install
- `cd backend && .venv/bin/pytest tests/test_event_user_lookup.py -v` — batched query test passes
- `grep '~=' backend/pyproject.toml | wc -l` — returns 25 (all runtime deps pinned)
- `grep 'uv sync' backend/Dockerfile` — confirms uv sync command present

## Observability / Diagnostics

- Runtime signals: SQLAlchemy query logging (when enabled via `echo=True`) shows single IN query instead of N selects for event log user resolution
- Inspection surfaces: `uv lock --check` for lockfile drift detection; `docker compose build` output shows uv sync step
- Failure visibility: `uv lock --check` exits non-zero with diff if lockfile is stale; Docker build fails at uv sync step if lockfile is missing or incompatible
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/uv.lock` (existing, stale), `backend/pyproject.toml` (existing deps), `backend/Dockerfile` (existing build), `backend/app/browser/events.py` (existing N+1 pattern)
- New wiring introduced in this slice: Dockerfile install step changes from pip to uv; `.dockerignore` added; event user resolution refactored
- What remains before the milestone is truly usable end-to-end: S06 (federation), S07 (Ideaverse import)

## Tasks

- [x] **T01: Pin dependency versions and regenerate lockfile** `est:30m`
  - Why: DEP-01 and DEP-02 — bare `>=` floors allow silent breakage; lockfile is stale (missing slowapi, http-message-signatures)
  - Files: `backend/pyproject.toml`, `backend/uv.lock`
  - Do: Replace all `>=` floors with `~=X.Y.Z` pins using resolved versions from current lockfile. Run `uv lock` to regenerate. Verify with `uv lock --check`.
  - Verify: `cd backend && uv lock --check` exits 0; `grep '~=' pyproject.toml | wc -l` returns 25
  - Done when: All 25 runtime deps have `~=` pins and lockfile is current

- [x] **T02: Switch Dockerfile to uv and add .dockerignore** `est:30m`
  - Why: DEP-02 — Docker builds currently use `pip install .` ignoring the lockfile, making builds non-reproducible
  - Files: `backend/Dockerfile`, `backend/.dockerignore`
  - Do: Add `COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/` stage. Replace `pip install .` with `uv sync --frozen --no-dev`. Set `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy`. COPY both `pyproject.toml` and `uv.lock` before sync. Create `.dockerignore` excluding `.venv/`, `__pycache__/`, `.git/`, `tests/`, `*.pyc`.
  - Verify: `docker compose build backend` succeeds; container starts and healthcheck passes
  - Done when: Docker build uses uv with frozen lockfile and `.dockerignore` exists

- [x] **T03: Batch event log user lookup** `est:30m`
  - Why: PERF-01 — current N+1 pattern issues one SQL query per unique user IRI in event results
  - Files: `backend/app/browser/events.py`, `backend/tests/test_event_user_lookup.py`
  - Do: Replace the for-loop of individual `SELECT ... WHERE id = ?` queries with a single `SELECT ... WHERE id IN (...)` query. Guard against empty list. Write a unit test that verifies the batched lookup function works correctly with 0, 1, and multiple user IRIs.
  - Verify: `cd backend && .venv/bin/pytest tests/test_event_user_lookup.py -v` passes
  - Done when: Event log user resolution uses single query; test passes

## Files Likely Touched

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/app/browser/events.py`
- `backend/tests/test_event_user_lookup.py`
