---
id: T02
parent: S04
milestone: M003
provides:
  - Tag-splitting functions (is_tag_property, split_tag_values) in object_patch module
  - Tag-splitting middleware in save_object() that splits comma-separated tags into individual triples
  - POST /browser/admin/migrate-tags endpoint for one-time triplestore migration
key_files:
  - backend/app/commands/handlers/object_patch.py
  - backend/app/browser/objects.py
  - backend/app/browser/workspace.py
key_decisions:
  - Placed split_tag_values and is_tag_property in object_patch.py (matching T01 test imports) rather than a separate utility module
patterns_established:
  - Tag properties identified by checking if IRI contains 'tags' or 'keywords' (case-insensitive)
  - Migration endpoint uses Python-side splitting (not SPARQL string functions) for triplestore portability
observability_surfaces:
  - logger.debug("Tag split: %s -> %s", value, result) in split_tag_values for diagnosing unexpected splits
  - POST /browser/admin/migrate-tags returns JSON {"migrated": N} count; errors surface as HTTP 500 with logged SPARQL query
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Implement tag-splitting middleware in save path and migration endpoint

**Added tag-splitting functions to object_patch module, wired into save_object() post-processing, and created idempotent tag migration endpoint.**

## What Happened

1. Added `is_tag_property(predicate_iri)` and `split_tag_values(value)` to `backend/app/commands/handlers/object_patch.py`. These are the public functions that T01 tests import from. `is_tag_property` checks if the IRI contains 'tags' or 'keywords' (case-insensitive). `split_tag_values` splits on commas, strips whitespace, and filters empty segments.

2. In `save_object()` (objects.py), added a post-processing loop after the properties dict is built from form data: iterates all property keys, and for any key matching `is_tag_property()`, flatmaps each value through `split_tag_values()`. This transforms `["a, b, c"]` into `["a", "b", "c"]` before the properties are passed to `ObjectPatchParams`.

3. Added `POST /browser/admin/migrate-tags` endpoint in workspace.py. It queries the `urn:sempkm:current` graph for `bpkm:tags` literals containing commas, then for each match: deletes the comma-separated literal and inserts individual trimmed tag triples. Uses Python-side splitting (not SPARQL string functions) for triplestore portability. Requires owner role. Returns `{"migrated": N}` count. Idempotent — re-running when no comma-separated values exist returns `{"migrated": 0}`.

## Verification

- `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — **12/12 passed**
- `cd backend && .venv/bin/pytest tests/ -v` — **183/183 passed**, zero regressions
- `rg "split_tag_values" backend/app/browser/objects.py` — confirms function is imported and called in save_object
- `rg "migrate-tags" backend/app/browser/` — confirms migration endpoint exists in workspace.py

### Slice-level verification (partial — intermediate task):
- ✅ `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — 12 passed
- ⏳ `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — test file not yet created (T03)
- ⏳ `cd e2e && npx playwright test tests/20-tags/` — E2E tests not yet created (T04)

## Diagnostics

- **Tag splitting logs:** `split_tag_values` emits `logger.debug("Tag split: %s -> %s", value, result)` when splitting occurs — visible in backend logs at DEBUG level during object saves.
- **Migration endpoint:** `POST /browser/admin/migrate-tags` returns `{"migrated": N}` for success, HTTP 500 with detail for failures. SPARQL queries are logged on exception.
- **Smoke test:** `docker compose exec backend python -c "from app.commands.handlers.object_patch import split_tag_values; print(split_tag_values('a,b,c'))"`

## Deviations

None. Functions placed in `object_patch.py` as T01 tests expected (matching the import path `app.commands.handlers.object_patch`).

## Known Issues

None.

## Files Created/Modified

- `backend/app/commands/handlers/object_patch.py` — Added `is_tag_property()`, `split_tag_values()` functions and logger
- `backend/app/browser/objects.py` — Added tag-splitting post-processing in `save_object()` after properties dict construction
- `backend/app/browser/workspace.py` — Added `POST /admin/migrate-tags` endpoint with `require_role("owner")`, `get_triplestore_client` imports, and `_sparql_escape` helper
