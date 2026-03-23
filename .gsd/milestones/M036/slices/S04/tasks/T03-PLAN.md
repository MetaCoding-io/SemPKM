---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T03: Full verification — parse validation, test suite, manifest check

**Slice:** S04 — Extended Framework Library
**Milestone:** M036

## Description

Final quality gate for S04. Parse all 4 JSON-LD files via rdflib and confirm they're structurally valid. Run the full quadrant test suite (existing 28 + ~10 new from T01) and confirm all pass. Validate the manifest has icon entries for every type defined in the ontology. Spot-check that each new quadrant type has exactly 2 `sh:in` properties with exactly 2 values so `_detect_quadrant_axes()` will discover them. Fix any issues found during validation.

## Steps

1. **Parse all 4 JSON-LD files via rdflib.** Run `Graph().parse(file, format='json-ld')` for ontology, shapes, views, and seed. Report triple counts. Any parse error is a blocker — fix the JSON-LD before continuing.

2. **Run the full test suite.** Execute `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v`. All tests (original 28 + new from T01) must pass. If any fail, diagnose and fix.

3. **Validate manifest completeness.** Check that every `@type` class in the ontology that is user-facing (i.e., has a NodeShape) has a corresponding icon entry in `manifest.yaml`. List any missing entries and add them.

4. **Spot-check quadrant axis constraints.** For each of the 5 new quadrant item types (SWOTItem, BCGItem, AnsoffItem, StakeholderItem, RiskItem), verify in the shapes file that exactly 2 PropertyShapes have `sh:in` with exactly 2 values. This is the contract that `_detect_quadrant_axes()` depends on. If any type has 0 or 1 matching properties, or has `sh:in` with 3+ values on an axis property, fix the shapes.

5. **Fix any issues found.** If parse errors, test failures, missing manifest entries, or incorrect `sh:in` counts are found, fix them in the source files and re-verify.

## Must-Haves

- [ ] All 4 JSON-LD files parse without error
- [ ] All unit tests pass (28 existing + ~10 new)
- [ ] Every NodeShape type has a manifest icon entry
- [ ] Each quadrant item type has exactly 2 properties with `sh:in` of length 2

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all pass
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(f'ontology: {len(g)} triples')"` — no error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(f'shapes: {len(g)} triples')"` — no error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/views/business-planning.jsonld', format='json-ld'); print(f'views: {len(g)} triples')"` — no error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/seed/business-planning.jsonld', format='json-ld'); print(f'seed: {len(g)} triples')"` — no error

## Observability Impact

- **No new runtime signals** — T03 is a verification-only task. It validates existing artifacts rather than adding runtime code.
- **Future agent inspection:** If any verification check fails, the task summary's Verification Evidence table records which specific check failed and why. The fix is always in the model archive files or test file, not in runtime code.
- **Failure visibility:** Parse errors surface as Python tracebacks with file path and line. Test failures surface via pytest output with assertion diffs. Manifest gaps surface as a list of missing type entries.

## Inputs

- `models/business-planning/ontology/business-planning.jsonld` — T02 output (complete ontology)
- `models/business-planning/shapes/business-planning.jsonld` — T02 output (complete shapes)
- `models/business-planning/views/business-planning.jsonld` — T02 output (complete views)
- `models/business-planning/seed/business-planning.jsonld` — T02 output (complete seed)
- `models/business-planning/manifest.yaml` — T02 output (complete manifest)
- `backend/tests/test_quadrant.py` — T01 output (extended test suite)

## Expected Output

- `models/business-planning/ontology/business-planning.jsonld` — validated (possibly with fixes)
- `models/business-planning/shapes/business-planning.jsonld` — validated (possibly with fixes)
- `models/business-planning/views/business-planning.jsonld` — validated (possibly with fixes)
- `models/business-planning/seed/business-planning.jsonld` — validated (possibly with fixes)
- `models/business-planning/manifest.yaml` — validated (possibly with fixes)
- `backend/tests/test_quadrant.py` — validated (possibly with fixes)
