---
estimated_steps: 6
estimated_files: 3
---

# T01: Playwright E2E spec for RSS Reader full lifecycle

**Slice:** S06 — E2E tests + user guide
**Milestone:** M010

## Description

Create the Playwright E2E test spec that exercises the complete RSS Reader lifecycle against a live Docker test stack. This is the authoritative final-assembly proof that the RSS Reader (S01-S05) works end-to-end.

The spec follows the established pattern from `e2e/tests/30-app-platform/app-platform.spec.ts` — a single sequential `test()` with phased structure, generous timeout (240s), cleanup-first idempotency, and retry loops for async operations (venv creation, process health checks).

**Relevant skill:** Load the `test` skill for test framework conventions.

## Steps

1. **Add RSS selectors to `e2e/helpers/selectors.ts`.** Add an `rss` section to the `SEL` object with selectors from the S03 research:

   ```typescript
   rss: {
     readerContainer: '#rss-reader-container',
     feedSidebar: '#rss-feed-sidebar',
     articleListContent: '#rss-article-list-content',
     readingPane: '#rss-reading-pane',
     feedItem: '.rss-feed-item',
     articleItem: '.rss-article-item',
     unreadArticle: '.rss-article-item.unread',
     starBtn: '.rss-star-btn',
     filterTab: '.rss-filter-tab',
     subscribeBtn: '.rss-subscribe-btn',
     emptyState: '.rss-empty-state',
     successMessage: '.rss-success',
     errorMessage: '.rss-error',
     opmlResult: '#opml-import-result',
     settingsForm: '#rss-settings',
     subscribeDialog: '#rss-subscribe-dialog',
   },
   ```

2. **Create OPML test fixture at `e2e/fixtures/test-feeds.opml`.** Small file with 2-3 feed entries matching the pattern from S05's `parse_opml()` expectations:

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

3. **Create `e2e/tests/31-rss-reader/rss-reader.spec.ts`.** Single `test.describe('RSS Reader')` with a single `test()` using 240_000ms timeout. Import from `../../fixtures/auth` (test, expect, BASE_URL), `../../helpers/selectors` (SEL), `../../helpers/wait-for` (waitForIdle, waitForWorkspace). Add `ownerPage.on('dialog', d => d.accept())` for hx-confirm dialogs.

4. **Implement the 14 test phases** within the single `test()`:

   **Phase 0 — Cleanup:** If `rss-feeds` model or `rss-reader` app are already installed, uninstall them via API (`ownerRequest`). For the app: POST stop, POST uninstall with `clean_data: true`. For the model: DELETE `/admin/models/rss-feeds`. Wrap each in try/catch for idempotency.

   **Phase 1 — Install rss-feeds model:** POST to `/admin/models` with form data `{ path: '/app/models/rss-feeds' }`. Navigate to `/admin/models`, verify `rss-feeds` or "RSS Feeds" appears in the model list. Allow a retry/reload loop (model install may take a few seconds).

   **Phase 2 — Install rss-reader app:** Navigate to `/admin/apps`. Open install form (expand `<details>` via `SEL.apps.installDetails`). Fill `#app-path-input` with `rss-reader`. Submit. Wait for redirect to `/admin/apps` with 90s timeout (venv creation + pip install). Retry-loop poll for "running" status badge on the RSS Reader card (up to 10 attempts, 5s apart — copy exact pattern from `app-platform.spec.ts`).

   **Phase 3 — Verify admin detail page:** Navigate to `/admin/apps/rss-reader`. Assert: h1 contains "RSS Reader" or "RSS", status badge shows "running", PID stat is not "—", permissions table contains "object.create", scheduled tasks section contains "poll-feeds".

   **Phase 4 — Verify workspace integration:** Navigate to workspace (`/`). Wait for workspace load (`waitForWorkspace`). Expand APPS section (`#section-apps`). Wait for apps tree to populate. Click "RSS Reader" tree leaf. Wait for `#rss-reader-container` to appear (15s timeout). Assert empty state is visible (`.rss-empty-state` with text about subscribing).

   **Phase 5 — Subscribe to a feed:** Within the reader container, click `.rss-subscribe-btn`. Wait for subscribe dialog or form to appear. Fill feed URL input with `https://example.com/feed.xml` (the value doesn't matter since Docker may not have internet — we just need the subscription created). Submit the form. Wait a few seconds. If feed items appear in sidebar, proceed. If not (offline Docker), the subscription object was still created — the subscribe POST creates the FeedSubscription in the triplestore regardless. Verify at least one `.rss-feed-item` appears in sidebar OR verify via SPARQL query that a FeedSubscription exists.

   **Phase 6 — Seed test article (if needed) and verify display:** Check if any `.rss-article-item` exists. If not (offline Docker), seed an article via the command API: POST to `/api/objects` with type `urn:sempkm:model:rss-feeds:Article`, properties including `dcterms:title`, `rss:isRead false`, `rss:isStarred false`. Then set a body via POST to the body endpoint. Reload the reader page and wait for articles to appear. Assert at least one article is visible in the article list.

   **Phase 7 — Read an article:** Click the first `.rss-article-item`. Wait for reading pane content to load (`#rss-reading-pane` should contain article title text). Assert reading pane is visible and contains content.

   **Phase 8 — Star an article:** Find the star button (`.rss-star-btn`) in the reading pane or article. Click it. Wait for htmx settle. Verify `data-starred="true"` attribute or star button visual change. Reload the page. Re-navigate to the reader. Verify star persists.

   **Phase 9 — Verify unread count / mark read:** Check if unread count decremented after opening an article (feed sidebar should show count). This is a soft check — htmx trigger `articleStateChanged` may take a moment.

   **Phase 10 — Workspace views:** Navigate to workspace. Look for "Unread Articles" or "Starred Articles" in the Views explorer section. Click one of them. Wait for the view tab to load with article content. Assert articles are visible.

   **Phase 11 — Command palette:** Open command palette (`Ctrl+K`). Wait for `ninja-keys` to be visible. Type "RSS" or "Mark All" or "Subscribe". Verify at least one RSS Reader command appears in the results. Press Escape to close.

   **Phase 12 — OPML import:** Navigate back to the reader page. Click the Import OPML button. Wait for the import form/dialog. Use Playwright's `setInputFiles()` on the file input with the path to `test-feeds.opml` (resolved via `path.resolve(__dirname, '../../fixtures/test-feeds.opml')`). Submit the import form. Wait for the result. Assert `.rss-success` or `#opml-import-result` is visible with `data-created` attribute.

   **Phase 13 — Settings:** Click the gear icon in the feed sidebar header. Wait for settings form. Change `articlesPerPage` value. Submit. Assert success message. 

   **Phase 14 — Cleanup:** Navigate to admin apps. Stop the app (POST `/admin/apps/rss-reader/stop`). Uninstall (POST `/admin/apps/rss-reader/uninstall` with `clean_data: true`). Delete the model (DELETE `/admin/models/rss-feeds`). Verify clean state (app and model no longer listed). This can be done via API calls for speed.

5. **Handle the offline-Docker resilience pattern.** The test stack may or may not have internet access. Key strategy:
   - Subscribe to a feed URL — this creates the FeedSubscription object regardless of whether the feed is reachable
   - If no articles appear after subscribing (offline), seed articles directly via the API using `ownerRequest.post()` to create article objects in the triplestore
   - The star/read/view assertions work on seeded articles just the same

6. **Verify the test runs.** The final check is `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium`. However, the test requires the Docker test stack to be running. The executor should verify that the spec file compiles (TypeScript) and is structurally sound. If the Docker stack is available, run the test. If not, verify by running `npx tsc --noEmit` in the e2e directory.

## Must-Haves

- [ ] `rss` section added to `SEL` in `e2e/helpers/selectors.ts`
- [ ] OPML fixture at `e2e/fixtures/test-feeds.opml` with valid OPML XML
- [ ] `e2e/tests/31-rss-reader/rss-reader.spec.ts` exists with single sequential test
- [ ] Test has 240s timeout to accommodate model install + venv creation + polling
- [ ] Cleanup phase runs first to ensure idempotency
- [ ] Test has ≥20 `expect()` assertions across all phases
- [ ] Test is resilient to offline Docker (seeds articles via API when needed)
- [ ] OPML file path resolved via `path.resolve()` for `setInputFiles()`

## Verification

- `cd e2e && npx tsc --noEmit` — TypeScript compiles without errors
- `grep -c "expect" e2e/tests/31-rss-reader/rss-reader.spec.ts` — ≥20 assertions
- `cat e2e/fixtures/test-feeds.opml` — valid XML with `<outline>` elements
- `grep "rss:" e2e/helpers/selectors.ts` — RSS selectors present
- If Docker stack available: `cd e2e && npx playwright test tests/31-rss-reader/rss-reader.spec.ts --project=chromium` passes

## Observability Impact

- **New signal**: Playwright HTML test report (`e2e/playwright-report/`) with per-phase timing, screenshots on failure, and assertion diffs. Inspect with `npx playwright show-report`.
- **New signal**: Failure screenshots in `e2e/test-results/` captured automatically on assertion failure — first diagnostic for debugging.
- **Inspection surface**: Each retry loop in the test prints attempt count; grep `attempt` in test output to diagnose slow startup vs. actual failure.
- **Failure visibility**: Cleanup errors wrapped in try/catch with console.log of response body — visible in Playwright stdout. API-seeded article failures log the 500 response.
- **Redaction**: No secrets logged. Session tokens handled by auth fixture. Setup token never printed.

## Inputs

- `e2e/tests/30-app-platform/app-platform.spec.ts` — canonical pattern for app lifecycle E2E testing (phase structure, retry loops, timeout, cleanup)
- `e2e/fixtures/auth.ts` — provides `ownerPage`, `ownerRequest`, `BASE_URL` fixtures
- `e2e/helpers/selectors.ts` — existing `SEL` object to extend
- `e2e/helpers/wait-for.ts` — `waitForIdle()`, `waitForWorkspace()` helpers
- S03 Summary — template selectors (`#rss-reader-container`, `.rss-article-item`, `.rss-star-btn`, `.rss-feed-item`, `.rss-empty-state`, `.rss-success`, `.rss-error`, `#rss-subscribe-dialog`, `data-article-iri`, `data-starred`, `data-read`, `data-feed-iri`)
- S04 Summary — workspace contributions (right pane related-articles, custom renderer, mark-all-read command palette, navigate command enrichment)
- S05 Summary — OPML import (`POST /_fragments/import-opml`, `#opml-import-result`, `data-created`), settings (`GET/POST /_fragments/settings`, `#rss-settings`)
- S03 Summary — HX-Trigger conventions: `articleStateChanged`, `feedsChanged`

## Expected Output

- `e2e/helpers/selectors.ts` — `rss` section added to SEL const
- `e2e/fixtures/test-feeds.opml` — new file, valid OPML with 2-3 test feeds
- `e2e/tests/31-rss-reader/rss-reader.spec.ts` — new file, ~250-350 lines, single sequential test with 14+ phases and ≥20 assertions
