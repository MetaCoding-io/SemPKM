---
estimated_steps: 7
estimated_files: 4
---

# T04: Type multi-select UI in mount form

**Slice:** S02 — VFS Quick Wins — Type Filter, Query IRI, Preview
**Milestone:** M007

## Description

Add a type multi-select UI to the VFS mount creation/edit form so users can filter mounts by type without writing SPARQL. The type list is populated from the same data source as generic view type pills. The selected type IRIs are sent as `type_filter` in the mount API request.

This also completes the API side: `mount_router.py` create/update/list endpoints need to handle `type_filter` as a multi-valued RDF predicate.

## Steps

1. **Add `type_filter` to Pydantic models in `mount_router.py`:**
   - Add `type_filter: list[str] | None = None` to `MountCreateRequest`, `MountUpdateRequest`, `MountPreviewRequest`

2. **Update mount create endpoint in `mount_router.py`:**
   - In the INSERT DATA block, for each IRI in `body.type_filter`, add a triple: `<{mount_iri}> <{TYPE_FILTER}> <{type_iri}>`
   - Import `TYPE_FILTER` from `mount_service`
   - Pass `type_filter` to `MountDefinition()` constructor in the return

3. **Update mount update endpoint in `mount_router.py`:**
   - Delete existing `sempkm:typeFilter` triples for the mount before inserting new ones
   - Insert new type_filter triples
   - Handle the case where type_filter is cleared (empty list → just delete, no insert)

4. **Update mount list/get queries in `mount_router.py`:**
   - The async SPARQL queries for mounts need to collect multi-valued `type_filter`. Use a sub-select with `GROUP_CONCAT`:
     ```sparql
     OPTIONAL {
       SELECT ?mount (GROUP_CONCAT(?tf; separator="|") AS ?typeFilters)
       WHERE { ?mount <{TYPE_FILTER}> ?tf }
       GROUP BY ?mount
     }
     ```
   - In binding parsing, split `typeFilters` on `|` to reconstruct the list
   - Same pattern for `_get_mount_by_id_async()`

5. **Also update sync queries in `mount_service.py`:**
   - Same GROUP_CONCAT pattern for `list_mounts()`, `get_mount_by_id()`, `get_mount_by_prefix()`
   - Update `_binding_to_mount()` or equivalent helper to parse `typeFilters`
   - Update `create_mount()` INSERT DATA to include type_filter triples
   - Update `update_mount()` to handle type_filter updates

6. **Add type multi-select UI in `_vfs_settings.html`:**
   - Add a new form row after scope, with label "Type Filter (optional)"
   - Use a container div with checkboxes, each checkbox value is a type IRI
   - Initially empty; populated by JS on form load
   - Style: use existing `.mount-form-row` and `.mount-form-label` classes

7. **Update JS in `workspace.js`:**
   - In `initMountForm()`: after loading properties and scope, fetch available types via `GET /browser/views/type-pills` (or better: add a lightweight `GET /api/vfs/mounts/types` endpoint that returns `[{iri, label}]`). Actually, the types are already available from `ShapesService.get_types()` which powers the generic view pills — reuse the same endpoint. Populate checkboxes in the type filter container.
   - In `mountSubmitForm()`: collect checked type IRIs into `type_filter: [...]` in the POST body
   - In `populateEditForm()`: pre-check checkboxes matching `mount.type_filter` IRIs
   - In `mountPreview()`: include `type_filter` in preview POST body
   - In `renderMountList()`: optionally show type filter summary in mount card

## Must-Haves

- [ ] Mount form shows type checkboxes populated from available types
- [ ] Selected types sent as `type_filter` array in create/update API calls
- [ ] Mount API stores multi-valued `sempkm:typeFilter` triples
- [ ] Mount list/get responses include `type_filter` array
- [ ] Edit form pre-selects previously saved types
- [ ] Preview endpoint accepts and applies type_filter

## Verification

- Browser: Settings → VFS → create mount → type checkboxes visible and selectable
- Browser: save mount with type filter → reload → edit → types pre-selected
- Browser: preview with type filter → shows filtered counts
- `cd backend && python -m pytest tests/ -v -k vfs` — existing tests pass

## Inputs

- `backend/app/vfs/mount_service.py` — `MountDefinition` with `type_filter` field and `TYPE_FILTER` constant from T01
- `backend/app/vfs/mount_router.py` — async endpoints with `scope_query` from T02
- `frontend/static/js/workspace.js` — mount form JS functions
- `backend/app/templates/browser/_vfs_settings.html` — mount form template
- Types endpoint: `GET /browser/views/type-pills` exists from M007/S01 — returns available type IRIs and labels

## Expected Output

- `backend/app/vfs/mount_router.py` — full type_filter support in create/update/list/preview
- `backend/app/vfs/mount_service.py` — full type_filter support in sync CRUD
- `backend/app/templates/browser/_vfs_settings.html` — type filter checkbox group
- `frontend/static/js/workspace.js` — type filter collection, population, and edit pre-selection

## Observability Impact

- **API responses:** `GET /api/vfs/mounts` and `GET /api/vfs/mounts/{id}` now include `type_filter: string[] | null` in JSON responses — inspectable via browser DevTools or curl
- **RDF verification:** `SELECT ?mount ?tf FROM <urn:sempkm:mounts> WHERE { ?mount <urn:sempkm:typeFilter> ?tf }` — shows stored type_filter triples per mount
- **Frontend state:** `document.querySelectorAll('input[name="mount-type-filter-cb"]:checked')` shows currently selected types in the mount form
- **Mount list cards:** Type filter count shown inline in mount meta line (e.g. "· 2 types") — visible without inspecting API
- **Failure visibility:** No new failure modes — empty/null type_filter is a no-op; non-existent type IRIs just produce zero SPARQL matches
