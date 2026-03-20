# S03: Two-Pass Import Executor + Full Flow — Research

**Date:** 2026-03-20

## Summary

This slice builds the Notion import executor — the final backend component that reads CSV data and markdown bodies from the extracted ZIP, creates objects (Pass 1), resolves cross-database relations as edges (Pass 2), and reports results via SSE progress. The Obsidian `ImportExecutor` at `backend/app/obsidian/executor.py` is a direct 1:1 reference pattern (~250 lines). The Notion version replaces frontmatter parsing with CSV row iteration and wiki-link resolution with title-based relation lookup, but the overall structure (two-pass, per-item error isolation, SSE progress, result persistence as `import_result.json`, summary template) is identical.

This is **straightforward application of a known pattern**. The Obsidian executor is clean, well-structured, and the Notion data model (scan result + mapping config) is already fully built by S01 and S02. The main novel logic is: (1) re-reading CSV files from the extracted workspace to iterate all rows, (2) building a `title → IRI` lookup dict after Pass 1 for relation resolution, and (3) handling standalone markdown pages as a separate pass. All three are simple data-structure operations.

## Recommendation

**Follow the Obsidian executor exactly.** Copy `executor.py`, adapt the two passes, and add three new router endpoints + two new templates (import_progress, import_summary). Enable the disabled Import button on `preview.html`. Add an `ImportResult` dataclass to `models.py`.

Build order: models first (ImportResult), executor second (the core logic), router+templates third (wiring), preview button fix last (trivial). Unit tests for the executor's pure logic (CSV reading, title→IRI indexing) should be co-located with the executor task.

## Implementation Landscape

### Key Files

#### Existing (read/modify)
- `backend/app/notion/models.py` — Add `ImportResult` dataclass with `to_dict()`/`from_dict()`. Follow Obsidian's `ImportResult` (created, skipped, edges_created, errors, unresolved_links, duration_seconds) but add `unresolved_relations` field (list of source_iri + relation_key + unmatched_value tuples) for Notion-specific ambiguity reporting.
- `backend/app/notion/router.py` — Add 3 endpoints: `POST /{import_id}/execute` (trigger import, return progress partial), `GET /{import_id}/execute/stream` (SSE), `GET /{import_id}/summary` (post-import summary). Copy pattern from Obsidian `router.py` lines 531–654.
- `backend/app/templates/notion/partials/preview.html` — Remove `disabled` attribute from Import button, add `hx-post` to execute endpoint. Change title text from "Coming in next update" to "Import".

#### New (create)
- `backend/app/notion/executor.py` — `NotionImportExecutor` class (~200–250 lines). Constructor takes same deps as Obsidian (scan_result, mapping_config, extract_path, event_store, triplestore_client, user, broadcast, import_dir). `execute()` method runs the two-pass import.
- `backend/app/templates/notion/partials/import_progress.html` — Adapt from Obsidian's `import_progress.html`. Change SSE URL from `/browser/import/` to `/browser/notion/`. Step 7 active.
- `backend/app/templates/notion/partials/import_summary.html` — Adapt from Obsidian's `import_summary.html`. Add "Unresolved Relations" section alongside "Unresolved Links". Add "Browse Imported Objects" and "Import More" buttons with Notion-specific URLs.
- `backend/tests/test_notion_executor.py` — Unit tests for the executor's pure logic.

#### Reference (read only)
- `backend/app/obsidian/executor.py` — The 1:1 reference pattern. 250 lines covering two-pass import, SSE broadcast, result persistence, error isolation.
- `backend/app/obsidian/router.py` lines 531–654 — Execute, stream, and summary endpoints.
- `backend/app/templates/obsidian/partials/import_progress.html` — SSE progress UI template.
- `backend/app/templates/obsidian/partials/import_summary.html` — Post-import summary template.
- `backend/app/commands/schemas.py` — `ObjectCreateParams`, `BodySetParams`, `EdgeCreateParams`.
- `backend/app/commands/handlers/object_create.py` — `handle_object_create()`, `_resolve_predicate()`.
- `backend/app/commands/handlers/edge_create.py` — `handle_edge_create()`.
- `backend/app/commands/handlers/body_set.py` — `handle_body_set()`.

### Executor Design (core logic)

**Pass 1 — Create Objects:**
1. For each database in `scan_result.databases`:
   - Skip if `mapping_config.type_mappings[db.name]` is None
   - Re-read the CSV file from `extract_path / db.csv_path` with `encoding='utf-8-sig'`
   - For each CSV row:
     - Title = first column value (row_titles pattern from scanner)
     - Build properties dict from `mapping_config.property_mappings[type_iri]` — for each mapped column, extract the cell value
     - Add `sempkm:importSource` = `db.csv_path` and `dcterms:title` = title
     - Call `handle_object_create()` → get `object_iri`
     - Read the corresponding `.md` file from `extract_path / db.folder_path / "{title} {notion_id}.md"` if it exists → call `handle_body_set()`
     - Commit via `event_store.commit()`
     - Store `title.lower() → object_iri` in lookup dict (per database, keyed by db name)
     - Broadcast SSE `import_progress` with phase="objects"

2. For standalone pages (if `mapping_config.standalone_page_type_iri` is set):
   - For each page in `scan_result.standalone_pages`:
     - Create object with the standalone type, title from page.title
     - Read body from `extract_path / page.file_path`
     - Commit, store in lookup dict

**Pass 2 — Resolve Relations as Edges:**
1. For each database with mapped relations:
   - Re-read CSV (or use cached data from Pass 1)
   - For each row, for each relation column:
     - Look up `mapping_config.relation_mappings[f"{db.name}|{col.name}"]`
     - If mapped, split cell value by comma (multi-relation), look up each value in the target DB's title→IRI dict
     - Call `handle_edge_create()` with the mapped predicate
     - Batch commit every 10 edges (same as Obsidian)
     - Track unresolved relations for summary

**Key data structure:** `title_index: dict[str, dict[str, str]]` — outer key is `db_name`, inner key is `title.lower()`, value is `object_iri`. Populated during Pass 1. Used by Pass 2 for O(1) title→IRI lookup.

**CSV re-reading:** The executor must re-read CSV files from `extract_path` because `scan_result` only stores sample rows (up to 5). The full CSV has all rows. Path: `Path(scan_result.extract_path) / db.csv_path`. The `extract_path` is stored as an absolute path string in `scan_result.json`.

**Markdown body files:** Inside a database folder, row body files are named `{title} {notion_id}.md`. To match them, iterate `.md` files in `extract_path / db.folder_path` and strip Notion IDs from stems. Build a `stripped_name.lower() → file_path` dict per database for body lookup. Import `_strip_notion_id` from `notion.scanner`.

### Build Order

1. **T01 — ImportResult model + Executor** (backend only): Add `ImportResult` dataclass to `models.py`. Create `executor.py` with the two-pass logic. Write unit tests for the pure functions (CSV re-reading, title indexing, body file matching). This is the core deliverable.

2. **T02 — Router endpoints + Templates + Preview button**: Add 3 router endpoints (execute, stream, summary). Create `import_progress.html` and `import_summary.html` templates adapted from Obsidian. Enable the Import button in `preview.html`. This wires up the full flow.

### Verification Approach

**Unit tests** (`backend/tests/test_notion_executor.py`):
- Test `ImportResult` serialization round-trip
- Test executor with mock EventStore and TriplestoreClient:
  - Pass 1 creates objects from CSV rows with correct properties
  - Pass 1 reads markdown body files and calls body_set
  - Pass 1 handles standalone pages
  - Pass 2 resolves relations by title matching
  - Pass 2 reports unresolved relations (ambiguous or missing)
  - Per-row error isolation (one bad row doesn't abort)
  - Broadcast events fire at correct phases

**Existing tests must still pass**: `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` — zero regressions.

**AST parse check**: `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` — no syntax errors.

**Template syntax**: All new Jinja2 templates parse without errors.

**Integration** (manual/browser): Upload ZIP → scan → map → preview → click Import → see SSE progress bar → see summary with stats. This is the full wizard flow.

## Constraints

- CSV files re-read from `extract_path` stored in `scan_result.json` — this is an absolute path on the container filesystem (`/app/data/imports/notion/{user_id}/{timestamp}/workspace/...`). If the import directory is moved or the container is recreated between scan and import, the path breaks. This matches the Obsidian pattern.
- The `_broadcasts` dict in `router.py` is module-level — same singleton pattern as Obsidian. Import broadcast uses a distinct key `f"{import_id}_import"` to avoid collision with scan broadcasts.
- `handle_object_create` and `handle_edge_create` are async functions that return `Operation` objects. The executor must await them individually and batch-commit via `event_store.commit()`.
- Step bar shows step 7 "Import" — the progress template should set `current_step = 7`.
- The SSE URL pattern must be `/browser/notion/{import_id}/execute/stream` (not `/browser/import/` like Obsidian). The Notion router prefix is `/browser/notion`.

## Common Pitfalls

- **CSV re-read encoding** — Must use `encoding='utf-8-sig'` when re-reading CSVs (same as scanner). Notion exports have UTF-8 BOM.
- **Body file matching by stripped title** — Notion filenames have the 32-char ID. Must use `_strip_notion_id()` from `scanner.py` to match CSV row titles to `.md` filenames. Case-insensitive matching needed because Notion may use different casing in filenames vs CSV values.
- **Multi-value relation cells** — Notion relation columns can contain comma-separated page titles (e.g., "Project A, Project B"). Must split on comma and look up each value independently.
- **Duplicate titles in target DB** — The title→IRI dict stores `title.lower() → iri`. If two rows in the same DB have the same title, the second overwrites the first. This is the expected behavior per D262 (first-match). Log a warning and include in `unresolved_relations` count.
- **Empty/missing body files** — Not all CSV rows have corresponding `.md` files (some rows are data-only). The executor must handle missing body files gracefully (skip body_set, no error).
- **Import button in preview.html** — Currently has `disabled` attribute and `title="Coming in next update"`. Must remove both, add `hx-post` and `hx-target="#import-content"` and `hx-swap="innerHTML"`.

## Open Risks

- **Large CSV performance** — A 500+ row CSV means 500+ individual `handle_object_create` + `event_store.commit` calls. The Obsidian importer handles 895 objects in ~30s with this pattern, so 500 rows should be fine. But if each commit involves a triplestore roundtrip, there's a linear scaling cost. The Obsidian pattern commits per-object (not batched), which is proven acceptable.
- **Relation column value format** — Notion's CSV export represents multi-relation values as comma-separated titles. If a page title itself contains a comma, splitting on comma produces wrong results. This is a known Notion export limitation — no workaround exists for ZIP-only import. Document in import summary warnings.
