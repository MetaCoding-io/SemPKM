# Domain Pitfalls: v2.0 Tighten Web UI

**Domain:** Adding split panes, dark mode, settings, event log, LLM proxy, and guided tours to existing htmx/vanilla JS + FastAPI application
**Researched:** 2026-02-23
**Confidence:** HIGH for htmx integration pitfalls (derived from codebase analysis + documented issues); MEDIUM for LLM streaming and Shepherd.js specifics (WebSearch-verified)

---

## Critical Pitfalls

Mistakes that cause rewrites or major architectural pain.

### Pitfall 1: Split.js Destroy/Recreate Fragility When Adding Editor Groups

**What goes wrong:**
The current workspace uses a single `Split(['#nav-pane', '#editor-pane', '#right-pane'])` instance for the three-column layout. VS Code-style split panes require dynamically adding/removing editor groups (splitting the center pane into 2-3 editors side by side). Split.js has no API for dynamically adding or removing panes -- you must destroy the entire instance and recreate it with new DOM elements. During the destroy/recreate cycle, if a user is mid-drag, the gutter removal fails with "Failed to execute 'removeChild' on 'Node'" errors. The tab state (`sessionStorage`) becomes out of sync with the actual DOM because tabs are now distributed across multiple editor groups. The entire workspace flickers during reconstruction.

**Why it happens:**
Split.js is designed for static layouts. Its `destroy()` method removes gutters and CSS but does not handle in-flight drag events. The existing code stores tab state as a single flat array (`sempkm_open_tabs`), which assumes one tab bar. Adding editor groups means tab state must become a tree structure (groups containing tabs), but the existing `renderTabBar()`, `openTab()`, `closeTab()`, and `switchTab()` functions all assume a single tab bar and a single `#editor-area` target.

**Consequences:**
- Complete rewrite of tab management if not designed correctly up front
- Loss of user's open tabs during group operations
- Broken htmx content loading (hardcoded `#editor-area` target throughout workspace.js and all htmx partials)

**Prevention:**
- Design the editor group data model FIRST before touching Split.js. Each group needs: a unique ID, its own tab array, its own active tab, and its own content container. Store as `{ groups: [{ id, tabs: [], activeTab }], layout: [sizes] }`.
- Create a `WorkspaceLayout` manager class that wraps Split.js. This class owns the destroy/recreate cycle and debounces it (no reconstruct during drag). It maintains a mapping from group IDs to DOM container IDs.
- Change all htmx `hx-target` attributes and `htmx.ajax()` calls to target a dynamically-determined container (`#editor-area-{groupId}`) instead of the hardcoded `#editor-area`.
- Implement drag-to-split as a two-step operation: (1) user initiates split via button or keyboard shortcut (not drag -- drag tabs between existing groups only), (2) workspace layout manager handles the Split.js teardown/rebuild.
- Gate the feature: if only one editor group exists, the layout behaves exactly as v1 (no Split.js nesting, no overhead).

**Detection:**
- Tab state losing items after split/unsplit operations
- `TypeError: Cannot read properties of null` on `#editor-area` after group operations
- Editor content loading into wrong group after switching tabs

**Phase to address:**
Must be designed in Phase 1 (architecture planning) and implemented early. All other features that load content into the editor area depend on the multi-group addressing scheme.

---

### Pitfall 2: Dark Mode CSS Causes Flash of Wrong Theme (FOWT) and Misses Third-Party Components

**What goes wrong:**
Three separate failures happen simultaneously:

1. **Flash of light theme:** User has saved dark mode preference in localStorage. On page load, the browser renders the default light theme for several paint cycles before JavaScript reads localStorage and applies the `data-theme="dark"` attribute. The user sees a blinding white flash on every navigation.

2. **CodeMirror ignores CSS custom properties:** CodeMirror 6 has its own theming system using `EditorView.theme()` and the `&dark`/`&light` selectors. It does NOT automatically respond to CSS custom property changes on `:root`. Changing `--color-bg` does nothing to the editor. The editor remains light-themed in a dark UI, creating a jarring contrast.

3. **Third-party components miss the memo:** ninja-keys, Cytoscape.js graph view, and any `<iframe>` content (docs page) have their own styling. Toggling a `data-theme` attribute on `<html>` does not propagate into these components without explicit integration for each one.

**Why it happens:**
The current CSS uses `var(--color-*)` custom properties defined on `:root` (see style.css lines 3-28), which is the correct foundation. But the theme toggle JavaScript runs after first paint. CodeMirror 6 uses a different styling paradigm (JavaScript-defined themes in `EditorView.theme()`, not CSS custom properties). The third-party components each have their own theming APIs that need separate integration.

**Consequences:**
- Users complain about the flash on every page load, especially in dark environments
- The Markdown editor (the primary writing surface) looks broken in dark mode
- Graph visualizations remain light-themed, making dark mode feel half-finished

**Prevention:**
- **Block FOWT with a `<script>` in `<head>`**: Add a synchronous inline script BEFORE any CSS loads that reads the theme preference and sets `document.documentElement.dataset.theme` immediately. This runs before first paint. Do NOT use an external JS file for this -- it must be inline in `base.html`'s `<head>`.
- **CodeMirror: use Compartment for theme switching**: Create both light and dark CodeMirror themes. Store the active theme in a `Compartment`. When the user toggles dark mode, dispatch a `Compartment.reconfigure()` on all active editor instances. The `editors` registry in `editor.js` already tracks all instances -- iterate and reconfigure.
- **ninja-keys**: Override its CSS custom properties (`--ninja-accent-color`, `--ninja-text-color`, `--ninja-modal-background`) in the dark theme scope, which the existing code already partially does (workspace.css line 456-458).
- **Cytoscape.js**: Re-apply the graph stylesheet with dark-mode-appropriate node/edge colors when theme changes. The graph view already fetches `type_colors` -- extend this to include theme-appropriate defaults.
- **Respect `prefers-color-scheme`**: Implement three-state toggle: Light / Dark / System. Default to System. Use `window.matchMedia('(prefers-color-scheme: dark)')` with a change listener so the app responds to OS-level theme changes. The CSS `light-dark()` function has full browser support since May 2024 and can simplify color declarations.

**Detection:**
- White flash visible on page load when theme is dark
- CodeMirror editor has white background in dark mode
- Graph nodes have light-theme colors in dark mode
- Third-party modal (ninja-keys command palette) looks wrong in dark mode

**Phase to address:**
Implement the `<head>` inline script and CSS custom property dark theme in the same phase. CodeMirror theme switching should be part of the same phase to avoid shipping half-broken dark mode.

---

### Pitfall 3: htmx afterSwap Event Listener Duplication and Library Re-initialization

**What goes wrong:**
The existing code already has an `htmx:afterSwap` listener in `workspace.js` (lines 776-799) that re-initializes the workspace and scans for new tree leaves. Adding dark mode, Shepherd.js tours, and new UI components means MORE afterSwap listeners. Each htmx content swap potentially fires multiple listeners, and if listeners are not carefully scoped, they accumulate: the same handler fires 2x, 3x, N times after repeated swaps, causing duplicated event handlers, performance degradation, and erratic behavior.

Additionally, Split.js instances inside swapped content (e.g., the form/editor vertical split in `object_tab.html`) need re-initialization after swap but their old instances are NOT cleaned up. The existing code calls `initSplit()` again on afterSwap, which creates a NEW Split.js instance without destroying the old one if the workspace element persists.

**Why it happens:**
htmx 2.x has documented edge cases where `htmx:afterSwap` does not fire when responses begin with newlines, when multi-swap replaces the calling element, or when `hx-swap="none"` is set. The event fires on the target element, not globally, but the existing code listens on `document` (global), so it catches ALL swaps. There is no mechanism to remove stale listeners when content is replaced. The `htmx:beforeCleanupElement` event (which fires before htmx removes an element) is the correct place to tear down third-party library instances, but it is not used in the current codebase.

**Consequences:**
- Memory leaks from accumulated event listeners
- Shepherd.js tour steps firing multiple times
- Split.js instances accumulating (duplicate gutters)
- Intermittent bugs that appear "after using the app for a while"

**Prevention:**
- **Use `htmx:beforeCleanupElement`** to tear down library instances (Split.js, CodeMirror, Shepherd tours, Cytoscape) before their container is removed from the DOM.
- **Scope afterSwap listeners**: Instead of a single global `document.addEventListener('htmx:afterSwap', ...)`, use targeted listeners on specific containers, or check `e.detail.target.id` early in the handler and bail if it is not the expected target.
- **Singleton pattern for workspace init**: The `init()` function in workspace.js is called multiple times but does not check if it has already run. Add an `initialized` flag or use `{ once: true }` for one-time setup, and separate one-time init from per-swap re-init.
- **Editor cleanup**: The `destroyEditor()` function exists but is never called automatically. Register a cleanup handler that calls `destroyEditor()` when the object tab is swapped out.

**Detection:**
- Multiple gutter elements appearing in the same pane
- Console warnings about duplicate event listeners
- Tour popups appearing twice
- Performance profiler showing growing listener counts

**Phase to address:**
Fix the afterSwap/cleanup architecture FIRST, before adding any new features that require initialization on swap. This is a foundational fix that all subsequent features depend on.

---

## Moderate Pitfalls

### Pitfall 4: Settings System Scope Confusion and Schema Validation Cost

**What goes wrong:**
A VS Code-style settings system with global + mental model/app-contributed settings seems straightforward, but three issues emerge:

1. **Scope resolution order is complex**: Settings can come from: built-in defaults, global user preferences, mental-model-contributed defaults, and per-workspace overrides. When a setting exists at multiple scopes, which wins? VS Code's resolution (workspace > user > default) is well-defined but requires careful implementation. Getting it wrong means settings silently fail to apply.

2. **JSON schema validation is expensive in the browser**: If settings use JSON Schema for validation (to support model-contributed settings with defined types), validators like `ajv` add 50-100KB to bundle size and use `eval()` by default, which violates Content Security Policy. Alternatives that avoid eval exist (`ajv` with code generation disabled) but are less performant.

3. **Settings changes require coordinating multiple systems**: Changing the theme setting must update CSS, CodeMirror theme compartments, Cytoscape styles, and ninja-keys. Changing editor font size must update CodeMirror config. This cross-cutting coordination is where bugs hide.

**Prevention:**
- Store settings server-side in SQLite (via the existing SQLAlchemy setup), not in localStorage. This makes settings available to the backend (for SSR decisions like default theme) and avoids localStorage's 5MB limit and lack of structure.
- Define a simple settings registry in Python (Pydantic model with defaults). Each setting has: key, type, default, scope, and an optional JSON Schema for model-contributed settings. Validate on the server, not in the browser.
- Use a pub/sub pattern for settings changes: `window.dispatchEvent(new CustomEvent('sempkm:setting-changed', { detail: { key, value } }))`. Each component (CodeMirror, Cytoscape, CSS theme) listens for its relevant keys. This decouples the settings UI from the consumers.
- Start with only the settings you need for v2.0: theme (light/dark/system), editor font size, sidebar collapsed state. Do not build a generic "extensible settings framework" until it is needed.

**Detection:**
- Settings saved but not taking effect (scope resolution bug)
- Page load slow due to JSON Schema validation of all settings
- Theme toggle works but editor font size does not (missing subscriber)

**Phase to address:**
Settings system should be implemented BEFORE dark mode (dark mode is a setting). But keep the initial implementation minimal -- avoid over-engineering the schema validation until model-contributed settings are actually needed.

---

### Pitfall 5: Event Log Explorer SPARQL Performance on Large Event Stores

**What goes wrong:**
The event log is stored as RDF named graphs in the triplestore. An event log viewer needs to: list events in reverse chronological order, filter by event type and object, show diffs between event states, and support pagination. SPARQL `LIMIT`/`OFFSET` pagination over named graphs becomes progressively slower as the offset increases (the triplestore must still scan all preceding results). Filtering events by type or object requires querying INTO named graphs (using `GRAPH ?g { ... }` patterns), which some triplestores handle inefficiently.

For a PKM with 1,000 objects and an average of 10 events per object (10,000 named graphs), listing "recent events" with `ORDER BY DESC(?timestamp) LIMIT 20 OFFSET 200` can take seconds on RDF4J if the event graph index is not optimized.

**Prevention:**
- **Use cursor-based pagination** instead of OFFSET pagination. Each event has a timestamp; page forward/backward using `FILTER(?timestamp < ?lastSeen)` with `LIMIT`. This is O(1) regardless of how deep into the log you are.
- **Maintain an event index graph**: A single named graph (`sempkm:event-index`) that contains lightweight triples mapping event graph IRIs to their timestamp, type, affected object, and actor. Query the index graph for listing/filtering (fast: single graph scan), then fetch full event details on demand.
- **Lazy diff computation**: Do not pre-compute diffs. When a user clicks on an event to see the diff, fetch the event's graph and the previous event's graph for the same object, compute the diff server-side (set difference on triples), and return the formatted diff as an htmx partial.
- **Set hard limits**: Cap the event log viewer at displaying the most recent N events (e.g., 1,000). Older events are available only through explicit search.

**Detection:**
- Event log page takes >1s to load with pagination
- "Load more" button becomes progressively slower
- Browser tab freezes when rendering large diff output

**Phase to address:**
Design the event index graph structure when implementing the event log viewer. Consider adding the index graph as part of the event write path (add a triple to the index graph for each new event).

---

### Pitfall 6: LLM Streaming Proxy -- SSE Buffering, Timeouts, and Key Exposure

**What goes wrong:**
Three distinct failure modes when adding an LLM API proxy:

1. **Nginx buffers SSE responses**: The existing Docker Compose setup uses nginx as a reverse proxy for the frontend. By default, nginx buffers upstream responses. SSE (Server-Sent Events) requires unbuffered streaming. Without `proxy_buffering off` and `X-Accel-Buffering: no`, the user sees no output until the entire LLM response completes -- defeating the purpose of streaming.

2. **Connection timeout kills long responses**: Nginx's default `proxy_read_timeout` is 60 seconds. LLM responses (especially for long content or slow endpoints like Claude) can exceed this. The connection drops mid-response with a 504 Gateway Timeout.

3. **API key exposure in browser**: If the frontend sends LLM API keys directly to the external API (bypassing the backend proxy), the keys are visible in browser DevTools Network tab. Even with a proxy, if the proxy endpoint does not require authentication, anyone on the network can use it as a free LLM gateway.

**Prevention:**
- **Configure nginx for SSE**: Add to the nginx location block for the LLM proxy endpoint: `proxy_buffering off`, `proxy_cache off`, `proxy_read_timeout 300s`, `proxy_set_header X-Accel-Buffering no`, and `chunked_transfer_encoding on`.
- **Backend-only key storage**: API keys are stored server-side (encrypted in SQLite, never sent to the frontend). The frontend sends requests to `/api/llm/chat` on the FastAPI backend; the backend adds the API key and proxies to the configured LLM endpoint. The settings UI for LLM configuration accepts the key via a password input and stores it via a POST endpoint.
- **Use `sse-starlette`** for the SSE endpoint instead of raw `StreamingResponse`. It handles proper SSE formatting, client disconnect detection, and heartbeat pings to keep connections alive.
- **Rate limiting**: Add per-user rate limiting on the proxy endpoint to prevent abuse if the instance is shared.
- **Heartbeat mechanism**: Send SSE comment lines every 15 seconds during LLM processing to prevent proxy/load balancer timeout.

**Detection:**
- LLM responses appear all at once instead of streaming token-by-token
- 504 errors on long responses
- API keys visible in browser Network tab
- Users on the same network using the LLM proxy without authentication

**Phase to address:**
LLM proxy and nginx configuration must be implemented together. Do not ship the proxy endpoint without the nginx SSE configuration.

---

### Pitfall 7: Shepherd.js Licensing Change and Dynamic Content Targeting

**What goes wrong:**
Two issues:

1. **Licensing trap**: Shepherd.js v14+ uses AGPL-3.0 for open source but requires a commercial license ($50-$300) for commercial applications. SemPKM is self-hosted open source, so AGPL-3.0 is likely acceptable, but this needs explicit verification. If SemPKM's license is incompatible with AGPL-3.0, Shepherd.js v14 cannot be used without a commercial license.

2. **Tour steps target elements that do not exist yet**: htmx loads content dynamically. The explorer tree, editor area, form fields, and right pane content are all loaded via htmx after initial page render. Shepherd.js tour steps that reference these elements by CSS selector fail because the element does not exist when the tour starts. The step appears in the wrong position or not at all.

**Prevention:**
- **Verify license compatibility**: SemPKM appears to be open source (self-hosted). If the project uses MIT or Apache-2.0, AGPL-3.0 dependency is problematic for redistribution. Consider: (a) using Shepherd.js v13 (MIT licensed, last MIT version), (b) switching to TourGuide JS (MIT licensed, actively maintained as of May 2025), or (c) purchasing the $50 Shepherd.js commercial license.
- **Use lazy element resolution**: Shepherd.js supports passing a function to `attachTo.element` that is called in the `before-show` phase. Use this for all steps targeting htmx-rendered content.
- **Trigger htmx loads before tour steps**: In the tour step's `beforeShowPromise`, use `htmx.ajax()` to load the required content, wait for the `htmx:afterSettle` event, then resolve the promise. This ensures the target element exists before the step attempts to attach.
- **Guard against missing elements**: Add a `when.show` handler that checks if the target element exists. If not, skip the step or show a modal fallback instead of an attached tooltip.

**Detection:**
- Tour steps appearing in the top-left corner (Shepherd's fallback when element not found)
- Console errors about missing attachTo elements
- Tours working on first run but failing on subsequent runs (stale DOM references)

**Phase to address:**
Evaluate the license issue BEFORE implementing. If AGPL-3.0 is incompatible, choose the alternative library early to avoid wasted integration work.

---

## Minor Pitfalls

### Pitfall 8: CSS Custom Property Naming Collision with Third-Party Libraries

**What goes wrong:**
The current CSS defines variables like `--color-bg`, `--color-surface`, `--color-text` on `:root`. These are common names. Third-party libraries or future dependencies may use identical variable names, causing unexpected style overrides.

**Prevention:**
- Namespace all SemPKM custom properties with a `--sempkm-` prefix: `--sempkm-color-bg`, `--sempkm-color-surface`, etc. This is a one-time migration of style.css and workspace.css.
- Alternatively, keep the short names but define them on `.dashboard-layout` or `.workspace-container` instead of `:root`, limiting their scope.
- Whichever approach: do it BEFORE adding dark mode (which will double the number of variable references).

**Detection:**
- Styles randomly breaking after adding a new third-party library
- Dark mode applying to some elements but not others

**Phase to address:**
Do the variable rename as a preparatory step before dark mode implementation. Much cheaper to do before the dark theme doubles all variable references.

---

### Pitfall 9: Collapsible Sidebar State Not Surviving htmx Navigation

**What goes wrong:**
The sidebar collapse state is managed client-side (CSS class toggle). On a full page reload or browser back/forward navigation, the sidebar reverts to its default expanded state because the collapsed state was only in the DOM, not persisted.

**Prevention:**
- Persist sidebar collapsed state in the settings system (server-side) or localStorage as a stopgap.
- On page load, the inline `<head>` script (same one that handles theme) should also read sidebar state and set the appropriate CSS class before first paint.
- When the sidebar transitions between collapsed and expanded, use CSS transitions (not display:none) to avoid layout shifts.

**Detection:**
- Sidebar expanding on page refresh
- Layout jump when sidebar collapses (content area width snaps instead of transitions)

**Phase to address:**
Same phase as the settings system, since sidebar state is a user preference.

---

### Pitfall 10: Inline onclick Handlers Create a Maintenance Nightmare

**What goes wrong:**
The current codebase uses inline `onclick` handlers extensively in both Jinja templates and JavaScript-generated HTML. Adding more interactive features (split panes, drag-to-split, context menus) will exponentially increase these inline handlers. They are hard to debug, impossible to unit test, and create XSS risks when user-provided strings (like object labels containing quotes) are interpolated.

The existing `escapeJs()` function (workspace.js line 735) handles single quotes and backslashes but would miss double quotes, angle brackets, or other special characters in labels, potentially breaking the onclick attribute or enabling DOM injection.

**Prevention:**
- Migrate to event delegation: instead of `onclick="openTab('iri', 'label')"` on each element, use `data-action="open-tab" data-iri="..." data-label="..."` attributes and a single delegated listener on the workspace container.
- This is a gradual migration -- do it feature-by-feature as each area is touched in v2.0, not as a big-bang rewrite.
- New v2.0 features should use the delegation pattern from day one.

**Detection:**
- Broken onclick handlers when object labels contain special characters
- Difficulty adding right-click context menus (inline onclick does not support this)

**Phase to address:**
Adopt the delegation pattern for all NEW code immediately. Migrate existing onclick handlers opportunistically when fixing bugs or touching the relevant templates.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Bug fixes (body loading, editor editability) | Fixing bugs in editor.js while other features change the editor initialization path | Fix bugs FIRST before restructuring editor init for dark mode and editor groups |
| Read-only object view | Read-only view loads into `#editor-area` but editor groups change the target | Design the multi-group addressing scheme before implementing read-only view |
| VS Code-style split panes | Split.js destroy/recreate breaks during drag; tab state model rewrite needed | Build WorkspaceLayout manager with debounced reconstruct; redesign tab state model first |
| Bottom panel infrastructure | Bottom panel is a fourth Split.js axis (vertical); nesting vertical inside horizontal split creates complexity | Use a separate vertical Split instance for the center column only, not nested in the main horizontal split |
| Collapsible sidebar | Sidebar collapse animation causes layout reflow that breaks Split.js sizes | Use CSS width transition with will-change: width; recalculate Split.js sizes after transition ends |
| Dark mode | CodeMirror, ninja-keys, Cytoscape all need separate dark mode integration | Budget time for each third-party component; do not assume CSS variables propagate |
| Settings system | Over-engineering the settings schema; scope resolution bugs | Start with 5-10 concrete settings, not a generic framework. Add model-contributed settings later |
| Event log explorer | SPARQL OFFSET pagination slows on large logs; diff computation is expensive | Cursor-based pagination; lazy diff loading; event index graph |
| LLM connection config | API key stored in localStorage; nginx buffers SSE | Server-side key storage only; nginx SSE configuration mandatory |
| Shepherd.js tutorials | License change in v14; dynamic elements not found | Verify license first; use lazy element resolution; consider v13 or TourGuide JS |
| Node type icons in graph | Icon rendering in Cytoscape requires image URIs, not CSS | Use Cytoscape background-image style property with data URIs or hosted SVGs, not CSS classes |

## Integration Risk Matrix

| Feature A | Feature B | Integration Risk | Why |
|---|---|---|---|
| Split panes | Dark mode | MEDIUM | Split.js gutter elements need dark mode styling; must be themed explicitly |
| Split panes | Settings system | LOW | Pane sizes already saved to localStorage; migrate to settings |
| Dark mode | CodeMirror editor | HIGH | Requires Compartment-based theme reconfiguration per editor instance |
| Dark mode | Graph view | MEDIUM | Cytoscape styles are JavaScript objects, not CSS; need programmatic update |
| Dark mode | Shepherd.js tours | LOW | Shepherd CSS is overridable; add dark theme styles |
| Settings system | LLM config | HIGH | API keys must be encrypted at rest; settings storage must handle sensitive values differently |
| Event log | Split panes | LOW | Event log renders as a standard htmx partial; just needs correct editor group targeting |
| Shepherd.js | htmx content | HIGH | Tour steps must wait for htmx content to load; requires beforeShowPromise integration |
| LLM streaming | nginx proxy | HIGH | SSE requires specific nginx configuration; will not work without it |
| Sidebar collapse | Split.js | MEDIUM | Sidebar width change requires Split.js to recalculate; use ResizeObserver or manual trigger |

## "Looks Done But Isn't" Checklist for v2.0

- [ ] **Dark mode toggle**: Does it work after a full page refresh? Does it work before JavaScript loads? Does it work in CodeMirror? In the graph view? In the command palette?
- [ ] **Split panes**: Can you split, move a tab to the new group, close the group, and have the tab return to the remaining group? Does closing the last tab in a group close the group?
- [ ] **Settings persistence**: Are settings available on the server side (for SSR theme class)? Do they survive container restarts (not just browser sessions)?
- [ ] **Event log pagination**: Does page 50 load as fast as page 1? (If using OFFSET, it won't.)
- [ ] **LLM streaming**: Does it work through nginx? What happens when the user navigates away mid-stream? Is the server-side connection properly cancelled?
- [ ] **Tour with dynamic content**: Do tours work when the user has no objects open? When the explorer tree is collapsed? After an htmx navigation?
- [ ] **Sidebar collapse + Split.js**: Does collapsing the sidebar cause the workspace content to expand smoothly, or does it leave a gap?
- [ ] **API key security**: Is the LLM API key visible anywhere in the frontend? In browser DevTools? In server logs?
- [ ] **Editor cleanup**: Open 10 tabs, close 8. Are the CodeMirror instances for the closed tabs destroyed, or are they leaking memory?
- [ ] **afterSwap handlers**: Use the app for 30 minutes, navigating repeatedly. Does memory usage stay flat? Do event handler counts stay stable?

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| Split.js editor groups break tab state | MEDIUM | Revert to single editor pane. Redesign tab state model. Reimplement with new model. Budget 2-3 days. |
| Dark mode flash of wrong theme | LOW | Add inline head script. 30-minute fix. |
| CodeMirror dark mode not working | LOW | Add Compartment-based theme switching. Requires modifying editor.js init and adding reconfigure calls. 1-2 hours per editor instance. |
| Shepherd.js license incompatibility | MEDIUM | Switch to TourGuide JS or Shepherd.js v13. API is similar but not identical. Budget 1 day for migration. |
| Nginx blocks SSE streaming | LOW | Add nginx SSE configuration. 15-minute fix once diagnosed. But hard to diagnose if you do not know to look for it. |
| Settings scope resolution wrong | MEDIUM | Debug which scope is winning. Fix the merge order. May require migration of existing saved settings. |
| Event log slow on large stores | HIGH | Requires adding event index graph and rewriting pagination. Potentially needs backfill migration for existing events. Budget 2-3 days. |
| API key leaked in browser | HIGH | Rotate compromised key immediately. Move to server-side-only key storage. Audit all network requests. |

## Sources

- [htmx afterSwap event issues](https://github.com/bigskysoftware/htmx/discussions/3190) -- documents cases where afterSwap does not fire as expected; MEDIUM confidence
- [htmx afterSwap firing with leading newlines](https://github.com/bigskysoftware/htmx/issues/2787) -- confirmed bug in htmx 2.0.x; HIGH confidence
- [htmx SSE Extension documentation](https://htmx.org/extensions/sse/) -- official docs for SSE reconnection and configuration; HIGH confidence
- [Split.js destroy during drag issue](https://github.com/nathancahill/split/issues/790) -- confirmed Split.js limitation; HIGH confidence
- [Split.js dynamic property update](https://github.com/nathancahill/split/issues/765) -- confirms no dynamic pane add/remove API; HIGH confidence
- [CodeMirror 6 dynamic theme switching](https://discuss.codemirror.net/t/dynamic-light-mode-dark-mode-how/4709) -- official forum guidance on Compartment-based theming; HIGH confidence
- [CSS light-dark() browser support](https://caniuse.com/mdn-css_types_color_light-dark) -- supported in all major browsers since May 2024; HIGH confidence
- [Shepherd.js license and pricing](https://docs.shepherdjs.dev/guides/license/) -- AGPL-3.0 + commercial dual license for v14+; HIGH confidence
- [Shepherd.js dynamic content issue](https://github.com/shepherd-pro/shepherd/issues/1201) -- documents inconsistent behavior with dynamically loaded elements; MEDIUM confidence
- [FastAPI SSE streaming guide](https://blog.gopenai.com/how-to-stream-llm-responses-in-real-time-using-fastapi-and-sse-d2a5a30f2928) -- covers nginx buffering and timeout pitfalls; MEDIUM confidence
- [CSS dark mode complete guide](https://css-tricks.com/a-complete-guide-to-dark-mode-on-the-web/) -- comprehensive guide including FOWT prevention; HIGH confidence
- [CSS dark mode toggle hackiness](https://code.mendhak.com/css-dark-mode-toggle-sucks/) -- documents real-world dark mode implementation frustrations; MEDIUM confidence
- [sse-starlette](https://github.com/sysid/sse-starlette) -- recommended SSE library for Starlette/FastAPI; MEDIUM confidence
- [LLM API security best practices](https://www.datasunrise.com/knowledge-center/ai-security/llm-api-security-tips/) -- covers proxy architecture and key management; MEDIUM confidence
- [SPARQL query performance on large datasets](https://www.sciencedirect.com/science/article/pii/S1570826814001061) -- academic research on SPARQL optimization; HIGH confidence
- SemPKM codebase analysis: workspace.js, editor.js, style.css, workspace.css, base.html -- direct code inspection; HIGH confidence

---
*Pitfalls research for: v2.0 Tighten Web UI (SemPKM)*
*Researched: 2026-02-23*
