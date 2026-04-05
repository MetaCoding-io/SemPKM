# S02: Diff-Based Save — No Phantom Events

**Goal:** Eliminate phantom save events: form saves only create events for actually-changed properties, and no-op saves create no events at all.
**Demo:** After this: Open an object, change one property field, save. Check the event log — only the changed property appears. Change nothing and save — no event is created.

## Tasks
- [x] **T01: Added diff-based property filtering to save_object() and client-side body save short-circuit to eliminate phantom events** — ## Why
The `save_object()` endpoint unconditionally creates an `object.patch` event recording every form property as changed, even when values haven't changed. This produces phantom events that clutter the timeline. The fix: query current values from the triplestore, compare against form values with proper normalization, and only patch actually-changed properties. If nothing changed, skip the patch entirely.

Secondarily, `saveCurrentObject()` in JS always POSTs the body content even when unchanged. The backend already handles this no-op, but skipping the network call is cleaner.

## Steps

1. **Add current-value query in `save_object()`** (objects.py, after the properties dict is built ~line 1370, BEFORE `dcterms:modified` injection at line 1373):
   - Query: `SELECT ?p ?o WHERE { GRAPH <urn:sempkm:current> { <{decoded_iri}> ?p ?o } }`
   - Build `current_values: dict[str, list[str]]` from bindings, keyed by predicate IRI string, values as sorted list of `?o` value strings
   - Filter out `rdf:type` and `urn:sempkm:body` from current_values (these aren't form-managed)

2. **Add normalization helper `_normalize_value_for_compare(value: str) -> str`** (in objects.py, module-level):
   - For datetime-like strings (matches `YYYY-MM-DDTHH:MM` pattern): strip timezone suffix (`+00:00`, `+HH:MM`, `Z`), truncate to minute precision (first 16 chars)
   - For all other strings: return as-is
   - This matches the form template truncation in `_field.html:140-143`

3. **Filter to changed-only properties** (between current query and `ObjectPatchParams` creation):
   - For each property in the form `properties` dict:
     - Normalize both form values and current values using `_normalize_value_for_compare()`
     - Compare as sorted lists: `sorted(normalized_form) == sorted(normalized_current)`
     - If equal → skip this property
     - If different → include in `changed_properties` dict
   - Also include properties in form that have no current value (new properties)
   - Also include properties where current has values but form doesn't (deletions — form sent empty)

4. **Move `dcterms:modified` injection AFTER the diff check:**
   - Remove the unconditional `properties[dcterms_modified] = [...]` from line 1373
   - Only add `dcterms:modified` to `changed_properties` when `changed_properties` is non-empty

5. **Conditional patch:** Replace `if properties:` with `if changed_properties:` — use `changed_properties` instead of `properties` when creating `ObjectPatchParams`

6. **Client-side body save short-circuit** (workspace.js ~line 1196):
   - In the `if (editor)` block, before the `apiFetch` call, add: `if (content === editor._sempkmSavedContent) { markClean(activeIri); return; }`

## Key Constraints
- `dcterms:modified` MUST only appear in the patch when other properties actually changed. It's a timestamp tracking real modifications, not saves.
- The SPARQL query for current values uses the same `CURRENT_GRAPH` constant already imported (line 42).
- The `_normalize_value_for_compare` function must handle: full ISO datetime with timezone, datetime without timezone, datetime-local format (no seconds), plain date strings, and non-datetime strings (pass through unchanged).
- Multi-valued properties: form sends `key[]` collected via `getlist()`. Current values may have multiple bindings for same predicate. Both must be collected as lists and compared as sorted lists.
- Properties in current but NOT in the form's skip_fields list and not in the form submission should NOT be treated as deletions — the form only submits fields it renders.
  - Estimate: 1h
  - Files: backend/app/browser/objects.py, frontend/static/js/workspace.js
  - Verify: rg -n '_normalize_value_for_compare' backend/app/browser/objects.py && rg -n 'changed_properties' backend/app/browser/objects.py && rg -n '_sempkmSavedContent' frontend/static/js/workspace.js | grep -v '= content' | grep -c '_sempkmSavedContent'
- [x] **T02: Added 22 unit tests for _normalize_value_for_compare and _compute_changed_properties covering datetime normalization, multi-value ordering, new/deleted properties, and dcterms:modified injection guard** — ## Why
The diff logic in `save_object()` handles datetime normalization, multi-value comparison, and no-op detection. Unit tests ensure these edge cases are covered and prevent regressions.

## Steps

1. **Create `backend/tests/test_save_diff.py`** with tests for the `_normalize_value_for_compare()` helper:
   - Full ISO datetime with timezone `2026-04-05T12:30:45.123456+00:00` → `2026-04-05T12:30`
   - Datetime with Z suffix `2026-04-05T12:30:45Z` → `2026-04-05T12:30`
   - Datetime-local format (already truncated) `2026-04-05T12:30` → `2026-04-05T12:30`
   - Plain date `2026-04-05` → `2026-04-05` (pass-through)
   - Non-datetime string `hello world` → `hello world` (pass-through)
   - URI string `http://example.org/thing` → `http://example.org/thing` (pass-through)
   - Empty string → empty string

2. **Add integration-style tests** that exercise the diff filtering logic (can test inline or via extracted helper):
   - Unchanged properties → empty changed dict
   - One property changed → only that property in changed dict
   - DateTime property unchanged (different format) → not in changed dict
   - Multi-valued property with same values in different order → not in changed dict
   - New property (in form but not in current) → in changed dict
   - `dcterms:modified` only present when other changes exist

3. **Follow the existing test pattern** from `test_object_create_timestamps.py` — use pytest with async tests, import from `app.browser.objects` or test the helper directly.

## Key Constraints
- Tests must be runnable with `cd backend && python -m pytest tests/test_save_diff.py -v`
- The `_normalize_value_for_compare` function should be importable from `app.browser.objects`
- If the diff filtering logic is inline in `save_object()`, extract the comparison into a testable helper function (e.g., `_compute_changed_properties(form_props, current_props)`) that T02 can import and test directly.
  - Estimate: 30m
  - Files: backend/tests/test_save_diff.py, backend/app/browser/objects.py
  - Verify: cd backend && python -m pytest tests/test_save_diff.py -v
