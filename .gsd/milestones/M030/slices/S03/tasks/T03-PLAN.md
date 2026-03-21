---
estimated_steps: 6
estimated_files: 5
---

# T03: Extend LintService with server-side filtering and wire user's filters into router

**Slice:** S03 — Lint Filter System (Suppress, Dismiss, Presets)
**Milestone:** M030

## Description

Add Python post-filtering to `LintService.get_results()` and `get_results_for_object()` so suppressed rules and dismissed object×rule pairs are excluded from returned results. Then wire the user's active filters into the lint router endpoints and browser routes so filtering is always applied.

Key design per D279: filter in Python after SPARQL returns results. For `get_results()` with pagination, use the over-fetch approach — fetch all results, filter, then re-paginate in Python. This is acceptable for typical result sets (~50-200 results).

## Steps

1. Extend `LintService.get_results_for_object()` in `backend/app/lint/service.py`:
   - Add optional params: `suppressed_rules: set[str] | None = None`, `dismissed_pairs: set[tuple[str,str]] | None = None`
   - After SPARQL returns `items` list, apply filtering:
     ```python
     if suppressed_rules:
         items = [i for i in items if i["source_shape"] not in suppressed_rules]
     if dismissed_pairs:
         items = [i for i in items if (object_iri, i["source_shape"]) not in dismissed_pairs]
     ```
   - Note: `source_shape` may be empty string — empty strings should NOT match any suppression (empty source_shape results always shown)

2. Extend `LintService.get_results()` in `backend/app/lint/service.py`:
   - Add same optional params: `suppressed_rules: set[str] | None = None`, `dismissed_pairs: set[tuple[str,str]] | None = None`
   - **Over-fetch approach**: When filters are active, remove the `OFFSET {offset} LIMIT {per_page}` from the results query. Fetch ALL results, then:
     - Apply Python filtering (exclude suppressed source_shapes, exclude dismissed focus_node+source_shape pairs)
     - Recalculate total from filtered list length
     - Slice `items[offset:offset+per_page]` for pagination
     - Recalculate total_pages from filtered total
   - When NO filters are active, keep existing SPARQL pagination (no performance regression)
   - Also fix the count query: when filters active, skip the separate count query (use filtered len instead)

3. Update lint API router in `backend/app/lint/router.py`:
   - In `get_lint_results()`: add `filter_service` dependency, call `filter_service.get_user_filters(user.id)` to get `(suppressed_rules, dismissed_pairs)`, pass them to `lint_service.get_results()`
   - Import `get_lint_filter_service` from dependencies

4. Update browser lint panel route in `backend/app/browser/objects.py`:
   - In `get_lint()` (~line 904): add `filter_service` dependency via `get_lint_filter_service`, call `get_user_filters(user.id)`, pass to `lint_service.get_results_for_object()`
   - Add dismissed count to template context: `dismissed_count` = count of dismissals for this specific object (filter `dismissed_pairs` by object_iri)

5. Update browser lint dashboard route in `backend/app/browser/pages.py`:
   - In `lint_dashboard()`: add `filter_service` dependency, call `get_user_filters(user.id)`, pass to `lint_service.get_results()`
   - Add `suppressed_count` to template context
   - Add `active_presets` to template context (from `filter_service.list_presets(user.id)`)

6. Write `backend/tests/test_lint_filtering.py`:
   - Mock SPARQL results (build fake return values matching `get_results_for_object` and `get_results` patterns)
   - Test: suppressed rule excluded from `get_results_for_object()`
   - Test: dismissed pair excluded from `get_results_for_object()`
   - Test: empty filters are no-op
   - Test: results with empty source_shape are never filtered
   - Test: `get_results()` over-fetch approach returns correct pagination after filtering
   - Test: `get_results()` without filters uses original SPARQL pagination
   - Target: 8+ tests

## Must-Haves

- [ ] `get_results_for_object()` accepts and applies suppression/dismissal filters
- [ ] `get_results()` applies filters with correct over-fetch re-pagination
- [ ] Empty `source_shape` results never filtered
- [ ] User's filters fetched and passed through in API router, browser lint panel, and browser dashboard
- [ ] 8+ filtering unit tests passing

## Verification

- `cd backend && python -m pytest tests/test_lint_filtering.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_lint_filter_service.py tests/test_lint_filter_api.py tests/test_lint_filtering.py -v` — full filter test suite passes

## Inputs

- `backend/app/lint/service.py` — existing LintService with `get_results()` and `get_results_for_object()`
- `backend/app/lint/filter_service.py` — T01's LintFilterService with `get_user_filters()` method
- `backend/app/lint/router.py` — T02's extended router with filter endpoints
- `backend/app/dependencies.py` — T02's `get_lint_filter_service` dependency

## Expected Output

- `backend/app/lint/service.py` — filtering params added to both query methods
- `backend/app/lint/router.py` — user filters wired into get_lint_results
- `backend/app/browser/objects.py` — user filters wired into lint panel
- `backend/app/browser/pages.py` — user filters + preset list wired into dashboard
- `backend/tests/test_lint_filtering.py` — 8+ passing tests
