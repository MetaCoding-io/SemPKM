---
estimated_steps: 4
estimated_files: 2
---

# T01: Pin dependency versions and regenerate lockfile

**Slice:** S05 — Dependency Pinning & Cleanup
**Milestone:** M002

## Description

Replace all bare `>=` version floors in `pyproject.toml` with compatible-release (`~=X.Y.Z`) pins based on the currently resolved versions in `uv.lock`. Then regenerate the lockfile to include packages added since last generation (slowapi, http-message-signatures). This satisfies DEP-01 (pinned versions) and partially satisfies DEP-02 (committed lockfile).

## Steps

1. Read current resolved versions from `uv.lock` for all 25 runtime dependencies
2. Edit `pyproject.toml` to replace each dependency version specifier with `~=X.Y.Z` format using the lockfile-resolved version. Special cases:
   - `fastapi[standard]` → `~=0.132.0` (0.x has no semver stability, pin tight)
   - `wsgidav` currently has `>=4.3.3,<5.0` → replace with `~=4.3.3` (equivalent intent)
   - Deps with no version constraint (e.g. `pydantic-settings`, `jinja2`, `uvicorn`) get `~=` pins from lockfile
3. Run `uv lock` to regenerate the lockfile (will pick up slowapi and http-message-signatures that were missing)
4. Verify with `uv lock --check` (should exit 0)

## Must-Haves

- [ ] All 25 runtime dependencies use `~=X.Y.Z` compatible-release pins
- [ ] No bare `>=` floors remain in runtime dependencies
- [ ] `uv.lock` includes slowapi and http-message-signatures entries
- [ ] `uv lock --check` exits 0

## Verification

- `cd backend && uv lock --check` exits 0
- `grep '~=' backend/pyproject.toml | wc -l` returns 25
- `grep -c '>=' backend/pyproject.toml` returns 0 for the `[project.dependencies]` section (dev deps may differ)
- `grep 'slowapi' backend/uv.lock` returns matches
- `grep 'http-message-signatures' backend/uv.lock` returns matches

## Observability Impact

- Signals added/changed: None (build-time only change)
- How a future agent inspects this: `uv lock --check` detects lockfile/pyproject.toml drift
- Failure state exposed: `uv lock --check` exits non-zero with a diff showing what changed

## Inputs

- `backend/pyproject.toml` — current dependency list with bare `>=` floors
- `backend/uv.lock` — stale lockfile with resolved versions to reference

## Expected Output

- `backend/pyproject.toml` — all 25 runtime deps pinned with `~=X.Y.Z`
- `backend/uv.lock` — regenerated, current, includes all deps
