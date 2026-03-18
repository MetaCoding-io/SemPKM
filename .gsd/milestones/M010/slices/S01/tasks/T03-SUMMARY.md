---
id: T03
parent: S01
milestone: M010
provides:
  - "rss-reader app skeleton with poll-feeds task handler, stub fragment routes, and importable helper functions"
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/requirements.txt
  - apps/rss-reader/frontend/templates/reader.html
  - apps/rss-reader/frontend/templates/subscribe-dialog.html
  - apps/rss-reader/frontend/static/styles.css
key_decisions:
  - "Article IRI minting uses SHA-256 of (feed_iri + entry_id) — uses feed_iri not feed_url for stable dedup even if URL redirects"
  - "entry_to_article() sets isRead=false and isStarred=false as default properties on every new article"
patterns_established:
  - "Pure helper functions (entry_to_article, _mint_article_iri) have zero SDK dependency — importable and testable by T04 directly"
  - "poll-feeds task uses async with ctx.commands.bulk() context manager for batched article creation per feed"
  - "SPARQL query pattern for FeedSubscription objects: SELECT ?sub ?url WHERE { ?sub a <SUBSCRIPTION_TYPE> . ?sub <RSS_NS>feedUrl ?url }"
observability_surfaces:
  - "poll-feeds task logs 'Polled {feed_url}: {N} new articles (skipped {M} existing)' per feed"
  - "poll-feeds task returns {'feeds_polled': N, 'articles_created': M} summary dict"
  - "Feed parse errors logged at exception level with feed URL context"
duration: 12m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Create rss-reader app skeleton with poll-feeds task handler

**Created rss-reader app with poll-feeds task handler that queries FeedSubscriptions via SPARQL, parses feeds with feedparser, deduplicates articles, and bulk-creates Article objects via ctx.commands.bulk().**

## What Happened

Created the complete `apps/rss-reader/` directory following the `apps/test-app/` reference patterns. The app has:

1. **manifest.yaml** — declares dependency on `rss-feeds` model ≥1.0.0, permissions for object.create/object.patch/edge.create/body.set, SPARQL read, backgroundTasks, and network access. Declares `poll-feeds` task at 5m interval with retry policy. Registers reader page, unread/starred views, and subscribe-feed/open-reader command palette entries.

2. **app.py** — core application with:
   - Pure helper functions (`entry_to_article`, `_mint_article_iri`, `_struct_time_to_iso`, `get_existing_article_iris`) designed for direct import by T04 test file
   - `poll-feeds` async task handler that queries all FeedSubscription objects via SPARQL, parses each feed with feedparser, deduplicates against existing articles in the triplestore, and bulk-creates new Article objects
   - 4 stub fragment routes for reader, unread-view, starred-view, and subscribe-dialog
   - Startup/shutdown lifecycle hooks

3. **Frontend stubs** — 5 HTML templates (main, reader, unread-view, starred-view, subscribe-dialog) and a placeholder CSS file. The subscribe dialog includes a real form structure with htmx POST wiring for when S03 implements it.

Key design choice: `_mint_article_iri()` hashes `feed_iri + entry_id` (not `feed_url + entry_id`) so article IRIs are stable relative to the subscription object, not the raw URL which could change due to redirects.

## Verification

- Manifest validates against `AppManifestSchema` with correct appId, version, tasks, models, permissions, pages, views, and command palette entries
- `app.py` syntax check passes (ast.parse)
- All exports importable: `entry_to_article`, `parse_feed`, `get_existing_article_iris`, `rss_reader_app`, constants
- `entry_to_article()` confirmed as pure function: produces deterministic IRIs, correct type IRI, correct property mappings
- Article type uses full IRI `urn:sempkm:model:rss-feeds:Article`
- Article IRIs use deterministic SHA-256 hash: `urn:sempkm:app:rss-reader:article-{hash16}`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "from backend.app.apps.manifest import parse_app_manifest; m = parse_app_manifest('apps/rss-reader/manifest.yaml'); print(f'OK: {m.appId} v{m.version}, tasks: {[t.id for t in m.tasks]}')"` | 0 | ✅ pass | <1s |
| 2 | `python -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('Syntax OK')"` | 0 | ✅ pass | <1s |
| 3 | `python -c "import sys; sys.path.insert(0, 'apps/rss-reader'); from app import entry_to_article; print('Import OK')"` | 0 | ✅ pass | <1s |
| 4 | `python -m pytest backend/tests/test_iri_prefix_fix.py -v` (slice check) | 0 | ✅ pass (13/13) | <1s |
| 5 | `python -c "from backend.app.models.manifest import parse_manifest; ..."` (slice check) | 0 | ✅ pass | <1s |
| 6 | `python -c "from backend.app.apps.manifest import parse_app_manifest; ..."` (slice check) | 0 | ✅ pass | <1s |
| 7 | `python -m pytest backend/tests/test_rss_feed_parser.py -v` (slice check) | — | ⏳ pending T04 | — |
| 8 | Docker integration test (slice check) | — | ⏳ pending Docker | — |

## Diagnostics

- **Import check:** `python -c "import sys; sys.path.insert(0, 'apps/rss-reader'); sys.path.insert(0, 'backend/sdk'); from app import rss_reader_app; print(list(rss_reader_app._task_handlers.keys()))"` → shows registered task handlers
- **Pure function test:** `entry_to_article(entry_dict, feed_iri)` — returns dict with `iri`, `type`, `properties` keys. No SDK dependency needed.
- **IRI minting:** `_mint_article_iri(feed_iri, entry_id)` — returns deterministic `urn:sempkm:app:rss-reader:article-{hash}` IRI
- **Task handler:** `poll_feeds(ctx)` is async — returns `{"feeds_polled": N, "articles_created": M}` summary

## Deviations

- Installed `feedparser` into the backend venv via `ensurepip` bootstrap + pip install (venv had no pip initially). This is a dev-time convenience — in Docker, feedparser would be installed from the app's requirements.txt during app installation.
- `entry_to_article()` hashes `feed_iri + entry_id` instead of `feed_url + entry_id` as plan suggested — feed_iri is more stable for dedup (URL can redirect, IRI is canonical).

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — app manifest with dependencies, permissions, tasks, UI declarations
- `apps/rss-reader/app.py` — core app with poll-feeds task handler, pure helper functions, stub routes, lifecycle hooks
- `apps/rss-reader/requirements.txt` — feedparser>=6.0 dependency
- `apps/rss-reader/frontend/templates/main.html` — main page stub template
- `apps/rss-reader/frontend/templates/reader.html` — reader page stub template
- `apps/rss-reader/frontend/templates/unread-view.html` — unread articles view stub
- `apps/rss-reader/frontend/templates/starred-view.html` — starred articles view stub
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — subscribe dialog with htmx form
- `apps/rss-reader/frontend/static/styles.css` — placeholder CSS styles
