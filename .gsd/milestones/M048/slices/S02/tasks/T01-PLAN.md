---
estimated_steps: 32
estimated_files: 2
skills_used: []
---

# T01: Add diff-based filtering to save_object() and body save short-circuit

## Why
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

## Inputs

- ``backend/app/browser/objects.py` — save_object() endpoint (line 1319), save_body() no-op pattern (line 530-546)`
- ``frontend/static/js/workspace.js` — saveCurrentObject() function (line 1177)`
- ``backend/app/templates/forms/_field.html` — datetime truncation logic (line 139-143)`
- ``backend/app/commands/handlers/object_patch.py` — handle_object_patch() and ObjectPatchParams`

## Expected Output

- ``backend/app/browser/objects.py` — save_object() with diff-based filtering, _normalize_value_for_compare() helper`
- ``frontend/static/js/workspace.js` — saveCurrentObject() with _sempkmSavedContent short-circuit before body POST`

## Verification

rg -n '_normalize_value_for_compare' backend/app/browser/objects.py && rg -n 'changed_properties' backend/app/browser/objects.py && rg -n '_sempkmSavedContent' frontend/static/js/workspace.js | grep -v '= content' | grep -c '_sempkmSavedContent'
