# Phase 39: Edit Form Helptext + Bug Fix Batch - Research

**Researched:** 2026-03-05
**Domain:** SHACL annotation extraction, form template rendering, dockview tab styling
**Confidence:** HIGH

## Summary

This phase has two active implementation tracks: (1) SHACL `sempkm:editHelpText` annotations on both NodeShape (form-level) and PropertyShape (field-level), rendered as collapsible markdown in edit forms; and (2) type-aware accent colors on dockview tabs (BUG-04). All other bugs (BUG-05 through BUG-09) are already fixed and deferred to Phase 40 for E2E verification only.

The helptext implementation requires changes at three layers: SHACL shape data (adding `sempkm:editHelpText` annotations to the basic-pkm model's shapes JSON-LD), backend extraction (extending `ShapesService` and its dataclasses to read the new property), and frontend rendering (form templates and CSS). The accent color track leverages the existing `IconService` pipeline which already reads per-type colors from manifest.yaml and passes them to the frontend via `_tabMeta.typeColor` -- the missing piece is applying that color to the dockview tab's border-bottom CSS.

**Primary recommendation:** Implement helptext as a data+template feature using the existing marked.js pipeline; implement accent colors by using the already-available `_tabMeta.typeColor` to set an inline style or CSS custom property on dockview tab elements.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single property: `sempkm:editHelpText` used on both `sh:NodeShape` (form-level) and `sh:PropertyShape` (field-level)
- Content is full markdown, rendered via marked.js (same pipeline as object body)
- Collapsed by default at both levels; user clicks to expand
- Form-level helptext: collapsible section at top of form, below form title/header, above first field; similar pattern to Phase 31 properties toggle
- Field-level helptext: small `?` icon (Lucide `help-circle`) next to field label, clicking expands helptext inline below field
- All fields on Note NodeShape get field-level helptext as complete example; Note also gets form-level helptext; other shapes get form-level helptext only (minimum)
- Type-aware accent colors: manifest-declared per type, fallback to current teal (`--color-accent`), applied to active tab accent bar only (2px bottom border), inactive tabs remain neutral
- Color palette: Notes=teal, Projects=indigo, Concepts=amber, Persons=rose
- BUG-05 through BUG-09: already fixed, verification only in Phase 40

### Claude's Discretion
- Exact CSS for help-circle icon sizing and positioning
- Collapse/expand animation timing
- Manifest property name and format for type accent color declaration
- How accent color flows from manifest to frontend (CSS custom property, data attribute, inline style, etc.)
- localStorage key for helptext collapse state (if persisted)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HELP-01 | SHACL shapes can declare `sempkm:editHelpText`; edit forms render collapsible markdown below fields | ShapesService dataclass extension, template rendering with marked.js, shapes JSON-LD annotation |
| BUG-04 | Tab accent bar is type-aware (different colors per type) | IconService already provides typeColor via _tabMeta; need CSS application on dockview tabs |
| BUG-05 | Card view borders in light/dark themes | Already fixed -- Phase 40 verification only |
| BUG-06 | Firefox Ctrl+K opens ninja-keys | Already fixed -- Phase 40 verification only |
| BUG-07 | Tab accent bar bleed into adjacent tabs | Already fixed -- Phase 40 verification only |
| BUG-08 | Panel chevron icons visible in dark mode | Already fixed -- Phase 40 verification only |
| BUG-09 | Concept search/linking works end-to-end | Already fixed -- Phase 40 verification only |

</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rdflib | (installed) | Parse SHACL shapes, extract `sempkm:editHelpText` | Already used by ShapesService |
| marked.js | (CDN) | Render helptext markdown client-side | Already used for object body rendering |
| DOMPurify | (CDN) | Sanitize rendered markdown HTML | Already used in markdown-render.js |
| Lucide | (CDN) | `help-circle` icon for field-level helptext | Already used throughout UI |
| dockview-core | 4.11.0 | Tab management and rendering | Already the tab system |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| highlight.js | (CDN) | Syntax highlighting in helptext code blocks | Already integrated with marked.js |

### Alternatives Considered
None -- all tools are already in the project stack.

## Architecture Patterns

### HELP-01: Helptext Data Flow

```
shapes JSON-LD (sempkm:editHelpText on NodeShape + PropertyShape)
    |
    v
ShapesService._extract_node_shape() / _extract_property_shape()
    |  reads sempkm:editHelpText from rdflib Graph
    v
NodeShapeForm.helptext / PropertyShape.helptext  (new string fields)
    |
    v
object_form.html template renders collapsible markdown sections
    |
    v
marked.js + DOMPurify renders markdown client-side
```

### Pattern 1: Extending ShapesService Dataclasses

**What:** Add `helptext: str | None = None` field to both `NodeShapeForm` and `PropertyShape` dataclasses.

**Implementation detail:** The `sempkm:editHelpText` property uses the `urn:sempkm:` namespace prefix which is already defined as `SEMPKM_NS` in `backend/app/models/registry.py`. The rdflib extraction pattern follows the existing `sh:description` pattern in `_extract_property_shape()`.

```python
# In shapes.py - SEMPKM_NS is "urn:sempkm:"
SEMPKM_EDIT_HELPTEXT = URIRef(f"{SEMPKM_NS}editHelpText")

# In _extract_property_shape:
helptexts = list(graph.objects(prop_node, SEMPKM_EDIT_HELPTEXT))
helptext = str(helptexts[0]) if helptexts else None

# In _extract_node_shape (for form-level):
helptexts = list(graph.objects(shape_node, SEMPKM_EDIT_HELPTEXT))
helptext = str(helptexts[0]) if helptexts else None
```

### Pattern 2: Form-Level Helptext Rendering

**What:** Collapsible markdown section at top of form, below title row.

**Implementation:** Add a `<details>` element in `object_form.html` between the `.form-title-row` and the `<form>` tag. Render markdown using `renderMarkdownBody()` from `markdown-render.js` (already loaded in workspace).

```html
{% if form.helptext %}
<details class="form-helptext form-helptext-top">
    <summary class="form-helptext-summary">
        <i data-lucide="help-circle" class="helptext-icon"></i>
        Form Help
    </summary>
    <div class="form-helptext-content">
        <pre id="helptext-src-{{ safe_id }}" style="display:none">{{ form.helptext }}</pre>
        <div id="helptext-rendered-{{ safe_id }}" class="markdown-body"></div>
    </div>
</details>
<script>
  if (typeof renderMarkdownBody === 'function') {
    renderMarkdownBody('helptext-src-{{ safe_id }}', 'helptext-rendered-{{ safe_id }}');
  }
</script>
{% endif %}
```

### Pattern 3: Field-Level Helptext Rendering

**What:** `?` icon next to field label, inline expandable helptext below field.

**Implementation:** Modify `_field.html` macro to check `prop.helptext` and add an icon + collapsible block.

```html
<label for="input-{{ field_id }}" title="{{ prop.path | compact_iri }}">
    {{ prop.name }}{% if is_required %}<span class="required-marker">*</span>{% endif %}
    {% if prop.helptext %}
    <button type="button" class="btn-helptext-toggle"
            onclick="toggleFieldHelp('{{ field_id }}')" title="Show help">
        <i data-lucide="help-circle"></i>
    </button>
    {% endif %}
</label>

{% if prop.helptext %}
<div class="field-helptext" id="helptext-{{ field_id }}" style="display:none">
    <pre id="helptext-src-{{ field_id }}" style="display:none">{{ prop.helptext }}</pre>
    <div id="helptext-rendered-{{ field_id }}" class="markdown-body"></div>
</div>
{% endif %}
```

### Pattern 4: Type-Aware Accent Color on Dockview Tabs (BUG-04)

**What:** Active dockview tab border-bottom uses type-specific color instead of uniform `--color-accent`.

**Current state:** `_tabMeta[panelId].typeColor` is already populated by `object_tab.html` (line 128). The color comes from `IconService.get_type_icon()` which reads the manifest's `tab` context color. However, dockview renders tabs natively -- we don't control the tab DOM directly.

**Implementation approach:** Use dockview's `onDidActivePanelChange` event (already wired in `workspace-layout.js` line 160) to apply a CSS custom property on the dockview container or the active tab element.

The dockview active tab gets the class `.dv-tab` and the active one is inside an element with specific dockview state classes. The most reliable approach:

1. On `onDidActivePanelChange`, look up `_tabMeta[panel.id].typeColor`
2. Set `--tab-accent-color` on the dockview container element
3. Override the tab border CSS to use `var(--tab-accent-color, var(--color-accent))`

**Manifest already has colors:**
- Note: `#4e79a7` (steel blue -- user wants teal)
- Project: `#59a14f` (green -- user wants indigo)
- Concept: `#f28e2b` (orange -- user wants amber)
- Person: `#76b7b2` (teal -- user wants rose)

The user decided on a warm/cool split palette: Notes=teal, Projects=indigo, Concepts=amber, Persons=rose. The existing manifest colors will need updating to match.

**Key colors for both themes (must work in light and dark):**
- Notes: teal (e.g., `#0d9488` / Tailwind teal-600)
- Projects: indigo (e.g., `#4f46e5` / Tailwind indigo-600)
- Concepts: amber (e.g., `#d97706` / Tailwind amber-600)
- Persons: rose (e.g., `#e11d48` / Tailwind rose-600)

### Pattern 5: Shapes JSON-LD Annotation Format

**What:** Adding `sempkm:editHelpText` to the installed model's shapes file.

**Format in JSON-LD** (the installed model uses JSON-LD, not Turtle):
```json
{
  "@id": "bpkm:NoteShape",
  "@type": "sh:NodeShape",
  "sh:targetClass": { "@id": "bpkm:Note" },
  "sempkm:editHelpText": "## Creating a Note\n\nNotes capture observations...",
  "sh:property": [
    {
      "sh:path": { "@id": "dcterms:title" },
      "sh:name": "Title",
      "sempkm:editHelpText": "A concise, descriptive title...",
      ...
    }
  ]
}
```

The JSON-LD `@context` block needs `"sempkm": "urn:sempkm:"` added.

### Anti-Patterns to Avoid
- **Server-side markdown rendering:** Do NOT render markdown on the backend. The existing pattern uses client-side marked.js + DOMPurify. Follow it.
- **Custom tab renderer for dockview:** Do NOT create a custom `createTabComponent` to control tab rendering. Use CSS custom properties set via JavaScript on panel change events.
- **Storing helptext in manifest.yaml:** The helptext belongs in the SHACL shapes file, NOT the manifest. It's a property of the shape.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom parser | `marked.js` + `DOMPurify` | XSS protection, syntax highlighting already integrated |
| Collapsible sections | Custom accordion | `<details>/<summary>` HTML | Native browser support, no JS needed for basic toggle |
| Type color lookup | Custom color mapping | `IconService.get_type_icon()` | Already reads manifest and resolves type IRIs |
| Icon rendering | Inline SVGs | Lucide `data-lucide="help-circle"` | Consistent with project pattern |

## Common Pitfalls

### Pitfall 1: Lucide Icons in Flex Labels
**What goes wrong:** The `?` help-circle icon disappears when placed inside a flex label container.
**Why it happens:** Lucide SVGs have zero width in flex containers without `flex-shrink: 0` (documented in CLAUDE.md).
**How to avoid:** Always apply `flex-shrink: 0`, `width`, `height` via CSS, never inline styles.
**Warning signs:** Icon invisible on first render.

### Pitfall 2: JSON-LD Context for sempkm namespace
**What goes wrong:** `sempkm:editHelpText` annotations are silently ignored when loading the shapes graph.
**Why it happens:** The `@context` block in `basic-pkm.jsonld` does not include the `sempkm` prefix mapping. Without it, the property becomes a relative IRI and won't match the expected `urn:sempkm:editHelpText`.
**How to avoid:** Add `"sempkm": "urn:sempkm:"` to the `@context` in the shapes JSON-LD file.
**Warning signs:** `graph.objects(node, SEMPKM_EDIT_HELPTEXT)` returns empty list.

### Pitfall 3: DOMPurify Stripping Markdown Content
**What goes wrong:** Rendered helptext loses formatting or elements.
**Why it happens:** DOMPurify default config may strip elements needed for markdown output.
**How to avoid:** Use the same DOMPurify config as `renderMarkdownBody()` in `markdown-render.js`.

### Pitfall 4: Dockview Tab DOM Access
**What goes wrong:** Cannot find the active tab DOM element to apply type-specific border color.
**Why it happens:** Dockview renders tabs internally; DOM structure may change between versions.
**How to avoid:** Use CSS custom properties on the container rather than targeting internal dockview DOM. Set a `--tab-accent-color` variable and reference it via CSS selectors that target dockview's active tab states.
**Warning signs:** Tab color works initially but breaks after dockview upgrade.

### Pitfall 5: Markdown Rendering Timing
**What goes wrong:** `renderMarkdownBody()` called before the DOM elements exist (htmx swap hasn't completed).
**Why it happens:** The helptext `<pre>` and render target are added via htmx partial, and the script runs before DOM update.
**How to avoid:** Place the `<script>` tag after the helptext elements in the template, or use `htmx:afterSettle` event.

### Pitfall 6: Accent Colors in Manifest Need Updating
**What goes wrong:** Tab accent colors don't match the user's decided palette.
**Why it happens:** The existing manifest colors (Note=#4e79a7, etc.) don't match the decided palette (Notes=teal, Projects=indigo, etc.).
**How to avoid:** Update both the installed model (`models/basic-pkm/manifest.yaml`) and the source model (`orig_specs/models/starter-basic-pkm/manifest.yaml`) with the new accent colors.

## Code Examples

### Extending NodeShapeForm and PropertyShape Dataclasses

```python
# Source: backend/app/services/shapes.py (existing pattern)
@dataclass
class PropertyShape:
    path: str
    name: str
    datatype: str | None = None
    target_class: str | None = None
    order: float = 0.0
    group: str | None = None
    min_count: int = 0
    max_count: int | None = None
    in_values: list[str] = field(default_factory=list)
    default_value: str | None = None
    description: str | None = None
    helptext: str | None = None  # NEW: sempkm:editHelpText

@dataclass
class NodeShapeForm:
    shape_iri: str
    target_class: str
    label: str
    groups: list[PropertyGroup] = field(default_factory=list)
    properties: list[PropertyShape] = field(default_factory=list)
    helptext: str | None = None  # NEW: form-level sempkm:editHelpText
```

### Field-Level Helptext Toggle JavaScript

```javascript
// Toggle field-level helptext visibility + lazy-render markdown
window.toggleFieldHelp = function(fieldId) {
    var el = document.getElementById('helptext-' + fieldId);
    if (!el) return;
    var isHidden = el.style.display === 'none';
    el.style.display = isHidden ? 'block' : 'none';
    // Lazy render on first show
    if (isHidden && !el.dataset.rendered) {
        var srcId = 'helptext-src-' + fieldId;
        var renderedId = 'helptext-rendered-' + fieldId;
        if (typeof renderMarkdownBody === 'function') {
            renderMarkdownBody(srcId, renderedId);
        }
        el.dataset.rendered = 'true';
    }
};
```

### Tab Accent Color Application

```javascript
// In workspace-layout.js onDidActivePanelChange handler:
dv.onDidActivePanelChange(function (panel) {
    if (!panel) return;
    var meta = _tabMeta[panel.id];
    var container = document.getElementById('editor-groups-container');
    if (container) {
        var accentColor = (meta && meta.typeColor) ? meta.typeColor : '';
        container.style.setProperty('--tab-accent-color', accentColor || 'var(--color-accent)');
    }
    // ... existing tab-activated dispatch
});
```

```css
/* Override dockview active tab border to use type color */
.dockview-theme-abyss .tab.active-tab,
#editor-groups-container .tab.active-tab {
    border-bottom-color: var(--tab-accent-color, var(--color-accent)) !important;
}
```

**Note:** The exact CSS selector for dockview's active tab needs verification against dockview-core 4.11.0's rendered DOM. The dockview theme is disabled (empty className), so the selector targets the container scope.

### Helptext CSS

```css
/* Form-level helptext */
.form-helptext-top {
    margin: 0 0 16px;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    background: var(--color-surface-raised);
}
.form-helptext-summary {
    padding: 8px 12px;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
}
.form-helptext-content {
    padding: 8px 12px 12px;
}

/* Field-level helptext toggle */
.btn-helptext-toggle {
    display: inline-flex;
    align-items: center;
    background: none;
    border: none;
    padding: 0 2px;
    cursor: pointer;
    color: var(--color-text-faint);
    vertical-align: middle;
}
.btn-helptext-toggle:hover {
    color: var(--color-accent);
}
.btn-helptext-toggle svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    stroke: currentColor;
}

/* Field-level helptext content */
.field-helptext {
    padding: 6px 0 8px;
    font-size: 0.85rem;
}
.field-helptext .markdown-body {
    font-size: 0.85rem;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sh:description` only | `sempkm:editHelpText` + `sh:description` | Phase 39 | sh:description still used for short inline help; editHelpText for rich markdown |
| Uniform teal accent on all tabs | Per-type accent colors from manifest | Phase 39 | Visual differentiation of object types in tab bar |

## Open Questions

1. **Dockview active tab CSS selector**
   - What we know: Dockview 4.11.0 renders tabs natively; theme is disabled (empty className)
   - What's unclear: Exact CSS class names on the active tab element in rendered DOM
   - Recommendation: Inspect the running application's DOM to determine the correct selector. The implementation should use the most stable selector available, potentially `[data-testid]` or stable class names.

2. **Accent color on multiple groups**
   - What we know: dockview supports multiple groups (split panes), each with their own active tab
   - What's unclear: Whether `--tab-accent-color` on the container applies correctly when multiple groups have different active types
   - Recommendation: May need per-group scoping via JavaScript that targets the specific tab element rather than a container-level CSS variable. Alternative: use inline `style` on individual tab elements.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (chromium project) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd e2e && npx playwright test --project=chromium -g "helptext"` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HELP-01 | Edit form shows collapsible helptext from SHACL annotations | e2e | Phase 40 (TEST-05) | No -- Wave 0 |
| BUG-04 | Tab accent bar uses type-specific color | e2e | Phase 40 (TEST-05) | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual browser verification (htmx hot-reload)
- **Per wave merge:** `cd e2e && npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- E2E tests for HELP-01 and BUG-04 are deferred to Phase 40 (TEST-05). Manual verification during implementation is sufficient. Existing tests should not regress.

## Sources

### Primary (HIGH confidence)
- `backend/app/services/shapes.py` -- ShapesService implementation, dataclass definitions, rdflib extraction patterns
- `backend/app/templates/forms/object_form.html` -- Current form rendering template
- `backend/app/templates/forms/_field.html` -- Field rendering macro with existing `sh:description` support
- `backend/app/services/icons.py` -- IconService with per-type color from manifest
- `backend/app/templates/browser/object_tab.html` -- Existing typeColor -> _tabMeta pipeline (lines 120-131)
- `frontend/static/js/workspace-layout.js` -- Dockview initialization, onDidActivePanelChange handler
- `frontend/static/css/dockview-sempkm-bridge.css` -- Token bridge for dockview styling
- `frontend/static/js/markdown-render.js` -- Existing renderMarkdownBody() function
- `models/basic-pkm/manifest.yaml` -- Installed model with icon/color definitions
- `models/basic-pkm/shapes/basic-pkm.jsonld` -- Installed model shapes (JSON-LD format)

### Secondary (MEDIUM confidence)
- `orig_specs/models/starter-basic-pkm/shapes.ttl` -- Source model shapes (Turtle format, used for model rebuilds)
- CLAUDE.md -- Lucide flex-shrink: 0 requirement, stroke: currentColor pattern

### Tertiary (LOW confidence)
- Dockview active tab CSS selectors -- needs DOM inspection for exact class names in 4.11.0

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project
- Architecture (helptext): HIGH -- follows existing patterns (sh:description extraction, marked.js rendering)
- Architecture (accent colors): MEDIUM -- _tabMeta.typeColor already available, but dockview tab DOM access needs verification
- Pitfalls: HIGH -- identified from direct codebase analysis

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- all components already in project)