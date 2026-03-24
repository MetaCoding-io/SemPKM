# S07: Integration Verification

**Goal:** E2E Playwright tests prove the Media Scheduler app works end-to-end against the Docker test stack.
**Demo:** `npx playwright test e2e/tests/55-media-scheduler/media-scheduler.spec.ts` passes — covering model install, app install, podcast subscription, tab navigation, rule CRUD, plan generation, status tracking, stats dashboard, and cleanup.

## Must-Haves

- Centralized selectors for Media Scheduler added to `e2e/helpers/selectors.ts`
- Single sequential Playwright spec covering the full app lifecycle (install → use → uninstall)
- Podcast subscription tested via CRUD (dummy URL — no live feed required)
- Schedule rule creation and display tested
- Plan generation triggered and response verified
- Tab navigation across Today/Episodes/Rules/Stats verified
- Status tracking actions (complete/skip/save) tested when plan entries exist
- Stats tab loads with chart canvases present
- Idempotent cleanup (app uninstall + model delete) at start and end
- Spec compiles without TypeScript errors

## Verification

- `cd e2e && npx tsc --noEmit` — spec compiles without errors
- `test -f e2e/tests/55-media-scheduler/media-scheduler.spec.ts` — spec file exists
- `grep -c 'mediaScheduler' e2e/helpers/selectors.ts` returns ≥ 1 — selectors registered

## Tasks

- [ ] **T01: Write Media Scheduler E2E spec with selectors** `est:2h`
  - Why: This is the only task — it produces the complete E2E test proving the assembled Media Scheduler app works end-to-end. The app (S01–S06) is fully built; this slice adds the integration proof.
  - Files: `e2e/helpers/selectors.ts`, `e2e/tests/55-media-scheduler/media-scheduler.spec.ts`
  - Do: Add `mediaScheduler` selector block to `SEL` in `selectors.ts`. Create the spec file following the RSS Reader single-sequential-test pattern (one `test()` with phases). Phases: (0) idempotent cleanup, (1) install model via POST `/admin/models`, (2) install app via admin form + poll for running status, (3) navigate to app and verify layout, (4) add podcast source with dummy URL + verify source appears, (5) tab navigation across all 4 tabs, (6) create schedule rule via form + verify rule card appears, (7) generate plan + verify response, (8) status tracking if entries exist, (9) stats tab with chart canvases, (10) uninstall app + delete model. Set `test.setTimeout(240_000)`. Add `ownerPage.on('dialog', d => d.accept())` for hx-confirm dialogs. Use `waitForIdle` / `page.waitForSelector` for htmx swap timing. For YouTube/Spotify: skip (require real API keys). For podcast polling: skip (source CRUD is sufficient — subscription creates the MediaSource immediately).
  - Verify: `cd e2e && npx tsc --noEmit` passes; `test -f e2e/tests/55-media-scheduler/media-scheduler.spec.ts`
  - Done when: Spec file compiles, contains ≥ 10 test phases, selectors are registered in helpers

## Files Likely Touched

- `e2e/helpers/selectors.ts`
- `e2e/tests/55-media-scheduler/media-scheduler.spec.ts`
