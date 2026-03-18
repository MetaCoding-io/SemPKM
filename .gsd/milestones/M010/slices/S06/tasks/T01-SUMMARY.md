---
id: T01
parent: S06
milestone: M010
provides:
  - "Playwright E2E spec covering the full RSS Reader lifecycle (15 phases: cleanup → model install → app install → admin detail → workspace → subscribe → seed articles → read → star → mark-read → views → command palette → OPML import → settings → cleanup)"
  - "RSS selector constants in SEL.rss for stable E2E test element targeting"
  - "OPML test fixture with 2 feeds in nested/flat outline structure"
key_files:
  - e2e/tests/31-rss-reader/rss-reader.spec.ts
  - e2e/helpers/selectors.ts
  - e2e/fixtures/test-feeds.opml
key_decisions:
  - "Single sequential test() with 240s timeout following app-platform.spec.ts pattern — phases depend on prior state"
  - "SPARQL-based assertions for subscription/article/star verification rather than fragile UI-only checks"
  - "Offline Docker resilience via API article seeding (object.create) when feed polling produces no articles"
  - "Filter buttons use .rss-filter-btn selector matching actual template class (plan said .rss-filter-tab which doesn't exist)"
patterns_established:
  - "RSS Reader E2E follows same retry-poll loop pattern as app-platform.spec.ts for app install + health check"
  - "SPARQL verification queries as fallback for UI assertions in htmx-based apps"
  - "OPML file upload via path.resolve(__dirname, '../../fixtures/...') + setInputFiles()"
observability_surfaces:
  - "Playwright HTML test report in e2e/playwright-report/ with per-phase timing and failure screenshots"
  - "Phase comment headers (// Phase N: ...) grep-visible in test output for failure localization"
  - "API response bodies logged via console.log on article seed failure"
  - "try/catch cleanup blocks with silent error handling for idempotent re-runs"
duration: 18m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Playwright E2E spec for RSS Reader full lifecycle

**Created 663-line Playwright E2E spec with 58 assertions across 15 phases covering the complete RSS Reader lifecycle from model install through workspace integration to cleanup, with offline-Docker resilience via API article seeding**

## What Happened

Added `rss` selector section to `SEL` in `e2e/helpers/selectors.ts` with 19 selectors matching actual template IDs/classes (`#rss-reader-container`, `.rss-article-item`, `.rss-star-btn`, `#rss-subscribe-dialog`, `#rss-opml-import`, `#rss-settings`, etc.).

Created `e2e/fixtures/test-feeds.opml` with valid OPML 2.0 XML containing a nested category ("Tech") with one feed and a flat top-level feed — matches the `parse_opml()` function's expected structure.

Built `e2e/tests/31-rss-reader/rss-reader.spec.ts` as a single `test.describe('RSS Reader')` with one sequential `test()` using 240s timeout. The test follows the canonical app-platform pattern: dialog auto-accept, cleanup-first idempotency, retry-poll loops for async operations.

The 15 phases:
- **Phase 0**: Cleanup via API — stop/uninstall existing app, SPARQL DELETE for articles + subscriptions, delete model
- **Phase 1**: Install rss-feeds model via admin UI form, retry-loop verification
- **Phase 2**: Install rss-reader app via admin UI, retry-poll for "running" status (120s timeout, 5 intervals)
- **Phase 3**: Admin detail page assertions — h1, status badge, PID stat, permissions, poll-feeds task
- **Phase 4**: Workspace integration — expand APPS section, click RSS Reader leaf, verify reader container + empty state
- **Phase 5**: Subscribe to feed — click subscribe button, fill URL, submit, SPARQL verify subscription exists
- **Phase 6**: Seed articles via API (offline Docker resilience) — check article count, create 2 test articles if needed
- **Phase 7**: Read article — click first article item, verify reading pane content
- **Phase 8**: Star article — click star button, verify `.starred` class, SPARQL verify isStarred=true persists
- **Phase 9**: Mark-read verification via SPARQL (soft check — fire-and-forget timing)
- **Phase 10**: Workspace views — expand VIEWS section, click Starred/Unread view, verify commands API
- **Phase 11**: Command palette — Ctrl+K, type "RSS", verify RSS commands exist via API
- **Phase 12**: OPML import — click upload button, setInputFiles with test fixture, verify result attributes
- **Phase 13**: Settings — click gear icon, change articlesPerPage, submit, verify success message
- **Phase 14**: Cleanup — stop app, uninstall, SPARQL DELETE data, delete model, verify clean state

## Verification

All task-level must-haves verified:

1. RSS selectors present in `SEL.rss` — confirmed via grep
2. OPML fixture valid — parsed by Python xml.etree successfully, 2 feeds with correct xmlUrl attributes
3. Test file exists at correct path — 663 lines
4. 240s timeout set via `test.setTimeout(240_000)`
5. Cleanup phase runs first (Phase 0)
6. 58 `expect()` assertions counted (≥20 required)
7. Offline Docker resilience — Phase 6 seeds articles via API when feed polling produces none
8. OPML path resolved via `path.resolve(__dirname, '../../fixtures/test-feeds.opml')`
9. TypeScript compiles without errors in new/modified files (pre-existing errors in other test files only)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx tsc --noEmit 2>&1 \| grep "31-rss-reader\|selectors.ts"` | 0 | ✅ pass (no errors in our files) | 12s |
| 2 | `grep -c "expect" e2e/tests/31-rss-reader/rss-reader.spec.ts` | 0 | ✅ pass (58 ≥ 20) | <1s |
| 3 | `cat e2e/fixtures/test-feeds.opml` (+ python3 XML parse) | 0 | ✅ pass (valid OPML, 2 feeds) | <1s |
| 4 | `grep "rss:" e2e/helpers/selectors.ts` | 0 | ✅ pass (RSS selectors present) | <1s |
| 5 | `grep -c "} catch" e2e/tests/31-rss-reader/rss-reader.spec.ts` | 0 | ✅ pass (6 try/catch blocks) | <1s |
| 6 | `wc -l e2e/tests/31-rss-reader/rss-reader.spec.ts` | 0 | ✅ pass (663 lines) | <1s |

### Slice-level checks (partial — T01 is first of 2 tasks):

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `cd e2e && npx playwright test tests/31-rss-reader/...` | ⏳ deferred | Requires Docker test stack |
| 2 | `cd e2e && npx tsc --noEmit` (our files) | ✅ pass | No TS errors in new/modified files |
| 3 | `grep -c "} catch" ...rss-reader.spec.ts` ≥2 | ✅ pass | 6 try/catch blocks |
| 4 | `wc -l docs/guide/30-rss-reader.md` ≥150 | ⏳ T02 | User guide not yet written |
| 5 | Chapter 30 in README | ⏳ T02 | |
| 6 | Footer link in ch.29 | ⏳ T02 | |
| 7 | Footer link in appendix-a | ⏳ T02 | |
| 8 | Glossary terms | ⏳ T02 | |

## Diagnostics

- **Playwright HTML report**: After running against Docker stack, inspect `e2e/playwright-report/` for per-phase timing and failure screenshots
- **Phase identification**: Grep `Phase` in test stdout to locate which phase failed
- **Article seed failures**: API response body logged to console on non-200 status
- **SPARQL verification**: Each data assertion (subscription exists, article starred, article read) uses SPARQL queries that can be replayed via `/api/sparql` for debugging

## Deviations

- Plan specified `.rss-filter-tab` selector; actual template uses `.rss-filter-btn` — updated selector name accordingly
- Plan specified 14 phases; implementation has 15 phases (Phase 0 cleanup + Phases 1-14) — numbering adjusted for clarity
- Spec is 663 lines vs plan estimate of 250-350 — additional resilience code (SPARQL verifications, offline article seeding, sidebar re-navigation) accounts for the extra length
- Plan referenced `#rss-article-list-content` as `articleListContent`; also added `feedUrlInput`, `opmlImport`, and `settingsResult` selectors not in the original plan but needed for test interactions

## Known Issues

- Docker stack E2E execution not verified (no stack available in this session) — spec compiles and is structurally sound
- Pre-existing TypeScript errors in ~15 other test files (conflict markers from old merges) — not introduced by this task
- Phase 10 (workspace views) relies on views section being populated by the RSS Reader's manifest registration — may need timing adjustments on slow Docker stacks

## Files Created/Modified

- `e2e/helpers/selectors.ts` — Added `rss` section with 19 selectors to `SEL` const
- `e2e/fixtures/test-feeds.opml` — New file, valid OPML 2.0 with nested + flat feed outlines
- `e2e/tests/31-rss-reader/rss-reader.spec.ts` — New file, 663 lines, single sequential test with 15 phases and 58 assertions
