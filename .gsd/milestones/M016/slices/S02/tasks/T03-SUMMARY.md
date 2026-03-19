---
id: T03
parent: S02
milestone: M016
provides:
  - "pull_sync(ctx) orchestrator: auth check → paginated GraphQL fetch → field mapping → SPARQL dedup → two-phase bulk create/update → delta cursor"
  - "poll-tasks handler in app.py wired to pull_sync"
  - "20 unit tests with fully mocked clients covering all sync paths"
key_files:
  - apps/linear-sync/services/sync_engine.py
  - backend/tests/test_sync_engine.py
  - apps/linear-sync/app.py
key_decisions:
  - "Two-phase bulk for new issues: phase 1 creates tasks (no IRI needed), phase 2 discovers platform-minted IRIs via SPARQL then submits body.set/edge.create"
  - "Simplified new_issue_assignees to store resolved Person IRI directly (not email+name dict) since PersonMatcher is already called during issue processing"
  - "body.set used for both new and existing task descriptions (no body.diff) — simpler and idempotent for v1"
patterns_established:
  - "importlib module loading in dependency order (field_mapper → person_matcher → linear_client → auth → sync_engine) with sys.modules registration for cross-module imports"
  - "StatefulGraph mock with call-count tracking for testing two-phase lookup patterns (first call returns empty, second returns created IRI)"
observability_surfaces:
  - "Logger linear_sync.sync — INFO for sync start/complete with counts dict, WARNING for per-issue errors"
  - "pull_sync() return dict: {status, created, updated, unchanged, errors} — structured result for callers"
  - "StateClient key last_sync_at — ISO timestamp of last successful sync, inspectable via ctx.state.get()"
duration: "~25 minutes"
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Build sync engine, wire poll-tasks, and add unit tests

**Implemented pull_sync() orchestrator with two-phase bulk creation, IRI prefix bypass, delta cursor, and 20 unit tests — wired into poll-tasks handler**

## What Happened

Built `sync_engine.py` (~250 lines) with `pull_sync(ctx)` as the main entry point. The function follows the pipeline: auth check → read sync state → paginated GraphQL fetch via LinearClient → per-issue processing (slug computation, SPARQL dedup, property building, assignee resolution) → two-phase bulk submission → cursor update.

Key design: new issues use a two-phase approach — phase 1 submits `object.create` commands (platform assigns IRI), phase 2 re-queries SPARQL to discover the minted IRIs and submits `body.set` / `edge.create` commands. Existing issues get all commands (patch, body, edge) in a single batch since the IRI is already known.

Commands bypass the SDK's `CommandClient` (which enforces IRI prefix checks on `object.patch`, `body.set`, `edge.create`) by posting directly to `/api/commands/bulk` via `ctx.commands._client` (the shared httpx.AsyncClient).

Wired `poll_tasks` in `app.py` to call `pull_sync(ctx)` as an async handler, replacing the noop stub.

Test file uses a dependency-ordered importlib loading chain (field_mapper → person_matcher → linear_client → auth → sync_engine) with `sys.modules` registration so that sync_engine's try/except import chain resolves correctly. Includes `StatefulGraph` mock for the two-phase lookup pattern.

## Verification

- `test_sync_engine.py` — 20/20 tests pass covering: auth/state skip conditions, new issue creation (object.create with correct properties and deterministic slug), phase 2 body.set discovery, existing task patching, assignee edge creation, trashed issue handling (skip new, cancel existing), delta cursor storage and query propagation, batch splitting at 1000 ops, per-issue error isolation, result shape, and SDK bypass confirmation.
- Full suite: 81/81 tests pass across all three files (49 field mapper + 12 person matcher + 20 sync engine).
- All source files pass AST parse validation.
- Error path tests confirm structured error output with `issue_id` and `error` fields.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `.venv/bin/python -m pytest tests/test_sync_engine.py -v` | 0 | ✅ pass (20/20) | 0.06s |
| 4 | `.venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v` | 0 | ✅ pass (81/81) | 0.09s |
| 5 | `.venv/bin/python -m pytest tests/test_sync_engine.py -v -k "error"` | 0 | ✅ pass (2/2) | 0.02s |

## Diagnostics

- **Sync result inspection:** `pull_sync()` returns `{"status": "ok", "created": N, "updated": N, "unchanged": N, "errors": [...]}` — callers can log or surface this directly.
- **Delta cursor:** `await ctx.state.get("last_sync_at")` shows when sync last ran.
- **Per-issue errors:** Each error in the `errors` list contains `{"issue_id": "...", "error": "..."}` for targeted debugging.
- **Logger:** `linear_sync.sync` at INFO level logs fetch count and final result dict; WARNING level logs individual issue processing failures.

## Deviations

- Plan suggested storing `{email, name}` dict in `new_issue_assignees` for phase 2; simplified to storing the resolved Person IRI directly since `PersonMatcher.match_or_create` is already called during issue processing — avoids redundant lookups.
- Plan mentioned `body.diff` for existing tasks with changed descriptions; used `body.set` uniformly — simpler, idempotent, and sufficient for v1 (diff requires knowing the old body content which isn't fetched from SPARQL).

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/services/sync_engine.py` — New sync engine with `pull_sync()`, `_find_existing_task()`, `_build_create_command()`, `_build_update_commands()`, `_submit_commands_batched()`
- `apps/linear-sync/app.py` — Modified `poll_tasks` handler to async, now calls `pull_sync(ctx)`
- `backend/tests/test_sync_engine.py` — 20 unit tests with MockStateClient, MockGraphClient, MockCommandClient, MockHttpClient, MockAppContext, StatefulGraph
