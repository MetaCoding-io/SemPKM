---
id: T04
parent: S02
milestone: M036
provides:
  - backend/tests/test_bmc.py — 31 unit tests covering BMC detection, SPARQL query building, and result grouping
key_files:
  - backend/tests/test_bmc.py
key_decisions: []
patterns_established:
  - BMC test structure mirrors test_quadrant.py exactly — same _make_property, _make_form, _build_service helpers with adapted assertions for 9-section BMC pipeline
observability_surfaces:
  - "pytest tests/test_bmc.py -v — 31 tests pin detection (10), SPARQL building (6), and result grouping (15)"
duration: 8m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T04: Unit tests for BMC detection, query building, and result grouping

**Created 31 unit tests in test_bmc.py covering the full BMC backend pipeline — section detection, SPARQL query generation, and 9-bucket result grouping with edge cases.**

## What Happened

Created `backend/tests/test_bmc.py` following the exact `test_quadrant.py` test structure with the same helper pattern (`_make_property`, `_make_form`, `_build_service`). Added `target_class` parameter to `_make_property` helper for canvas detection tests. Three test classes cover the complete BMC pipeline:

- **TestDetectBmcSections** (10 tests): happy path with 9 `sh:in` values, keyword preference for "sectiontype" in path (case-insensitive), rejection of properties with ≠9 values, fallback to first 9-value property without keyword match, no shapes service, no form, shapes exception, canvas property detection (BusinessModelCanvas target class), generic canvas name match, and no canvas when target class is unrelated.

- **TestBuildBmcSelect** (6 tests): basic query structure verification (SELECT with sectionType, label, sectionContent), sectionType non-OPTIONAL assertion, scope filter injection, canvas path OPTIONAL clause, no canvas clause when absent, and label path verification (rdfs:label|dcterms:title).

- **TestExecuteBmcQuery** (15 tests): groups into 9 section buckets, missing sections have empty items, empty results, total count, kebab-to-display label mapping, deduplication, query failure returns empty sections, item fields (iri/label/content), canonical section ordering, multiple items per section, unknown section type skipped, label fallback to local name, section_types dict in result, content defaults to empty string, and canvas field captured.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — 31 passed in 0.48s
- `grep -c "def test_\|async def test_" backend/tests/test_bmc.py` — 31 (≥ 20 required)
- All slice-level checks pass:
  - 4 JSON-LD model files parse without error
  - `parse_manifest()` validates (Business Planning version: 1.0.0)
  - `bmc` in `_VALID_RENDERERS` and `RENDERER_REGISTRY`
  - `stopPropagation` count in bmc.js: 2
  - `data-theme="dark"` count in bmc.css: 22
  - `data-section-type` count in bmc.css: 55

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` | 0 | ✅ pass | 0.48s |
| 2 | `grep -c "def test_\|async def test_" backend/tests/test_bmc.py` | 0 | ✅ pass (31 ≥ 20) | <1s |
| 3 | rdflib parse 4 JSON-LD model files | 0 | ✅ pass | <1s |
| 4 | `parse_manifest()` validates | 0 | ✅ pass | <1s |
| 5 | `bmc` in `RENDERER_REGISTRY` | 0 | ✅ pass | <1s |
| 6 | `grep -c "stopPropagation" frontend/static/js/bmc.js` | 0 | ✅ pass (2 ≥ 1) | <1s |
| 7 | `grep -c 'data-theme="dark"' frontend/static/css/bmc.css` | 0 | ✅ pass (22 ≥ 1) | <1s |
| 8 | `grep -c 'data-section-type' frontend/static/css/bmc.css` | 0 | ✅ pass (55 — 9 sections) | <1s |

## Diagnostics

- `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v --tb=short` — shows per-test pass/fail with short tracebacks on failure
- Test names encode the behavior pinned: `test_happy_path_9_values`, `test_keyword_preference_case_insensitive`, etc.
- `grep -c "def test_" backend/tests/test_bmc.py` — quick count of total tests

## Deviations

- Exceeded planned 20+ tests to 31 — added extra coverage for canvas detection (2 tests), unknown section type handling, content defaults, and canvas field capture. No structural deviations.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_bmc.py` — 31 unit tests across 3 test classes covering BMC backend pipeline
- `.gsd/milestones/M036/slices/S02/tasks/T04-PLAN.md` — Added Observability Impact section
