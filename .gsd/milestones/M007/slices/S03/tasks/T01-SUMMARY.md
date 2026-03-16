---
id: T01
parent: S03
milestone: M007
provides:
  - filename_template field on MountDefinition with SPARQL read/write in sync + async paths
  - template variable expansion ({title}, {date}, {type}, {id}) in _build_file_map_from_bindings()
  - dcterms:created OPTIONAL in all object-listing SPARQL query builders
key_files:
  - backend/app/vfs/mount_collections.py
  - backend/app/vfs/mount_router.py
  - backend/app/vfs/strategies.py
  - backend/tests/test_vfs_path_contract.py
key_decisions:
  - Unknown template variables (e.g. {bogus}) pass through as literal text and get slugified rather than raising errors
  - {id} uses first 8 chars of SHA-256 hash of the IRI (deterministic, short)
  - dcterms:created OPTIONAL added to all 6 object-listing query builders in strategies.py for {date} support
patterns_established:
  - filename_template parameter threading from mount definition → collection classes → _build_file_map_from_bindings()
  - type_labels dict parameter for overriding type IRI → label resolution in templates
observability_surfaces:
  - DEBUG log in _build_file_map_from_bindings() when filename_template expanded (template string + resulting slug)
  - MountDefinition.to_dict() includes filename_template for API response visibility
duration: 25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Filename templates — backend + tests

**Added `filename_template` field with `{title}`, `{date}`, `{type}`, `{id}` variable expansion to VFS file map builder, with full SPARQL persistence in sync + async paths and 12 new unit tests.**

## What Happened

Step 1 (data model) was already complete from prior work — `FILENAME_TEMPLATE` constant, `filename_template` field on `MountDefinition`, SPARQL read/write in sync service, and `to_dict()` serialization were all present.

Step 2: Added `FILENAME_TEMPLATE` import to `mount_router.py`. Added `filenameTemplate` OPTIONAL to all async SPARQL queries (`_get_mount_by_id_async`, `list_mounts`). Added `filename_template` triple to `create_mount` and `update_mount` INSERT DATA. Added `filename_template` to MountDefinition constructors in all async paths.

Step 3: Extended `_build_file_map_from_bindings()` signature with `filename_template: str | None` and `type_labels: dict[str, str] | None`. Added template expansion logic before `_slugify()` — replaces `{title}` with label, `{id}` with 8-char SHA-256 prefix, `{date}` with first 10 chars of dcterms:created (or "undated"), `{type}` with type label (from type_labels dict, or IRI local name extraction). Added DEBUG log on expansion.

Step 4: Threaded `filename_template=self._mount.filename_template` through `MountRootCollection._get_flat_file_map()` and `StrategyFolderCollection._build_file_map()`. Added `OPTIONAL { ?iri <dcterms:created> ?created }` to all 6 object-listing query builders in `strategies.py`.

Step 5: Wrote 12 new tests in `TestFilenameTemplates` class covering all 4 variables, missing date fallback, missing type fallback, no-template backward compat, dedup with templates, bogus variable passthrough, hash fragment type IRIs, and colon-separated type IRIs.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_vfs_path_contract.py -v` — **38 passed** (26 existing + 12 new)
- `cd backend && .venv/bin/python -m pytest tests/test_vfs_scope.py -v` — **21 passed** (no regressions)

Slice-level verification (partial — T01 is first of 4 tasks):
- ✅ New filename template tests in `test_vfs_path_contract.py`: all 4 variables, missing variables, backward compat, dedup
- ✅ Diagnostic: `{bogus}` passes through as literal text (test_bogus_variable_passthrough)
- ✅ Existing single-strategy mounts work unchanged (all 26 existing tests pass)
- ⏳ Chain tests, provider dispatch tests, CRUD round-trip, browser verification — future tasks

## Diagnostics

- **Template expansion logging:** When `filename_template` is set, DEBUG log emitted with template string, IRI, and resulting slug. Grep for `filename_template expanded` in logs.
- **API inspection:** `GET /api/vfs/mounts` response includes `filename_template` field per mount.
- **Failure shape:** Unknown variables like `{bogus}` are left as-is, curly braces become hyphens after slugification. No errors raised.

## Deviations

- Step 1 was already implemented in mount_service.py from prior milestone work — skipped re-implementation.
- Added `?created` to `query_objects_by_type` SELECT even though it doesn't include `?typeIri` — the binding key `created` is available for template expansion regardless.
- Added 12 tests instead of the planned 7 — extra coverage for type_labels dict, missing type fallback, hash fragment IRIs, and colon-separated IRIs.

## Known Issues

None.

## Files Created/Modified

- `backend/app/vfs/mount_collections.py` — Extended `_build_file_map_from_bindings()` with template expansion; threaded `filename_template` through collection classes
- `backend/app/vfs/mount_router.py` — Added `FILENAME_TEMPLATE` import; added `filenameTemplate` to async SPARQL queries and CRUD; added `filename_template` triple to create/update
- `backend/app/vfs/strategies.py` — Added `OPTIONAL { ?iri <dcterms:created> ?created }` to all 6 object-listing query builders
- `backend/tests/test_vfs_path_contract.py` — Added `TestFilenameTemplates` class with 12 tests
