---
id: T01
parent: S04
milestone: M003
provides:
  - Seed data with JSON-LD array tags (11 objects)
  - Updated ontology comment for bpkm:tags
  - Unit test file for tag-splitting functions (12 test cases)
key_files:
  - models/basic-pkm/seed/basic-pkm.jsonld
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - backend/tests/test_tag_splitting.py
key_decisions:
  - none
patterns_established:
  - Test file imports from app.commands.handlers.object_patch (split_tag_values, is_tag_property) — T02 must export these names from that module
observability_surfaces:
  - none (seed data and test-only changes)
duration: 1 step
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Fix seed data, ontology comment, and add tag-splitting unit tests

**Converted all 11 seed data tag values from comma-separated strings to JSON-LD arrays, updated ontology comment, and created 12 unit tests for tag-splitting functions.**

## What Happened

1. Edited `models/basic-pkm/seed/basic-pkm.jsonld` — converted all 11 `bpkm:tags` values from comma-separated strings (e.g. `"a,b,c"`) to JSON-LD arrays (e.g. `["a", "b", "c"]`). Objects span all four types: Project (2), Person (3), Note (3), Concept (3).
2. Edited `models/basic-pkm/ontology/basic-pkm.jsonld` — changed `rdfs:comment` on `bpkm:tags` from `"Comma-separated tags for categorization"` to `"Tags for categorization (individual values)"`.
3. Created `backend/tests/test_tag_splitting.py` with 12 test cases in two classes:
   - `TestSplitTagValues` (8 tests): basic split, whitespace trimming, single value, empty string, empty segments, whitespace-only, trailing comma, leading comma
   - `TestIsTagProperty` (4 tests): bpkm:tags → True, schema:keywords → True, dcterms:title → False, arbitrary predicate → False

## Verification

- `python3 -c "import json; json.load(open('models/basic-pkm/seed/basic-pkm.jsonld'))"` — ✅ parses without error
- `python3 -c "...assert all(isinstance(g['bpkm:tags'], list)...)"` — ✅ all 11 tags are arrays
- `rg 'Comma-separated' models/basic-pkm/ontology/basic-pkm.jsonld` — ✅ no matches (old comment gone)
- `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — ✅ ImportError on collection (expected — functions not yet implemented, T02 scope)

### Slice-level verification status (intermediate task — partial expected):
- `pytest tests/test_tag_splitting.py` — ❌ ImportError (expected, T02 implements functions)
- `pytest tests/test_tag_explorer.py` — not yet created (T03+ scope)
- E2E tag tests — not yet created (later task scope)

## Diagnostics

None — this task only modifies seed data and creates test scaffolding. Inspect seed JSON-LD directly to verify tag array format.

## Deviations

Added 4 extra test cases beyond the 8 specified in the plan (whitespace-only, trailing comma, leading comma, arbitrary predicate) for more thorough edge-case coverage. Total: 12 tests.

## Known Issues

None.

## Files Created/Modified

- `models/basic-pkm/seed/basic-pkm.jsonld` — converted 11 bpkm:tags values from comma-separated strings to JSON-LD arrays
- `models/basic-pkm/ontology/basic-pkm.jsonld` — updated rdfs:comment on bpkm:tags to reflect individual-value storage
- `backend/tests/test_tag_splitting.py` — 12 unit tests for split_tag_values() and is_tag_property() (initially failing)
