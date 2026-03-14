---
estimated_steps: 5
estimated_files: 4
---

# T02: Fix broken tests, add M004 requirements, and close milestone

**Slice:** S05 — Docs & Test Coverage
**Milestone:** M004

## Description

Fix the 3 broken `TestCreateClassEndpoint` tests by adding the missing `description=""` and `example=""` parameters that the `create_class` route handler gained in S01. Add M004 feature requirements to REQUIREMENTS.md (PROP-01 through PROP-03, TYPE-05 through TYPE-07, TAB-01), mark them validated, and update the traceability table and coverage summary. Mark S05 complete in the M004 roadmap and update STATE.md.

## Steps

1. Read `backend/tests/test_class_creation.py` to locate the 3 failing test methods in `TestCreateClassEndpoint`: `test_create_class_missing_name_returns_422`, `test_create_class_success_returns_hx_trigger`, `test_create_class_updates_icon_cache`
2. Add `description=""` and `example=""` keyword arguments to each `await create_class(...)` call in those 3 tests — these match the `Form("")` defaults that FastAPI resolves but aren't provided when calling the handler directly
3. Run `cd backend && .venv/bin/pytest tests/test_class_creation.py::TestCreateClassEndpoint -q` to confirm all 4 tests pass
4. Run `cd backend && .venv/bin/pytest tests/ -q` to confirm all 386 tests pass with 0 failures
5. Add 7 new requirements to `.gsd/REQUIREMENTS.md` in the Validated section (they were delivered and verified in S01-S04):
   - PROP-01: In-app property creation (ObjectProperty and DatatypeProperty) — primary M004/S01
   - PROP-02: Property editing (rename, change domain/range) — primary M004/S03
   - PROP-03: Property deletion with confirmation — primary M004/S02
   - TYPE-05: Class editing (rename, icon, parent, add/remove properties, SHACL shape update) — primary M004/S01
   - TYPE-06: Class deletion with instance-count warnings and confirmation — primary M004/S02
   - TYPE-07: Custom section on Mental Models page listing user types/properties — primary M004/S03
   - TAB-01: Create-new-object opens fresh dockview tab — primary M004/S04
6. Update the traceability table with all 7 new requirements and update the coverage summary counts
7. Mark S05 as `[x]` in `.gsd/milestones/M004/M004-ROADMAP.md`
8. Update `.gsd/STATE.md` to reflect S05 completion and overall M004 milestone status

## Must-Haves

- [ ] 3 failing tests fixed: `description=""` and `example=""` added to all direct `create_class()` calls
- [ ] All 386 backend tests pass with 0 failures
- [ ] 7 M004 requirements added to REQUIREMENTS.md with validated status and correct primary slice attribution
- [ ] Traceability table includes all 7 new requirements
- [ ] Coverage summary updated (validated count increases by 7)
- [ ] S05 marked complete in M004-ROADMAP.md
- [ ] STATE.md updated

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py::TestCreateClassEndpoint -q` → 4 passed, 0 failed
- `cd backend && .venv/bin/pytest tests/ -q` → 386 passed, 0 failed
- `grep "PROP-01" .gsd/REQUIREMENTS.md` → returns match
- `grep "TYPE-07" .gsd/REQUIREMENTS.md` → returns match
- `grep "TAB-01" .gsd/REQUIREMENTS.md` → returns match
- `grep "\[x\] \*\*S05" .gsd/milestones/M004/M004-ROADMAP.md` → returns match

## Observability Impact

- Signals added/changed: None — test fixes and documentation files only
- How a future agent inspects this: run pytest, grep REQUIREMENTS.md, read STATE.md
- Failure state exposed: None

## Inputs

- `backend/tests/test_class_creation.py` — contains the 3 failing tests in TestCreateClassEndpoint
- `backend/app/ontology/router.py` — the `create_class` handler signature showing `description: str = Form("")`, `example: str = Form("")`
- `.gsd/REQUIREMENTS.md` — current requirements with 0 active, 81 validated
- `.gsd/STATE.md` — current project state
- `.gsd/milestones/M004/M004-ROADMAP.md` — roadmap with S01-S04 checked, S05 unchecked

## Expected Output

- `backend/tests/test_class_creation.py` — 3 test methods fixed with added params, all passing
- `.gsd/REQUIREMENTS.md` — 7 new validated requirements (PROP-01/02/03, TYPE-05/06/07, TAB-01), traceability updated, coverage summary: 88 validated
- `.gsd/milestones/M004/M004-ROADMAP.md` — S05 marked `[x]`
- `.gsd/STATE.md` — reflects M004 milestone completion status
