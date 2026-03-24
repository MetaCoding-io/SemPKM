---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T02: User guide chapter 48 and index updates

**Slice:** S07 — End-to-End Integration & Acceptance
**Milestone:** M037

## Description

Write the user guide chapter documenting the mobile app and context system, and update all three guide index files. This is a documentation-only task — no code changes.

The chapter covers the full user journey: installing the mobile app, connecting to a SemPKM instance, configuring geofence zones, understanding the context dashboard, setting up auto-persona rules, managing push notification preferences, and reading the workspace context indicator. Follow the style of chapter 33 (Context Overlay) — feature overview, setup steps, usage walkthrough, troubleshooting.

Per KNOWLEDGE.md rule "User guide has THREE files that must stay in sync", all three index files must be updated together.

## Steps

1. **Write `docs/guide/48-mobile-app-context.md`** (~200–300 lines). Structure:
   - Title: "Chapter 48: Mobile App & Context"
   - Overview — what the mobile app does (context provider, not a full SemPKM client), what context means (location zone, activity, time period, calendar event)
   - Prerequisites — SemPKM instance running, API key generated
   - Installation — Expo dev build via `npx expo start`, TestFlight/Play Store for production
   - Onboarding — instance URL input, API key entry, connection test
   - Zone Configuration — MapView interface, adding/editing zones, geofence limits (iOS 20-region limit), enable/disable
   - Context Dashboard — server-reported vs device-detected values, staleness indicator, pull-to-refresh
   - Auto-Persona Rules — navigating to Settings → Context Rules, creating a rule (conditions + target persona), priority ordering, testing against current context
   - Push Notifications — enabling notifications, quiet hours, suppress when busy, notification types, test send
   - Workspace Context Indicator — sidebar chip showing location/activity/time/calendar, real-time SSE updates, stale state appearance
   - Troubleshooting — stale context (check TTL, device connectivity), permission revocation (re-enable in OS Settings), offline behavior (updates lost without offline queue), geofence not triggering (check permissions, zone radius, iOS background restrictions)

2. **Update `docs/guide/README.md`** — Add `48. [Mobile App & Context](48-mobile-app-context.md)` to the table of contents. Place it after line `47. [Asana Sync](47-asana-sync.md)` in the sync apps section, or create a new "Part X: Mobile & Context" section if more appropriate. Check existing structure to find the right insertion point.

3. **Update `docs/guide/index.html`** — Add `<li><a href="#" data-file="48-mobile-app-context.md">48. Mobile App & Context</a></li>` in the sidebar chapter list. Place it after the Asana Sync entry (line referencing `47-asana-sync.md`).

4. **Update `backend/app/templates/guide.html`** — Add a `<button>` entry following the pattern of existing chapters. Use `smartphone` as the Lucide icon name. Place after the Asana Sync button entry:
   ```html
   <button class="docs-chapter-item"
           hx-get="/guide/48-mobile-app-context.md"
           hx-target="#app-content"
           hx-swap="innerHTML"
           hx-push-url="true">
     <i data-lucide="smartphone"></i>
     <span>48. Mobile App & Context</span>
   </button>
   ```

## Must-Haves

- [ ] `docs/guide/48-mobile-app-context.md` exists with 200+ lines of substantive content
- [ ] Chapter covers: overview, installation, onboarding, zones, dashboard, rules, notifications, indicator, troubleshooting
- [ ] `docs/guide/README.md` references `48-mobile-app-context.md`
- [ ] `docs/guide/index.html` references `48-mobile-app-context.md`
- [ ] `backend/app/templates/guide.html` references `48-mobile-app-context.md`

## Verification

- `test -f docs/guide/48-mobile-app-context.md` — file exists
- `wc -l docs/guide/48-mobile-app-context.md` — 200+ lines
- `grep -q '48-mobile-app-context' docs/guide/README.md` — README references chapter
- `grep -q '48-mobile-app-context' docs/guide/index.html` — index.html references chapter
- `grep -q '48-mobile-app-context' backend/app/templates/guide.html` — guide.html references chapter

## Inputs

- `docs/guide/33-context-overlay.md` — style reference (257 lines, feature overview + setup + usage + troubleshooting)
- `docs/guide/README.md` — existing table of contents (insert after chapter 47)
- `docs/guide/index.html` — existing sidebar (insert after 47-asana-sync.md entry)
- `backend/app/templates/guide.html` — existing chapter buttons (insert after 47-asana-sync.md button)

## Expected Output

- `docs/guide/48-mobile-app-context.md` — new user guide chapter
- `docs/guide/README.md` — modified with chapter 48 entry
- `docs/guide/index.html` — modified with chapter 48 sidebar link
- `backend/app/templates/guide.html` — modified with chapter 48 button
