# Phase 38: Global Lint Dashboard UI - Research

**Researched:** 2026-03-05
**Domain:** htmx-driven dashboard UI, bottom panel tabs, SSE real-time updates
**Confidence:** HIGH

## Summary

Phase 38 builds a global lint dashboard as a new bottom panel tab ("LINT") that consumes the Phase 37 REST API (`/api/lint/results`, `/api/lint/status`, `/api/lint/stream`). The existing codebase provides all integration points: bottom panel tab infrastructure (HTML in `workspace.html`, JS switching in `workspace.js`, CSS in `workspace.css`), command palette registration via `ninja-keys`, SSE broadcast via `LintBroadcast`, and the per-object lint panel (`lint_panel.html`) as a visual reference for severity icons and CSS classes.

The API already supports server-side pagination (`page`/`per_page`), severity filtering, object type filtering, and sorting by focus node + severity. The dashboard needs to add: (1) a new bottom panel tab + pane, (2) an htmx-rendered HTML partial for the dashboard, (3) a backend endpoint to render that partial, (4) client-side filter/sort controls using htmx `hx-include` + `hx-trigger="change"` (matching the inference panel pattern), (5) a persistent health indicator badge on the LINT tab, (6) SSE-driven auto-refresh, and (7) keyword search (requires a new `search` query param on the API).

**Primary recommendation:** Build as a server-rendered htmx partial (like inference panel), NOT a client-side JS app. Use `hx-include` for filter controls, server-side pagination, and SSE EventSource for auto-refresh. Add keyword search to the existing `/api/lint/results` endpoint.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dashboard location: Bottom panel tab alongside Event Log, Inference, AI Copilot
- Non-contextual view (content does not depend on focused object tab)
- Tab label: "LINT" (consistent with existing tab naming)
- Access methods: Click LINT tab in bottom panel; Command Palette action "Toggle Lint Dashboard"; No dedicated keyboard shortcut

### Claude's Discretion
- Health indicator placement and states (status bar badge vs sidebar icon vs bottom panel tab badge; should be visible without opening the lint panel)
- Result table design: columns, density, grouping strategy
- Filter control placement (inline toolbar vs sidebar filters)
- Sort interaction (clickable column headers vs dropdown)
- Pagination vs virtual-scroll for large result sets
- Click-to-navigate behavior (what happens when user clicks a lint result row)
- Auto-refresh mechanism (htmx polling, SSE, or manual refresh button)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LINT-03 | Visual health indicator showing overall KB validation status at a glance | Tab badge on LINT tab + summary bar inside dashboard; CSS badge pattern documented below |
| LINT-04 | Filter lint results by severity level | API already supports `?severity=Violation\|Warning\|Info`; htmx `hx-include` filter controls |
| LINT-05 | Filter lint results by object type | API already supports `?object_type=<IRI>`; need endpoint to list available types from shapes service |
| LINT-06 | Search/filter lint results by keyword | New `?search=` param needed on `/api/lint/results`; server-side SPARQL FILTER(CONTAINS()) |
| LINT-07 | Sort lint results by severity, object name, property path, or timestamp | New `?sort=` param on API; SPARQL ORDER BY clause mapping |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| htmx | (already loaded) | Server-rendered partials, AJAX swaps | Project standard -- all DOM updates via htmx |
| Jinja2 | (already loaded) | HTML templates | Project standard for all partials |
| FastAPI | (already loaded) | Backend API + HTML endpoints | Project framework |
| EventSource (browser native) | N/A | SSE for real-time lint updates | Already used by per-object lint panel |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ninja-keys | (already loaded) | Command palette "Toggle Lint Dashboard" action | Register command on init |
| Lucide | (already loaded) | Icons in filter bar and badges | Severity icons, refresh icon |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Server-side pagination | Virtual-scroll (JS) | Server-side pagination is simpler, matches API design, avoids JS complexity. 50 results/page is fine for htmx swap. |
| htmx hx-include filters | Client-side JS filtering | hx-include matches inference panel pattern exactly. No custom JS needed. |

**Installation:** No new dependencies needed. Everything is already in the stack.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/templates/browser/
  lint_dashboard.html         # New htmx partial for global lint dashboard
  lint_panel.html             # Existing per-object lint panel (reference)
  inference_panel.html        # Existing inference panel (pattern reference)

backend/app/browser/router.py # Add GET /browser/lint-dashboard endpoint
backend/app/lint/router.py    # Extend with ?search= and ?sort= params

frontend/static/css/workspace.css  # Add .lint-dashboard-* CSS classes
frontend/static/js/workspace.js    # Add LINT tab, command palette, SSE handler
```

### Pattern 1: Bottom Panel Tab Registration
**What:** Add LINT as a fourth bottom panel tab following the existing 3-tab pattern.
**When to use:** This is the only pattern for adding bottom panel content.
**Example:**
```html
<!-- workspace.html: Add tab button to panel-tab-bar -->
<button class="panel-tab" data-panel="lint-dashboard">LINT</button>

<!-- workspace.html: Add pane to panel-content -->
<div class="panel-pane" id="panel-lint-dashboard">
  {% include 'browser/lint_dashboard.html' %}
</div>
```

```javascript
// workspace.js panelState.activeTab switching already handles data-panel matching
// No changes needed to initPanelTabs() -- it uses querySelectorAll('.panel-tab')
```

### Pattern 2: htmx Filter Controls (Inference Panel Pattern)
**What:** `<select>` and `<input>` elements with `hx-get`, `hx-target`, `hx-include`, `hx-trigger="change"`.
**When to use:** For all filter/sort/search controls in the dashboard.
**Example:**
```html
<!-- Matches inference_panel.html pattern exactly -->
<select class="lint-dashboard-filter-severity"
        hx-get="/browser/lint-dashboard"
        hx-target="#lint-dashboard-results"
        hx-include="[class*='lint-dashboard-filter']"
        hx-trigger="change"
        name="severity">
  <option value="">All severities</option>
  <option value="Violation">Violations</option>
  <option value="Warning">Warnings</option>
  <option value="Info">Info</option>
</select>
```

### Pattern 3: SSE Auto-Refresh
**What:** EventSource listens for `validation_complete` events, triggers htmx reload.
**When to use:** To auto-refresh dashboard when validation runs complete.
**Example:**
```javascript
// Reuse existing /api/lint/stream SSE endpoint (already broadcasts to all clients)
var es = new EventSource('/api/lint/stream');
es.addEventListener('validation_complete', function(e) {
  // Refresh the dashboard results via htmx
  htmx.ajax('GET', '/browser/lint-dashboard', {
    target: '#lint-dashboard-results',
    swap: 'innerHTML'
  });
  // Also update the tab badge
  updateLintBadge(JSON.parse(e.data));
});
```

### Pattern 4: Health Indicator Badge on Tab
**What:** A small badge element inside the LINT tab button showing violation count.
**When to use:** LINT-03 -- visible health indicator without opening the panel.
**Recommended approach:** Badge on the LINT tab itself (visible whenever bottom panel header is visible, which it is when any panel tab is active). Also update on SSE events.
```html
<button class="panel-tab" data-panel="lint-dashboard">
  LINT <span class="lint-badge" id="lint-badge" style="display:none"></span>
</button>
```
```css
.lint-badge {
  display: inline-block;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  margin-left: 6px;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 700;
  text-align: center;
  line-height: 16px;
}
.lint-badge--violations { background: var(--color-error); color: #fff; }
.lint-badge--warnings { background: var(--color-warning); color: #000; }
.lint-badge--pass { background: var(--color-success); color: #fff; }
```

### Pattern 5: Click-to-Navigate
**What:** Clicking a lint result row opens that object in dockview.
**When to use:** LINT-11 is deferred, but basic navigation is expected.
**Example:**
```html
<tr class="lint-dashboard-row" onclick="openTab('{{ item.focus_node }}', '{{ item.object_label | e }}')">
```
`window.openTab()` is already globally available and handles dockview panel creation/focus.

### Anti-Patterns to Avoid
- **Client-side filtering JS:** Do NOT build a JS filter engine. The API already handles filtering server-side. Use htmx `hx-include` like the inference panel.
- **Polling instead of SSE:** The SSE stream already exists (`/api/lint/stream`). Do NOT add `hx-trigger="every 10s"` polling. Use SSE for the dashboard (the per-object panel also uses SSE now).
- **Inline icon styles:** Per CLAUDE.md, never use inline `style="width:..."` on Lucide icons in flex containers. Use CSS classes with `flex-shrink: 0`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination | Custom JS paginator | Server-side `?page=N&per_page=50` + htmx prev/next links | API already paginates; htmx swaps are instant |
| Real-time updates | Custom WebSocket or polling | EventSource on `/api/lint/stream` | Already implemented in Phase 37 |
| Tab switching | Custom tab manager | Existing `initPanelTabs()` + `data-panel` attributes | Works automatically for any new tab |
| Object navigation | Custom routing | `window.openTab(iri, label)` | Already handles dockview panel creation |
| Label resolution | Client-side IRI parsing | API returns `object_label`, `path_label`, `object_type_label` | LintService resolves all labels server-side |

**Key insight:** Phase 37 did the hard work. The API returns fully resolved, human-readable data. The dashboard is purely a presentation layer consuming that API.

## Common Pitfalls

### Pitfall 1: Multiple EventSource Connections
**What goes wrong:** Each panel tab that uses SSE creates its own EventSource. If lint panel + lint dashboard both connect, there are duplicate listeners.
**Why it happens:** Per-object lint panel creates `window._lintSSE` in its `<script>` tag. Dashboard would create another.
**How to avoid:** Use a single shared EventSource. Store it on `window._lintSSE`. Dashboard script checks if it already exists and adds its own listener instead of creating a new connection. Or, refactor to a shared SSE manager.
**Warning signs:** Multiple SSE connections visible in browser DevTools Network tab.

### Pitfall 2: Tab Pane ID Mismatch
**What goes wrong:** Panel tab `data-panel="X"` must match pane `id="panel-X"`. If mismatched, clicking the tab shows nothing.
**Why it happens:** The `_applyPanelState()` function constructs `'panel-' + panelState.activeTab` to find the pane.
**How to avoid:** Use `data-panel="lint-dashboard"` and `id="panel-lint-dashboard"` consistently.
**Warning signs:** Tab click activates the tab visually but no content appears.

### Pitfall 3: Keyword Search SPARQL Injection
**What goes wrong:** Free-text search param passed directly into SPARQL FILTER clause.
**Why it happens:** The existing severity filter uses an allowlist (`SEVERITY_ALLOWLIST`). Keyword search is free-text.
**How to avoid:** Sanitize the search string: escape backslashes, quotes, and special SPARQL regex characters. Use SPARQL `CONTAINS(LCASE(?message), LCASE(?search))` for simple substring matching (no regex).
**Warning signs:** Search with quotes or backslashes causes SPARQL errors.

### Pitfall 4: Empty State on First Load
**What goes wrong:** Dashboard shows blank when no validation has ever run.
**Why it happens:** `get_latest_run_iri()` returns None if no lint runs exist.
**How to avoid:** Render a clear empty state: "No validation results yet. Save an object to trigger validation." Match the per-object panel's empty state pattern.
**Warning signs:** Blank panel with no guidance.

### Pitfall 5: Lucide Icons in Flex Filter Bar
**What goes wrong:** Icons disappear in the filter bar because SVGs collapse to 0 width.
**Why it happens:** Per CLAUDE.md, Lucide SVGs are flex items and need `flex-shrink: 0`.
**How to avoid:** CSS rule `.lint-dashboard-filters svg { width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor; }`.
**Warning signs:** Filter bar icons invisible but clickable.

## Code Examples

### Backend: lint-dashboard HTML endpoint
```python
# backend/app/browser/router.py -- new endpoint
@router.get("/lint-dashboard")
async def lint_dashboard(
    request: Request,
    page: int = 1,
    severity: str | None = None,
    object_type: str | None = None,
    search: str | None = None,
    sort: str = "severity",
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    # Get paginated results (with new search/sort params)
    results = await lint_service.get_results(
        page=page, per_page=50,
        severity=severity, object_type=object_type,
    )
    status = await lint_service.get_status()
    types = await shapes_service.get_types()

    return templates.TemplateResponse(request, "browser/lint_dashboard.html", {
        "request": request,
        "results": results,
        "status": status,
        "types": types,
        "current_severity": severity or "",
        "current_type": object_type or "",
        "current_search": search or "",
        "current_sort": sort,
    })
```

### Template: Summary Bar
```html
<div class="lint-dashboard-summary">
  <span class="lint-dashboard-total">{{ status.violation_count + status.warning_count + status.info_count }} issues</span>
  {% if status.violation_count > 0 %}
  <span class="lint-count-violations">&#9679; {{ status.violation_count }}</span>
  {% endif %}
  {% if status.warning_count > 0 %}
  <span class="lint-count-warnings">&#9650; {{ status.warning_count }}</span>
  {% endif %}
  {% if status.info_count > 0 %}
  <span class="lint-count-infos">&#9432; {{ status.info_count }}</span>
  {% endif %}
  {% if status.conforms %}
  <span class="lint-conforms">&#10003; All clear</span>
  {% endif %}
  <span class="lint-dashboard-timestamp">{{ status.run_timestamp or 'Never' }}</span>
</div>
```

### Command Palette Registration
```javascript
// In initCommandPalette(), add to ninja.data array:
{
  id: 'toggle-lint-dashboard',
  title: 'Toggle Lint Dashboard',
  section: 'View',
  handler: function () {
    panelState.activeTab = 'lint-dashboard';
    if (!panelState.open) panelState.open = true;
    _applyPanelState();
    savePanelState();
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-object lint only | Per-object + global API | Phase 37 | Dashboard now possible |
| Polling (`hx-trigger="every 10s"`) | SSE EventSource | Phase 37 | Real-time updates, lower latency |
| No structured lint data | Per-run named graphs with structured triples | Phase 37 | Queryable, filterable, diffable |

**Deprecated/outdated:**
- Polling pattern for lint: The per-object panel was migrated from polling to SSE in Phase 37. Dashboard should use SSE from the start.

## Open Questions

1. **Keyword search implementation**
   - What we know: API needs a `?search=` param for LINT-06. SPARQL `CONTAINS()` works for substring matching.
   - What's unclear: Should search match against message text only, or also object label and path label? (Requirement says "keyword across message text, property path, and object label")
   - Recommendation: Search across all three fields using `FILTER(CONTAINS(LCASE(?message), LCASE(?search)) || CONTAINS(LCASE(STR(?focusNode)), LCASE(?search)))`. For path labels, search the resolved label string server-side after SPARQL query (simpler than joining labels in SPARQL).

2. **Sort parameter implementation**
   - What we know: API currently sorts by `?focusNode ?severity`. LINT-07 requires sort by severity, object name, property path, or timestamp.
   - What's unclear: Sorting by object name requires label resolution which happens post-query. Sorting by timestamp means run timestamp (same for all results in a run).
   - Recommendation: Sort by severity (SPARQL ORDER BY), by object (ORDER BY ?focusNode), by path (ORDER BY ?path). "Timestamp" sort is less useful since all results in a run share the same timestamp -- could sort by run recency if multi-run view is added later.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (chromium project) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/04-validation/` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LINT-03 | Health indicator badge visible on LINT tab | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts -g "health badge"` | No -- Wave 0 |
| LINT-04 | Filter by severity | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts -g "severity filter"` | No -- Wave 0 |
| LINT-05 | Filter by object type | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts -g "type filter"` | No -- Wave 0 |
| LINT-06 | Keyword search | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts -g "keyword search"` | No -- Wave 0 |
| LINT-07 | Sort results | e2e | `npx playwright test tests/04-validation/lint-dashboard.spec.ts -g "sort"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/04-validation/`
- **Per wave merge:** `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/04-validation/lint-dashboard.spec.ts` -- covers LINT-03 through LINT-07 (new file)
- Note: Test infrastructure (Playwright, config, helpers) already exists. Only the test file is needed.

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** -- `backend/app/lint/router.py`, `service.py`, `models.py`, `broadcast.py`
- **Codebase inspection** -- `backend/app/templates/browser/lint_panel.html` (per-object lint panel reference)
- **Codebase inspection** -- `backend/app/templates/browser/inference_panel.html` (filter pattern reference)
- **Codebase inspection** -- `backend/app/templates/browser/workspace.html` (bottom panel tab structure)
- **Codebase inspection** -- `frontend/static/js/workspace.js` (panel state, tab switching, command palette)
- **Codebase inspection** -- `frontend/static/css/workspace.css` (panel CSS, lint CSS)
- **Codebase inspection** -- `frontend/static/css/theme.css` (color variables for light/dark)

### Secondary (MEDIUM confidence)
- Phase 37 CONTEXT.md decisions (SSE architecture, API design choices)

### Tertiary (LOW confidence)
- None -- all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- patterns directly observed in inference panel and existing lint panel
- Pitfalls: HIGH -- derived from actual codebase patterns and CLAUDE.md rules

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- internal codebase patterns)