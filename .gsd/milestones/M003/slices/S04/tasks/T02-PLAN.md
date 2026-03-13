---
estimated_steps: 5
estimated_files: 3
---

# T02: Implement tag-splitting middleware in save path and migration endpoint

**Slice:** S04 — Tag System Fix & Tag Explorer
**Milestone:** M003

## Description

Implement the tag-splitting logic and wire it into the object save path. When a user saves an object, properties whose IRI contains `tags` or `keywords` have their values split on commas into individual entries. Also add a one-time migration endpoint that splits existing comma-separated `bpkm:tags` triples in the triplestore via SPARQL UPDATE.

## Steps

1. Create a tag-splitting utility — either in `backend/app/browser/objects.py` as private helpers or in a small utility module. Two functions:
   - `is_tag_property(predicate_iri: str) -> bool` — returns True if IRI path contains `tags` or `keywords`
   - `split_tag_values(value: str) -> list[str]` — splits on commas, strips whitespace, filters empty strings
2. In `save_object()` (backend/app/browser/objects.py), after the properties dict is built from form data (after the `for key in form_data.keys()` loop), add a post-processing step: iterate properties items; for keys matching `is_tag_property()`, flatmap each value through `split_tag_values()` replacing the original list. This ensures comma-separated input from a single form field becomes individual triples.
3. Add a tag migration endpoint in `backend/app/browser/workspace.py` (or a suitable admin route):
   - `POST /browser/admin/migrate-tags` (requires owner role)
   - Runs a SPARQL UPDATE against `urn:sempkm:current` graph: find all `bpkm:tags` literals containing a comma (`FILTER(CONTAINS(STR(?val), ","))`), delete them, and insert individual triples by string-splitting server-side (Python loop, not SPARQL string functions which vary by triplestore)
   - Return count of migrated triples
   - Idempotent: re-running when no comma-separated values exist is a no-op
4. Ensure the T01 unit tests now pass by importing from the correct module path. Update imports in `test_tag_splitting.py` if needed to match where the functions were placed.
5. Run `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — all tests pass.

## Must-Haves

- [ ] `is_tag_property()` correctly identifies `bpkm:tags` and `schema:keywords` IRIs
- [ ] `split_tag_values()` handles: commas, whitespace trimming, empty segments, single values
- [ ] `save_object()` calls tag splitting for tag properties before building ObjectPatchParams
- [ ] Migration endpoint exists, requires owner role, is idempotent
- [ ] All T01 unit tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — all tests pass
- `cd backend && .venv/bin/pytest tests/ -v` — no regressions in existing test suite
- Grep confirms `split_tag_values` is called in `save_object`: `rg "split_tag_values" backend/app/browser/objects.py`
- Grep confirms migration endpoint exists: `rg "migrate-tags" backend/app/browser/`

## Observability Impact

- Signals added/changed: `logger.debug("Tag split: %s -> %s", original, split_values)` in tag-splitting path for diagnosing unexpected splits
- How a future agent inspects this: Check logs during object save; hit migration endpoint to see count
- Failure state exposed: Migration endpoint returns JSON with `{"migrated": N}` count; errors surface as HTTP 500 with logged SPARQL query

## Inputs

- `backend/tests/test_tag_splitting.py` — tests from T01 defining the expected function signatures
- `backend/app/browser/objects.py` — existing `save_object()` function (line ~1059)
- `backend/app/commands/handlers/object_patch.py` — `handle_object_patch` already handles list values correctly
- S04-RESEARCH.md — documents the save flow and migration requirements

## Expected Output

- `backend/app/browser/objects.py` — modified with tag-splitting logic in save_object + utility functions
- `backend/app/browser/workspace.py` — new migrate-tags endpoint (or separate admin route file)
- `backend/tests/test_tag_splitting.py` — imports updated to match actual module location; all tests pass
