# S06: E2E tests + user guide

**Goal:** Playwright E2E spec covers the full RSS Reader lifecycle (install → subscribe → poll → read → star → workspace views → admin → uninstall) and a user guide Chapter 30 documents RSS Reader setup and usage.
**Demo:** `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium` passes against the Docker test stack. `docs/guide/30-rss-reader.md` exists with ≥150 lines, navigation chain is correct (ch.29 → ch.30 → Appendix A), and glossary has RSS-specific terms.

## Must-Haves

- Playwright E2E spec in `e2e/tests/31-rss-reader/rss-reader.spec.ts` with ≥20 assertions covering model install, app install, reader UI, star/read toggles, workspace views, command palette, OPML import, settings, admin task history, and cleanup
- RSS selectors added to `e2e/helpers/selectors.ts` centralized `SEL` object
- OPML test fixture at `e2e/fixtures/test-feeds.opml`
- User guide `docs/guide/30-rss-reader.md` with ≥150 lines covering all RSS Reader features
- Navigation chain: ch.29 footer → ch.30, ch.30 footer → Appendix A, Appendix A footer → ch.30
- ≥3 RSS-specific glossary entries in `docs/guide/appendix-d-glossary.md`
- `docs/guide/README.md` TOC includes Chapter 30

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (E2E runs against Docker stack)
- Human/UAT required: no (Playwright assertions are sufficient)

## Verification

- `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium` — passes against Docker test stack on port 3901
- `cd e2e && npx tsc --noEmit` — TypeScript compiles without errors (catches structural/import issues before runtime)
- `grep -c "try.*catch" e2e/tests/31-rss-reader/rss-reader.spec.ts` — ≥2 (cleanup and offline-resilience error handling present)
- `wc -l docs/guide/30-rss-reader.md` — ≥150 lines
- `grep -c "Chapter 30" docs/guide/README.md` — ≥1
- `grep "30-rss-reader" docs/guide/29-app-platform.md` — present (updated footer)
- `grep "30-rss-reader" docs/guide/appendix-a-environment-variables.md` — present (updated footer)
- `grep -c "RSS\|OPML\|Feed Subscription\|Article.*RSS\|Poll Interval" docs/guide/appendix-d-glossary.md` — ≥3 new terms

## Integration Closure

- Upstream surfaces consumed: All S01-S05 deliverables — RSS Reader app templates (stable `data-*` selectors from S03), workspace contributions (S04 manifest), OPML import/settings (S05 routes), feed service (S02)
- New wiring introduced in this slice: none (E2E spec and docs don't introduce runtime wiring)
- What remains before the milestone is truly usable end-to-end: nothing — S06 is the final slice

## Observability / Diagnostics

- **Test report output**: Playwright HTML report written to `e2e/playwright-report/` after each run — shows per-phase timing, screenshot on failure, and assertion diffs. Inspect with `npx playwright show-report`.
- **Failure screenshots**: On test failure, Playwright captures a viewport screenshot saved in `e2e/test-results/` — the first diagnostic artifact for debugging.
- **Phase-level structure**: The single sequential test uses comment headers (`// Phase N: ...`) — grep-visible in test output for locating which phase failed.
- **Retry loop observability**: Each retry loop logs `attempt` count; on timeout, the assertion message includes "after N attempts" for diagnosing slow startup vs. actual failure.
- **Offline Docker resilience**: If article seeding via API fails (500), the error response body is logged via `console.log` in the test — visible in Playwright's stdout capture.
- **OPML import result attributes**: `data-created`, `data-duplicates`, `data-errors` on the result div — test asserts on these for structured pass/fail, not just text content.
- **Redaction**: No secrets in test output. Session cookies are injected via Playwright fixtures, never logged. The setup token is read inside `auth.ts` and never printed.

## Failure-Path Verification

- TypeScript compilation (`npx tsc --noEmit`) catches structural errors before runtime
- Cleanup phase at test start ensures idempotency — if a prior run left dirty state, cleanup removes it
- Each API call in cleanup is wrapped in try/catch — partial cleanup doesn't abort the test
- Offline Docker detection: article count check after subscribe; if zero, API-seeded articles are used as fallback

## Tasks

- [x] **T01: Playwright E2E spec for RSS Reader full lifecycle** `est:1h`
  - Why: Authoritative proof that the RSS Reader works end-to-end against a live Docker stack — validates all S01-S05 deliverables and covers RSS-01 through RSS-08 (active) requirements
  - Files: `e2e/tests/31-rss-reader/rss-reader.spec.ts`, `e2e/helpers/selectors.ts`, `e2e/fixtures/test-feeds.opml`
  - Do: Add `rss` section to SEL in selectors.ts with RSS Reader UI selectors. Create OPML test fixture with 2-3 feeds. Write single sequential `test()` with 14 phases: cleanup → install model → install app → admin detail → workspace integration → subscribe → article display → star → read/unread → workspace views → command palette → OPML import → settings → cleanup. Use 240s timeout. Resilient to offline Docker (seed articles via API if polling doesn't produce them). Copy retry patterns from `app-platform.spec.ts`.
  - Verify: `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium` passes
  - Done when: E2E spec passes with ≥20 assertions covering all phases, test is idempotent (cleanup handles prior state)

- [x] **T02: User guide Chapter 30 and navigation chain updates** `est:40m`
  - Why: Documents the RSS Reader for users — the standing requirement for M010 milestone completion
  - Files: `docs/guide/30-rss-reader.md`, `docs/guide/README.md`, `docs/guide/29-app-platform.md`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Write Chapter 30 covering: Getting Started (install model + app), Subscribing to Feeds (URL, discovery, OPML import), Reader Interface (3 panes), Reading Articles (open, star, read/unread, keyboard nav), Workspace Integration (views, right pane, command palette, custom renderer), Managing Feeds (unsubscribe, error indicators), Settings (articlesPerPage, markReadOnOpen, poll interval), Admin Monitoring (status, task history). Update README.md TOC. Fix navigation chain (ch.29 → ch.30 → Appendix A). Add ≥3 glossary entries (Article, Feed Subscription, OPML, Poll Interval).
  - Verify: `wc -l docs/guide/30-rss-reader.md` ≥150 lines; `grep "30-rss-reader" docs/guide/29-app-platform.md`; `grep "30-rss-reader" docs/guide/appendix-a-environment-variables.md`
  - Done when: Chapter 30 exists with ≥150 lines, TOC updated, navigation chain correct, ≥3 glossary entries added

## Files Likely Touched

- `e2e/tests/31-rss-reader/rss-reader.spec.ts` (new)
- `e2e/helpers/selectors.ts` (add `rss` section)
- `e2e/fixtures/test-feeds.opml` (new)
- `docs/guide/30-rss-reader.md` (new)
- `docs/guide/README.md` (TOC update)
- `docs/guide/29-app-platform.md` (footer update)
- `docs/guide/appendix-a-environment-variables.md` (footer update)
- `docs/guide/appendix-d-glossary.md` (new terms)
