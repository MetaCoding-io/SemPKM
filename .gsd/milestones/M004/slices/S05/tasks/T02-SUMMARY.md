---
id: T02
parent: S05
milestone: M004
provides:
  - All 386 backend tests passing with 0 failures
  - 7 M004 requirements registered and validated in REQUIREMENTS.md
  - M004 milestone marked complete in roadmap and STATE.md
key_files:
  - backend/tests/test_class_creation.py
  - .gsd/REQUIREMENTS.md
  - .gsd/milestones/M004/M004-ROADMAP.md
  - .gsd/STATE.md
key_decisions:
  - Also fixed test_create_class_invalid_properties_json_returns_422 which had the same missing params (4 tests fixed total, not 3)
patterns_established:
  - When FastAPI handler gains new Form() params with defaults, direct-call tests must include them explicitly
observability_surfaces:
  - none
duration: 10m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Fix broken tests, add M004 requirements, and close milestone

**Fixed 4 broken TestCreateClassEndpoint tests by adding missing `description=""` and `example=""` params, registered 7 M004 requirements as validated, and closed the M004 milestone.**

## What Happened

The `create_class` route handler gained `description` and `example` Form parameters in S01. Four tests in `TestCreateClassEndpoint` called the handler directly without these params, causing `TypeError` failures. Added `description=""` and `example=""` to all 4 direct `create_class()` calls, plus updated the `assert_awaited_once_with` assertion to expect `description=None` and `example=None` (the handler strips empty strings to `None` before passing to the service).

Added 7 new validated requirements to REQUIREMENTS.md: PROP-01 (property creation), PROP-02 (property edit), PROP-03 (property delete), TYPE-05 (class edit), TYPE-06 (class delete with warnings), TYPE-07 (Custom section), TAB-01 (fresh tab fix). Updated traceability table with all 7 entries and coverage summary from 81 to 88 validated.

Marked S05 complete in M004-ROADMAP.md (all 5 slices now checked). Updated STATE.md to reflect M004 completion.

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py::TestCreateClassEndpoint -q` → 4 passed, 0 failed ✅
- `cd backend && .venv/bin/pytest tests/ -q` → 386 passed, 0 failed ✅
- `grep "PROP-01" .gsd/REQUIREMENTS.md` → match ✅
- `grep "TYPE-07" .gsd/REQUIREMENTS.md` → match ✅
- `grep "TAB-01" .gsd/REQUIREMENTS.md` → match ✅
- `grep "\[x\] \*\*S05" .gsd/milestones/M004/M004-ROADMAP.md` → match ✅
- Slice verification: `grep -c` for 6 doc sections → 6 ✅
- Slice verification: `grep -c` for 7 requirement IDs → 14 (each in Validated + Traceability) ✅

## Diagnostics

None — test fixes and documentation files only. Run `cd backend && .venv/bin/pytest tests/ -q` to verify.

## Deviations

Fixed 4 tests instead of 3 — `test_create_class_invalid_properties_json_returns_422` also had the same missing params issue. Also updated the `assert_awaited_once_with` assertion in `test_create_class_success_returns_hx_trigger` to include `description=None, example=None` since the router now passes these to the service.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_class_creation.py` — Added `description=""` and `example=""` to 4 direct `create_class()` calls; updated assertion to match new service call signature
- `.gsd/REQUIREMENTS.md` — Added 7 M004 requirements (PROP-01/02/03, TYPE-05/06/07, TAB-01) as validated; updated traceability table and coverage summary (81→88)
- `.gsd/milestones/M004/M004-ROADMAP.md` — Marked S05 as `[x]`
- `.gsd/STATE.md` — Updated to reflect M004 completion, phase idle, 88 validated requirements
