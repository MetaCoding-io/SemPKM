# Quick Task: Recover RSS Reader app and all missing worktree code

**Date:** 2026-03-21
**Branch:** gsd/quick/2-i-do-not-see-the-rss-feed-reader-app-as

## What Changed

The RSS Reader app wasn't installable because its source code was never committed to main. Investigation revealed this was a systemic problem: **8 milestones had source code trapped in dangling git objects** from cleaned-up worktrees.

### Root Cause

GSD worktree isolation mode (`taskIsolation.mode: worktree`) creates a separate git worktree per milestone. Auto-mode commits `.gsd/` planning artifacts to main, but source code stays in the worktree on a `milestone/<MID>` branch. When worktrees are cleaned up and branches deleted, source code becomes unreachable — surviving only as dangling objects that `git gc` would permanently delete.

### Recovery

All files recovered via `git fsck --lost-found` to find dangling commits, then `git checkout <hash> -- <path>` to extract files.

**Commit 1 — M010 RSS Reader (from 89b71093 + c724c90c stash):**
- `apps/rss-reader/` — 21 files (app, templates, CSS, JS, services)
- `models/rss-feeds/` — Mental Model (ontology, shapes, views)
- SDK IRI prefix fix, navigate command enrichment
- 7 test files, settings.html recreated

**Commit 2 — M019-M022 sync apps (from 3623430f):**
- `apps/todoist-sync/` — complete app + 6 test files
- `apps/outlook-calendar/` — complete app + 5 test files
- `apps/caldav-calendar/` — complete app + 5 test files
- `apps/asana-sync/` — complete app + 5 test files
- M018 Google Calendar E2E + docs
- 5 E2E mock servers, 5 E2E specs, 5 user guide chapters

**Commit 3 — M027 Notion + M028 AI (from 233006839):**
- `backend/app/notion/executor.py` + templates + test
- `backend/app/api/ai.py` + 4 test files
- E2E mock LLM server, 2 E2E specs, 2 user guide chapters

**Commit 4 — M010 remaining (from 735febba + 73d8cb65):**
- `test_rss_settings.py`, E2E spec, OPML fixture, Chapter 32

### Prevention

- Added Rules R01-R03 and Lesson K003 to KNOWLEDGE.md
- `taskIsolation.mode` already set to `none` in preferences

## Files Modified
- `apps/rss-reader/` — 22 files recovered
- `apps/todoist-sync/` — 12 files recovered
- `apps/outlook-calendar/` — 12 files recovered
- `apps/caldav-calendar/` — 12 files recovered
- `apps/asana-sync/` — 12 files recovered
- `models/rss-feeds/` — 4 files recovered
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — IRI prefix fix
- `backend/app/browser/apps.py` — navigate enrichment
- `backend/app/notion/executor.py` — Notion import executor
- `backend/app/api/ai.py` — AI features endpoint
- `frontend/static/js/workspace.js` — navigate handler
- `backend/tests/` — 40+ test files recovered
- `e2e/` — 7 E2E specs, 5 mock servers, 1 fixture
- `docs/guide/` — 7 user guide chapters
- `.gsd/KNOWLEDGE.md` — Rules R01-R03, Lesson K003

## Verification
- All Python files pass `ast.parse()` syntax check
- All app manifests validate against `AppManifestSchema`
- Model manifest validates against `ManifestSchema`
- No conflict markers in any recovered files
- Post-recovery audit confirms all milestone-claimed files now exist on disk
