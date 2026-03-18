---
id: T01
parent: S01
milestone: M010
provides:
  - SDK IRI prefix validation whitelist — model, standard vocab, and user-type IRIs pass through
  - Updated existing permission tests to match new enforcement scope
key_files:
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/tests/test_iri_prefix_fix.py
  - backend/tests/test_app_permissions.py
key_decisions:
  - "Enforcement narrowed to only urn:sempkm:app:* and urn:sempkm:data:* per D171 — everything else passes through"
patterns_established:
  - "IRI prefix check is a 2-line startswith guard, not a complex whitelist cascade — simpler is better"
observability_surfaces:
  - "PermissionError message includes both the offending IRI and the required prefix string"
  - "test_foreign_app_iri_blocked verifies error message content for diagnostics"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Fix SDK IRI prefix validation to whitelist model and standard namespace IRIs

**Rewrote `_check_iri_prefix()` to enforce only on `urn:sempkm:app:*` and `urn:sempkm:data:*` namespaces — model types, standard vocabularies, and user-types now pass through unchecked.**

## What Happened

The old `_check_iri_prefix()` treated ANY string starting with `urn:`, `http://`, or `https://` as an IRI and required it to start with `urn:sempkm:app:{appId}:`. This blocked all model type references and all standard vocabulary properties.

Rewrote the method to only enforce prefix checking on `urn:sempkm:app:*` and `urn:sempkm:data:*` — the two namespaces where apps create NEW IRIs that need scoping. All other IRIs (model namespace, user-types, http/https vocabs, urn:uuid, etc.) pass through with no check.

Updated 4 existing tests in `test_app_permissions.py` that tested the old restrictive behavior:
- `test_invalid_iri_raises` → `test_foreign_app_iri_raises` (uses `urn:sempkm:app:other-app:xxx`)
- `test_nested_params_scanned_recursively` → `test_nested_params_foreign_app_iri_scanned` (uses `urn:sempkm:app:evil-app:ref`)
- `test_deeply_nested_iri_caught` → `test_deeply_nested_data_iri_caught` (uses `urn:sempkm:data:foreign:thing`)
- `test_http_url_in_params_checked` → `test_http_url_in_params_allowed` (now asserts success)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py -v` — **13/13 tests passed**
- `cd backend && .venv/bin/python -m pytest tests/test_app_permissions.py -v` — **33/33 tests passed** (no regressions)
- Manual inspection of updated method: only `urn:sempkm:app:*` and `urn:sempkm:data:*` trigger the prefix check

### Slice-level verification (T01 scope):
- ✅ `cd backend && python -m pytest tests/test_iri_prefix_fix.py -v` — 13 tests pass (≥8 required)
- ⏳ `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — not yet created (T04)
- ⏳ Model manifest validation — not yet created (T02)
- ⏳ App manifest validation — not yet created (T03)
- ⏳ Docker integration — requires T02-T04

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_foreign_app_iri_blocked -v` to verify PermissionError message content
- PermissionError messages include both the offending IRI and the required prefix for easy debugging
- The method is at `backend/sdk/sempkm_app_sdk/clients/commands.py` — search for `_check_iri_prefix`

## Deviations

- Added 2 extra tests beyond the plan's 11: `test_urn_uuid_passes` (verifies other URN schemes) and `test_own_data_namespace_still_blocked` (verifies data namespace blocked even for own app-id). Total: 13 tests vs planned 11.
- Updated 4 existing tests in `test_app_permissions.py` to match new behavior — these tested the old restrictive logic which was the bug we're fixing.

## Known Issues

None.

## Files Created/Modified

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — rewrote `_check_iri_prefix()` with D171 whitelist logic
- `backend/tests/test_iri_prefix_fix.py` — new test file with 13 IRI prefix whitelist tests
- `backend/tests/test_app_permissions.py` — updated 4 tests to match new enforcement scope
- `.gsd/milestones/M010/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight)
- `.gsd/milestones/M010/slices/S01/S01-PLAN.md` — added diagnostic verification step (pre-flight)
