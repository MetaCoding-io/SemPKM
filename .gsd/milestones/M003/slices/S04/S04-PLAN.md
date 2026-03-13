# S04: Tag System Fix & Tag Explorer

**Goal:** Comma-separated tags are split into individual RDF triples at save time and in seed data. Tags render as #-prefixed pills in object views for both `bpkm:tags` and `schema:keywords`. A "By Tag" explorer mode groups objects by tag with counts.
**Demo:** User saves an object with tags — each tag becomes a separate triple. Opening the object shows styled pills. Switching explorer to "By Tag" shows tag folders with counts; expanding a tag lists its objects.

## Must-Haves

- Seed data in `basic-pkm.jsonld` uses JSON-LD arrays for `bpkm:tags` (individual triples on install)
- Ontology comment updated from "Comma-separated" to reflect individual-triple storage
- `save_object` splits comma-separated values for tag properties (`'tags' in key` or `'keywords' in key`) into individual triples
- Management endpoint or startup migration splits existing comma-separated `bpkm:tags` triples (idempotent)
- Tag pill rendering in `object_read.html` matches both `'tags' in prop.path` and `'keywords' in prop.path`
- Tag pill edit styling in `_field.html` matches both tag detection patterns
- `_handle_by_tag` in workspace.py replaced with real implementation querying both `bpkm:tags` and `schema:keywords`
- Tag folders show `COUNT(DISTINCT ?iri)` to avoid double-counting objects with both tag properties
- New `/browser/explorer/tag-children?tag={value}` endpoint returns objects for a given tag
- Tag tree uses same leaf rendering pattern as mount_tree_objects.html for click-through to object tabs

## Proof Level

- This slice proves: integration
- Real runtime required: yes (SPARQL queries, triplestore data, htmx rendering)
- Human/UAT required: no (automated tests cover tag splitting, pill rendering detection, explorer mode)

## Verification

- `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — tag-splitting logic unit tests
- `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — by-tag handler + tag-children query tests
- `cd e2e && npx playwright test tests/20-tags/` — E2E test for tag pill display and by-tag explorer mode
- Manual: `docker compose up -d && docker compose exec backend python -c "from app.commands.handlers.object_patch import _split_tag_values; print(_split_tag_values('a,b,c'))"` — smoke test tag splitting function

## Observability / Diagnostics

- Runtime signals: `logger.debug("Tag split: %s -> %s", original, split_values)` in save path for tag splitting; `logger.debug("By-tag query: %d folders, %d objects", ...)` in explorer handler
- Inspection surfaces: `/browser/explorer/tree?mode=by-tag` returns tag folder tree (htmx); `/browser/explorer/tag-children?tag=X` returns objects for tag X
- Failure visibility: HTTP 400 for bad tag-children params; empty tree with "No tags found" message on no results; SPARQL query errors logged with full query text
- Redaction constraints: none (no secrets in tag data)

## Integration Closure

- Upstream surfaces consumed: `EXPLORER_MODES` registry from S01, `_bindings_to_objects` helper, `mount_tree.html` / `mount_tree_objects.html` template patterns, VFS `query_tag_folders`/`query_objects_by_tag` SPARQL patterns (adapted, not reused directly), `_LABEL_OPTIONALS` / `_LABEL_COALESCE` from `strategies.py`
- New wiring introduced in this slice: tag-splitting middleware in `save_object`, `_handle_by_tag` real implementation in workspace.py, `tag_children` endpoint in workspace.py, `tag_tree.html` + `tag_tree_objects.html` templates, tag migration endpoint
- What remains before the milestone is truly usable end-to-end: S05 (favorites), S06 (comments), S07 (ontology viewer + gist), S08 (class creation), S09 (admin charts), S10 (E2E coverage gaps)

## Tasks

- [x] **T01: Fix seed data, ontology comment, and add tag-splitting unit tests** `est:45m`
  - Why: Foundation for all tag work — seed data must produce individual triples, and splitting logic needs tests before wiring into the save path.
  - Files: `models/basic-pkm/seed/basic-pkm.jsonld`, `models/basic-pkm/ontology/basic-pkm.jsonld`, `backend/tests/test_tag_splitting.py`
  - Do: Convert all 11 `bpkm:tags` values from comma-separated strings to JSON-LD arrays. Update ontology comment to "Tags for categorization (individual values)". Create `test_tag_splitting.py` with tests for the splitting function (splits on commas, trims whitespace, skips empty, no-op for single value, handles `schema:keywords` path detection).
  - Verify: `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — tests initially fail (function not yet implemented); seed data validated with `python -c "import json; d=json.load(open('models/basic-pkm/seed/basic-pkm.jsonld')); [print(g['bpkm:tags']) for g in d['@graph'] if 'bpkm:tags' in g]"` shows arrays.
  - Done when: All 11 seed entries are JSON-LD arrays, ontology comment updated, test file exists with 6+ tests that import from the correct module.

- [x] **T02: Implement tag-splitting middleware in save path and migration endpoint** `est:1h`
  - Why: Core TAG-01 requirement — comma-separated values must split on save, and existing data needs a one-time migration.
  - Files: `backend/app/browser/objects.py`, `backend/app/browser/workspace.py`, `backend/tests/test_tag_splitting.py`
  - Do: In `save_object()`, after building the properties dict, iterate keys and split any value containing commas when the key IRI contains `tags` or `keywords` — replace `["a,b,c"]` with `["a","b","c"]` (strip whitespace). Add a `POST /browser/admin/migrate-tags` endpoint that runs a SPARQL UPDATE: find all `bpkm:tags` literals containing commas, delete them, insert individual triples. Make it idempotent (`FILTER(CONTAINS(STR(?val), ","))`). Ensure the existing tests from T01 now pass.
  - Verify: `cd backend && .venv/bin/pytest tests/test_tag_splitting.py -v` — all tests pass.
  - Done when: Tag-splitting function exists and is called in save_object; migration endpoint defined; all unit tests pass.

- [x] **T03: Extend tag pill rendering to schema:keywords and create by-tag explorer backend** `est:1h`
  - Why: TAG-02 (pills for both tag properties) and TAG-03 backend (by-tag explorer handler + tag-children endpoint).
  - Files: `backend/app/templates/browser/object_read.html`, `backend/app/templates/forms/_field.html`, `backend/app/browser/workspace.py`, `backend/app/templates/browser/tag_tree.html`, `backend/app/templates/browser/tag_tree_objects.html`, `backend/tests/test_tag_explorer.py`
  - Do: (1) Extend tag pill detection in `object_read.html` from `'tags' in prop.path` to `'tags' in prop.path or 'keywords' in prop.path`. Same for `_field.html`. (2) Replace `_handle_by_tag` placeholder with real SPARQL: query `DISTINCT ?tagValue (COUNT(DISTINCT ?iri) AS ?count)` across both `bpkm:tags` and `schema:keywords` using `UNION`, ordered alphabetically. (3) Create `tag_tree.html` template (folder nodes with `hx-get` for lazy tag-children expansion, showing tag name + count badge). (4) Add `tag_children` endpoint at `GET /browser/explorer/tag-children?tag={value}` — SPARQL query objects with that tag value across both properties, render via `tag_tree_objects.html` (same leaf pattern as mount_tree_objects.html). (5) Write `test_tag_explorer.py` with unit tests for SPARQL query construction and handler registry.
  - Verify: `cd backend && .venv/bin/pytest tests/test_tag_explorer.py -v` — all tests pass.
  - Done when: By-tag mode returns real tag folders with counts; tag-children endpoint returns objects; pill rendering works for both tag properties; unit tests pass.

- [x] **T04: E2E test for tag pills and by-tag explorer mode** `est:45m`
  - Why: Verifies the full integration — tags render as pills in the UI, by-tag explorer shows tag folders, expanding shows objects.
  - Files: `e2e/tests/20-tags/tag-explorer.spec.ts`, `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`
  - Do: (1) Create `e2e/tests/20-tags/` directory and `tag-explorer.spec.ts`. (2) Test: navigate to workspace, open an object with tags (basic-pkm seed data), verify `.tag-pill` elements visible with `#` prefix. (3) Test: switch explorer to "By Tag" mode, verify tag folder nodes appear with count badges. (4) Test: expand a tag folder, verify object leaves appear and are clickable. (5) Update the existing explorer-mode-switching spec to expect real tag tree content instead of placeholder when switching to by-tag. (6) Combine tests to stay within auth rate limit (max 2 authenticated sessions).
  - Verify: `cd e2e && npx playwright test tests/20-tags/ --reporter=list` — all tests pass against running Docker stack.
  - Done when: E2E tests pass — tag pills visible, by-tag explorer shows real folders, tag expansion shows objects.

## Files Likely Touched

- `models/basic-pkm/seed/basic-pkm.jsonld`
- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `backend/app/browser/objects.py`
- `backend/app/browser/workspace.py`
- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/forms/_field.html`
- `backend/app/templates/browser/tag_tree.html`
- `backend/app/templates/browser/tag_tree_objects.html`
- `backend/tests/test_tag_splitting.py`
- `backend/tests/test_tag_explorer.py`
- `e2e/tests/20-tags/tag-explorer.spec.ts`
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`
- `frontend/static/css/workspace.css` (minor — tag count badge styling if needed)
