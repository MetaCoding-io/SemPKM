# S04: Workspace contributions + custom renderer

**Goal:** Wire RSS Reader into the workspace integration layer: right pane "Related Articles" section, custom `rss:Article` read renderer in the object browser, "Mark All as Read" command palette entry, and fix the "Open RSS Reader" navigate action to open as a dockview tab instead of navigating away from the workspace SPA.

**Demo:** Open any object in the object browser → right pane shows "RELATED ARTICLES" section (from RSS Reader). Open an `rss:Article` from the object browser → see clean reader layout (not default SHACL form). Press Ctrl+K → "Mark All as Read" and "Open RSS Reader" commands work correctly (mark-all-read runs in-place, Open RSS Reader opens a dockview tab).

## Must-Haves

- `manifest.yaml` updated with `rightPane` contribution, `objectRenderers` declaration, and `mark-all-read` command palette entry
- `/_fragments/related-articles` route handler + template — shows articles sharing tags or from same feed as focused object
- `/_fragments/article-read-renderer` route handler + template — custom read renderer for Article objects (reuses reading pane pattern, no fire-and-forget mark-read)
- `mark-all-read` command palette entry works: detects command palette context (HX-Target header) and returns confirmation message instead of sidebar HTML
- `commands_list()` API enhanced to include `appId`/`pageId` for navigate commands matching app pages
- JS `_loadAppCommandEntries()` fixed to call `openAppPageTab()` for navigate commands with `appId`
- ≥15 new unit tests covering both new fragment handlers and the navigate action fix

## Proof Level

- This slice proves: contract (mocked SDK for fragments, TestClient for API)
- Real runtime required: no (unit tests with mocked context)
- Human/UAT required: no (deferred to S06 E2E)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` — S03's 43 tests + new S04 tests all pass
- `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — existing tests + new navigate fix tests all pass
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` — valid YAML
- `objectRenderers[0].type` is the full IRI `urn:sempkm:model:rss-feeds:Article` in manifest
- Navigate command JSON includes `appId` and `pageId` when path matches an app page
- Grep for `rss-error` in `related-articles.html` and `article-read-renderer.html` confirms error-state HTML is rendered on SPARQL failure
- `mark_all_read_route()` returns `rss-success` class when `HX-Target` is `#modal-container` (failure-path: returns `rss-error` on exception)

## Observability / Diagnostics

- Runtime signals: SPARQL errors in related-articles and renderer fragments logged as warnings, rendered as `<div class="rss-error">` fragments
- Inspection surfaces: `data-article-iri` attributes on related articles template elements; HX-Trigger headers on mark-all-read response
- Failure visibility: right pane and renderer fragments degrade to error messages on SPARQL failure; empty states for no-results
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S02's `FeedService` (not imported — fragments query triplestore directly); S03's `_sparql_bool()`, `_format_date()`, `_sparql_int()` helpers in `app.py`; S03's star-button template pattern; platform's `right_pane_sections.html` rendering; platform's `_get_renderer_override()` dispatch; platform's `commands_list()` API
- New wiring introduced: manifest `rightPane` → platform renders section via `right_pane_sections.html`; manifest `objectRenderers` → platform's `_get_renderer_override()` dispatches to app fragment; manifest `commandPalette` mark-all-read entry → command palette POST; `commands_list()` navigate entries include `appId`/`pageId` → JS opens dockview tab
- What remains before the milestone is truly usable end-to-end: S05 (OPML import + settings), S06 (E2E tests + user guide)

## Tasks

- [ ] **T01: Add right pane, custom renderer, and mark-all-read command to manifest + app** `est:45m`
  - Why: Core slice deliverables — these are the workspace contributions that wire the RSS Reader into the platform's right pane, object browser, and command palette
  - Files: `apps/rss-reader/manifest.yaml`, `apps/rss-reader/app.py`, `apps/rss-reader/frontend/templates/related-articles.html`, `apps/rss-reader/frontend/templates/article-read-renderer.html`
  - Do: (1) Add `rightPane`, `objectRenderers`, and `mark-all-read` command palette entry to manifest. (2) Add `/_fragments/related-articles` route that queries articles sharing tags or same feed source as focused object, renders template. (3) Add `/_fragments/article-read-renderer` route that reuses reading pane SPARQL pattern but without fire-and-forget mark-read. (4) Update `mark_all_read_route()` to detect command palette context via HX-Target header and return confirmation message.
  - Verify: `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` and `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"`
  - Done when: Both new route handlers exist, manifest has all 3 new contributions, mark-all-read returns confirmation when HX-Target is `#modal-container`

- [ ] **T02: Fix navigate action to open app pages as dockview tabs** `est:20m`
  - Why: "Open RSS Reader" command palette entry currently does `window.location.href = path` which navigates away from the workspace SPA. All apps with navigate commands need this fix.
  - Files: `backend/app/browser/apps.py`, `frontend/static/js/workspace.js`
  - Do: (1) In `commands_list()`, for navigate commands whose path matches an app page, add `appId` and `pageId` to the JSON. (2) In `_loadAppCommandEntries()`, when `cmd.appId` exists on a navigate command, call `openAppPageTab(cmd.appId, cmd.pageId, cmd.title)` instead of `window.location.href`.
  - Verify: Existing `test_app_views_commands.py` tests still pass; navigate command JSON structure correct
  - Done when: Navigate entries for app pages include `appId`/`pageId` in API response; JS handler dispatches to `openAppPageTab` when those fields are present

- [ ] **T03: Unit tests for S04 fragments and navigate fix** `est:30m`
  - Why: Contract verification for all new code — two new app fragment handlers, mark-all-read context detection, and navigate command enrichment
  - Files: `backend/tests/test_rss_reader_ui.py`, `backend/tests/test_app_views_commands.py`
  - Do: Add tests for related-articles handler (SPARQL structure, template args, empty state, SPARQL error), article-read-renderer handler (SPARQL query, template args, missing IRI, article not found, star button inclusion), mark-all-read command palette context detection, and navigate command with appId/pageId enrichment. Follow S03's `_make_mock_request()` pattern.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py tests/test_app_views_commands.py -v`
  - Done when: ≥15 new tests pass; zero regressions on S03's 43 tests and existing command tests

## Files Likely Touched

- `apps/rss-reader/manifest.yaml`
- `apps/rss-reader/app.py`
- `apps/rss-reader/frontend/templates/related-articles.html`
- `apps/rss-reader/frontend/templates/article-read-renderer.html`
- `backend/app/browser/apps.py`
- `frontend/static/js/workspace.js`
- `backend/tests/test_rss_reader_ui.py`
- `backend/tests/test_app_views_commands.py`
