# Phase 11: Read-Only Object View - Research

**Researched:** 2026-02-23
**Domain:** Browser-side markdown rendering, CSS 3D animations, read-only data presentation
**Confidence:** HIGH

## Summary

Phase 11 transforms the object viewing experience from edit-by-default to read-by-default. Currently, clicking an object loads `object_tab.html` which immediately renders the SHACL form (editable inputs) and a CodeMirror editor for the body. The new architecture introduces a dual-mode object tab: a read-only view (styled property table + rendered Markdown body) shown by default, with a flip animation transition to the existing edit mode.

The standard stack for this is **marked.js** (v17.x) for Markdown-to-HTML rendering with **marked-highlight** (v2.x) and **highlight.js** (v11.x) for syntax-highlighted code blocks, plus **DOMPurify** (v3.x) for HTML sanitization. All are available as CDN UMD scripts matching the project's existing unpkg-based loading pattern. The CSS 3D flip animation uses native CSS transforms (perspective, preserve-3d, backface-visibility, rotateY) with no additional library.

**Primary recommendation:** Add a `mode` query parameter to the `get_object` endpoint (`?mode=read` default, `?mode=edit` for explicit edit). Render a new `object_read.html` template for read mode that includes a `<div class="markdown-body">` for rendered Markdown, a property table driven by form metadata + values, and reference pills that call `openTab()`. The flip animation wraps both views in a CSS 3D container toggled by a class. The backend must be enhanced to return multi-valued properties and resolve reference labels for display.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two-column table layout: labels on left, values on right (like VS Code details panel or GitHub issue sidebar)
- Labels styled bold, normal case -- clear hierarchy, document-like feel
- Empty optional properties are hidden entirely -- only properties with values display
- Type-specific value formatting: dates as human-readable (e.g., "Feb 23, 2026"), booleans as check/x icons, URIs as clickable links
- Edit/Done toggle button positioned top-right of content area
- Horizontal flip animation (card rotates on vertical axis) when transitioning between read-only and edit mode
- Edit mode indicated by a subtle background tint (e.g., faint blue) so user knows they're in editing state
- Switching from edit to read-only with unsaved changes prompts "Discard changes?" confirmation
- Newly created objects open directly in edit mode (no flip needed)
- Ctrl+E keyboard shortcut toggles mode
- GitHub-style rendering: proportional font, generous spacing, clear heading hierarchy
- Syntax-highlighted code blocks with code font and subtle background (like GitHub fenced blocks)
- Thin horizontal rule as visual separator between property table and Markdown body
- Images rendered inline where they appear in the Markdown text
- Reference values displayed as pill/badge style -- rounded pill with subtle background, visually distinct from plain text
- Each pill shows a type icon (or colored dot) + object name -- visual hint of the linked object's type
- Hovering a reference pill shows a tooltip preview with the linked object's type and key properties
- Clicking a reference pill opens the target object in a new tab
- Multiple references on a property wrap inline as a pill row (like tags), flowing naturally

### Claude's Discretion
- Exact flip animation duration and easing
- Specific color values for edit-mode background tint
- Markdown rendering library choice (marked, markdown-it, etc.)
- Syntax highlighting library choice (highlight.js, Prism, etc.)
- Tooltip preview layout and which properties to show
- Type icon mapping (until Phase 15 icon system exists, use simple colored dots or generic icons)
- Exact spacing and padding in the two-column table

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-01 | Objects open in read-only mode by default showing styled property key-value pairs and rendered Markdown body | New `object_tab.html` with read-mode as default; marked.js renders body; property table from form metadata + values; backend `get_object` enhanced with `mode` parameter and multi-value property support |
| VIEW-02 | User can switch between read-only and edit mode via Edit/Done button or Ctrl+E shortcut | CSS 3D flip animation using native transforms; JS toggle adds/removes `.flipped` class; Ctrl+E shortcut registered in workspace.js; unsaved changes confirmation via `window.confirm()` |
| VIEW-03 | Reference properties in read-only mode render as clickable links that open the target object in a new tab | Backend resolves reference IRIs to labels via LabelService; template renders pill/badge elements with `onclick="openTab()"` handlers; PropertyShape.target_class identifies references |
| VIEW-04 | The Markdown body text area in edit mode is resizable via Split.js gutter, with maximize/restore toggle | Split.js `setSizes([0, 100])` to maximize editor; `setSizes([40, 60])` to restore; toggle button in editor toolbar; prior sizes stored in variable for exact restore |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| [marked](https://github.com/markedjs/marked) | 17.x | Markdown to HTML rendering | Fastest JS markdown parser; GFM enabled by default; 97% CommonMark compliant; UMD CDN build available |
| [marked-highlight](https://github.com/markedjs/marked-highlight) | 2.x | Code block syntax highlighting bridge | Official marked extension; bridges marked + highlight.js; v2.2.3 current |
| [highlight.js](https://highlightjs.org/) | 11.11.1 | Syntax highlighting for code blocks | Zero dependencies; 180+ languages; auto-detection; GitHub theme included; CDN available |
| [DOMPurify](https://github.com/cure53/DOMPurify) | 3.x | HTML sanitization (XSS prevention) | marked docs recommend it; <30KB; DOM-only sanitizer from Cure53 security team |
| CSS 3D Transforms | native | Flip animation between read/edit modes | No library needed; perspective + preserve-3d + rotateY(180deg) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Split.js | 1.6.5 (already loaded) | Resizable form/editor split in edit mode | Already in project; `setSizes()` API for maximize/restore |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| marked | markdown-it | markdown-it has richer plugin system but marked is faster, lighter, and GFM is default; project needs simple rendering, not extensibility |
| highlight.js | Prism | Prism requires manual language loading; highlight.js auto-detects and has broader CDN support; highlight.js simpler for the "render and forget" use case |
| DOMPurify | None (trust marked output) | Marked output is user-generated Markdown; must sanitize to prevent stored XSS from body content |

**Installation (CDN in base.html):**
```html
<!-- Markdown rendering -->
<script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js"></script>

<!-- Syntax highlighting -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>

<!-- XSS sanitization -->
<script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
```

## Architecture Patterns

### Recommended Structure Changes

```
backend/app/templates/
├── browser/
│   ├── object_tab.html        # MODIFIED: wraps read + edit in flip container
│   ├── object_read.html       # NEW: read-only view (property table + rendered markdown)
│   └── ...
frontend/static/
├── js/
│   ├── workspace.js           # MODIFIED: Ctrl+E shortcut, mode toggle, openTab in read mode
│   ├── markdown-render.js     # NEW: marked + highlight.js + DOMPurify initialization
│   └── ...
├── css/
│   ├── workspace.css          # MODIFIED: flip animation, read-only styles, property table
│   └── ...
backend/app/
├── browser/
│   └── router.py              # MODIFIED: get_object enhanced with mode param, multi-value, labels
```

### Pattern 1: Dual-Mode Object Tab with CSS 3D Flip
**What:** The object tab contains both a read-only face and an edit face, stacked absolutely within a preserve-3d container. Toggling adds a `.flipped` class that rotates 180deg.
**When to use:** Any time a view needs a dramatic mode switch with preserved DOM state on both sides.

```html
<!-- object_tab.html structure -->
<div class="object-tab" data-object-iri="{{ object_iri }}">
  <div class="object-toolbar">
    <span class="object-toolbar-title">{{ object_label }}</span>
    <div class="object-toolbar-actions">
      <button class="btn btn-sm mode-toggle" onclick="toggleObjectMode()" title="Toggle Edit (Ctrl+E)">
        Edit
      </button>
    </div>
  </div>

  <div class="object-flip-container" id="flip-{{ safe_id }}">
    <div class="object-flip-inner">
      <!-- Read-only face (front) -->
      <div class="object-face object-face-read">
        {% include "browser/object_read.html" %}
      </div>
      <!-- Edit face (back, pre-rotated 180deg) -->
      <div class="object-face object-face-edit">
        {# existing form + editor content #}
      </div>
    </div>
  </div>
</div>
```

```css
.object-flip-container {
  perspective: 1200px;
  flex: 1;
  overflow: hidden;
}

.object-flip-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.6s ease-in-out;
  transform-style: preserve-3d;
}

.object-flip-inner.flipped {
  transform: rotateY(180deg);
}

.object-face {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  overflow-y: auto;
}

.object-face-edit {
  transform: rotateY(180deg);
  background: rgba(45, 90, 158, 0.03); /* subtle blue tint */
}
```

### Pattern 2: Read-Only Property Table from SHACL Form Metadata
**What:** Reuse the same `form` (NodeShapeForm) object to drive the property table in read mode. Iterate form.properties, skip empty optionals, format values by datatype.
**When to use:** The form metadata is already loaded -- reuse it for consistent property ordering and labels.

```html
<!-- object_read.html property table -->
<div class="property-table">
  {% for prop in form.properties %}
    {% set val = values.get(prop.path) %}
    {% if val is not none and val != '' %}
    <div class="property-row">
      <div class="property-label">{{ prop.name }}</div>
      <div class="property-value">
        {% if prop.target_class %}
          {# Reference: render as pill #}
          <span class="ref-pill" onclick="openTab('{{ val }}', '{{ ref_labels.get(val, val) }}')"
                title="{{ val }}">
            <span class="ref-pill-dot"></span>
            {{ ref_labels.get(val, val) }}
          </span>
        {% elif prop.datatype == 'http://www.w3.org/2001/XMLSchema#date' %}
          {{ val | format_date }}
        {% elif prop.datatype == 'http://www.w3.org/2001/XMLSchema#boolean' %}
          {% if val == 'true' %}&#10003;{% else %}&#10007;{% endif %}
        {% elif prop.datatype == 'http://www.w3.org/2001/XMLSchema#anyURI' %}
          <a href="{{ val }}" target="_blank" rel="noopener">{{ val }}</a>
        {% else %}
          {{ val }}
        {% endif %}
      </div>
    </div>
    {% endif %}
  {% endfor %}
</div>
```

### Pattern 3: Client-Side Markdown Rendering
**What:** Render Markdown body on the client using marked.js after the template loads. The template provides the raw markdown in a hidden element or data attribute; JS picks it up, renders, and inserts.
**When to use:** Avoids adding a Python markdown library to the backend; keeps rendering consistent with what the user would see in a GitHub README.

```javascript
// markdown-render.js
(function() {
  'use strict';

  var _marked = null;

  function getMarked() {
    if (_marked) return _marked;
    if (typeof globalThis.marked === 'undefined' || typeof globalThis.markedHighlight === 'undefined') {
      return null;
    }
    var Marked = globalThis.marked.Marked;
    var markedHighlight = globalThis.markedHighlight.markedHighlight;

    _marked = new Marked(
      markedHighlight({
        emptyLangClass: 'hljs',
        langPrefix: 'hljs language-',
        highlight: function(code, lang) {
          if (typeof hljs === 'undefined') return code;
          var language = hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language: language }).value;
        }
      })
    );
    return _marked;
  }

  window.renderMarkdownBody = function(sourceId, targetId) {
    var source = document.getElementById(sourceId);
    var target = document.getElementById(targetId);
    if (!source || !target) return;

    var md = getMarked();
    if (!md) {
      target.textContent = source.textContent;
      return;
    }

    var rawHtml = md.parse(source.textContent || '');
    // Sanitize to prevent XSS
    if (typeof DOMPurify !== 'undefined') {
      rawHtml = DOMPurify.sanitize(rawHtml);
    }
    target.innerHTML = rawHtml;
  };
})();
```

### Pattern 4: Maximize/Restore Toggle for Editor
**What:** A button in the editor toolbar toggles the editor section to 100% of the split area by calling `Split.setSizes([0, 100])` and restoring with `Split.setSizes(savedSizes)`.
**When to use:** When user wants to focus on writing the body text.

```javascript
// In object_tab.html script
var isMaximized = false;
var savedSplitSizes = null;

window.toggleEditorMaximize = function() {
  var splitContainerId = 'object-split-{{ safe_id }}';
  var splitInstance = window._sempkmSplits && window._sempkmSplits[splitContainerId];
  if (!splitInstance) return;

  if (isMaximized) {
    splitInstance.setSizes(savedSplitSizes || [40, 60]);
    isMaximized = false;
  } else {
    savedSplitSizes = splitInstance.getSizes();
    splitInstance.setSizes([0, 100]);
    isMaximized = true;
  }
};
```

### Anti-Patterns to Avoid
- **Server-side Markdown rendering:** Adding a Python markdown library increases backend complexity and creates rendering inconsistency with the client-side editor preview. Render on the client where the libraries already exist.
- **Separate endpoints for read/edit modes:** Don't create `/browser/object/{iri}/read` and `/browser/object/{iri}/edit`. Use a single endpoint with a `mode` parameter, since both modes need the same data (form + values + body).
- **innerHTML without sanitization:** Never set `innerHTML` from marked output without DOMPurify. User-created Markdown body content could contain `<script>` tags or event handlers.
- **Destroying/recreating DOM on mode switch:** The flip animation requires both faces to exist simultaneously. Don't remove one face when showing the other -- this would break the 3D transform and require expensive re-rendering.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown to HTML | Custom regex-based parser | marked.js | Edge cases in GFM tables, lists, code blocks, and HTML entities are complex |
| Syntax highlighting | Manual token parsing | highlight.js | Language grammars are maintained by community; auto-detection is non-trivial |
| HTML sanitization | String replacement or allowlists | DOMPurify | XSS bypasses are discovered regularly; DOMPurify from security researchers |
| 3D flip animation | JavaScript animation library | CSS 3D transforms | GPU-accelerated; native; no JS overhead; simpler to maintain |
| Date formatting | Manual date string parsing | `Intl.DateTimeFormat` or Jinja2 filter | Locale-aware, handles edge cases |

**Key insight:** The read-only view is primarily a presentation layer. All the data already exists in the backend; the challenge is formatting it nicely, which off-the-shelf libraries handle better than custom code.

## Common Pitfalls

### Pitfall 1: Flip Animation Breaks Scrollable Content
**What goes wrong:** Absolutely-positioned faces inside a preserve-3d container lose their scroll behavior. The front and back faces need overflow-y: auto but the container itself is overflow: hidden.
**Why it happens:** `transform-style: preserve-3d` creates a new stacking context that can interfere with overflow behavior in some browsers.
**How to avoid:** Set `overflow: hidden` on the flip container, `overflow-y: auto` on each face. Test in Firefox and Chrome -- they handle preserve-3d overflow differently. If broken, use `will-change: transform` on the flip-inner element.
**Warning signs:** Content appears clipped or scrollbar disappears after flip.

### Pitfall 2: Markdown Renders Before Libraries Load
**What goes wrong:** If `renderMarkdownBody()` is called before marked.js/highlight.js CDN scripts have loaded, the body shows raw markdown or nothing.
**Why it happens:** CDN scripts load asynchronously; the inline `<script>` in the template may execute before they're ready.
**How to avoid:** Check for library availability in `renderMarkdownBody()` with a graceful fallback (show raw text in a `<pre>` block). Alternatively, use the `DOMContentLoaded` pattern or defer rendering until htmx afterSwap.
**Warning signs:** Body area is blank or shows raw markdown text intermittently.

### Pitfall 3: Edit Mode Initializes Expensive Resources Upfront
**What goes wrong:** Even though the user sees read-only mode, CodeMirror and Split.js are initialized on the hidden edit face, wasting resources.
**Why it happens:** The edit face DOM exists from page load (needed for flip animation); inline scripts init libraries immediately.
**How to avoid:** Defer CodeMirror and Split.js initialization until the user first switches to edit mode. Use a flag (`data-edit-initialized="false"`) and initialize on first flip.
**Warning signs:** Slow initial load time; high memory usage for objects that are only ever read.

### Pitfall 4: Multi-Valued Properties in Backend
**What goes wrong:** The current `get_object` endpoint uses `values[pred] = obj_val` which overwrites multi-valued properties. The read-only view shows only the last value.
**Why it happens:** The original implementation assumed single-valued properties for the edit form. SPARQL can return multiple `?o` values for the same `?p`.
**How to avoid:** Change `values` to `dict[str, list[str]]` in the backend, appending each value. Template iteration handles lists. This is a breaking change that also affects the edit form template.
**Warning signs:** Objects with multiple values for the same property show only one value.

### Pitfall 5: Reference Label Resolution for Read View
**What goes wrong:** Reference property values are IRIs (e.g., `urn:sempkm:obj:abc123`). Without label resolution, the read-only view shows raw IRIs instead of human-readable names.
**Why it happens:** The current `get_object` endpoint doesn't resolve reference labels since the edit form uses search-as-you-type (labels resolved on the client during search).
**How to avoid:** Identify properties with `target_class` in the form metadata, collect their IRI values, and resolve labels via `LabelService.resolve_batch()` before passing to the template. Pass as a `ref_labels` dict.
**Warning signs:** Read-only view shows IRIs like `urn:sempkm:obj:abc123` instead of "My Project".

### Pitfall 6: Unsaved Changes Lost Without Warning
**What goes wrong:** User edits properties/body, then clicks "Done" to return to read-only mode. Changes are discarded without warning.
**Why it happens:** The flip animation simply hides the edit face without checking for unsaved state.
**How to avoid:** Before flipping from edit to read, check the tab's dirty state (from `getTabs()` in workspace.js). If dirty, prompt with `window.confirm("Discard unsaved changes?")`. Only flip if confirmed or not dirty.
**Warning signs:** Users lose work after mode switching.

## Code Examples

### Marked + Highlight.js + DOMPurify Integration (Browser UMD)
```html
<!-- In base.html, before workspace.js -->
<script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
```

```javascript
// markdown-render.js: Initialize once, use everywhere
(function() {
  'use strict';
  var _marked = null;

  function initMarked() {
    if (_marked) return _marked;
    var Marked = globalThis.marked.Marked;
    var mh = globalThis.markedHighlight.markedHighlight;
    _marked = new Marked(
      mh({
        emptyLangClass: 'hljs',
        langPrefix: 'hljs language-',
        highlight: function(code, lang) {
          var language = hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language: language }).value;
        }
      })
    );
    return _marked;
  }

  window.renderMarkdownBody = function(sourceId, targetId) {
    var source = document.getElementById(sourceId);
    var target = document.getElementById(targetId);
    if (!source || !target) return;
    var md = initMarked();
    if (!md) { target.textContent = source.textContent; return; }
    var html = md.parse(source.textContent || '');
    target.innerHTML = DOMPurify.sanitize(html);
  };
})();
```

### CSS 3D Flip Animation
```css
/* Container wrapping both faces */
.object-flip-container {
  perspective: 1200px;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.object-flip-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.6s ease-in-out;
  transform-style: preserve-3d;
}

/* Flipped state (edit mode visible) */
.object-flip-inner.flipped {
  transform: rotateY(180deg);
}

/* Both faces */
.object-face {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
}

/* Read face (front, default visible) */
.object-face-read {
  overflow-y: auto;
}

/* Edit face (back, rotated 180deg so backface shows through) */
.object-face-edit {
  transform: rotateY(180deg);
  overflow: hidden;
  background: rgba(45, 90, 158, 0.03);
}
```

### Property Table CSS (Two-Column GitHub Sidebar Style)
```css
.property-table {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0;
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 6px;
  overflow: hidden;
}

.property-row {
  display: contents;
}

.property-label {
  padding: 8px 12px;
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--color-text, #1a1a2e);
  background: #f8f9fb;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
  white-space: nowrap;
}

.property-value {
  padding: 8px 12px;
  font-size: 0.85rem;
  color: var(--color-text, #1a1a2e);
  border-bottom: 1px solid var(--color-border, #e0e0e0);
  word-break: break-word;
}

.property-row:last-child .property-label,
.property-row:last-child .property-value {
  border-bottom: none;
}
```

### Reference Pill CSS
```css
.ref-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  background: rgba(45, 90, 158, 0.08);
  border-radius: 12px;
  font-size: 0.82rem;
  color: var(--color-primary, #2d5a9e);
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.ref-pill:hover {
  background: rgba(45, 90, 158, 0.15);
  text-decoration: underline;
}

.ref-pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary, #2d5a9e);
  flex-shrink: 0;
}
```

### Backend Enhancement: Multi-Value + Reference Labels
```python
# In get_object endpoint (browser/router.py)
# Change values from dict[str, str] to dict[str, list[str]]
values: dict[str, list[str]] = {}

for b in bindings:
    pred = b["p"]["value"]
    obj_val = b["o"]["value"]
    if pred == rdf_type:
        type_iris.append(obj_val)
    elif pred == sempkm_body:
        body_text = obj_val
    else:
        if pred not in values:
            values[pred] = []
        values[pred].append(obj_val)

# Resolve reference labels for read mode
ref_iris: set[str] = set()
if form:
    for prop in form.properties:
        if prop.target_class and prop.path in values:
            for v in values[prop.path]:
                if v.startswith("http") or v.startswith("urn:"):
                    ref_iris.add(v)

ref_labels = await label_service.resolve_batch(list(ref_iris)) if ref_iris else {}

# Also resolve type label for reference pill tooltips
type_label_map: dict[str, str] = {}
# ... (resolve from type_iris for display)

context = {
    "request": request,
    "form": form,
    "values": values,       # Now list-valued
    "ref_labels": ref_labels,
    "object_iri": decoded_iri,
    "object_label": object_label,
    "body_text": body_text,
    "mode": mode,            # "read" or "edit"
}
```

### Jinja2 Date Formatting Filter
```python
# In app setup or template globals
from datetime import datetime

def format_date(value):
    """Format ISO date string to human-readable: 'Feb 23, 2026'."""
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(value)

# Register as Jinja2 filter
templates.env.filters["format_date"] = format_date
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| marked built-in `highlight` option | marked-highlight extension package | marked v8.0.0 (2023) | Must use marked-highlight, not `highlight` option |
| marked built-in `sanitize` option | External DOMPurify | marked v8.0.0 (2023) | Must add DOMPurify separately for XSS prevention |
| highlight.js auto-init via `hljs.initHighlightingOnLoad()` | `hljs.highlightAll()` | highlight.js v11 (2021) | Use highlightAll() or manual highlight() calls |

**Deprecated/outdated:**
- `marked.setOptions({ highlight: ... })`: Removed in v8; use marked-highlight extension
- `marked.setOptions({ sanitize: true })`: Removed in v8; use DOMPurify
- `hljs.initHighlightingOnLoad()`: Deprecated in v11; use `hljs.highlightAll()` or `hljs.highlight()`

## Open Questions

1. **Multi-value property display in EDIT mode**
   - What we know: Changing `values` from `dict[str, str]` to `dict[str, list[str]]` affects the edit form template (`_field.html`), which currently expects single values via `values.get(prop.path)`
   - What's unclear: The edit form already has multi-value support via `values` parameter (list) in `render_field` macro, but the router passes individual values. Need to verify the template handles both.
   - Recommendation: Modify the router to always pass lists, and update `object_form.html` to pass lists to `render_field` macro. Test with existing objects.

2. **Tooltip preview content for reference pills**
   - What we know: User wants a tooltip with type and key properties on hover
   - What's unclear: Fetching key properties for every referenced object on initial render could be expensive (N+1 SPARQL queries). An htmx lazy-load tooltip might be more practical.
   - Recommendation: Use a simple CSS tooltip showing type label initially. If richer preview is needed, add an htmx endpoint that fetches key properties on hover (lazy load, small request).

3. **Newly created objects and mode initialization**
   - What we know: User decided "newly created objects open directly in edit mode (no flip needed)"
   - What's unclear: After the create form POST, the response re-renders in edit mode. The current flow opens via `objectCreated` event. Need to ensure the new object tab skips the read-only default.
   - Recommendation: Pass `mode=edit` in the context when `objectCreated` triggers `loadObjectContent()`. Add `?mode=edit` query parameter to the htmx GET request.

## Sources

### Primary (HIGH confidence)
- [marked.js official docs](https://marked.js.org/) - API, CDN usage, GFM configuration, removed highlight option
- [marked-highlight GitHub](https://github.com/markedjs/marked-highlight) - v2.2.3, CDN UMD usage, highlight.js integration code
- [highlight.js official site](https://highlightjs.org/) - v11.11.1, CDN URLs, themes, API
- [DOMPurify GitHub](https://github.com/cure53/DOMPurify) - v3.3.1, CDN, sanitization API
- [W3Schools CSS Flip Card](https://www.w3schools.com/howto/howto_css_flip_card.asp) - Complete CSS 3D flip pattern with perspective/preserve-3d/backface-visibility
- [Split.js docs](https://split.js.org/) - getSizes(), setSizes(), collapse() API for maximize/restore
- Project codebase: `backend/app/browser/router.py`, `backend/app/templates/browser/object_tab.html`, `frontend/static/js/workspace.js`, `frontend/static/js/editor.js`, `frontend/static/js/cleanup.js`

### Secondary (MEDIUM confidence)
- [npm-compare marked vs markdown-it](https://npm-compare.com/markdown-it,marked,remark,showdown) - Library comparison, download stats
- [3D Transforms by Desandro](https://3dtransforms.desandro.com/card-flip) - In-depth CSS 3D flip tutorial with browser compatibility notes

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs; CDN URLs confirmed; UMD builds confirmed
- Architecture: HIGH - Codebase thoroughly examined; patterns derived from existing code structure; no assumptions
- Pitfalls: HIGH - Based on direct codebase analysis (multi-value bug, reference labels missing) and established CSS 3D quirks

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable libraries, no rapid changes expected)
