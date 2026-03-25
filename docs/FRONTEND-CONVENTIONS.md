# SemPKM Frontend Conventions

Developer-facing reference for the frontend architecture, patterns, and conventions.

All frontend code lives in `frontend/static/` (JS, CSS, images) and `backend/app/templates/` (Jinja2 HTML). There is no build step — files are served directly by nginx.

---

## htmx Patterns

htmx drives all server-rendered DOM updates. The app does **not** use a frontend framework — htmx + Jinja2 partials handle the request/response cycle.

### Swap Modes

| Mode | When to use | Example |
|------|-------------|---------|
| `innerHTML` (default, ~170 uses) | Replace the contents of the target element | Explorer sections, settings panels, form results |
| `outerHTML` (~20 uses) | Replace the entire target element, including itself | Pagination controls, inline edit forms that replace themselves |
| `none` (~10 uses) | Side-effect only — don't touch the DOM | Delete actions, toggling state where a custom event refreshes the UI |
| `beforeend` (rare) | Append content to the end of the target | Infinite scroll / "load more" patterns |

**Default:** Most elements use `innerHTML`. Only specify `hx-swap` when you need a different mode.

### Trigger Patterns

| Pattern | Usage |
|---------|-------|
| `hx-trigger="load"` | Lazy-load content when the element enters the DOM (explorer sections, panel fragments) |
| `hx-trigger="change"` | React to select/input changes (dropdowns, filters) |
| `hx-trigger="click once"` | One-shot click actions (delete confirmations, one-time fetches) |
| `hx-trigger="input changed delay:300ms"` | Debounced search/filter input fields |
| `hx-trigger="intersect once"` | Lazy-load when the element scrolls into view |
| `hx-trigger="revealed"` | Similar to intersect — fires when element becomes visible |
| Custom events: `hx-trigger="queriesRefreshed from:body"` | Re-fetch when another component dispatches a custom event on `document.body` |
| Compound: `hx-trigger="load, favoritesRefreshed from:body"` | Load initially AND refresh when a custom event fires |

### hx-boost

`hx-boost="true"` is set on the `<body>` in the base layout, enabling progressive enhancement for all anchor tags and forms. Links that must do a full page navigation (e.g., external URLs, download links, auth pages) use `hx-boost="false"` to opt out.

### htmx Events in JavaScript

The following htmx lifecycle events are used in JS code:

| Event | Purpose | Files |
|-------|---------|-------|
| `htmx:afterSwap` | Re-initialize JS components after htmx swaps new content into the DOM (e.g., re-run Lucide icon replacement, rebind event handlers) | workspace.js, sidebar.js |
| `htmx:afterSettle` | Run logic after htmx has fully settled the DOM (later than afterSwap — use when you need final layout dimensions) | workspace.js |
| `htmx:configRequest` | Modify outgoing htmx requests (e.g., inject headers, adjust URLs) | workspace.js |
| `htmx:responseError` | Handle server errors from htmx requests (e.g., show toast on 500) | workspace.js |
| `htmx:pushedIntoHistory` | React to htmx URL pushes (e.g., update active sidebar state) | sidebar.js |
| `htmx:beforeCleanupElement` | Run teardown functions before htmx removes a DOM element (see [Event Cleanup](#event-cleanup)) | cleanup.js |

### Partial Rendering with jinja2-fragments

Server endpoints detect htmx requests via the `HX-Request` header and return only the requested block instead of the full page:

```python
block_name = "content" if is_htmx else None
return templates.TemplateResponse(request, "page.html", context, block_name=block_name)
```

This means a single Jinja2 template serves both full-page loads (initial navigation) and partial updates (htmx swaps). The `block_name` parameter tells jinja2-fragments to render only the named `{% block %}`.

---

## JavaScript Module Structure

### IIFE Pattern

All page-specific JS files use the Immediately Invoked Function Expression (IIFE) pattern with strict mode:

```javascript
/**
 * Module description
 */
(function () {
  'use strict';

  // Private variables and functions here

  // Export public API to the SemPKM namespace
  window.SemPKM.myFunction = myFunction;
})();
```

24 of 29 JS files follow this pattern. The exceptions are:
- **copilot.js** — lazy-loaded via dynamic `import()`, uses module-level vars
- **editor.js** — CodeMirror integration, script-level scope
- **sparql-console.js** — Yasgui integration, script-level scope
- **auth.js** — standalone auth page, no workspace dependencies
- **app.js** — admin debug page, local functions only

### SemPKM Namespace (D370)

All custom globals live under `window.SemPKM`. The namespace object is initialized in `api-fetch.js`, which loads in `base.html` before all other page-specific scripts:

```javascript
window.SemPKM = window.SemPKM || {};
```

Each file re-asserts this guard before exporting, ensuring load-order independence:

```javascript
window.SemPKM = window.SemPKM || {};
window.SemPKM.myFunction = myFunction;
```

**Rules:**
- Never assign directly to `window.X` — use `window.SemPKM.X`
- Existing concatenated names like `SemPKMSettings`, `SemPKMLayouts`, `SemPKMCanvas` are left as-is (already namespaced by convention)
- Internal names keep `_sempkm` prefixes under the namespace for mechanical safety (e.g., `window.SemPKM._sempkmCleanup`)
- Cross-IIFE guard flags use `window` directly when two IIFEs need to share a boolean (e.g., `window._switchingPersona`)

---

## CSS Theme System

All theming is in `frontend/static/css/theme.css`. See decision D371 for rationale.

### Two-Tier Token Architecture

1. **Primitive tokens** (`--_color-*`, `--_spacing-*`, `--_font-size-*`) — raw values, defined once in `:root`, never overridden between themes
2. **Semantic tokens** (`--color-*`, `--spacing-*`, `--font-size-*`) — reference primitives or define role-based values, overridden in dark mode

```css
:root {
  /* Primitive — never changes */
  --_color-green-500: #59a14f;
  /* Semantic — overridden in dark mode */
  --color-success: #2a8a4a;
}

html[data-theme="dark"] {
  --color-success: #98c379;
}
```

### Color Rules

- **All colors** must use `var(--color-*)` or `var(--_color-*)` tokens — no standalone hex, rgb, or rgba values in CSS files outside `theme.css`
- **Transparent variants** use `color-mix()`:
  ```css
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
  ```
- CSS named colors (`gold`, `silver`) are permitted only in `decision-matrix.css` rank badges

### Breakpoints

Two breakpoints — no others:

| Breakpoint | Value | Usage |
|------------|-------|-------|
| Mobile | `600px` | `@media (max-width: 600px)` |
| Tablet | `768px` | `@media (max-width: 768px)` |

### Dark Mode

Dark mode is toggled by setting `data-theme="dark"` on the `<html>` element. CSS overrides use:

```css
html[data-theme="dark"] {
  --color-bg: #1e2127;
  --color-surface: #282c34;
  /* ... semantic token overrides ... */
}
```

The theme toggle lives in the user popover. `theme.js` handles persistence via `localStorage` and applies the `data-theme` attribute on load (with a `no-transition` class to prevent flash).

### Crossfade Transitions

Theme changes animate via 150ms transitions on `background-color`, `color`, and `border-color`. These are applied to specific layout elements (body, sidebar, panels, tabs) — **not** universally via `*`.

---

## Debug Logging

### SemPKM.debug()

Development-only logging gated by a localStorage flag. Silent in production by default.

```javascript
// In any JS file:
SemPKM.debug('copilot', 'streaming response', { chunks: 42 });
SemPKM.debug('calendar', 'event clicked', eventId);
```

**Enable:**
```javascript
localStorage.setItem('sempkm_debug', '1');
```

**Disable:**
```javascript
localStorage.removeItem('sempkm_debug');
```

When enabled, outputs `[tag] ...args` to `console.log`. When disabled, it's a no-op — zero cost.

### Implementation

Defined in `api-fetch.js` on `window.SemPKM.debug`:

```javascript
window.SemPKM.debug = function debug(tag, ...args) {
  try {
    if (localStorage.getItem('sempkm_debug')) {
      console.log('[' + tag + ']', ...args);
    }
  } catch (_) {
    // localStorage unavailable (private browsing, iframe sandbox)
  }
};
```

### Logging Severity Guide

| Level | Function | When to use | Gated? |
|-------|----------|-------------|--------|
| Debug | `SemPKM.debug(tag, ...)` | Development tracing, state inspection, flow logging | Yes — localStorage flag |
| Warning | `console.warn(...)` | Recoverable issues, deprecation notices, unexpected-but-handled states | No — always emits |
| Error | `console.error(...)` | Failures, caught exceptions, unrecoverable states | No — always emits |

**Rule:** Never use `console.log()` directly. Use `SemPKM.debug()` for development tracing, or `console.warn`/`console.error` for operational signals that should always be visible.

---

## Fetch Conventions

### SemPKM.apiFetch() (D369)

All HTTP calls go through `SemPKM.apiFetch()` — never use raw `fetch()`.

```javascript
// Basic GET
var resp = await SemPKM.apiFetch('/api/objects');
var data = await resp.json();

// POST with JSON body
var resp = await SemPKM.apiFetch('/api/objects', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});

// Silent mode — suppress toasts, handle errors locally
try {
  var resp = await SemPKM.apiFetch('/api/check', { silent: true });
} catch (err) {
  // err.status, err.body, err.response available
  showMyCustomError(err.body);
}
```

### Behavior

| Scenario | apiFetch behavior |
|----------|-------------------|
| Success (2xx) | Returns the raw `Response` object |
| Network error | Toasts "Network error", rethrows the error |
| 401 Unauthorized | Redirects to `/login.html` (unless already on an auth page) |
| 403 Forbidden | Toasts "Access denied", throws `{ status: 403, body, response }` |
| 5xx Server Error | Toasts "Server error (NNN)", throws `{ status, body, response }` |
| Other non-2xx | Toasts "Request failed (NNN)", throws `{ status, body, response }` |
| AbortError | Silently returns `undefined` (no toast, no throw) |
| `{ silent: true }` | All toasts suppressed — caller handles UX |

### One Exemption

`auth.js` uses raw `fetch()` for `/api/auth/me` because `apiFetch`'s 401 redirect loses the `?next=` query parameter needed for return-URL preservation.

---

## Event Cleanup

### The Problem

htmx swaps replace DOM subtrees, but JavaScript library instances (Cytoscape graphs, Chart.js charts, CodeMirror editors, dockview panels) hold references and event listeners that must be torn down explicitly.

### registerCleanup / runCleanup

Defined in `cleanup.js`, available as `SemPKM.registerCleanup()` and `SemPKM.runCleanup()`:

```javascript
// When creating a library instance, register its teardown:
var chart = new Chart(canvas, config);
SemPKM.registerCleanup('my-chart-container', function () {
  chart.destroy();
});

// Multiple cleanup functions can be registered per element ID.
// They run in registration order.
```

### Automatic Cleanup via htmx

`cleanup.js` listens for `htmx:beforeCleanupElement` and automatically calls `runCleanup()` on:
1. The root element being removed (if it has an `id`)
2. All descendant elements with `id` attributes

This means cleanup functions fire automatically when htmx replaces content — no manual teardown needed in most cases.

### Manual Cleanup

For non-htmx DOM removal (e.g., dockview panel close), call `runCleanup()` directly:

```javascript
SemPKM.runCleanup('my-panel-id');
```

### Dockview Panel Lifecycle

Dockview panels register cleanup in their `init()` or render function. When the panel is closed or the tab is removed, the panel's `dispose()` callback calls `SemPKM.runCleanup(containerId)` to tear down any library instances inside.

---

## Lucide Icons

Lucide replaces `<i data-lucide="icon-name">` placeholder elements with inline `<svg>` elements at runtime.

### Sizing Rule

Always size Lucide icons via CSS — never with inline `style` attributes:

```css
/* Correct — CSS rule with flex protection */
.my-btn svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke: currentColor;
}
```

```html
<!-- Correct -->
<button class="my-btn"><i data-lucide="x"></i></button>

<!-- Wrong — inline style gets overridden by flex layout -->
<button class="my-btn"><i data-lucide="x" style="width:14px;height:14px;"></i></button>
```

**Why:** SVG elements are flex items inside flex containers. Without `flex-shrink: 0`, the browser can compress their width to 0px — making the icon invisible even with an explicit inline size.

### Stroke Inheritance

Lucide SVGs use `stroke` (not `fill`). Set `stroke: currentColor` on the SVG or its container to inherit the parent's `color`:

```css
.my-btn { color: var(--color-text-muted); }
.my-btn svg { stroke: currentColor; }
```

### Re-initialization After htmx Swap

After htmx swaps new content containing `<i data-lucide="...">` placeholders, call `lucide.createIcons()` in an `htmx:afterSwap` handler to replace them with SVGs.

---

## File Serving

nginx serves static assets directly. The Docker volume mount maps `frontend/static/` → `/usr/share/nginx/html/`.

| File location | Served at | Notes |
|--------------|-----------|-------|
| `frontend/static/js/foo.js` | `/js/foo.js` | **Not** `/static/js/foo.js` |
| `frontend/static/css/bar.css` | `/css/bar.css` | **Not** `/static/css/bar.css` |

There is no `/static/` prefix in URLs. Template references must use `/js/` and `/css/` paths directly.
