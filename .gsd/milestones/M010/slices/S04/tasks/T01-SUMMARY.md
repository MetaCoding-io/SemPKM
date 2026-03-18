---
id: T01
parent: S04
milestone: M010
provides:
  - Right pane "Related Articles" fragment route + template
  - Custom rss:Article read renderer fragment route + template
  - Mark-all-read command palette entry with context detection
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/related-articles.html
  - apps/rss-reader/frontend/templates/article-read-renderer.html
key_decisions:
  - Related articles use UNION SPARQL: same feedSource OR shared bpkm:tags
  - Article read renderer omits fire-and-forget mark-read since it's for the object browser
  - Command palette context detected via HX-Target header matching #modal-container
patterns_established:
  - Right pane fragment receives ?iri param, returns complete HTML including empty/error states
  - Command palette POST handlers detect context via HX-Target header for context-appropriate responses
observability_surfaces:
  - SPARQL errors logged as warnings, rendered as <div class="rss-error"> fragments
  - data-article-iri attributes on related-articles items for test automation
  - HX-Trigger headers (articleStateChanged, feedsChanged) on mark-all-read command palette response
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Add right pane, custom renderer, and mark-all-read command to manifest + app

**Added rightPane, objectRenderers, and mark-all-read command palette contributions to RSS Reader manifest with corresponding route handlers and templates**

## What Happened

Updated `manifest.yaml` with three new workspace contributions: a `rightPane` "Related Articles" section, an `objectRenderers` entry for `urn:sempkm:model:rss-feeds:Article` with custom read renderer, and a `mark-all-read` command palette entry with `actionType: "post"`.

Added two new route handlers in `app.py`:
- `/_fragments/related-articles`: queries articles sharing the same `feedSource` or `bpkm:tags` as the focused object using a UNION SPARQL pattern, limited to 10 results ordered by creation date descending
- `/_fragments/article-read-renderer`: reuses the reading pane SPARQL pattern but omits the fire-and-forget mark-read trigger since this renders in the object browser

Updated `mark_all_read_fragment()` to detect command palette context via `HX-Target: #modal-container` header — returns a `<div class="rss-success">Marked N articles as read</div>` confirmation message with both `articleStateChanged` and `feedsChanged` HX-Trigger headers when called from the command palette, while preserving the existing sidebar-refresh behavior for the reader UI.

Created two templates:
- `related-articles.html`: clickable article items with `data-article-iri` attributes that dispatch `sempkm:open-object` custom events
- `article-read-renderer.html`: article content with `data-md-source`/`data-md-target` attributes for markdown rendering, star button inclusion, no mark-read trigger

## Verification

- Python syntax check passed: `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"`
- YAML syntax check passed: `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"`
- All 37 existing S03 tests pass with zero regressions
- `objectRenderers[0].type` is the full IRI `urn:sempkm:model:rss-feeds:Article` (D165 compliance)
- `related-articles` present in manifest `rightPane`
- `mark-all-read` present in manifest `commandPalette` with `actionType: "post"`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | 3.0s |
| 2 | `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` | 0 | ✅ pass | 3.0s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` | 0 | ✅ pass (37/37) | 2.7s |
| 4 | `grep objectRenderers manifest.yaml` → type is full IRI | 0 | ✅ pass | <1s |
| 5 | `grep related-articles manifest.yaml` → in rightPane | 0 | ✅ pass | <1s |
| 6 | `grep mark-all-read manifest.yaml` → in commandPalette | 0 | ✅ pass | <1s |

Slice-level checks (partial — T01 is intermediate):
- ✅ `python3 syntax` — app.py parses
- ✅ `yaml syntax` — manifest.yaml parses
- ✅ `objectRenderers[0].type` is full IRI
- ✅ `rss-error` in route handlers for related-articles and article-read-renderer
- ✅ `rss-success` class in mark-all-read when HX-Target is `#modal-container`
- ⬜ `cd backend && pytest tests/test_rss_reader_ui.py` — S04 tests not yet written (T03)
- ⬜ `cd backend && pytest tests/test_app_views_commands.py` — navigate fix not yet done (T02)

## Diagnostics

- SPARQL failures in `related_articles_fragment` and `article_read_renderer_fragment` logged via `logger.warning()` and return `<div class="rss-error">` HTML fragments
- Empty IRI params return empty-state HTML (`rss-empty-state` or `rss-reading-pane-empty`)
- `data-article-iri` attributes on related article items enable test automation targeting
- Command palette mark-all-read response includes `HX-Trigger: articleStateChanged, feedsChanged` for downstream UI refresh

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — Added `rightPane`, `objectRenderers`, and `mark-all-read` command palette entry
- `apps/rss-reader/app.py` — Added `related_articles_fragment()` and `article_read_renderer_fragment()` route handlers; updated `mark_all_read_fragment()` with command palette context detection
- `apps/rss-reader/frontend/templates/related-articles.html` — New template for right pane related articles
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — New template for custom Article read renderer
