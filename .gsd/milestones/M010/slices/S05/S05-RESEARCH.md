# S05: OPML import + app settings — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

This is a straightforward slice with two independent features: (1) OPML file import that creates feed subscriptions, and (2) an app settings page for configuring poll interval and reader preferences. Both features have clear patterns to follow and no novel technology.

OPML import is simple XML parsing — stdlib `xml.etree.ElementTree` handles it cleanly with no third-party dependency needed (the research doc suggested `listparser` but the format is trivial). The import calls `FeedService.subscribe()` for each feed, which already handles dedup. Category folders in OPML map to tags on subscriptions.

App settings uses the existing `SettingsClient` (wraps `StateClient` with `settings:` prefix) and the `AppSettingDef` manifest schema. The platform already validates settings declarations and the SDK provides `ctx.settings.get/set()`. Settings are string key/value pairs — poll interval, articles-per-page, etc.

Both features are self-contained — OPML import is a new route + template + pure parsing function, and settings is a new route + template + manifest additions. No platform changes required.

## Recommendation

Build OPML import first (it's a user-facing feature that delivers RSS-05), then settings (lower priority, more configuration plumbing). Test the OPML parser as a pure function (no mocking needed) and the routes with the same mock pattern established in S02/S04.

**Do NOT add `listparser` as a dependency.** OPML is a simple XML format — `xml.etree.ElementTree` handles it in ~40 lines. Adding a dependency for this is over-engineering. The stdlib approach also avoids any Docker install risk.

## Implementation Landscape

### Key Files

**Existing (read, don't modify unless adding routes/imports):**
- `apps/rss-reader/app.py` — Add OPML import route, settings routes, and import the new OPML parser. Currently 1196 lines with all fragment routes.
- `apps/rss-reader/services/feed_service.py` — `subscribe()` is the API contract for OPML import. Each OPML feed entry calls this. No changes needed.
- `apps/rss-reader/manifest.yaml` — Must add `permissions.settings: true` and `settings:[]` definitions. Currently missing both.
- `apps/rss-reader/requirements.txt` — No new dependencies needed (stdlib handles OPML).
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — `SettingsClient` with `get(key)` → `str|None` and `set(key, value)`. Keys auto-prefixed with `settings:`.
- `backend/app/apps/manifest.py` — `AppSettingDef` with `key`, `label`, `description`, `inputType`, `options`, `default`. `inputType` values: text, password, toggle, select, number. Validates that `permissions.settings` is true when settings are declared.

**New files to create:**
- `apps/rss-reader/services/opml_parser.py` — Pure OPML parsing function. Input: XML string. Output: list of dicts with `url`, `title`, `category` keys. No SDK dependency — fully testable in isolation.
- `apps/rss-reader/frontend/templates/opml-import.html` — File upload form for OPML. htmx POST to `/_fragments/import-opml` with multipart form data.
- `apps/rss-reader/frontend/templates/settings.html` — Settings form rendered from manifest `AppSettingDef` definitions + current values from `ctx.settings`.
- `backend/tests/test_opml_import.py` — Tests for OPML parser (pure function tests) + import route (mock ctx tests).

### Build Order

1. **OPML parser (pure function)** — `parse_opml(xml_string) -> list[dict]`. Handles nested `<outline>` categories, extracts `xmlUrl`, `text`/`title`, `htmlUrl`, and parent category. Returns empty list on parse errors. This is the foundation — fully testable without mocking.

2. **OPML import route + template** — POST `/_fragments/import-opml` reads the uploaded file, calls `parse_opml()`, then calls `subscribe()` for each feed. Returns HTML summary showing created/duplicate/error counts. Template has file input + submit button. Add to subscribe-dialog.html or as a standalone dialog reachable from the feed sidebar.

3. **Settings manifest declarations** — Add `permissions.settings: true` and `settings:` array to `manifest.yaml` with keys: `pollInterval` (select: 1m/5m/15m/30m/1h), `articlesPerPage` (number, default 50), `markReadOnOpen` (toggle, default true).

4. **Settings route + template** — GET `/_fragments/settings` renders the settings form with current values. POST `/_fragments/settings` saves values via `ctx.settings.set()`. Template renders inputs based on setting definitions. Add a settings button/link to the feed sidebar.

5. **Wire poll interval setting** — In `poll_feeds()`, read `ctx.settings.get("pollInterval")` to... actually, poll interval is controlled by the platform scheduler, not the app. The manifest already declares `configurable: true` on the poll-feeds task, meaning the admin can change the interval via the admin UI. The app settings page should document this rather than trying to override it. **Skip poll interval as an app setting** — it's already configurable in admin.

### Verification Approach

**Unit tests (pure function):**
```bash
cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v
```

Test cases for OPML parser:
- Valid OPML with flat feeds (no categories)
- Valid OPML with nested category folders
- Feeds with missing titles (fall back to URL)
- Empty OPML body (no feeds)
- Invalid XML (returns empty list, no exception)
- Mixed: some outlines are categories, some are feeds
- Category names preserved on feed entries
- Deeply nested categories (2+ levels) — flatten to `/`-delimited tag

Test cases for import route:
- Successful import with N feeds → shows "Created N subscriptions"
- Some duplicates → shows "N created, M already subscribed"
- Empty file → error message
- Invalid XML → error message
- No file uploaded → error message

Test cases for settings:
- GET settings returns form with default values when none set
- POST settings saves values, re-GET shows saved values
- Settings values are strings (SettingsClient stores strings only)

**Syntax checks:**
```bash
python3 -c "import ast; ast.parse(open('apps/rss-reader/services/opml_parser.py').read())"
python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"
```

## Constraints

- **File upload via Starlette `request.form()`** — The SDK app runs FastAPI/Starlette. File uploads work via multipart form data. Access uploaded file via `form = await request.form(); file = form["opml_file"]`. The file object has `.read()` (bytes), `.filename`, etc. `python-multipart` is a transitive dependency of FastAPI (already in SDK deps).

- **SettingsClient stores strings only** — All values are strings. Numbers need `str()` on write and `int()` on read. Booleans are `"true"`/`"false"` strings. No JSON blobs — use separate keys.

- **AppSettingDef key pattern** — Keys must match `^[a-zA-Z][a-zA-Z0-9]*$` (no hyphens, no underscores). Max 64 chars.

- **Import fallback pattern** — Any new function in `services/opml_parser.py` needs the `try/except ImportError` fallback in `app.py` for test compatibility (documented in KNOWLEDGE.md). Alternatively, tests can use `importlib.util.spec_from_file_location` to load the module directly.

- **subscribe() is async** — Each OPML feed subscription is an async call to `subscribe(ctx, feed_url, title)`. For many feeds, these should be called sequentially (not `asyncio.gather`) to avoid overwhelming the platform with concurrent SDK calls. subscribe() already handles dedup, so re-importing the same OPML is safe.

## Common Pitfalls

- **OPML category extraction** — Categories in OPML are parent `<outline>` elements without `xmlUrl`. A feed's category comes from its parent outline's `text` attribute. Feeds at the root level have no category. The parser must walk the tree, tracking parent category context — don't just iterate all outlines flat.

- **OPML encoding** — OPML files may have different XML encodings declared. `xml.etree.ElementTree.fromstring()` expects a string, but `ET.parse()` or `ET.fromstring(bytes)` handles encoding declarations. Since we receive bytes from the upload, pass bytes to `ET.fromstring()` to let the XML parser handle encoding.

- **Multipart file size** — No limit on uploaded file size in the SDK app's Starlette config. OPML files are tiny (usually <100KB) so this isn't a real concern, but reading the entire file into memory is fine.

- **Empty outline titles** — Some OPML exporters produce feeds with `text=""` or missing `text` attribute. Use `xmlUrl` as the fallback title (same pattern as `subscribe()`).
