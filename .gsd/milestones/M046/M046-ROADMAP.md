# M046: 

## Vision
Fix all 62 failing E2E tests across 7 failure categories. The test suite is the project's regression safety net — at 19% failure rate it provides false confidence. After this milestone, the full 122-spec suite passes reliably against the Docker test stack.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Auth Fixture — Session Caching & Member Login | high | — | ⬜ | Auth-dependent tests (admin-access-control, member-permissions, dark-mode, session-management) all pass without magic link failures |
| S02 | Copilot Bottom Panel — Z-Index Fix | low | — | ⬜ | All 5 copilot tests pass — AI COPILOT tab button is clickable regardless of editor-empty overlay state |
| S03 | App Platform — Subprocess Lifecycle in Test Container | high | — | ⬜ | Sync app tests (linear, github, jira, monday, todoist, caldav, asana, app-platform) find running processes and render settings UI |
| S04 | Ontology Viewer — Locator Scoping for Dockview Panels | low | — | ⬜ | Ontology viewer and class creation tests pass without 'resolved to 2 elements' strict mode errors |
| S05 | Calendar, Recurring Tasks & Setup Wizard Fixes | medium | — | ⬜ | Calendar view, recurring task, and setup wizard tests all pass |
| S06 | Miscellaneous Failures & Full Suite Verification | medium | S01, S02, S03, S04, S05 | ⬜ | Full `npx playwright test` run passes with 0 failures across all 122 specs |
