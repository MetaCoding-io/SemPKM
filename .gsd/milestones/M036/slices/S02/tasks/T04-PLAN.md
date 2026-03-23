---
estimated_steps: 3
estimated_files: 1
skills_used:
  - test
---

# T04: Unit tests for BMC detection, query building, and result grouping

**Slice:** S02 — Business Model Canvas — 9-Box Poster Renderer
**Milestone:** M036

## Description

Create `backend/tests/test_bmc.py` following the exact `test_quadrant.py` test structure — same helper functions, same mock patterns, same `AsyncMock`/`MagicMock` setup. Tests pin the BMC backend pipeline: `_detect_bmc_sections()`, `_build_bmc_select()`, and `execute_bmc_query()`.

## Steps

1. **Read** `backend/tests/test_quadrant.py` to understand the helper functions (`_make_property`, `_make_form`, `_build_service`), mock patterns, and test class structure.
2. **Create `test_bmc.py`** with adapted helpers: `_make_property()` and `_make_form()` unchanged. `_build_service()` adapted to mock the BMC-specific service methods. Add the 9 BMC section type values as a module-level constant. Test classes:
   - `TestDetectBmcSections` (~8 tests): happy path with 9 `sh:in` values on `bp:sectionType`, keyword preference for "sectiontype" in path (case-insensitive), rejection of property with ≠9 `sh:in` values, fallback when no keyword match but exactly one 9-value property exists, no shapes service returns `(None, None)`, no form for type returns `(None, None)`, shapes exception returns `(None, None)`, canvas property detection (finds ObjectProperty targeting BusinessModelCanvas).
   - `TestBuildBmcSelect` (~4 tests): basic query structure (SELECT with sectionType, title, sectionContent), OPTIONAL on sectionContent, with scope filter, with canvas path adds OPTIONAL canvas binding.
   - `TestExecuteBmcQuery` (~10 tests): groups items into 9 section buckets, missing sections appear with empty items list, handles empty results, total count correct, label mapping (kebab-case → display name), deduplicates subjects, query failure returns empty sections, items have iri/title/content fields, section ordering follows canonical BMC order, multiple items in same section.
3. **Run tests**: `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — all pass.

## Must-Haves

- [ ] 20+ tests total across 3 test classes
- [ ] Detection tests cover happy path, keyword preference, rejection, edge cases
- [ ] SPARQL building tests verify OPTIONAL on sectionContent
- [ ] Result grouping tests verify 9 buckets with correct label mapping
- [ ] All tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — all tests pass
- `grep -c "def test_\|async def test_" backend/tests/test_bmc.py` — ≥ 20

## Inputs

- `backend/tests/test_quadrant.py` — test structure pattern to follow
- `backend/app/views/service.py` — BMC service methods added by T02 (method signatures, return types)

## Expected Output

- `backend/tests/test_bmc.py` — 20+ unit tests covering detection, SPARQL building, and result grouping

## Observability Impact

- **Test count signal:** `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v --tb=short` — tests pin BMC detection, query building, and result grouping. Test names encode the behavior being pinned.
- **Failure visibility:** Pytest output shows which specific BMC pipeline behavior regressed (detection, SPARQL generation, or result grouping).
- **Inspection:** `grep -c "def test_\|async def test_" backend/tests/test_bmc.py` — should return ≥ 20.
