# S05: OPML import + app settings

**Goal:** User uploads an OPML file to bulk-create feed subscriptions, and configures reader preferences via an app settings page.
**Demo:** User clicks "Import OPML" in the feed sidebar, uploads an OPML file containing 5+ feeds, sees a summary showing "N created, M duplicates". User clicks a settings gear icon, changes `markReadOnOpen` toggle and `articlesPerPage` number, saves, and sees values persist on page reload.

## Must-Haves

- `parse_opml(xml_bytes)` pure function parses OPML XML into feed dicts with url, title, category
- OPML category folders preserved as category field on feed entries
- Import route accepts multipart file upload, calls `subscribe()` per feed, returns HTML summary
- Invalid XML / empty file / no file upload produce user-friendly error messages
- Manifest declares `permissions.settings: true` and `settings:[]` with `articlesPerPage` and `markReadOnOpen`
- Settings route reads/writes via `ctx.settings.get()`/`ctx.settings.set()`
- Settings and OPML import UI accessible from feed sidebar

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` — ≥20 tests pass (parser pure function + route mock tests)
- `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v` — ≥8 tests pass (settings route + manifest tests)
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/opml_parser.py').read())"` — syntax OK
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — zero S01/S02 regressions
- `cd backend && .venv/bin/python -c "from apps.rss_reader.services.opml_parser import parse_opml; r=parse_opml(b'<not xml'); assert r==[], f'Expected empty list on invalid XML, got {r}'"` — invalid XML returns `[]` (failure-path check)

## Observability / Diagnostics

- **OPML parse errors:** `parse_opml()` logs a warning via `logging.getLogger(__name__).warning(...)` on invalid XML or missing `<body>`, including the exception type and message. The function never raises — it returns `[]` on any parse failure.
- **Import route summary:** The POST import-opml route returns an HTML fragment with structured counts: `data-created`, `data-duplicates`, `data-errors` attributes on the summary div, making them inspectable via browser automation or curl.
- **Settings round-trip:** GET settings route returns current values in form field `value` attributes — inspectable without JS. POST returns a success/error feedback div with CSS class `rss-success` or `rss-error`.
- **Failure visibility:** All error paths (invalid XML, empty file, no file, settings save failure) return user-visible error messages in `<div class="rss-error">` — never silent failures.
- **Redaction:** No secrets or PII are involved in OPML import or settings. Feed URLs are logged/displayed as-is.

## Integration Closure

- Upstream surfaces consumed: `FeedService.subscribe(ctx, feed_url, title)` from S02's `services/feed_service.py`; `SettingsClient.get()/set()` from SDK; `AppSettingDef` schema from `backend/app/apps/manifest.py`
- New wiring introduced: OPML import route + template in app.py; settings route + template in app.py; `permissions.settings: true` and `settings:[]` in manifest.yaml
- What remains before the milestone is truly usable end-to-end: S06 E2E tests + user guide

## Tasks

- [x] **T01: Create OPML parser pure function with comprehensive tests** `est:30m`
  - Why: The OPML parser is a pure data transformer (XML bytes → list of feed dicts) with zero SDK dependency. Building and testing it first gives T02 a proven foundation to wire into routes.
  - Files: `apps/rss-reader/services/opml_parser.py`, `backend/tests/test_opml_import.py`
  - Do: Create `parse_opml(xml_content: bytes) -> list[dict]` using stdlib `xml.etree.ElementTree`. Walk tree tracking parent category context. Handle: flat feeds (no categories), nested category folders (2+ levels → `/`-delimited), missing titles (fall back to URL), empty body, invalid XML (return empty list), encoding declarations. Each returned dict has keys: `url` (xmlUrl), `title` (text/title attr or URL fallback), `html_url` (htmlUrl or None), `category` (parent outline text or None). Write ≥12 pure function tests in `test_opml_import.py` using `importlib.util.spec_from_file_location` pattern.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v -k "test_parse"` — ≥12 tests pass
  - Done when: `parse_opml()` handles all documented edge cases and all parser tests pass

- [x] **T02: Wire OPML import route + template into app with integration tests** `est:45m`
  - Why: This delivers requirement RSS-05 — user uploads an OPML file and feed subscriptions are created. Wires T01's parser into the app's route/template system.
  - Files: `apps/rss-reader/app.py`, `apps/rss-reader/frontend/templates/opml-import.html`, `apps/rss-reader/frontend/templates/feed-sidebar.html`, `backend/tests/test_opml_import.py`
  - Do: (1) Add `try/except ImportError` fallback import for `services.opml_parser` in app.py (same pattern as feed_service). (2) Create POST `/_fragments/import-opml` route: read multipart file via `request.form()`, call `parse_opml()`, call `subscribe(ctx, entry["url"], entry["title"])` sequentially for each feed, tally created/duplicate/error counts, return HTML summary fragment with CSS status classes. Pass category to subscribe if present (as optional tag — store via `object.patch` adding `bpkm:tags`). Handle: no file uploaded, empty file, invalid XML — all return rss-error div. Emit `HX-Trigger: feedsChanged` on success. (3) Create `opml-import.html` template with file input (`accept=".opml,.xml"`), submit button, and result target div. (4) Add "Import OPML" button to `feed-sidebar.html` below the Subscribe button, using `hx-get="/_fragments/opml-import-dialog"` to load the form. (5) Add GET `/_fragments/opml-import-dialog` route that renders the template. (6) Add ≥8 route tests to `test_opml_import.py`: successful import, some duplicates, empty file, invalid XML, no file uploaded.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` — ≥20 tests total pass; `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
  - Done when: Import route creates subscriptions from OPML, returns correct HTML summary, error cases handled gracefully, all tests pass

- [x] **T03: Add settings manifest declarations, route, template, and tests** `est:45m`
  - Why: Enables user-configurable reader preferences. The manifest must declare settings with `permissions.settings: true` for the platform to validate and the SDK to expose `ctx.settings`. Completes the app settings feature.
  - Files: `apps/rss-reader/manifest.yaml`, `apps/rss-reader/app.py`, `apps/rss-reader/frontend/templates/settings.html`, `apps/rss-reader/frontend/templates/feed-sidebar.html`, `backend/tests/test_rss_settings.py`
  - Do: (1) Add to manifest.yaml: `permissions.settings: true` and `settings:` array with two entries: `articlesPerPage` (inputType: number, default: "50", label: "Articles per page", description: "Number of articles shown per feed page") and `markReadOnOpen` (inputType: toggle, default: "true", label: "Mark read on open", description: "Automatically mark articles as read when opened"). (2) Create GET `/_fragments/settings` route: read current values via `ctx.settings.get("articlesPerPage")` and `ctx.settings.get("markReadOnOpen")`, fall back to defaults from manifest, render `settings.html` with current values. (3) Create POST `/_fragments/settings` route: read form values, save via `ctx.settings.set()`, return success HTML fragment. (4) Create `settings.html` template with form inputs matching setting types (number input for articlesPerPage, checkbox/toggle for markReadOnOpen), submit button, and result feedback div. Use htmx POST. (5) Add settings gear icon button to `feed-sidebar.html` header area, using `hx-get="/_fragments/settings"` to load the form into the reading pane. (6) Write ≥8 tests in `test_rss_settings.py`: GET returns defaults when nothing set, GET returns saved values, POST saves values correctly, POST with missing values uses defaults, manifest validates with settings declared. Use mock ctx pattern with mock settings client.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v` — ≥8 tests pass; manifest.yaml validates: `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('../apps/rss-reader/manifest.yaml')"`
  - Done when: Settings page renders with current/default values, saves values via SettingsClient, manifest validates with settings declared, gear icon in sidebar opens settings, all tests pass

## Files Likely Touched

- `apps/rss-reader/services/opml_parser.py` (new)
- `apps/rss-reader/app.py` (modified — new routes + imports)
- `apps/rss-reader/manifest.yaml` (modified — settings declarations)
- `apps/rss-reader/frontend/templates/opml-import.html` (new)
- `apps/rss-reader/frontend/templates/settings.html` (new)
- `apps/rss-reader/frontend/templates/feed-sidebar.html` (modified — import + settings buttons)
- `backend/tests/test_opml_import.py` (new)
- `backend/tests/test_rss_settings.py` (new)
