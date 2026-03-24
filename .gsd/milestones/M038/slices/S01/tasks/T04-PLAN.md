---
estimated_steps: 4
estimated_files: 7
skills_used: []
---

# T04: App UI templates + unit tests

**Slice:** S01 — Mental Model + Podcast Sources
**Milestone:** M038

## Description

Create the Jinja2 HTML templates for the Media Scheduler app page and write comprehensive unit tests covering the pure functions, manifest validation, and poll task logic. This closes the slice: after this task, the app has a visible UI and verified behavior.

Templates follow the same htmx-driven fragment pattern as `apps/rss-reader/frontend/templates/`:
- `main.html` — full app page layout with sidebar (sources) and main content (items)
- `sources-list.html` — htmx fragment listing all media sources with unread counts
- `items-list.html` — htmx fragment showing discovered episodes/items with metadata
- `add-source.html` — form fragment for adding a podcast RSS feed

Tests follow the `backend/tests/test_rss_settings.py` pattern:
- Import the app module via `importlib.util.spec_from_file_location` to avoid package path conflicts
- Mock feedparser at module level before `exec_module`
- Test pure functions (IRI minting, entry conversion, duration parsing) with real assertions
- Test manifest validation via `parse_app_manifest()`
- Test poll task logic with mocked SDK context

## Steps

1. Replace the placeholder `apps/media-scheduler/frontend/templates/main.html` with the full app page template:
   - Two-column layout: left sidebar (sources list) + right main area (items list)
   - Sources sidebar loads via `hx-get="/app/media-scheduler/_fragments/sources" hx-trigger="load"` (note: htmx URLs must use the `/app/media-scheduler/` proxy prefix per KNOWLEDGE.md "App template htmx URLs must use proxy prefix")
   - Items area loads via `hx-get="/app/media-scheduler/_fragments/items" hx-trigger="load"`
   - "Add Source" button opens inline form
   - Use standard SemPKM workspace CSS classes where possible, app-specific classes prefixed with `ms-`

2. Create the fragment templates:
   - `sources-list.html` — iterates over `sources` list, renders each with title, sourceType badge, lastPolled date, errorCount indicator. Each source row has a click handler to filter items by source (hx-get with source_iri param). Remove button per source.
   - `items-list.html` — iterates over `items` list, renders each with title, published date, duration (formatted mm:ss), source name. Status badge (queued/completed/skipped). Items are clickable (future: open in object browser).
   - `add-source.html` — form with feed_url text input and submit button. Posts to `/app/media-scheduler/_fragments/sources/add-podcast`. Success/error response swapped into a status area. Emits `sourcesChanged` event on success to refresh sidebar.

3. Create `apps/media-scheduler/frontend/static/styles.css` with basic styling for the app layout: `.ms-container` (flex row), `.ms-sidebar` (250px fixed, scrollable), `.ms-main` (flex 1), `.ms-source-item`, `.ms-item-row`, `.ms-status-badge`, `.ms-add-form`. Keep it minimal — a functional layout, not polished design. Use CSS variables from the workspace theme (`var(--color-bg)`, `var(--color-text)`, `var(--color-border)`, etc.).

4. Create `backend/tests/test_media_scheduler.py` with comprehensive tests:
   - **Import pattern**: use `importlib.util.spec_from_file_location("media_scheduler_app", "apps/media-scheduler/app.py")` with `sys.modules["feedparser"] = MagicMock()` pre-patched
   - **Manifest tests**: validate manifest via `parse_app_manifest()`, assert appId, task count, task id, permissions
   - **IRI minting tests**: `mint_source_iri()` is deterministic (same input → same output), different inputs → different IRIs; `mint_item_iri()` same pattern
   - **entry_to_media_item tests**: map a feedparser entry dict with title, link, id, summary, published_parsed → verify output has correct type IRI, dcterms:title, ms:externalId, ms:status="queued", ms:mediaSource set
   - **Enclosure extraction test**: entry with `enclosures: [{"href": "https://example.com/ep.mp3", "type": "audio/mpeg"}]` → ms:enclosureUrl set to the href
   - **Duration parsing test**: `_parse_itunes_duration("1:23:45")` → 5025 seconds, `"45:30"` → 2730, `"3600"` → 3600, `""` → None, `"invalid"` → None
   - **Dedup test**: mock `get_existing_item_iris()` returning a set of IRIs, verify that `entry_to_media_item()` output with matching IRI would be filtered out (test the filtering logic, not the function itself since filtering happens in poll_sources)
   - **subscribe_podcast test**: mock ctx with graph.query returning empty (no existing sub), verify commands.execute called with correct object.create params; mock returning existing sub → verify "duplicate" status returned
   - **Poll task test**: mock ctx with graph returning one podcast source, mock fetch_feed returning feed content, verify bulk creation called with correct item params

## Must-Haves

- [ ] `main.html` renders a two-column layout with htmx-loading sources and items
- [ ] All htmx URLs use `/app/media-scheduler/` proxy prefix
- [ ] `sources-list.html` and `items-list.html` iterate over template variables correctly
- [ ] `test_media_scheduler.py` has ≥10 test cases covering all pure functions
- [ ] All tests pass: `cd backend && python -m pytest tests/test_media_scheduler.py -v`
- [ ] CSS uses workspace theme variables, not hardcoded colors

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass (≥10 tests)
- `python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler'"` — manifest still validates after all changes

## Inputs

- `apps/media-scheduler/app.py` — app module with routes and task handler to test
- `apps/media-scheduler/services/podcast_service.py` — pure functions to test
- `apps/media-scheduler/manifest.yaml` — manifest to validate in tests
- `apps/rss-reader/frontend/templates/reader.html` — reference pattern for app page layout
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — reference pattern for sidebar list fragment
- `backend/tests/test_rss_settings.py` — reference pattern for importlib-based app module testing

## Expected Output

- `apps/media-scheduler/frontend/templates/main.html` — full app page template
- `apps/media-scheduler/frontend/templates/sources-list.html` — sources list fragment
- `apps/media-scheduler/frontend/templates/items-list.html` — items list fragment
- `apps/media-scheduler/frontend/templates/add-source.html` — add source form fragment
- `apps/media-scheduler/frontend/static/styles.css` — app-specific CSS
- `backend/tests/test_media_scheduler.py` — comprehensive unit test suite
