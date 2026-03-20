# S03: Two-Pass Import Executor + Full Flow — UAT

**Milestone:** M027
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: The executor is tested via 20 unit tests with mocked EventStore/TriplestoreClient. Router endpoints and templates are verified via AST parsing and Jinja2 compilation. Full live-runtime verification (Docker stack import) is deferred to S04's E2E Playwright test, which is the right place for integration testing.

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d` from main tree)
- At least one Mental Model installed (basic-pkm)
- A synthetic Notion export ZIP file available with:
  - At least 2 CSV databases with rows
  - At least 1 cross-database relation column
  - At least 1 standalone markdown page
  - At least 1 body markdown file with Notion ID in filename

## Smoke Test

Navigate to Admin > Import > Notion in the workspace. The upload page should render. Upload a Notion ZIP, complete scan/mapping/preview, and click Import. The progress bar should animate and a summary should appear with created/edges/skipped counts.

## Test Cases

### 1. Import button is enabled on preview page

1. Upload a Notion ZIP and complete scan → type mapping → property mapping → relation mapping steps
2. Reach the Preview step (step 6)
3. **Expected:** The "Import" button is visible, clickable, and has no `disabled` attribute or "Coming in next update" tooltip

### 2. Pass 1 creates objects from CSV rows with mapped properties

1. Upload a ZIP with a "Tasks" database containing columns: Name, Status, Priority
2. Map "Tasks" → bpkm:Task type, map Status → bpkm:taskStatus, Priority → bpkm:taskPriority
3. Click Import
4. **Expected:** Objects are created with correct type and mapped property values. The summary shows `Created: N` matching the number of non-empty CSV rows.

### 3. Body files matched to objects by stripped Notion ID

1. Upload a ZIP where the database folder contains markdown files named like `My Task abc123def456789012345678901234.md`
2. The CSV has a row with title "My Task"
3. Click Import
4. **Expected:** The object "My Task" has its body set to the content of the markdown file. The Notion ID suffix is stripped for matching.

### 4. Pass 2 resolves cross-database relations as edges

1. Upload a ZIP with "Tasks" database and "Projects" database
2. "Tasks" has a column "Project" whose values match titles in "Projects"
3. Map both databases to types, map the "Project" relation column to a predicate (e.g., dcterms:isPartOf)
4. Click Import
5. **Expected:** Summary shows `Edges: N` where N matches the number of resolved relation values. Each task has an edge pointing to the correct project object.

### 5. Multi-value relation cells split and resolved independently

1. Upload a ZIP where a relation column contains comma-separated values: "Project A, Project B"
2. Both "Project A" and "Project B" exist in the target database
3. Click Import
4. **Expected:** Two separate edges are created — one for each target. Summary edges count reflects both.

### 6. Unresolved relations reported in summary

1. Upload a ZIP where a relation column references "Nonexistent Project"
2. No database row has that title
3. Click Import
4. **Expected:** Summary shows an "Unresolved Relations" section with the source object, relation column, and "Nonexistent Project" as the unmatched value.

### 7. Standalone pages imported when type configured

1. Upload a ZIP with standalone markdown files outside any database folder
2. During type mapping, set the standalone page type to bpkm:Note (or any type)
3. Click Import
4. **Expected:** Standalone pages appear as objects of the configured type with their markdown content as body. Summary `Created` count includes standalone pages.

### 8. SSE progress events during import

1. Open browser dev tools Network tab, filter to EventSource
2. Click Import on the preview page
3. **Expected:** EventSource connects to `/browser/notion/{import_id}/execute/stream`. Events include `import_progress` (with phase "objects" then "edges"), then `import_complete` with the full result dict.

### 9. Import summary renders with all sections

1. Complete an import that has some created objects, some edges, some skipped rows (empty titles), and at least one unresolved relation
2. **Expected:** Summary page shows:
   - Stat cards: Created (green if >0), Edges, Skipped (yellow if >0), Duration
   - Collapsible "Unresolved Relations" section with 3-column table
   - Action buttons: Browse Imported Objects, Import More, Discard Files

### 10. Per-row error isolation

1. Upload a ZIP where one CSV row would cause a creation error (e.g., invalid data that triggers an exception in handle_object_create)
2. Other rows are valid
3. Click Import
4. **Expected:** Valid rows are imported successfully. The failing row appears in the Errors section of the summary. The import doesn't abort.

## Edge Cases

### Empty CSV database (all rows have empty titles)

1. Upload a ZIP where a database CSV has rows but all title columns are empty
2. Click Import
3. **Expected:** All rows skipped. Summary shows `Skipped: N`, `Created: 0` for that database. No errors.

### SSE race condition — import completes before client connects

1. Import a very small dataset (1-2 rows) — import may complete before the SSE EventSource establishes
2. **Expected:** The SSE stream endpoint detects the completed import_result.json and sends a single `import_complete` event with the result. Summary page renders correctly.

### Unmapped database skipped entirely

1. Upload a ZIP with multiple databases, map only some of them (leave others with "Skip" in type mapping)
2. Click Import
3. **Expected:** Only mapped databases are imported. Unmapped databases do not produce objects, edges, or errors.

## Failure Signals

- Import button still shows "disabled" or "Coming in next update" → T02 preview.html edit was not applied
- 500 error on POST execute → router endpoint not registered or executor import fails
- SSE stream never connects → stream endpoint URL mismatch or broadcast key mismatch
- Summary page never loads after import → `import_complete` SSE event not fired, or htmx ajax target mismatch
- Objects created but no edges → Pass 2 not executing, or relation mappings not loaded from mapping_config.json
- All relations unresolved → title_index not populated during Pass 1, or title matching is case-sensitive when it shouldn't be

## Requirements Proved By This UAT

- NOTION-01 — ZIP import wizard with full flow from upload through import summary (integration proof deferred to S04 E2E)
- NOTION-03 — Relation→edge resolution via title matching with unresolved relation reporting

## Not Proven By This UAT

- Live runtime integration test against Docker stack (deferred to S04 E2E Playwright test)
- Performance with 500+ page exports (operational verification deferred to S04)
- Command palette entry point (not part of S03 scope)
- User guide documentation (S04)

## Notes for Tester

- The edge progress bar shows 100% throughout because total equals current (total unknown upfront). This is cosmetic, not a bug.
- Body file matching is case-insensitive but depends on the `_strip_notion_id` regex matching exactly 32 hex chars. Fixture filenames must follow Notion's naming convention.
- The "Discard Files" button removes extracted ZIP contents but leaves imported objects in the triplestore — this is by design.
- If testing against a fresh stack, install basic-pkm model first (the type mapper needs available types).
