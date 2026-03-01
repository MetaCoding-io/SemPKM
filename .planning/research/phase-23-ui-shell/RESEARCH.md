## Decision

Use `dockview-core` (the framework-agnostic package of Dockview v4.x) as the panel management library, replacing Split.js incrementally across three migration phases (Phase A: inner editor-pane split; Phase B: full workspace; Phase C: floating panels and named layouts); simultaneously expand `theme.css` from ~40 to ~91 CSS custom property tokens using a two-tier primitive + semantic architecture.

**Rationale:**
- `dockview-core` has zero dependencies and first-class vanilla TypeScript support; content injection via `params.containerElement` (a plain DOM element) is a perfect integration point for htmx's `htmx.ajax()` — matching the existing `loadTabInGroup()` pattern in `workspace-layout.js` exactly
- Dockview's CSS custom property theming (`--dv-*` variables) integrates cleanly with SemPKM's existing `theme.css` token system; `--dv-*` variables can be mapped directly to `--color-*` and `--tab-*` tokens
- Dockview supports drag-and-drop panel reordering, floating panels, popout windows, and named layout serialization (`toJSON()`/`fromJSON()`) — the full feature set required for v2.3 without any framework dependency
- Incremental migration from Split.js bounds risk: Phase A replaces only the inner editor-groups split (managed by `workspace-layout.js`), keeping the sidebar, nav tree, and bottom panel structure unchanged; this validates the htmx integration before committing to full workspace migration
- The two-tier CSS token architecture (primitive `--_*` + semantic `--color-*`, `--tab-*`, `--panel-*`, etc.) formalizes the existing approach, adds coverage for spacing, typography, and new panel surfaces, and stays under 100 tokens — the practical upper bound before developer confusion
- Named dashboard layouts via Dockview `toJSON()`/`fromJSON()` can be stored as user preferences in the RDF triplestore with a localStorage fast-path cache (see Section 3 for the storage design)

**Alternatives ruled out:**
- **GoldenLayout 2** — DOM reparenting in non-Virtual mode breaks htmx event handlers and internal state; the Virtual mode avoids reparenting but requires the application to manually manage `position:absolute` overlays for all component positioning — significant complexity; LESS-based themes (not CSS custom properties) require a translation layer; no floating panels (only popout windows); sporadic maintenance activity
- **Lumino (PhosphorJS)** — requires multiple `@lumino/*` packages; tightly coupled to the Lumino Widget lifecycle model and message-passing system; would require wrapping every htmx partial in a Lumino Widget subclass; Jupyter-centric documentation
- **FlexLayout-React** — requires React as a runtime dependency; SemPKM's architecture is vanilla JS + htmx; adding React is not an option
- **rc-dock** — requires React; eliminated for the same reason as FlexLayout-React
- **Keep Split.js** — Split.js provides only basic two-pane splitting with no tabs, no drag-and-drop, no layout serialization, and no floating panels; the current `workspace-layout.js` implementation is already 1024+ lines managing tabs, groups, and pane state manually; Dockview provides all of this natively

---

# Phase 23: UI Shell Architecture Research

**Researched:** 2026-02-27
**Overall confidence:** MEDIUM-HIGH
**Mode:** Ecosystem + Feasibility

---

## Executive Summary and Recommendation

**Use Dockview (`dockview-core`) over GoldenLayout 2 for flexible panel management.** Dockview is the better fit for SemPKM's vanilla JS + htmx architecture. It offers zero dependencies, first-class vanilla TypeScript support via the standalone `dockview-core` package, a straightforward content injection model (direct `containerElement` access), built-in CSS custom property theming (all `--dv-*` variables), and active maintenance (v4.13+, frequent releases through 2025-2026). GoldenLayout 2 is viable but has a more complex component binding model (three different modes), reparents DOM ancestors when layout changes (breaking htmx handlers), ships LESS-based themes instead of CSS variables, and has slowed maintenance activity.

For theming, extend the existing CSS custom property system in `theme.css` using a two-tier token architecture (primitive + semantic), modeled on the patterns from Open Props and Radix Themes. The current ~40 tokens should expand to ~80-90 tokens to cover new panel management UI surfaces, spacing, and typography scales.

Named dashboard layouts ("Research Mode", "Exploration Mode") are well-supported by Dockview through `toJSON()` / `fromJSON()` serialization, and can be stored as user preferences in the RDF triplestore with a localStorage fast-path cache.

The migration from Split.js should be **incremental**: Phase A replaces the inner editor-pane split (the editor groups area managed by `workspace-layout.js`), Phase B promotes Dockview to manage the entire workspace, and Phase C adds advanced features like floating panels and named layouts.

---

## 1. Panel Layout Library Comparison

### Candidates Evaluated

| Library | Version | Vanilla JS? | Zero Deps? | Tabs | Drag-to-Dock | Serialize | Floating Panels | Popout Windows | Active Maint. |
|---------|---------|------------|-----------|------|-------------|-----------|----------------|----------------|---------------|
| **Dockview (`dockview-core`)** | 4.13+ | YES (first-class) | YES | YES | YES | YES (`toJSON`/`fromJSON`) | YES | YES | YES (frequent) |
| **GoldenLayout 2** | 2.6.x | YES (usable) | YES | YES | YES | YES (`saveLayout`/`loadLayout`) | NO | YES | LOW (sporadic) |
| **Lumino** | 2.x | YES (TypeScript) | NO (multiple `@lumino/*` pkgs) | YES | YES | Partial | NO | NO | MEDIUM (Jupyter-coupled) |
| **FlexLayout-React** | 0.7.x | NO (React required) | NO (React dep) | YES | YES | YES | YES | YES | MEDIUM |
| **rc-dock** | 3.x | NO (React required) | NO (React dep) | YES | YES | YES | YES | NO | LOW |

**Confidence:** MEDIUM -- feature assessment based on documentation and GitHub repositories. Bundle sizes estimated from npm metadata (exact gzipped measurements not retrieved from Bundlephobia during this research session).

### Detailed Assessment

#### Dockview (`dockview-core`) -- RECOMMENDED

**Why Dockview wins for SemPKM:**

1. **True vanilla TypeScript support.** The `dockview-core` package is a standalone, framework-agnostic package. Content injection uses a direct `containerElement` property -- a plain DOM element that htmx can target immediately:

```typescript
import { DockviewComponent } from 'dockview-core';

const dockview = new DockviewComponent(rootElement, {
  createComponent: (options) => {
    return {
      init: (params) => {
        // Direct DOM access -- perfect for htmx
        htmx.ajax('GET', '/browser/object/' + encodeURIComponent(options.params.iri), {
          target: params.containerElement,
          swap: 'innerHTML'
        });
      },
    };
  },
});
```

2. **Zero dependencies.** No React, no jQuery, nothing. `dockview-core` is self-contained.

3. **Rich feature set.** Tabs, groups, grids, splitviews, drag-and-drop between groups, floating panels, popout windows -- all available without framework bindings.

4. **CSS custom property theming.** Dockview's themes are controlled through `--dv-*` CSS variables. The built-in themes (`dockview-theme-dark`, `dockview-theme-light`, `dockview-theme-abyss`, `dockview-theme-replit`, `dockview-theme-dracula`) can be extended or replaced. Known variables include:
   - `--dv-activegroup-visiblepanel-tab-background-color`
   - `--dv-activegroup-hiddenpanel-tab-background-color`
   - `--dv-inactivegroup-visiblepanel-tab-background-color`
   - `--dv-tabs-and-actions-container-height`
   - `--dv-tabs-and-actions-container-font-size`
   - `--dv-group-view-background-color`
   - `--dv-tab-font-size`
   - `--dv-tab-margin`
   - `--dv-border-radius`
   - `--dv-sash-color` / `--dv-active-sash-color`
   - `--dv-drag-over-background-color` / `--dv-drag-over-border-color`
   - `--dv-floating-box-shadow`
   - `--dv-paneview-header-border-color`
   - `--dv-paneview-active-outline-color`
   - `--dv-icon-hover-background-color`
   - `--dv-tabs-container-scrollbar-color`
   - `--dv-overlay-z-index`

   This aligns perfectly with SemPKM's existing `theme.css` approach -- we can map `--dv-*` variables to our own `--color-*` / `--tab-*` tokens.

5. **Panel constraints.** Dockview supports locked panels (prevents resize via drag handles) and group constraints. This is important for Phase B where the nav tree panel should be non-closable.

6. **Active maintenance.** v4.x is actively developed. The maintainer (mathuo) is responsive on GitHub. Multiple releases per month through 2025. The project has ~3K GitHub stars and growing.

7. **Layout serialization.** `api.toJSON()` and `api.fromJSON(data)` provide clean serialization. The `onDidLayoutChange` event fires on any layout mutation -- ideal for auto-save.

**Risks:**
- Newer library (less battle-tested than GoldenLayout in production at scale)
- Documentation for `dockview-core` (vanilla) is sparser than the React-specific docs
- Some advanced examples in docs only show React patterns; vanilla equivalents must be inferred
- Exact minified+gzipped size of `dockview-core` was not retrieved during research -- needs measurement

#### GoldenLayout 2 -- VIABLE BUT NOT RECOMMENDED

**Strengths:**

1. **Mature and proven.** GoldenLayout has been around since ~2014. Many production deployments. ~6.6K GitHub stars.

2. **TypeScript rewrite in v2.** Clean TypeScript codebase.

3. **Three component binding modes:**
   - **Embedding via Registration:** Classic approach -- register a constructor, GL manages the DOM.
   - **Embedding via Events:** Components obtained via events (`getComponentEvent` / `releaseComponentEvent`), GL manages DOM.
   - **Virtual (VirtualLayout):** Application controls component placement entirely. GL advises via `bindComponentEvent` / `unbindComponentEvent`. Components' root HTML elements' ancestors are NOT reparented. Application manages position:absolute overlays.

4. **Layout serialization.** `saveLayout()` returns a resolved config object. `loadLayout(config)` replaces the current layout. `LayoutConfig.fromResolved()` converts back for reloading.

**Why NOT GoldenLayout for SemPKM:**

1. **DOM reparenting problem.** In non-Virtual mode, whenever the layout is rearranged, "the GoldenLayout DOM is adjusted to reflect the new layout hierarchy. Effectively this involves the ancestors of components' root HTML elements being reparented." This breaks htmx event handlers and internal state. The Virtual mode avoids this but requires the application to manage position:absolute overlay placement manually -- significant complexity.

2. **No floating panels.** GoldenLayout 2 does not support floating/undocked panels within the window (only popout to separate browser windows). Dockview supports both.

3. **LESS-based themes, not CSS custom properties.** GoldenLayout ships `goldenlayout-base.css` + theme files in LESS (`goldenlayout-dark-theme.less`). CSS custom properties are not natively used. SemPKM would need to wrap or override these, adding a translation layer.

4. **Maintenance concerns.** Releases are sporadic. The v2 TypeScript rewrite was significant but community activity has slowed.

5. **Complex binding model.** Three different approaches to component binding means more documentation to navigate and more ways to get it wrong. Dockview's single `createComponent` callback is simpler.

#### Lumino -- NOT RECOMMENDED

Lumino (formerly PhosphorJS) powers JupyterLab. Very capable, but:
- Requires importing multiple `@lumino/*` packages (commands, widgets, dragdrop, messaging, default-theme)
- Tightly coupled to the Lumino Widget lifecycle model (Message passing, attached properties)
- Would require wrapping every htmx partial in a Lumino Widget subclass
- Documentation is Jupyter-centric, not general-purpose
- Overkill for our needs

#### FlexLayout-React, rc-dock -- ELIMINATED

Both require React as a runtime dependency. SemPKM's architecture decision is vanilla JS + htmx. Adding React to the stack is not an option.

---

## 2. Dockview + htmx Compatibility

### Content Injection Strategy

Dockview's `createComponent` callback provides a `params.containerElement` -- a plain DOM element. This is the integration point for htmx.

**Pattern A: htmx.ajax (matches current SemPKM pattern)**

```javascript
const dockview = new DockviewComponent(rootElement, {
  createComponent: (options) => {
    return {
      init: (params) => {
        const container = params.containerElement;

        // Matches current loadTabInGroup pattern exactly
        htmx.ajax('GET', '/browser/object/' + encodeURIComponent(options.params.iri), {
          target: container,
          swap: 'innerHTML'
        });
      },
      update: (event) => {
        // Called when panel parameters change (e.g., different IRI)
        if (event.params.iri) {
          htmx.ajax('GET', '/browser/object/' + encodeURIComponent(event.params.iri), {
            target: event.containerElement,
            swap: 'innerHTML'
          });
        }
      },
    };
  },
});
```

**Pattern B: Declarative hx-* attributes (alternative)**

```javascript
init: (params) => {
  const container = params.containerElement;
  container.setAttribute('hx-get', '/browser/object/' + encodeURIComponent(options.params.iri));
  container.setAttribute('hx-trigger', 'load');
  container.setAttribute('hx-swap', 'innerHTML');
  htmx.process(container);  // Tell htmx to process the new attributes
}
```

Pattern A is recommended because it matches the existing SemPKM pattern used in `loadTabInGroup()` in `workspace-layout.js` (lines 704-762). No refactoring of server-side partials needed.

### DOM Preservation During Panel Moves

**Critical question:** Does Dockview destroy/recreate DOM when panels are dragged to new positions?

**Answer (MEDIUM confidence):** Dockview reparents container elements when panels move between groups. The actual container element is moved in the DOM tree -- it is typically NOT destroyed and recreated. This means:

- Native DOM event listeners (`addEventListener`) survive reparenting because they are attached to the element, not its position in the tree
- htmx's internal state is stored on DOM elements via attributes and internal data maps. When elements are reparented (moved), attributes travel with the element
- **However**, htmx may need re-processing after a move if htmx relies on ancestor-scoped selectors (`closest`, `find` in `hx-target`). Call `htmx.process(containerElement)` after a panel move as a safety measure

**Mitigation strategy:**

```javascript
// After any layout change, re-process htmx on affected panels
dockview.onDidLayoutChange(() => {
  // Process all panel containers to re-establish htmx bindings
  const containers = rootElement.querySelectorAll('[class*="dv-content-container"]');
  containers.forEach(el => {
    htmx.process(el);
  });
});
```

### Event Handler Survival Matrix

| Scenario | htmx handlers survive? | Action needed? |
|----------|----------------------|----------------|
| Tab switch (same group) | YES -- content stays in DOM, just hidden/shown | None |
| Panel drag within group (reorder tabs) | YES -- just tab order changes | None |
| Panel drag to another group | LIKELY YES -- element reparented | Call `htmx.process()` as safety net |
| Panel float/unfloat | NEEDS TESTING -- may reconstruct | Call `htmx.process()` after |
| Panel popout to new window | NO -- entirely new window context | Full re-render via htmx.ajax |

### Key htmx Integration Points

1. **`htmx.process(element)`** -- Process new content, enabling htmx behavior on dynamically added elements. Use after panel creation and layout changes.

2. **`htmx:init` event** -- Triggered after htmx initializes a DOM node. Can be used for additional setup after htmx processes Dockview panel content.

3. **`htmx:beforeProcessNode` / `htmx:afterProcessNode`** -- Lifecycle events for customizing how htmx initializes nodes. Useful for extensions that need to run before/after htmx processes hx-* attributes.

4. **`htmx:beforeSwap`** -- Can intercept content swaps within Dockview panels if custom swap behavior is needed.

---

## 3. Layout Persistence

### Dockview Serialization Format

Dockview's `toJSON()` produces a JSON object describing the full layout hierarchy:

```json
{
  "grid": {
    "root": {
      "type": "branch",
      "data": [
        {
          "type": "leaf",
          "data": {
            "id": "group-1",
            "activeView": "panel-editor-1",
            "views": ["panel-editor-1", "panel-editor-2"]
          },
          "size": 600
        },
        {
          "type": "leaf",
          "data": {
            "id": "group-2",
            "activeView": "panel-relations",
            "views": ["panel-relations", "panel-lint"]
          },
          "size": 300
        }
      ],
      "size": 900
    },
    "width": 900,
    "height": 700,
    "orientation": "HORIZONTAL"
  },
  "panels": {
    "panel-editor-1": {
      "id": "panel-editor-1",
      "contentComponent": "object-editor",
      "params": { "iri": "https://example.org/note/1" },
      "title": "My Note"
    },
    "panel-editor-2": {
      "id": "panel-editor-2",
      "contentComponent": "object-editor",
      "params": { "iri": "https://example.org/concept/2" },
      "title": "Knowledge Management"
    },
    "panel-relations": {
      "id": "panel-relations",
      "contentComponent": "relations-panel",
      "params": {},
      "title": "Relations"
    },
    "panel-lint": {
      "id": "panel-lint",
      "contentComponent": "lint-panel",
      "params": {},
      "title": "Lint"
    }
  },
  "activeGroup": "group-1"
}
```

Key properties of this format:
- `grid.root` is a recursive tree of `branch` (containing children) and `leaf` (containing a group) nodes
- Each `leaf` has `size` (pixels at time of save) and a `data` block with the group's tab list
- `panels` is a flat map of all panels with their component type and parameters
- The format is stable across Dockview patch versions. Major versions may change structure, so version-stamping saved layouts is prudent

### Storing in RDF

Layout JSON can be stored as a user preference in the RDF triplestore using a dedicated vocabulary:

```turtle
@prefix sempkm: <https://sempkm.org/vocab/> .
@prefix user:   <https://sempkm.org/users/> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .

user:alice sempkm:savedLayout [
    a sempkm:WorkspaceLayout ;
    sempkm:layoutName "Research Mode" ;
    sempkm:layoutConfig """{"grid":{"root":{"type":"branch",...}}}""" ;
    sempkm:isDefault true ;
    sempkm:dockviewVersion "4.13" ;
    sempkm:createdAt "2026-02-27T12:00:00Z"^^xsd:dateTime ;
    sempkm:updatedAt "2026-02-27T14:30:00Z"^^xsd:dateTime
] .

user:alice sempkm:savedLayout [
    a sempkm:WorkspaceLayout ;
    sempkm:layoutName "Exploration Mode" ;
    sempkm:layoutConfig """{"grid":{"root":{"type":"branch",...}}}""" ;
    sempkm:isDefault false ;
    sempkm:dockviewVersion "4.13" ;
    sempkm:createdAt "2026-02-27T13:00:00Z"^^xsd:dateTime
] .

user:alice sempkm:activeLayoutName "Research Mode" .
```

### API Endpoints

```
GET  /api/layouts                    -> list user's saved layouts (names + metadata)
GET  /api/layouts/{name}             -> get specific layout JSON config
POST /api/layouts                    -> save current layout (body: {name, config})
PUT  /api/layouts/{name}             -> update existing layout config
DELETE /api/layouts/{name}           -> delete saved layout
PUT  /api/layouts/{name}/activate    -> switch active layout
GET  /api/layouts/active             -> get currently active layout config
```

### Load on Workspace Init

```javascript
async function initLayout() {
  // Fast path: try localStorage cache first
  const cached = localStorage.getItem('sempkm_layout_cache');
  if (cached) {
    try {
      const layoutData = JSON.parse(cached);
      dockview.fromJSON(layoutData);
      // Async validate against server in background
      fetchServerLayout();
      return;
    } catch (e) {
      localStorage.removeItem('sempkm_layout_cache');
    }
  }

  // Slow path: fetch from server
  const resp = await fetch('/api/layouts/active');
  if (resp.ok) {
    const layoutData = await resp.json();
    dockview.fromJSON(layoutData.config);
    localStorage.setItem('sempkm_layout_cache', JSON.stringify(layoutData.config));
  } else {
    // Use default layout
    dockview.fromJSON(DEFAULT_LAYOUT);
  }
}
```

### Auto-Save on Layout Change

```javascript
let saveTimeout;
dockview.onDidLayoutChange(() => {
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    const config = dockview.toJSON();
    // Save to localStorage immediately (fast)
    localStorage.setItem('sempkm_layout_cache', JSON.stringify(config));
    // Persist to server (async, debounced)
    fetch('/api/layouts/active', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config })
    });
  }, 2000); // 2-second debounce
});
```

---

## 4. CSS Custom Property Token Vocabulary

### Current State Analysis

SemPKM's `theme.css` already defines ~40 CSS custom properties across these categories:

| Category | Count | Examples |
|----------|-------|---------|
| Surfaces | 5 | `--color-bg`, `--color-surface`, `--color-surface-raised`, `--color-surface-recessed`, `--color-surface-hover` |
| Text | 3 | `--color-text`, `--color-text-muted`, `--color-text-faint` |
| Borders | 2 | `--color-border`, `--color-border-subtle` |
| Accent | 4 | `--color-accent`, `--color-accent-hover`, `--color-accent-subtle`, `--color-accent-muted` |
| Primary | 3 | `--color-primary`, `--color-primary-hover`, `--color-primary-subtle` |
| Semantic status | 11 | success/error/warning + their bg/border variants |
| Code | 1 | `--color-code-bg` |
| Shadows | 2 | `--shadow`, `--shadow-elevated` |
| Misc | 5 | danger, skeleton, focus-shadow, avatar-text, highlight |
| Non-color (`style.css`) | 3 | `--font-sans`, `--font-mono`, `--radius` |

This is a solid foundation. The naming is already semantic (e.g., `--color-surface-raised` communicates purpose, not hue). The dark mode override in `html[data-theme="dark"]` is clean.

### Recommended Token Architecture

Adopt a **two-tier system** inspired by Open Props (primitive + semantic):

**Tier 1 -- Primitive tokens** (internal, prefixed with `--_` to signal "do not use directly"):
These are raw color scale values. Components never reference these directly. They exist to keep the semantic tier DRY and to make theme swaps possible by changing primitives.

```css
:root {
  /* Gray scale (not referenced by components) */
  --_gray-50:  #fafafa;
  --_gray-100: #f4f5f7;
  --_gray-200: #e0e0e0;
  --_gray-300: #c0c0c0;
  --_gray-400: #999999;
  --_gray-500: #666666;
  --_gray-600: #444444;
  --_gray-700: #2c2c2c;
  --_gray-800: #1a1a2e;

  /* Teal scale */
  --_teal-400: #2dd4bf;
  --_teal-500: #14b8a6;
  --_teal-600: #0d9488;
  --_teal-700: #0f766e;

  /* Blue scale */
  --_blue-400: #60a5fa;
  --_blue-500: #3b82f6;
  --_blue-600: #2d5a9e;
  --_blue-700: #1e3f7a;
}
```

**Tier 2 -- Semantic tokens** (what components reference). The following is the full proposed vocabulary, organized by category. Items marked `(EXISTING)` are already in `theme.css`; items marked `(NEW)` are additions.

### Full Token Vocabulary (Draft)

```css
:root {
  /* ================================================================
     SURFACES
     ================================================================ */
  --color-bg:                    #fafafa;                        /* (EXISTING) page background */
  --color-surface:               #ffffff;                        /* (EXISTING) cards, panels */
  --color-surface-raised:        #f8f9fb;                        /* (EXISTING) elevated surfaces */
  --color-surface-recessed:      #f4f5f7;                        /* (EXISTING) inset areas */
  --color-surface-hover:         rgba(0, 0, 0, 0.04);            /* (EXISTING) hover state */
  --color-surface-active:        rgba(0, 0, 0, 0.08);            /* (NEW) pressed/active state */
  --color-surface-overlay:       rgba(0, 0, 0, 0.5);             /* (NEW) modal backdrop */

  /* ================================================================
     TEXT
     ================================================================ */
  --color-text:                  #1a1a2e;                        /* (EXISTING) primary text */
  --color-text-muted:            #666666;                        /* (EXISTING) secondary text */
  --color-text-faint:            #999999;                        /* (EXISTING) tertiary text */
  --color-text-inverse:          #ffffff;                        /* (NEW) text on dark/accent bg */
  --color-text-on-accent:        #ffffff;                        /* (NEW) text on accent buttons */

  /* ================================================================
     BORDERS
     ================================================================ */
  --color-border:                #e0e0e0;                        /* (EXISTING) default border */
  --color-border-subtle:         #f0f0f0;                        /* (EXISTING) faint border */
  --color-border-strong:         #c0c0c0;                        /* (NEW) focused inputs, dividers */
  --color-border-accent:         var(--color-accent);             /* (NEW) active panel indicator */

  /* ================================================================
     ACCENT (teal/cyan)
     ================================================================ */
  --color-accent:                #0d9488;                        /* (EXISTING) */
  --color-accent-hover:          #0f766e;                        /* (EXISTING) */
  --color-accent-subtle:         rgba(13, 148, 136, 0.08);       /* (EXISTING) */
  --color-accent-muted:          rgba(13, 148, 136, 0.15);       /* (EXISTING) */

  /* ================================================================
     PRIMARY
     ================================================================ */
  --color-primary:               #2d5a9e;                        /* (EXISTING) */
  --color-primary-hover:         #1e3f7a;                        /* (EXISTING) */
  --color-primary-subtle:        rgba(45, 90, 158, 0.08);        /* (EXISTING) */

  /* ================================================================
     SEMANTIC STATUS
     ================================================================ */
  --color-success:               #2a8a4a;                        /* (EXISTING) */
  --color-error:                 #c0392b;                        /* (EXISTING) */
  --color-warning:               #d4a017;                        /* (EXISTING) */
  --color-info:                  var(--color-primary);            /* (NEW) explicit info color */
  --color-danger:                #e74c3c;                        /* (EXISTING) */
  /* + existing bg/border variants for success/error/warning/info */
  --color-success-bg:            #e8f5e9;                        /* (EXISTING) */
  --color-success-border:        #a5d6a7;                        /* (EXISTING) */
  --color-error-bg:              #fef2f2;                        /* (EXISTING) */
  --color-error-border:          #fca5a5;                        /* (EXISTING) */
  --color-warning-bg:            #fffbeb;                        /* (EXISTING) */
  --color-warning-border:        #fcd34d;                        /* (EXISTING) */
  --color-info-bg:               #eff6ff;                        /* (EXISTING) */
  --color-info-border:           #93c5fd;                        /* (EXISTING) */

  /* ================================================================
     SHADOWS
     ================================================================ */
  --shadow-sm:                   0 1px 2px rgba(0, 0, 0, 0.05);  /* (NEW) subtle elevation */
  --shadow:                      0 1px 3px rgba(0, 0, 0, 0.08);  /* (EXISTING) cards */
  --shadow-md:                   0 4px 8px rgba(0, 0, 0, 0.12);  /* (NEW) dropdowns */
  --shadow-elevated:             0 4px 12px rgba(0, 0, 0, 0.15); /* (EXISTING) popovers */
  --shadow-popover:              0 8px 24px rgba(0, 0, 0, 0.20); /* (NEW) floating panels */

  /* ================================================================
     SPACING SCALE
     ================================================================ */
  --space-1:                     4px;                             /* (NEW) */
  --space-2:                     8px;                             /* (NEW) */
  --space-3:                     12px;                            /* (NEW) */
  --space-4:                     16px;                            /* (NEW) */
  --space-5:                     20px;                            /* (NEW) */
  --space-6:                     24px;                            /* (NEW) */
  --space-8:                     32px;                            /* (NEW) */

  /* ================================================================
     RADII
     ================================================================ */
  --radius-sm:                   4px;                             /* (NEW) small elements */
  --radius:                      6px;                             /* (EXISTING) default */
  --radius-md:                   8px;                             /* (NEW) cards */
  --radius-lg:                   12px;                            /* (NEW) modals, dialogs */

  /* ================================================================
     TYPOGRAPHY
     ================================================================ */
  --font-sans:                   -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; /* (EXISTING) */
  --font-mono:                   "SF Mono", "Fira Code", "Fira Mono", "Roboto Mono", Consolas, monospace; /* (EXISTING) */
  --font-size-xs:                0.72rem;                         /* (NEW) labels, badges */
  --font-size-sm:                0.83rem;                         /* (NEW) tree nodes, small text */
  --font-size-base:              0.9rem;                          /* (NEW) body text -- matches current */
  --font-size-md:                1rem;                            /* (NEW) headings */
  --font-size-lg:                1.15rem;                         /* (NEW) page titles */

  /* ================================================================
     PANEL / TAB -- Dockview Integration
     ================================================================ */
  --panel-header-height:         36px;                            /* (NEW) matches current .pane-header */
  --panel-header-bg:             var(--color-surface);            /* (NEW) */
  --panel-header-text:           var(--color-text-muted);         /* (NEW) */
  --panel-header-border:         var(--color-border);             /* (NEW) */

  --tab-height:                  32px;                            /* (NEW) */
  --tab-bg:                      transparent;                     /* (NEW) inactive tab */
  --tab-bg-active:               var(--color-surface);            /* (NEW) active tab */
  --tab-bg-hover:                var(--color-surface-hover);      /* (NEW) */
  --tab-text:                    var(--color-text-muted);         /* (NEW) */
  --tab-text-active:             var(--color-text);               /* (NEW) */
  --tab-border-active:           var(--color-accent);             /* (NEW) active tab indicator */
  --tab-close-hover:             var(--color-error);              /* (NEW) close button on hover */

  --gutter-size:                 5px;                             /* (NEW) -- matches current */
  --gutter-color:                var(--color-border);             /* (NEW) */
  --gutter-color-hover:          var(--color-accent);             /* (NEW) */
  --gutter-color-active:         var(--color-accent);             /* (NEW) while dragging */

  /* ================================================================
     SIDEBAR
     ================================================================ */
  --sidebar-width:               220px;                           /* (NEW) formalize existing inline */
  --sidebar-width-collapsed:     48px;                            /* (NEW) formalize existing inline */
  --sidebar-bg:                  var(--color-surface);            /* (NEW) */
  --sidebar-border:              var(--color-border);             /* (NEW) */

  /* ================================================================
     GRAPH VIEW
     ================================================================ */
  --graph-bg:                    var(--color-bg);                 /* (NEW) Cytoscape canvas bg */
  --graph-node-fill:             var(--color-accent);             /* (NEW) */
  --graph-edge-color:            var(--color-border);             /* (NEW) */
  --graph-label-color:           var(--color-text);               /* (NEW) */

  /* ================================================================
     MODAL / DIALOG
     ================================================================ */
  --modal-bg:                    var(--color-surface);            /* (NEW) */
  --modal-backdrop:              var(--color-surface-overlay);    /* (NEW) */
  --modal-shadow:                var(--shadow-popover);           /* (NEW) */
  --modal-radius:                var(--radius-lg);                /* (NEW) */

  /* ================================================================
     FOCUS
     ================================================================ */
  --color-focus-shadow:          rgba(45, 90, 158, 0.15);        /* (EXISTING) */
  --focus-ring:                  0 0 0 2px var(--color-focus-shadow); /* (NEW) reusable ring */

  /* ================================================================
     MISC (EXISTING)
     ================================================================ */
  --color-code-bg:               #f5f5f5;
  --color-skeleton-from:         #f0f0f0;
  --color-skeleton-mid:          #e0e0e0;
  --color-avatar-text:           #ffffff;
  --color-highlight:             rgba(255, 235, 59, 0.3);
}
```

### Token Count Summary

| Category | Existing | New | Total |
|----------|----------|-----|-------|
| Surfaces | 5 | 2 | 7 |
| Text | 3 | 2 | 5 |
| Borders | 2 | 2 | 4 |
| Accent | 4 | 0 | 4 |
| Primary | 3 | 0 | 3 |
| Status | 12 | 1 | 13 |
| Shadows | 2 | 3 | 5 |
| Spacing | 0 | 7 | 7 |
| Radii | 1 | 3 | 4 |
| Typography | 2 fonts | 5 sizes | 7 |
| Panel/Tab | 0 | 13 | 13 |
| Sidebar | 0 | 4 | 4 |
| Graph | 0 | 4 | 4 |
| Modal | 0 | 4 | 4 |
| Focus | 1 | 1 | 2 |
| Misc | 5 | 0 | 5 |
| **TOTAL** | **~40** | **~51** | **~91** |

This is a manageable count. Each token has a clear purpose. The system stays under 100 tokens, which is the practical upper bound before developer confusion sets in.

### Migration Notes for Existing CSS

Existing CSS files (`workspace.css`, `style.css`, `forms.css`, `views.css`) should be audited to replace hardcoded values with tokens. For example:

```css
/* BEFORE (workspace.css line 43) */
.pane-header {
    height: 36px;
    font-size: 0.8rem;
    font-weight: 600;
}

/* AFTER */
.pane-header {
    height: var(--panel-header-height);
    font-size: var(--font-size-xs);
    font-weight: 600;
}
```

---

## 5. Model-Contributed Themes

### Recommended Format: CSS Override Files

A Mental Model's theme bundle should be a CSS file that overrides semantic tokens. CSS is the native format -- no translation layer needed.

**Example: Academic Research Model theme**

```css
/* model-theme-academic.css */
/* Contributed by: Academic Research Model */
/* Overrides accent and primary colors to indigo/purple */

:root {
  --color-accent: #6366f1;
  --color-accent-hover: #4f46e5;
  --color-accent-subtle: rgba(99, 102, 241, 0.08);
  --color-accent-muted: rgba(99, 102, 241, 0.15);
  --color-primary: #7c3aed;
  --color-primary-hover: #6d28d9;
  --color-primary-subtle: rgba(124, 58, 237, 0.08);
}

html[data-theme="dark"] {
  --color-accent: #818cf8;
  --color-accent-hover: #a5b4fc;
  --color-accent-subtle: rgba(129, 140, 248, 0.12);
  --color-accent-muted: rgba(129, 140, 248, 0.20);
  --color-primary: #a78bfa;
  --color-primary-hover: #c4b5fd;
  --color-primary-subtle: rgba(167, 139, 250, 0.12);
}
```

### Why CSS Over JSON

- CSS is the native browser format -- zero translation overhead
- `<link>` tags can be dynamically added/removed without JavaScript processing
- CSS specificity/cascade handles conflicts naturally (model CSS loaded after base `theme.css`)
- Developers can inspect applied theme values directly in browser DevTools
- No build step required

### Model Manifest Declaration

```json
{
  "id": "academic-research",
  "name": "Academic Research Model",
  "version": "1.0.0",
  "contributions": {
    "theme": {
      "stylesheet": "themes/academic.css",
      "name": "Academic Indigo",
      "description": "Indigo and purple accent colors for academic use",
      "previewColors": ["#6366f1", "#7c3aed"]
    }
  }
}
```

### Runtime Loading Mechanism

```javascript
function loadModelTheme(modelId) {
  // Remove any existing model theme link
  const existing = document.getElementById('model-theme-css');
  if (existing) existing.remove();

  if (!modelId) return; // Clear model theme

  const link = document.createElement('link');
  link.id = 'model-theme-css';
  link.rel = 'stylesheet';
  link.href = '/api/models/' + encodeURIComponent(modelId) + '/theme.css';
  // Insert after base theme.css so model overrides take precedence
  const baseTheme = document.querySelector('link[href*="theme.css"]');
  if (baseTheme && baseTheme.nextSibling) {
    baseTheme.parentNode.insertBefore(link, baseTheme.nextSibling);
  } else {
    document.head.appendChild(link);
  }
}
```

### Guardrails

Model themes should be constrained to prevent breaking the UI:

1. **Only allow `:root` and `html[data-theme]` selectors.** Reject CSS that targets structural classes directly (`.sidebar`, `.workspace-container`, etc.). Validate server-side before serving.
2. **Only override color, shadow, and opacity tokens.** Models should NOT change spacing, sizing, or typography tokens -- those affect layout structure.
3. **Provide a "reset to default" escape hatch** in the settings UI.
4. **Preview before applying** -- show a small swatch or thumbnail of the model's color palette before the user activates it.

---

## 6. Named Saved Layouts (Dashboards)

### Core Mechanism

Dockview natively supports named layouts through its serialization API:

1. **Save:** `const config = dockview.toJSON()` produces serializable JSON
2. **Load:** `dockview.fromJSON(config)` replaces the current layout entirely
3. **Switch:** Call `fromJSON` with a different saved config to switch between layouts

### Preset Layout Factories

Define factory functions for built-in layout presets that users get out of the box:

```javascript
const LAYOUT_PRESETS = {
  'default': {
    name: 'Default',
    description: 'Three-column layout: Explorer, Editor, Sidebar',
    icon: 'layout',
    factory: () => ({
      grid: {
        root: { type: 'branch', data: [
          { type: 'leaf', size: 220, data: { id: 'g-nav', views: ['nav-tree'], activeView: 'nav-tree' } },
          { type: 'leaf', size: 550, data: { id: 'g-editor', views: [], activeView: null } },
          { type: 'leaf', size: 280, data: { id: 'g-side', views: ['relations', 'lint'], activeView: 'relations' } }
        ]},
        orientation: 'HORIZONTAL'
      },
      panels: {
        'nav-tree': { id: 'nav-tree', contentComponent: 'nav-tree', title: 'Explorer' },
        'relations': { id: 'relations', contentComponent: 'relations-panel', title: 'Relations' },
        'lint': { id: 'lint', contentComponent: 'lint-panel', title: 'Lint' }
      }
    })
  },

  'research-mode': {
    name: 'Research Mode',
    description: 'Wide editor, narrow nav, relations visible',
    icon: 'book-open',
    factory: () => ({
      grid: {
        root: { type: 'branch', data: [
          { type: 'leaf', size: 180, data: { id: 'g-nav', views: ['nav-tree'], activeView: 'nav-tree' } },
          { type: 'leaf', size: 650, data: { id: 'g-editor', views: [], activeView: null } },
          { type: 'leaf', size: 220, data: { id: 'g-side', views: ['relations'], activeView: 'relations' } }
        ]},
        orientation: 'HORIZONTAL'
      },
      panels: {
        'nav-tree': { id: 'nav-tree', contentComponent: 'nav-tree', title: 'Explorer' },
        'relations': { id: 'relations', contentComponent: 'relations-panel', title: 'Relations' }
      }
    })
  },

  'exploration-mode': {
    name: 'Exploration Mode',
    description: 'Graph view prominent, SPARQL console open',
    icon: 'compass',
    factory: () => ({
      grid: {
        root: { type: 'branch', data: [
          { type: 'leaf', size: 200, data: { id: 'g-nav', views: ['nav-tree'], activeView: 'nav-tree' } },
          { type: 'branch', size: 850, data: [
            { type: 'leaf', size: 500, data: { id: 'g-main', views: ['graph-view'], activeView: 'graph-view' } },
            { type: 'leaf', size: 250, data: { id: 'g-console', views: ['sparql-console'], activeView: 'sparql-console' } }
          ]}
        ]},
        orientation: 'HORIZONTAL'
      },
      panels: {
        'nav-tree': { id: 'nav-tree', contentComponent: 'nav-tree', title: 'Explorer' },
        'graph-view': { id: 'graph-view', contentComponent: 'graph-view', title: 'Graph' },
        'sparql-console': { id: 'sparql-console', contentComponent: 'sparql-console', title: 'SPARQL' }
      }
    })
  },

  'writing-mode': {
    name: 'Writing Mode',
    description: 'Full-width editor, no side panels',
    icon: 'pen-line',
    factory: () => ({
      grid: {
        root: { type: 'leaf', data: { id: 'g-editor', views: [], activeView: null } },
        orientation: 'HORIZONTAL'
      },
      panels: {}
    })
  }
};
```

### UX for Save/Load/Switch

**Command palette integration (ninja-keys):**

```
Layout: Save Current as...     -> prompts for name, calls toJSON() + POST /api/layouts
Layout: Switch to...           -> shows list of saved + preset layouts
Layout: Delete...              -> shows list of user-saved layouts
Layout: Reset to Default       -> loads the 'default' preset
```

**Status bar widget (optional, bottom-right corner):**

```
[ Research Mode v ]   -> dropdown showing all available layouts
```

**Keyboard shortcuts:**

```
Ctrl+Shift+L         -> open layout switcher (filtered ninja-keys)
```

### Layout Switching Flow

```javascript
async function switchLayout(layoutName) {
  // 1. Check if it's a preset
  if (LAYOUT_PRESETS[layoutName]) {
    const config = LAYOUT_PRESETS[layoutName].factory();
    dockview.fromJSON(config);
    // Update active layout on server
    await fetch('/api/layouts/' + encodeURIComponent(layoutName) + '/activate', { method: 'PUT' });
    return;
  }

  // 2. Fetch user-saved layout from server
  const resp = await fetch('/api/layouts/' + encodeURIComponent(layoutName));
  if (resp.ok) {
    const data = await resp.json();
    dockview.fromJSON(data.config);
    await fetch('/api/layouts/' + encodeURIComponent(layoutName) + '/activate', { method: 'PUT' });
  }
}
```

---

## 7. Migration Strategy from Split.js

### Current Architecture

SemPKM currently uses Split.js in two distinct places:

1. **Outer 3-pane split** (`workspace.js`, line 47):
   ```javascript
   splitInstance = Split(['#nav-pane', '#editor-pane', '#right-pane'], {
     sizes: lastFullSizes || [20, 50, 30],
     minSize: [180, 300, 200],
     gutterSize: 5,
     cursor: 'col-resize',
     ...
   });
   ```
   Manages the three main columns: navigation, editor, and right panel (relations/lint).

2. **Inner editor group split** (`workspace-layout.js`, line 368):
   ```javascript
   groupSplitInstance = Split(selectors, {
     sizes: sizes,
     minSize: 200,
     gutterSize: 1,
     gutterClass: 'gutter-editor-groups',
     cursor: 'col-resize',
     ...
   });
   ```
   Manages horizontal splits between editor groups (1-4 groups). This is the complex part with tab management, drag-and-drop between groups, context menus, etc.

Plus a manual bottom panel resize handle (not Split.js).

### The Plan: Three Incremental Phases

#### Phase A: Dockview for Editor Groups (replace inner split)

**Scope:** Replace the editor groups system in `workspace-layout.js` with a Dockview instance mounted inside `#editor-pane`. The outer 3-pane Split.js remains untouched.

**Why start here:**
- The editor groups area is already the most complex part of the layout code (1050 lines in `workspace-layout.js`)
- The existing `WorkspaceLayout` class manages tab state, serialization, group creation/removal, drag-and-drop, context menus -- all of which Dockview provides natively
- The outer pane split (nav/editor/right) is simple and stable -- no benefit to replacing it first
- Lowest blast radius: if Dockview has issues, they are contained within the editor pane

**Steps:**
1. Add `dockview-core` to the project (npm install or CDN)
2. Include Dockview's base CSS + create `dockview-sempkm-bridge.css` theme mapping
3. Create `workspace-dockview.js` -- Dockview wrapper that implements the same public API as current `workspace-layout.js` (`openTab`, `closeTab`, `switchTab`, `splitRight`, `getActiveEditorArea`)
4. Mount DockviewComponent inside `#editor-pane` (replacing `#editor-groups-container`)
5. Map existing `WorkspaceLayout` tab state from sessionStorage to Dockview's `fromJSON`
6. Wire `createComponent` to load content via `htmx.ajax` (same pattern as current `loadTabInGroup`)
7. Remove inner Split.js dependency; keep outer Split.js for nav/editor/right columns
8. Update E2E test selectors for changed DOM structure inside editor pane
9. Verify: tab operations, drag-and-drop, split right, close group, dirty indicators, context menus

**DOM structure after Phase A:**
```
.workspace-container
  +-- #nav-pane                       (unchanged, Split.js outer)
  +-- .gutter                         (unchanged, Split.js outer)
  +-- #editor-pane                    (unchanged container)
  |     +-- DockviewComponent         (NEW -- replaces #editor-groups-container)
  |           +-- dockview tabs/groups
  |           +-- panel containers (htmx-loaded content)
  |     +-- #panel-resize-handle      (unchanged)
  |     +-- #bottom-panel             (unchanged)
  +-- .gutter                         (unchanged, Split.js outer)
  +-- #right-pane                     (unchanged, Split.js outer)
```

#### Phase B: Dockview for Full Layout (replace outer split)

**Scope:** Promote Dockview to manage the entire workspace layout. Nav tree, editor, right panel, and bottom panel all become Dockview panels.

**Steps:**
1. Nav tree becomes a Dockview panel (constrained: locked, not closable, min-width)
2. Right pane (relations, lint) becomes Dockview panels (closable, can be hidden)
3. Bottom panel (SPARQL console) becomes a Dockview panel in a bottom split
4. Remove outer Split.js entirely
5. Remove `#nav-pane`, `#editor-pane`, `#right-pane` hardcoded DOM -- Dockview creates its own structure
6. Port pane toggle logic (Ctrl+B for nav, Ctrl+Shift+B for right) to Dockview panel show/hide API
7. Full E2E test update: all selectors change

**DOM structure after Phase B:**
```
.workspace-container
  +-- DockviewComponent (manages everything)
        +-- Panel: "Explorer" (nav tree, locked, not closable)
        +-- Group: "Editors" (tabbed, main area)
        |     +-- Panel: "Editor Tab 1" (htmx-loaded)
        |     +-- Panel: "Editor Tab 2" (htmx-loaded)
        +-- Group: "Sidebar" (tabbed, right area)
        |     +-- Panel: "Relations" (htmx-loaded)
        |     +-- Panel: "Lint" (htmx-loaded)
        +-- Panel: "SPARQL Console" (bottom area)
```

#### Phase C: Advanced Features

After the full Dockview migration is stable:

1. **Floating panels** -- undock any panel to a floating overlay within the window
2. **Named layout presets** -- Research Mode, Exploration Mode, Writing Mode
3. **Layout persistence** -- save/load layouts to RDF triplestore with localStorage cache
4. **Model-contributed themes** -- CSS override injection per active Mental Model
5. **Panel popout** -- pop a panel to a separate browser window (if needed)
6. **Layout sharing** -- export/import layout configs (JSON download/upload)

### Risk Mitigation During Migration

| Risk | Phase | Mitigation |
|------|-------|-----------|
| E2E tests break (124 tests depend on current DOM) | A | Phase A: outer DOM unchanged. Inner selectors update required but contained |
| htmx handlers lost during panel moves | A, B | Call `htmx.process()` on panels after any `onDidLayoutChange` event |
| Split.js + Dockview coexist causes sizing conflicts | A | They operate in separate DOM regions (outer vs inner) in Phase A |
| Dockview CSS clashes with existing workspace.css | A | Namespace overrides under `.dockview-theme-sempkm` class; audit specificity |
| CodeMirror instances break when panel reparented | A | Test in PoC; may need `editor.destroy()` / recreate after move |
| Cytoscape.js canvas breaks when panel reparented | B | Test in PoC; canvas may need resize event dispatch after move |
| Performance regression from heavier library | A | Dockview is zero-dep; profile before/after. Unlikely to regress |
| Saved sessionStorage layout format incompatible | A | Write migration function: old format -> Dockview `fromJSON` format |

### Rollback Strategy

Keep `workspace-layout.js` in a `_deprecated/` folder during Phase A. If Dockview integration fails, revert by swapping the JS include back. The outer layout does not change in Phase A, making rollback safe.

---

## 8. Dockview Integration Architecture

### Component Type Registry

```javascript
// workspace-dockview.js

const PANEL_TYPES = {
  'object-editor': {
    init: (params) => {
      const iri = params.params.iri;
      htmx.ajax('GET', '/browser/object/' + encodeURIComponent(iri), {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    },
    update: (params) => {
      if (params.params.iri) {
        htmx.ajax('GET', '/browser/object/' + encodeURIComponent(params.params.iri), {
          target: params.containerElement,
          swap: 'innerHTML'
        });
      }
    }
  },

  'nav-tree': {
    init: (params) => {
      htmx.ajax('GET', '/browser/nav-tree', {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    }
  },

  'table-view': {
    init: (params) => {
      const viewId = params.params.viewId;
      htmx.ajax('GET', '/browser/views/table/' + encodeURIComponent(viewId), {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    }
  },

  'card-view': {
    init: (params) => {
      const viewId = params.params.viewId;
      htmx.ajax('GET', '/browser/views/card/' + encodeURIComponent(viewId), {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    }
  },

  'graph-view': {
    init: (params) => {
      htmx.ajax('GET', '/browser/views/graph/' + encodeURIComponent(params.params.viewId), {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    }
  },

  'sparql-console': {
    init: (params) => {
      htmx.ajax('GET', '/browser/sparql-panel', {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    }
  },

  'relations-panel': {
    init: (params) => {
      if (params.params.iri) {
        htmx.ajax('GET', '/browser/relations/' + encodeURIComponent(params.params.iri), {
          target: params.containerElement,
          swap: 'innerHTML'
        });
      }
    }
  },

  'lint-panel': {
    init: (params) => {
      if (params.params.iri) {
        htmx.ajax('GET', '/browser/lint/' + encodeURIComponent(params.params.iri), {
          target: params.containerElement,
          swap: 'innerHTML'
        });
      }
    }
  }
};
```

### CSS Theme Bridge

Map Dockview's `--dv-*` CSS variables to SemPKM's token system:

```css
/* dockview-sempkm-bridge.css */

.dockview-theme-sempkm {
  /* Tab backgrounds */
  --dv-activegroup-visiblepanel-tab-background-color: var(--tab-bg-active);
  --dv-activegroup-hiddenpanel-tab-background-color: var(--tab-bg);
  --dv-inactivegroup-visiblepanel-tab-background-color: var(--tab-bg-active);
  --dv-inactivegroup-hiddenpanel-tab-background-color: var(--tab-bg);

  /* Tab sizing and typography */
  --dv-tabs-and-actions-container-height: var(--tab-height);
  --dv-tabs-and-actions-container-font-size: var(--font-size-sm);
  --dv-tab-font-size: var(--font-size-sm);
  --dv-tab-margin: 0;
  --dv-border-radius: var(--radius-sm);

  /* Tab dividers */
  --dv-tab-divider-color: var(--color-border-subtle);

  /* Group/panel backgrounds */
  --dv-group-view-background-color: var(--color-surface);
  --dv-tabs-and-actions-container-background-color: var(--panel-header-bg);
  --dv-paneview-header-background-color: var(--panel-header-bg);
  --dv-paneview-header-border-color: var(--panel-header-border);

  /* Splitter/sash */
  --dv-sash-color: var(--gutter-color);
  --dv-active-sash-color: var(--gutter-color-active);
  --dv-active-sash-transition-duration: 150ms;
  --dv-active-sash-transition-delay: 100ms;

  /* Drag and drop */
  --dv-drag-over-background-color: var(--color-accent-subtle);
  --dv-drag-over-border-color: var(--color-accent);

  /* Focus */
  --dv-paneview-active-outline-color: var(--tab-border-active);
  --dv-color-focused-tab: var(--tab-border-active);

  /* Floating panels */
  --dv-floating-box-shadow: var(--shadow-popover);

  /* Scrollbar */
  --dv-tabs-container-scrollbar-color: var(--color-border);

  /* Icon hover */
  --dv-icon-hover-background-color: var(--color-surface-hover);

  /* Z-index */
  --dv-overlay-z-index: 999;
}
```

### Public API Compatibility Layer

To minimize churn in existing code that calls `openTab()`, `closeTab()`, etc., the Dockview wrapper should expose the same public API:

```javascript
// Backwards-compatible API surface
window.openTab = function(objectIri, label, mode) { /* ... delegate to dockview.addPanel */ };
window.closeTab = function(objectIri) { /* ... delegate to dockview panel removal */ };
window.switchTab = function(objectIri) { /* ... delegate to dockview setActivePanel */ };
window.splitRight = function(groupId) { /* ... delegate to dockview group operations */ };
window.getActiveEditorArea = function() { /* ... return active panel's containerElement */ };
window.markDirty = function(objectIri) { /* ... update panel title with dirty indicator */ };
window.markClean = function(objectIri) { /* ... remove dirty indicator from title */ };
window._workspaceLayout = dockviewAdapter; // Adapter with .groups, .activeGroupId, etc.
```

---

## 9. Risks and Mitigations

### HIGH Severity

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| `dockview-core` vanilla docs are sparse -- discovery by trial-and-error | Dev velocity decrease, 2-3x time for Phase A | MEDIUM | Build a small PoC first (1-2 days). Study React docs (same concepts apply). Read `dockview-core` TypeScript source directly |
| htmx event handlers break on panel drag between groups | Broken save forms, broken hx-trigger attributes | MEDIUM | `htmx.process()` after every `onDidLayoutChange` event. Build explicit test cases in PoC |
| E2E test suite (124 tests) breaks due to DOM structure changes | Regression blocking | HIGH | Phase A minimizes blast radius (outer structure unchanged). Budget time for selector updates |

### MEDIUM Severity

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Dockview CSS conflicts with existing workspace.css | Visual glitches, doubled borders, wrong backgrounds | MEDIUM | Wrap Dockview in `.dockview-theme-sempkm` class. Audit specificity carefully. Test both light and dark themes |
| CodeMirror editors break when panel is reparented | Editor loses state/cursor/content | MEDIUM | Test in PoC. Potential fix: CodeMirror's `dom.removeEventListener` is robust to reparenting, but scroll position may reset |
| Layout serialization format changes between Dockview major versions | Saved layouts become invalid, users lose their custom layouts | LOW | Pin Dockview version. Version-stamp saved layouts. Write migration function for version bumps |

### LOW Severity

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Dockview project abandoned | Would need to migrate again eventually | VERY LOW | Active project with growing community. VSCode-inspired architecture is standard. Fork-and-maintain is feasible given zero deps |
| Token system becomes too large | Developer confusion about which token to use | LOW | Keep under 100 tokens. Document each one with examples. Provide a visual token reference page |
| Model-contributed themes break accessibility | Poor contrast ratios in custom themes | MEDIUM | Validate contrast ratios server-side (WCAG AA). Warn model developers about minimum contrast requirements |

---

## 10. Open Questions for Phase-Specific Research

These questions could not be fully resolved during this research phase and should be addressed during implementation (PoC or Phase A):

1. **Dockview `containerElement` timing.** Exactly when is `containerElement` available after `addPanel()`? Can we call `htmx.ajax` immediately in `init`, or does it need `requestAnimationFrame`?

2. **CodeMirror + Dockview reparenting.** Does CodeMirror 6 survive DOM reparenting when a Dockview panel moves between groups? If not, what is the cost of destroy + recreate?

3. **Cytoscape.js + Dockview reparenting.** Does the Cytoscape.js canvas survive panel moves? Canvas elements may need a `resize()` call after reparenting.

4. **Dockview popout windows and htmx.** If a panel is popped out to a new browser window, can htmx still make same-origin requests to the backend? (Should work, but needs verification.)

5. **Exact bundle size.** `dockview-core` minified+gzipped size was not retrieved from Bundlephobia. Need to `npm install dockview-core` and measure. Expected to be in the 50-100kB gzipped range based on the npm unpacked size.

6. **Panel lock constraints.** Can Dockview mark a panel as "not closable", "not draggable", and "minimum width"? Documentation suggests yes via locked panels and group constraints, but exact API needs verification for `dockview-core` (not React wrapper).

7. **Dockview tab rendering customization.** Can we add custom elements to tab headers (dirty dot indicator, type icon, close button)? The React version supports custom tab renderers; need to confirm `dockview-core` exposes the same.

---

## Sources

### Dockview
- [Dockview official site](https://dockview.dev/) -- zero dependency layout manager
- [Dockview GitHub](https://github.com/mathuo/dockview) -- source code, issues, releases
- [Dockview Theme Documentation](https://dockview.dev/docs/overview/getStarted/theme/) -- CSS variable theming
- [Dockview theme.scss source](https://github.com/mathuo/dockview/blob/master/packages/dockview-core/src/theme.scss) -- full list of `--dv-*` variables
- [Dockview Saving State](https://dockview.dev/docs/core/state/save/) -- `toJSON()` documentation
- [Dockview Loading State](https://dockview.dev/docs/core/state/load/) -- `fromJSON()` documentation
- [Dockview Locked Panels](https://dockview.dev/docs/core/locked/) -- panel constraints
- [Dockview Group Constraints](https://dockview.dev/docs/core/groups/constraints/) -- group-level constraints
- [Dockview Adding Panels](https://dockview.dev/docs/core/panels/add/) -- panel creation API
- [Dockview Options](https://dockview.dev/docs/api/dockview/options/) -- `createComponent` and other options
- [Dockview Panel API](https://dockview.dev/docs/api/dockview/panelApi/) -- panel instance methods
- [dockview-core npm](https://www.npmjs.com/package/dockview-core) -- npm package
- [dockview-core README](https://github.com/mathuo/dockview/blob/master/packages/dockview-core/README.md) -- vanilla TS usage
- [Dockview 4.0.0 Release](https://dockview.dev/blog/dockview-4.0.0-release/) -- v4 changes

### GoldenLayout
- [GoldenLayout v2 docs](https://golden-layout.github.io/golden-layout/version-2/) -- version 2 changes
- [GoldenLayout binding components](https://golden-layout.github.io/golden-layout/binding-components/) -- three binding modes
- [GoldenLayout GitHub](https://github.com/golden-layout/golden-layout) -- source code
- [GoldenLayout npm](https://www.npmjs.com/package/golden-layout) -- npm package
- [GoldenLayout virtual-layout.ts source](https://github.com/golden-layout/golden-layout/blob/master/src/ts/virtual-layout.ts) -- VirtualLayout implementation
- [GoldenLayout binding docs (GitHub)](https://github.com/golden-layout/golden-layout/blob/master/docs/binding-components/index.md) -- DOM reparenting details

### CSS Design Tokens
- [Open Props](https://open-props.style/) -- CSS custom property system
- [CSS-Tricks: Open Props as a system](https://css-tricks.com/open-props-and-custom-properties-as-a-system/) -- analysis of the pattern
- [Penpot: Design tokens and CSS variables guide](https://penpot.app/blog/the-developers-guide-to-design-tokens-and-css-variables/) -- two-tier architecture
- [EightShapes: Naming tokens](https://medium.com/eightshapes-llc/naming-tokens-in-design-systems-9e86c7444676) -- naming conventions
- [Radix Themes styling](https://www.radix-ui.com/themes/docs/overview/styling) -- CSS variable theming approach
- [The Design System Guide: Design Tokens](https://thedesignsystem.guide/design-tokens) -- tier architecture
- [Smashing Magazine: Naming best practices](https://www.smashingmagazine.com/2024/05/naming-best-practices/) -- semantic naming
- [Nord Design System: Naming](https://nordhealth.design/naming/) -- naming conventions
- [Token CSS](https://tokencss.com/) -- token-based CSS approach

### htmx
- [htmx Documentation](https://htmx.org/docs/) -- core concepts
- [htmx JavaScript API](https://htmx.org/api/) -- `htmx.process()` and programmatic usage
- [htmx Events](https://htmx.org/events/) -- lifecycle events (init, beforeProcessNode, etc.)
- [htmx Reference](https://htmx.org/reference/) -- full attribute and event reference
