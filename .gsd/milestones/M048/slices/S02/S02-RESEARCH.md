# S02: Diff-Based Save — No Phantom Events — Research

**Researched:** 2026-04-05
**Depth:** Targeted — known patterns, well-understood code paths, one tricky normalization edge case

---

## Summary

The form save path (`save_object` in objects.py:1319) always sends ALL form field values via htmx POST, then the backend unconditionally creates an `object.patch` event recording every property as "changed" — even unchanged ones. The fix is a **backend-side diff** in `save_object()`: query current property values from the triplestore, compare to form values, and only include actually-changed properties in the `ObjectPatchParams`. If nothing changed, skip the patch entirely and return success without creating an event.

The body save path already has this pattern — `save_body()` (objects.py:509) queries existing body, returns early if unchanged. The form save needs the same treatment.

A secondary optimization: the JS `saveCurrentObject()` always POSTs the body even when unchanged. Adding a client-side `_sempkmSavedContent` check avoids the unnecessary network call (the backend already handles no-op, but skipping the fetch is cleaner).

---

## Recommendation

**Backend diff in `save_object()`** — query current values, compare, patch only changes. This is the reliable approach (source of truth), follows the existing `save_body()` pattern, and works regardless of how the form is submitted.

---

## Implementation Landscape

### Two Save Paths, Two Fixes

**Path 1: Form properties** (htmx submit → `POST /browser/objects/{iri}/save` → `save_object()`)
- **File:** `backend/app/browser/objects.py:1319`
- **Problem:** Always builds properties dict from ALL form fields, auto-injects `dcterms:modified`, then calls `handle_object_patch()` which creates delete+insert operations for EVERY property
- **Fix location:** Between line 1373 (after properties dict is built + `dcterms:modified` injection) and line 1376 (before `ObjectPatchParams` creation)
- **Fix logic:**
  1. Query current property values: `SELECT ?p ?o WHERE { GRAPH <urn:sempkm:current> { <{iri}> ?p ?o } }`
  2. Build a current values dict: `current[pred] = sorted list of values` (same structure as form properties)
  3. Filter `rdf:type` and `urn:sempkm:body` from current values (not form-managed)
  4. Compare each form property against current values
  5. Build `changed_properties` dict with only actually-different entries
  6. If `changed_properties` is empty → skip the patch entirely, return success without event
  7. If `changed_properties` is non-empty → add `dcterms:modified` to `changed_properties`, create `ObjectPatchParams` with `changed_properties` instead of `properties`
- **Key insight:** `dcterms:modified` must ONLY be included when other properties actually changed. The current code always injects it (line 1373), which means every save creates at least one "changed" property. Move the injection to AFTER the diff check.

**Path 2: Body content** (fetch POST → `POST /browser/objects/{iri}/body` → `save_body()`)
- **Backend already handles no-op** (objects.py:544-546): queries existing body, returns early if unchanged ✅
- **Frontend optimization:** `saveCurrentObject()` (workspace.js:1196) always POSTs body regardless of dirty state
- **Fix location:** workspace.js, inside the `if (editor)` block, before the `apiFetch` call
- **Fix logic:** Add `if (content === editor._sempkmSavedContent) { markClean(activeIri); return; }` before the fetch

### Critical Normalization Edge Case: DateTime Values

The form template (`_field.html:139-146`) strips timezone and seconds from `xsd:dateTime` values for `datetime-local` input:
- Triplestore stores: `2026-04-05T12:30:45.123456+00:00`
- Form displays: `2026-04-05T12:30`
- Form submits: `2026-04-05T12:30`

A naive string comparison will ALWAYS see dateTime properties as "changed" because the form value is truncated. The diff logic must normalize both sides before comparing:
- Strip timezone suffix (`+00:00`, `Z`)
- Truncate to minute precision (`YYYY-MM-DDTHH:MM`)
- Compare normalized strings

Similarly, `xsd:date` values should be straightforward (both sides are `YYYY-MM-DD`), but verify.

### Multi-Valued Properties

Properties can have multiple values (e.g., tags). The form sends them as `key[]` which `form_data.getlist(key)` collects. The diff must compare **sets of values**, not single values:
- Current: `{"predicate": ["a", "b"]}` (from SPARQL query with multiple bindings for same predicate)
- Form: `{"predicate": ["a", "b"]}` (from getlist)
- Comparison: `sorted(current_values) == sorted(form_values)` → unchanged

### Files to Modify

| File | What Changes |
|------|-------------|
| `backend/app/browser/objects.py` | `save_object()` — add SPARQL query for current values, diff logic, conditional patch |
| `frontend/static/js/workspace.js` | `saveCurrentObject()` — add `_sempkmSavedContent` check before body POST |

### Files to Add (Tests)

| File | Purpose |
|------|---------|
| `backend/tests/test_save_diff.py` | Unit tests for the diff logic: unchanged props → no event, changed props → event with only changes, dateTime normalization, multi-value comparison, empty form → no event, dcterms:modified only added when changes exist |

### Existing Patterns to Follow

| Pattern | Location | How It Applies |
|---------|----------|----------------|
| Body no-op detection | `objects.py:530-546` | Same query→compare→skip pattern for form properties |
| SPARQL current graph query | `objects.py:123-132` | Same `SELECT ?p ?o WHERE { GRAPH <current> { <iri> ?p ?o } }` query structure |
| `CURRENT_GRAPH` constant | `app.rdf.namespaces` | Already imported in objects.py line 42 |
| `TriplestoreClient` injection | `save_object()` params | Already has `client: TriplestoreClient = Depends(get_triplestore_client)` |
| `_to_rdf_value` normalization | `object_create.py:49` | Reference for how form strings become RDF values (important for understanding dateTime path) |

### Natural Task Decomposition

1. **Backend diff logic in `save_object()`** — the core fix. Query current values, normalize, compare, filter to changed-only, conditionally skip `dcterms:modified` and the entire patch. This is one self-contained change in `objects.py`.

2. **Client-side body save short-circuit** — small JS change in `saveCurrentObject()`. Independent of task 1.

3. **Unit tests** — test the diff behavior: unchanged → no event, changed → correct event, dateTime normalization, multi-value, empty form.

### How to Verify

**Acceptance test (manual or E2E):**
1. Open an object, change one property field, save → event log shows ONLY that property
2. Open an object, change nothing, save → no new event appears in event log
3. Open an object with dateTime properties, change nothing, save → no phantom dateTime event

**Unit test commands:**
```bash
cd backend && python -m pytest tests/test_save_diff.py -v
```

**Quick smoke test:**
```bash
# Check the save_object function has the diff query
grep -n "SELECT.*WHERE.*GRAPH.*current" backend/app/browser/objects.py
# Check the _sempkmSavedContent check exists in workspace.js
grep -n "_sempkmSavedContent" frontend/static/js/workspace.js | grep -v "= content"
```

---

## Risk Assessment

- **Low risk:** The backend diff approach follows the exact same pattern as `save_body()` no-op detection
- **Medium risk:** DateTime normalization — must handle all formats the triplestore returns (with/without timezone, with/without fractional seconds). Recommend a small `_normalize_for_compare(value)` helper.
- **Low risk:** Multi-value comparison is just sorted-list equality
- **Zero risk on body path:** Backend already handles no-op; the JS check is a pure optimization

---

## Skill Discovery

No external skills needed. This is a backend Python change (FastAPI, SPARQL) + minor JS change — all well-established patterns in this codebase. The `rg`, `fd` tooling specified in CLAUDE.md is sufficient for navigation.
