---
estimated_steps: 5
estimated_files: 2
skills_used:
  - test
  - agent-browser
---

# T01: Write Media Scheduler E2E spec with selectors

**Slice:** S07 — Integration Verification
**Milestone:** M038

## Description

Create a comprehensive E2E Playwright spec for the Media Scheduler app, following the established RSS Reader / App Platform single-sequential-test pattern. Add centralized selectors to the shared selectors file. The spec covers the full lifecycle: cleanup → model install → app install → app navigation → podcast subscription → tab navigation → rule CRUD → plan generation → status tracking → stats dashboard → uninstall.

## Steps

1. Add a `mediaScheduler` block to `SEL` in `e2e/helpers/selectors.ts` with selectors for: container (`#ms-container`), sidebar (`#ms-sidebar`), tabs (`#ms-tabs`), tab content (`#ms-tab-content`), individual tab buttons (`.ms-tab[data-tab="today"]` etc.), sources list (`#ms-sources-list`), source items (`.ms-source-item`), add form toggle (`#ms-toggle-add-form`), add section (`#ms-add-section`), add result (`#ms-add-result`), today view (`.ms-today-view`), plan entries (`.ms-plan-entry`), status badges (`.ms-status-badge`), generate button (`.ms-today-header button`), rules view (`.ms-rules-view`), rule cards (`.ms-rule-card`), rule name (`.ms-rule-name`), rule form area (`#ms-rule-form-area`), rules list (`#ms-rules-list`), stats view (`.ms-stats-view`), stats cards (`.ms-stats-card`), chart canvases (`#ms-chart-hours`, `#ms-chart-top-sources`, `#ms-chart-weekly`), empty state (`.ms-empty-state`), success/error (`.ms-success`, `.ms-error`).

2. Create `e2e/tests/55-media-scheduler/media-scheduler.spec.ts`. Import `test`, `expect`, `BASE_URL` from `../../fixtures/auth`, `SEL` from `../../helpers/selectors`, and `waitForIdle` from `../../helpers/wait-for`. Use `test.describe('Media Scheduler', () => { ... })` with `test.setTimeout(240_000)` and a single `test()` block.

3. Implement Phase 0 (Cleanup): Try to stop+uninstall the app via API (`POST /admin/apps/media-scheduler/stop`, `POST /admin/apps/media-scheduler/uninstall`), then delete the model (`DELETE /admin/models/media-scheduler`). All wrapped in try/catch — failures are expected on first run.

4. Implement Phase 1 (Model Install) + Phase 2 (App Install): POST to `/admin/models` with `path=/app/models/media-scheduler`. Navigate to admin models page, poll for model visibility. Then go to `/admin/apps`, fill install form with `/app/apps/media-scheduler`, submit, poll for running status badge (120s timeout, 5-10s intervals).

5. Implement Phase 3 (App Navigation): Navigate to `${BASE_URL}/app/media-scheduler/`. Wait for `#ms-container` to be visible. Assert sidebar (`#ms-sidebar`) and tabs (`#ms-tabs`) are visible. Wait for `#ms-sources-list` to settle (htmx `hx-trigger="load"`).

6. Implement Phase 4 (Podcast Subscription): Click `#ms-toggle-add-form` to reveal add section. Wait for `#ms-add-section` to be visible (htmx loads the add-source form). Fill the podcast `feed_url` input with `http://example.com/test-podcast.xml` and optional title. Click "Add Podcast" submit button. Assert `.ms-success` appears in `#ms-add-result` (the subscription handler creates a MediaSource immediately via CommandClient, regardless of feed validity). Wait for `sourcesChanged` htmx trigger to refresh `#ms-sources-list`. Assert `.ms-source-item` count ≥ 1.

7. Implement Phase 5 (Tab Navigation): Click `.ms-tab[data-tab="episodes"]` → wait for `#ms-tab-content` content to change → assert `.ms-items-table` or `.ms-empty-state` visible. Click `.ms-tab[data-tab="rules"]` → assert `.ms-rules-view` visible. Click `.ms-tab[data-tab="stats"]` → assert `.ms-stats-view` visible. Click `.ms-tab[data-tab="today"]` → assert `.ms-today-view` visible.

8. Implement Phase 6 (Rule CRUD): Navigate to Rules tab. Click "Add Rule" button (the one with `hx-get="/_fragments/rules/add"`). Wait for `#ms-rule-form-area` to have content (the rule form loads via htmx). Fill form: name = "E2E Test Rule", select activity = "commuting", action type = "source_type" (default), action source type = "podcast". Submit form. Assert `.ms-rule-card` appears in `#ms-rules-list` with `.ms-rule-name` containing "E2E Test Rule".

9. Implement Phase 7 (Plan Generation): Click Today tab. Click "Generate Plan" button. Wait for htmx swap on `#ms-tab-content`. Assert either `.ms-plan-entry` appears (plan generated with content) or `.ms-today-empty` / `.ms-empty-state` persists (no matching content — acceptable since we have a dummy podcast URL with no real episodes).

10. Implement Phase 8 (Status Tracking — conditional): If `.ms-plan-entry` elements exist, find one with action buttons (`.ms-action-complete`), click it. Assert the entry's status changes (`.ms-status-badge` text changes or `.ms-entry-done` appears). If no entries exist, skip this phase with a console log.

11. Implement Phase 9 (Stats Dashboard): Click Stats tab. Assert `.ms-stats-view` visible. Assert all three chart canvases exist: `#ms-chart-hours`, `#ms-chart-top-sources`, `#ms-chart-weekly`. They may show empty state text or render charts — both are valid.

12. Implement Phase 10 (Cleanup): Stop the app via `POST /admin/apps/media-scheduler/stop` (wait 2s). Uninstall via `POST /admin/apps/media-scheduler/uninstall` with `clean_data=true`. Delete model via `DELETE /admin/models/media-scheduler`. Verify the app is gone from admin list.

13. Run `cd e2e && npx tsc --noEmit` to verify the spec compiles without TypeScript errors.

## Must-Haves

- [ ] `mediaScheduler` selector block added to `SEL` in `e2e/helpers/selectors.ts`
- [ ] Spec file at `e2e/tests/55-media-scheduler/media-scheduler.spec.ts`
- [ ] Single sequential test with ≥ 10 phases covering the full lifecycle
- [ ] `test.setTimeout(240_000)` for generous Docker operation timeout
- [ ] `ownerPage.on('dialog', d => d.accept())` for hx-confirm dialogs
- [ ] Idempotent cleanup at both start and end of test
- [ ] TypeScript compiles without errors (`npx tsc --noEmit`)

## Verification

- `cd e2e && npx tsc --noEmit` exits 0
- `test -f e2e/tests/55-media-scheduler/media-scheduler.spec.ts` exits 0
- `grep -c 'mediaScheduler' e2e/helpers/selectors.ts` returns ≥ 1
- `grep -c 'Phase' e2e/tests/55-media-scheduler/media-scheduler.spec.ts` returns ≥ 10

## Inputs

- `e2e/helpers/selectors.ts` — existing centralized selectors to extend
- `e2e/helpers/wait-for.ts` — htmx wait helpers to import
- `e2e/fixtures/auth.ts` — auth fixture providing ownerPage/ownerRequest
- `e2e/tests/31-rss-reader/rss-reader.spec.ts` — reference pattern for single-sequential-test
- `e2e/tests/30-app-platform/app-platform.spec.ts` — reference pattern for app install/uninstall
- `apps/media-scheduler/frontend/templates/main.html` — app layout with CSS selectors
- `apps/media-scheduler/frontend/templates/add-source.html` — add source form structure
- `apps/media-scheduler/frontend/templates/today.html` — plan view with entry actions
- `apps/media-scheduler/frontend/templates/rules.html` — rules view structure
- `apps/media-scheduler/frontend/templates/rule-form.html` — rule creation form fields
- `apps/media-scheduler/frontend/templates/stats.html` — stats dashboard with chart canvases
- `apps/media-scheduler/frontend/templates/sources-list.html` — source items display
- `apps/media-scheduler/frontend/templates/items-list.html` — episodes/items table
- `apps/media-scheduler/frontend/templates/rules-list.html` — rule cards with hx-confirm delete

## Expected Output

- `e2e/helpers/selectors.ts` — modified with `mediaScheduler` selector block
- `e2e/tests/55-media-scheduler/media-scheduler.spec.ts` — new E2E spec file (~400-600 lines)
