# S02: Body.Diff — Incremental Storage & Rendering — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

This slice adds a `body.diff` operation type so that editing an existing body stores an incremental unified diff instead of the full replacement text. The codebase is well-prepared — the diff computation (`difflib.unified_diff`) is already used in `_compute_body_diff()` for display, the event log template already renders diff lines with green/red CSS, and the `EventStore.commit()` is operation-type-agnostic (no changes needed there). The work is a contained backend change with a template rendering extension.

The slice touches five areas: (1) a new `body.diff` handler that stores the diff text in the event graph, (2) modification to `save_body()` in `objects.py` to detect existing body and choose `body.diff` vs `body.set`, (3) `get_event_detail()` changes to read the stored diff directly for `body.diff` events instead of computing it, (4) template changes in `event_detail.html` to render both operation types, and (5) undo support for `body.diff` events in `build_compensation()`. Additionally, the VFS write path (`vfs/write.py`) also commits `body.set` events — it should also gain diff awareness to be consistent.

This is straightforward work using established patterns. Risk is low — the main concern is ensuring backward compatibility (old `body.set` events with computed diffs continue working alongside new `body.diff` events with stored diffs).

## Recommendation

**Approach:** Create a new `handle_body_diff()` handler alongside `handle_body_set()`. Modify `save_body()` to query the current body from `urn:sempkm:current` first — if body exists, compute a unified diff and emit `body.diff`; if no body exists, emit `body.set` as before (per D157). Store the diff string as a single `sempkm:bodyDiff` literal in the event graph alongside the affected IRI and predicate. For event detail rendering, detect `body.diff` and read the stored diff directly rather than computing it.

**Diff storage format:** Store the unified diff output as a single string literal using `sempkm:bodyDiff` as the predicate. The diff is the output of `difflib.unified_diff()` joined with newlines — the same format already used for display. This avoids inventing a custom format and makes the stored diff human-readable in raw SPARQL queries.

**Undo approach:** For undoing `body.diff`, query the current body from `urn:sempkm:current`, apply the diff in reverse (swap + and - lines), and emit a compensating `body.set` with the reconstructed previous body. Simpler alternative: query the current body, and since the diff stores enough info to reconstruct the old body, build a `body.set` operation that restores it. In practice, the simplest approach is to query the materialized state for the current body (which is the post-diff value), then reverse-apply the diff to recover the pre-diff body and emit `body.set` as the compensating operation.

## Implementation Landscape

### Key Files

- `backend/app/commands/handlers/body_set.py` (56 lines) — Current `handle_body_set()`. Stays unchanged. **New file:** `body_diff.py` with `handle_body_diff()` that creates an `Operation` with `operation_type="body.diff"`, stores the diff text via a `sempkm:bodyDiff` predicate in the event graph, and materializes the full new body into `urn:sempkm:current` (materialization is the same as `body.set` — delete old body, insert new body).

- `backend/app/commands/schemas.py` (113 lines) — Add `BodyDiffParams(iri, body, diff_text, predicate)` model and `BodyDiffCommand` with `command: Literal["body.diff"]`. Add to `Command` discriminated union. The `body` field holds the new full body (needed for materialization), `diff_text` holds the computed diff string.

- `backend/app/commands/dispatcher.py` (55 lines) — Register `handle_body_diff` in `HANDLER_REGISTRY["body.diff"]`.

- `backend/app/commands/router.py` (line 40) — Add `"body.diff": "object.changed"` to `_COMMAND_EVENT_MAP` for webhook notifications.

- `backend/app/browser/objects.py` (line 362–414, `save_body()`) — **Key change.** Before building `BodySetParams`, query the current body from `urn:sempkm:current`:
  ```python
  body_sparql = f"""SELECT ?body WHERE {{
    GRAPH <urn:sempkm:current> {{ <{decoded_iri}> <{predicate_iri}> ?body }}
  }}"""
  ```
  If a body exists, compute `difflib.unified_diff(old_lines, new_lines)`, build `BodyDiffParams`, and call `handle_body_diff()`. If no body exists (first write), use `handle_body_set()` as before.

- `backend/app/events/query.py` (556 lines) — Three changes:
  1. Add `"body.diff"` to `_OP_PRIORITY` list (after `"body.set"`).
  2. In `get_event_detail()`, add a branch for `body.diff`: read the stored diff text from `data_triples` (the triple `<subject> sempkm:bodyDiff <diff_text>`), parse it into `[{type: add|remove|context, text: str}]` format, and set `body_diff` on `EventDetail`. No need to query before-values or compute diff — it's stored.
  3. In `build_compensation()`, add `body.diff` handler: query current body from materialized state, reverse-apply the diff to recover old body, emit a `body.set` compensation operation.

- `backend/app/templates/browser/event_detail.html` — Extend the first `{% if %}` block to also match `body.diff`:
  ```jinja
  {% if ('body.set' in detail.summary.operation_type or 'body.diff' in detail.summary.operation_type) and detail.body_diff %}
  ```
  The rest of the diff rendering (`.diff-body`, `.diff-lines`, `.diff-line-add`, `.diff-line-remove`) is identical — already works for `body.diff` since `body_diff` is the same `[{type, text}]` format.

- `backend/app/vfs/write.py` (line 79, `_commit_body_set()`) — Should also gain diff awareness for consistency. When a DAV PUT updates a body, the VFS write path currently always emits `body.set`. It should query the current body and emit `body.diff` when appropriate. However, this is in a sync context (`asyncio.run()`) which complicates the current-body query. **Recommendation:** Defer VFS diff support or add a minimal sync wrapper. The primary save path (browser `save_body()`) is the priority.

- `backend/app/rdf/namespaces.py` — Add `SEMPKM.bodyDiff` if not already defined (the `SEMPKM` namespace object auto-generates terms, so `SEMPKM.bodyDiff` should work as `URIRef("urn:sempkm:bodyDiff")`).

- `frontend/static/css/workspace.css` (lines 4247–4272) — No changes needed. The existing `.diff-line-add`, `.diff-line-remove`, `.diff-line-marker` CSS classes already handle the rendering.

- `frontend/static/js/app.js` (line 178) — The event console command form has `"body.set"` fields. Optionally add a `"body.diff"` entry, though users won't typically create body.diff events manually via the console.

### Build Order

**Task 1: Schema + Handler (foundation)**
Create `BodyDiffParams`, `BodyDiffCommand` in `schemas.py`. Create `handle_body_diff()` in new `handlers/body_diff.py`. Register in `dispatcher.py` and `router.py`. This is pure backend with no dependencies — can be unit-tested immediately.

**Task 2: Save endpoint modification (integration point)**
Modify `save_body()` in `objects.py` to query current body, compute diff, and choose `body.diff` vs `body.set`. This is the core behavior change. Adds one SPARQL read per body save.

**Task 3: Event detail rendering (display)**
Update `get_event_detail()` to handle `body.diff` events — read stored diff from data triples, parse into display format. Update `event_detail.html` template condition. Update `_OP_PRIORITY`.

**Task 4: Undo support**
Add `body.diff` case to `build_compensation()` — query current body, reverse-apply diff, emit `body.set` compensation.

**Task 5: Unit tests**
Test diff computation, handler output, event detail rendering for both `body.set` and `body.diff` events, undo/compensation for `body.diff`. Follow pattern in `test_event_log_labels.py`.

### Verification Approach

**Unit tests:**
- `test_body_diff.py`:
  - `handle_body_diff()` produces correct `Operation` with `operation_type="body.diff"`, `sempkm:bodyDiff` data triple, and correct materialize inserts/deletes
  - Diff computation produces expected unified diff output for simple text changes
  - `get_event_detail()` correctly parses stored diff for `body.diff` events (mock triplestore returning diff triple)
  - `get_event_detail()` still computes diff on-the-fly for old `body.set` events (backward compat)
  - `build_compensation()` for `body.diff` produces a `body.set` operation with the old body restored
  - Edge case: empty diff (no changes) — should still work or be prevented at save endpoint

**Browser verification:**
- Edit an object body (change one paragraph), save, open event log → expand the event detail → should show green/red diff lines (not full body text)
- Create a new object with a body → event log shows `body.set` with full text display
- Edit the body again → event log shows `body.diff` with incremental diff

## Constraints

- **Event graphs are immutable** — Cannot retroactively change `body.set` events to `body.diff`. Old events use the existing `_compute_body_diff()` rendering path; new events use stored diffs.
- **Body predicate can vary** — `BodySetParams.predicate` defaults to `sempkm:body` but can be model-specific. Diff computation must use the same predicate for querying old body.
- **One extra SPARQL read per body save** — Querying current body from `urn:sempkm:current` before computing the diff. The query is simple and fast: `SELECT ?body WHERE { GRAPH <urn:sempkm:current> { <IRI> <pred> ?body } }`.
- **VFS write path is sync** — `vfs/write.py` uses `asyncio.run()` to bridge sync/async. Adding diff awareness there requires an async current-body query inside the sync bridge. Deferring VFS diff support is acceptable since VFS body writes are less common than browser saves.

## Common Pitfalls

- **First body set must remain `body.set`** — If no prior body exists in `urn:sempkm:current`, there's no diff to compute. The save endpoint must check for existing body before choosing the operation type (per D157).
- **Diff of identical content** — If user saves body with no changes, the diff is empty. The save endpoint should either skip the event entirely or store a `body.diff` with an empty diff. Recommendation: skip the event (no-op) when the body content is unchanged — add an equality check before creating the operation.
- **`_compute_body_diff()` vs stored diff** — For `body.set` events, `get_event_detail()` currently computes the diff by querying `_query_before_value()` to find the previous event's body. For `body.diff` events, the diff is stored directly in the event graph. The template renders both identically. The code path must branch on operation type.
- **Predicate in diff triple vs body triple** — The `body.set` handler stores `(subject, predicate, bodyLiteral)` in data_triples. The `body.diff` handler should store `(subject, SEMPKM.bodyDiff, diffLiteral)` for the diff text. But it also needs to store the predicate used (for undo/context). Store both: `(subject, SEMPKM.bodyDiff, diffLiteral)` and `(subject, predicate, newBodyLiteral)` in data_triples. Or simpler: just store the diff text + use the subject IRI to infer the predicate. Since the affected IRI and predicate are recoverable from the materialized state, storing `(subject, SEMPKM.bodyDiff, diffText)` plus `(subject, predicate, newBody)` gives full context.

## Open Risks

- **VFS write path consistency** — If VFS body writes continue using `body.set` while browser saves use `body.diff`, the event log will show inconsistent operation types for the same action (editing body). This is acceptable for v1 but should be addressed. The VFS write path could be updated in a follow-up.
- **Large diffs** — If a user replaces most of a long document, the diff could be larger than the original body. `difflib.unified_diff` with context lines will produce a diff close to the size of both documents combined. No mitigation needed — this is an edge case and the diff is still smaller than storing two full copies.
