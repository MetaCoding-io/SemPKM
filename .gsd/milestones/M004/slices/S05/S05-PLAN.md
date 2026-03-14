# S05: Docs & Test Coverage

**Goal:** User guide documents all M004 features (property CRUD, class edit/delete, Custom section, fresh-tab fix); all backend tests pass; M004 requirements tracked and validated in REQUIREMENTS.md.
**Demo:** Chapter 10 of user guide has subsections for creating properties, editing classes, editing properties, deleting classes (with instance warning flow), deleting properties, and the Custom section on Mental Models. `cd backend && .venv/bin/pytest tests/ -q` shows 386 passed, 0 failed. REQUIREMENTS.md has M004 requirement entries marked validated.

## Must-Haves

- Chapter 10 extended with subsections covering all M004 features (property creation, class edit, property edit, class delete with instance warnings, property delete, Custom section on Mental Models)
- 3 broken `TestCreateClassEndpoint` tests fixed (add missing `description=""` and `example=""` params)
- All 386 backend tests pass with 0 failures
- M004 requirements added to REQUIREMENTS.md Active section, then validated with traceability entries
- STATE.md and M004-ROADMAP.md updated to reflect S05 completion and milestone status

## Proof Level

- This slice proves: contract (documentation accuracy + test coverage)
- Real runtime required: no (tests are pure-function with mocked triplestore)
- Human/UAT required: no (documentation is prose review, not UI verification — M004 UI was verified in S01-S04)

## Verification

- `cd backend && .venv/bin/pytest tests/ -q` → 386 passed, 0 failed
- `cd backend && .venv/bin/pytest tests/test_class_creation.py::TestCreateClassEndpoint -q` → 4 passed, 0 failed
- `grep -c "### Creating Properties\|### Editing Classes\|### Editing Properties\|### Deleting Classes\|### Deleting Properties\|### Custom Section" docs/guide/10-managing-mental-models.md` → 6 (all sections present)
- `grep -c "PROP-01\|PROP-02\|PROP-03\|TYPE-05\|TYPE-06\|TYPE-07\|TAB-01" .gsd/REQUIREMENTS.md` → at least 14 (each ID appears in Active/Validated + Traceability)

## Observability / Diagnostics

- Runtime signals: none — this slice produces static documentation and test fixes, no runtime changes
- Inspection surfaces: pytest output, grep on docs structure
- Failure visibility: pytest failure messages identify exact test + line; grep counts confirm doc section presence
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S01-S04 service methods, route handlers, and UI flows (documented as-built); existing `test_class_creation.py` and `test_ontology_service.py` test files
- New wiring introduced in this slice: none (docs + test maintenance only)
- What remains before the milestone is truly usable end-to-end: nothing — S01-S04 delivered all runtime features; this slice closes documentation and test hygiene

## Tasks

- [x] **T01: Update user guide chapter 10 with M004 feature documentation** `est:45m`
  - Why: Users need documentation for property creation, class/property editing, class/property deletion with instance warnings, and the Custom section on Mental Models — all delivered in S01-S04 but not yet documented
  - Files: `docs/guide/10-managing-mental-models.md`
  - Do: Add six subsections after the existing "Creating Custom Classes" section: Creating Properties, Editing Classes, Editing Properties, Deleting Classes (with instance warning flow), Deleting Properties, Custom Section on Mental Models. Follow existing heading levels and style (tip/warning blocks, step-by-step lists). Do not re-document M003 features already covered.
  - Verify: `grep -c "### Creating Properties\|### Editing Classes\|### Editing Properties\|### Deleting Classes\|### Deleting Properties\|### Custom Section" docs/guide/10-managing-mental-models.md` returns 6
  - Done when: all six subsections present in chapter 10 with accurate step-by-step instructions matching S01-S04 as-built behavior

- [x] **T02: Fix broken tests, add M004 requirements, and close milestone** `est:45m`
  - Why: 3 TestCreateClassEndpoint tests fail due to missing Form params; M004 requirements need to be registered in REQUIREMENTS.md; roadmap/state files need final updates
  - Files: `backend/tests/test_class_creation.py`, `.gsd/REQUIREMENTS.md`, `.gsd/STATE.md`, `.gsd/milestones/M004/M004-ROADMAP.md`
  - Do: (1) Add `description=""` and `example=""` to 3 failing test calls in TestCreateClassEndpoint. (2) Add M004 requirements to REQUIREMENTS.md: PROP-01 (property creation), PROP-02 (property edit), PROP-03 (property delete), TYPE-05 (class edit), TYPE-06 (class delete with warnings), TYPE-07 (Custom section on Mental Models), TAB-01 (create-new-object fresh tab) — mark as validated with primary slices. Update traceability table and coverage summary. (3) Mark S05 complete in M004-ROADMAP.md. (4) Update STATE.md.
  - Verify: `cd backend && .venv/bin/pytest tests/ -q` → 386 passed, 0 failed; `grep "PROP-01" .gsd/REQUIREMENTS.md` confirms requirement exists
  - Done when: all tests green, requirements registered and validated, roadmap shows S05 checked off, STATE.md reflects milestone completion status

## Files Likely Touched

- `docs/guide/10-managing-mental-models.md`
- `backend/tests/test_class_creation.py`
- `.gsd/REQUIREMENTS.md`
- `.gsd/STATE.md`
- `.gsd/milestones/M004/M004-ROADMAP.md`
