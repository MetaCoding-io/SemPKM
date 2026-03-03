# Phase 32: Carousel Views and View Bug Fixes - Research

**Researched:** 2026-03-03
**Domain:** Frontend tab bar UI, htmx partial rendering, localStorage persistence, CSS accordion
**Confidence:** HIGH

## Summary

Phase 32 adds a carousel tab bar to the object view so users can switch between manifest-declared views (table, cards, graph) for a given type. It also fixes the concept cards group-by bug and removes the broken view switch buttons from the old view toolbar. The work is entirely frontend-focused with a small backend change to pass view spec metadata into the object template context.

The existing `ViewSpecService.get_view_specs_for_type(type_iri)` already returns all views for a type -- this is used in the view toolbar today. The key architectural change is that view specs need to be accessible from the **object tab template** (not just the standalone view pages), and the view body area within the object tab needs to load view content via htmx. The broken view switch buttons (`switchViewType()` in `view_toolbar.html`) target `#editor-area` which does not exist in the dockview world -- all view rendering goes into `.group-editor-area` containers managed by dockview panels.

**Primary recommendation:** Add a new backend endpoint or extend the existing object endpoint to pass view specs for the object's type into `object_tab.html`. Render the carousel tab bar in the object template between the toolbar and the flip container. Load view content via htmx into a designated view body area. Remove the old `view_toolbar.html` view-type-switcher entirely.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Tab bar position:** Directly above the view body, below the object header (from Phase 31)
- **Active tab indicator:** Bottom border accent (colored bottom border on active tab)
- **Conditional rendering:** Only render the tab bar when the type has multiple views in the manifest; single-view types show no tab bar
- **Tab labels:** Prettified display names derived from manifest view keys (e.g., `cards_view` -> "Cards View")
- **View switching:** Instant swap -- no animation or transition when clicking a tab
- **Loading state:** While a view fetches server data (e.g., graph view loading relationships), show a spinner in the view body area; tab bar stays interactive
- **Default view:** First view listed in the manifest (manifest order = priority)
- **Remove old buttons:** Remove the old broken graph/card/table view switch buttons and their code entirely -- the carousel tab bar replaces them
- **Cards group-by:** Collapsible accordion sections -- each group is a collapsible section with a header
- **Accordion defaults:** All groups expanded by default; users can collapse groups they don't need
- **Ungrouped:** Objects missing the group-by predicate value appear in an "Ungrouped" section at the bottom
- **Group headers:** Show a count of cards in the group (e.g., "Philosophy (5)")
- **Persistence scope:** Active tab selection persists per type IRI (not per individual object)
- **Persistence storage:** localStorage, consistent with existing `sempkm_panel_positions` pattern
- **Fallback:** If the manifest changes and the saved view no longer exists, fall back to the first available view silently (no error/toast)
- **Accordion state:** Accordion collapse/expand state does NOT persist -- resets to all-expanded each session

### Claude's Discretion
- Exact tab bar styling, colors, spacing, and typography
- Spinner implementation details
- localStorage key naming convention
- Accordion expand/collapse animation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-02 | Object types with multiple manifest-declared views show a tab bar above the view body; user can switch between views; active view persists per type IRI | Carousel tab bar architecture, htmx view loading, localStorage persistence pattern |
| BUG-01 | User sees correctly grouped concept cards when group-by is applied | Cards group-by htmx target fix (currently targets non-existent `#editor-area`), accordion redesign |
| BUG-03 | Broken view switch buttons are removed from the object view (replaced by VIEW-02 carousel tab bar) | Old `switchViewType()` and `.view-type-switcher` removal, new carousel tab bar as replacement |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| htmx | (existing CDN) | Partial HTML fetching for view content | Already the project's DOM update mechanism; all views use htmx partials |
| dockview-core | 4.11.0 | Panel/tab management for workspace | Already integrated in Phase 30; carousel bar lives inside dockview panels |
| Jinja2 | (existing) | Server-side template rendering | Backend renders view HTML partials; carousel bar is a Jinja2 template include |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| localStorage API | Browser native | Persist active carousel tab per type IRI | View selection memory across sessions |
| CSS grid-template-rows | Browser native | Accordion collapse animation | Smooth expand/collapse for card groups (matches Phase 31 properties pattern) |

### Alternatives Considered
None -- this phase uses only existing project dependencies. No new libraries needed.

## Architecture Patterns

### Pattern 1: Carousel Tab Bar in Object Template
**What:** A horizontal tab bar rendered between the object toolbar and the flip container in `object_tab.html`. Each tab corresponds to a view spec from the manifest for the object's type. Clicking a tab loads the view content via htmx into a dedicated view body area below the tab bar.

**When to use:** When the object's type has 2+ view specs in the manifest.

**How it works:**
1. Backend `get_object()` endpoint in `browser/router.py` already resolves `type_iris[0]` -- extend it to also fetch `ViewSpecService.get_view_specs_for_type(type_iri)` and pass the list into the template context
2. `object_tab.html` renders a new `carousel-tab-bar` div between the toolbar and the flip container (only if `view_specs|length > 1`)
3. Each tab is a button with `data-spec-iri`, `data-renderer-type`, and the prettified label
4. Clicking a tab: JS function loads `/browser/views/{renderer_type}/{spec_iri}` via htmx into a view body container within the object tab
5. The flip container (read/edit object view) becomes the default "Object" pseudo-tab or is shown when no carousel view is active

**Key decision:** The carousel tab bar replaces both the old `.view-type-switcher` in `view_toolbar.html` AND determines what content appears in the object view body area. The read/edit flip container IS the default view for the object -- carousel tabs switch to table/card/graph views of the same type.

Wait -- re-reading the requirements more carefully: VIEW-02 says "Object types with multiple manifest-declared views show a tab bar above the **view body**". The views here are the manifest-declared views (table, card, graph views for the type), not the object's read/edit view. The carousel tab bar appears when viewing type-level browse views (tables, cards, graphs), not on individual object read views.

Let me reconsider: Looking at the manifest, each type has table, card, and graph view specs. The "object view" (object_tab.html) is for viewing a single object. The "carousel" is for when you're browsing a **type** (e.g., all Concepts) -- you see a tab bar letting you switch between Table, Cards, and Graph views of that type.

Actually, re-reading the success criteria more carefully:
- "For an object type with multiple views declared in the manifest, a tab bar appears above the view body listing each view by name"
- "The broken graph/card/table view switch buttons are absent from the **object view**"

The old `.view-type-switcher` currently appears in the view toolbar (table_view, cards_view, graph_view). The carousel tab bar replaces it. This is a **view-level** feature, not an individual object feature. The tab bar appears when browsing type views.

### Revised Pattern 1: Carousel Tab Bar on Type Views
**What:** When a user opens a type view (table/cards/graph) in a dockview panel, a tab bar appears above the view body listing all available views for that type. Clicking a tab switches the view content instantly via htmx.

**Structure in the dockview panel:**
```
+---------------------------------------+
|  Carousel Tab Bar                     |  <- new, replaces view-type-switcher
|  [Table] [Cards] [Graph]             |
+---------------------------------------+
|  View Body (table/cards/graph)        |  <- loaded via htmx
|                                       |
+---------------------------------------+
```

**Implementation path:**
1. Create a new template `carousel_tab_bar.html` that renders tabs from `all_specs` (already passed to every view template)
2. Include it at the top of each view template instead of the old `view_toolbar.html` `.view-type-switcher` section
3. Active tab has a bottom-border accent
4. Clicking a tab triggers htmx load of the new view into `closest .group-editor-area`
5. Store active tab per type IRI in localStorage

**Source:** Codebase analysis of `view_toolbar.html`, `cards_view.html`, `table_view.html`, `graph_view.html`

### Pattern 2: htmx Target Fix for Dockview
**What:** All view templates currently target `#editor-area` for htmx swaps. This ID does not exist in the dockview world -- each panel's content area is a `.group-editor-area` div. The fix is to change all `hx-target="#editor-area"` to `hx-target="closest .group-editor-area"`.

**Why it matters:** This is the root cause of both BUG-01 (cards group-by dropdown doesn't work) and BUG-03 (view switch buttons are broken). The htmx requests fire but can't find the target element, so the response is silently dropped.

**Files affected:**
- `backend/app/templates/browser/view_toolbar.html` -- filter input `hx-target`, switchViewType JS function
- `backend/app/templates/browser/cards_view.html` -- group-by select `hx-target`
- `backend/app/templates/browser/table_view.html` -- sort header `hx-target`
- `backend/app/templates/browser/pagination.html` -- all pagination `hx-target` references
- `backend/app/templates/browser/search_suggestions.html` -- suggestion click

**Source:** Codebase analysis; confirmed by searching for `#editor-area` in templates

### Pattern 3: Accordion Group Headers for Cards
**What:** Replace the current flat `h3.card-group-header` with collapsible accordion sections. Each group header is a clickable bar that expands/collapses its card grid.

**CSS approach:** Use `grid-template-rows: 0fr/1fr` transition (same pattern as Phase 31 properties collapsible):
```css
.card-group-body {
  display: grid;
  grid-template-rows: 1fr;
  transition: grid-template-rows 0.25s ease;
}
.card-group-body.collapsed {
  grid-template-rows: 0fr;
}
.card-group-body > .card-grid {
  overflow: hidden;
}
```

**Header structure:**
```html
<div class="card-group-header" onclick="this.nextElementSibling.classList.toggle('collapsed'); ...">
  <span class="card-group-chevron">▸</span>
  Philosophy (5)
</div>
<div class="card-group-body">
  <div class="card-grid">...</div>
</div>
```

**Source:** Phase 31 decision (31-01: CSS grid-template-rows 0fr/1fr for smooth properties slide animation)

### Pattern 4: localStorage Persistence for Active View Tab
**What:** Store the user's last-selected carousel tab per type IRI in localStorage.

**Key convention:** `sempkm_carousel_view` (follows existing `sempkm_` namespace pattern per project conventions)

**Data structure:**
```json
{
  "urn:sempkm:model:basic-pkm:Concept": "urn:sempkm:model:basic-pkm:view-concept-card",
  "urn:sempkm:model:basic-pkm:Project": "urn:sempkm:model:basic-pkm:view-project-table"
}
```

**Behavior:**
- On view load, check `localStorage[sempkm_carousel_view][typeIri]`
- If saved spec_iri exists in current `all_specs`, activate that tab
- If saved spec_iri not found (manifest changed), fall back to first spec silently
- On tab click, update the stored value

**Source:** Existing patterns: `sempkm_fts_fuzzy`, `sempkm_props_collapsed`, `sempkm_panel_positions`

### Anti-Patterns to Avoid
- **Targeting `#editor-area`:** This ID does not exist in dockview panels. Always use `closest .group-editor-area` for htmx targets within view content.
- **Full page reload for view switch:** Views must load via htmx partial into the existing panel, not by opening a new dockview panel.
- **Animating view transitions:** User decision explicitly says "instant swap -- no animation or transition".
- **Persisting accordion state:** User decision explicitly says accordion collapse/expand state does NOT persist.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Smooth accordion animation | JavaScript height calculation/animation | CSS `grid-template-rows: 0fr/1fr` transition | Zero JS needed for smooth expand/collapse; already proven in Phase 31 |
| View loading with progress | Custom fetch + DOM manipulation | htmx `hx-get` + `hx-indicator` | htmx has built-in loading indicator support; consistent with project patterns |
| Tab persistence across sessions | Custom event system | localStorage read/write | Simple, synchronous, already used throughout the project |

**Key insight:** The entire carousel implementation is achievable with existing htmx + CSS patterns already in the codebase. No new dependencies, no complex state management. The main work is structural -- moving view-switching from the standalone view pages into a shared carousel bar template and fixing the dockview htmx target issue.

## Common Pitfalls

### Pitfall 1: Stale htmx Target References
**What goes wrong:** View templates hardcode `hx-target="#editor-area"` which does not exist in dockview panels. htmx silently drops responses when the target element is not found.
**Why it happens:** The view templates were written before dockview migration (Phase 30). The old layout had a single `#editor-area` div; dockview creates multiple `.group-editor-area` containers.
**How to avoid:** Audit ALL htmx target attributes in view templates. Replace `#editor-area` with `closest .group-editor-area`. For the `switchViewType()` JS function, use `htmx.ajax('GET', url, { target: el.closest('.group-editor-area'), swap: 'innerHTML' })`.
**Warning signs:** View loads but filter/sort/pagination/group-by changes don't update the UI.

### Pitfall 2: Carousel Tab Bar vs. Object View Confusion
**What goes wrong:** Implementing the carousel tab bar on individual object views (object_tab.html) instead of on type-level browse views.
**Why it happens:** The phase description says "object types with multiple manifest-declared views" which could be misread as "when viewing an object".
**How to avoid:** The carousel tab bar replaces the `.view-type-switcher` in `view_toolbar.html`. It appears on type-level browse views (table, cards, graph), not on individual object read/edit views. Individual object views already have the read/edit flip toggle.
**Warning signs:** Tab bar appearing on individual Note or Project read views where it makes no sense.

### Pitfall 3: View Content Loading Replaces Carousel Bar
**What goes wrong:** htmx swap replaces the entire panel content including the carousel tab bar, so after clicking a tab the bar disappears.
**Why it happens:** If the carousel tab bar is part of the htmx swap target, the entire content (including the bar) gets replaced.
**How to avoid:** Structure the template so the carousel tab bar is OUTSIDE the htmx swap target. Use a two-container pattern:
```html
<div class="carousel-tab-bar">...</div>        <!-- stays -->
<div class="carousel-view-body">...</div>       <!-- htmx swaps here -->
```
The htmx target should be `.carousel-view-body`, not the parent `.group-editor-area`.
**Warning signs:** Tab bar disappears after clicking a tab.

### Pitfall 4: Graph View Cytoscape Container Visibility
**What goes wrong:** Graph view loaded into a carousel tab but Cytoscape.js fails because the container is not visible when init runs.
**Why it happens:** Per existing research (view_router.py docstring): "container must be visible before Cytoscape init". If the carousel switches to graph view but the container is hidden or zero-height during init, Cytoscape renders nothing.
**How to avoid:** The graph view already handles this with a separate `/data` endpoint loaded after DOM is ready. Ensure the carousel view body container has explicit height before loading graph view content.
**Warning signs:** Empty graph view when switching to it via carousel tab.

### Pitfall 5: Prettified Label Generation
**What goes wrong:** View spec labels from the manifest are already human-readable (e.g., "Projects Table", "Concepts Cards"). The decision says "prettified display names derived from manifest view keys" but the view specs already have `rdfs:label` values.
**Why it happens:** The CONTEXT.md mentions prettifying keys like `cards_view` -> "Cards View", but the actual view specs have proper labels.
**How to avoid:** Use the existing `spec.label` directly. The labels are already good: "Projects Table", "Projects Cards", "Projects Graph". For the tab bar, consider showing just the renderer type portion (e.g., "Table", "Cards", "Graph") since the type name is already visible in the view toolbar.
**Warning signs:** Redundant labels like "Projects Table" when browsing Projects.

### Pitfall 6: Lucide Icons in Flex Tab Bar
**What goes wrong:** If Lucide icons are used in the carousel tab buttons (which are flex containers), the SVG shrinks to 0px width.
**Why it happens:** CLAUDE.md documented pitfall -- SVGs need `flex-shrink: 0` in flex containers.
**How to avoid:** Follow CLAUDE.md rules: size icons via CSS, add `flex-shrink: 0`, use `stroke: currentColor`.
**Warning signs:** Invisible icons in tab buttons.

## Code Examples

### Example 1: Carousel Tab Bar Template (carousel_tab_bar.html)
```html
{# Carousel tab bar: view switching for types with multiple manifest views.
   Only rendered when all_specs|length > 1.
   Context: all_specs (list[ViewSpec]), spec (current ViewSpec), type_iri, type_label #}

{% if all_specs|length > 1 %}
<div class="carousel-tab-bar" data-type-iri="{{ type_iri }}">
    {% for s in all_specs %}
    <button class="carousel-tab{% if s.spec_iri == spec.spec_iri %} active{% endif %}"
            data-spec-iri="{{ s.spec_iri }}"
            data-renderer-type="{{ s.renderer_type }}"
            onclick="switchCarouselView(this, '{{ s.spec_iri }}', '{{ s.renderer_type }}', '{{ type_iri }}')">
        {{ s.label | replace(type_label ~ ' ', '') }}
    </button>
    {% endfor %}
</div>
{% endif %}
```

### Example 2: View Switching JavaScript
```javascript
function switchCarouselView(tabEl, specIri, rendererType, typeIri) {
    // Update active tab styling
    var bar = tabEl.closest('.carousel-tab-bar');
    bar.querySelectorAll('.carousel-tab').forEach(function(t) {
        t.classList.remove('active');
    });
    tabEl.classList.add('active');

    // Persist selection per type IRI
    try {
        var data = JSON.parse(localStorage.getItem('sempkm_carousel_view') || '{}');
        data[typeIri] = specIri;
        localStorage.setItem('sempkm_carousel_view', JSON.stringify(data));
    } catch (e) {}

    // Load view content via htmx
    var url = '/browser/views/' + rendererType + '/' + encodeURIComponent(specIri);
    var viewBody = bar.nextElementSibling; // .carousel-view-body
    htmx.ajax('GET', url, { target: viewBody, swap: 'innerHTML' });
}
```

### Example 3: Accordion Card Group Header
```html
<div class="card-group-section">
    <div class="card-group-header" onclick="toggleCardGroup(this)">
        <span class="card-group-chevron">&#9656;</span>
        <span class="card-group-label">{{ group.group_label }}</span>
        <span class="card-group-count">({{ group.cards|length }})</span>
    </div>
    <div class="card-group-body">
        <div class="card-grid">
            {% for card in group.cards %}
            {{ render_card(card) }}
            {% endfor %}
        </div>
    </div>
</div>
```

### Example 4: Accordion CSS (grid-template-rows pattern from Phase 31)
```css
.card-group-body {
    display: grid;
    grid-template-rows: 1fr;
    transition: grid-template-rows 0.25s ease;
}
.card-group-body.collapsed {
    grid-template-rows: 0fr;
}
.card-group-body > .card-grid {
    overflow: hidden;
}
.card-group-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    cursor: pointer;
    user-select: none;
    font-weight: 600;
}
.card-group-chevron {
    transition: transform 0.2s;
    display: inline-block;
}
.card-group-body.collapsed + .card-group-header .card-group-chevron,
.card-group-header.collapsed .card-group-chevron {
    transform: rotate(0deg);
}
```

### Example 5: htmx Target Fix
```html
<!-- Before (broken in dockview): -->
<select hx-target="#editor-area" ...>

<!-- After (works in dockview panels): -->
<select hx-target="closest .group-editor-area" ...>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `#editor-area` single div | `.group-editor-area` per dockview panel | Phase 30 (dockview migration) | All htmx targets in view templates are broken |
| `.view-type-switcher` buttons | Carousel tab bar (this phase) | Phase 32 | Single view-switching affordance, persistent per type |
| Flat card group headers | Collapsible accordion sections | Phase 32 | Better UX for grouped cards |

**Deprecated/outdated:**
- `switchViewType()` function in `view_toolbar.html`: Will be removed, replaced by `switchCarouselView()`
- `.view-type-switcher` CSS class: Will be removed
- `#editor-area` htmx targets in view templates: Must be updated to `closest .group-editor-area`

## Open Questions

1. **Carousel bar placement relative to view toolbar**
   - What we know: The view toolbar has a filter input, column settings button, and the old view-type-switcher. The carousel tab bar replaces the switcher.
   - What's unclear: Should the carousel tab bar be a separate row above the existing toolbar, or should it replace the `.view-toolbar-left` section? Or should the view toolbar be restructured to integrate the carousel?
   - Recommendation: Make the carousel tab bar a separate row above the view toolbar. This keeps the filter/sort controls in their own row and gives the carousel tabs visual prominence. The carousel bar is a structural navigation element; the toolbar is for filtering/configuration within a view.

2. **View content rendering inside carousel vs. standalone**
   - What we know: Currently, view templates (table_view, cards_view, graph_view) include `view_toolbar.html` and render full content. In the carousel model, the tab bar is separate and the view content loads into a body area.
   - What's unclear: Should the view templates continue to include the full toolbar, or should they have a "carousel mode" that strips the toolbar and renders only the view body?
   - Recommendation: Keep view templates as-is but remove the `.view-type-switcher` from `view_toolbar.html`. The carousel tab bar is rendered by a parent template. When view content loads via htmx into `.carousel-view-body`, it includes its own filter/toolbar but without the switcher buttons. This avoids duplicating template logic.

3. **"Ungrouped" section ordering**
   - What we know: User decided objects missing the group-by value go in an "Ungrouped" section at the bottom.
   - What's unclear: The current `ViewSpecService.execute_cards_query()` groups by property value and uses "(No value)" as the group label. Need to rename to "Ungrouped" and ensure it sorts last.
   - Recommendation: Change the backend grouping logic to use "Ungrouped" instead of "(No value)" and sort it to the end of the groups list.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/views/service.py` -- ViewSpecService, get_view_specs_for_type(), execute_cards_query() with group_by
- Codebase analysis: `backend/app/views/router.py` -- view endpoints, all_specs passed to templates
- Codebase analysis: `backend/app/templates/browser/view_toolbar.html` -- current view-type-switcher, switchViewType()
- Codebase analysis: `backend/app/templates/browser/cards_view.html` -- current group-by rendering, hx-target issue
- Codebase analysis: `backend/app/templates/browser/object_tab.html` -- object view structure, Phase 31 layout
- Codebase analysis: `frontend/static/js/workspace-layout.js` -- dockview panel creation, view-panel component
- Codebase analysis: `frontend/static/css/workspace.css` -- object tab CSS, properties-collapsible pattern
- Codebase analysis: `frontend/static/css/views.css` -- view toolbar, card grid, group header styling
- Codebase analysis: `models/basic-pkm/views/basic-pkm.jsonld` -- 12 view specs (3 per type x 4 types)
- Project memory: Phase 31 decisions on CSS grid-template-rows for animations
- Project memory: Dockview theme pitfall and constructor options

### Secondary (MEDIUM confidence)
- CLAUDE.md: Lucide icon flex container pitfall, SVG stroke inheritance rules

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all existing project dependencies, no new libraries
- Architecture: HIGH -- patterns directly derived from codebase analysis of existing view system and dockview integration
- Pitfalls: HIGH -- identified from actual bugs in the codebase (htmx target mismatch confirmed by code review)

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable -- internal project patterns, no external dependency concerns)
