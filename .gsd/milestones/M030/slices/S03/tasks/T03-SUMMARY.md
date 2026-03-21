---
id: T03
parent: S03
milestone: M030
provides:
  - LintService.get_results_for_object() accepts suppressed_rules and dismissed_pairs filter params
  - LintService.get_results() supports over-fetch filtering with correct re-pagination
  - User filters automatically wired into lint API router, browser lint panel, and lint dashboard
  - 11 filtering unit tests covering suppression, dismissal, empty source_shape, and pagination
key_files:
  - backend/app/lint/service.py
  - backend/app/lint/router.py
  - backend/app/browser/objects.py
  - backend/app/browser/pages.py
  - backend/tests/test_lint_filtering.py
key_decisions:
  - source_shape is always populated on LintResultItem from SPARQL (not just in detail mode) so filtering can work; this also benefits the frontend for dismiss buttons
  - Empty filter sets (set()) are normalized to None before passing to LintService to avoid triggering the over-fetch path unnecessarily
patterns_established:
  - Over-fetch pattern for Python post-filtering with SPARQL: when filters active, skip OFFSET/LIMIT and count query, fetch all results, filter in Python, then re-paginate with slice
  - Empty source_shape guard: always check `not i.source_shape` before applying filter predicates to ensure results with no source shape are never excluded
observability_surfaces:
  - GET /api/lint/results total/total_pages reflect post-filter counts when user has active filters
  - dismissed_count in lint_panel template context; suppressed_count and active_presets in lint_dashboard template context
  - Single SPARQL query (no count query) when filters active; standard 2-query path when no filters
duration: 25min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Extend LintService with server-side filtering and wire user's filters into router

**Added Python post-filtering to LintService for suppressed rules and dismissed pairs, wired user filters into all 3 lint endpoints (API, browser panel, dashboard), with 11 passing unit tests.**

## What Happened

Extended `LintService.get_results_for_object()` and `get_results()` with optional `suppressed_rules` and `dismissed_pairs` parameters. After SPARQL returns results, Python list comprehensions exclude matching items while always preserving results with empty `source_shape` (those have no identifiable rule and should never be hidden).

For `get_results()`, implemented the over-fetch approach per D279: when filters are active, the SPARQL query runs without `OFFSET`/`LIMIT` and no separate count query is issued. All results are fetched, filtered in Python, then the total is recalculated from the filtered list length and items are sliced for the requested page. When no filters are active, the original 2-query SPARQL pagination is preserved with zero performance impact.

Wired `LintFilterService` into three consumer routes:
1. **API router** (`GET /api/lint/results`): fetches user filters and passes to `get_results()`
2. **Browser lint panel** (`GET /browser/lint/{iri}`): fetches user filters and passes to `get_results_for_object()`, adds `dismissed_count` to template context
3. **Browser lint dashboard** (`GET /browser/lint-dashboard`): fetches user filters and passes to `get_results()`, adds `suppressed_count` and `active_presets` to template context

## Verification

- `test_lint_filtering.py`: 11 tests covering suppression exclusion, dismissal exclusion, empty filters as no-op, empty source_shape protection, wrong-object dismissal non-exclusion, over-fetch pagination (page 1 and page 2), SPARQL pagination without filters, and count query skipping with filters.
- Full filter test suite: 59 tests across `test_lint_filter_service.py`, `test_lint_filter_api.py`, and `test_lint_filtering.py` all passing.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filtering.py -v` | 0 | ✅ pass | 0.25s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filter_service.py tests/test_lint_filter_api.py tests/test_lint_filtering.py -v` | 0 | ✅ pass | 3.76s |

## Diagnostics

- **Verify filtering active:** Compare `GET /api/lint/results` response `total` before and after adding suppressions via `POST /api/lint/suppress`
- **Inspect active filters:** `GET /api/lint/suppressions` and `GET /api/lint/dismissals` show what's being filtered
- **Performance check:** When filters are active, only 1 SPARQL query is issued per `get_results()` call (observable in debug logs). Without filters, 2 queries (count + paginated results).
- **Template context:** `dismissed_count` available in lint panel, `suppressed_count` and `active_presets` available in lint dashboard

## Deviations

- `source_shape` is now always populated on `LintResultItem` from SPARQL results (previously only in `detail=True` mode). This is needed for the filtering logic and is a backwards-compatible enhancement since the field is `Optional[str]` with `None` default.

## Known Issues

None.

## Files Created/Modified

- `backend/app/lint/service.py` — Added filter params to `get_results_for_object()` and `get_results()`, implemented over-fetch re-pagination
- `backend/app/lint/router.py` — Wired `filter_service` dependency into `get_lint_results()` endpoint
- `backend/app/browser/objects.py` — Wired `filter_service` into lint panel route, added `dismissed_count` to context
- `backend/app/browser/pages.py` — Wired `filter_service` into lint dashboard, added `suppressed_count` and `active_presets` to context
- `backend/tests/test_lint_filtering.py` — 11 unit tests for post-SPARQL filtering logic
- `.gsd/milestones/M030/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section
