# S03: VFS Composable Chains & Filename Templates — UAT

**Milestone:** M007
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All features are testable via unit tests (98 passing) and browser interaction with the mount form. Chain nesting and filename templates are deterministic transformations — no subjective UX judgment needed.

## Preconditions

- Docker stack running (`docker compose up -d`)
- Backend accessible at localhost
- At least one Mental Model installed (e.g., basic-pkm) with some objects created
- At least one tag applied to an object (for by-tag chain testing)

## Smoke Test

Open Settings → VFS Mounts → Create Mount. Verify the strategy dropdown has an "+ Add level" button next to it and a filename template text input below the strategy section.

## Test Cases

### 1. Filename template with {date}-{title}

1. Create a new VFS mount: name "Template Test", strategy "flat"
2. In the filename template field, type `{date}-{title}`
3. Save the mount
4. Open Settings → VFS Mounts → click Edit on "Template Test"
5. **Expected:** Filename template field shows `{date}-{title}`
6. Open the mount in the VFS browser or preview
7. **Expected:** Files are named like `2024-01-15-my-note.md` (date prefix + slugified title). Objects without `dcterms:created` show `undated-my-note.md`.

### 2. Filename template with {type}-{title}

1. Create a mount with filename template `{type}-{title}`, strategy "flat"
2. Preview or browse the mount
3. **Expected:** Files named like `note-my-first-note.md` (type label slugified + title slugified)

### 3. Filename template with {id} variable

1. Create a mount with filename template `{title}-{id}`
2. Preview or browse the mount
3. **Expected:** Files named like `my-note-a1b2c3d4.md` (8-character hex suffix from SHA-256 of IRI)

### 4. No filename template (backward compat)

1. Create a mount with no filename template (field empty), strategy "flat"
2. Preview or browse the mount
3. **Expected:** Files named with just the slugified label (e.g., `my-note.md`) — same behavior as before S03

### 5. Two-level strategy chain (by-tag → by-date)

1. Create a new VFS mount: name "Chain Test"
2. Select strategy "by-tag"
3. Click "+ Add level"
4. In the new chain level dropdown, select "by-date"
5. Set the group_by_property field (should be visible since by-tag is in chain) to `schema:keywords`
6. Save the mount
7. **Expected:** Mount saves successfully
8. Open Settings → VFS Mounts → click Edit on "Chain Test"
9. **Expected:** First strategy shows "by-tag", chain level shows "by-date"
10. Expand the mount in the explorer sidebar
11. **Expected:** Top level shows tag folders. Expanding a tag folder shows year/month date folders. Expanding a month folder shows the actual objects.

### 6. Preset chain combo "Tag → Date"

1. Open the mount creation form
2. Click the "Tag → Date" preset button
3. **Expected:** First strategy set to "by-tag", one chain level added with "by-date"
4. Both group_by_property and date_property fields should be visible

### 7. Three-level chain (maximum)

1. Create a mount with strategy "by-type"
2. Click "+ Add level" → select "by-tag"
3. Click "+ Add level" → select "by-date"
4. **Expected:** "+ Add level" button is hidden (max 3 total reached)
5. Save the mount
6. Edit the mount
7. **Expected:** All 3 levels restored correctly

### 8. Chain builder — remove level

1. Open mount creation form
2. Add a chain level (click "+ Add level")
3. Click the × button on the added chain level row
4. **Expected:** Chain level removed, "+ Add level" button reappears

### 9. Flat strategy hides add-level button

1. Open mount creation form
2. Select strategy "flat" from the first dropdown
3. **Expected:** "+ Add level" button is hidden (flat cannot be chained)
4. Select strategy "by-type"
5. **Expected:** "+ Add level" button appears

### 10. collectFormData sends correct shape

1. Open browser dev tools → Network tab
2. Create a mount with single strategy "by-date"
3. Inspect the POST request body
4. **Expected:** `strategy` is a string `"by-date"` (not an array)
5. Create another mount with chain "by-tag" + "by-date"
6. Inspect the POST request body
7. **Expected:** `strategy` is an array `["by-tag", "by-date"]`

### 11. Preview with chain strategy

1. Create a mount with strategy chain ["by-tag", "by-date"]
2. Click the Preview button (if available in UI)
3. **Expected:** Preview shows nested tree: tag names at top level, year/month folders nested inside each tag

### 12. Chain + filename template combined

1. Create a mount with strategy chain ["by-type", "by-tag"] and filename template `{date}-{title}`
2. Browse or preview the mount
3. **Expected:** Type folders at top level → tag folders inside → files with date-prefixed names

## Edge Cases

### Chain depth > 3 rejected

1. Via API (curl or dev tools): POST to mount create with `strategy: ["by-type", "by-tag", "by-date", "flat"]`
2. **Expected:** HTTP 422 with validation error mentioning "Strategy chain too long (4 levels). Maximum is 3 levels."

### Invalid strategy in chain rejected

1. Via API: POST with `strategy: ["by-type", "bogus"]`
2. **Expected:** HTTP 422 with validation error mentioning invalid strategy name

### Unknown template variable

1. Create a mount with filename template `{bogus}-{title}`
2. Browse or preview the mount
3. **Expected:** Files named like `bogus-my-note.md` — the `{bogus}` passes through as literal text and gets slugified (curly braces removed)

### Empty filename template

1. Create a mount with filename template field left empty
2. **Expected:** Behaves identically to no-template mounts. `filename_template` not included in form submission.

## Failure Signals

- "+ Add level" button never appears → chain builder JS not loaded or `updateAddChainButton()` not called from `initMountForm()`
- Chain levels not restored on edit → `populateEditForm()` not reading `mount.strategy_chain` array
- Files not date-prefixed when template set → `_build_file_map_from_bindings()` not receiving `filename_template` parameter, or `dcterms:created` OPTIONAL missing from strategy query
- Explorer shows flat list instead of nested folders for chain mount → `mount_children` not receiving `depth`/`parent_values` params, or `mount_tree_folders.html` not rendering chain-aware hx-get URLs
- Preset buttons do nothing → `applyChainPreset()` not exposed on `window`, or chain container ID mismatch

## Requirements Proved By This UAT

- VFS-11 — Tests 5, 6, 7, 8, 9, 10, 11 prove composable strategy chains with UI, API, and explorer integration
- VFS-12 — Tests 1, 2, 3, 4 prove filename templates with variable expansion and backward compatibility

## Not Proven By This UAT

- WebDAV client access (macOS Finder, Windows Explorer) to chain-structured mounts — would require OS-level mount testing
- Performance under large datasets (hundreds of objects per chain level) — would require load testing
- E2E Playwright tests — not written for S03 (standing requirement deferred to coverage slice)

## Notes for Tester

- The by-tag chain test (Test 5) requires at least one object with a tag value. If no tags exist, the top-level folder list will be empty.
- The date folders in a by-tag → by-date chain will only appear if objects have `dcterms:created` values. Otherwise you'll see an "undated" folder or empty expansion.
- Chain by-type narrowing uses local name matching (D123) — type folder names are the label portion of the type IRI, not the full IRI.
- The scope dropdown's "Custom SPARQL..." showing "all" when editing is a pre-existing issue, not from S03.
