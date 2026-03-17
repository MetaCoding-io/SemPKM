---
id: S02
parent: M012
milestone: M012
provides:
  - body.diff operation type with BodyDiffParams/BodyDiffCommand schemas
  - handle_body_diff() handler storing unified diff alongside full body in data triples
  - save_body() three-way branching — body.diff for changes, body.set for first body, no-op for unchanged
  - _parse_stored_diff() and _reverse_apply_diff() for diff rendering and undo
  - body.diff registered in HANDLER_REGISTRY, _COMMAND_EVENT_MAP, and _OP_PRIORITY
  - event_detail.html renders both body.set and body.diff events with diff highlighting
  - build_compensation() handles body.diff undo — recovers old body from stored diff, emits body.set
requires: []
affects:
  - S04
key_files:
  - backend/app/commands/handlers/body_diff.py
  - backend/app/commands/schemas.py
  - backend/app/commands/dispatcher.py
  - backend/app/commands/router.py
  - backend/app/browser/objects.py
  - backend/app/events/query.py
  - backend/app/templates/browser/event_detail.html
  - backend/tests/test_body_diff.py
key_decisions:
  - D156 — Line-level unified diff via difflib (stdlib, no new dependency)
  - D157 — body.diff only for updates; first body set remains body.set
patterns_established:
  - body.diff handler mirrors body.set but adds sempkm:bodyDiff data triple for stored diff text alongside the full body triple
  - save_body() queries urn:sempkm:current for existing body before choosing operation type
  - Unified diff normalization — always ensure each diff line ends with \n before storing (difflib header lines lack trailing newlines with lineterm="")
  - build_compensation for body.diff reconstructs old body from context+removed lines, emits body.set
observability_surfaces:
  - body.diff events visible in event log with operation type body.diff
  - Stored diff text queryable via SPARQL — SELECT ?diff WHERE { GRAPH <event_iri> { ?s <urn:sempkm:bodyDiff> ?diff } }
  - No-op saves produce no event (empty event log for unchanged body)
  - build_compensation returns None on malformed diff — undo button disabled gracefully
drill_down_paths:
  - .gsd/milestones/M012/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012/slices/S02/tasks/T03-SUMMARY.md
duration: 52m
verification_result: passed
completed_at: 2026-03-17
---

# S02: Body.Diff — Incremental Storage & Rendering

**Body edits on existing objects now store incremental unified diffs instead of full replacement text, with diff highlighting in the event log and full undo support.**

## What Happened

Three tasks built the body.diff feature end-to-end:

**T01 — Schema, handler, and wiring.** Created `BodyDiffParams(iri, body, diff_text, predicate)` and `BodyDiffCommand` Pydantic schemas in `schemas.py`. The handler `handle_body_diff()` in new `handlers/body_diff.py` mirrors `handle_body_set()` but stores two data triples: `(subject, SEMPKM.bodyDiff, diff_literal)` for the diff text and `(subject, predicate, body_literal)` for the full new body. Materialization is identical to body.set (delete old, insert new). Registered `body.diff` in `HANDLER_REGISTRY` and added `body.diff → object.changed` to `_COMMAND_EVENT_MAP`.

**T02 — Save endpoint branching and event detail rendering.** Modified `save_body()` in `objects.py` to query `urn:sempkm:current` for existing body content before choosing operation type. Three-way branch: (a) body unchanged → early return, no event; (b) body exists and differs → compute `difflib.unified_diff`, emit `body.diff`; (c) no prior body → emit `body.set` (per D157). Added `body.diff` to `_OP_PRIORITY` for compound event ordering. Added `_parse_stored_diff()` to `EventQueryService` — reads diff text from stored `sempkm:bodyDiff` data triple and parses into `[{type, text}]` display format. Extended `event_detail.html` condition to render both `body.set` and `body.diff` using existing diff CSS.

**T03 — Undo support and comprehensive tests.** Added `_reverse_apply_diff()` to reconstruct the old body from a stored unified diff (context + removed lines = original file). Added `body.diff` case to `build_compensation()`: reads diff and body predicate from data triples, reverse-applies diff to recover old body, emits `body.set` compensation. Discovered and fixed a diff normalization bug — `difflib.unified_diff` with `lineterm=""` produces header lines without trailing `\n`, which broke both `_parse_stored_diff()` and `_reverse_apply_diff()`. Fixed by normalizing each line to end with `\n` before joining. Wrote 34 total tests covering all code paths.

## Verification

All slice-level verification checks passed:

- `python -m pytest tests/test_body_diff.py -v` — **34/34 passed**
  - ✅ `handle_body_diff()` produces correct Operation with `operation_type="body.diff"`, `sempkm:bodyDiff` data triple, and correct materialize inserts/deletes
  - ✅ Diff computation produces expected unified diff output for simple text changes
  - ✅ `get_event_detail()` correctly parses stored diff for `body.diff` events
  - ✅ `get_event_detail()` still computes diff on-the-fly for old `body.set` events (backward compat)
  - ✅ `build_compensation()` for `body.diff` produces a `body.set` operation with old body restored
  - ✅ `build_compensation()` for `body.set` still works (no regression)
  - ✅ `save_body()` routing logic tested (body.diff vs body.set vs no-op)
  - ✅ `_reverse_apply_diff()` handles line changes, additions, removals, multiple changes, empty/malformed input
- `python -m pytest tests/ -v --tb=short` — **943 passed, 0 failures** (no regressions)
- Dispatcher wiring: `'body.diff' in HANDLER_REGISTRY` — ✅
- Webhook mapping: `_COMMAND_EVENT_MAP['body.diff'] == 'object.changed'` — ✅
- Schema imports: `BodyDiffCommand`, `BodyDiffParams` — ✅

## Requirements Advanced

- BDIFF-01 — Body changes store incremental diffs instead of full replacements. `save_body()` now computes and stores unified diff when prior body exists, and stores diff text as `sempkm:bodyDiff` data triple.
- BDIFF-02 — Event log renders body.diff events with addition/deletion highlighting. `event_detail.html` condition extended to render both `body.set` and `body.diff` with diff highlighting CSS.
- BDIFF-03 — Existing body.set events continue to display correctly. Backward compat tested: `get_event_detail()` still computes diff on-the-fly for old `body.set` events.

## Requirements Validated

- none — BDIFF-01/02/03 are advanced but not validated until S04 E2E browser tests confirm the full user flow in a running Docker instance.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Diff normalization fix** — discovered that `difflib.unified_diff` with `lineterm=""` produces header lines without trailing `\n`, causing stored diffs to be unparseable by both `_parse_stored_diff()` and `_reverse_apply_diff()`. Not in the original plan but required for correctness. Fixed in `save_body()` with per-line normalization.

## Known Limitations

- **No live browser verification** — unit tests prove all code paths but E2E browser tests verifying the full user flow (edit body → see diff in event log) are deferred to S04.
- **No graceful fallback on diff failure** — if unified diff computation raises an exception in `save_body()`, it propagates as a 500 error. The plan mentions fallback to `body.set` but was not implemented since `difflib.unified_diff` on two strings is not expected to fail.

## Follow-ups

- S04 E2E tests should cover: edit existing body → event log shows body.diff with green/red highlighting; create new body → event log shows body.set with full text; edit body to same content → no new event created.

## Files Created/Modified

- `backend/app/commands/handlers/body_diff.py` — new handler for body.diff operations
- `backend/app/commands/schemas.py` — added BodyDiffParams, BodyDiffCommand, updated Command union
- `backend/app/commands/dispatcher.py` — registered body.diff handler
- `backend/app/commands/router.py` — added body.diff to webhook event map
- `backend/app/browser/objects.py` — save_body() three-way branching + diff normalization
- `backend/app/events/query.py` — _OP_PRIORITY, _parse_stored_diff(), _reverse_apply_diff(), body.diff in get_event_detail() and build_compensation()
- `backend/app/templates/browser/event_detail.html` — extended condition to render body.diff events
- `backend/tests/test_body_diff.py` — 34 unit tests across 10 test classes

## Forward Intelligence

### What the next slice should know
- body.diff is pure backend — no new frontend JS was needed. The event detail template already had diff rendering CSS from body.set, and body.diff reuses it.
- The `sempkm:bodyDiff` predicate stores the raw unified diff text in event graph data triples. This is the source of truth — diffs are never recomputed from before/after states for body.diff events.

### What's fragile
- **Diff normalization** — the `save_body()` normalization loop (`line if line.endswith("\n") else line + "\n"`) is the only thing preventing malformed stored diffs. If someone stores a diff through a different code path without normalization, `_parse_stored_diff()` and `_reverse_apply_diff()` will produce garbled output (not crash, but wrong content). This is documented in KNOWLEDGE.md.
- **SPARQL query for existing body** — `save_body()` queries `urn:sempkm:current` graph directly. If the materialized state is out of sync with event history, the wrong operation type could be emitted.

### Authoritative diagnostics
- `python -m pytest tests/test_body_diff.py -v` — 34 tests covering all handler, rendering, undo, and routing code paths. If this passes, the body.diff feature is working.
- `SELECT ?diff WHERE { GRAPH <event_iri> { ?s <urn:sempkm:bodyDiff> ?diff } }` — inspect stored diff text for any body.diff event in the triplestore.

### What assumptions changed
- Original plan assumed diff normalization was unnecessary — actually, `difflib.unified_diff` with `lineterm=""` produces inconsistent line endings that must be normalized before storage.
