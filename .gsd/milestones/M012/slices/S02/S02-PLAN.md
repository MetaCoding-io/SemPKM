# S02: Body.Diff — Incremental Storage & Rendering

**Goal:** Body edits on existing objects store incremental unified diffs instead of full replacement text, and the event log renders them with green/red highlighting.
**Demo:** User edits an existing note body (changes one paragraph) → saves → opens event log → expands the event detail → sees green/red diff lines showing only the changed paragraph, not the full body text. Creating a new body still uses `body.set` with full text display.

## Must-Haves

- New `body.diff` operation type with `BodyDiffParams`/`BodyDiffCommand` in command schemas
- `handle_body_diff()` handler that stores diff text via `sempkm:bodyDiff` predicate and materializes full new body
- `save_body()` endpoint detects existing body in `urn:sempkm:current` — emits `body.diff` when prior body exists, `body.set` when no prior body (per D157)
- Skip event entirely when body content is unchanged (no-op save)
- `get_event_detail()` reads stored diff directly for `body.diff` events (no recomputation)
- `_OP_PRIORITY` includes `body.diff`
- Event detail template renders both `body.set` and `body.diff` events with diff highlighting
- `build_compensation()` handles `body.diff` undo — queries current body, reverse-applies diff, emits `body.set`
- Existing `body.set` events continue to display correctly (backward compatibility)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (SPARQL queries against triplestore for current body)
- Human/UAT required: no (unit tests + browser verification in S04)

## Verification

- `cd backend && python -m pytest tests/test_body_diff.py -v` — all tests pass
  - `handle_body_diff()` produces correct `Operation` with `operation_type="body.diff"`, `sempkm:bodyDiff` data triple, and correct materialize inserts/deletes
  - Diff computation produces expected unified diff output for simple text changes
  - `get_event_detail()` correctly parses stored diff for `body.diff` events
  - `get_event_detail()` still computes diff on-the-fly for old `body.set` events (backward compat)
  - `build_compensation()` for `body.diff` produces a `body.set` operation with old body restored
  - `save_body()` chooses `body.diff` when prior body exists, `body.set` when no prior body
  - `save_body()` skips event when body content is unchanged
- `cd backend && python -m pytest tests/ -v --tb=short` — no regressions in existing tests
- `cd backend && python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); assert 'body.diff' in HANDLER_REGISTRY; print('body.diff handler registered')"` — dispatcher knows about body.diff (failure: KeyError or AssertionError if wiring is broken)
- `cd backend && python -c "from app.commands.router import _COMMAND_EVENT_MAP; assert _COMMAND_EVENT_MAP.get('body.diff') == 'object.changed'; print('webhook mapping OK')"` — webhook event map is correct (failure: AssertionError if mapping missing)

## Observability / Diagnostics

- Runtime signals: `body.diff` events visible in event log with operation type `body.diff`; diff text stored as `sempkm:bodyDiff` literal in event graphs
- Inspection surfaces: Event log detail panel shows diff rendering; SPARQL query on event graphs can inspect stored diff text
- Failure visibility: If diff computation fails, save endpoint falls back to `body.set` (graceful degradation)

## Integration Closure

- Upstream surfaces consumed: `EventStore.commit()` (unchanged), `handle_body_set()` (unchanged, used as fallback), `_compute_body_diff()` (unchanged, used for old events)
- New wiring introduced: `handle_body_diff` registered in `dispatcher.py`, `body.diff` added to `_COMMAND_EVENT_MAP`, `save_body()` gains current-body query
- What remains before the milestone is truly usable end-to-end: S04 E2E browser tests verify the full user flow

## Tasks

- [x] **T01: Add body.diff command schema, handler, and dispatcher wiring** `est:45m`
  - Why: Foundation for the body.diff feature — creates the new operation type, handler, and wires it into the command system
  - Files: `backend/app/commands/schemas.py`, `backend/app/commands/handlers/body_diff.py`, `backend/app/commands/dispatcher.py`, `backend/app/commands/router.py`
  - Do: Create `BodyDiffParams(iri, body, diff_text, predicate)` and `BodyDiffCommand` in schemas. Create `handle_body_diff()` in new `handlers/body_diff.py` that stores `(subject, SEMPKM.bodyDiff, diff_literal)` and `(subject, predicate, new_body_literal)` in data_triples, with materialization deleting old body and inserting new. Register in dispatcher and add `body.diff` to webhook event map.
  - Verify: `python -c "from app.commands.handlers.body_diff import handle_body_diff; print('OK')"` and `python -c "from app.commands.schemas import BodyDiffCommand; print('OK')"`
  - Done when: `handle_body_diff` is importable, registered in `HANDLER_REGISTRY`, and `body.diff` maps to `object.changed` in `_COMMAND_EVENT_MAP`

- [ ] **T02: Modify save endpoint to emit body.diff and update event detail rendering** `est:1h`
  - Why: Core behavior change — makes `save_body()` detect existing body content and emit `body.diff` when appropriate, and makes the event detail viewer render stored diffs for `body.diff` events
  - Files: `backend/app/browser/objects.py`, `backend/app/events/query.py`, `backend/app/templates/browser/event_detail.html`
  - Do: (1) In `save_body()`, before building params, query `urn:sempkm:current` for existing body via SPARQL SELECT. If body exists and content differs, compute `difflib.unified_diff`, build `BodyDiffParams`, call `handle_body_diff()`. If body exists and content is identical, return early (no-op). If no body exists, use `handle_body_set()` as before. (2) Add `"body.diff"` to `_OP_PRIORITY` after `"body.set"`. In `get_event_detail()`, add branch for `body.diff`: read diff text from `data_triples` (the triple with predicate `urn:sempkm:bodyDiff`), parse into `[{type: add|remove|context, text: str}]` format, set on `body_diff`. (3) Update template condition from `'body.set' in detail.summary.operation_type` to also match `body.diff`.
  - Verify: LSP diagnostics clean. Manual review of query/template logic.
  - Done when: `save_body()` emits `body.diff` for existing bodies, `get_event_detail()` reads stored diffs for `body.diff` events, and template renders both `body.set` and `body.diff` with diff highlighting

- [ ] **T03: Add body.diff undo support and comprehensive unit tests** `est:1h`
  - Why: Closes the slice — undo support ensures body.diff events are reversible, and unit tests prove all code paths including backward compatibility
  - Files: `backend/app/events/query.py`, `backend/tests/test_body_diff.py`
  - Do: (1) Add `body.diff` case to `build_compensation()`: query current body from materialized state (it's the post-diff value), reverse-apply the diff (swap + and - lines in stored diff text, apply to current body) to recover pre-diff body, emit a `body.set` compensation operation. (2) Write comprehensive test file `test_body_diff.py` covering: handler produces correct Operation, diff computation for text changes, event detail parsing for body.diff events, event detail still computes diff for old body.set events, build_compensation for body.diff produces body.set with old body, save_body chooses body.diff vs body.set based on existing body, no-op when body unchanged.
  - Verify: `cd backend && python -m pytest tests/test_body_diff.py -v` — all tests pass; `cd backend && python -m pytest tests/ -v --tb=short` — no regressions
  - Done when: All unit tests pass, undo produces correct compensation operations, no regressions in existing test suite

## Files Likely Touched

- `backend/app/commands/schemas.py` — new `BodyDiffParams`, `BodyDiffCommand`, add to `Command` union
- `backend/app/commands/handlers/body_diff.py` — new file with `handle_body_diff()`
- `backend/app/commands/dispatcher.py` — register `handle_body_diff` in `HANDLER_REGISTRY`
- `backend/app/commands/router.py` — add `body.diff` to `_COMMAND_EVENT_MAP`
- `backend/app/browser/objects.py` — modify `save_body()` to detect existing body and choose operation type
- `backend/app/events/query.py` — add `body.diff` to `_OP_PRIORITY`, handle in `get_event_detail()` and `build_compensation()`
- `backend/app/templates/browser/event_detail.html` — extend condition to match `body.diff`
- `backend/tests/test_body_diff.py` — new test file
