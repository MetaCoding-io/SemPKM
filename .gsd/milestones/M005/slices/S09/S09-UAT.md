# S09: E2E Tests & Docs — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E tests)
- Why this mode is sufficient: E2E tests require the running Docker stack; docs are static markdown files verifiable by inspection

## Preconditions

- Docker test stack running: `docker compose up -d` (api, triplestore, frontend)
- Health check passes: `curl -s http://localhost:3911/health | jq .status` returns `"ok"`
- Basic PKM model installed (seed data present)
- At least one model install has occurred (for ops log entries)
- Node.js and Playwright installed: `cd e2e && npx playwright install`

## Smoke Test

Run `cd e2e && npx playwright test tests/24-tag-hierarchy/ tests/25-ops-log/ --reporter=list` — all 5 tests should pass.

## Test Cases

### 1. Hierarchical Tag Folder Expansion

1. Open workspace at `http://localhost:3911/browser/workspace`
2. Log in as owner
3. Switch explorer mode dropdown to "By Tag"
4. Wait for tag tree to load
5. Look for a tag with `/` in its name (e.g., `architecture/patterns` or any imported hierarchical tag)
6. Click the parent folder node (the part before `/`)
7. **Expected:** Sub-folder nodes appear nested inside the parent, with folder icons and indent. Each node shows a count badge reflecting the number of tagged objects.

### 2. Tag Count Badges

1. In the By Tag explorer (from test 1), locate a parent folder node
2. Note the count badge on the parent
3. Expand the folder and note count badges on each child
4. **Expected:** Parent badge shows a total ≥ sum of visible children's counts. Child badges show ≥ 1 each.

### 3. Tag Autocomplete in Edit Form

1. Open any object that has tags (or create one)
2. Click the "Edit" toggle button (`.mode-toggle`)
3. If the Properties section is collapsed, expand it
4. Find a tag input field (look for inputs inside `.tag-autocomplete-field`)
5. Clear the input and type a prefix of an existing tag (e.g., "arch")
6. **Expected:** A dropdown appears below the input with suggestion items containing the typed prefix. Clicking a suggestion fills the input with that tag value.

### 4. Operations Log Page Rendering

1. Navigate to Admin Portal → Operations Log (`/admin/ops-log`)
2. **Expected:** Page shows "Operations Log" heading, a filter dropdown, and a table with at least one row showing a type badge (e.g., `model.install`), description, timestamp, and status.

### 5. Operations Log Type Filter

1. On the Operations Log page, note the current number of rows
2. Select a specific activity type from the filter dropdown (e.g., "model.install")
3. Wait for htmx to refresh the table
4. **Expected:** Only rows matching the selected type are shown. All visible type badges show the same selected type.
5. Select "All activities" from the filter
6. **Expected:** All rows reappear (count matches or exceeds the filtered count)

### 6. Model Refresh Button and Ops Log Entry

1. Navigate to Admin Portal → Mental Models (`/admin/models`)
2. Find the "Basic PKM" model row
3. Locate the "Refresh" button in that row
4. Click "Refresh"
5. **Expected:** A confirmation dialog appears ("Are you sure you want to refresh...?")
6. Confirm the dialog
7. **Expected:** The page responds without a 500 error (success message or a known error message about JSON parsing is acceptable)
8. Navigate to Operations Log (`/admin/ops-log`)
9. **Expected:** A recent entry with type badge `model.refresh` appears in the log

### 7. User Guide: Hierarchical Tags Documentation

1. Open `docs/guide/04-workspace-interface.md`
2. Search for "Hierarchical Tags"
3. **Expected:** A subsection exists describing `/`-delimited tag nesting, folder icons, count badges, and lazy expansion behavior

### 8. User Guide: Tag Autocomplete Documentation

1. Open `docs/guide/05-working-with-objects.md`
2. Search for "Tag Autocomplete" or "autocomplete"
3. **Expected:** A subsection exists describing type-ahead suggestions, frequency ordering, and click-to-fill behavior

### 9. User Guide: Model Refresh Documentation

1. Open `docs/guide/10-managing-mental-models.md`
2. Search for "Refreshing Model Artifacts"
3. **Expected:** A section exists describing what refresh does, what it preserves (seed data, user data), what it replaces (ontology, shapes, views, rules), and the Admin Portal workflow

### 10. User Guide: Operations Log Documentation

1. Open `docs/guide/14-system-health-and-debugging.md`
2. Search for "Operations Log"
3. **Expected:** A subsection exists describing access, logged activities, type filter, pagination, and PROV-O vocabulary

## Edge Cases

### Empty Operations Log

1. On a fresh install with no model operations, navigate to `/admin/ops-log`
2. **Expected:** Page renders with "No operations logged yet" message instead of crashing

### Tag Autocomplete with No Matches

1. In an edit form tag input, type a string that matches no existing tags (e.g., "zzzzxxx")
2. **Expected:** Either no dropdown appears or the dropdown is empty — no error or crash

### Model Refresh with Malformed Model Archive

1. If the model archive on disk has JSON parsing issues (known for basic-pkm)
2. Click Refresh
3. **Expected:** An error message appears but the page does not crash. The models table remains intact.

### Ops Log Filter with No Matching Type

1. If a filter type is selected that has no matching entries
2. **Expected:** Table shows empty state or "no results" message, not a crash

## Failure Signals

- Any Playwright test failing in `tests/24-tag-hierarchy/` or `tests/25-ops-log/`
- Operations Log page returning 500 or blank
- Model Refresh button missing from the models table
- Tag autocomplete not triggering on type (check for missing htmx attributes on the input)
- Grep for documentation keywords returning empty results
- Missing `tagHierarchy` or `opsLog` keys in `SEL` object in `selectors.ts`

## Requirements Proved By This UAT

- TAG-04 — Hierarchical tag tree expansion with nested sub-folders (tests 1-2)
- TAG-05 — Tag autocomplete suggestions in edit forms (test 3)
- LOG-01 — Operations log rendering with filter and entries (tests 4-5)
- MIG-01 — Model refresh button, confirmation, and ops log entry (test 6)

## Not Proven By This UAT

- S01 query SQL→RDF migration — covered by existing `sparql-advanced.spec.ts`, not retested here
- PROV-O alignment (S06), Views Rethink (S07), VFS v2 Design (S08) — design docs, no runtime behavior
- Performance under load (tag tree with thousands of tags, ops log with thousands of entries)
- Cross-browser compatibility beyond Chromium and Firefox (Safari not tested)

## Notes for Tester

- E2E tests require the Docker stack running on port 3911. Start with `docker compose up -d`.
- Rate limiting: auth endpoint allows 5 requests/minute per IP. If tests fail with auth errors, wait 60 seconds and retry.
- The basic-pkm model has a known JSON parsing error when refreshing — the test accounts for this. A non-500 response (even with an error message) is a pass.
- Tag hierarchy tests create their own test data via the API — they don't depend on specific seed data having `/` tags.
- Pre-existing flaky test in `tests/20-tags/tag-explorer.spec.ts` test 1 is unrelated to this slice.
