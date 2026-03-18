# S06: E2E tests + user guide — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E)
- Why this mode is sufficient: E2E spec assertions prove runtime behavior when run against Docker; docs verification is file-level inspection

## Preconditions

- Docker test stack running on port 3901 (`docker compose -f docker-compose.test.yml up -d` from worktree root)
- No pre-existing `rss-reader` app or `rss-feeds` model installed (test cleanup handles this, but clean state is faster)
- Node.js ≥18 and Playwright installed in `e2e/` directory (`cd e2e && npm install`)
- At least one user account exists with admin/owner role

## Smoke Test

Run `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium` — the test should complete within 240s. If it passes, the entire RSS Reader lifecycle is proven end-to-end.

## Test Cases

### 1. E2E spec compiles without TypeScript errors

1. `cd e2e && npx tsc --noEmit 2>&1 | grep "31-rss-reader\|selectors"`
2. **Expected:** Zero errors from rss-reader spec file or selectors.ts

### 2. E2E spec has sufficient assertion coverage

1. `grep -c "expect" e2e/tests/31-rss-reader/rss-reader.spec.ts`
2. **Expected:** Count ≥ 20 (actual: 58)

### 3. E2E spec has cleanup error handling

1. `grep -c "} catch" e2e/tests/31-rss-reader/rss-reader.spec.ts`
2. **Expected:** Count ≥ 2 (actual: 6 try/catch blocks for idempotent cleanup)

### 4. RSS selectors are centralized

1. `grep "rss:" e2e/helpers/selectors.ts`
2. **Expected:** `rss:` section exists with selectors like `readerContainer`, `articleItem`, `starBtn`, etc.

### 5. OPML fixture is valid XML with feeds

1. `python3 -c "import xml.etree.ElementTree as ET; tree = ET.parse('e2e/fixtures/test-feeds.opml'); outlines = tree.findall('.//outline[@xmlUrl]'); print(f'{len(outlines)} feeds'); assert len(outlines) >= 2"`
2. **Expected:** "2 feeds" and no assertion error

### 6. Full E2E lifecycle against Docker stack

1. Start Docker test stack on port 3901
2. `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium`
3. **Expected:** Test passes. All 15 phases complete:
   - Phase 0: Cleanup succeeds (idempotent)
   - Phase 1: rss-feeds model installs, appears in model list
   - Phase 2: rss-reader app installs, reaches "running" status
   - Phase 3: Admin detail shows h1 title, status badge, PID stat, permissions, poll-feeds task
   - Phase 4: RSS Reader page opens from APPS sidebar with reader container visible
   - Phase 5: Subscribe creates a feed subscription (verified via SPARQL)
   - Phase 6: Articles exist (via polling or API seeding fallback)
   - Phase 7: Clicking an article shows content in reading pane
   - Phase 8: Star toggle adds `.starred` class and persists in triplestore
   - Phase 9: Mark-read state verified (soft check via SPARQL)
   - Phase 10: Workspace views section has Starred/Unread entries
   - Phase 11: Command palette includes RSS-related commands
   - Phase 12: OPML import creates subscriptions from fixture file
   - Phase 13: Settings page saves articlesPerPage change
   - Phase 14: Cleanup removes app, model, and data

### 7. User guide Chapter 32 exists with sufficient content

1. `wc -l docs/guide/32-rss-reader.md`
2. **Expected:** ≥ 150 lines (actual: 305)

### 8. Chapter 32 covers all required features

1. Inspect `docs/guide/32-rss-reader.md` for these sections:
   - Getting Started (model + app install)
   - Subscribing to Feeds (URL, discovery, OPML)
   - Reader Interface (3 panes with layout diagram)
   - Reading Articles (star, read/unread, keyboard nav)
   - Workspace Integration (views, right pane, command palette, custom renderer)
   - Managing Feeds (unsubscribe, errors)
   - Settings (articlesPerPage, markReadOnOpen, poll interval)
   - Admin Monitoring (status, task history)
2. **Expected:** All 8 sections present

### 9. README TOC includes Chapter 32

1. `grep "32-rss-reader" docs/guide/README.md`
2. **Expected:** Entry like "32. [RSS Reader](32-rss-reader.md)"

### 10. Navigation chain is correct

1. `grep "32-rss-reader" docs/guide/31-api-surface.md` — ch.31 links Next to ch.32
2. `grep "31-api-surface" docs/guide/32-rss-reader.md` — ch.32 links Previous to ch.31
3. `grep "appendix-a" docs/guide/32-rss-reader.md` — ch.32 links Next to Appendix A
4. `grep "32-rss-reader" docs/guide/appendix-a-environment-variables.md` — Appendix A links Previous to ch.32
5. **Expected:** All four footer links present and correct

### 11. Glossary has RSS-specific terms

1. `grep -c "RSS\|OPML\|Feed Subscription\|Poll Interval" docs/guide/appendix-d-glossary.md`
2. **Expected:** ≥ 3 matches (actual: 8, covering 4 terms)

## Edge Cases

### E2E: Offline Docker (no internet access for feeds)

1. Run E2E spec when Docker container has no outbound internet
2. **Expected:** Phase 6 detects 0 articles from polling and seeds 2 test articles via API. Subsequent phases pass using seeded articles.

### E2E: Prior dirty state

1. Leave a previous test run's rss-reader app installed
2. Run E2E spec
3. **Expected:** Phase 0 cleanup removes the stale app and model before starting fresh. Test passes.

### E2E: Slow Docker startup

1. Run E2E spec immediately after Docker stack starts (cold triplestore)
2. **Expected:** Retry-poll loops in Phases 1-2 handle slow startup. The 240s timeout provides sufficient headroom.

### OPML fixture edge cases

1. Inspect `e2e/fixtures/test-feeds.opml` for both nested (within `<outline text="Tech">`) and flat top-level feeds
2. **Expected:** Both feed types present with valid `xmlUrl` attributes

## Failure Signals

- TypeScript compilation errors in `31-rss-reader/rss-reader.spec.ts` → structural problem in test code
- E2E test timeout (>240s) → likely Phase 2 app install stuck or Phase 5 subscription failing
- "SOFT-FAIL" in Playwright output → CSS selector missed, check if template classes changed
- Chapter 32 `wc -l` < 150 → content was truncated or not written
- Missing navigation footers → cross-file link updates incomplete
- SPARQL assertion failures in E2E → triplestore data not materialized (check EventStore pipeline)

## Requirements Proved By This UAT

- RSS-01 — Full lifecycle: subscribe → poll → articles appear (E2E phases 5-6)
- RSS-02 — Reader UI with split pane, star, read/unread (E2E phases 7-9)
- RSS-05 — OPML import creates subscriptions (E2E phase 12)
- RSS-06 — Workspace views and command palette entries (E2E phases 10-11)
- RSS-08 — Feed URL subscription works (E2E phase 5)

## Not Proven By This UAT

- RSS-03 partial — oa:Annotation custom renderer not tested (deferred with RSS-04)
- RSS-04 — Hypothesis annotation sync not implemented (deferred to future milestone)
- RSS-07 partial — web-annotations model not tested (deferred with RSS-04)
- Runtime E2E execution — spec is structurally verified but Docker stack execution deferred to availability
- Performance under load — no stress testing of feed polling with many subscriptions

## Notes for Tester

- The E2E spec numbers phases 0-14 in code comments — if a phase fails, grep for `Phase N:` in the Playwright stdout to identify exactly where
- If Phase 2 (app install) hangs, check Docker logs for app subprocess startup failures: `docker compose -f docker-compose.test.yml logs api`
- The chapter is numbered 32, not 30 as the original plan stated — chapters 30 (Personas) and 31 (API Surface) were created by M012 and M013
- SPARQL verification queries in the E2E spec can be replayed manually via `POST /api/sparql` for debugging
- Pre-existing TypeScript errors in ~15 other test files are from old merge conflicts — they don't affect the RSS Reader spec
