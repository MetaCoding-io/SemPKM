---
estimated_steps: 8
estimated_files: 3
---

# T01: ImportResult model + NotionImportExecutor + unit tests

**Slice:** S03 — Two-Pass Import Executor + Full Flow
**Milestone:** M027

## Description

Create the core Notion import engine. This task adds the `ImportResult` dataclass to `models.py` and creates `executor.py` with the `NotionImportExecutor` class — a two-pass import that creates objects from CSV data (Pass 1) and resolves cross-database relations as edges by title matching (Pass 2). Unit tests use mock EventStore and TriplestoreClient to verify all import paths.

The Obsidian executor at `backend/app/obsidian/executor.py` is the 1:1 reference pattern (~250 lines). The Notion version replaces frontmatter parsing with CSV row iteration and wiki-link resolution with title-based relation lookup. The overall structure (two-pass, per-item error isolation, SSE broadcast, result persistence) is identical.

**Relevant skills:** `test` (for unit test generation guidance)

## Steps

1. **Add `ImportResult` dataclass to `backend/app/notion/models.py`:**
   - Add `@dataclass` class after `MappingConfig` at the end of the file
   - Fields: `created: int = 0`, `skipped: int = 0`, `edges_created: int = 0`, `unresolved_relations: list[tuple[str, str, str]] = field(default_factory=list)` (source_iri, relation_key, unmatched_value), `errors: list[tuple[str, str]] = field(default_factory=list)` (path, error_message), `duration_seconds: float = 0.0`
   - Add `to_dict()` method that serializes tuples as dicts: `unresolved_relations` as `[{"source": s, "relation": r, "value": v}]`, `errors` as `[{"path": p, "message": m}]`
   - Add `from_dict()` classmethod for deserialization
   - Import `field` from dataclasses is already imported at top of file

2. **Create `backend/app/notion/executor.py`:**
   - Import: `json, logging, csv, time` from stdlib; `Path` from pathlib; `URIRef` from rdflib; `User` from `app.auth.models`; command handlers (`handle_object_create`, `handle_body_set`, `handle_edge_create`), schemas (`ObjectCreateParams`, `BodySetParams`, `EdgeCreateParams`), `_resolve_predicate` from `app.commands.handlers.object_create`; `settings` from `app.config`; `EventStore` from `app.events.store`; `TriplestoreClient` from `app.triplestore.client`; `ScanBroadcast, SSEEvent` from `.broadcast`; `ImportResult, MappingConfig, NotionScanResult` from `.models`; `_strip_notion_id` from `.scanner`
   - Class `NotionImportExecutor` with `__init__` taking: `scan_result: NotionScanResult`, `mapping_config: MappingConfig`, `extract_path: Path`, `event_store: EventStore`, `triplestore_client: TriplestoreClient`, `user: User`, `broadcast: ScanBroadcast`, `import_dir: Path`
   - Store `_user_iri = URIRef(f"urn:sempkm:user:{user.id}")` and `_base_namespace = settings.base_namespace`

3. **Implement `execute()` async method — Pass 1 (Create Objects):**
   - Initialize `ImportResult`, start timer
   - Build a `title_index: dict[str, dict[str, str]]` — outer key is `db_name`, inner key is `title.lower()`, value is `object_iri`
   - Count total items for progress: sum of `db.row_count` for mapped databases + len of standalone pages if mapped
   - For each database in `scan_result.databases`:
     - Skip if `mapping_config.type_mappings.get(db.name)` is None
     - Get `type_iri` from the TypeMapping
     - Get `prop_mappings` from `mapping_config.property_mappings.get(type_iri, {})`
     - Re-read the CSV file from `Path(scan_result.extract_path) / db.csv_path` with `encoding='utf-8-sig'`, using `csv.DictReader`
     - Build a body file lookup dict: iterate `.md` files in `Path(scan_result.extract_path) / db.folder_path`, call `_strip_notion_id(md_file.stem).lower()` → `md_file` path. This handles body file matching.
     - For each CSV row:
       - Title = first column value (use `next(iter(row.values()))` or `row[reader.fieldnames[0]]`)
       - Build properties dict: for each `(col_name, pm)` in prop_mappings where `pm is not None`, extract `row.get(col_name, "")`, skip if empty
       - Add `sempkm:importSource = db.csv_path` and `dcterms:title = title` to properties
       - Call `handle_object_create(ObjectCreateParams(type=type_iri, slug=None, properties=properties), self._base_namespace)` → get `object_iri` from `create_op.affected_iris[0]`
       - Look up body: `body_lookup.get(title.lower())` → if found, read the `.md` file and call `handle_body_set(BodySetParams(iri=object_iri, body=body_text), self._base_namespace)`
       - Commit via `event_store.commit(operations, performed_by=self._user_iri, performed_by_role=self.user.role)`
       - Store `title.lower() → object_iri` in `title_index[db.name]`
       - Broadcast SSE `import_progress` with phase="objects", current, total
       - Wrap entire per-row logic in try/except — on error, increment `result.errors`, log warning, continue
   - For standalone pages (if `mapping_config.standalone_page_type_iri` is set):
     - For each page in `scan_result.standalone_pages`:
       - Create object with type=standalone_page_type_iri, title from page.title
       - Read body from `Path(scan_result.extract_path) / page.file_path` if the file exists
       - Commit, broadcast progress
       - Store in a "standalone" key in title_index (for potential future use)

4. **Implement `execute()` — Pass 2 (Resolve Relations):**
   - For each database with mapped relations in `mapping_config.relation_mappings`:
     - Re-read the CSV file (or cache rows from Pass 1 — for simplicity, re-read)
     - For each row:
       - For each detected relation from `scan_result.detected_relations` where `source_db_name == db.name`:
         - `relation_key = f"{db.name}|{rel.source_column}"`
         - Look up `rm = mapping_config.relation_mappings.get(relation_key)` — skip if None
         - Get cell value `row.get(rel.source_column, "")`
         - Split on comma → list of target titles
         - For each target title (stripped):
           - Look up `target_iri = title_index.get(rel.target_db_name, {}).get(target_title.lower())`
           - If found: call `handle_edge_create(EdgeCreateParams(source=source_iri, target=target_iri, predicate=rm.target_predicate_iri, properties={}), self._base_namespace)`
           - If not found: append to `result.unresolved_relations`
         - Batch-commit every 10 edges (same as Obsidian)
         - Broadcast SSE `import_progress` with phase="edges"
   - Commit remaining edge batch
   - **Important:** Need to track which row maps to which object_iri from Pass 1. Store a `row_iri_map: dict[str, dict[str, str]]` keyed by `db_name`, inner key is `title.lower()` → `object_iri`. This is the same as `title_index` — reuse it.

5. **Implement result persistence and completion:**
   - Set `result.duration_seconds = round(time.monotonic() - start, 2)`
   - Write `import_result.json` to `import_dir`
   - Broadcast `import_complete` SSE event with `result.to_dict()`
   - Wrap entire execute in try/except — on catastrophic failure, broadcast `import_error`

6. **Create `backend/tests/test_notion_executor.py`:**
   - Test `ImportResult` serialization round-trip (to_dict → from_dict)
   - Test `ImportResult` with empty unresolved_relations and errors
   - Test executor Pass 1 with mock EventStore: create a temp dir with a CSV file and a corresponding .md body file. Set up a NotionScanResult with one database pointing at the CSV. Set up a MappingConfig with type mapping and one property mapping. Mock `handle_object_create` to return a fake Operation with `affected_iris = ["urn:test:obj1"]`. Mock `handle_body_set` similarly. Mock `event_store.commit` as async no-op. Verify `result.created == row_count`, `handle_object_create` called with correct type and properties, `handle_body_set` called for rows with body files.
   - Test executor Pass 2: set up a relation mapping, verify `handle_edge_create` called with correct source/target/predicate. Use the title_index populated from Pass 1 mocks.
   - Test unresolved relations: set up a relation column value that doesn't match any title in target DB. Verify it appears in `result.unresolved_relations`.
   - Test per-row error isolation: mock `handle_object_create` to raise on the 2nd row. Verify first and third rows still succeed.
   - Test standalone page import: set up standalone_page_type_iri in mapping config with a standalone page in scan result.
   - Test body file matching with stripped Notion ID: body file named `"My Page abc123def456abc123def456abc12345.md"` should match CSV row title `"My Page"`.
   - Test multi-value relation cells: cell value `"Project A, Project B"` should create two edge_create calls.
   - Test broadcast events fire at correct phases.
   - Use `pytest` with `unittest.mock.AsyncMock` for async mocks. Use `tmp_path` fixture for filesystem.

7. **Run all Notion tests to verify zero regressions:**
   - `cd backend && python -m pytest tests/test_notion_executor.py tests/test_notion_scanner.py tests/test_notion_mapping.py -v`

8. **AST parse check:**
   - `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"`
   - `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"`

## Must-Haves

- [ ] `ImportResult` dataclass with `unresolved_relations` field (list of tuples) and `to_dict()`/`from_dict()`
- [ ] `NotionImportExecutor.execute()` creates objects from CSV rows with mapped properties
- [ ] Executor reads markdown body files by matching stripped Notion IDs to CSV row titles (case-insensitive)
- [ ] Pass 2 resolves relations by title→IRI lookup in the target database's index
- [ ] Multi-value relation cells (comma-separated) split and looked up independently
- [ ] Per-row error isolation — one bad row doesn't abort the import
- [ ] Standalone page import when `standalone_page_type_iri` is set
- [ ] SSE broadcast events fire during both phases
- [ ] `import_result.json` persisted to import directory
- [ ] All unit tests pass with zero regressions on existing tests

## Verification

- `cd backend && python -m pytest tests/test_notion_executor.py -v` — all new tests pass
- `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` — 49 existing tests pass (zero regressions)
- `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` — no syntax errors

## Observability Impact

- Signals added: SSE events `import_progress` (phase/current/total/current_file or current_link), `import_complete` (full result dict), `import_error` (message)
- How a future agent inspects this: `cat /app/data/imports/notion/{user_id}/{timestamp}/import_result.json`
- Failure state exposed: `ImportResult.errors` list with path+message per failed row; `ImportResult.unresolved_relations` with source_iri+relation_key+value for each failed lookup

## Inputs

- `backend/app/notion/models.py` — existing dataclasses (NotionScanResult, MappingConfig, etc.) from S01+S02
- `backend/app/notion/scanner.py` — `_strip_notion_id()` function for body file matching
- `backend/app/notion/broadcast.py` — `ScanBroadcast` and `SSEEvent` for SSE progress
- `backend/app/obsidian/executor.py` — reference pattern for two-pass import structure, per-item error isolation, batch edge commits, result persistence
- `backend/app/obsidian/models.py` (line 256+) — reference `ImportResult` dataclass (Notion version adds `unresolved_relations`)
- `backend/app/commands/handlers/object_create.py` — `handle_object_create()`, `_resolve_predicate()`
- `backend/app/commands/handlers/edge_create.py` — `handle_edge_create()`
- `backend/app/commands/handlers/body_set.py` — `handle_body_set()`
- `backend/app/commands/schemas.py` — `ObjectCreateParams`, `BodySetParams`, `EdgeCreateParams`

## Expected Output

- `backend/app/notion/models.py` — Extended with `ImportResult` dataclass (~40 lines)
- `backend/app/notion/executor.py` — New file, ~200-250 lines, `NotionImportExecutor` class with two-pass `execute()` method
- `backend/tests/test_notion_executor.py` — New file, ~300-400 lines, comprehensive unit tests covering all import paths
