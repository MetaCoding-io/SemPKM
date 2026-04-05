# M048: Critical Bug Fixes — Research

**Researched:** 2026-04-05
**Status:** Ready for planning

---

## 1. Executive Summary

M048 addresses 7 distinct bugs that degrade core functionality: missing single-object delete UI, phantom save events, broken table/cards views, missing creation timestamps, potential model loading issues, and Docker volume permission problems. The existing codebase already has bulk delete (backend + explorer multi-select UI), server-side body diff detection, and a mature command/event pipeline — so most fixes are surgical rather than architectural.

**Key finding:** The backend body save endpoint (`save_body` in objects.py:509) already has no-op detection — it queries the current body and skips if unchanged. The phantom body.set issue is exclusively in the **form save path** (`save_object` in objects.py:1319), which always sends ALL form fields regardless of whether they changed. And the `saveCurrentObject()` JS function always sends the body content even when the editor's `_sempkmSavedContent` matches — bypassing the server's no-op check via a race with the form submission.

---

## 2. Bug-by-Bug Analysis

### Bug #29: Object Delete — Missing Single-Object UI

**Current state:**
- Backend: `bulk_delete_objects()` endpoint exists at `POST /browser/objects/delete` (objects.py:973). Accepts `{"iris": [...]}`, queries all triples where IRI is subject, creates Operation with materialize_deletes, commits via EventStore. Works correctly.
- Frontend: Only accessible via multi-select in explorer (`bulkDeleteSelected()` at workspace.js:1410). No single-object delete button on the object header bar, no command palette entry, no explorer hover action for individual objects.
- The object tab toolbar (object_tab.html) has star, properties toggle, mode toggle, and save buttons — but no delete button.
- `showConfirmDialog()` utility exists at workspace.js:3334 for reuse.

**What's needed:**
1. Delete button on object toolbar (object_tab.html) — can reuse the existing bulk endpoint with a single-IRI array.
2. Command palette entry ("Delete Object") for the active tab's IRI.
3. Explorer hover action (trash icon on tree leaf hover) — needs CSS + click handler.
4. After delete: close the tab, refresh nav tree, show toast.

**Edge deletion gap:** The current `bulk_delete_objects` only deletes triples where the object is the **subject**. Inbound edges (where the object is the **object** of a triple from another subject) are NOT cleaned up. This leaves dangling references. The fix should query `?s ?p <deleted_iri>` as well and include those in materialize_deletes.

**Risk:** Low — straightforward UI wiring + minor backend gap.

### Bug #30: Phantom Save Events (Form Properties)

**Current state:**
- `saveCurrentObject()` (workspace.js:1177) does TWO things on Ctrl+S:
  1. Triggers htmx form submission (`htmx.trigger(form, 'submit')`)
  2. POSTs body content via fetch to `/browser/objects/{iri}/body`
- The form submission always sends ALL form fields to `save_object()` (objects.py:1319).
- `save_object()` builds a properties dict from ALL form data, auto-adds `dcterms:modified`, then calls `handle_object_patch()` which creates delete+insert operations for EVERY property — even unchanged ones.
- The body save via `saveCurrentObject()` always sends content regardless of dirty state — it doesn't check `editor._sempkmSavedContent`. However, the backend `save_body()` already has no-op detection (queries existing body, returns early if unchanged). So body phantom events only happen on first save of a new object where body is empty.

**The real issue:** The **form path** has no diffing at all. Every Ctrl+S creates an event with all properties as "changed". This pollutes the event log with phantom `object.patch` events showing properties that didn't actually change, plus false "(new)" markers on the frontend event diff display.

**Fix approach:**
- Option A (backend diff): In `save_object()`, query current property values from the triplestore before building the patch. Compare new values vs current values. Only include actually-changed properties in the `ObjectPatchParams`. If nothing changed, skip the patch entirely.
- Option B (frontend diff): Track original form values on page load. On save, compare current form values to originals and only send changed fields. This avoids a round-trip to the triplestore but requires careful JS plumbing.
- **Recommendation:** Option A (backend diff) is more reliable — it's the source of truth and works regardless of how forms are submitted. The server already does this for body saves.
- Also: the `saveCurrentObject()` JS should check `editor._sempkmSavedContent === content` before sending the body, for a quick client-side short-circuit.

**Risk:** Medium — querying current values adds a SPARQL call per save, but it's a targeted query (`SELECT ?p ?o WHERE { GRAPH <current> { <iri> ?p ?o } }`) which is cheap.

### Bug #36: Table View "No objects found"

**Current state:**
- Generic table view endpoint: `GET /browser/views/generic/table` (views/router.py)
- Calls `build_dynamic_query()` then `execute_table_query()` from ViewSpecService.
- `build_dynamic_query()` calls `_build_default_select()` when no type is specified (or SHACL shapes are sparse).
- The default query uses `OPTIONAL { ?s dcterms:created ?created }` etc.
- `execute_table_query()` runs the query through `scope_to_current_graph()`.
- Template `table_view.html` renders rows if `rows` is truthy, else shows "No objects found."

**Diagnosis needed:** The bug is likely in the SPARQL query or the `_extract_where_body()` helper. The two-phase approach (get distinct subjects, then fetch properties) could fail if the WHERE body extraction regex doesn't handle the default query format. This needs runtime debugging — run the generated SPARQL directly against the triplestore to see if it returns results.

**Possible causes:**
1. `_extract_where_body()` fails to parse the generated query → returns None → empty results
2. `scope_to_current_graph()` adds FROM clauses incorrectly
3. Query returns subjects but `_extract_where_body` strips something critical
4. Hidden types filter excludes too much (unlikely — `get_hidden_types()` only reads manifest `browserVisible: false`)

**Risk:** Medium — needs live debugging. The fix could be a one-line regex fix or a query structure change.

### Bug #41: Cards View Broken Rendering

**Current state:**
- Same pipeline as table view — `build_dynamic_query()` → `execute_cards_query()`.
- Cards template (cards_view.html) renders correctly if `cards` list is populated.
- The `execute_cards_query()` method uses the same two-phase approach as table.

**Likely same root cause as #36** — if the SPARQL query generation or extraction fails for table, it fails for cards too. Fix one, fix both.

**Risk:** Low (coupled with #36).

### Bug #63: Missing dcterms:created Timestamp

**Current state:**
- `handle_object_create()` (object_create.py) mints an IRI, adds `rdf:type` triple, and property triples from form data. It does NOT auto-inject `dcterms:created`.
- The form submission on create (`create_object()` in objects.py:1201) passes form data properties through to `ObjectCreateParams`. There's no auto-injection of `dcterms:created` there either.
- The `save_object()` path (edit saves) auto-injects `dcterms:modified` (line ~1375), but `create_object()` does neither `dcterms:created` nor `dcterms:modified`.

**Fix:** Add `dcterms:created` injection in `handle_object_create()`:
```python
from rdflib.namespace import XSD
from datetime import datetime, timezone
DCTERMS_CREATED = URIRef("http://purl.org/dc/terms/created")
DCTERMS_MODIFIED = URIRef("http://purl.org/dc/terms/modified")
now = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)
triples.append((subject, DCTERMS_CREATED, now))
triples.append((subject, DCTERMS_MODIFIED, now))
```

**Risk:** Very low — two lines of code. Purely additive.

### Bug #4a: Model Loading (Business Planning — 33 Shapes)

**Current state:**
- The `business-planning` model has 33 NodeShapes in a 72KB JSON-LD file.
- `load_archive()` parses JSON-LD via rdflib → `Graph.parse(format="json-ld")`.
- `_build_insert_data_sparql()` serializes ALL triples into a single SPARQL INSERT DATA statement.
- For 33 shapes, this could be a very large SPARQL statement (potentially >1MB of SPARQL text).
- RDF4J has default request size limits — a single INSERT DATA that's too large could be silently truncated or fail.

**Diagnosis approach:** The context notes suggest trying uninstall/reinstall first. If reinstall on current code loads all 33 shapes, it was stale data. If not, we need to:
1. Check the generated SPARQL size
2. Check RDF4J transaction_update for HTTP errors
3. Potentially chunk the INSERT DATA into batches

**Risk:** Medium — could be a non-issue (stale data) or could require chunked inserts for large models.

### Bugs #1/#2: Docker Volume Permissions

**Current state:**
- Backend Dockerfile creates user `sempkm` (uid 1000), `chown`s `/app/data`, then `USER sempkm`.
- docker-compose.yml mounts `sempkm_data` named volume at `/app/data`.
- Problem: Docker named volumes are initialized with the image's directory content + permissions on first create. But if the volume already exists (e.g., from a previous run with different uid), the permissions may not match.
- There's no entrypoint script in the backend Dockerfile — it goes straight to `CMD ["uvicorn", ...]`.
- Frontend Dockerfile has an entrypoint script but backend does not.

**Fix:** Add a `docker-entrypoint.sh` for the backend that:
1. Checks/fixes ownership of `/app/data` (only if running as root)
2. Execs the CMD as the sempkm user
3. OR: use `gosu` / `su-exec` to drop privileges after fixing permissions

**Alternative:** Since the container runs as `sempkm` (USER directive), it can't `chown`. The fix is either:
- Remove `USER sempkm` and use entrypoint to fix perms + drop privileges
- Or ensure the volume is always created with correct permissions (use `user:` in docker-compose)

**Risk:** Low-medium — standard Docker pattern, but needs testing on fresh + existing volumes.

---

## 3. Existing Patterns to Reuse

| Pattern | Location | Reuse For |
|---------|----------|-----------|
| EventStore Operation model | `events/store.py` | Delete operation (already used by bulk_delete) |
| `showConfirmDialog()` | workspace.js:3334 | Single-object delete confirmation |
| `bulkDeleteSelected()` flow | workspace.js:1410 | Reuse `/browser/objects/delete` endpoint for single delete |
| `save_body()` no-op detection | objects.py:530-533 | Pattern for form property diffing in `save_object()` |
| `handle_object_patch()` | object_patch.py | Already handles variable-based delete + insert |
| `refreshNavTree()` | workspace.js:1457 | Post-delete UI refresh |
| `showToast()` | workspace.js | User feedback for all actions |
| Command palette registration | workspace.js ~1560-1700 | "Delete Object" palette entry |
| `_rdf_term_to_sparql()` | services/models.py:253 | N/A — existing serialization |
| Frontend entrypoint script | frontend/docker-entrypoint.sh | Pattern for backend entrypoint |

---

## 4. Boundary Contracts

### Delete Flow
- Input: Single object IRI (from tab, explorer, or command palette)
- Backend: `POST /browser/objects/delete` with `{"iris": [iri]}` — already exists
- Side effects: Close tab, refresh explorer tree, invalidate label cache
- Event: `object.delete` operation recorded in EventStore
- Edge cleanup: Also delete triples where `?s ?p <deleted_iri>` (inbound edges)

### Save Diffing
- Input: Form data from htmx submission
- Backend must query current state, diff properties, only patch changes
- Body save: JS should check `_sempkmSavedContent` before POSTing
- Output: Event log should show ONLY actually-changed properties

### View Rendering
- Input: `/browser/views/generic/{table|card}` endpoint
- SPARQL: `_build_default_select()` → `scope_to_current_graph()` → execute
- Output: rows/cards list (possibly empty but should match actual data)
- Contract: If objects exist in `urn:sempkm:current`, views MUST show them

### dcterms:created
- Injected server-side in `handle_object_create()` — not client-dependent
- Format: ISO 8601 datetime with xsd:dateTime datatype
- Also inject `dcterms:modified` at creation time

### Docker
- Backend entrypoint: fix `/app/data` permissions, then exec CMD
- Must be idempotent (safe on every container start)
- Must work on fresh volumes AND existing volumes with wrong ownership

---

## 5. Risk Assessment & Slice Ordering

### Prove First: Table/Cards View Fix (#36/#41)
These are the most uncertain — we don't know the root cause yet. Could be a one-line regex fix or could require restructuring the query pipeline. Debug this first because it's the highest-risk unknown.

### Then: dcterms:created (#63) + Save Diffing (#30)
These are well-understood fixes with clear code paths. dcterms:created is trivial (2 lines). Save diffing requires a SPARQL query + comparison logic, but the pattern already exists in `save_body()`.

### Then: Delete UI (#29)
Backend already exists. UI wiring is straightforward. Edge cleanup is a small backend enhancement.

### Then: Model Loading Diagnosis (#4a)
Start with uninstall/reinstall diagnostic. If it works, no code change needed. If not, investigate chunked inserts.

### Last: Docker Permissions (#1/#2)
Well-understood Docker pattern. Lowest user-facing impact (only affects fresh deploys).

---

## 6. Technical Constraints

1. **Event sourcing is mandatory** — every write must produce an immutable event. Delete creates an event that records what was deleted.
2. **htmx form submission** — the form save flow goes through htmx, so diffing must happen either in JS (intercept before submit) or server-side (query + compare). Server-side is more reliable.
3. **SPARQL scoping** — all user-facing queries must go through `scope_to_current_graph()`. This is the standard pattern and should not be bypassed.
4. **Template rendering** — views use Jinja2 templates rendered server-side. No client-side rendering to debug.
5. **Docker security** — `security_opt: no-new-privileges` and `cap_drop: ALL` on the API container constrain entrypoint options.

---

## 7. Open Questions

1. **Edge cascade on delete:** Should `bulk_delete_objects` also query `SELECT ?s ?p WHERE { GRAPH <current> { ?s ?p <deleted_iri> } }` and delete those inbound edges? **Recommendation: Yes** — otherwise dangling references persist.
2. **Save diffing location:** Backend (reliable, adds SPARQL query) vs frontend (faster, no round-trip). **Recommendation: Backend** — follows existing save_body pattern and is the source of truth.
3. **Model loading:** Is this a stale data issue or a pipeline bug? **Recommendation: Diagnose first** with uninstall/reinstall before writing code.
4. **Docker entrypoint approach:** gosu/su-exec vs removing USER directive? **Recommendation: Entrypoint with gosu** — maintains non-root runtime but allows startup permission fixes.

---

## 8. Candidate Requirements

These findings should be surfaced as potential requirements but NOT auto-bound:

- **CR-01:** Object deletion should cascade to inbound edges (prevents dangling references in SPARQL queries and views)
- **CR-02:** Save operation should produce no event when no properties actually changed (event log integrity)
- **CR-03:** Every object.create should auto-set dcterms:created and dcterms:modified (data completeness)
- **CR-04:** Docker containers should self-heal volume permissions on startup (operational reliability)

---

## 9. Skill Discovery

The core technologies are well-established in this codebase (Python/FastAPI, htmx, rdflib, SPARQL, Docker). No external skill packages are needed — the bugs are all in existing application code.

---

## 10. Files Likely Touched

| Bug | Files |
|-----|-------|
| #29 Delete UI | `backend/app/browser/objects.py` (edge cleanup), `backend/app/templates/browser/object_tab.html` (button), `frontend/static/js/workspace.js` (handlers, palette) |
| #30 Save Diff | `backend/app/browser/objects.py` (`save_object`), `frontend/static/js/workspace.js` (`saveCurrentObject` body check) |
| #36/#41 Views | `backend/app/views/service.py` (query building/execution), possibly `backend/app/sparql/client.py` |
| #63 Created | `backend/app/commands/handlers/object_create.py` |
| #4a Models | `backend/app/services/models.py` (potentially chunk inserts) |
| #1/#2 Docker | `backend/Dockerfile`, new `backend/docker-entrypoint.sh`, `docker-compose.yml` |
