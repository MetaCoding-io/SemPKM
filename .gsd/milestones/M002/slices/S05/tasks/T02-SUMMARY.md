---
id: T02
parent: S05
milestone: M002
provides:
  - Dockerfile uses uv with frozen lockfile for reproducible Docker builds
  - .dockerignore excludes build-irrelevant files from Docker context
key_files:
  - backend/Dockerfile
  - backend/.dockerignore
key_decisions:
  - Added ENV PATH="/app/.venv/bin:$PATH" so uv-installed binaries (uvicorn, alembic) are available without venv activation in the container
patterns_established:
  - Docker builds use COPY --from=ghcr.io/astral-sh/uv:0.9 for pinned uv binary
  - UV_COMPILE_BYTECODE=1 and UV_LINK_MODE=copy set as ENV for all uv operations in Docker
  - uv sync --frozen --no-dev --no-editable for production installs from lockfile
observability_surfaces:
  - Docker build output shows uv sync step with exact locked package list
  - Build fails immediately if uv.lock is missing or stale (--frozen refuses to resolve)
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Switch Dockerfile to uv and add .dockerignore

**Replaced pip install with uv sync --frozen in Dockerfile and added .dockerignore to exclude build-irrelevant files**

## What Happened

Created `backend/.dockerignore` with entries for `.venv/`, `__pycache__/`, `.git/`, `tests/`, `*.pyc`, `.pytest_cache/`, and `*.egg-info/`.

Rewrote `backend/Dockerfile` to:
1. Copy uv binary from `ghcr.io/astral-sh/uv:0.9` (pinned)
2. Set `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy` environment variables
3. Add `.venv/bin` to PATH so installed tools are available without activation
4. Copy both `pyproject.toml` and `uv.lock` before the install step
5. Replace `pip install --no-cache-dir .` with `uv sync --frozen --no-dev --no-editable`

Initial build succeeded but the container failed to start because `uvicorn` wasn't on PATH — uv installs into `.venv/` and the CMD used a bare `uvicorn` command. Fixed by adding `ENV PATH="/app/.venv/bin:$PATH"` to the Dockerfile.

## Verification

- `docker compose build api` — completed successfully, uv sync installed 86 packages from lockfile
- `docker compose up api -d` + `docker compose logs api` — container starts, uvicorn running, application startup complete
- `grep 'uv sync' backend/Dockerfile` — shows `RUN uv sync --frozen --no-dev --no-editable`
- `grep 'UV_COMPILE_BYTECODE' backend/Dockerfile` — shows `ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy`
- `test -f backend/.dockerignore` — exits 0
- `grep '.venv' backend/.dockerignore` — shows `.venv/`
- `grep 'ghcr.io/astral-sh/uv:0.9' backend/Dockerfile` — shows pinned COPY --from

Slice-level checks (partial — T03 remaining):
- `cd backend && uv lock --check` — exits 0 ✅
- `grep '~=' backend/pyproject.toml | wc -l` — returns 25 ✅
- `grep 'uv sync' backend/Dockerfile` — confirms uv sync present ✅
- `docker compose build api` — completes successfully ✅
- `tests/test_event_user_lookup.py` — not yet created (T03)

## Diagnostics

- Docker build logs show exact packages installed from lockfile at the `uv sync` step
- `uv lock --check` in `backend/` detects drift between pyproject.toml and uv.lock before build
- Build fails immediately if lockfile is missing or stale (`--frozen` flag)

## Deviations

Added `ENV PATH="/app/.venv/bin:$PATH"` which was not in the original plan. This was necessary because uv installs into a `.venv` directory (unlike pip which installs to the system site-packages), so the CMD's bare `uvicorn` command couldn't find the binary without the PATH addition.

## Known Issues

None.

## Files Created/Modified

- `backend/Dockerfile` — replaced pip install with uv-based install using frozen lockfile
- `backend/.dockerignore` — new file excluding .venv/, __pycache__/, .git/, tests/, *.pyc, .pytest_cache/, *.egg-info/ from build context
