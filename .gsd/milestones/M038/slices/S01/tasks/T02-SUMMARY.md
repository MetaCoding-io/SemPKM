---
id: T02
parent: S01
milestone: M038
provides:
  - media-scheduler app scaffold with manifest, entrypoint, 5 fragment routes, and podcast subscription CRUD service
key_files:
  - apps/media-scheduler/manifest.yaml
  - apps/media-scheduler/app.py
  - apps/media-scheduler/services/podcast_service.py
  - apps/media-scheduler/frontend/templates/main.html
  - apps/media-scheduler/requirements.txt
key_decisions:
  - Used sourceType="inactive" for soft-delete unsubscribe (simpler than adding a separate isActive boolean property — matches the existing sh:in enum constraint)
  - Added parse_duration() helper for iTunes duration strings (HH:MM:SS, MM:SS, bare seconds) — needed for entry_to_media_item and reusable in T03
patterns_established:
  - App namespace urn:sempkm:app:media-scheduler: for minted IRIs (source-{hash}, item-{hash})
  - Sources use SOURCES_WITH_STATE_SPARQL for listing with poll state — mirrors rss-reader's SUBSCRIPTIONS_WITH_STATE_SPARQL
  - Fragment routes follow /_fragments/{resource} convention with HX-Trigger: sourcesChanged for htmx reactivity
observability_surfaces:
  - App route handlers log warnings on SPARQL failure and info on subscribe/unsubscribe
  - podcast_service logs IRI minting and state changes at debug/info levels
  - HTML error fragments use .ms-error class for testable failure visibility
  - SOURCES_WITH_STATE_SPARQL query inspectable for active sources with errorCount/lastError
duration: 12m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Scaffold media-scheduler app with podcast CRUD

**Created media-scheduler app scaffold with manifest, 5 fragment routes, and podcast service providing deterministic IRI minting, feedparser-to-RDF conversion, and subscription CRUD.**

## What Happened

Built the complete media-scheduler app following the rss-reader reference pattern. The app manifest declares the `poll-sources` scheduled task at 15m interval, model dependency on media-scheduler, and permissions for commands + SPARQL + network + background tasks. The `podcast_service.py` module provides pure functions (`mint_source_iri`, `mint_item_iri`, `entry_to_media_item`, `parse_duration`) that are fully testable without the SDK, plus async SDK-dependent functions (`subscribe_podcast`, `unsubscribe_source`, `update_source_state`, `get_existing_item_iris`) for subscription management. The `app.py` entrypoint registers 5 fragment routes (main, sources list, add-podcast, remove source, items list) with proper error handling and htmx trigger headers. Created functional Jinja2 templates for sources-list and items-list that T04 will refine.

## Verification

All task-level must-haves and applicable slice-level verifications pass:
- App manifest validates via `parse_app_manifest()` with correct appId, task count, and task ID
- `mint_source_iri()` produces deterministic IRIs from feed URLs
- `mint_item_iri()` produces deterministic IRIs from source IRI + episode ID
- `entry_to_media_item()` correctly maps feedparser fields including enclosure preference, duration parsing, and all ms: namespace properties
- `subscribe_podcast()` includes duplicate check via SPARQL before creation
- App registers exactly 5 routes with correct HTTP methods
- `poll-sources` task declared in manifest with 15m interval

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('../apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler' and len(m.tasks)==1 and m.tasks[0].id=='poll-sources'"` | 0 | ✅ pass | <1s |
| 2 | Pure function smoke test: mint_source_iri determinism, mint_item_iri determinism, parse_duration, entry_to_media_item field mapping | 0 | ✅ pass | <1s |
| 3 | App module loads with 5 routes registered (main, sources, add-podcast, remove, items) | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler'"` | 0 | ✅ pass | <1s |
| 5 | `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); assert any(n.get('@id','').endswith('MediaSource') for n in d['@graph'])"` | 0 | ✅ pass | <1s |

## Diagnostics

- Verify app routes: `cd backend && PYTHONPATH=sdk .venv/bin/python -c "import importlib.util, pathlib; spec=importlib.util.spec_from_file_location('m', pathlib.Path('../apps/media-scheduler/app.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); [print(r) for r in mod.media_scheduler_app._routes]"`
- Test pure functions: `cd backend && .venv/bin/python -c "import importlib.util, pathlib; spec=importlib.util.spec_from_file_location('ps', pathlib.Path('../apps/media-scheduler/services/podcast_service.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print(mod.mint_source_iri('https://example.com/feed.xml'))"`
- Inspect SPARQL query: `grep -A 10 'SOURCES_WITH_STATE_SPARQL' apps/media-scheduler/services/podcast_service.py`

## Deviations

- Created `sources-list.html` and `items-list.html` templates as functional placeholders (not just empty stubs) — the routes reference them via `ctx.render_template()` and would crash without them. T04 will refine the final UI but the basic structure is usable now.
- Added `_format_date()` and `_format_duration()` helpers to `app.py` for template rendering — not in the plan but required for the items list route to produce readable output.

## Known Issues

- The `test_media_scheduler.py` unit test file doesn't exist yet — it's created in T04.
- The `poll-sources` task handler is not yet implemented in `app.py` — that's T03's scope.

## Files Created/Modified

- `apps/media-scheduler/manifest.yaml` — App manifest with poll-sources task, model dependency, permissions, and UI page
- `apps/media-scheduler/app.py` — App entrypoint with 5 fragment routes and lifecycle hooks
- `apps/media-scheduler/requirements.txt` — feedparser>=6.0 dependency
- `apps/media-scheduler/services/__init__.py` — Empty package init
- `apps/media-scheduler/services/podcast_service.py` — Pure functions (IRI minting, feedparser conversion, duration parsing) and SDK subscription management
- `apps/media-scheduler/frontend/templates/main.html` — Main app page with htmx-powered sources and items panels
- `apps/media-scheduler/frontend/templates/sources-list.html` — Sources list with add/remove forms
- `apps/media-scheduler/frontend/templates/items-list.html` — Items table with title, source, date, duration, status columns
- `.gsd/milestones/M038/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
