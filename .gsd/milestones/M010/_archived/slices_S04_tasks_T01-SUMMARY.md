---
id: T01
parent: S04
milestone: M010
provides:
  - rightPane "Related Articles" section in manifest + route handler + template
  - objectRenderers entry for rss:Article with custom read renderer route + template
  - mark-all-read command palette entry with command palette context detection
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/related-articles.html
  - apps/rss-reader/frontend/templates/article-read-renderer.html
key_decisions:
  - RELATED_ARTICLES_SPARQL uses UNION of feedSource match and bpkm:tags match, with LIMIT 10
  - article-read-renderer.html omits fire-and-forget mark-read div (object browser context, not reader)
  - Command palette detection via HX-Target header == "#modal-container"
patterns_established:
  - Right pane fragment handler pattern: receive ?iri= param, SPARQL query, render template with articles list
  - Custom object renderer fragment pattern: receive ?iri= param, reuse existing SPARQL shape, render without reader-specific triggers
observability_surfaces:
  - SPARQL errors in related-articles/renderer handlers logged as warnings, rendered as <div class="rss-error">
  - data-article-iri attributes on related-articles list items for test automation
  - HX-Trigger: articleStateChanged, feedsChanged on mark-all-read command palette response
  - rss-success/rss-error class on mark-all-read command palette response for confirmation visibility
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Add right pane, custom renderer, and mark-all-read command to manifest + app

**Added three workspace contributions: rightPane "Related Articles" section, custom Article read renderer, and "Mark All as Read" command palette entry with context-aware response.**

## What Happened

1. Updated `manifest.yaml` with three new sections: `rightPane` array (related-articles entry with priority 60, targetTypes `["*"]`), `objectRenderers` array (type `urn:sempkm:model:rss-feeds:Article` with `modes.read: "article-read-renderer"`), and `mark-all-read` added to `commandPalette` with `actionType: "post"` and `endpoint: "/_fragments/mark-all-read"`.

2. Added `/_fragments/related-articles` GET route handler in `app.py`. Uses a `RELATED_ARTICLES_SPARQL` constant with UNION of same-feedSource and shared-bpkm:tags, excluding the focused IRI, ordered by created DESC, limited to 10. Handles empty IRI (empty state), SPARQL errors (rss-error div), and renders `related-articles.html`.

3. Created `related-articles.html` template with `data-article-iri` attributes on each article item, showing title, date, feed source. Each item is clickable via `openTab()`.

4. Added `/_fragments/article-read-renderer` GET route handler. Reuses the same SPARQL pattern as `article_reading_pane_fragment` (title, link, author, created, isStarred, body, description, feedTitle) but does NOT include the fire-and-forget mark-read div. Handles missing IRI and article-not-found cases.

5. Created `article-read-renderer.html` template with `data-md-source`/`data-md-target` attributes for markdown rendering, star button inclusion via `{% include "star-button.html" %}`, and "no content" fallback.

6. Updated `mark_all_read_route()` to detect command palette context via `request.headers.get("HX-Target") == "#modal-container"`. When from command palette, returns `<div class="rss-success">Marked N articles as read</div>` with `HX-Trigger: articleStateChanged, feedsChanged` headers. Existing reader UI behavior unchanged.

## Verification

- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — ✓ syntax OK
- `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` — ✓ valid YAML
- Grep `objectRenderers` in manifest → type is `urn:sempkm:model:rss-feeds:Article` ✓
- Grep `related-articles` in manifest → present in `rightPane` ✓
- Grep `mark-all-read` in manifest → present in `commandPalette` with `actionType: "post"` ✓
- `data-article-iri` attribute present in `related-articles.html` ✓
- `data-md-source`/`data-md-target` present in `article-read-renderer.html` ✓
- `is_command_palette` check in `mark_all_read_route()` returning `rss-success` div ✓
- `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` — 43/43 passed (zero regressions)
- `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — 13/13 passed (zero regressions)

### Slice-level verification status (T01 of 3):
- ✓ `test_rss_reader_ui.py` — 43 passed (S03 tests, no S04 tests yet — T03 will add)
- ✓ `test_app_views_commands.py` — 13 passed (existing tests, T03 will add navigate fix tests)
- ✓ Python syntax OK
- ✓ YAML syntax OK
- ✓ `objectRenderers[0].type` is full IRI `urn:sempkm:model:rss-feeds:Article`
- ⏳ Navigate command JSON includes `appId` and `pageId` — T02 work
- ✓ Error-state HTML verified in both new handlers (rss-error class on SPARQL failure)
- ✓ mark-all-read returns rss-success when HX-Target is #modal-container

## Diagnostics

- **Related articles handler:** SPARQL errors logged as `"Related articles SPARQL error: ..."` at WARNING level. Error response: `<div class="rss-error">Failed to load related articles: {exc}</div>`. Empty IRI returns `<div class="rss-empty-state">No related articles found</div>`.
- **Article renderer handler:** SPARQL errors logged as `"Article read renderer SPARQL error: ..."` at WARNING level. Missing IRI returns `<div class="rss-error">Missing article IRI</div>`. Article not found returns `<div class="rss-reading-pane-empty"><p>Article not found</p></div>`.
- **Mark-all-read command palette:** Returns `<div class="rss-success">Marked N articles as read</div>` with `HX-Trigger: articleStateChanged, feedsChanged` headers.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — Added rightPane, objectRenderers, and mark-all-read commandPalette entry
- `apps/rss-reader/app.py` — Added `BPKM_TAGS` constant, `RELATED_ARTICLES_SPARQL`, `related_articles_fragment()`, `article_read_renderer_fragment()`, updated `mark_all_read_route()` with command palette detection
- `apps/rss-reader/frontend/templates/related-articles.html` — New template for right pane related articles section
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — New template for custom Article read renderer
- `.gsd/milestones/M010/slices/S04/S04-PLAN.md` — Added diagnostic verification step (pre-flight fix)
- `.gsd/milestones/M010/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
