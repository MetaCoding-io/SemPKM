---
id: T02
parent: S06
milestone: M038
provides:
  - User guide chapter 49 documenting the Media Scheduler app end-to-end
  - Updated guide TOC, HTML sidebar, and in-app guide template with chapter 49
key_files:
  - docs/guide/49-media-scheduler.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
key_decisions:
  - Used "radio" Lucide icon for guide.html button, matching the manifest's ui.pages icon
patterns_established: []
observability_surfaces:
  - none (documentation-only task)
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: User guide chapter 49

**Write chapter 49 documenting the Media Scheduler app (sources, rules, plan, stats, mobile, troubleshooting) and update all three guide index files**

## What Happened

Created `docs/guide/49-media-scheduler.md` with 13 major sections following the structure and tone of chapter 40 (RSS Reader). The chapter covers: prerequisites and installation (Mental Model + app), the scheduler interface layout (sidebar + 4 tabs), adding media sources (podcasts via RSS, YouTube channels/playlists with API key, Spotify playlists via OAuth PKCE flow), schedule rules (creation, evaluation logic, enable/disable/delete), today's plan view (time slots, complete/skip/save actions, context re-evaluation), the stats dashboard (hours by category, top sources, weekly activity charts), managing sources (removal, poll settings per task type, error handling), mobile integration (context service subscription), admin monitoring (status, task history, permissions), and troubleshooting (missing episodes, YouTube quota, Spotify OAuth, empty plans, context issues).

Updated all three guide index files per KNOWLEDGE.md rule: `docs/guide/README.md` (TOC entry after chapter 48), `docs/guide/index.html` (sidebar `<li>` after chapter 48), and `backend/app/templates/guide.html` (htmx button with `radio` icon after chapter 48).

## Verification

All 5 task-level checks pass: chapter file exists, TOC updated, sidebar updated, in-app guide updated, section count ≥ 6 (actual: 13). All 7 slice-level checks pass: 19 stats tests pass, both AST syntax checks pass, stats template exists, chapter file exists, and all three index files contain the chapter reference.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "stats" --tb=short` | 0 | ✅ pass | 0.33s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/stats_service.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `test -f apps/media-scheduler/frontend/templates/stats.html` | 0 | ✅ pass | <1s |
| 5 | `test -f docs/guide/49-media-scheduler.md` | 0 | ✅ pass | <1s |
| 6 | `grep -q "49-media-scheduler" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 7 | `grep -q "49-media-scheduler" docs/guide/index.html` | 0 | ✅ pass | <1s |
| 8 | `grep -q "49-media-scheduler" backend/app/templates/guide.html` | 0 | ✅ pass | <1s |
| 9 | `grep -c "^## " docs/guide/49-media-scheduler.md` (≥ 6) | 0 | ✅ pass (13) | <1s |

## Diagnostics

None — documentation-only task with no runtime behavior.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/49-media-scheduler.md` — new user guide chapter covering the full Media Scheduler app
- `docs/guide/README.md` — added chapter 49 entry after chapter 48 in the TOC
- `docs/guide/index.html` — added chapter 49 sidebar link after chapter 48
- `backend/app/templates/guide.html` — added chapter 49 button with `radio` icon after chapter 48
