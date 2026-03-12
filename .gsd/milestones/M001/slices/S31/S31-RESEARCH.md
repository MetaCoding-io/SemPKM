# Phase 31: Object View Redesign - Research

**Researched:** 2026-03-02
**Domain:** Frontend template restructuring, CSS transitions, localStorage per-object preferences
**Confidence:** HIGH

## Summary

This phase redesigns the object tab so that the Markdown body is the primary visible content in both view and edit modes, with RDF properties hidden behind a toggle badge. The existing architecture (Jinja2 templates, htmx partials, CSS 3D flip, dockview panels) is well understood from direct codebase inspection and requires no new libraries or frameworks.

The implementation is entirely frontend template + CSS + JS work. The current `object_tab.html` renders a toolbar, a flip container with read face (`object_read.html`) and edit face (`object_form.html`). The read face currently shows properties first (in a `<details open>` element) followed by the Markdown body. The edit face shows properties (form) at top and body editor at bottom in a vertical split. Both faces need to be inverted: body first, properties collapsed by default.

**Primary recommendation:** Restructure `object_read.html` and `object_tab.html` (edit face) to place body content first with properties in a collapsible section controlled by a badge button in the toolbar. Use localStorage keyed per object IRI for collapse preference persistence. No backend changes needed except passing a property count to the template context.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Toggle badge positioned in the header toolbar, grouped with other controls on the right side
- Clicking the badge slides properties down inline, pushing the body content down with a smooth CSS transition
- Badge shows "N properties" with the actual count (e.g. "5 properties")
- Expanded properties list appears between the fixed header and the body content area
- Same pattern on both sides of the flip card: view mode shows read-only properties; edit mode shows the existing editable fieldsets (collapsible fieldsets already exist — reuse them inside the toggle)
- Markdown body (view mode) or Markdown editor (edit mode) fills the full width of the dockview panel with comfortable padding
- Fixed header at top; body content scrolls independently beneath it
- When an object has no Markdown body (empty or missing): show subtle muted placeholder text ("No content") AND auto-expand properties by default
- Typography matches existing app styles — no special reading-mode treatment
- Edit mode mirrors the same layout: body editor is primary, properties hidden behind toggle
- The toggle in edit mode expands the existing editable fieldsets (same collapsible fieldsets that currently exist, just collapsed by default)
- Collapse preference is shared per object IRI — if user expanded properties in view mode, they stay expanded after flipping to edit mode (and vice versa)
- Title on the left, controls (properties badge + edit button) grouped on the right — standard toolbar pattern
- Small muted type label (e.g. "Note", "Person", "Concept") displayed next to the title as a chip or muted text
- No modified-date in the header — keep it minimal
- Edit button keeps its current style unchanged — do not modify the 3D flip trigger
- Default state depends on body content: collapsed if body exists (body-first), expanded if body is empty
- Collapse preference stored in localStorage per object IRI — same pattern as existing panel position storage (`sempkm_panel_positions`)
- No bulk reset / "collapse all" feature — per-object only
- If localStorage is cleared, falls back to the body-aware default logic (collapsed if body, expanded if empty)

### Claude's Discretion
- Visual style of the properties badge (pill, chip, button variant — whatever fits the existing design system)
- Exact CSS transition duration and easing for the slide-down animation
- Spacing and padding values within the properties list
- localStorage key naming convention for collapse preferences

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-01 | Object view shows Markdown body by default with properties collapsed; user can reveal/collapse properties with one click; preference persists per object IRI | All research findings directly support this: template restructuring pattern (body first), properties badge in toolbar, localStorage per-IRI persistence, CSS slide transition |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | (existing) | Server-side template rendering | Already used for all templates; `object_tab.html`, `object_read.html`, `object_form.html` |
| htmx | (existing) | DOM updates without full-page reloads | Already used for object loading, form submission |
| CSS transitions | native | Smooth slide-down animation for properties panel | No library needed; `max-height` or `grid-template-rows` transition |
| localStorage | native | Per-object collapse preference persistence | Already used extensively: `sempkm_pane_sizes`, `sempkm_panel_positions`, `sempkm_fts_fuzzy`, `sempkm_workspace_layout_dv` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Lucide icons | (existing CDN) | Optional icon for the properties badge toggle | If a chevron or icon is desired alongside the "N properties" text |

### Alternatives Considered
None — this is pure template/CSS/JS restructuring within the existing stack. No new dependencies needed.

## Architecture Patterns

### Current Object Tab Structure (Before)
```
object_tab.html
├── .object-toolbar                    ← fixed header
│   ├── .object-toolbar-title          ← object label
│   ├── .object-toolbar-type           ← type chip (e.g. "Note")
│   └── .object-toolbar-actions        ← Edit + Save buttons
├── .object-flip-container             ← 3D flip wrapper
│   └── .object-flip-inner
│       ├── .object-face-read          ← READ FACE
│       │   └── object_read.html
│       │       ├── <details open>     ← properties (VISIBLE by default)
│       │       │   └── .property-table
│       │       └── .markdown-body     ← body (below properties)
│       └── .object-face-edit          ← EDIT FACE
│           └── .object-split (Split.js vertical)
│               ├── .object-form-section  ← properties form (TOP, always visible)
│               └── .object-editor-section ← body editor (BOTTOM)
```

### Target Object Tab Structure (After)
```
object_tab.html
├── .object-toolbar                         ← fixed header (UNCHANGED position)
│   ├── .object-toolbar-title               ← object label (LEFT)
│   ├── .object-toolbar-type                ← type chip (LEFT, next to title)
│   └── .object-toolbar-actions             ← properties badge + Edit + Save (RIGHT)
│       ├── .properties-toggle-badge        ← NEW: "5 properties" clickable badge
│       ├── .mode-toggle                    ← Edit/Cancel button (UNCHANGED)
│       └── .btn-save                       ← Save button (UNCHANGED)
├── .object-flip-container                  ← 3D flip (UNCHANGED mechanics)
│   └── .object-flip-inner
│       ├── .object-face-read               ← READ FACE (restructured)
│       │   ├── .properties-collapsible     ← NEW: slide-down container
│       │   │   └── .property-table         ← existing property grid (moved inside)
│       │   └── .object-read-body           ← body area (NOW PRIMARY, scrolls)
│       │       ├── .markdown-body          ← rendered markdown
│       │       └── .body-placeholder       ← "No content" (when empty)
│       └── .object-face-edit               ← EDIT FACE (restructured)
│           ├── .properties-collapsible     ← NEW: slide-down container
│           │   └── .object-form-section    ← existing form fieldsets (moved inside)
│           └── .object-editor-section      ← body editor (NOW PRIMARY)
```

### Pattern 1: Properties Toggle Badge
**What:** A clickable badge/pill in the toolbar that shows "N properties" and toggles the properties section open/closed.
**When to use:** Both read and edit faces share the same toggle mechanism.
**Example:**
```html
<!-- In object_tab.html toolbar -->
<button class="btn btn-sm properties-toggle-badge"
        id="props-toggle-{{ safe_id }}"
        onclick="toggleProperties('{{ safe_id }}', '{{ object_iri }}')"
        title="Toggle properties">
  {{ property_count }} properties
</button>
```

**Design recommendation:** Style as a subtle pill matching `.object-toolbar-type` (the existing type chip). Use `border-radius: 10px`, muted background, small font. Add a chevron indicator (CSS `::after` or inline Lucide icon) to signal expandability. Active/expanded state gets a slightly different background.

### Pattern 2: CSS Slide-Down Transition
**What:** Smooth expand/collapse animation for the properties section.
**When to use:** When the properties badge is clicked.
**Example:**
```css
/* Collapsible container — uses grid row transition for smooth animation */
.properties-collapsible {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 0.25s ease-out;
    overflow: hidden;
}

.properties-collapsible.expanded {
    grid-template-rows: 1fr;
}

.properties-collapsible > .properties-inner {
    min-height: 0;
    overflow: hidden;
}
```

**Why `grid-template-rows` over `max-height`:** The `max-height` trick requires guessing a maximum value (e.g., `1000px`) and causes animation timing issues when the actual height differs. The `grid-template-rows: 0fr → 1fr` pattern animates to the natural content height without hardcoding values. This is supported in all modern browsers (Chrome 107+, Firefox 107+, Safari 16.4+).

**Alternative (simpler but less smooth):** Use JavaScript to measure `scrollHeight` and set `max-height` explicitly. Works everywhere but requires measurement on each toggle.

### Pattern 3: localStorage Per-Object Preference
**What:** Store collapse/expand state per object IRI in localStorage.
**When to use:** On every toggle action and on object load.
**Example:**
```javascript
var PROPS_PREF_KEY = 'sempkm_props_collapsed';

function getPropsPreference(objectIri) {
    try {
        var data = JSON.parse(localStorage.getItem(PROPS_PREF_KEY) || '{}');
        return data[objectIri]; // true = collapsed, false = expanded, undefined = no pref
    } catch (e) { return undefined; }
}

function setPropsPreference(objectIri, collapsed) {
    try {
        var data = JSON.parse(localStorage.getItem(PROPS_PREF_KEY) || '{}');
        data[objectIri] = collapsed;
        localStorage.setItem(PROPS_PREF_KEY, JSON.stringify(data));
    } catch (e) {}
}

function getDefaultState(hasBody) {
    return hasBody; // collapsed=true when body exists, collapsed=false when empty
}
```

**Key naming recommendation:** `sempkm_props_collapsed` — follows existing `sempkm_` namespace convention. Value is a JSON object mapping IRI strings to boolean (true = collapsed). This is consistent with `sempkm_panel_positions` which stores a JSON object.

**Storage growth concern:** Over time, this object can accumulate many IRIs. Consider pruning entries for objects that no longer exist, but this is LOW priority and can be deferred (localStorage can handle tens of thousands of keys comfortably).

### Pattern 4: Scroll Layout with Fixed Header
**What:** The toolbar stays fixed at the top of the object tab. The properties collapsible and body content scroll together beneath it.
**When to use:** This is the target layout for the object tab.
**Example:**
```css
.object-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.object-toolbar {
    /* Already position/style is correct — flexbox row, border-bottom */
    flex-shrink: 0; /* Ensure toolbar never shrinks */
}

.object-flip-container {
    flex: 1;
    min-height: 0; /* Allow flex child to shrink below content size */
    overflow: hidden;
}

/* Read face: properties + body scroll together */
.object-face-read .object-read-view {
    height: 100%;
    overflow-y: auto;
}
```

### Pattern 5: Edit Mode Layout Change
**What:** In edit mode, properties form and body editor are currently in a vertical Split.js arrangement. This changes to properties in a collapsible section above the body editor.
**Critical consideration:** The existing Split.js vertical split between form and editor sections needs to be removed. The body editor should fill the remaining space after the (possibly collapsed) properties section.
**Example:**
```css
/* Edit face layout: collapsible props + editor */
.object-face-edit {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.object-face-edit .properties-collapsible {
    flex-shrink: 0; /* Properties don't grow/shrink with remaining space */
}

.object-editor-section {
    flex: 1;
    min-height: 0;
    overflow: hidden;
}
```

### Anti-Patterns to Avoid
- **Do NOT use `display: none` for collapse:** It causes layout reflow and cannot be animated. Use the grid or max-height transition instead.
- **Do NOT break the 3D flip mechanics:** The `.object-flip-inner`, `.flipped` class, `backface-visibility`, and face visibility toggling at the 300ms midpoint are all critical. Do not change the flip container structure or timing.
- **Do NOT duplicate toggle state:** Both faces share ONE preference per object IRI. Do not store separate read/edit preferences.
- **Do NOT add new backend endpoints:** Property count can be computed in the template from the existing `form.properties` and `values` context variables.
- **Do NOT use the `<details>` element for the new toggle:** The existing `<details class="read-properties-section" open>` in `object_read.html` should be replaced. `<details>` cannot be smoothly animated with CSS alone and doesn't support the toolbar-button-controlled toggle pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Smooth collapse animation | Custom JS height measurement + requestAnimationFrame | CSS `grid-template-rows` transition | Browser handles animation, zero JS needed for the animation itself |
| Per-object preference storage | Custom IndexedDB wrapper | localStorage JSON object | Matches existing codebase pattern, trivial data size |
| Property counting | New backend API endpoint | Jinja2 template loop counter | `form.properties` and `values` are already in template context |

**Key insight:** Everything needed for this phase is already available in the template context and existing CSS/JS patterns. The challenge is restructuring, not building new capabilities.

## Common Pitfalls

### Pitfall 1: Breaking E2E Test Selectors
**What goes wrong:** Tests rely on specific CSS selectors like `.object-tab`, `.object-read-view`, `.property-table`, `.ref-pill`, `.mode-toggle`, `.object-toolbar-title`, `.object-toolbar-type`, `[data-testid="object-form"]`, `.form-success`, `.object-form-container`.
**Why it happens:** Template restructuring moves or renames elements.
**How to avoid:** Preserve all existing class names and data-testid attributes. The read-only property table (`.property-table`, `.property-row`, `.ref-pill`) must remain in the DOM — just inside a different container. The form (`.object-form-container`, `#object-form`) must remain with the same selectors.
**Warning signs:** E2E tests failing on `.object-tab` or `.ref-pill` visibility checks.

### Pitfall 2: Flip Animation Breaking with Layout Changes
**What goes wrong:** The CSS 3D flip requires `position: absolute` faces inside a `position: relative` container with `transform-style: preserve-3d`. Adding content above or below the flip container, or changing the face structure, can break the flip.
**Why it happens:** The faces are absolutely positioned and need explicit height. The flip container uses `flex: 1` to fill remaining space.
**How to avoid:** Keep the flip container structure unchanged. Only modify the **content inside** each face. The `.object-flip-container`, `.object-flip-inner`, `.object-face-read`, `.object-face-edit` CSS must remain as-is (lines 1287-1331 in workspace.css).
**Warning signs:** Faces overlapping, flip animation showing both sides, or faces having zero height.

### Pitfall 3: Split.js Conflict in Edit Mode
**What goes wrong:** The current edit face uses Split.js for a vertical form/editor split. If the properties section becomes collapsible, Split.js must be removed or reconfigured.
**Why it happens:** Split.js creates gutter elements and manages sizes via inline styles. A collapsible properties section would conflict with Split.js size management.
**How to avoid:** Remove the Split.js vertical split from the edit face entirely. Replace with flex layout where properties collapse and editor fills remaining space. The `initVerticalSplit()` function in `object_tab.html` (line 219) and the `toggleEditorMaximize()` function need to be updated or removed.
**Warning signs:** Gutter visible when properties are collapsed, editor not filling available space.

### Pitfall 4: Scroll Context Loss
**What goes wrong:** When properties expand/collapse in the read view, the scroll position of the body content jumps.
**Why it happens:** The body area's scroll container changes height when the properties panel slides in/out.
**How to avoid:** Either accept the scroll jump (natural behavior) or save/restore `scrollTop` before/after toggle. The natural behavior is acceptable for most cases.

### Pitfall 5: Empty Body Detection
**What goes wrong:** The template must detect whether the object has a body to determine the default collapse state (collapsed if body exists, expanded if empty).
**Why it happens:** `body_text` can be an empty string, None, or whitespace-only.
**How to avoid:** Use `body_text and body_text.strip()` in Jinja2 for truthiness check. Pass a `has_body` boolean to JavaScript via a data attribute for the runtime default logic.
**Warning signs:** Properties always collapsed even for empty-body objects, or always expanded for objects with body.

### Pitfall 6: Toggle Shared Between Faces
**What goes wrong:** User expands properties in read mode, flips to edit, and properties are collapsed there (or vice versa).
**Why it happens:** Each face has its own DOM; toggling in one face doesn't automatically update the other.
**How to avoid:** The toggle function must update BOTH faces when triggered. Since the inactive face is hidden (visibility: hidden), updating its DOM is safe. On flip transition, read the preference from localStorage and apply to the newly visible face. The `toggleObjectMode` function (workspace.js line 525) already refreshes the read face from the server on flip-back — this refresh should respect the current preference.
**Warning signs:** Inconsistent property visibility after flipping.

## Code Examples

### Example 1: Property Count Computation in Template
```jinja2
{# Count properties that have values (for badge text) #}
{% set ns_count = namespace(n=0) %}
{% if form %}
  {% for prop in form.properties %}
    {% set vals = values.get(prop.path, []) %}
    {% if vals and prop.path != body_property_path %}
      {% set ns_count.n = ns_count.n + 1 %}
    {% endif %}
  {% endfor %}
{% endif %}
{% set property_count = ns_count.n %}
```

### Example 2: Properties Badge in Toolbar
```html
<div class="object-toolbar-actions">
    {% if property_count > 0 %}
    <button class="btn btn-sm properties-toggle-badge"
            id="props-toggle-{{ safe_id }}"
            data-object-iri="{{ object_iri }}"
            data-has-body="{{ 'true' if body_text and body_text.strip() else 'false' }}"
            data-property-count="{{ property_count }}"
            onclick="toggleProperties('{{ safe_id }}', '{{ object_iri }}')"
            title="Toggle properties">
        <span class="props-badge-icon">&#9656;</span>
        {{ property_count }} propert{{ 'y' if property_count == 1 else 'ies' }}
    </button>
    {% endif %}
    <button class="btn btn-sm mode-toggle" ...> Edit </button>
    <button class="btn btn-sm btn-save" ...> Save </button>
</div>
```

### Example 3: Read Face Restructured
```html
<div class="object-read-view">
  {# Properties collapsible section #}
  {% if ns.any_prop %}
  <div class="properties-collapsible" id="read-props-{{ safe_id }}">
    <div class="properties-inner">
      <div class="property-table">
        {# ... existing property rows unchanged ... #}
      </div>
    </div>
  </div>
  {% endif %}

  {# Body content (primary) #}
  {% if body_text and body_text.strip() %}
  <div class="markdown-body" id="md-rendered-{{ safe_id }}">
    <div class="markdown-loading">Rendering...</div>
  </div>
  {% else %}
  <div class="body-placeholder">No content</div>
  {% endif %}
</div>
```

### Example 4: Toggle Function
```javascript
function toggleProperties(safeId, objectIri) {
    var readProps = document.getElementById('read-props-' + safeId);
    var editProps = document.getElementById('edit-props-' + safeId);
    var badge = document.getElementById('props-toggle-' + safeId);

    // Determine current state
    var isExpanded = readProps && readProps.classList.contains('expanded');
    var newCollapsed = isExpanded; // toggling: if expanded, now collapse

    // Update both faces
    [readProps, editProps].forEach(function(el) {
        if (!el) return;
        if (newCollapsed) {
            el.classList.remove('expanded');
        } else {
            el.classList.add('expanded');
        }
    });

    // Update badge icon
    if (badge) {
        var icon = badge.querySelector('.props-badge-icon');
        if (icon) icon.textContent = newCollapsed ? '\u25B6' : '\u25BC';
    }

    // Persist preference
    setPropsPreference(objectIri, newCollapsed);
}
```

### Example 5: Initialize Properties State on Load
```javascript
// Called after htmx loads object_tab.html content
function initPropertiesState(safeId, objectIri, hasBody) {
    var pref = getPropsPreference(objectIri);
    var collapsed;

    if (pref !== undefined) {
        collapsed = pref; // User has an explicit preference
    } else {
        collapsed = hasBody; // Default: collapsed if body exists
    }

    if (!collapsed) {
        // Expand without animation on initial load
        var readProps = document.getElementById('read-props-' + safeId);
        var editProps = document.getElementById('edit-props-' + safeId);
        [readProps, editProps].forEach(function(el) {
            if (el) el.classList.add('expanded');
        });
    }

    // Update badge icon
    var badge = document.getElementById('props-toggle-' + safeId);
    if (badge) {
        var icon = badge.querySelector('.props-badge-icon');
        if (icon) icon.textContent = collapsed ? '\u25B6' : '\u25BC';
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<details>` HTML element for collapse | CSS `grid-template-rows` transition | ~2023 (Safari 16.4 support) | Smooth animation without JavaScript measurement |
| `max-height` hack for CSS collapse | `grid-template-rows: 0fr → 1fr` | Same | No guessing max values, correct animation timing |
| jQuery `.slideToggle()` | Pure CSS transitions | Long ago | Zero JS dependency for animation |

**Deprecated/outdated:**
- The current `<details class="read-properties-section" open>` in `object_read.html` uses a native HTML disclosure widget. This works but cannot be smoothly animated and doesn't support external button control (the badge in the toolbar). It should be replaced.

## Open Questions

1. **Editor maximize button behavior after Split.js removal**
   - What we know: The edit face currently has a "maximize editor" button (`toggleEditorMaximize`) that collapses the form section to 0% via Split.js `setSizes([0, 100])`.
   - What's unclear: Should this button be retained, repurposed, or removed? With properties already collapsed by default, maximizing is less necessary.
   - Recommendation: Remove the maximize button. The collapsible properties section replaces its function. If properties are collapsed, the editor is already "maximized." If expanded, user can collapse them with the badge. This simplifies the edit face significantly.

2. **Property count for objects without a SHACL form**
   - What we know: When `form` is None, the template shows "No form schema available." These objects have no structured properties to count.
   - What's unclear: Should the properties badge still appear?
   - Recommendation: Hide the badge entirely when `property_count == 0` or `form is None`. The badge is meaningless without properties to show.

3. **Read face refresh after flip-back**
   - What we know: `toggleObjectMode` fetches fresh HTML from the server when flipping from edit back to read mode (line 551-572 in workspace.js). This replaces the entire read face innerHTML.
   - What's unclear: After refresh, the properties state needs to be re-applied based on the localStorage preference.
   - Recommendation: After the read face refresh completes (in the `.then()` callback), call `initPropertiesState()` to reapply the saved preference. This is a small addition to the existing refresh logic.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all files listed below — this is the authoritative source for all architecture claims
  - `backend/app/templates/browser/object_tab.html` — flip container, toolbar, edit face structure
  - `backend/app/templates/browser/object_read.html` — read face with properties and body
  - `backend/app/templates/forms/object_form.html` — edit form with collapsible fieldsets
  - `backend/app/templates/forms/_group.html` — collapsible `<details>` groups
  - `backend/app/browser/router.py` (lines 492-634) — `get_object` endpoint, template context
  - `frontend/static/css/workspace.css` — all object tab styling (flip, toolbar, properties, body)
  - `frontend/static/js/workspace.js` — `toggleObjectMode`, `saveCurrentObject`, `markDirty`
  - `frontend/static/js/workspace-layout.js` — dockview panel rendering, htmx loading
  - `frontend/static/js/markdown-render.js` — `renderMarkdownBody` function
  - `e2e/tests/01-objects/edit-object-ui.spec.ts` — E2E selectors that must be preserved

### Secondary (MEDIUM confidence)
- CSS `grid-template-rows` animation: Well-documented CSS feature, supported since Safari 16.4 (March 2023), Chrome 107, Firefox 107. Verified against MDN documentation knowledge.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries, all existing patterns
- Architecture: HIGH - Full codebase inspection completed, all files read and understood
- Pitfalls: HIGH - E2E test selectors verified, flip mechanics understood, Split.js conflict identified

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable — no external dependencies, pure codebase refactoring)