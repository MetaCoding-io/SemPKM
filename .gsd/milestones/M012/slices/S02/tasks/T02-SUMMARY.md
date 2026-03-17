---
id: T02
parent: S02
milestone: M012
provides:
  - save_body() branches on existing body — body.diff for changes, body.set for first body, no-op for unchanged
  - _parse_stored_diff() method for rendering stored unified diffs
  - body.diff in _OP_PRIORITY for compound event ordering
  - event_detail.html renders both body.set and body.diff events with diff highlighting
key_files:
  - backend/app/browser/objects.py
  - backend/app/events/query.py
  - backend/app/templates/browser/event_detail.html
  - backend/tests/test_body_diff.py
key_decisions: []
patterns_established:
  - save_body() queries urn:sempkm:current before choosing operation type — SPARQL SELECT for existing body value
  - Stored diffs parsed from data_triples (sempkm:bodyDiff predicate) rather than recomputed from before/after
observability_surfaces:
  - body.diff events visible in event log with stored diff text in sempkm:bodyDiff data triple
  - No-op saves produce no event (empty event log for unchanged body)
  - SPARQL inspection of diff text via SELECT ?diff WHERE { GRAPH <event_iri> { ?s <urn:sempkm:bodyDiff> ?diff } }
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Modify save endpoint to emit body.diff and update event detail rendering

**Modified save_body() to detect existing body and branch between body.diff/body.set/no-op, added stored diff parsing and template rendering for body.diff events.**

## What Happened

1. **save_body() branching logic** (`objects.py`): Added SPARQL query against `urn:sempkm:current` to check for existing body content. Three-way branch: (a) body unchanged → early return with "Saved" response, no event; (b) body exists and differs → compute `difflib.unified_diff`, emit `body.diff` via `handle_body_diff()`; (c) no prior body → emit `body.set` via `handle_body_set()` (per D157). Rest of function (dcterms:modified, commit, validation queue) unchanged.

2. **_OP_PRIORITY** (`query.py`): Added `"body.diff"` immediately after `"body.set"` for compound event ordering.

3. **get_event_detail() body.diff handling** (`query.py`): New branch for `body.diff` events reads stored diff text from `data_triples` (the triple with predicate `urn:sempkm:bodyDiff`) and parses it via new `_parse_stored_diff()` method. Old `body.set` events continue using `_compute_body_diff()` for backward compatibility.

4. **_parse_stored_diff()** (`query.py`): New method that parses unified diff format into `[{type: add|remove|context, text: str}]` display format. Identical logic to `_compute_body_diff()` parsing but reads from a stored string rather than computing fresh.

5. **Template** (`event_detail.html`): Condition extended from `'body.set' in ...` to `('body.set' in ... or 'body.diff' in ...)` — both operation types now render the diff panel.

6. **Tests**: Added 9 new tests to `test_body_diff.py` covering `_OP_PRIORITY`, `_parse_stored_diff()` (4 cases), event detail body.diff handling, and backward compat. Total: 17 tests, all passing.

## Verification

- `lsp diagnostics backend/app/browser/objects.py` — no new errors (all pre-existing import resolution issues in worktree)
- `lsp diagnostics backend/app/events/query.py` — no new errors
- `python -m pytest tests/test_body_diff.py -v` — ✅ 17/17 passed
- `python -m pytest tests/ -v --tb=short` — ✅ 872 passed, 0 failures (no regressions)
- `python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); assert 'body.diff' in HANDLER_REGISTRY; print('OK')"` — ✅
- `python -c "from app.commands.router import _COMMAND_EVENT_MAP; assert _COMMAND_EVENT_MAP.get('body.diff') == 'object.changed'; print('OK')"` — ✅

### Slice-level verification (partial — T02 is intermediate):
- ✅ handler produces correct Operation, data triples, materialization
- ✅ _parse_stored_diff() parses stored diffs correctly
- ✅ get_event_detail() reads stored diff for body.diff events
- ✅ get_event_detail() still computes diff for old body.set events (backward compat)
- ✅ _OP_PRIORITY includes body.diff
- ✅ Template renders both body.set and body.diff
- ⏳ build_compensation() for body.diff — deferred to T03
- ⏳ save_body() integration tests (routing logic) — deferred to T03

## Diagnostics

- **Inspect stored diff in event graph:** `SELECT ?diff WHERE { GRAPH <event_iri> { ?s <urn:sempkm:bodyDiff> ?diff } }`
- **Verify save_body branching:** Check event log after editing an existing object — should show `body.diff` operation type instead of `body.set`
- **Failure shape:** If SPARQL query for existing body fails, save_body() raises unhandled exception → 500 response
- **No-op verification:** Save body without changes — no new event appears in event log

## Deviations

None.

## Known Issues

- Worktree `.venv` has no packages installed — must use main repo venv at `/home/james/Code/SemPKM/backend/.venv/bin/python` with `PYTHONPATH` override for verification commands.

## Files Created/Modified

- `backend/app/browser/objects.py` — save_body() now queries existing body and branches between body.diff/body.set/no-op
- `backend/app/events/query.py` — added body.diff to _OP_PRIORITY, body.diff handling in get_event_detail(), new _parse_stored_diff() method
- `backend/app/templates/browser/event_detail.html` — condition extended to render body.diff events
- `backend/tests/test_body_diff.py` — added 9 T02 tests (17 total)
- `.gsd/milestones/M012/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M012/slices/S02/S02-PLAN.md` — marked T02 done
