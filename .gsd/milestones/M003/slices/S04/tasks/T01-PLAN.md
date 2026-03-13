---
estimated_steps: 5
estimated_files: 3
---

# T01: Fix seed data, ontology comment, and add tag-splitting unit tests

**Slice:** S04 — Tag System Fix & Tag Explorer
**Milestone:** M003

## Description

Fix the root cause of TAG-01 at the source: convert all 11 `bpkm:tags` values in the basic-pkm seed data from comma-separated strings to JSON-LD arrays. Update the ontology property comment to reflect individual-value storage. Create the unit test file for the tag-splitting function (tests will initially fail since the function is implemented in T02).

## Steps

1. Open `models/basic-pkm/seed/basic-pkm.jsonld` and convert every `"bpkm:tags": "a,b,c"` to `"bpkm:tags": ["a", "b", "c"]`. There are 11 objects with this pattern — verify count matches after edit.
2. Open `models/basic-pkm/ontology/basic-pkm.jsonld` and update `rdfs:comment` on `bpkm:tags` from `"Comma-separated tags for categorization"` to `"Tags for categorization (individual values)"`.
3. Create `backend/tests/test_tag_splitting.py` with unit tests covering:
   - `split_tag_values("a,b,c")` → `["a", "b", "c"]`
   - `split_tag_values("a, b , c")` → `["a", "b", "c"]` (trims whitespace)
   - `split_tag_values("single")` → `["single"]` (no-op for single value)
   - `split_tag_values("")` → `[]` (empty string)
   - `split_tag_values("a,,b")` → `["a", "b"]` (skips empty segments)
   - `is_tag_property("urn:sempkm:model:basic-pkm:tags")` → `True`
   - `is_tag_property("https://schema.org/keywords")` → `True`
   - `is_tag_property("http://purl.org/dc/terms/title")` → `False`
4. Validate seed data change: run `python -c "import json; d=json.load(open('models/basic-pkm/seed/basic-pkm.jsonld')); tags=[g['bpkm:tags'] for g in d['@graph'] if 'bpkm:tags' in g]; assert all(isinstance(t, list) for t in tags), 'Not all arrays'; print(f'{len(tags)} objects with array tags')"` — should print `11 objects with array tags`.
5. Run `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — tests should fail with `ImportError` or `ModuleNotFoundError` (function not yet implemented). This is expected and correct.

## Must-Haves

- [ ] All 11 `bpkm:tags` values in seed data converted to JSON-LD arrays
- [ ] Ontology comment updated to reflect individual-value storage
- [ ] Test file created with 8+ assertions covering split logic and property detection
- [ ] Seed data validates as correct JSON (no parse errors)

## Verification

- `python -c "import json; json.load(open('models/basic-pkm/seed/basic-pkm.jsonld'))"` — parses without error
- `python -c "import json; d=json.load(open('models/basic-pkm/seed/basic-pkm.jsonld')); assert all(isinstance(g['bpkm:tags'], list) for g in d['@graph'] if 'bpkm:tags' in g)"` — all tags are arrays
- `rg 'Comma-separated' models/basic-pkm/ontology/basic-pkm.jsonld` — returns no matches
- `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — test file loads (may fail on import, but file structure is valid)

## Observability Impact

- Signals added/changed: None (seed data change, no runtime signals)
- How a future agent inspects this: Check seed JSON-LD directly; inspect ontology comment
- Failure state exposed: JSON parse error if seed data is malformed

## Inputs

- `models/basic-pkm/seed/basic-pkm.jsonld` — current comma-separated tag strings
- `models/basic-pkm/ontology/basic-pkm.jsonld` — current ontology property definition
- S04-RESEARCH.md — documents 11 objects with comma-separated tags pattern

## Expected Output

- `models/basic-pkm/seed/basic-pkm.jsonld` — all `bpkm:tags` as JSON-LD arrays
- `models/basic-pkm/ontology/basic-pkm.jsonld` — updated rdfs:comment
- `backend/tests/test_tag_splitting.py` — unit test file with 8+ test cases (initially failing)
