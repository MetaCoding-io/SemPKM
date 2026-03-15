---
estimated_steps: 8
estimated_files: 5
---

# T01: Parameterized SPARQL with VALUES Injection

**Slice:** S05 — Interactive Dashboards — Cross-View Context
**Milestone:** M006

## Description

Add `inject_values_binding()` to ViewSpecService that safely injects a `VALUES ?var { <iri> }` clause into a SPARQL query's WHERE body. Wire it into the `table_view` and `cards_view` endpoints via a new `context_iri` query parameter, and update `render_block()` in the dashboard router to pass context_iri through to view-embed block URLs when the block config specifies `listens_to_context`.

## Steps

1. Add `inject_values_binding(query, var_name, iri)` to `backend/app/views/service.py`:
   - Import `_validate_iri` from `app.browser._helpers`
   - Extract WHERE body via existing `_extract_where_body()`
   - Validate IRI with `_validate_iri()` — return query unchanged if invalid
   - Build `VALUES ?{var_name} { <{iri}> }` string
   - Prepend VALUES clause to the WHERE body content
   - Reassemble the full query with the modified WHERE body
   - Log at DEBUG level when injection occurs, WARNING when IRI rejected

2. Add `context_iri`, `context_var`, and `dashboard_mode` query params to `table_view()` in `backend/app/views/router.py`:
   - `context_iri: str = Query(default="")` — the IRI to bind
   - `context_var: str = Query(default="")` — the SPARQL variable name (without `?`)
   - `dashboard_mode: int = Query(default=0)` — 1 when rendered inside a dashboard block
   - When both `context_iri` and `context_var` are non-empty, call `inject_values_binding()` on the spec's `sparql_query` before passing to `execute_table_query()`
   - Pass `dashboard_mode` to the template context

3. Add same params to `cards_view()` — same logic as table_view.

4. Update `render_block()` in `backend/app/dashboard/router.py`:
   - For view-embed blocks: read `emits_context` and `listens_to_context` from block config
   - Append `?dashboard_mode=1` to all view-embed block URLs
   - If `listens_to_context` is set, add `data-listens-to-context="{var_name}"` and `data-dashboard-id="{dashboard_id}"` attributes to the block wrapper div
   - The actual `context_iri` injection into the URL happens on the frontend via `htmx:configRequest` (T02)
   - If `emits_context` is true, add `data-emits-context="1"` attribute

5. Create `backend/tests/test_values_injection.py`:
   - Test: injects VALUES clause into simple SELECT WHERE query
   - Test: injects VALUES clause with nested braces in WHERE body
   - Test: returns query unchanged when IRI is empty
   - Test: returns query unchanged when IRI fails validation (contains `<`, `>`, quotes)
   - Test: var_name is sanitized (alphanumeric + underscore only)
   - Test: VALUES clause placed at start of WHERE body (before existing patterns)

6. Extend `backend/tests/test_dashboard.py`:
   - Test: render_block for view-embed with `listens_to_context` config produces correct data attributes
   - Test: render_block for view-embed with `emits_context` config produces correct data attribute

## Must-Haves

- [ ] `inject_values_binding()` uses `_validate_iri()` — never injects unvalidated IRIs
- [ ] VALUES clause goes inside WHERE body, not outside
- [ ] var_name validated to prevent SPARQL injection (alphanumeric + underscore only)
- [ ] Empty context_iri is a no-op (returns original query)
- [ ] Existing view endpoint behavior unchanged when context params absent

## Verification

- `cd backend && .venv/bin/pytest tests/test_values_injection.py -v` — all VALUES injection tests pass
- `cd backend && .venv/bin/pytest tests/test_dashboard.py -v` — all dashboard tests pass (existing + new)
- `cd backend && .venv/bin/pytest -x -q` — full suite passes, no regressions

## Observability Impact

- **New log signals:** `logger.debug("inject_values_binding: var=%s iri=%s", var_name, iri)` emitted on successful VALUES injection; `logger.warning("inject_values_binding: rejected invalid IRI: %s", iri)` on validation failure
- **Inspection:** Future agent can grep `inject_values_binding` in backend logs to trace whether context filtering fired. Query params `context_iri`, `context_var`, `dashboard_mode` are visible in request URLs / network tab.
- **Failure state:** Invalid IRI → query returned unchanged (graceful no-op). No error raised, but WARNING log emitted. Empty `context_iri` → silent no-op (no log).
- **Data attributes on DOM:** `data-listens-to-context`, `data-emits-context`, `data-dashboard-id` on view-embed block wrappers — inspectable via browser devtools.

## Inputs

- `backend/app/views/service.py` — existing `_extract_where_body()` for WHERE clause parsing
- `backend/app/browser/_helpers.py` — existing `_validate_iri()` for IRI validation
- `backend/app/dashboard/router.py` — existing `render_block()` dispatches by block type
- `backend/app/views/router.py` — existing `table_view()` and `cards_view()` endpoints

## Expected Output

- `backend/app/views/service.py` — new `inject_values_binding()` function
- `backend/app/views/router.py` — `table_view` and `cards_view` accept `context_iri`, `context_var`, `dashboard_mode` params
- `backend/app/dashboard/router.py` — `render_block()` passes context data attributes on view-embed blocks
- `backend/tests/test_values_injection.py` — new test file with 6+ tests
- `backend/tests/test_dashboard.py` — extended with 2+ new tests
