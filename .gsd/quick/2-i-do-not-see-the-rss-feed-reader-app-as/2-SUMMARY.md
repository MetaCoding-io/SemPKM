# Quick Task: Recover RSS Reader app missing from installable apps

**Date:** 2026-03-21
**Branch:** gsd/quick/2-i-do-not-see-the-rss-feed-reader-app-as

## What Changed

The RSS Reader app (`apps/rss-reader/`) and `rss-feeds` Mental Model (`models/rss-feeds/`) were not visible as installable because they were never committed to main. M010 built them across 6 slices in a worktree, but only `.gsd/` planning artifacts were committed — the actual source code lived in dangling git objects after the worktree was cleaned up.

**Recovery method:** Found dangling commit `89b71093` (S05/T02 — last committed code) and stash `c724c90c` (WIP with S05/T03 settings additions) via `git fsck --lost-found`. Extracted all files from those commits and applied platform fixes that were part of M010.

- Recovered `apps/rss-reader/` — complete RSS reader app (1418-line app.py, 16 templates, CSS, JS, feed service, OPML parser, manifest)
- Recovered `models/rss-feeds/` — Mental Model with Article and FeedSubscription types
- Recovered SDK IRI prefix enforcement fix (D179) — apps can now reference model types and standard vocabularies
- Recovered navigate command enrichment — app commands open dockview tabs instead of full-page navigation
- Recovered 7 test files (229 tests)
- Created `settings.html` template (was in uncommitted T03 work, reconstructed from app.py route contract)

## Files Modified
- `apps/rss-reader/` — 21 files (app.py, manifest.yaml, requirements.txt, services/, frontend/)
- `models/rss-feeds/` — 4 files (manifest.yaml, ontology, shapes, views JSON-LD)
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — IRI prefix fix
- `backend/app/browser/apps.py` — Navigate command enrichment
- `frontend/static/js/workspace.js` — Navigate handler uses openAppPageTab()
- `backend/tests/test_*.py` — 7 test files

## Verification
- All Python files pass `ast.parse()` syntax check
- App manifest validates against `AppManifestSchema` (rss-reader v1.0.0)
- Model manifest validates against `ManifestSchema` (rss-feeds v1.0.0)
- All JSON-LD files parse as valid JSON
- No conflict markers in any recovered files
- `apps/rss-reader/` now visible to admin page's "Available Apps" discovery
