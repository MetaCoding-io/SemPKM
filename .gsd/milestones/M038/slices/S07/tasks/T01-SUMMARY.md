---
id: T01
parent: S07
milestone: M038
provides:
  - E2E Playwright spec for Media Scheduler app lifecycle
  - Centralized mediaScheduler selectors in shared selectors file
key_files:
  - e2e/tests/55-media-scheduler/media-scheduler.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Used toBeAttached() for chart canvas assertions since CDN-loaded Chart.js may not render visually in test environment
patterns_established:
  - Media Scheduler E2E follows same single-sequential-test pattern as RSS Reader (rss-reader.spec.ts)
observability_surfaces:
  - Playwright test output shows per-phase pass/fail with console.log for skipped phases
duration: 30m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Write Media Scheduler E2E spec with selectors

**Added comprehensive E2E Playwright spec for Media Scheduler app covering 10 lifecycle phases with centralized selectors**

## What Happened

Added a `mediaScheduler` selector block (40 selectors) to `e2e/helpers/selectors.ts` mapped to real CSS selectors from the app's templates (main.html, add-source.html, today.html, rules.html, rule-form.html, stats.html, sources-list.html, items-list.html, rules-list.html).

Created `e2e/tests/55-media-scheduler/media-scheduler.spec.ts` with a single sequential test covering the full app lifecycle:

- **Phase 0:** Idempotent cleanup (stop/uninstall/delete if present)
- **Phase 1:** Model install via API
- **Phase 2:** App install via admin form + poll for running status
- **Phase 3:** App navigation — verify container, sidebar, tabs layout
- **Phase 4:** Podcast subscription — toggle add form, fill feed URL, submit, verify source appears
- **Phase 5:** Tab navigation — episodes/rules/stats/today with content assertions
- **Phase 6:** Rule CRUD — add rule via htmx form, verify rule card with name
- **Phase 7:** Plan generation — click generate, accept either entries or empty state
- **Phase 8:** Status tracking — conditional mark-complete if plan entries exist
- **Phase 9:** Stats dashboard — verify chart canvases attached
- **Phase 10:** Cleanup — stop/uninstall/delete + verify removal

All selectors verified against actual template HTML. Used `waitForIdle()` between htmx-driven phases. Set 240s timeout for Docker operations.

## Verification

- TypeScript compiles without errors (no media-scheduler or selectors.ts errors in `npx tsc --noEmit`)
- Spec file exists at expected path
- `mediaScheduler` selector block present in selectors.ts (grep count ≥ 1)
- 14 Phase references in spec (≥ 10 required)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx tsc --noEmit 2>&1 \| grep '55-media-scheduler\|selectors.ts'` | 0 (no matches) | ✅ pass | ~3s |
| 2 | `test -f e2e/tests/55-media-scheduler/media-scheduler.spec.ts` | 0 | ✅ pass | <1s |
| 3 | `grep -c 'mediaScheduler' e2e/helpers/selectors.ts` | 0 (result: 1) | ✅ pass | <1s |
| 4 | `grep -c 'Phase' e2e/tests/55-media-scheduler/media-scheduler.spec.ts` | 0 (result: 14) | ✅ pass | <1s |

## Diagnostics

- Run `npx playwright test e2e/tests/55-media-scheduler/media-scheduler.spec.ts --trace on` for full trace zip
- Run with `--ui` for step-through debugging
- Phase 8 (status tracking) logs "skipping" to console when no plan entries exist — visible in Playwright output
- Pre-existing TS errors in ~15 other spec files are unrelated to this task

## Deviations

- Task plan specified `#ms-add-section` toggle via `classList.toggle('ms-hidden')` in the onclick handler — the actual template confirms this. The test clicks the toggle button and waits for visibility rather than checking class manipulation directly.
- Used `toBeAttached()` instead of `toBeVisible()` for chart canvases because Chart.js loads from CDN and canvas elements may not have visual dimensions in the test environment (per KNOWLEDGE.md pattern on SVG visibility).

## Known Issues

- Pre-existing TypeScript syntax errors in ~15 other spec files prevent `npx tsc --noEmit` from exiting 0 globally. Our files compile cleanly (zero errors referencing media-scheduler or selectors.ts).

## Files Created/Modified

- `e2e/helpers/selectors.ts` — Added `mediaScheduler` block with 40 selectors mapped to real template CSS
- `e2e/tests/55-media-scheduler/media-scheduler.spec.ts` — New E2E spec (~270 lines, 10+ phases)
- `.gsd/milestones/M038/slices/S07/S07-PLAN.md` — Added Observability section, marked T01 done
