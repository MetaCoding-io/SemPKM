# S06: E2E tests + user guide — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E)
- Why this mode is sufficient: E2E spec proves runtime behavior against Docker stack. User guide is static documentation verifiable by structural checks and human review.

## Preconditions

1. Docker test stack running on port 3901 (`docker compose -f docker-compose.test.yml up -d` from main tree)
2. Node.js and Playwright installed in `e2e/` directory (`cd e2e && npm install`)
3. The `rss-feeds` model exists in `models/rss-feeds/` and `rss-reader` app exists in `apps/rss-reader/`
4. No pre-existing RSS Reader installation (test handles cleanup, but clean state is ideal)

## Smoke Test

```bash
cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium
```
Test should complete within 240 seconds with all assertions passing.

## Test Cases

### 1. E2E spec compiles without TypeScript errors

1. `cd e2e && npx tsc --noEmit 2>&1 | grep "31-rss-reader\|selectors.ts"`
2. **Expected:** Zero errors from rss-reader spec or selectors.ts. (Pre-existing errors in other files are acceptable.)

### 2. E2E spec has sufficient coverage

1. `grep -c "expect" e2e/tests/31-rss-reader/rss-reader.spec.ts`
2. **Expected:** ≥ 58 assertion calls
3. `grep -c "} catch" e2e/tests/31-rss-reader/rss-reader.spec.ts`
4. **Expected:** ≥ 6 try/catch blocks (cleanup + offline resilience)

### 3. RSS selectors are centralized

1. `grep "rss:" e2e/helpers/selectors.ts`
2. **Expected:** `rss:` section exists in SEL object with selectors for reader container, article items, star button, subscribe dialog, OPML import, settings, etc.

### 4. OPML fixture is valid

1. `python3 -c "import xml.etree.ElementTree as ET; t = ET.parse('e2e/fixtures/test-feeds.opml'); outlines = t.findall('.//outline[@xmlUrl]'); print(f'{len(outlines)} feeds'); assert len(outlines) >= 2"`
2. **Expected:** "2 feeds" with no assertion error

### 5. E2E spec runs against live Docker stack

1. Start Docker test stack: `docker compose -f docker-compose.test.yml up -d`
2. Wait for API health: `curl -s http://localhost:3901/api/health | jq .`
3. Run: `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium`
4. **Expected:** Test passes. All 15 phases complete. Playwright report shows green.

### 6. User guide Chapter 32 exists with sufficient content

1. `wc -l docs/guide/32-rss-reader.md`
2. **Expected:** ≥ 305 lines (or ≥ 150 minimum)
3. Skim the chapter content for: Getting Started, Subscribing, Reader Interface, Reading Articles, Workspace Integration, Feed Management, Settings, Admin Monitoring sections
4. **Expected:** All sections present with meaningful content, not stubs

### 7. README TOC includes Chapter 32

1. `grep "32-rss-reader" docs/guide/README.md`
2. **Expected:** Line like `32. [RSS Reader](32-rss-reader.md)` exists in Part VIII section

### 8. Navigation chain is correct

1. `grep "32-rss-reader" docs/guide/31-api-surface.md`
2. **Expected:** Footer contains `Next: [Chapter 32: RSS Reader](32-rss-reader.md)`
3. `head -5 docs/guide/32-rss-reader.md && tail -5 docs/guide/32-rss-reader.md`
4. **Expected:** Chapter 32 header at top; footer has Previous → ch.31 and Next → Appendix A
5. `grep "32-rss-reader" docs/guide/appendix-a-environment-variables.md`
6. **Expected:** Footer contains `Previous: [Chapter 32: RSS Reader](32-rss-reader.md)`

### 9. Glossary has RSS-specific entries

1. `grep -E "Article \(RSS\)|Feed Subscription|OPML|Poll Interval" docs/guide/appendix-d-glossary.md`
2. **Expected:** All 4 terms present as bold glossary entries with descriptions referencing Chapter 32

## Edge Cases

### E2E offline Docker resilience

1. Run the E2E spec with the Docker stack running but no internet access (disconnect after startup)
2. **Expected:** Phase 6 detects zero articles from polling and seeds test articles via API. Test continues through phases 7–14 using seeded data.

### E2E idempotent re-run

1. Run the E2E spec twice in succession without manual cleanup between runs
2. **Expected:** Phase 0 (cleanup) handles prior state. Second run passes identically to first.

### Guide link integrity

1. `cd docs/guide && for f in 32-rss-reader.md; do grep -oP '\[.*?\]\(\K[^)]+' "$f"; done | while read link; do [ -f "$link" ] || echo "BROKEN: $link"; done`
2. **Expected:** No broken internal links in Chapter 32

## Failure Signals

- E2E spec fails to compile: TypeScript errors in rss-reader.spec.ts or selectors.ts
- E2E runtime failure: Playwright report shows red phases — check `e2e/test-results/` for screenshots
- Phase 2 timeout: App install or health check taking > 120s — check Docker container logs
- Phase 6 seed failure: API returns non-200 — check console output for logged response body
- Phase 10 empty views: Workspace views section not populated — manifest workspace_contributions not registered
- Guide missing sections: Chapter 32 under 150 lines — incomplete documentation
- Broken navigation chain: Footer links point to wrong chapters or missing files

## Requirements Proved By This UAT

- RSS-01 — E2E phases 5–6 prove subscribe + poll lifecycle works end-to-end
- RSS-02 — E2E phases 7–9 prove reader UI, star toggle, mark-read in live browser
- RSS-03 — E2E phase 4 proves custom Article renderer loads from workspace
- RSS-05 — E2E phase 12 proves OPML import creates subscriptions from uploaded file
- RSS-06 — E2E phases 10–11 prove workspace views and command palette entries
- RSS-07 — E2E phase 1 proves rss-feeds model installs correctly
- RSS-08 — Guide documents feed discovery and content extraction features

## Not Proven By This UAT

- Actual feed polling against live internet feeds (E2E uses seeded articles for reliability)
- trafilatura content extraction quality (not exercised in E2E — only the graceful degradation path is tested)
- Feed error indicators for 404/timeout/malformed XML (not covered in E2E phases)
- Performance under 100+ feeds or 10k+ articles (no load testing)
- RSS-04 (Hypothesis sync) — deferred to M011

## Notes for Tester

- The E2E spec has not been executed against a live Docker stack as of this writing — first runtime execution is the real validation gate
- Pre-existing TypeScript errors exist in ~15 other test files from old merge conflicts; these are not related to S06 work
- Phase timing (retry loops, poll intervals) may need adjustment on slow Docker hosts — increase the 240s timeout if phases consistently time out
- The user guide is Chapter 32, not Chapter 30 as the original plan specified — this is correct and intentional (D188)
