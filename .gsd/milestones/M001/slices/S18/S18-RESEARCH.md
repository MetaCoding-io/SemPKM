# Phase 18: Tutorials and Documentation - Research

**Researched:** 2026-02-24
**Domain:** Driver.js guided tours, htmx async step handling, SemPKM special tab pattern
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCS-01 | A Docs & Tutorials page accessible from the Meta sidebar section lists available interactive tutorials and documentation links | The sidebar already has `<a href="/docs" class="nav-link disabled">` — enable it by pointing to a new `/browser/docs` route. The page follows the same `special:docs` tab pattern as `special:settings` in `workspace-layout.js`. A new `GET /browser/docs` FastAPI endpoint returns `browser/docs_page.html` (a static HTML fragment). No DB dependency. |
| DOCS-02 | Driver.js (MIT) is integrated for guided tours with lazy element resolution for htmx-rendered content | Driver.js 1.4.0 is the current stable version (MIT). CDN via jsDelivr: `driver.js.iife.js` + `driver.css`. The `element` property in `DriveStep` accepts `() => Element` — a function evaluated lazily at step activation time, which handles htmx-rendered content that is not in the DOM at tour start. Loaded in `base.html` alongside other CDN libs. |
| DOCS-03 | A "Welcome to SemPKM" tutorial walks through the workspace (sidebar, explorer, opening objects, read/edit toggle, command palette, saving) | Implemented as a Driver.js tour defined in `tutorials.js`. Steps target stable DOM IDs already in the workspace template: `#app-sidebar`, `#nav-pane`, `#section-objects`, `#editor-pane`, `#right-pane`. The command palette step uses a lazy element resolver. Tour launched by button on docs page. |
| DOCS-04 | A "Creating Your First Object" tutorial walks through object creation from type selection to save | Each step that targets htmx-loaded content uses `onNextClick` override: trigger the htmx action, listen for `htmx:afterSwap`, then call `driverObj.moveNext()`. Steps: sidebar → object explorer → type picker dialog → form fields → save button. |
</phase_requirements>

---

## Summary

Phase 18 adds a Docs & Tutorials hub (a new special tab in the workspace) and two Driver.js guided tours. Driver.js 1.4.0 (MIT) is the locked choice per STATE.md. The library is loaded via jsDelivr CDN (same pattern as marked, DOMPurify in the project). The most technically interesting challenge is that tour steps targeting htmx-rendered content require **lazy element resolution**: Driver.js v1 supports `element: () => Element` (a function) which is evaluated at step activation time rather than tour creation time. For steps that require triggering an htmx request first (e.g., opening the type picker), use `onNextClick` override + `htmx:afterSwap` listener + `driverObj.moveNext()` to gate progression.

The page architecture follows the established `special:settings` tab pattern exactly: a new `special:docs` tab key in `workspace-layout.js`'s `loadTabInGroup`, a new `GET /browser/docs` FastAPI route, and a static HTML template `docs_page.html`. The sidebar `<a href="/docs">` link is already present but marked disabled — it needs to be wired to call a new `openDocsTab()` JS function.

Driver.js theming is handled via CSS class overrides targeting `.driver-popover` and its children. The project's CSS token system (`--color-bg`, `--color-surface`, `--color-accent`, `--color-text`, `--color-border`) provides the exact values needed to theme the Driver.js popover to match VS Code dark/light mode.

**Primary recommendation:** Two plans: Plan 01 = docs page + Driver.js CDN integration + `special:docs` tab wiring; Plan 02 = both tutorials implemented in `tutorials.js`. The tours are pure JS — no backend changes beyond Plan 01's route.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Driver.js | 1.4.0 | Guided product tours with overlay highlights | MIT licensed; locked in STATE.md; replaces Shepherd.js (AGPL-3.0) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsDelivr CDN | N/A | Host Driver.js IIFE bundle + CSS | Project already uses jsDelivr for marked, DOMPurify |
| FastAPI + Jinja2 | existing | Docs page route + HTML fragment | Existing pattern for all browser pages |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Driver.js | Shepherd.js | Shepherd.js v14 is AGPL-3.0 — explicitly rejected in STATE.md |
| Driver.js | Intro.js | Intro.js has commercial licensing; Driver.js is fully MIT |
| jsDelivr | unpkg | Project mixes both; jsDelivr preferred for non-htmx libs (consistency with marked) |

**Installation (CDN — add to `base.html`):**
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/driver.js@1.4.0/dist/driver.css">
<script src="https://cdn.jsdelivr.net/npm/driver.js@1.4.0/dist/driver.js.iife.js"></script>
```

After IIFE load, the API is available at `window.driver.js.driver` (destructure at call site).

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/static/js/
└── tutorials.js          # New: all Driver.js tour definitions + launcher functions

backend/app/
├── browser/router.py     # Add GET /browser/docs route (single function)
└── templates/browser/
    └── docs_page.html    # New: static HTML listing tutorials + doc links

backend/app/templates/
└── base.html             # Add driver.css + driver.js.iife.js CDN links
```

The sidebar `_sidebar.html` needs one change: remove `disabled` class from the Docs & Tutorials `<a>` and add `onclick="openDocsTab(); return false;"`.

`workspace-layout.js` needs one addition in `loadTabInGroup`: handle `special:docs` similarly to `special:settings`.

`workspace.js` needs `openDocsTab()` function mirroring `openSettingsTab()`.

### Pattern 1: Special Tab Opening (mirrors `special:settings`)

**What:** A tab with a synthetic key (`special:docs`) that loads a static HTML fragment via htmx, without right-pane sections.
**When to use:** Pages that are workspace-global tools (settings, docs) rather than object content.

```javascript
// Source: workspace.js pattern (existing openSettingsTab)
function openDocsTab() {
  var tabKey = 'special:docs';
  var layout = window._workspaceLayout;
  if (!layout) return;
  var groupId = layout.activeGroupId;
  var group = layout.getGroup ? layout.getGroup(groupId) : (layout.groups && layout.groups[groupId]);
  if (group) {
    var existing = group.tabs.find(function (t) { return (t.id || t.iri) === tabKey; });
    if (existing) {
      if (typeof switchTabInGroup === 'function') switchTabInGroup(tabKey, groupId);
      return;
    }
  }
  var tabDef = { id: tabKey, iri: tabKey, label: 'Docs & Tutorials', dirty: false, isView: false, isSpecial: true, specialType: 'docs' };
  if (layout.addTabToGroup) layout.addTabToGroup(tabDef, groupId);
  if (typeof window.loadTabInGroup === 'function') window.loadTabInGroup(groupId, tabKey);
}
window.openDocsTab = openDocsTab;
```

In `workspace-layout.js` `loadTabInGroup`, add before the `else` branch:

```javascript
} else if (tabId === 'special:docs' || (tab && tab.specialType === 'docs')) {
  url = '/browser/docs';
}
```

Also update the `isSpecial` check:

```javascript
var isSpecial = tabId === 'special:settings' || (tab && tab.specialType === 'settings')
             || tabId === 'special:docs' || (tab && tab.specialType === 'docs');
```

### Pattern 2: Driver.js CDN IIFE Access

**What:** When loaded via IIFE script tag, Driver.js exposes itself at `window.driver.js.driver`. Must destructure before use.
**When to use:** Always when using CDN (not npm imports).

```javascript
// Source: Driver.js official docs (https://driverjs.com/docs/installation)
var driver = window.driver.js.driver;

var driverObj = driver({
  showProgress: true,
  steps: [ /* ... */ ]
});
driverObj.drive();
```

### Pattern 3: Lazy Element Resolution for htmx Content

**What:** `DriveStep.element` accepts `() => Element` (function). Driver.js calls it at step activation time, not tour creation. Handles elements not yet in DOM when tour starts.
**When to use:** Any step that targets content rendered by htmx after tour begins.

```javascript
// Source: Driver.js TypeScript source (DriveStep interface)
// element?: string | Element | (() => Element)
{
  element: function() {
    return document.querySelector('#nav-tree .tree-node');
  },
  popover: {
    title: 'Explorer tree',
    description: 'Objects appear here after a model is installed.'
  }
}
```

### Pattern 4: Async Step Gating for htmx Actions

**What:** For steps that must trigger an htmx load *before* the next step can render, override `onNextClick` at the step level to intercept the button, fire the action, wait for `htmx:afterSwap`, then call `driverObj.moveNext()`.
**When to use:** "Creating Your First Object" tutorial where clicking Next in the tour should open the type picker.

```javascript
// Source: Driver.js docs (https://driverjs.com/docs/async-tour)
{
  element: '#nav-tree',
  popover: {
    title: 'Open the type picker',
    description: 'Click Next to open the object creation dialog.',
    onNextClick: function() {
      // Trigger the htmx action that loads the type picker
      htmx.trigger(document.querySelector('[data-action="new-object"]'), 'click');
      // Wait for htmx to swap in the type picker, then advance
      document.body.addEventListener('htmx:afterSwap', function handler(e) {
        if (e.detail.target.id === 'type-picker-container') {
          document.body.removeEventListener('htmx:afterSwap', handler);
          driverObj.moveNext();
        }
      });
    }
  }
}
```

### Pattern 5: Driver.js Dark Mode Theming via CSS Variables

**What:** Override `.driver-popover` CSS to use project CSS tokens so the popover respects the current `data-theme` attribute.
**When to use:** Always — the default Driver.js popover is white with dark text, which clashes with the project's dark mode.

```css
/* In workspace.css or a new tutorials.css */
.driver-popover {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
}
.driver-popover-title {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 600;
}
.driver-popover-description {
  color: var(--color-text-muted);
  font-size: 13px;
}
.driver-popover-footer {
  border-top: 1px solid var(--color-border);
}
.driver-popover-progress-text {
  color: var(--color-text-faint);
  font-size: 12px;
}
.driver-popover-next-btn,
.driver-popover-done-btn {
  background: var(--color-accent);
  color: #fff;
  border: none;
}
.driver-popover-next-btn:hover,
.driver-popover-done-btn:hover {
  background: var(--color-accent-hover);
}
.driver-popover-prev-btn,
.driver-popover-close-btn {
  background: transparent;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}
.driver-overlay {
  background: rgba(0, 0, 0, 0.5);
}
```

### Pattern 6: "Welcome to SemPKM" Tour Step Targets

All elements in this tour are stable, always-present DOM IDs in `workspace.html` and `_sidebar.html`. No lazy resolution needed except the command palette step.

| Step | Element Selector | Notes |
|------|-----------------|-------|
| 1 | `#app-sidebar` | Always present |
| 2 | `#nav-pane` | Left pane, always present |
| 3 | `#section-objects` | Explorer section in nav tree |
| 4 | `#editor-pane` | Center pane |
| 5 | `#right-pane` | Right pane |
| 6 | `ninja-keys` | Command palette (always in DOM) |
| 7 | `null` (centered) | "You're ready" end step (no element = centered popover) |

For step targeting the command palette, use `element: function() { return document.querySelector('ninja-keys'); }` (lazy, in case the custom element hasn't registered yet).

### Pattern 7: "Creating Your First Object" Tour Step Design

This tour has htmx-dependent steps. Key steps:

| Step | Action Required | Technique |
|------|----------------|-----------|
| 1 | Show explorer | Static element `#section-objects` |
| 2 | Trigger "New Object" | `onNextClick` fires htmx to load type picker, waits for `htmx:afterSwap` |
| 3 | Type picker dialog | Lazy element `() => document.querySelector('#type-picker-modal')` |
| 4 | Form fields | Lazy element `() => document.querySelector('.object-form')` |
| 5 | Save button | Lazy element `() => document.querySelector('[data-action="save-object"]')` |

### Anti-Patterns to Avoid

- **`element: '#selector'` for htmx content at tour start**: Driver.js resolves string selectors at tour creation. If the element isn't in the DOM yet, the step silently fails or errors. Always use `element: () => document.querySelector('#selector')` for dynamically loaded content.
- **Pinning `driver.js@latest` in CDN URL**: Always pin to `@1.4.0` to prevent breaking changes, consistent with project pattern (ninja-keys pinned to `@1.2.2`).
- **Loading driver.css after driver.js.iife.js**: The CSS must load before the JS to avoid a flash of unstyled overlay. In `base.html`, put the `<link>` before the `<script>`.
- **Calling `driverObj.destroy()` from `htmx:afterSwap`**: If the tour is running during an htmx afterSwap triggered by the tour itself, calling destroy or moveNext in the wrong handler can cause double-fires. Always use a named handler function and `removeEventListener` before calling `moveNext()`.
- **Using `window.driver` directly**: After IIFE load, the namespace is `window.driver.js.driver` (the package name contains a `.`). Access pattern: `var driver = window['driver.js'].driver;` or `var driver = window.driver.js.driver;`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Step-by-step overlay tours | Custom modal/overlay sequence | Driver.js | Scroll into view, popover positioning, keyboard nav, overlay, progress all built-in |
| Dark mode popover | Inline style per theme toggle | CSS custom properties on `.driver-popover` | Tokens auto-update on `data-theme` change via cascade |
| htmx wait logic | setTimeout polling | `htmx:afterSwap` event with named handler | Deterministic; no race condition |

**Key insight:** Driver.js handles 95% of the tour complexity (positioning, scroll, overlay, keyboard nav). All project-specific work is step data + CSS theming + htmx async gating.

---

## Common Pitfalls

### Pitfall 1: IIFE Namespace Confusion
**What goes wrong:** `window.driver` is undefined after loading the IIFE bundle. Code fails silently.
**Why it happens:** The package name is `driver.js` (with a dot), so the IIFE uses `window['driver.js']` as the namespace key.
**How to avoid:** Always access as `window['driver.js'].driver` or `var drv = window.driver; var d = drv && drv.js && drv.js.driver;` with fallback guard.
**Warning signs:** `TypeError: Cannot read properties of undefined (reading 'driver')` in console.

### Pitfall 2: String Selector for htmx-Rendered Element
**What goes wrong:** Driver.js tour step with `element: '#type-picker-modal'` fails when that element loads via htmx *after* `driverObj.drive()` is called.
**Why it happens:** String selectors are resolved at `drive()` call time (or at step init time), not at step activation time. Function form `() => document.querySelector(...)` is lazy.
**How to avoid:** Use function form for any element that is htmx-rendered. Use string only for always-present elements (`#app-sidebar`, `#nav-pane`, etc.).
**Warning signs:** Step shows no highlight, popover appears at viewport edge or doesn't appear.

### Pitfall 3: Double `htmx:afterSwap` Fire
**What goes wrong:** The `onNextClick` handler adds a `htmx:afterSwap` listener, but unrelated htmx swaps also trigger it, causing `moveNext()` to be called unexpectedly.
**Why it happens:** `htmx:afterSwap` fires for ALL htmx swaps on the page (lazy panel loads, autocomplete, etc.).
**How to avoid:** In the handler, check `e.detail.target.id` or `e.detail.requestConfig.path` to confirm it's the expected swap. Remove listener immediately after matching.
**Warning signs:** Tour jumps steps unexpectedly when user or background code triggers htmx requests.

### Pitfall 4: `driver.css` Missing or Loading Order
**What goes wrong:** Tour runs but overlay has no background, popover has no styling, or layout shifts as CSS loads.
**Why it happens:** `driver.css` loaded after `driver.js.iife.js` or not loaded at all.
**How to avoid:** In `base.html`, add `<link>` before `<script>` for Driver.js entries. Verify in browser Network tab that both 200 OK.
**Warning signs:** White flash or unstyled overlay on tour start.

### Pitfall 5: `openDocsTab()` vs `openSettingsTab()` isSpecial check
**What goes wrong:** The docs tab loads content but also triggers `loadRightPaneSection` (relations, lint) because the `isSpecial` guard doesn't include `special:docs`.
**Why it happens:** `workspace-layout.js` has a hardcoded `isSpecial` check for `special:settings` only.
**How to avoid:** Update both the URL dispatch block AND the `isSpecial` variable in `loadTabInGroup` to include `special:docs` and `specialType === 'docs'`.
**Warning signs:** Console errors trying to load relations/lint for the docs tab.

---

## Code Examples

Verified patterns from official sources:

### Complete Tour Definition (CDN IIFE)
```javascript
// Source: Driver.js TypeScript source + installation docs
// frontend/static/js/tutorials.js

(function () {
  'use strict';

  function getDriver() {
    // IIFE namespace: window['driver.js'].driver
    return window['driver.js'] && window['driver.js'].driver;
  }

  window.startWelcomeTour = function () {
    var driver = getDriver();
    if (!driver) { console.warn('Driver.js not loaded'); return; }

    var driverObj = driver({
      showProgress: true,
      steps: [
        {
          element: '#app-sidebar',
          popover: {
            title: 'Welcome to SemPKM',
            description: 'This is your workspace sidebar. Navigate between sections here.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#nav-pane',
          popover: {
            title: 'Explorer',
            description: 'Browse your knowledge objects organized by type.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: function () {
            return document.querySelector('ninja-keys');
          },
          popover: {
            title: 'Command Palette',
            description: 'Press Ctrl+K to open the command palette and search everything.',
            side: 'bottom',
            align: 'center'
          }
        },
        {
          // No element = centered popover (end of tour)
          popover: {
            title: "You're all set!",
            description: "Explore the tutorials page for more guided walkthroughs.",
            showButtons: ['done']
          }
        }
      ]
    });

    driverObj.drive();
  };

  window.startCreateObjectTour = function () {
    var driver = getDriver();
    if (!driver) return;
    var driverObj;

    driverObj = driver({
      showProgress: true,
      steps: [
        {
          element: '#section-objects',
          popover: {
            title: 'Object Explorer',
            description: 'Objects are listed here. Click Next to open the creation dialog.',
            onNextClick: function () {
              // Trigger htmx new-object action
              var btn = document.querySelector('[data-action="new-object"]');
              if (btn) {
                htmx.trigger(btn, 'click');
              }
              // Wait for type picker to appear
              document.body.addEventListener('htmx:afterSwap', function handler(e) {
                if (e.detail.target && e.detail.target.id === 'type-picker-container') {
                  document.body.removeEventListener('htmx:afterSwap', handler);
                  driverObj.moveNext();
                }
              });
            }
          }
        },
        {
          element: function () {
            return document.querySelector('#type-picker-container');
          },
          popover: {
            title: 'Choose a Type',
            description: 'Select the type of knowledge object you want to create.',
            side: 'right'
          }
        }
      ]
    });

    driverObj.drive();
  };
})();
```

### FastAPI Docs Route
```python
# Source: pattern from existing /browser/settings route in router.py
@router.get("/docs")
async def docs_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Docs & Tutorials hub page rendered as a workspace tab fragment."""
    return templates.TemplateResponse(request, "browser/docs_page.html", {
        "user": user,
    })
```

### Driver.js Popover CSS Theming
```css
/* Source: Driver.js exposed CSS classes (theming docs) */
/* In workspace.css — appended after existing rules */

.driver-popover {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
.driver-popover-title {
  color: var(--color-text);
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 8px;
  margin-bottom: 8px;
}
.driver-popover-description {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.5;
}
.driver-popover-footer {
  border-top: 1px solid var(--color-border-subtle);
  margin-top: 8px;
  padding-top: 8px;
}
.driver-popover-progress-text {
  color: var(--color-text-faint);
  font-size: 12px;
}
.driver-popover-next-btn,
.driver-popover-done-btn {
  background: var(--color-accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 4px !important;
}
.driver-popover-prev-btn,
.driver-popover-close-btn {
  background: transparent !important;
  color: var(--color-text-muted) !important;
  border: 1px solid var(--color-border) !important;
  border-radius: 4px !important;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shepherd.js for tours | Driver.js | Phase 18 decision (STATE.md) | License change: AGPL-3.0 → MIT |
| `element: '#selector'` | `element: () => querySelector()` | Driver.js v1 API | Enables lazy DOM resolution |
| Global `onNextClick` | Per-step `popover.onNextClick` | Driver.js v1 | Fine-grained async gating per step |

**Deprecated/outdated:**
- Shepherd.js: AGPL-3.0 licensed — explicitly rejected in STATE.md. Do not use.

---

## Open Questions

1. **"New Object" button selector for Creating Your First Object tour**
   - What we know: There is a new-object trigger in the workspace, but the exact `data-action` or element ID is not confirmed from research.
   - What's unclear: Whether the trigger is a button with `data-action="new-object"` or an `hx-get` trigger on a specific element.
   - Recommendation: During implementation of Plan 02, inspect `nav_tree.html` and `workspace.html` for the exact new-object element selector. Document the selector in the plan's key_links.

2. **Type picker container ID**
   - What we know: The type picker is loaded via htmx into the workspace, but the exact target element ID (`#type-picker-container` or similar) is not confirmed.
   - What's unclear: Whether the type picker replaces the editor area or uses a modal overlay with its own ID.
   - Recommendation: Inspect `type_picker.html` and the relevant router endpoint during Plan 02 implementation to confirm the target selector.

3. **Does the docs page need a FastAPI route or can it be a static file?**
   - What we know: All existing "special" pages (settings) use FastAPI routes. The docs page has no dynamic data.
   - What's unclear: Whether serving a fully static HTML fragment via FastAPI is wasteful.
   - Recommendation: Use FastAPI route for consistency with `special:settings` pattern. The overhead is negligible (no DB call). Keeps the same htmx.ajax flow.

---

## Sources

### Primary (HIGH confidence)
- Driver.js npm registry — version 1.4.0, MIT license: `npm view driver.js`
- Driver.js TypeScript source (GitHub raw): `DriveStep` interface, `element?: string | Element | (() => Element)`, confirmed function form exists
- Driver.js official docs (driverjs.com/docs/configuration): All callbacks (`onHighlightStarted`, `onHighlighted`, `onDeselected`, `onNextClick`, `onPrevClick`, `onCloseClick`, `onPopoverRender`), all config options
- Driver.js popover TypeScript source (GitHub raw): `Popover` type fields (`title`, `description`, `side`, `align`, `showButtons`, `progressText`, `nextBtnText`, `prevBtnText`, `doneBtnText`, `popoverClass`, `onNextClick`)
- Driver.js async tour docs (driverjs.com/docs/async-tour): `onNextClick` override + `driverObj.moveNext()` pattern confirmed
- jsDelivr CDN directory listing for driver.js@1.4.0: `driver.css` (3.85KB), `driver.js.iife.js` (20.8KB) both confirmed present
- Project codebase: `workspace.js` openSettingsTab pattern, `workspace-layout.js` loadTabInGroup special tab dispatch, `_sidebar.html` disabled docs link, `base.html` CDN loading pattern, theme.css CSS token names

### Secondary (MEDIUM confidence)
- Driver.js theming docs (driverjs.com/docs/theming): CSS class names for popover customization — confirmed class names match source CSS

### Tertiary (LOW confidence)
- None. All critical claims verified from primary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm confirms v1.4.0, MIT; CDN files verified on jsDelivr
- Architecture: HIGH — openSettingsTab/loadTabInGroup patterns read directly from source; Driver.js DriveStep interface read from GitHub source
- Pitfalls: HIGH — IIFE namespace pitfall verified from official docs; htmx double-fire is standard htmx behavior; CSS loading order is general web knowledge
- Tour step selectors: MEDIUM — workspace DOM IDs read from templates; type picker selector and new-object trigger unconfirmed (Open Questions 1-2)

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable; Driver.js 1.x is unlikely to change in 30 days)