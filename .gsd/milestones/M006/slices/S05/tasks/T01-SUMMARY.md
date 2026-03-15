---
id: T01
parent: S05
milestone: M006
provides:
  - inject_values_binding() function for parameterized SPARQL with VALUES clause
  - context_iri, context_var, dashboard_mode query params on table_view and cards_view endpoints
  - data-emits-context, data-listens-to-context, data-dashboard-id attributes on view-embed blocks
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/dashboard/router.py
  - backend/tests/test_values_injection.py
  - backend/tests/test_dashboard.py
key_decisions:
  - VALUES clause prepended at start of WHERE body (before existing patterns) for predictable SPARQL composition
  - var_name validated with regex ^[A-Za-z_]\w*$ to prevent SPARQL injection via variable names
  - Context injection creates a new ViewSpec copy rather than mutating the cached spec in-place
patterns_established:
  - inject_values_binding(query, var_name, iri) pattern for parameterized SPARQL — reusable for any VALUES-based filtering
  - dashboard_mode=1 appended to all view-embed block URLs for template-level behavior switching
observability_surfaces:
  - logger.debug("inject_values_binding: var=%s iri=%s") on successful injection
  - logger.warning("inject_values_binding: rejected invalid IRI: %s") on validation failure
  - logger.warning("inject_values_binding: rejected invalid var_name: %s") on bad variable names
duration: 18m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Parameterized SPARQL with VALUES Injection

**Added `inject_values_binding()` to ViewSpecService and wired context params into table/cards endpoints and dashboard block rendering**

## What Happened

1. Added `inject_values_binding(query, var_name, iri)` to `backend/app/views/service.py`. It uses `_extract_where_body()` to find the WHERE clause, validates the IRI via `_validate_iri()` from browser helpers, validates var_name with `^[A-Za-z_]\w*$`, prepends `VALUES ?{var_name} { <{iri}> }` to the WHERE body, and reassembles the query. Returns query unchanged for empty/invalid inputs.

2. Added `context_iri`, `context_var`, and `dashboard_mode` query params to both `table_view()` and `cards_view()` in `backend/app/views/router.py`. When both context params are present, a copy of the ViewSpec is created with the modified SPARQL query (avoids mutating cached specs). `dashboard_mode` is passed to template context.

3. Updated `render_block()` in `backend/app/dashboard/router.py` to append `?dashboard_mode=1` to all view-embed block URLs, and add `data-emits-context="1"`, `data-listens-to-context="{var_name}"`, and `data-dashboard-id="{dashboard_id}"` attributes based on block config.

4. Created 13 unit tests for VALUES injection covering: simple query injection, nested braces, empty IRI no-op, invalid IRI rejection (angle brackets, quotes, whitespace), var_name sanitization (special chars, empty, digit-start, underscore), placement verification, HTTP and URN IRI acceptance.

5. Added 3 dashboard tests verifying render_block HTML output for listens_to_context, emits_context, and no-context-config scenarios.

## Verification

- `cd backend && .venv/bin/pytest tests/test_values_injection.py -v` — 13/13 passed
- `cd backend && .venv/bin/pytest tests/test_dashboard.py -v` — 22/22 passed (19 existing + 3 new)
- `cd backend && .venv/bin/pytest -x -q` — 615 passed, 0 failures
- `grep -rn "^<<<<<<< " backend/ frontend/` — zero conflict markers

### Slice-level verification status (T01 is first of 3 tasks):
- ✅ `test_values_injection.py` — all VALUES injection tests pass
- ✅ `test_dashboard.py` — context attribute tests pass
- ⬜ E2E browser test — requires T02 frontend wiring (not yet implemented)
- ✅ 0 conflict markers
- ⬜ Diagnostic failure path (invalid IRI graceful degradation) — needs running stack (T02/T03)

## Diagnostics

- Grep backend logs for `inject_values_binding` to trace VALUES injection events
- DEBUG log on successful injection, WARNING on rejected IRI or var_name
- View endpoint requests show `?context_iri=`, `?context_var=`, `?dashboard_mode=` in URL
- Block wrapper divs have `data-emits-context`, `data-listens-to-context`, `data-dashboard-id` attributes inspectable in browser devtools

## Deviations

- Added a 3rd dashboard test (no-context-config) beyond the 2 required, to verify plain view-embed blocks are unaffected but still get `dashboard_mode=1`

## Known Issues

None

## Files Created/Modified

- `backend/app/views/service.py` — added `inject_values_binding()` function + `_validate_iri` import
- `backend/app/views/router.py` — added context_iri/context_var/dashboard_mode params to table_view and cards_view, import inject_values_binding
- `backend/app/dashboard/router.py` — render_block adds dashboard_mode=1 and context data attributes on view-embed blocks
- `backend/tests/test_values_injection.py` — new file with 13 VALUES injection tests
- `backend/tests/test_dashboard.py` — extended with 3 context attribute tests (TestRenderBlockContextAttributes)
