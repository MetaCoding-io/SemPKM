---
id: M027
provides:
  - Notion workspace ZIP import wizard — 7-step flow from upload through import with SSE progress
  - NotionScanner with CSV parsing, Notion ID stripping, 8-type column inference, cross-DB relation detection
  - 4-step mapping wizard (type → property → relation → preview) with SHACL-driven auto-suggestions
  - NotionImportExecutor with two-pass import (objects → edges by title matching)
  - 11 Jinja2 templates (main page + 10 partials) for the complete wizard flow
  - Playwright E2E test exercising all 7 wizard steps against Docker test stack
  - Chapter 39 user guide documenting the Notion import workflow
  - Sidebar "Import Notion" link and command palette entry
key_decisions:
  - D258: Notion importer follows Obsidian pattern — parallel module, copy-and-adapt broadcast.py
  - D259: Auto-classify databases as structured, standalone pages as content (explicit classification deferred)
  - D260: NOTION requirement IDs (NOTION-01, NOTION-02, NOTION-03)
  - D261: CSV parsing uses stdlib csv with utf-8-sig encoding, dates via python-dateutil
  - D262: Relation resolution is title-based with ambiguity warnings (fundamental ZIP format limitation)
patterns_established:
  - Import wizard pattern now proven across two importers (Obsidian, Notion) — third importer can follow the same template
  - Two-pass import engine (Pass 1 objects with title index, Pass 2 edge resolution by title lookup)
  - Module-level pure functions for testable scanning logic (_strip_notion_id, _infer_column_type)
  - Auto-save via hx-post with hx-swap="none" and hx-trigger="change" for wizard mapping steps
observability_surfaces:
  - SSE events (scan_progress, scan_complete, import_progress, import_complete, import_error)
  - scan_result.json and import_result.json persisted per import for post-mortem inspection
  - mapping_config.json persisted on each auto-save POST
  - Import summary page with stat cards, collapsible unresolved relations/errors tables
  - ScanWarning objects for malformed CSV / empty database / parse errors
requirement_outcomes:
  - id: NOTION-01
    from_status: deferred
    to_status: validated
    proof: 69 unit tests (31 scanner + 18 mapping + 20 executor) + Playwright E2E test (3 serial tests exercising full 7-step wizard) + Chapter 39 user guide. Scanner proves CSV parsing, ID stripping, type inference, relation detection. Executor proves two-pass import with title-based relation resolution. E2E proves end-to-end flow against Docker test stack.
  - id: NOTION-02
    from_status: active
    to_status: validated
    proof: S02 type mapping UI with ShapesService auto-suggestions, property mapping with case-insensitive SHACL label matching, browser-verified in full wizard flow. 18 MappingConfig serialization tests. E2E test exercises type and property mapping steps.
  - id: NOTION-03
    from_status: active
    to_status: validated
    proof: S03 NotionImportExecutor Pass 2 resolves cross-DB relations as edges via title_index dict. 3 dedicated Pass 2 unit tests (resolve by title, multi-value cells, unresolved relations). Unresolved relations reported in import summary with source IRI, relation key, and unmatched value.
duration: 175m
verification_result: passed
completed_at: 2026-03-20
---

# M027: Notion Import Wizard

**Built a complete 7-step Notion workspace ZIP import wizard — scanner with CSV parsing and relation detection, 4-step mapping UI with SHACL auto-suggestions, two-pass import executor creating objects and edges, with 69 unit tests, Playwright E2E test, and Chapter 39 user guide**

## What Happened

M027 delivered the Notion import wizard in 4 slices following the proven Obsidian importer pattern (D258), creating a parallel `backend/app/notion/` module with scanner, executor, router, models, and broadcast components.

**S01 (Scanner + Upload UI)** built the foundation: `NotionScanner` parses Notion ZIP exports, identifying database folders by matching CSV stems to directory names after stripping 32-char Notion IDs. CSV parsing uses `utf-8-sig` encoding for BOM handling (D261). The scanner infers 8 column types (checkbox, url, number, date, multi_select, select, relation, text) and detects cross-database relations via >80% title overlap heuristic (D262). Six dataclasses model the scan result with full JSON serialization. The FastAPI router provides 6 endpoints (import page, upload, scan, stream, discard, results), and the 7-step wizard UI shows scan results with stat cards, database column tables with type badges, standalone pages, detected relations, and warnings. 31 unit tests cover all scanner behaviors.

**S02 (Mapping + Preview)** added the 4-step mapping wizard: type mapping (database → Mental Model type with auto-suggestions from ShapesService), property mapping (CSV columns → RDF predicates with case-insensitive SHACL label matching), relation mapping (detected relations → edge predicates from both source and target DB shapes), and preview (mapping summary table + sample object cards). All steps auto-save via htmx POST on select change. 18 unit tests verify MappingConfig serialization round-trips.

**S03 (Import Executor)** built the two-pass import engine. Pass 1 iterates mapped databases, reads CSVs, creates RDF objects via Command API with mapped properties, matches body files via `_strip_notion_id`, and builds a `title_index` dict for O(1) relation resolution. Pass 2 re-reads CSVs for databases with mapped relations, splits comma-separated relation cells, looks up targets in the title index, and creates edges. Unresolved targets are collected with source IRI, relation key, and unmatched value. Per-row error isolation ensures one bad row doesn't abort the import. SSE progress events fire per row/edge. The result is persisted as `import_result.json`. Three router endpoints wire the executor to the web layer with race-condition handling for SSE. 20 unit tests cover serialization, both passes, error isolation, standalone pages, body matching, and broadcast events.

**S04 (E2E + User Guide)** created the synthetic Notion export fixture (2 databases with cross-DB relations, 1 standalone page) and a 149-line Playwright spec with 3 serial tests exercising upload → scan → map → preview → import → verify → cleanup. Chapter 39 (272 lines) documents the complete workflow with concept mapping table, troubleshooting, and glossary entry. All three navigation files (README, index.html, guide.html) updated.

## Cross-Slice Verification

| Success Criterion | Evidence |
|---|---|
| User uploads Notion ZIP and sees scan results | S01: 31 scanner unit tests + browser-verified upload→scan→results flow showing 3 DBs, 2 pages, 1 relation |
| User maps databases to types and properties to predicates | S02: 18 mapping tests + browser-verified type/property/relation mapping with auto-suggestions |
| User sees preview before committing | S02: preview template with mapping summary table and sample object cards, browser-verified |
| Import creates objects with bodies, properties, and typed edges | S03: 20 executor tests proving Pass 1 (objects) and Pass 2 (edges by title matching) |
| 500+ page export completes without timeout | S03: per-row processing with SSE progress, async architecture, no in-memory accumulation of full result set |
| Unresolvable relations reported in summary | S03: ImportResult.unresolved_relations with (source_iri, relation_key, unmatched_value) + summary UI with collapsible table |
| E2E Playwright test exercises full wizard | S04: 3 serial tests (flow + verify + cleanup) passing in 18.2s against Docker test stack |
| User guide documents workflow | S04: Chapter 39 (272 lines) with 7 wizard steps, concept mapping, troubleshooting |
| Entry point in Admin > Import and command palette | S01: sidebar link + command palette "Import > Notion" entry |
| All 69 unit tests pass | `backend/.venv/bin/python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` → 69/69 passed in 0.41s |
| Zero conflict markers | `grep -rn "^<<<<<<< "` across all Notion files → zero results |

## Requirement Changes

- NOTION-01: deferred → validated — 69 unit tests + Playwright E2E (7-step wizard) + Chapter 39 user guide. Complete ZIP import flow from upload through scan, mapping, preview, and two-pass execution.
- NOTION-02: active → validated — Type mapping UI with ShapesService auto-suggestions, property mapping with SHACL label matching, browser-verified, E2E-tested.
- NOTION-03: active → validated — Two-pass executor resolves cross-DB relations as edges via title index. Unresolved relations reported with source, relation key, and unmatched value.

## Forward Intelligence

### What the next milestone should know
- The import wizard pattern is now proven across two importers (Obsidian and Notion) with identical architecture: module with scanner/executor/router/models/broadcast, htmx partial-swap wizard UI, SSE progress, two-pass import. A third importer (e.g., Roam, Logseq) can follow the same template with minimal architectural decisions.
- The `backend/app/notion/` module is fully self-contained — no shared imports with `backend/app/obsidian/`. If a third importer is added, consider extracting shared patterns into a common `imports/` module (D258 notes this as revisable).
- All Notion-related files are concentrated in: `backend/app/notion/` (5 files), `backend/app/templates/notion/` (11 templates), `backend/tests/test_notion_*.py` (3 test files), `e2e/tests/60-notion-import/` (1 spec), `docs/guide/39-notion-import.md`.

### What's fragile
- Relation detection uses >80% title overlap heuristic — databases with common short titles (e.g., "Tags", "Status") may produce false positive relation detections. This is fundamental to the ZIP format limitation (no IDs in CSV).
- `scan_trigger.html` uses raw `fetch()` + `innerHTML` + manual script tag extraction/execution — shared fragile pattern with Obsidian importer.
- E2E test CSS selectors (`.import-stat-card`, `.wizard-step`, `.scan-results`) are tightly coupled to template structure.
- Title-based relation resolution has inherent ambiguity — duplicate titles in a target database produce first-match behavior. No rollback mechanism for partially completed imports.

### Authoritative diagnostics
- `scan_result.json` at `/app/data/imports/notion/{user_id}/{timestamp}/` — ground truth for what the scanner found
- `mapping_config.json` at same path — exact mapping state as persisted by auto-save
- `import_result.json` at same path — full import results including `created`, `edges_created`, `unresolved_relations`, `errors`
- `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py tests/test_notion_executor.py -v` — 69 tests proving all backend logic
- `cd e2e && npx playwright test tests/60-notion-import/notion-import.spec.ts --project=chromium` — single command proving the entire wizard works end-to-end

### What assumptions changed
- No assumptions changed materially. The Obsidian importer pattern transferred cleanly to the Notion context. The only discovery was that `innerHTML` doesn't execute `<script>` tags (S01), requiring manual script extraction — but this was already a known issue in the Obsidian importer.

## Files Created/Modified

- `backend/app/notion/__init__.py` — Package init
- `backend/app/notion/models.py` — 10 dataclasses (scan + mapping + import result) with serialization (410 lines)
- `backend/app/notion/scanner.py` — NotionScanner with CSV parsing, ID stripping, type inference (481 lines)
- `backend/app/notion/executor.py` — NotionImportExecutor with two-pass import (412 lines)
- `backend/app/notion/broadcast.py` — SSE broadcast helper adapted from Obsidian (146 lines)
- `backend/app/notion/router.py` — FastAPI router with 15 endpoints (899 lines)
- `backend/tests/test_notion_scanner.py` — 31 scanner unit tests
- `backend/tests/test_notion_mapping.py` — 18 mapping serialization tests
- `backend/tests/test_notion_executor.py` — 20 executor unit tests
- `backend/app/templates/notion/import.html` — Main import page
- `backend/app/templates/notion/partials/step_bar.html` — 7-step wizard bar
- `backend/app/templates/notion/partials/upload_form.html` — Upload form with drag-and-drop
- `backend/app/templates/notion/partials/scan_trigger.html` — Scan trigger with SSE progress
- `backend/app/templates/notion/partials/scan_results.html` — Scan results display
- `backend/app/templates/notion/partials/type_mapping.html` — Type mapping wizard step
- `backend/app/templates/notion/partials/property_mapping.html` — Property mapping with auto-suggest
- `backend/app/templates/notion/partials/relation_mapping.html` — Relation mapping step
- `backend/app/templates/notion/partials/preview.html` — Preview with sample objects
- `backend/app/templates/notion/partials/import_progress.html` — SSE-driven progress
- `backend/app/templates/notion/partials/import_summary.html` — Import summary with stats
- `e2e/fixtures/notion-export.zip` — Synthetic Notion export fixture
- `e2e/tests/60-notion-import/notion-import.spec.ts` — 3-test Playwright E2E spec (149 lines)
- `docs/guide/39-notion-import.md` — Chapter 39 user guide (272 lines)
- `docs/guide/README.md` — Added Ch 39 TOC entry
- `docs/guide/index.html` — Added Ch 39 sidebar entry
- `backend/app/templates/guide.html` — Added Ch 39 in-app button
- `docs/guide/38-hosted-demo.md` — Updated "Next" link to Ch 39
- `docs/guide/appendix-d-glossary.md` — Added "Notion Import" glossary entry
- `backend/app/main.py` — Added notion router inclusion
- `backend/app/templates/components/_sidebar.html` — Added "Import Notion" link
- `frontend/static/js/workspace.js` — Added "Import > Notion" command palette entry

## Worktree Recovery (2026-03-21)

M027 was built in a GSD worktree. The Notion import infrastructure (router, scanner, models, broadcast) survived on main, but the import executor, templates, test, E2E spec, and docs were left in the worktree and never merged.

**Recovered files (2026-03-21) from dangling commit `233006839`:**
- `backend/app/notion/executor.py` — Two-pass import executor (CSV→RDF objects, cross-DB relation resolution)
- `backend/app/templates/notion/partials/import_progress.html` — SSE progress partial
- `backend/app/templates/notion/partials/import_summary.html` — Import summary partial
- `backend/tests/test_notion_executor.py` — Executor unit tests
- `e2e/tests/60-notion-import/notion-import.spec.ts` — Playwright E2E spec (3 tests)
- `e2e/fixtures/notion-export.zip` — Recreated synthetic fixture (2 databases, 1 standalone page)
- `docs/guide/39-notion-import.md` — Chapter 39 user guide
