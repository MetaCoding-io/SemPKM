# S05: Dependency Pinning & Cleanup — Research

**Date:** 2026-03-12

## Summary

S05 covers three requirements: DEP-01 (pin dependency versions in pyproject.toml), DEP-02 (commit uv.lock and use it in Docker builds), and PERF-01 (batch the N+1 user lookup in the event log endpoint). All three are low-risk, well-scoped changes with clear implementation paths.

The lockfile (`backend/uv.lock`) already exists and is committed to git, but it is **stale** — `slowapi` and `http-message-signatures` (added during S01) are missing. The Dockerfile currently uses `pip install .` and ignores the lockfile entirely, so Docker builds are not reproducible. The fix is to regenerate the lockfile and switch the Dockerfile to use `uv sync --frozen`.

The N+1 pattern in the event log endpoint is textbook — one SQL SELECT per unique `performed_by` user IRI instead of a single IN query. The fix is a batched `WHERE User.id IN (...)` query, which SQLAlchemy handles natively.

## Recommendation

**Three tasks:**

1. **T01 — Pin versions + regenerate lockfile:** Add compatible-release pins (`~=X.Y.Z`) to all dependencies in `pyproject.toml` using versions from the current lockfile as reference, then run `uv lock` to regenerate with `slowapi` and `http-message-signatures` included.

2. **T02 — Switch Dockerfile to uv:** Replace `pip install .` with `COPY --from=ghcr.io/astral-sh/uv` and `uv sync --frozen --no-dev` so Docker builds respect the lockfile. Keep the existing single-stage structure but add the uv binary via multi-stage copy.

3. **T03 — Batch user lookup:** Replace the for-loop SQL queries in `event_log()` with a single `SELECT ... WHERE id IN (...)` query.

T01 and T02 are tightly coupled (pinning without Docker consumption is only half-useful). T03 is independent.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Lockfile generation | `uv lock` | Already in use locally; generates deterministic resolution |
| Docker uv install | `COPY --from=ghcr.io/astral-sh/uv:latest` | Official multi-stage copy pattern — no apt-get, no curl, fast |
| Batched SQL queries | SQLAlchemy `where(User.id.in_([...]))` | Standard ORM pattern, already used elsewhere in codebase |

## Existing Code and Patterns

- `backend/pyproject.toml` — 25 runtime deps + 3 dev deps. 8 deps have no version constraint at all; the rest use `>=` floors only. No upper bounds or compatible-release pins.
- `backend/uv.lock` — Exists and is committed (86 packages). Last regenerated before S01, so missing `slowapi>=0.1.9` and `http-message-signatures>=2.0.1`. `uv lock --check` confirms it's stale.
- `backend/Dockerfile` — Single-stage `python:3.12-slim`, uses `pip install --no-cache-dir .`. No uv, no lockfile consumption. Volume mounts app code for dev hot-reload.
- `backend/app/browser/events.py:59-80` — The N+1 pattern: iterates `user_iris` list, runs one `sa_select(User).where(User.id == uuid_obj)` per user IRI. Typically 1-5 unique users per page (cursor-paginated events).
- `backend/app/auth/models.py:19` — `User` model with `id: UUID` primary key, `display_name: str | None`, `email: str`.
- `docker-compose.yml` and `docker-compose.test.yml` — Both use `build: ./backend` so the same Dockerfile serves dev and test.

## Constraints

- **Dockerfile must stay compatible with docker-compose hot-reload.** The dev compose mounts `./backend/app:/app/app` as a volume — the Dockerfile's `COPY app/ app/` is overridden at runtime. uv changes must not break this pattern.
- **`uv sync --frozen` requires both `pyproject.toml` AND `uv.lock` in the Docker build context.** Both files must be COPYed before the sync step.
- **No `.dockerignore` exists.** The entire `backend/` directory is the build context. A `.venv/` directory exists locally and would bloat the build context — should add a `.dockerignore`.
- **Python 3.12 base image.** The lockfile has `requires-python = ">=3.12"` and resolution markers for 3.13/3.14. uv will resolve for the container's Python version.
- **dev dependencies (`pytest`, `pytest-asyncio`, `httpx`) should not be in the production image.** Use `--no-dev` flag with uv sync. Note: `httpx` is both a runtime dep (`>=0.28`) and a dev dep (unpinned). uv handles this correctly — the runtime version satisfies both.
- **Compatible-release (`~=`) vs exact (`==`) pins.** Use `~=` — it allows patch updates within a minor version (e.g., `~=3.1.6` means `>=3.1.6, <3.2.0`). The lockfile pins exact versions for reproducibility; pyproject.toml pins express compatibility intent. This is the uv-recommended pattern.

## Common Pitfalls

- **`fastapi[standard]` unpinned could pull a new major.** FastAPI moves fast — 0.x series has no semver stability guarantee. Pin to `~=0.132.0` to prevent breakage on next `uv lock`.
- **`COPY --from=ghcr.io/astral-sh/uv:latest` is non-deterministic.** Pin the uv image tag (e.g., `ghcr.io/astral-sh/uv:0.9`) for reproducible builds.
- **Forgetting `UV_COMPILE_BYTECODE=1` in Docker.** Without it, Python compiles bytecode on first import at runtime, adding startup latency.
- **`UV_LINK_MODE=copy` required in Docker.** Docker's overlay filesystem doesn't support hardlinks across layers. Without this, uv sync can fail.
- **The `--reload` CMD in Dockerfile assumes local dev.** This is fine — the existing pattern works because the volume mount provides live code. uv changes are only about the install step.
- **SQLAlchemy `in_()` with empty list.** If `user_iris` parsing yields zero valid UUIDs, don't execute the query — SQLAlchemy's `in_([])` generates invalid SQL on some backends.

## Open Risks

- **Dockerfile rebuild required after this slice.** Both dev and test stacks need `docker compose build` or `--build` flag. This is expected and documented in CLAUDE.md (rebuild needed for pyproject.toml changes).
- **uv version drift between host and container.** Host has uv 0.9.5; Docker will COPY a pinned version. Minor version differences in lockfile format are unlikely but possible — pin to same minor.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| uv (Python package manager) | `wshobson/agents@uv-package-manager` (3.7K installs) | available — not installed |
| SQLAlchemy | (not searched — standard ORM, no skill needed) | n/a |
| Docker | (not searched — standard tooling) | n/a |

The `uv-package-manager` skill has high install count but S05's uv usage is straightforward (lock + sync). Not needed unless complications arise.

## Sources

- uv Docker best practices — `COPY --from=ghcr.io/astral-sh/uv`, `UV_COMPILE_BYTECODE`, `UV_LINK_MODE=copy`, `--frozen` flag (source: [Astral docs](https://docs.astral.sh/uv/guides/integration/docker/))
- uv lockfile format — version 1, revision 3, resolution markers for Python version ranges (source: `backend/uv.lock` header)
- Existing lockfile staleness confirmed via `uv lock --check` (exits non-zero, reports 5 missing packages)
