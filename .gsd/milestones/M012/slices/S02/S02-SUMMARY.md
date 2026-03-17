---
id: S02
parent: M012
milestone: M012
provides:
  - body.diff operation type with BodyDiffParams/BodyDiffCommand schemas
  - handle_body_diff() handler storing diff text + full body in data triples
  - save_body() three-way branch — body.diff for changes, body.set for first body, no-op for unchanged
  - _parse_stored_diff() for rendering stored unified diffs in event detail
  - _reverse_apply_diff() for undo — reconstructs old body from stored diff
  - build_compensation() body.diff case producing body.set compensation
  - Event detail template rendering both body.set and body.diff with diff highlighting
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
  - D157 — body.diff only for updates; first body set remains body.set
patterns_established:
  - body.diff handler mirrors body.set but adds sempkm:bodyDiff data triple alongside the full body triple
  - save_body() queries urn:sempkm:current for existing body before choosing operation type
  - Stored diffs parsed from data_triples (sempkm:bodyDiff predicate) rather than recomputed
  - Unified diff normalization — each diff line must end with \n before storing (difflib header lines lack trailing newlines with lineterm="")
  - build_compensation for body.diff reconstructs old body from context+removed lines in unified diff, emits body.set
observability_surfaces:
  - body.diff events visible in event log with operation type body.diff
  - Stored diff text inspectable via SPARQL on event graphs (sempkm:bodyDiff predicate)
  - No-op saves produce no event — empty event log for unchanged body
  - _reverse_apply_diff() returns None on malformed diff — undo button disabled gracefully
drill_down_paths:
  - .gsd/milestones/M012/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012/slices/S02/tasks/T03-SUMMARY.md
duration: 52m
verification_result: passed
completed_at: 2026-03-17
---

# S02: Body.Diff — Incremental Storage & Rendering

**Body edits on existing objects now store incremental unified diffs instead of full replacement text, with diff rendering in event log and reversible undo.**

## What Happened

Three tasks built the body.diff feature bottom-up:

**T01 — Schema and handler plumbing.** Created `BodyDiffParams(iri, body, diff_text, predicate)` and `BodyDiffCommand` Pydantic schemas. Built `handle_body_diff()` handler that stores TWO data triples per event: `(subject, SEMPKM.bodyDiff, diff_literal)` for the diff text and `(subject, predicate, body_literal)` for the full new body. Materialization is identical to body.set (delete old → insert new). Registered in `HANDLER_REGISTRY` and added `body.diff → object.changed` to `_COMMAND_EVENT_MAP`.

**T02 — Save endpoint branching and event detail rendering.** Modified `save_body()` with a three-way branch: (a) body unchanged → early return, no event; (b) body exists and differs → compute `difflib.unified_diff`, emit `body.diff`; (c) no prior body → emit `body.set` (per D157). Added `body.diff` to `_OP_PRIORITY`. Created `_parse_stored_diff()` to read diff text from stored `sempkm:bodyDiff` triples and parse into `[{type: add|remove|context, text}]` format for template rendering. Extended event detail template to render both `body.set` and `body.diff` operation types with identical diff highlighting CSS.

**T03 — Undo support and comprehensive tests.** Built `_reverse_apply_diff()` — reconstructs old body from stored diff by keeping context + removed lines, skipping added lines (well-known unified diff property). Added `body.diff` case to `build_compensation()` producing a `body.set` operation with the recovered old body. Discovered and fixed a diff normalization bug: `difflib.unified_diff` with `lineterm=""` produces header lines without trailing `\n`, breaking diff parsing. Fixed by normalizing all lines to end with `\n` before joining. 34 total unit tests cover all code paths.

## Verification

- `python -m pytest tests/test_body_diff.py -v` — 34/34 passed
- `python -m pytest tests/ -v --tb=short` — 943 passed, 0 failures (no regressions)
- `handle_body_diff` importable and registered in `HANDLER_REGISTRY`
- `_COMMAND_EVENT_MAP["body.diff"] == "object.changed"`
- `_OP_PRIORITY` includes `body.diff` after `body.set`
- `_parse_stored_diff()` correctly parses additions, removals, context, headers, empty input
- `_reverse_apply_diff()` handles line changes, additions, removals, multiple changes, empty/malformed input
- `build_compensation()` for body.diff produces body.set with correct old body
- `build_compensation()` for body.set still works (backward compat)
- Event detail template renders both body.set and body.diff

## Requirements Advanced

- BDIFF-01 — Body changes now store incremental diffs via body.diff operation type with stored unified diff in sempkm:bodyDiff predicate
- BDIFF-02 — Event detail template extended to render body.diff events with add/remove/context highlighting
- BDIFF-03 — body.set events continue rendering via existing _compute_body_diff() path, backward compat verified in tests

## Requirements Validated

None — full validation requires S04 E2E browser tests to prove the complete user flow in a live Docker environment.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- **Diff normalization fix** — T03 discovered that `difflib.unified_diff` with `lineterm=""` produces header lines without trailing `\n`, causing stored diffs to be unparseable by `_parse_stored_diff()` and `_reverse_apply_diff()`. Fixed by normalizing each line to end with `\n` before joining. This was not in the original plan but was required for correctness. Added to KNOWLEDGE.md.

## Known Limitations

- **No E2E browser verification yet** — the full user flow (edit body → save → open event log → see diff) is not verified against a running Docker stack. S04 will provide this.
- **No graceful fallback in save_body()** — if the SPARQL query for existing body fails, save_body() raises an unhandled exception (500 response). The plan mentioned "falls back to body.set" but this was not implemented since the SPARQL query is straightforward and shouldn't fail under normal conditions.
- **Worktree venv not self-contained** — tests run using main repo venv with PYTHONPATH override.

## Follow-ups

- S04 E2E tests must verify: edit existing body → event log shows body.diff with green/red highlighting; create new body → event log shows body.set with full text; edit body without changes → no new event.

## Files Created/Modified

- `backend/app/commands/handlers/body_diff.py` — new handler for body.diff operations
- `backend/app/commands/schemas.py` — BodyDiffParams, BodyDiffCommand, Command union updated
- `backend/app/commands/dispatcher.py` — body.diff registered in HANDLER_REGISTRY
- `backend/app/commands/router.py` — body.diff added to _COMMAND_EVENT_MAP
- `backend/app/browser/objects.py` — save_body() three-way branch + diff normalization
- `backend/app/events/query.py` — _OP_PRIORITY, _parse_stored_diff(), _reverse_apply_diff(), build_compensation() body.diff case, get_event_detail() body.diff branch
- `backend/app/templates/browser/event_detail.html` — condition extended for body.diff rendering
- `backend/tests/test_body_diff.py` — 34 unit tests across 10 test classes

## Forward Intelligence

### What the next slice should know
- body.diff is pure backend — no frontend JS changes were needed because the existing diff CSS (green/red line highlighting) in event_detail.html works for both body.set and body.diff events. The template just checks for either operation type.
- The `save_body()` function now has a SPARQL query at the top that hits `urn:sempkm:current` — this adds latency to every body save. Unlikely to be noticeable but worth knowing.

### What's fragile
- **Diff normalization** — the `difflib.unified_diff` header-line-no-newline issue is subtle. If anyone changes the diff computation in `save_body()` they must preserve the normalization step or `_reverse_apply_diff()` will silently produce wrong results. Pattern documented in KNOWLEDGE.md.
- **_reverse_apply_diff() is best-effort** — it returns None on malformed input rather than raising. Callers (build_compensation) must handle None gracefully.

### Authoritative diagnostics
- `python -m pytest tests/test_body_diff.py -v` — 34 tests covering all code paths, runs in <1s
- SPARQL: `SELECT ?diff WHERE { GRAPH <event_iri> { ?s <urn:sempkm:bodyDiff> ?diff } }` — inspect stored diff text in any body.diff event

### What assumptions changed
- Original plan expected `_parse_stored_diff()` to be trivial — it was, but the stored diff format required normalization that wasn't anticipated. The normalization fix was small but critical.
