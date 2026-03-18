# S05: OPML import + app settings — UAT

**Milestone:** M010
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: OPML import and settings are pure data transformations (XML→subscriptions, form→storage) with 41 unit tests proving all paths. Live-runtime E2E testing is deferred to S06 by design. Artifact-driven verification confirms parser correctness, route wiring, template rendering, and manifest validation.

## Preconditions

- Docker stack running (`docker compose up -d`)
- `rss-feeds` Mental Model installed
- `rss-reader` app installed and running (status: running in Admin > Applications)
- At least one feed already subscribed (for testing OPML duplicate detection)
- An OPML file prepared with 3+ feeds (at least 1 matching an existing subscription for duplicate test)

## Smoke Test

Upload a valid OPML file via the "Import OPML" button in the feed sidebar. Verify a success summary appears with correct created/duplicate counts.

## Test Cases

### 1. OPML import — happy path

1. Open RSS Reader page
2. Click "Import OPML" button in the feed sidebar
3. Select a valid OPML file containing 5 feeds (none previously subscribed)
4. Click "Import" submit button
5. **Expected:** Success summary div appears with text like "Imported 5 feeds: 5 created, 0 duplicates, 0 errors". The div has class `rss-success` and attributes `data-created="5"`, `data-duplicates="0"`, `data-errors="0"`. Feed sidebar refreshes to show new subscriptions.

### 2. OPML import — with duplicates

1. Subscribe to a feed URL manually (e.g. `https://example.com/feed.xml`)
2. Upload an OPML file containing that same URL plus 2 new feeds
3. **Expected:** Summary shows "3 feeds: 2 created, 1 duplicate, 0 errors". Only the 2 new feeds appear in sidebar; the existing subscription is unchanged.

### 3. OPML import — categories preserved as tags

1. Upload an OPML file with category folders:
   ```xml
   <outline text="Tech">
     <outline text="Example Blog" xmlUrl="https://example.com/feed" type="rss"/>
   </outline>
   ```
2. After import, open the newly created subscription in the object browser
3. **Expected:** The subscription has a `bpkm:tags` value of "Tech". For nested categories like `Tech/AI`, the tag is `Tech/AI` (slash-delimited).

### 4. OPML import — empty file error

1. Click "Import OPML" and upload an empty file (0 bytes)
2. **Expected:** Error div appears with class `rss-error` and text indicating the file is empty or invalid. No subscriptions created.

### 5. OPML import — invalid XML error

1. Create a text file with content `<not valid xml` and rename to `.opml`
2. Upload it via Import OPML
3. **Expected:** Error div with `rss-error` class appears. No crash, no subscriptions created.

### 6. OPML import — no file selected

1. Click "Import OPML" to open the dialog
2. Click "Import" without selecting a file
3. **Expected:** Error div appears with message like "No file uploaded". No crash.

### 7. Settings — view defaults

1. Open RSS Reader page
2. Click the gear icon in the feed sidebar header
3. **Expected:** Settings form appears in the reading pane with "Articles per page" set to 50 and "Mark read on open" checked (both defaults from manifest).

### 8. Settings — save and persist

1. Change "Articles per page" to 25
2. Uncheck "Mark read on open"
3. Click Save
4. **Expected:** Success message "Settings saved" appears with `rss-success` class
5. Navigate away from settings (click a feed)
6. Click gear icon again to reopen settings
7. **Expected:** "Articles per page" shows 25 and "Mark read on open" is unchecked — values persisted.

### 9. Settings — validation clamping

1. Open settings
2. Enter 5 in "Articles per page" (below minimum of 10)
3. Click Save
4. Reopen settings
5. **Expected:** Value shows 10 (clamped to minimum). Similarly, entering 500 would be clamped to 200.

### 10. Settings — manifest validation

1. Run: `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(f'Settings: {len(m.settings)} defined, permissions.settings={m.permissions.settings}')"` 
2. **Expected:** Output shows `Settings: 2 defined, permissions.settings=True`

## Edge Cases

### OPML with no feeds (only category folders)

1. Upload an OPML file with only `<outline text="Category">` elements (no `xmlUrl` attributes)
2. **Expected:** Error div with message like "No feeds found in OPML file". Zero subscriptions created.

### OPML with encoding declaration

1. Upload an OPML file starting with `<?xml version="1.0" encoding="UTF-8"?>` and containing UTF-8 feed titles with special characters (é, ñ, ü)
2. **Expected:** Feeds imported with correct Unicode titles preserved.

### Settings form with non-numeric input

1. Open settings and type "abc" into "Articles per page"
2. Click Save
3. **Expected:** Value is clamped to default (50) since "abc" is not a valid integer. No crash.

### Large OPML file (50+ feeds)

1. Upload an OPML file with 50+ feeds
2. **Expected:** All feeds processed (may take several seconds). Summary shows correct counts. No timeout or crash.

## Failure Signals

- `<div class="rss-error">` appearing when it shouldn't (on valid OPML upload)
- Import summary showing `data-errors` > 0 when all feeds should succeed
- Settings not persisting after save (values revert to defaults on reload)
- Gear icon or "Import OPML" button missing from feed sidebar
- Python traceback in app logs during OPML import or settings save
- manifest.yaml failing `parse_app_manifest()` validation

## Requirements Proved By This UAT

- RSS-05 — OPML import for feed subscriptions: upload creates subscriptions, categories preserved as tags, error handling for invalid files, duplicate detection

## Not Proven By This UAT

- RSS-05 E2E browser automation — deferred to S06 Playwright spec
- Settings effect on reader behavior — articlesPerPage and markReadOnOpen are stored but their influence on article rendering is not yet wired (reader templates would need to read these settings)
- OPML export — only import is implemented

## Notes for Tester

- The fastest way to test OPML import is with a sample OPML file. Most RSS reader apps (Feedly, Inoreader, NewsBlur) can export OPML files you can use.
- Settings values are stored via the SDK's SettingsClient (`ctx.settings.get/set`). If the app process restarts, settings should still persist (they're in the state graph).
- The 41 pytest tests are the primary verification surface. Run `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py tests/test_rss_settings.py -v` to verify all paths without needing a running Docker stack.
