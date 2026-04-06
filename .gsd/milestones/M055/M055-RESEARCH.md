# M055 Research: Browser History & Tab Recovery

## Executive Summary

M055 addresses a fundamental usability gap: the workspace URL never changes as users navigate, making bookmarks, link sharing, and browser back/forward impossible. The codebase is well-positioned for this work — all tab opens funnel through a small set of functions in `workspace.js`, dockview provides the right lifecycle events, and the History API integration is straightforward. The hardest part is the URL format design and the closed-tab recovery stack (which doesn't exist yet).

## Codebase Analysis

### Tab System Architecture

The workspace uses dockview-core 4.11.0 as the panel manager. All tab operations flow through functions in `workspace.js`:

**Tab ID conventions (panel IDs):**
- Object tabs: raw IRI string (e.g., `urn:sempkm:current:abc123`)
- View tabs: `view:{viewId}`
- Special tabs: `special:docs`, `special:canvas`, `special:vfs`, `special:import`, `special:rdf-import`, `special:ontology`
- Dashboard tabs: `dashboard:{dashboardId}`
- App tabs: `app-page:{appId}:{pageId}`, `app-view:{appId}:{viewId}`
- Catalog tabs: `catalog:list`, `catalog:{appId}`
- Workflow tabs: `workflow:{workflowId}`
- Generic views: `generic-view:{renderer}:scope:{scopeQuery}` or `generic-view:{renderer}:{timestamp}`
- Dashboard/workflow builders: `dashboard-builder:{id}`, `workflow-builder:{id}`
- Create forms: `__new-object-{timestamp}` (ephemeral, filtered from layout save)

**Key tab functions (all on `window.SemPKM`):**
- `openTab(iri, label, mode)` — object tabs (used by ~20 templates)
- `openViewTab(viewId, viewLabel, viewType)` — named views
- `openGenericViewTab(renderer, scopeQuery, ...)` — generic renderers
- `openSettingsTab()`, `openDocsTab()`, `openCanvasTab()`, `openDashboardTab()`, etc. — special tabs
- `closeTab(iri)` — delegates to `panel.api.close()`
- `getActiveTabIri()` — returns `dv.activePanel.id`

### Existing URL/History Handling

Currently minimal and one-directional (writes but never reads back):

1. **`?panel=sparql`** — handled on init, opens SPARQL console, then cleaned from URL via `replaceState`
2. **`#ontology-viewer`** — handled on init via hash check, opens ontology tab, then cleaned
3. **`?tour=welcome`** — starts guided tour, then cleaned from URL
4. **Import navigation** — `pushState({}, '', '/browser/import')` but this breaks on page reload (no server route catches it)

The pattern is consistent: query params are consumed once on page load and immediately cleaned. No popstate listener exists anywhere.

### Dockview Event Hooks (Integration Points)

1. **`dv.onDidActivePanelChange(panel)`** — fires when any panel becomes active. Currently dispatches `sempkm:tab-activated` custom event. **This is where URL update (pushState/replaceState) should be wired.**

2. **`dv.onDidRemovePanel(panel)`** — fires when a panel is removed. The dockview source confirms it passes `{ panel }` or the panel object, but the current handler ignores the argument. **This is where closed-tab stack capture should be wired.**

3. **`dv.onDidLayoutChange()`** — fires on any layout mutation. Currently saves to localStorage. Not needed for history.

### Server-Side Routes

- `GET /browser/` → renders full workspace page (workspace.html)
- `GET /browser/object/{object_iri:path}` → renders object tab HTML partial (htmx target)
- `GET /browser/views/{type}/{view_id}` → renders view partial
- `GET /browser/dashboard/{id}` → renders dashboard partial

The `/browser/` route accepts no query parameters currently. All object/view routes return **HTML partials** designed for htmx swap, not full pages. Deep linking requires the workspace to load first, then open a tab programmatically — the object partial alone is not a standalone page.

### nginx Config

Catch-all `location /` proxies everything to the backend. No special handling needed for query parameters — they pass through transparently.

## Technical Approach

### URL Format Decision

**Recommended: `?tab=` query parameter on `/browser/`**

Options considered:
1. **`/browser/?tab=<encoded-panel-id>`** — simple, clean, backward-compatible with existing `/browser/` route. No server changes for basic case.
2. **`/browser/object/<encoded-iri>`** — prettier but requires a new server route that renders the full workspace page with the object pre-opened. More complex.
3. **Hash routing (`#tab=...`)** — no server changes at all, but ugly and conflicts with existing `#ontology-viewer` usage.

Query parameter wins because:
- The server route `/browser/` already exists — just needs to read `?tab=` and pass to template context
- The frontend already handles `?panel=sparql` this way — proven pattern
- No nginx config changes
- Encodes naturally in browser bookmarks and share links
- Works with `history.pushState` for clean back/forward

### History API Strategy

**pushState for tab switches, replaceState for URL cleanup:**

```javascript
// On active panel change:
dv.onDidActivePanelChange(function(panel) {
    // ... existing tab-activated dispatch ...
    
    // Update URL to reflect focused tab
    var url = new URL(window.location.href);
    if (panel && panel.id) {
        url.searchParams.set('tab', panel.id);
    } else {
        url.searchParams.delete('tab');
    }
    history.pushState({ tabId: panel.id }, '', url.toString());
});

// On popstate (back/forward):
window.addEventListener('popstate', function(e) {
    if (e.state && e.state.tabId) {
        // Focus existing panel or open it
        var existing = dv.panels.find(p => p.id === e.state.tabId);
        if (existing) {
            existing.api.setActive();  // Don't re-pushState!
        } else {
            // Panel was closed — could reopen or just update URL
        }
    }
});
```

**Critical subtlety:** The `popstate` handler must NOT trigger another `pushState` when it activates a panel. Need a guard flag (`_navigatingFromHistory = true`) to suppress the pushState in `onDidActivePanelChange` during popstate-driven activation.

### Closed Tab Recovery Stack

No recovery mechanism exists. Need:

1. **Capture on close:** Wire `dv.onDidRemovePanel` to push `{ id, component, params, title }` onto a `_closedTabStack` array (capped at ~20 entries).

2. **Reopen command:** New `reopenClosedTab()` function that pops from stack and calls the appropriate `open*Tab()` function based on `component` type.

3. **Entry points:**
   - Keyboard shortcut: `Ctrl+Shift+T` (matches browser convention)
   - Command palette: "Reopen Closed Tab" entry
   - Tab context menu: "Reopen Closed Tab" entry

4. **Persistence:** The closed-tab stack should be session-only (in-memory array, maybe sessionStorage). Not worth persisting to localStorage across browser sessions.

### Deep Link Handling on Page Load

When `/browser/?tab=urn:sempkm:current:abc123` is loaded:

1. Server-side: pass `tab` query param through to template context
2. Client-side: after `initWorkspaceLayout()` completes and dockview restores layout, check URL for `?tab=` param
3. If tab is already open (from layout restore), just focus it
4. If tab is not open, call `openTab(tabId)` to load it
5. Clean the URL (or leave it — keeping it is fine for bookmarkability)

**Edge case:** The tab ID is a panel ID like `urn:sempkm:current:abc123`. For object tabs this works because `openTab(iri, label)` can fetch the label. For view/special tabs, the label isn't in the URL. Options:
- Store `{id, label, component}` in the pushState state object (not visible in URL but available on popstate)
- Accept that shared URLs for non-object tabs might show a generic title until content loads
- Only put object IRIs in the URL; views/special tabs don't get URL representation

**Recommendation:** Start with object tabs only in the URL. Views and special tabs don't benefit much from bookmarking (they're transient explorations). This keeps the URL clean and avoids encoding complexity.

## Risk Assessment

### Low Risk
- **URL update on tab switch** — straightforward History API, well-understood pattern, single integration point (`onDidActivePanelChange`). Proven by existing `?panel=sparql` handling.
- **Command palette entry** — ninja-keys already has 30+ entries, adding one more is trivial.
- **Keyboard shortcut** — existing `_keydownHandler` handles all Alt+key shortcuts. Adding Ctrl+Shift+T is one `if` block.

### Medium Risk
- **History navigation guard flag** — popstate→setActive→onDidActivePanelChange loop must be broken. Missing the guard causes infinite pushState. This is a known pattern but easy to get wrong.
- **Deep link on page load** — timing between dockview layout restore and tab opening from URL param. If the layout hasn't finished restoring when we try to open the tab, dockview might error or create a duplicate. Need a sequencing delay or callback.
- **Tab ID encoding in URLs** — IRIs contain colons, slashes, and other special characters. `encodeURIComponent()` handles most, but need to verify round-trip with `decodeURIComponent()`.

### Low Risk (but worth noting)
- **Closed tab stack capture** — `onDidRemovePanel` provides the panel object. Need to verify that `panel.params` and `panel.title` are still readable at the moment the event fires (panel might already be disposed). If not, need to capture metadata from `_tabMeta` before it's deleted.

## Slice Boundary Recommendations

### S01: URL Sync & Back/Forward Navigation (highest risk)
- Add `?tab=` pushState on active panel change
- Add `popstate` listener to navigate back/forward between tabs
- Guard flag to prevent pushState→popstate→pushState loop
- Handle deep link from `?tab=` query param on page load
- **Prove:** Open A → URL shows A → Open B → URL shows B → Back → A focused → URL shows A

### S02: Closed Tab Recovery (independent of S01)
- Closed-tab stack in `workspace-layout.js` (capture on `onDidRemovePanel`)
- `reopenClosedTab()` function that dispatches to correct `open*Tab()` based on component type
- Ctrl+Shift+T keyboard shortcut
- Command palette "Reopen Closed Tab" entry
- **Prove:** Close tab → Ctrl+Shift+T → tab reopens with same content

### S03: Deep Link Bookmarking (depends on S01)
- Verify bookmarked URLs work: copy URL → paste in new tab → correct object opens
- Handle the timing: workspace loads → dockview restores → check URL → open tab
- Server-side: pass `tab` query param to template context (optional — could be pure client-side)
- E2E tests proving the round-trip
- **Prove:** Copy URL while viewing object A → open in new browser tab → object A opens

S01 carries the most risk (History API state machine). S02 is independent and could go first if risk-ordering prefers it. S03 is an integration test of S01's deep link path.

## Existing Patterns to Reuse

| Pattern | Where | Apply To |
|---------|-------|----------|
| `?panel=sparql` URL consumption on init | `workspace.js` initBottomPanel | `?tab=` deep link handling |
| `_tabMeta` sidecar for panel metadata | `workspace-layout.js` | Closed tab stack metadata |
| ninja-keys command palette entries | `workspace.js` initCommandPalette | "Reopen Closed Tab" command |
| `_keydownHandler` keyboard shortcuts | `workspace.js` initKeyboardShortcuts | Ctrl+Shift+T binding |
| `dv.onDidActivePanelChange` event | `workspace-layout.js` | URL pushState trigger |
| `dv.onDidRemovePanel` event | `workspace-layout.js` | Closed tab stack capture |
| `openTab(iri, label, mode)` dispatch | `workspace.js` | Reopen from stack |
| E2E `dockview.ts` helpers | `e2e/helpers/dockview.ts` | History navigation tests |

## Requirements Analysis

No explicit requirements exist for M055 yet. Candidate requirements from the milestone context:

### Table Stakes (should become requirements)
1. **URL reflects active tab** — URL updates when user switches tabs (the core value proposition)
2. **Back/forward navigation** — browser back/forward buttons navigate tab focus history
3. **Closed tab recovery** — Ctrl+Shift+T reopens last closed tab (matches browser UX convention)

### Should Likely Be Requirements
4. **Bookmarkable URLs** — pasting a bookmarked URL opens the correct object
5. **Shareable URLs** — giving someone a URL opens the correct object (same as bookmarkable, different use case)

### Probably Not Requirements (advisory)
6. **Full workspace state in URL** — encoding all open tabs + positions in URL (explicitly out of scope per context)
7. **View tab URLs** — URL representation for non-object tabs (low value, high complexity)
8. **Cross-session closed tab stack** — persisting the stack across browser restarts (session memory is sufficient)

## Constraints

1. **No server-side route changes needed for basic URL sync** — `?tab=` query params pass through nginx to FastAPI but don't need to be read server-side if handled entirely client-side.
2. **Deep linking might need one server-side change** — if we want the server to pre-render an object in the initial HTML (avoiding a flash of empty workspace), the `/browser/` endpoint needs to read `?tab=` and include it in template context. But client-side handling after page load works fine without this.
3. **Object tab IDs are IRIs** — they encode/decode cleanly with `encodeURIComponent`/`decodeURIComponent`. No special handling needed.
4. **Layout restore happens in `initWorkspaceLayout()`** — deep link tab opening must happen AFTER this completes, or it risks conflicting with the restored layout.
5. **The `Alt+W` shortcut already closes tabs** — Ctrl+Shift+T for reopen is the natural complement.
6. **`_switchingPersona` guard flag pattern** — already exists in codebase for suppressing layout save during persona switch. Same pattern applies for the history navigation guard.

## Technology Notes

- **History API** — standard `pushState`, `replaceState`, `popstate`. No library needed. Well-supported across all browsers.
- **dockview-core 4.11.0** — provides `onDidActivePanelChange`, `onDidRemovePanel` with panel reference. No built-in history support — must be wired manually.
- **ninja-keys** — web component for command palette. Already has 30+ entries. Adding "Reopen Closed Tab" is one object push to `ninja.data`.

No external libraries needed. No skills to install. This is pure application-layer work using standard browser APIs.
