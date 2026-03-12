---
estimated_steps: 5
estimated_files: 2
---

# T02: Switch Dockerfile to uv and add .dockerignore

**Slice:** S05 — Dependency Pinning & Cleanup
**Milestone:** M002

## Description

Replace the `pip install .` step in the Dockerfile with uv-based installation that respects the lockfile. Add a `.dockerignore` to exclude local artifacts from the build context. This completes DEP-02 — Docker builds will now produce reproducible installs from `uv.lock`.

## Steps

1. Create `backend/.dockerignore` with entries: `.venv/`, `__pycache__/`, `.git/`, `tests/`, `*.pyc`, `.pytest_cache/`, `*.egg-info/`
2. Edit `backend/Dockerfile`:
   - Add `COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/` near the top (after FROM, before WORKDIR)
   - Set environment variables: `ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy`
   - Replace `COPY pyproject.toml .` with `COPY pyproject.toml uv.lock ./`
   - Replace `RUN pip install --no-cache-dir .` with `RUN uv sync --frozen --no-dev --no-editable`
   - Keep the rest of the Dockerfile unchanged (alembic.ini, migrations/, app/ copies, EXPOSE, CMD)
3. Verify the Dockerfile still works with docker-compose volume mounts (the `--reload` CMD and volume mount pattern is unaffected by the install step change)
4. Run `docker compose build backend` and confirm it succeeds
5. Spot-check that the built image starts correctly: `docker compose up backend -d` then `docker compose logs backend | head -20`

## Must-Haves

- [ ] Dockerfile uses `COPY --from=ghcr.io/astral-sh/uv:0.9` (pinned, not `:latest`)
- [ ] `uv sync --frozen --no-dev --no-editable` replaces `pip install`
- [ ] `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy` are set
- [ ] Both `pyproject.toml` and `uv.lock` are COPYed before the sync step
- [ ] `.dockerignore` exists and excludes `.venv/`, `__pycache__/`, `tests/`
- [ ] `docker compose build backend` succeeds

## Verification

- `docker compose build backend` completes without error
- `grep 'uv sync' backend/Dockerfile` shows the frozen sync command
- `grep 'UV_COMPILE_BYTECODE' backend/Dockerfile` confirms env var
- `test -f backend/.dockerignore` exits 0
- `grep '.venv' backend/.dockerignore` shows .venv is excluded

## Observability Impact

- Signals added/changed: Docker build output shows `uv sync` step with locked package list instead of pip resolver output
- How a future agent inspects this: Docker build logs show exact packages installed from lockfile; `uv lock --check` catches drift before build
- Failure state exposed: Build fails immediately if lockfile is missing or stale (uv sync --frozen refuses to resolve)

## Inputs

- `backend/Dockerfile` — current pip-based Dockerfile
- `backend/pyproject.toml` — pinned deps from T01
- `backend/uv.lock` — regenerated lockfile from T01

## Expected Output

- `backend/Dockerfile` — uv-based install with frozen lockfile
- `backend/.dockerignore` — excludes build-irrelevant files from context
