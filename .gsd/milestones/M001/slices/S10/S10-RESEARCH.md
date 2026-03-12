# Phase 10: Bug Fixes and Cleanup Architecture - Research

**Researched:** 2026-02-23
**Domain:** htmx lifecycle management, CodeMirror 6 editor reliability, Split.js teardown, CSS dropdown positioning
**Confidence:** HIGH

## Summary

Phase 10 addresses five concrete bugs in the existing v1.0 workspace: unreliable CodeMirror body loading (FIX-01), editor editability/sizing race conditions with Split.js (FIX-02), autocomplete dropdown clipping (FIX-03), views explorer lazy-load requiring a user click (FIX-04), and resource accumulation from repeated tab navigation (FIX-05). The root cause of most issues is the absence of a coordinated cleanup lifecycle -- htmx swaps DOM content but the application never tears down CodeMirror instances, Split.js instances, or Cytoscape instances that were attached to the old DOM.

The fix requires establishing an `htmx:beforeCleanupElement` listener that walks replaced DOM subtrees and calls `.destroy()` on every tracked library instance before htmx removes the elements. This is the foundational architecture that all subsequent phases (dark mode reconfiguration, editor groups, event log) depend on.

**Primary recommendation:** Implement a centralized cleanup registry (`window._sempkmCleanup`) that maps DOM element IDs to teardown functions, with a single `htmx:beforeCleanupElement` event handler that invokes them. Fix the five bugs using this registry as the coordination point.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIX-01 | Body content loads reliably into the Markdown editor with a visible loading skeleton and graceful fallback after timeout | Loading skeleton CSS pattern + 3-second timeout with fallback textarea; bump CodeMirror to 6.28.5+ for Chrome EditContext leak fix |
| FIX-02 | CodeMirror editor is editable with proper minimum height regardless of Split.js initialization timing | CSS `min-height: 200px` on `.codemirror-container`, decouple editor init from Split.js init, ensure `contenteditable` is never overridden |
| FIX-03 | Autocomplete dropdown for reference properties positions correctly and clicking a suggestion populates the field | Move `.suggestions-dropdown` to `position: fixed` with dynamic positioning via JS, or increase `z-index` and ensure parent containers do not clip with `overflow: hidden` |
| FIX-04 | Views explorer section loads its content eagerly on workspace init (no perpetual "Loading..." state) | Change `hx-trigger="click once"` to `hx-trigger="load"` or fire the htmx request programmatically on workspace init |
| FIX-05 | htmx afterSwap cleanup architecture prevents listener accumulation and properly destroys library instances (Split.js, CodeMirror, Cytoscape) before DOM removal | `htmx:beforeCleanupElement` event + cleanup registry pattern; `.destroy()` calls for CodeMirror, Split.js, and Cytoscape |
</phase_requirements>

## Standard Stack

### Core (already in project)

| Library | Current Version | Target Version | Purpose | Action |
|---------|----------------|----------------|---------|--------|
| htmx | 2.0.4 | 2.0.4 (keep) | HTML-over-the-wire | Use `htmx:beforeCleanupElement` event for cleanup |
| CodeMirror 6 (@codemirror/view) | 6.28.2 | 6.28.5+ | Markdown editor | Bump to fix Chrome EditContext memory leak |
| Split.js | 1.6.5 | 1.6.5 (keep) | Resizable panes | Call `.destroy()` on cleanup |
| Cytoscape.js | 3.33.1 | 3.33.1 (keep) | Graph visualization | Call `.destroy()` on cleanup |
| ninja-keys | latest | latest (keep) | Command palette | No cleanup needed (web component) |

### Supporting (no new libraries needed)

This phase requires no new dependencies. All fixes use existing libraries and pure CSS/JS.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `htmx:beforeCleanupElement` | MutationObserver | MutationObserver is framework-agnostic but fires too late (after removal); htmx event fires BEFORE removal, which is what we need |
| CSS skeleton animation | Third-party skeleton library | Pure CSS is simpler and adds zero weight; a 3-line `@keyframes` pulse is sufficient |
| `position: fixed` dropdown | Portal/teleport pattern | No framework to teleport with; `position: fixed` with JS coordinate calculation achieves the same result in vanilla JS |

## Architecture Patterns

### Pattern 1: Cleanup Registry

**What:** A global registry that maps DOM element IDs to arrays of teardown functions. When `htmx:beforeCleanupElement` fires, the handler looks up the element (and its descendants) in the registry and calls each teardown function.

**When to use:** Every time a library instance (CodeMirror, Split.js, Cytoscape) is created inside htmx-swappable content.

**Example:**

```javascript
// Source: htmx official docs (htmx.org/events/) + GitHub Discussion #1823
(function() {
  // Registry: elementId -> [cleanupFn, cleanupFn, ...]
  window._sempkmCleanup = {};

  function registerCleanup(elementId, cleanupFn) {
    if (!window._sempkmCleanup[elementId]) {
      window._sempkmCleanup[elementId] = [];
    }
    window._sempkmCleanup[elementId].push(cleanupFn);
  }

  function runCleanup(elementId) {
    var fns = window._sempkmCleanup[elementId];
    if (fns) {
      fns.forEach(function(fn) {
        try { fn(); } catch (e) { console.warn('Cleanup error:', e); }
      });
      delete window._sempkmCleanup[elementId];
    }
  }

  // Listen for htmx cleanup events
  document.addEventListener('htmx:beforeCleanupElement', function(evt) {
    var el = evt.detail.elt;
    if (el && el.id) {
      runCleanup(el.id);
    }
    // Also check descendants (htmx fires on root, not children)
    if (el && el.querySelectorAll) {
      var descendants = el.querySelectorAll('[id]');
      descendants.forEach(function(child) {
        runCleanup(child.id);
      });
    }
  });

  window.registerCleanup = registerCleanup;
})();
```

### Pattern 2: Loading Skeleton with Timeout Fallback

**What:** Show a CSS-animated skeleton placeholder while the CodeMirror editor module loads via ESM import. If the editor fails to initialize within 3 seconds, hide the skeleton and show a plain `<textarea>` fallback with a user-visible message.

**When to use:** Every time an object tab is loaded (FIX-01).

**Example:**

```html
<!-- Skeleton placeholder -->
<div class="editor-skeleton" id="skeleton-{{ safe_id }}">
  <div class="skeleton-line" style="width: 80%"></div>
  <div class="skeleton-line" style="width: 60%"></div>
  <div class="skeleton-line" style="width: 90%"></div>
  <div class="skeleton-line" style="width: 45%"></div>
</div>

<style>
  .editor-skeleton {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .skeleton-line {
    height: 14px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
    border-radius: 4px;
  }
  @keyframes skeleton-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
</style>

<script>
  // 3-second timeout: if editor not ready, show fallback
  var timeout = setTimeout(function() {
    var skeleton = document.getElementById('skeleton-{{ safe_id }}');
    if (skeleton) skeleton.style.display = 'none';
    enableFallback();
    console.warn('CodeMirror editor timed out, using textarea fallback');
  }, 3000);

  // On successful init, clear timeout and hide skeleton
  function onEditorReady() {
    clearTimeout(timeout);
    var skeleton = document.getElementById('skeleton-{{ safe_id }}');
    if (skeleton) skeleton.style.display = 'none';
  }
</script>
```

### Pattern 3: Fixed-Position Autocomplete Dropdown

**What:** Move the suggestions dropdown out of the `overflow: hidden` ancestor chain by using `position: fixed` and calculating screen coordinates from the input's `getBoundingClientRect()`.

**When to use:** Reference property autocomplete fields (FIX-03).

**Example:**

```javascript
// Source: Common pattern for overflow-clipped dropdowns
function positionDropdown(inputEl, dropdownEl) {
  var rect = inputEl.getBoundingClientRect();
  dropdownEl.style.position = 'fixed';
  dropdownEl.style.top = rect.bottom + 'px';
  dropdownEl.style.left = rect.left + 'px';
  dropdownEl.style.width = rect.width + 'px';
  dropdownEl.style.zIndex = '9999';
  dropdownEl.style.maxHeight = '200px';
  dropdownEl.style.overflowY = 'auto';
}
```

**Alternative simpler fix:** If the clipping is caused by `.object-form-section { overflow-y: auto }`, change it to `overflow-y: visible` on the direct parent of `.reference-field`, or increase the `z-index` on `.suggestions-dropdown` above any stacking context. Test first -- the simpler CSS fix may be sufficient.

### Anti-Patterns to Avoid

- **Re-initializing Split.js on every htmx:afterSwap without destroying the old instance:** This creates duplicate gutters and event listeners. Always destroy before re-creating.
- **Relying on `setInterval` polling to detect editor readiness:** The current code uses `setInterval` with 50ms intervals and 20 retries. Replace with a Promise-based flow that resolves on module load or rejects on timeout.
- **Attaching event listeners inside htmx-swapped `<script>` blocks without cleanup:** Inline scripts in swapped content re-execute on every swap. Move listener attachment to the cleanup-registry pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Element cleanup on DOM swap | Custom MutationObserver tracker | `htmx:beforeCleanupElement` event | htmx fires this BEFORE removal; MutationObserver fires AFTER, when .destroy() may fail |
| Loading skeleton animation | JavaScript-driven animation | Pure CSS `@keyframes` shimmer | Zero JS overhead, works immediately, no flash |
| Dropdown overflow escape | DOM teleportation/portal system | `position: fixed` + `getBoundingClientRect()` | Vanilla JS, no framework needed, 10 lines of code |
| Editor module loading | Custom module loader | Native `import()` dynamic import | Already using ESM; native `import()` returns a Promise natively |

**Key insight:** This phase is about fixing existing code and establishing patterns, not adding features. The temptation is to over-engineer the cleanup system. A simple registry (object mapping IDs to functions) is sufficient. Do not build an event bus, component lifecycle, or framework abstraction.

## Common Pitfalls

### Pitfall 1: htmx:beforeCleanupElement Fires on Root Only

**What goes wrong:** Developers expect the event to fire on every child element being removed. It fires on the root element that htmx is about to remove/replace.
**Why it happens:** htmx fires the event on the element it is cleaning up, then recursively on children. But if you only check `evt.detail.elt`, you miss nested registered elements.
**How to avoid:** In the cleanup handler, query `evt.detail.elt.querySelectorAll('[id]')` and run cleanup for ALL descendants with registered IDs.
**Warning signs:** Editors inside the swapped container leak after cleanup is supposedly implemented.

### Pitfall 2: Split.js Gutter Duplication

**What goes wrong:** Each time an object tab is loaded via htmx swap into `#editor-area`, a new `Split()` call creates a new vertical split with new gutter elements. The old gutters are removed when the DOM is replaced, but the old Split.js instance still holds references.
**Why it happens:** The inline `<script>` in `object_tab.html` calls `initVerticalSplit()` on every load but never destroys the previous instance.
**How to avoid:** Before calling `Split()`, check if a previous split instance exists for this container and call `.destroy()` on it. Register the new instance in the cleanup registry.
**Warning signs:** Multiple horizontal divider bars appearing in the editor area, or drag handles that don't work.

### Pitfall 3: CodeMirror 6.28.2 Chrome EditContext Memory Leak

**What goes wrong:** On Chrome, CodeMirror 6.28.2 creates cyclic event handlers via Chrome's EditContext feature that prevent garbage collection even after `.destroy()` is called.
**Why it happens:** A Chrome browser API bug interacts with CodeMirror's internal event handling. Fixed in `@codemirror/view@6.28.5`.
**How to avoid:** Bump `@codemirror/view` from `6.28.2` to `6.28.5` or later in the ESM import URLs.
**Warning signs:** Chrome DevTools shows increasing "Detached HTMLElement" count after opening/closing tabs.

### Pitfall 4: Editor Container Height Collapse

**What goes wrong:** The CodeMirror editor renders with 0px height or is not editable.
**Why it happens:** Split.js initialization timing -- if Split.js initializes before the editor container has content, it may calculate the editor section height as 0. Also, if `overflow: hidden` is set on a parent without explicit height, the flex layout collapses.
**How to avoid:** Set `min-height: 200px` on `.codemirror-container` in CSS. Initialize CodeMirror BEFORE Split.js (or use `requestAnimationFrame` to defer Split.js by one frame). Verify `.cm-editor { height: 100% }` is applied.
**Warning signs:** Editor container visible in DevTools but has 0px computed height; editor area appears as a thin line.

### Pitfall 5: Views Explorer hx-trigger="click once"

**What goes wrong:** The views explorer section shows "Loading..." forever until the user clicks the section header.
**Why it happens:** The `hx-trigger="click once"` attribute on the section header means the htmx GET request only fires on user click. The section starts as `expanded` CSS class, so the body is visible, but the content never loads.
**How to avoid:** Change `hx-trigger` to `"load"` so the request fires when the element enters the DOM, or programmatically trigger the request from `workspace.js` `init()`.
**Warning signs:** "Loading..." text visible in the Views section until user clicks the header.

### Pitfall 6: Suggestions Dropdown Clipped by overflow: auto

**What goes wrong:** The autocomplete dropdown for reference fields is invisible or cut off.
**Why it happens:** `.object-form-section { overflow-y: auto }` creates a scrollable container. The `.suggestions-dropdown` uses `position: absolute` relative to `.reference-field`, but the absolutely positioned dropdown is clipped by the ancestor's `overflow: auto`.
**How to avoid:** Either (a) use `position: fixed` with JS-calculated coordinates, or (b) move the dropdown outside the overflow container to `document.body` with absolute positioning, or (c) change the suggestions container to render outside the scroll parent.
**Warning signs:** Typing in a reference field shows no dropdown, or shows a thin sliver of the dropdown before it's clipped.

## Code Examples

### Example 1: Registering CodeMirror Cleanup

```javascript
// In editor.js initEditor(), after creating the EditorView:
var view = new EditorView({ /* ... */ });
editors[objectIri] = view;

// Register cleanup so htmx:beforeCleanupElement destroys the editor
if (typeof window.registerCleanup === 'function') {
  window.registerCleanup(containerId, function() {
    if (editors[objectIri]) {
      editors[objectIri].destroy();
      delete editors[objectIri];
    }
  });
}
```

### Example 2: Registering Split.js Cleanup

```javascript
// In object_tab.html inline script, after creating the split:
var splitInstance = Split(['#' + formId, '#' + editorId], {
  sizes: [40, 60],
  minSize: [100, 100],
  gutterSize: 5,
  direction: 'vertical',
  cursor: 'row-resize'
});

// Register cleanup
if (typeof window.registerCleanup === 'function') {
  window.registerCleanup('object-split-' + safeId, function() {
    splitInstance.destroy();
  });
}
```

### Example 3: Registering Cytoscape Cleanup

```javascript
// In graph.js _renderGraph(), after creating the cy instance:
var cy = cytoscape({ container: container, /* ... */ });
window._sempkmGraph = cy;

// Register cleanup
if (typeof window.registerCleanup === 'function' && container.id) {
  window.registerCleanup(container.id, function() {
    if (window._sempkmGraph === cy) {
      window._sempkmGraph = null;
    }
    cy.destroy();
  });
}
```

### Example 4: Views Explorer Eager Loading

```html
<!-- Change hx-trigger from "click once" to "load" -->
<div class="explorer-section-header"
     onclick="this.parentElement.classList.toggle('expanded')"
     hx-get="/browser/views/explorer"
     hx-target="#views-tree"
     hx-trigger="load"
     hx-swap="innerHTML">
```

### Example 5: Bumping CodeMirror Version

```javascript
// In editor.js, update the esm.sh import URLs:
// FROM:
import { EditorView } from "https://esm.sh/@codemirror/view@6.28.2?pin=v135";
import { keymap } from "https://esm.sh/@codemirror/view@6.28.2?pin=v135";

// TO:
import { EditorView } from "https://esm.sh/@codemirror/view@6.35.0?pin=v135";
import { keymap } from "https://esm.sh/@codemirror/view@6.35.0?pin=v135";
```

Note: Use the latest stable 6.x version available at implementation time (6.35.0+ as of Feb 2026). The critical fix is in 6.28.5 but there is no reason not to use the latest.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual setInterval polling for editor readiness | Promise-based dynamic `import()` with timeout | Always available in ESM | Cleaner flow, proper error handling |
| No htmx cleanup handling | `htmx:beforeCleanupElement` event | htmx 1.9+ (stable in 2.0) | Essential for SPA-like htmx apps with third-party libraries |
| CodeMirror 6.28.2 (Chrome leak) | CodeMirror 6.28.5+ (fixed) | Late 2024 | Eliminates Chrome-specific memory leak |
| `position: absolute` dropdowns | `position: fixed` with getBoundingClientRect | Evergreen pattern | Escapes overflow clipping from any ancestor |

**Deprecated/outdated:**
- The current `setInterval`-based polling in `object_tab.html` (tries variable with 50ms interval) should be replaced with a Promise-based approach
- In htmx 4.0, `htmx:beforeCleanupElement` will be renamed to `htmx:before:cleanup` (not a concern for htmx 2.0.4)

## Open Questions

1. **Exact latest CodeMirror @codemirror/view version**
   - What we know: 6.28.5+ fixes the Chrome EditContext leak; the project uses 6.28.2 via esm.sh
   - What's unclear: The exact latest stable version number (esm.sh may have a slightly different latest)
   - Recommendation: Check esm.sh at implementation time; use latest 6.x (likely 6.35+)

2. **Whether `position: fixed` dropdown is needed or CSS-only fix suffices**
   - What we know: `.object-form-section` has `overflow-y: auto` which clips absolutely positioned children. The dropdown uses `position: absolute` with `z-index: 100`.
   - What's unclear: Whether simply changing `.object-form-section` to `overflow: visible` (and letting the parent handle scrolling) would fix the issue without the complexity of `position: fixed`.
   - Recommendation: Try the CSS-only fix first (change overflow or increase z-index). If clipping persists, implement `position: fixed` approach.

3. **Editor Group Data Model Design (Plan 10-03)**
   - What we know: STATE.md says "Phase 10 plan 10-03 designs the model, Phase 14 implements." Split.js has no dynamic pane API -- you cannot add/remove panes after initialization.
   - What's unclear: The exact shape of the data model. It needs to support 1-4 groups, each with independent tab lists, and map to Split.js recreation.
   - Recommendation: Design a `WorkspaceLayout` class with `groups: [{id, tabs, activeTab, size}]` that can serialize/restore from sessionStorage and drive Split.js destruction/recreation when groups change. This is design-only in Phase 10 -- no implementation.

## Sources

### Primary (HIGH confidence)
- [htmx Events Reference](https://htmx.org/events/) - `htmx:beforeCleanupElement` event documentation
- [Split.js README (GitHub)](https://github.com/nathancahill/split/blob/master/packages/splitjs/README.md) - `.destroy()` method, `getSizes()`, `setSizes()` API
- [CodeMirror 6 Memory Leak Discussion](https://discuss.codemirror.net/t/codemirror-v6-0-1-leaks/8451) - Chrome EditContext fix in 6.28.5
- [Cytoscape.js Documentation](https://js.cytoscape.org/) - `cy.destroy()` method

### Secondary (MEDIUM confidence)
- [htmx GitHub Discussion #1823](https://github.com/bigskysoftware/htmx/discussions/1823) - Cleanup function patterns, confirmed recursive behavior
- [htmx GitHub Issue #3046](https://github.com/bigskysoftware/htmx/issues/3046) - `beforeCleanupElement` behavior details
- [CodeMirror Forum: EditorView destroy](https://discuss.codemirror.net/t/how-to-clear-editor-instance-when-it-is-not-in-dom/8363) - Proper destroy pattern

### Tertiary (LOW confidence)
- CSS overflow/dropdown clipping patterns: derived from multiple Stack Overflow and GitHub issues; pattern is well-established but exact interaction with this project's CSS hierarchy needs testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project; version bump is well-documented fix
- Architecture: HIGH - `htmx:beforeCleanupElement` is the official htmx pattern; cleanup registry is simple JS
- Pitfalls: HIGH - All pitfalls identified from reading actual project source code and matching to known issues
- Code examples: HIGH - Derived from official docs and adapted to actual project code patterns

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable libraries, no expected breaking changes)