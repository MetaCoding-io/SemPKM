---
id: T01
parent: S05
milestone: M002
provides:
  - All 25 runtime dependencies pinned with ~=X.Y.Z compatible-release constraints
  - Regenerated uv.lock including slowapi and http-message-signatures
key_files:
  - backend/pyproject.toml
  - backend/uv.lock
key_decisions:
  - Used lockfile-resolved versions for all pins (not latest available) to preserve tested combinations
  - fastapi pinned ~=0.132.0 (0.x has no semver stability guarantees)
patterns_established:
  - All runtime deps use ~= compatible-release operator; no bare >= floors
observability_surfaces:
  - "uv lock --check" detects lockfile/pyproject.toml drift (exits non-zero with diff)
duration: 10m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Pin dependency versions and regenerate lockfile

**Replaced all 25 bare `>=` version floors with `~=X.Y.Z` compatible-release pins and regenerated `uv.lock`.**

## What Happened

Read resolved versions from `uv.lock` for all 25 runtime dependencies. Edited `pyproject.toml` to replace every dependency specifier with `~=X.Y.Z` format using those exact versions. Special cases handled: `fastapi[standard]` pinned tight at `~=0.132.0` (0.x semver), `wsgidav` simplified from `>=4.3.3,<5.0` to `~=4.3.3`, and previously unpinned deps (`pydantic-settings`, `jinja2`, `uvicorn`, etc.) all received pins. Ran `uv lock` which resolved 91 packages cleanly. Lockfile now includes slowapi and http-message-signatures which were previously missing.

## Verification

- `uv lock --check` exits 0 ✅
- `grep '~=' backend/pyproject.toml | wc -l` returns 25 ✅
- No bare `>=` in `[project.dependencies]` section (0 matches) ✅
- `grep 'slowapi' backend/uv.lock` returns matches ✅
- `grep 'http-message-signatures' backend/uv.lock` returns matches ✅

Slice-level checks status (this is T01 of 3):
- `uv lock --check` exits 0 ✅
- `docker compose build backend` — not yet (T02 scope)
- `pytest tests/test_event_user_lookup.py` — not yet (T03 scope)
- `grep '~=' pyproject.toml | wc -l` returns 25 ✅
- `grep 'uv sync' backend/Dockerfile` — not yet (T02 scope)

## Diagnostics

Run `uv lock --check` in `backend/` to detect any drift between pyproject.toml and uv.lock.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/pyproject.toml` — replaced all 25 runtime dependency specifiers from bare `>=` floors to `~=X.Y.Z` compatible-release pins
- `backend/uv.lock` — regenerated lockfile (now includes slowapi and http-message-signatures)
