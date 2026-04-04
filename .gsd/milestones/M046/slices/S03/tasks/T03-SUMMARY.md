---
id: T03
parent: S03
milestone: M046
key_files:
  - e2e/helpers/selectors.ts
  - backend/app/templates/admin/apps/list.html
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-03-29T02:17:13.316Z
blocker_discovered: false
---

# T03: Add 6 E2E selector groups (todoistSync, asanaSync, caldavCalendarSync, googleCalendarSync, outlookCalendarSync, rss), 4 apps selectors, and wrap admin install form in details element

**Add 6 E2E selector groups (todoistSync, asanaSync, caldavCalendarSync, googleCalendarSync, outlookCalendarSync, rss), 4 apps selectors, and wrap admin install form in details element**

## What Happened

Added all 6 planned selector groups to e2e/helpers/selectors.ts, each with selectors derived from the actual HTML templates of the corresponding sync app. Added 4 missing apps selectors (installDetails, installPathInput, sidebarAppsSection, appsTree) used by the RSS reader and app-platform E2E tests. Fixed the admin apps list template by wrapping the install form in a details.install-details element with a summary, matching the E2E test expectation for installDetails.locator('summary').click().

## Verification

TypeScript compilation (npx tsc --noEmit) reports zero errors for any of the 6 new selector groups. Admin template grep confirms details.install-details wrapper is present.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx tsc --noEmit 2>&1 | grep -c 'todoistSync|asanaSync|caldavCalendarSync|googleCalendarSync|outlookCalendarSync|SEL.rss' | grep -q '^0$'` | 0 | ✅ pass | 8000ms |
| 2 | `grep -A5 'install-details' backend/app/templates/admin/apps/list.html` | 0 | ✅ pass | 50ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `e2e/helpers/selectors.ts`
- `backend/app/templates/admin/apps/list.html`
