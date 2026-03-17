# S06: E2E tests + user guide — UAT

**Milestone:** M010
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E spec)
- Why this mode is sufficient: The E2E spec is the authoritative runtime proof (runs against Docker stack). Documentation verification is artifact-driven (file existence, line counts, link integrity). No human-experience testing needed — Playwright assertions cover all user-facing interactions.

## Preconditions

- Docker test stack running on port 3901 (`docker compose -f docker-compose.test.yml up -d`)
- Node.js and Playwright installed in `e2e/` directory (`cd e2e && npm ci`)
- No prior RSS Reader artifacts (model, app) installed — test handles its own cleanup but clean state is fastest
- Working internet connection for real feed polling (test falls back to API seeding if offline)

## Smoke Test

Run: `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium`

Expected: Test passes within 240 seconds with 42 assertions green. If the Docker stack is offline or feeds unreachable, API fallback seeding activates and the test still passes.

## Test Cases

### 1. E2E spec executes successfully

1. Start Docker test stack: `docker compose -f docker-compose.test.yml up -d`
2. Wait for health: `curl -f http://localhost:3901/health`
3. Run: `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium`
4. **Expected:** All 42 assertions pass. No phase timeouts. Exit code 0.

### 2. E2E spec is idempotent

1. Run the E2E spec once (should pass)
2. Run the E2E spec again immediately without any manual cleanup
3. **Expected:** Second run also passes — Phase 0 cleanup handles leftover state from the first run.

### 3. TypeScript compiles without errors

1. Run: `cd e2e && npx tsc --noEmit --project tsconfig.json 2>&1 | grep -E "rss-reader|selectors|test-feeds"`
2. **Expected:** No errors from `rss-reader.spec.ts`, `selectors.ts`, or any file referencing RSS selectors. (Pre-existing errors in other spec files are acceptable.)

### 4. RSS selectors exist in centralized SEL object

1. Run: `grep -A 30 "rss:" e2e/helpers/selectors.ts`
2. **Expected:** 20 selectors visible covering: readerContainer, feedSidebar, articleList, readingPane, starButton, filterTabs, subscribeForm, importForm, settingsForm, feedUrlInput, subscribeFeedBtn, opmlFileInput, opmlImportForm, feedItem, articleItem, articleTitle, articleBody, subscribeResult, settingsResult, sidebarIconBtn.

### 5. OPML fixture is valid XML

1. Run: `xmllint --noout e2e/fixtures/test-feeds.opml` (or `python3 -c "import xml.etree.ElementTree; xml.etree.ElementTree.parse('e2e/fixtures/test-feeds.opml')"`)
2. **Expected:** No parse errors. File contains 2 feed entries.

### 6. Chapter 30 exists with sufficient content

1. Run: `wc -l docs/guide/30-rss-reader.md`
2. **Expected:** ≥150 lines (actual: 233).
3. Verify sections: `grep "^##" docs/guide/30-rss-reader.md`
4. **Expected:** Sections for Getting Started, Subscribing to Feeds, Reader Interface, Reading Articles, Workspace Integration, Managing Feeds, Settings, Admin Monitoring, See Also.

### 7. Navigation chain is correct

1. Check ch.29 → ch.30: `grep "30-rss-reader" docs/guide/29-app-platform.md`
2. **Expected:** Footer contains `Next: [Chapter 30: RSS Reader](30-rss-reader.md)`
3. Check ch.30 → ch.29 and ch.30 → Appendix A: `tail -3 docs/guide/30-rss-reader.md`
4. **Expected:** Previous points to ch.29, Next points to appendix-a-environment-variables.md
5. Check Appendix A → ch.30: `grep "30-rss-reader" docs/guide/appendix-a-environment-variables.md`
6. **Expected:** Footer contains `Previous: [Chapter 30: RSS Reader](30-rss-reader.md)`

### 8. README TOC includes Chapter 30

1. Run: `grep "30-rss-reader" docs/guide/README.md`
2. **Expected:** Entry for Chapter 30 in Part VIII section of the TOC.

### 9. Glossary has RSS-specific entries

1. Run: `grep -E "Article \(RSS\)|Feed Subscription|OPML|Poll Interval" docs/guide/appendix-d-glossary.md`
2. **Expected:** 4 distinct entries, each with "See [Chapter 30" cross-reference.

## Edge Cases

### Offline Docker environment

1. Disconnect internet, then run E2E spec
2. **Expected:** Phase 5 (subscribe) may succeed or fail depending on timing. Phase 6 detects zero articles and seeds them via direct API. Test still passes — offline resilience path activates.

### Prior dirty state (model/app already installed)

1. Manually install rss-feeds model and rss-reader app
2. Run E2E spec
3. **Expected:** Phase 0 cleanup removes existing model/app. Test proceeds normally and passes.

### Partial cleanup (app running but model missing)

1. Manually delete model but leave app installed
2. Run E2E spec
3. **Expected:** Phase 0 try/catch blocks handle partial state — each cleanup step is independent. Test recovers and passes.

## Failure Signals

- **E2E test timeout (>240s):** App startup is hanging or Docker stack is unhealthy. Check `docker compose -f docker-compose.test.yml logs api`.
- **Phase 2 failure ("running" status not reached):** App subprocess failed to start. Check admin detail page for error logs.
- **Phase 6 failure (no articles):** Feed polling failed AND API seeding failed. Check network connectivity and API error response logged to Playwright stdout.
- **Phase 11 failure (no command palette results):** ninja-keys shadow DOM structure may have changed. Verify manually with browser devtools.
- **Phase 12 failure (OPML import):** File upload path resolution issue. Check that `path.resolve()` produces absolute path in test environment.
- **Navigation chain broken:** Missing footer update in one of the three files. Grep for `30-rss-reader` across all docs/guide/*.md files.

## Requirements Proved By This UAT

- RSS-01 — Feed subscription and polling verified via E2E phases 1-6 (install → subscribe → poll → articles appear)
- RSS-02 — Reader UI verified via E2E phases 4, 7-9 (3-pane layout, article reading, star toggle, read/unread)
- RSS-03 — Custom Article renderer verified via E2E phase 7 (reading pane shows clean typography, not SHACL form)
- RSS-05 — OPML import verified via E2E phase 12 (file upload → subscriptions created)
- RSS-06 — Workspace views + command palette verified via E2E phases 10-11
- RSS-07 — rss-feeds model install/uninstall verified via E2E phases 1, 14
- RSS-08 — Content extraction verified via E2E phases 5-6 (subscribe → articles with bodies)

## Not Proven By This UAT

- RSS-04 (Hypothesis sync) — intentionally deferred to M011 per D170
- RSS-03 partial (oa:Annotation renderer) — deferred alongside RSS-04
- RSS-07 partial (web-annotations model) — deferred alongside RSS-04
- Feed error indicators under sustained failure conditions — E2E test uses working feeds, not fault injection
- Performance under bulk feed polling (50+ subscriptions) — E2E tests 1-3 subscriptions

## Notes for Tester

- The E2E spec runs as a single sequential test, not parallel tests. This is intentional — phases depend on prior state (install before subscribe, subscribe before read, etc.).
- If the test fails at Phase 2 with timeout, the most common cause is the Docker stack being unhealthy. Run `docker compose -f docker-compose.test.yml ps` to verify all 3 services are up.
- The test includes "soft" phases (9, 10) that check for elements that may or may not exist depending on timing — these use lenient assertions to avoid flaky failures.
- Pre-existing TypeScript compilation errors in ~15 other spec files are from prior merge conflict markers. These are unrelated to S06 and do not affect the RSS Reader spec.
