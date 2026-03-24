---
estimated_steps: 3
estimated_files: 4
skills_used: []
---

# T02: User guide chapter 49

**Slice:** S06 — Stats Dashboard + Polish
**Milestone:** M038

## Description

Write user guide chapter 49 documenting the Media Scheduler app end-to-end: prerequisites, installing the model and app, adding media sources (podcast RSS, YouTube channels, Spotify playlists), creating schedule rules, today's plan view, the stats dashboard, mobile integration, and troubleshooting. Update all three index files per KNOWLEDGE.md rule.

## Steps

1. **Create `docs/guide/49-media-scheduler.md`** following the structure and tone of `docs/guide/40-rss-reader.md`:
   - Prerequisites section: media-scheduler Mental Model + app installation (reference Ch. 29 App Platform)
   - Installing the Mental Model (path: `media-scheduler`)
   - Installing the App (path: `/app/apps/media-scheduler`)
   - Adding Media Sources: three subsections for Podcast (RSS feed URL), YouTube (channel/playlist URL, API key), Spotify (OAuth connect flow, playlist selection)
   - Schedule Rules: creating conditions (location, activity, time period), actions (source type/category), priority ordering
   - Today's Plan: generating, time slots, action buttons (complete/skip/save), context-driven re-evaluation
   - Stats Dashboard: hours by category chart, top sources chart, weekly activity trend
   - Mobile Integration: current suggestion card, deep links to native apps
   - Troubleshooting: common issues (API keys, OAuth tokens, empty plan, context not updating)

2. **Update `docs/guide/README.md`**: Add `49. [Media Scheduler](49-media-scheduler.md)` to the chapter list, after chapter 48.

3. **Update `docs/guide/index.html`**: Add `<li><a href="#" data-file="49-media-scheduler.md">49. Media Scheduler</a></li>` to the sidebar list, after the chapter 48 entry.

4. **Update `backend/app/templates/guide.html`**: Add a `<button>` entry for chapter 49 following the pattern of existing chapter buttons, with `hx-get="/guide/49-media-scheduler.md"` attribute, after the chapter 48 button.

## Must-Haves

- [ ] Chapter 49 covers all major app features: sources, rules, plan, stats, mobile
- [ ] Chapter follows established guide format (headings, tips, step-by-step instructions)
- [ ] `docs/guide/README.md` lists chapter 49
- [ ] `docs/guide/index.html` lists chapter 49 in sidebar
- [ ] `backend/app/templates/guide.html` lists chapter 49 button

## Verification

- `test -f docs/guide/49-media-scheduler.md` — chapter file exists
- `grep -q "49-media-scheduler" docs/guide/README.md` — TOC updated
- `grep -q "49-media-scheduler" docs/guide/index.html` — sidebar updated
- `grep -q "49-media-scheduler" backend/app/templates/guide.html` — in-app guide updated
- `grep -c "^## " docs/guide/49-media-scheduler.md` returns >= 6 (at least 6 major sections)

## Inputs

- `docs/guide/40-rss-reader.md` — format reference for a similar app guide chapter
- `docs/guide/README.md` — existing TOC to extend
- `docs/guide/index.html` — existing HTML sidebar to extend
- `backend/app/templates/guide.html` — existing in-app guide template to extend
- `apps/media-scheduler/frontend/templates/main.html` — UI reference for describing features
- `apps/media-scheduler/frontend/templates/stats.html` — stats view reference (created by T01)

## Expected Output

- `docs/guide/49-media-scheduler.md` — new user guide chapter
- `docs/guide/README.md` — modified with chapter 49 entry
- `docs/guide/index.html` — modified with chapter 49 sidebar entry
- `backend/app/templates/guide.html` — modified with chapter 49 button
