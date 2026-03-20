# S01: Notion ZIP Scanner + Upload UI — UAT

**Milestone:** M027
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for scanner unit tests + live-runtime for upload/scan UI)
- Why this mode is sufficient: Scanner logic is proven by 31 unit tests covering all parsing behaviors. The UI flow requires a running Docker stack to verify upload, SSE progress, and results rendering.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least one user account exists (setup wizard completed)
- Logged in as an authenticated user

## Smoke Test

Navigate to `/browser/notion/import` — the page loads with a 7-step wizard bar (Upload step active) and an upload form with drag-and-drop area and file select button.

## Test Cases

### 1. Upload form renders at correct URL

1. Navigate to `/browser/notion/import`
2. **Expected:** Page shows "Import Notion Workspace" heading, 7-step wizard bar with "Upload" highlighted, upload form with drag-and-drop area and "Choose File" button

### 2. Upload a valid Notion ZIP and see scan results

1. Create a synthetic Notion ZIP with this structure:
   - `Projects abc1234567890abcdef1234567890ab/` folder containing `Projects abc1234567890abcdef1234567890ab.csv` with columns: Name, Status, Lead
   - `People def1234567890abcdef1234567890ab/` folder containing `People def1234567890abcdef1234567890ab.csv` with columns: Name, Email, Role
   - `standalone-note 1234567890abcdef1234567890ab.md` with markdown content
   - Ensure the "Lead" column in Projects has values that match names in the People database (for relation detection)
2. Upload the ZIP via the upload form
3. Click "Start Scan" when the scan trigger appears
4. **Expected:**
   - SSE progress bar fills during scan
   - Scan results show stat cards: 2 Databases, 1 Page, at least 1 Relation
   - Projects database table shows columns: Name (text/select), Status (select), Lead (relation)
   - People database table shows columns: Name (text/select), Email (text), Role (select)
   - Standalone pages section lists the markdown file
   - Detected relations section shows Projects → Lead → People with match ratio

### 3. Notion ID stripping works correctly

1. Upload a ZIP where folder names have 32-hex-char Notion IDs (e.g., `My Database abc1234567890abcdef1234567890ab`)
2. **Expected:** Database names in scan results show "My Database" (ID stripped), not the full folder name with hex suffix

### 4. BOM-encoded CSV parses correctly

1. Upload a ZIP containing a CSV file saved with UTF-8 BOM (bytes `\xEF\xBB\xBF` at start)
2. **Expected:** First column header parses correctly without the `\ufeff` BOM character prefix. Column names display cleanly in results.

### 5. Column type inference shows correct badges

1. Upload a ZIP with a database CSV containing columns of various types:
   - A column with values "Yes", "No" → should infer as **checkbox**
   - A column with values "https://example.com" → should infer as **url**
   - A column with values "42", "3.14" → should infer as **number**
   - A column with values "2024-01-15", "March 10, 2024" → should infer as **date**
   - A column with values "tag1, tag2", "tag3, tag4" → should infer as **multi_select**
   - A column with 5+ unique single values → should infer as **select**
2. **Expected:** Each column shows the correct inferred type badge in the database table

### 6. Discard import returns to upload form

1. After a successful scan, click "Discard Import"
2. **Expected:** Page returns to the initial upload form state. The uploaded ZIP data is cleaned up.

### 7. Sidebar navigation entry exists

1. Open the workspace at `/browser/`
2. Look at the left sidebar navigation
3. **Expected:** "Import Notion" link visible (near "Import Vault"), clicking it navigates to `/browser/notion/import`

### 8. Command palette entry exists

1. Press Ctrl+K to open the command palette
2. Type "Notion"
3. **Expected:** "Import > Notion" entry appears under Navigation section. Selecting it navigates to `/browser/notion/import`.

### 9. Scan results persist across page reloads

1. Upload a ZIP and complete a scan
2. Reload the page (`/browser/notion/import`)
3. **Expected:** The page shows scan results (not the upload form), because `scan_result.json` is persisted server-side

## Edge Cases

### Malformed CSV produces warning, not crash

1. Upload a ZIP with a database folder whose CSV has mismatched column counts (e.g., header has 3 columns, some rows have 4)
2. **Expected:** Scan completes. A "Warnings" section appears in scan results showing a warning for the malformed CSV file with its path. Other databases still parse correctly.

### Empty database (CSV with headers only)

1. Upload a ZIP with a database folder containing a CSV that has column headers but zero data rows
2. **Expected:** Database appears in results with 0 rows. Columns still show with type "text" (default for empty columns). No crash or warning.

### ZIP with no databases (only standalone pages)

1. Upload a ZIP containing only `.md` files and no database folders
2. **Expected:** Scan results show 0 Databases, N Pages (where N = number of .md files), 0 Relations. Standalone pages section lists all markdown files.

### Large ZIP with many databases

1. Upload a ZIP with 10+ database folders
2. **Expected:** All databases appear in scan results with correct column summaries. SSE progress events show incremental count during scan.

## Failure Signals

- Upload form doesn't render at `/browser/notion/import` → router not wired in main.py
- "Import Notion" missing from sidebar → `_sidebar.html` not updated
- SSE progress bar doesn't move during scan → broadcast.py not connected or stream endpoint broken
- Scan results show raw hex IDs in database names → `_strip_notion_id` regex not matching
- Column types all show "text" → `_infer_column_type` not being called or getting empty values
- No "Detected Relations" section → relation detection threshold too high or column values not matching titles
- Page crash or 500 error on upload → file handling or ZIP extraction failure

## Requirements Proved By This UAT

- NOTION-01 (partial) — Proves ZIP upload, CSV parsing, ID stripping, column type inference, relation detection, and scan results UI. Does not prove mapping, preview, or import execution (S02/S03).

## Not Proven By This UAT

- Type mapping (S02)
- Property mapping (S02)
- Relation mapping (S02)
- Preview of mapped objects (S02)
- Two-pass import execution (S03)
- Performance with 500+ page exports (S03)
- E2E Playwright tests (S04)

## Notes for Tester

- The "Continue to Type Mapping" button is intentionally disabled — it will be enabled by S02.
- To create synthetic test ZIPs, use the helper in `backend/tests/test_notion_scanner.py` — the `_make_zip` fixture creates properly structured Notion exports programmatically.
- Relation detection requires >80% of a column's non-empty values to match another database's row titles. If testing with small datasets, ensure the overlap is high enough.
- The scanner expects Notion's specific export structure: folder name matches CSV filename (both with 32-hex Notion ID suffix).
