# S07: Integration Verification — Research

## Summary

This is a straightforward E2E Playwright test slice for the completed Media Scheduler app. The app is already fully built (S01–S06) and unit-tested (5000-line test_media_scheduler.py with comprehensive coverage). The E2E tests follow well-established patterns from the codebase — particularly the RSS Reader spec (`e2e/tests/31-rss-reader/`) and App Platform spec (`e2e/tests/30-app-platform/`). No new technology, no novel architecture, no risky integration.

**Key constraint:** YouTube and Spotify APIs require real credentials, and the test Docker stack has no mock servers for them. The E2E test must focus on what's provable without external API keys: model install, app install, podcast subscription (can use a mock RSS feed or inline test feed), rule CRUD, plan generation, status tracking, and UI navigation. YouTube/Spotify source addition can be tested for form validation only (error paths).

## Requirement Coverage

No MEDIA-* requirements are defined in REQUIREMENTS.md. The verification targets the milestone success criteria from the roadmap:
- Model + app install lifecycle
- Podcast source subscription and discovery
- Schedule rule CRUD
- Daily plan generation and display
- Entry status tracking (completed/skipped/saved)
- Stats dashboard rendering
- Tab navigation across Today/Episodes/Rules/Stats

## Recommendation

One large spec file at `e2e/tests/55-media-scheduler/media-scheduler.spec.ts` using the established single-sequential-test pattern (one `test()` block with phases, like RSS Reader). The test should add selectors to `SEL` in `e2e/helpers/selectors.ts` for reuse.

Split into two tasks:
1. **T01**: Selectors + core lifecycle spec (model install → app install → podcast subscription → rule creation → plan generation → status tracking → stats → uninstall)
2. **T02**: Review + edge cases + cleanup verification (form validation errors, empty states, tab navigation, idempotent cleanup)

## Implementation Landscape

### Test Infrastructure (all exists, nothing to build)

| Component | Location | Role |
|-----------|----------|------|
| Auth fixture | `e2e/fixtures/auth.ts` | `ownerPage` + `ownerRequest` contexts with session cookies |
| Selectors | `e2e/helpers/selectors.ts` | Centralized CSS selectors (add `mediaScheduler` block) |
| Wait helpers | `e2e/helpers/wait-for.ts` | `waitForHtmxSettle`, `waitForElement`, `waitForText` |
| API client | `e2e/helpers/api-client.ts` | Direct API calls for arrangement (SPARQL, commands) |
| Playwright config | `e2e/playwright.config.ts` | Single-worker sequential execution, 60s default timeout |
| Test harness | `e2e/fixtures/test-harness.ts` | Docker stack health check |

### App Surface to Test

| Fragment Route | CSS Anchors | What to Assert |
|---------------|-------------|----------------|
| `/_fragments/main` | `#ms-container`, `.ms-sidebar`, `.ms-tabs`, `#ms-tab-content` | App page loads with correct layout |
| `/_fragments/sources` | `.ms-source-list`, `.ms-source-item`, `.ms-badge-podcast` | Sources listed with type badges |
| `/_fragments/add-source` (POST podcast) | `.ms-success`, `.ms-error` | htmx response text for success/error |
| `/_fragments/items` | `.ms-item-row` or equivalent | Items listed with title, duration |
| `/_fragments/today` | `.ms-today-view`, `.ms-plan-entry`, `.ms-status-badge` | Plan entries with time slots |
| `/_fragments/rules` | `.ms-rules-view`, `.ms-rule-card`, `.ms-rule-name` | Rules listed with conditions display |
| `/_fragments/rules` (POST) | `#ms-rules-list` | Rule created/updated, list refreshes |
| `/_fragments/plan/generate` (POST) | `.ms-plan-entry` | Plan entries appear after generation |
| `/_fragments/entry/{iri}/status` (POST) | `.ms-status-badge`, `.ms-entry-done` | Status badge changes |
| `/_fragments/stats` | `.ms-stats-view`, `#ms-chart-hours`, `#ms-chart-top-sources`, `#ms-chart-weekly` | Chart canvases render |

### Selectors to Add to `SEL`

```typescript
mediaScheduler: {
  container: '#ms-container',
  sidebar: '#ms-sidebar',
  tabs: '#ms-tabs',
  tabContent: '#ms-tab-content',
  tabToday: '.ms-tab[data-tab="today"]',
  tabEpisodes: '.ms-tab[data-tab="episodes"]',
  tabRules: '.ms-tab[data-tab="rules"]',
  tabStats: '.ms-tab[data-tab="stats"]',
  sourcesList: '#ms-sources-list',
  sourceItem: '.ms-source-item',
  sourceBadge: '.ms-badge',
  addFormToggle: '#ms-toggle-add-form',
  addSection: '#ms-add-section',
  addResult: '#ms-add-result',
  todayView: '.ms-today-view',
  planEntry: '.ms-plan-entry',
  statusBadge: '.ms-status-badge',
  generateBtn: '.ms-today-header button',
  rulesView: '.ms-rules-view',
  ruleCard: '.ms-rule-card',
  ruleName: '.ms-rule-name',
  ruleFormArea: '#ms-rule-form-area',
  rulesListContainer: '#ms-rules-list',
  statsView: '.ms-stats-view',
  statsCard: '.ms-stats-card',
  chartHours: '#ms-chart-hours',
  chartTopSources: '#ms-chart-top-sources',
  chartWeekly: '#ms-chart-weekly',
},
```

### Test Phase Structure

Following the RSS Reader pattern — one `test()` with sequential phases:

**Phase 0: Cleanup** — Idempotent removal of prior state (app uninstall, model delete).

**Phase 1: Install model** — `POST /admin/models` with `path=/app/models/media-scheduler`. Poll admin page for model visibility.

**Phase 2: Install app** — Fill install form with `media-scheduler`. Poll for `running` status badge. Generous timeout (120s) for venv creation + pip install.

**Phase 3: Navigate to app** — `GET /app/media-scheduler/` (or via `GET /browser/` → sidebar APPS section). Verify `#ms-container` loads with sidebar and tab structure.

**Phase 4: Add podcast source** — Click `+` button to reveal add form. Fill `feed_url` with a test RSS feed URL. Submit. Assert `.ms-success` appears. Assert `.ms-source-item` appears in sources list with `.ms-badge-podcast` badge.

**Phase 5: Tab navigation** — Click Episodes tab → assert items list loads. Click Rules tab → assert rules view loads. Click Stats tab → assert stats view loads with chart canvases. Click Today tab → return to plan view.

**Phase 6: Create schedule rule** — Click "Add Rule" button. Fill rule form (name, activity=commuting, action=source_type/podcast). Submit. Assert `.ms-rule-card` appears with rule name.

**Phase 7: Generate plan** — Click "Generate Plan" button on Today tab. Assert plan generation completes (plan entries appear or empty-state message changes).

**Phase 8: Status tracking** — If plan entries exist, click complete/skip/save buttons. Assert status badge changes to the new status.

**Phase 9: Stats** — Switch to Stats tab. Assert chart canvases exist (even if empty data — verify `.ms-stats-empty` or canvas presence).

**Phase 10: Uninstall** — Stop app, uninstall app, delete model. Verify removal.

### Podcast Feed Challenge

The test Docker stack doesn't have a mock RSS feed server. Options:
1. **Use a real public podcast feed** (e.g., `https://feeds.simplecast.com/54nAGcIl`) — works but depends on external availability, slow, and creates real data
2. **Use the `mock-llm` server** — it's already in the Docker stack at port 8080, could serve a static XML response, but requires modifying the mock
3. **Accept that podcast subscription creates a MediaSource even if polling fails** — `subscribe_podcast()` creates the source object in the triplestore *before* polling. The test can verify source creation without needing a working feed. The poll-sources task would fail on the next scheduled run, but that's fine for E2E verification of the CRUD flow.

**Recommendation:** Option 3. Create the podcast source with a dummy URL (e.g., `http://example.com/test.xml`). Verify the source appears in the list. The app creates the MediaSource via CommandClient immediately on subscription — polling is a separate scheduled task. This tests the CRUD flow without external dependencies. For items verification, use the API client to create MediaItems directly via SPARQL/commands.

### Key CSS Selectors Already in Templates

| Element | Selector | Template |
|---------|----------|----------|
| App container | `#ms-container` | `main.html` |
| Sources list target | `#ms-sources-list` | `main.html` |
| Tab buttons | `.ms-tab[data-tab="today"]` etc. | `main.html` |
| Tab content target | `#ms-tab-content` | `main.html` |
| Source items | `.ms-source-item` | `sources-list.html` |
| Source type badge | `.ms-badge-podcast`, `.ms-badge-youtube`, `.ms-badge-spotify` | `sources-list.html` |
| Plan entries | `.ms-plan-entry` | `today.html` |
| Status badges | `.ms-status-badge`, `.ms-status-completed`, `.ms-status-skipped`, `.ms-status-saved` | `today.html` |
| Rule cards | `.ms-rule-card` | `rules-list.html` |
| Rule name | `.ms-rule-name` | `rules-list.html` |
| Stats canvases | `#ms-chart-hours`, `#ms-chart-top-sources`, `#ms-chart-weekly` | `stats.html` |
| Empty states | `.ms-empty-state` | multiple |
| Success/error messages | `.ms-success`, `.ms-error`, `.ms-info` | multiple |

### Admin Page Selectors (reuse existing)

- Install form: `SEL.apps.installForm` (`form.install-form`)
- Install input: `SEL.apps.installInput` (`#app_path`)
- App card: `SEL.apps.appCard` (`.dashboard-cards .card`)
- Status badge: `SEL.apps.statusBadge` (`.status-badge`)

### Timeouts

- Model install: 30s (RDF4J schema loading)
- App install: 120s (venv creation + pip install + subprocess start + health check)
- htmx swaps: 10s default (wait-for helpers)
- Plan generation: 15s (SPARQL queries + rule evaluation + bulk object creation)

### What NOT to Test in E2E

- **YouTube source addition** — requires real YouTube Data API key (not in test env). Can test form validation (empty URL error).
- **Spotify OAuth flow** — requires real Spotify app credentials + browser redirect. Cannot be mocked in this stack.
- **Context SSE subscription** — requires M037 context API running. The test stack doesn't include it. Context-driven adaptation is unit-tested.
- **Mobile suggestion endpoint** — JSON API can be tested via `ownerRequest.get()` directly, no browser needed.
- **Actual podcast feed polling** — requires a working RSS feed URL accessible from Docker network. Source CRUD is sufficient.

## Pitfalls

1. **htmx swap timing** — All fragments load via htmx `hx-trigger="load"`. After navigating to the app page, wait for `#ms-sources-list` to have content before interacting. Use `waitForElement` or `page.waitForSelector('.ms-source-item', { state: 'attached' })` after subscription.

2. **Tab switching is JS, not navigation** — `msSelectTab()` calls `htmx.ajax()` to swap `#ms-tab-content`. After clicking a tab button, wait for the new content to appear in the tab content area. No URL change to wait for.

3. **installDetails selector missing** — The RSS reader test references `SEL.apps.installDetails` which doesn't exist in selectors.ts. The app-platform test uses the correct `SEL.apps.installForm` / `SEL.apps.installInput`. Follow the app-platform pattern.

4. **App install timeout** — The media-scheduler app has `requirements.txt` which triggers venv creation + pip install. The RSS reader takes ~60-90s for this. Set `test.setTimeout(240_000)` like existing app tests.

5. **Dialog handling** — Rule deletion uses `hx-confirm` which triggers a browser confirm dialog. Add `ownerPage.on('dialog', d => d.accept())` at the top of the test (same as RSS reader pattern).

6. **Chart.js CDN** — Stats charts lazy-load Chart.js from CDN. The test Docker stack may not have internet access (depends on Docker network config). If CDN load fails, charts won't render but the stats view itself will. Assert canvas presence, not chart rendering.
