---
id: T04
parent: S01
milestone: M038
provides:
  - Full app page template (main.html) with two-column layout and htmx fragment loading
  - Sources list fragment (sources-list.html) with source filtering, error badges, and remove button
  - Items list fragment (items-list.html) with episode table and status badges
  - Add-source form fragment (add-source.html) with htmx submission
  - App-specific CSS (styles.css) using workspace theme variables
  - 64-test comprehensive unit test suite covering all pure functions and async workflows
  - Add-source fragment route in app.py
key_files:
  - apps/media-scheduler/frontend/templates/main.html
  - apps/media-scheduler/frontend/templates/sources-list.html
  - apps/media-scheduler/frontend/templates/items-list.html
  - apps/media-scheduler/frontend/templates/add-source.html
  - apps/media-scheduler/frontend/static/styles.css
  - backend/tests/test_media_scheduler.py
  - apps/media-scheduler/app.py
key_decisions:
  - All htmx URLs use /app/media-scheduler/ proxy prefix per KNOWLEDGE.md rule, avoiding the latent bug present in rss-reader templates
  - Added /_fragments/add-source GET route to app.py so main.html can lazy-load the form via htmx (plan didn't specify a separate route but the inline-form UX requires it)
  - Poll-sources tests patch on _app_mod not _svc_mod — poll_sources binds its own references to service functions at import time via the fallback importlib path, so patching the service module has no effect
patterns_established:
  - importlib-based test pattern for app modules with feedparser mock at sys.modules level, tested and proven across 64 cases
  - Badge variant CSS classes (ms-badge-{status}) for consistent status display across sources and items
observability_surfaces:
  - 64 unit tests in test_media_scheduler.py as regression signal for all pure functions and async workflows
  - Templates individually testable via fragment endpoints (/_fragments/sources, /_fragments/items, /_fragments/add-source)
  - Error badge visibility in sources list template shows feed health at a glance
duration: 12m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: App UI templates + unit tests

**Created Jinja2 templates for Media Scheduler app page (two-column layout with htmx fragment loading), app CSS with workspace theme variables, and 64 comprehensive unit tests covering manifest, IRI minting, entry conversion, duration parsing, dedup, subscribe/unsubscribe, feed fetching, and poll-sources task.**

## What Happened

Replaced the placeholder `main.html` with a proper two-column layout: left sidebar (sources list with add-source toggle) and right main area (episodes table). The sidebar header has a + button that toggles an inline form section loaded via htmx GET from a new `/_fragments/add-source` route. Sources and items load on page open and refresh on `sourcesChanged` events.

Rewrote `sources-list.html` to include per-source click-to-filter (clicking a source re-fetches items filtered by source_iri), error badges with count and tooltip, and a remove button that posts to the remove route. Added a "Show all items" button below the source list to clear the source filter.

Rewrote `items-list.html` as a table with columns for title (linked to enclosure URL), source name, date, duration, and status badge. The `add-source.html` fragment is a compact form with URL and optional title inputs that posts via htmx with results swapped into a status area.

Created `styles.css` with 44 CSS variable references using workspace theme tokens (--color-bg, --color-text, --color-border, --color-surface-recessed, --color-accent, etc.) with sensible fallbacks. Status badges for source types (podcast/youtube/spotify) and item states (queued/completed/skipped/playing/saved) use semantic colors.

Built `test_media_scheduler.py` with 64 tests across 13 test classes: TestManifest (4), TestIRIMinting (7), TestParseDuration (9), TestEntryToMediaItem (11), TestStructTimeToIso (2), TestAppHelpers (12), TestDedup (3), TestSubscribePodcast (3), TestUnsubscribeSource (1), TestUpdateSourceState (2), TestFeedFetchError (2), TestFetchFeed (3), TestPollSources (4). The poll-sources tests required patching on `_app_mod` rather than `_svc_mod` because the app module's fallback import path binds its own references.

## Verification

All slice-level checks pass:
- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — 64/64 tests pass
- Model manifest parses correctly
- Ontology contains MediaSource class
- App manifest validates with correct appId

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_media_scheduler.py -v` | 0 | ✅ pass (64 tests) | 0.33s |
| 2 | `python3 -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler'"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); assert any(n.get('@id','').endswith('MediaSource') for n in d['@graph'])"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('../apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler'"` | 0 | ✅ pass | <1s |
| 5 | `grep hx-get hx-post apps/media-scheduler/frontend/templates/*.html` — all URLs use /app/media-scheduler/ prefix | 0 | ✅ pass | <1s |

## Diagnostics

- Run full test suite: `cd backend && python -m pytest tests/test_media_scheduler.py -v`
- Inspect template htmx URLs: `grep -n 'hx-get\|hx-post' apps/media-scheduler/frontend/templates/*.html`
- Verify CSS variable usage: `grep -c 'var(--color' apps/media-scheduler/frontend/static/styles.css` (expect 44+)
- Check template structure: `cat apps/media-scheduler/frontend/templates/main.html`

## Deviations

- Added `/_fragments/add-source` GET route not in original plan — needed because `main.html` lazy-loads the add-source form via htmx rather than embedding it inline.
- Poll-sources test mocking targets `_app_mod` instead of `_svc_mod` — the app module's fallback import creates its own bound references that can't be patched via the service module.

## Known Issues

- Badge status colors (youtube red, spotify green, playing blue, saved yellow) use hardcoded hex values since no matching workspace theme variables exist. These are intentional semantic colors.

## Files Created/Modified

- `apps/media-scheduler/frontend/templates/main.html` — Full two-column app page layout with htmx fragment loading for sources sidebar and items area
- `apps/media-scheduler/frontend/templates/sources-list.html` — Sources list fragment with click-to-filter, error badges, remove button, and "show all" action
- `apps/media-scheduler/frontend/templates/items-list.html` — Items table fragment with title/source/date/duration/status columns and status badges
- `apps/media-scheduler/frontend/templates/add-source.html` — Add podcast form fragment with URL and title inputs, htmx submission
- `apps/media-scheduler/frontend/static/styles.css` — App CSS with 44 workspace theme variable references, badge variants, table styles
- `backend/tests/test_media_scheduler.py` — 64 unit tests across 13 classes covering manifest, IRI minting, entry conversion, duration parsing, dedup, CRUD, feed fetching, and poll-sources task
- `apps/media-scheduler/app.py` — Added `/_fragments/add-source` GET route for lazy-loading the add-source form
