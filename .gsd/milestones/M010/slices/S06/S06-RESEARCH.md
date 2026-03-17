# S06: E2E Tests + User Guide — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S06 is the final slice of M010 — a Playwright E2E test spec covering the full RSS Reader lifecycle and a user guide chapter (Chapter 30) documenting RSS Reader setup and usage. Both deliverables follow established patterns in the codebase: the E2E spec mirrors `app-platform.spec.ts` (single sequential test with phased structure) and the guide follows Chapter 29 (App Platform) in style and navigation chain.

This is straightforward application of well-established patterns. The test infrastructure, fixture system, selector constants, and guide conventions are all proven. The main complexity is test sequencing — the RSS Reader depends on the `rss-feeds` model being installed, then the app being installed and started, then a feed subscription being created, then articles being polled — each step must succeed before the next can be verified.

## Recommendation

### Two tasks: E2E spec first, user guide second

**T01 — Playwright E2E spec** (~250-350 lines). A single sequential `test()` in `e2e/tests/31-rss-reader/rss-reader.spec.ts` covering all RSS-01 through RSS-08 requirements that are active. Uses `ownerPage` + `ownerRequest` fixtures from `auth.ts`. Generous timeout (240s) since model install + app install + venv creation + first poll cycle can take 90-120s combined. Must clean up on completion (uninstall app, remove model) so the test is idempotent.

**T02 — User guide Chapter 30** (~180-250 lines). `docs/guide/30-rss-reader.md` covering: subscribing to feeds, the reader UI layout, starring and reading articles, OPML import, settings, workspace views, and admin monitoring. Update `README.md` TOC, fix navigation chain (ch. 29 → ch. 30 → Appendix A), and add glossary entries for RSS-specific terms.

## Implementation Landscape

### Key Files

**Existing (read, reference):**
- `e2e/tests/30-app-platform/app-platform.spec.ts` — The canonical E2E pattern for app lifecycle. Copy its phase structure: cleanup → install → verify workspace → verify admin → actions → uninstall.
- `e2e/fixtures/auth.ts` — Provides `ownerPage`, `ownerRequest`, `BASE_URL`. The RSS test uses the same fixture pattern.
- `e2e/helpers/selectors.ts` — `SEL.apps.*` selectors for app platform UI elements. RSS Reader reuses these for admin and sidebar interactions.
- `e2e/helpers/wait-for.ts` — `waitForIdle()`, `waitForWorkspace()`, `waitForHtmxSettle()` helpers. Critical for htmx-driven fragment loading.
- `e2e/fixtures/seed-data.ts` — Reference for constant pattern if RSS-specific seed constants are needed.
- `e2e/playwright.config.ts` — Confirms test directory, timeout settings, sequential execution (workers: 1).
- `docs/guide/29-app-platform.md` — Previous chapter in navigation chain. Its footer links to Appendix A — needs updating to point to Chapter 30.
- `docs/guide/README.md` — Table of contents. Needs Chapter 30 entry.
- `docs/guide/appendix-d-glossary.md` — Needs RSS-specific terms (Feed Subscription, Article, OPML, Poll Interval).

**New files (S06 creates):**
- `e2e/tests/31-rss-reader/rss-reader.spec.ts` — Full lifecycle E2E spec
- `docs/guide/30-rss-reader.md` — User guide Chapter 30

**Modified files:**
- `e2e/helpers/selectors.ts` — Add `rss` section with selectors for RSS Reader UI elements
- `docs/guide/README.md` — Add Chapter 30 to TOC
- `docs/guide/29-app-platform.md` — Update footer navigation (Next → Chapter 30)
- `docs/guide/appendix-a-environment-variables.md` — Update footer (Previous → Chapter 30)
- `docs/guide/appendix-d-glossary.md` — Add RSS-specific terms

### Build Order

**T01 first (E2E spec) because:**
- It validates all S01-S05 deliverables in a live Docker stack — the authoritative proof that the RSS Reader works end-to-end.
- The spec's phase structure documents the exact user flow that the guide will describe.
- Any bugs discovered during E2E testing should be fixed before documenting the feature.

**T02 second (user guide) because:**
- It depends on knowing the exact UI behavior, which the E2E spec exercises and verifies.
- Guide screenshots/descriptions should reflect the working system proven by E2E.

### E2E Spec Structure (T01)

The spec should use a single `test()` (matching the `app-platform.spec.ts` pattern) with these phases:

**Phase 0: Cleanup.** If rss-feeds model or rss-reader app are already installed from a previous run, uninstall them. Use API calls (`ownerRequest`) for speed.

**Phase 1: Install rss-feeds model.** POST to `/admin/models` with path `/app/models/rss-feeds`. Verify model appears in model list. (Model must be installed before app because app declares `dependencies.models: [{id: "rss-feeds"}]`.)

**Phase 2: Install rss-reader app.** Navigate to Admin > Applications. Fill install form with `rss-reader`. Wait for venv creation + process start (up to 90s). Verify status badge shows "running".

**Phase 3: Verify admin detail page.** Navigate to `/admin/apps/rss-reader`. Verify: app name, status badge, PID, permissions table shows `object.create`/`object.patch`/`edge.create`/`body.set`, scheduled tasks shows `poll-feeds`.

**Phase 4: Verify workspace integration.** Navigate to workspace. Expand APPS section. Click "RSS Reader" tree leaf. Verify reader fragment loads (`#rss-reader-container` visible). Verify empty state ("No feeds yet. Subscribe to get started.").

**Phase 5: Subscribe to a feed.** Click "Subscribe" button in feed sidebar. Fill feed URL with a reliable test feed URL. Submit. Wait for `feedsChanged` HX-Trigger. Verify feed appears in sidebar. 

_Feed URL strategy:_ The test runs against a Docker stack with no internet access guaranteed. Two options:
1. Use a mock route (`ownerPage.route()`) to intercept the app's HTTP request and return a canned RSS XML response. But the app fetches feeds from within its subprocess (not from the browser), so Playwright route interception won't work.
2. Use the subscribe API endpoint directly via `ownerRequest.post()` to create a subscription in the triplestore, then manually create a test article via SPARQL or the command API. This bypasses feed parsing but proves the UI displays data correctly.

**Recommended approach:** Use direct SPARQL/API to seed test data. The subscribe endpoint (`/_fragments/subscribe`) goes through the app's proxy, and the app then needs to actually fetch the feed URL over HTTP. Since the Docker test stack may not have outbound internet, the safest path is:
1. Subscribe to a feed via the UI (POST to subscribe endpoint with a URL)
2. If the poll doesn't find articles (no internet), seed articles directly via `ownerRequest.post()` to the command API using `object.create` with type `urn:sempkm:model:rss-feeds:Article`
3. Verify the reader UI displays the seeded articles

_Alternative:_ The subscribe route accepts any URL — if the test stack has internet access, use a well-known stable feed like `https://feeds.bbci.co.uk/news/rss.xml`. If it fails, fall back to API seeding. The test should be resilient to both paths.

**Phase 6: Verify article display.** After seeding data, reload the reader page. Verify article list shows articles. Click an article. Verify reading pane loads with article title and body content.

**Phase 7: Star an article.** Click the star button in the reading pane. Verify star state changes (button appearance). Reload page. Verify star persists.

**Phase 8: Mark read/unread.** Verify unread count in feed sidebar. After opening an article, verify unread count decrements (if mark-read-on-open is working).

**Phase 9: Workspace views.** Navigate to workspace. Find "Unread Articles" or "Starred Articles" in the Views section. Click to open. Verify articles appear in the view tab.

**Phase 10: Command palette.** Open command palette (Ctrl+K). Type "Subscribe" or "Mark All". Verify RSS Reader commands appear in the palette.

**Phase 11: OPML import.** Open subscribe dialog. Click "Import OPML". Upload a test OPML file. Verify success message with `data-created` count.

**Phase 12: Settings.** Open settings via gear icon. Change articlesPerPage value. Submit. Verify success message.

**Phase 13: Admin task history.** Navigate to admin detail page. Check task history section for poll-feeds runs.

**Phase 14: Cleanup.** Stop app. Uninstall app. Remove rss-feeds model. Verify clean state.

### Testable CSS Selectors (from templates)

| Element | Selector |
|---------|----------|
| Reader container | `#rss-reader-container` |
| Feed sidebar | `#rss-feed-sidebar` |
| Article list content | `#rss-article-list-content` |
| Reading pane | `#rss-reading-pane` |
| Feed item | `.rss-feed-item` |
| Article item | `.rss-article-item` |
| Unread article | `.rss-article-item.unread` |
| Star button | `.rss-star-btn` (in star-button.html) |
| Filter tabs | `.rss-filter-tab` |
| Subscribe button | `.rss-subscribe-btn` |
| Empty state | `.rss-empty-state` |
| Success message | `.rss-success` |
| Error message | `.rss-error` |
| OPML result | `#opml-import-result` |
| Settings form | `#rss-settings` |
| Subscribe dialog | `#rss-subscribe-dialog` |
| Article data attrs | `[data-article-iri]`, `[data-starred]`, `[data-read]` |
| Feed data attrs | `[data-feed-iri]` |

### OPML Test Fixture

The E2E test needs a small OPML file for the import phase. Create a fixture file at `e2e/fixtures/test-feeds.opml` with 2-3 feed entries. The file upload uses `<input type="file">` — Playwright's `setInputFiles()` can set this.

Example OPML content:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Test Feeds</title></head>
  <body>
    <outline text="Tech" title="Tech">
      <outline type="rss" text="Example Blog" xmlUrl="https://example.com/feed.xml" htmlUrl="https://example.com" />
    </outline>
    <outline type="rss" text="Test Feed" xmlUrl="https://test.example.org/rss" />
  </body>
</opml>
```

### User Guide Structure (T02)

Chapter 30 follows the established pattern from chapters 27-29:

```markdown
# Chapter 30: RSS Reader

Introduction paragraph describing RSS Reader and its purpose.

## Getting Started
- Installing the rss-feeds Mental Model
- Installing the RSS Reader app
- Opening the reader from the Apps sidebar

## Subscribing to Feeds
- Adding feeds by URL
- Feed discovery (paste website URL)
- OPML import

## The Reader Interface
- Feed sidebar (feed list, unread counts, error indicators)
- Article list (filter tabs: All / Unread / Starred)
- Reading pane (clean typography, markdown-rendered body)

## Reading Articles
- Opening an article
- Mark as read / unread
- Star / unstar
- Keyboard navigation (j/k)

## Workspace Integration
- Unread Articles view
- Starred Articles view
- Related Articles in right pane
- Command palette entries (Subscribe, Mark All as Read, Open RSS Reader)
- Custom article renderer in object browser

## Managing Feeds
- Unsubscribing from a feed
- Feed error indicators
- Re-subscribing to a feed

## Settings
- Articles per page
- Mark read on open
- Poll interval (Admin > Applications > RSS Reader)

## Admin Monitoring
- App status and lifecycle
- Task history for poll-feeds
- Permissions overview

---
Previous: [Chapter 29: App Platform](29-app-platform.md) | Next: [Appendix A: ...](appendix-a-environment-variables.md)
```

### Verification Approach

**T01 verification:**
- `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium` passes against the test Docker stack
- Test is idempotent — running twice in a row produces the same result (cleanup phase handles prior state)
- Total assertion count should be ≥20 (matching the milestone definition of done)

**T02 verification:**
- `docs/guide/30-rss-reader.md` exists, ≥150 lines, no broken relative links
- `README.md` TOC includes Chapter 30
- Navigation chain: ch. 29 footer → ch. 30, ch. 30 footer → Appendix A, Appendix A footer → (Previous: ch. 30)
- Glossary has ≥3 new RSS-specific terms
- All section headers match actual UI labels/features

## Constraints

- E2E tests run against Docker stack on port 3901 (`TEST_BASE_URL`). The test environment may or may not have outbound internet access — the spec must be resilient to offline operation by falling back to API-seeded test data.
- Playwright config uses `workers: 1` and `fullyParallel: false` — RSS Reader spec must not assume parallel execution with other tests.
- The app install creates a Python venv and pip-installs dependencies (feedparser, trafilatura, listparser) — this can take 30-60s on first run. Generous timeout (240s) needed.
- Model must be installed before app — the app manifest declares `dependencies.models: [{id: "rss-feeds"}]`. Install order matters.
- The E2E spec should extend `SEL` in `selectors.ts` with RSS-specific selectors to keep them centralized (matching the existing convention).

## Common Pitfalls

- **Feed subscription without internet:** The Docker test stack runs on an isolated network. Subscribing to a real RSS feed URL will succeed (creating the FeedSubscription object) but polling won't fetch articles. The test must seed articles via the command API or accept empty article lists after subscribe.
- **App startup race:** After installing the app, it takes time for the venv to be created, deps installed, process started, and health check to pass. The `app-platform.spec.ts` handles this with a retry loop polling the admin page — copy this exact pattern.
- **htmx fragment load timing:** RSS Reader UI uses htmx lazy-load triggers (`hx-trigger="load"`). After navigating to the reader page, wait for `#rss-reader-container` to appear, then wait for feed sidebar and article list fragments to complete loading before asserting on content.
- **HX-Trigger event propagation:** Star/read toggles emit `articleStateChanged` and `feedsChanged` HX-Trigger headers. After toggling, wait for htmx to process these triggers and re-fetch affected fragments before asserting on updated counts.
- **OPML file upload path:** Playwright's `setInputFiles()` needs an absolute file path. The fixture file should be at `e2e/fixtures/test-feeds.opml` and resolved relative to the test file using `path.resolve()`.

## Sources

- `e2e/tests/30-app-platform/app-platform.spec.ts` — canonical E2E pattern for app lifecycle testing
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — model install/uninstall pattern
- `docs/guide/27-spatial-canvas.md`, `28-dashboards-and-workflows.md`, `29-app-platform.md` — guide chapter style reference
- S03, S04, S05 summaries — template selectors, route handlers, HX-Trigger conventions
