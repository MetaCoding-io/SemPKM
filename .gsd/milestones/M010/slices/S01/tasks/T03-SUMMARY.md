---
id: T03
parent: S01
milestone: M010
provides:
  - rss-reader app skeleton with manifest, poll-feeds task handler, stub routes, and frontend templates
  - Importable pure helper functions (entry_to_article, parse_feed, get_existing_article_iris) for T04 tests
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/requirements.txt
  - apps/rss-reader/frontend/templates/reader.html
  - apps/rss-reader/frontend/static/styles.css
key_decisions:
  - "entry_to_article uses feed_iri (subscription IRI) as feedSource and for IRI hash input when entry._feed_url not set — keeps hashing deterministic even when caller doesn't set _feed_url"
  - "poll-feeds handler is async (not sync like test-app heartbeat) because it awaits graph.query and commands.bulk"
  - "isRead/isStarred default to False in article properties — new articles start unread/unstarred"
patterns_established:
  - "Article IRI pattern: urn:sempkm:app:rss-reader:article-{sha256(feed_url+entry_id)} — deterministic, dedup-friendly"
  - "Bulk command usage: async with ctx.commands.bulk(summary, source) as batch → batch.add() per article"
  - "SPARQL query for subscriptions returns ?sub, ?feedUrl, ?title — handler iterates bindings"
observability_surfaces:
  - "poll-feeds task logs per-feed: 'Polled {url}: N new articles created'"
  - "poll-feeds returns summary dict: {feeds_polled: N, articles_created: M}"
  - "Feed parse errors logged with feed URL for diagnosis"
duration: 20m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Create rss-reader app skeleton with poll-feeds task handler

**Built rss-reader app with poll-feeds async task handler that queries FeedSubscription objects, parses feeds via feedparser, deduplicates articles, and bulk-creates Article objects via ctx.commands.bulk().**

## What Happened

Created the complete `apps/rss-reader/` directory following `apps/test-app/` patterns:

1. **manifest.yaml** — Declares rss-reader app with rss-feeds model dependency, permissions for object.create/patch, edge.create, body.set, SPARQL read, backgroundTasks, and network wildcard. Single poll-feeds task at 5m interval with retry policy. UI page for reader, view contributions for unread/starred, command palette entries for subscribe and open-reader.

2. **app.py** — Core module with:
   - Constants: `ARTICLE_TYPE`, `SUBSCRIPTION_TYPE`, `RSS_NS` for full model IRIs
   - `parse_feed(feed_url)` — wraps feedparser.parse()
   - `_mint_article_iri(feed_url, entry_id)` — SHA-256 deterministic IRI
   - `_time_struct_to_iso(t)` — converts feedparser time structs to ISO 8601
   - `entry_to_article(entry, feed_iri, app_id)` — pure function mapping feedparser entry to article creation params dict with full IRI types and dcterms/rss properties
   - `get_existing_article_iris(graph_client, feed_iri)` — SPARQL dedup query
   - `poll_feeds(ctx, body)` — async task handler that queries subscriptions, parses each feed, deduplicates, and bulk-creates articles
   - 4 stub fragment routes for reader, unread-view, starred-view, subscribe-dialog
   - Startup/shutdown lifecycle hooks

3. **requirements.txt** — feedparser>=6.0

4. **5 frontend templates** — Stub HTML for reader page, unread view, starred view, subscribe dialog, and main page

5. **styles.css** — Minimal placeholder styles

## Verification

- ✅ `parse_app_manifest('apps/rss-reader/manifest.yaml')` — validates with poll-feeds task, rss-feeds dependency, all permissions
- ✅ `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK
- ✅ `from app import entry_to_article` — importable with SDK venv (pure function, no SDK dependency in logic)
- ✅ `entry_to_article()` produces correct dict with `urn:sempkm:model:rss-feeds:Article` type, dcterms properties, deterministic IRI
- ✅ IRI determinism verified — same input produces same hash
- ✅ `rss_reader_app._task_handlers` contains `poll-feeds`, 4 routes registered

**Slice-level verification (T03 is intermediate — partial pass expected):**
- ✅ `test_iri_prefix_fix.py` — 13/13 tests pass
- ⏳ `test_rss_feed_parser.py` — not yet created (T04)
- ✅ Model manifest validates
- ✅ App manifest validates
- ⏳ Docker integration — not testable until full stack run
- ✅ Diagnostic: `test_foreign_app_iri_blocked` passes with correct error message

## Diagnostics

- Inspect app structure: `find apps/rss-reader -type f | sort`
- Validate manifest: `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(m.appId, m.version)"`
- Test entry_to_article: `cd /path/to/repo && backend/.venv/bin/python -c "import sys; sys.path.insert(0, 'apps/rss-reader'); from app import entry_to_article; print('OK')"`
- Inspect task handler: `grep -n 'def poll_feeds' apps/rss-reader/app.py`

## Deviations

- Plan said `rss_reader_app = App("rss-reader")` (class instance naming), app.py uses that exactly. Plan mentioned `RSSReaderApp` in the T03 "Do" section but the actual entrypoint in manifest is `app:rss_reader_app` — followed the manifest pattern from Step 1 which is correct.
- Added `_time_struct_to_iso()` helper not in plan — needed for feedparser time struct → ISO 8601 conversion.
- Added `_mint_article_iri()` as separate helper — plan implied it was inline in `entry_to_article`.

## Known Issues

- `entry._feed_url` attribute is set by the poll-feeds handler before calling `entry_to_article` — this is a side-effect on the feedparser entry object. Works fine but is slightly impure. T04 tests should set this explicitly.
- feedparser is installed in the backend venv for local testing but in production would be in the app's own venv (managed by app runner).

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — Complete app manifest with dependencies, permissions, tasks, UI declarations
- `apps/rss-reader/app.py` — App module with poll-feeds task handler, helper functions, stub routes, lifecycle hooks
- `apps/rss-reader/requirements.txt` — feedparser>=6.0 dependency
- `apps/rss-reader/frontend/templates/main.html` — Main page stub
- `apps/rss-reader/frontend/templates/reader.html` — Reader page stub
- `apps/rss-reader/frontend/templates/unread-view.html` — Unread view stub
- `apps/rss-reader/frontend/templates/starred-view.html` — Starred view stub
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — Subscribe dialog stub
- `apps/rss-reader/frontend/static/styles.css` — Placeholder styles
