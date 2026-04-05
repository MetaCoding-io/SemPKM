---
id: M048
title: "Critical Bug Fixes"
status: complete
completed_at: 2026-04-05T19:52:47.627Z
key_decisions:
  - D384: bulk_delete_objects cascades to inbound edges — prevents dangling references after object deletion
  - D385: Removed separate lucene_index Docker volume — lucene data lives inside rdf4j_data volume to fix fresh-volume permission mismatch
  - D386: Added _wait_for_repo_ready() polling with retry backoff after RDF4J repository creation to handle initialization race
key_files:
  - backend/app/views/service.py — inject_prefixes() on all reconstructed SPARQL queries
  - backend/app/commands/handlers/object_create.py — auto-inject dcterms:created/modified timestamps
  - backend/app/browser/objects.py — diff-based save + inbound edge cleanup in delete
  - frontend/static/js/workspace.js — deleteObject() function + _sempkmSavedContent guard
  - backend/docker-entrypoint.sh — new entrypoint ensuring data directories exist
  - backend/app/triplestore/setup.py — _wait_for_repo_ready() polling
  - docker-compose.yml — removed separate lucene_index volume
  - backend/tests/test_view_prefix_fix.py — 6 tests for prefix injection
  - backend/tests/test_object_create_timestamps.py — 10 tests for timestamps
  - backend/tests/test_save_diff.py — 22 tests for diff-based save
  - backend/tests/test_object_delete_inbound.py — 7 tests for inbound edge cleanup
  - scripts/verify-docker-fresh.sh — reproducible fresh-volume deploy verification
lessons_learned:
  - SPARQL query reconstruction (extracting WHERE body and rebuilding) drops PREFIX declarations — always apply inject_prefixes() after reconstruction
  - HTML datetime-local inputs truncate to minute precision — datetime comparison between form and triplestore values needs normalization (strip tz, truncate to 16 chars)
  - Docker named volumes are created with root ownership — child volumes for non-root services (like RDF4J's tomcat user) should be subdirectories of a parent volume owned by the correct user
  - RDF4J repository creation is async — LuceneSail + NativeStore need initialization time before SPARQL operations succeed; poll /size endpoint for readiness
---

# M048: Critical Bug Fixes

**Fixed five showstopper bugs: broken view rendering (missing SPARQL prefixes), phantom save events, missing delete UI with dangling reference cleanup, absent creation timestamps, and Docker fresh-volume deploy failures.**

## What Happened

M048 addressed the critical bugs blocking core CRUD operations and deployment. The milestone delivered four slices across 8 tasks with 45 new unit tests.

**S01 — Table & Cards Views + Creation Timestamps:** Root-caused the zero-results bug to missing PREFIX declarations in reconstructed SPARQL queries. The `execute_table_query` and `execute_cards_query` methods extract WHERE bodies and rebuild count/data queries, but dropped all PREFIX lines. RDF4J rejected these with parse errors, silently caught as warnings. Applied `inject_prefixes()` at each reconstruction site (4 queries total). Also added auto-injection of `dcterms:created` and `dcterms:modified` timestamps to object creation, with user-supplied value precedence.

**S02 — Diff-Based Save:** The save endpoint unconditionally created `object.patch` events recording every form property as changed. Added `_normalize_value_for_compare()` (handles datetime format mismatches between HTML inputs and triplestore values) and `_compute_changed_properties()` (compares normalized sorted lists). The save path now queries current triplestore values, diffs against form values, and patches only changes. Client-side added a `_sempkmSavedContent` guard skipping body POST when content is unchanged.

**S03 — Object Delete UI:** Delivered single-object delete across three surfaces (toolbar button, command palette, explorer hover action) all calling the shared `deleteObject()` function. Backend fix: `bulk_delete_objects()` now also queries and deletes inbound edges (`?s ?p <deleted_iri>`), preventing dangling references. The empty-bindings guard was moved downstream to handle objects with only inbound references.

**S04 — Docker Fresh-Volume Deploy:** Created `backend/docker-entrypoint.sh` ensuring data directories exist before app startup. Fixed LuceneSail permission failure by consolidating the separate `lucene_index` volume into the parent `rdf4j_data` volume. Added `_wait_for_repo_ready()` polling to handle the RDF4J initialization race after repository creation. All fixes verified with full fresh-volume cycle.

## Success Criteria Results

### Success Criteria Results

- ✅ **Table View renders objects with labels, types, created, and modified columns.** `inject_prefixes()` applied to all 4 reconstructed SPARQL queries in `execute_table_query()` and `execute_cards_query()`. 6 unit tests in `test_view_prefix_fix.py` confirm prefix injection and non-empty results.

- ✅ **Cards View renders cards with data.** Same `inject_prefixes()` fix covers both table and cards query paths. Verified by unit tests.

- ✅ **New objects have dcterms:created timestamp.** `handle_object_create` now auto-injects `dcterms:created` and `dcterms:modified` as `xsd:dateTime` literals. 10 unit tests in `test_object_create_timestamps.py` verify presence, format, datatype, and user-supplied precedence.

- ✅ **Save only produces events for actually-changed properties.** `_compute_changed_properties()` diffs form vs triplestore values. 22 unit tests in `test_save_diff.py` cover normalization, multi-value ordering, new/deleted properties, and the `dcterms:modified` injection guard.

- ✅ **No-op save creates no event.** When `_compute_changed_properties()` returns empty dict, no `object.patch` command is built. Client-side `_sempkmSavedContent` guard prevents no-op body POST. Verified by `TestDctermsModifiedIntegration` tests.

- ✅ **Delete button on object toolbar with confirmation dialog.** `.delete-btn` with trash-2 Lucide icon in `object_tab.html`, `showConfirmDialog()` before API call, tab close + tree refresh + toast after. Also wired to command palette and explorer hover action.

- ✅ **Deleted object removed from explorer tree, views, and SPARQL.** Inbound edge cleanup in `bulk_delete_objects()` prevents dangling references. 7 unit tests in `test_object_delete_inbound.py` verify inbound/outbound coverage.

- ✅ **Docker fresh-volume deploy succeeds.** Entrypoint script, consolidated lucene volume, and `_wait_for_repo_ready()` polling fix the three failure modes. `scripts/verify-docker-fresh.sh` provides reproducible verification.

- ✅ **Business-planning model loads all 33 NodeShapes.** Confirmed via direct triplestore SPARQL query after fresh install. The stale-data theory was validated — the previous "2 shapes" observation was from an older archive.

## Definition of Done Results

### Definition of Done Results

- ✅ **All 4 slices complete** — S01, S02, S03, S04 all marked ✅ in roadmap
- ✅ **All slice summaries exist** — 4/4 slice SUMMARY.md files present
- ✅ **All task summaries exist** — 8/8 task SUMMARY.md files present (2 per slice)
- ✅ **45 new unit tests pass** — `pytest` across 4 test files: 6 (prefix) + 10 (timestamps) + 22 (diff-save) + 7 (delete inbound) = 45 passed, 0 failed
- ✅ **All Python source files parse cleanly** — ast.parse verified on all 4 key backend files
- ✅ **No source file deletions** — `git diff-tree --diff-filter=D` returns empty
- ✅ **20 non-.gsd/ files changed** — substantial code, test, Docker, and frontend changes verified via git diff --stat
- ✅ **Cross-slice integration**: S03 depends on S01 (views render correctly to verify delete removes objects) — both complete

## Requirement Outcomes

### Requirement Status Transitions

No requirements changed status during this milestone. M048 was a bug-fix milestone addressing broken functionality rather than advancing new requirements. R001 (lazy-load panels) remains active, owned by M049/S03.

## Deviations

S04/T02 required two code fixes (removing lucene_index volume, adding _wait_for_repo_ready()) that the plan classified as conditional. The empty-bindings guard in S03/T01 was moved downstream (correctness improvement beyond plan). All deviations were improvements.

## Follow-ups

None — all four bugs are fully resolved with tests.
