---
phase: quick-36
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/templates/browser/lint_dashboard.html
  - backend/app/templates/browser/inference_panel.html
  - backend/app/inference/router.py
  - frontend/static/css/workspace.css
autonomous: true
requirements: [QUICK-36]
must_haves:
  truths:
    - "Lint dashboard shows filters on the left (25%) and results table on the right (75%)"
    - "Inference panel shows header+filters on the left (25%) and results on the right (75%)"
    - "Inference results use card-style layout instead of dense table rows"
    - "Both panels remain scrollable in their results area"
    - "Layout does not break at narrow widths (falls back to stacked)"
  artifacts:
    - path: "frontend/static/css/workspace.css"
      provides: "Vertical split layout styles for both panels"
    - path: "backend/app/templates/browser/lint_dashboard.html"
      provides: "Two-column HTML structure for lint dashboard"
    - path: "backend/app/templates/browser/inference_panel.html"
      provides: "Two-column HTML structure for inference panel"
    - path: "backend/app/inference/router.py"
      provides: "Card-based HTML rendering for inference triples"
  key_links:
    - from: "lint_dashboard.html"
      to: "workspace.css"
      via: "CSS classes for vertical split"
      pattern: "lint-dashboard-body"
    - from: "inference_panel.html"
      to: "workspace.css"
      via: "CSS classes for vertical split"
      pattern: "inference-body"
---

<objective>
Change the bottom panel's lint dashboard and inference tabs from horizontal split (controls on top, results on bottom) to vertical split (form controls on the left ~25%, results on the right ~75%). Also improve inference results with a card-based visual presentation instead of the current dense table layout.

Purpose: Better use of horizontal space in the bottom panel -- the filter controls are compact and don't need the full panel width. Placing them as a sidebar lets the results area use more vertical space for content.
Output: Updated templates and CSS for both panels with vertical split layout.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/static/css/workspace.css (lines 1266-1394 for lint panel, lines 3185-3615 for inference+lint dashboard)
@backend/app/templates/browser/lint_dashboard.html
@backend/app/templates/browser/inference_panel.html
@backend/app/inference/router.py (lines 300-467 for HTML rendering)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Restructure lint dashboard and inference panel templates to vertical split</name>
  <files>backend/app/templates/browser/lint_dashboard.html, backend/app/templates/browser/inference_panel.html</files>
  <action>
**Lint Dashboard (`lint_dashboard.html`):**
Wrap the existing content in a two-column body container. The current `.lint-dashboard` div remains the outer shell.

1. Create a new `div.lint-dashboard-body` inside `.lint-dashboard` that uses the existing `#lint-dashboard-container` id
2. Move the filters section (`.lint-dashboard-filters` with its selects and search input) into a `div.lint-dashboard-sidebar` on the left
3. Stack the filter controls vertically in the sidebar (each select/input gets full width)
4. Move the summary counts into the sidebar as well (above or below the filters)
5. Keep the results area (`#lint-dashboard-results`) in a `div.lint-dashboard-main` on the right
6. Ensure all `hx-target`, `hx-include`, and `hx-get` attributes remain unchanged so htmx still works
7. The `hx-include="[class*='lint-dashboard-filter']"` selector must still find all filter inputs -- keep the same class naming convention

Structure:
```html
<div class="lint-dashboard" id="lint-dashboard-container">
  <div class="lint-dashboard-body">
    <div class="lint-dashboard-sidebar">
      <!-- Filters stacked vertically, each with a small label -->
      <div class="lint-dashboard-sidebar-group">
        <label>Severity</label>
        <select ...>
      </div>
      ...
      <!-- Summary at bottom of sidebar -->
    </div>
    <div class="lint-dashboard-main">
      <div class="lint-dashboard-results-wrap" id="lint-dashboard-results">
        ... (unchanged results content)
      </div>
    </div>
  </div>
</div>
```

**Inference Panel (`inference_panel.html`):**
Similarly restructure to vertical split.

1. Create `div.inference-body` as the two-column container
2. Move the header (refresh button, spinner, last-run, summary) and filters into `div.inference-sidebar`
3. Stack all controls vertically in the sidebar
4. Keep the results `#inference-results` in `div.inference-main` on the right
5. Preserve all htmx attributes -- `hx-include="[class*='inference-filter']"` must still find all filter inputs
6. Add small `<label>` elements above each filter for clarity in the stacked layout

Structure:
```html
<div class="inference-panel">
  <div class="inference-body">
    <div class="inference-sidebar">
      <!-- Refresh button + spinner -->
      <!-- Filters stacked vertically with labels -->
      <!-- Summary at bottom -->
    </div>
    <div class="inference-main">
      <div class="inference-results" id="inference-results" ...>
      </div>
    </div>
  </div>
</div>
```
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('backend/app/templates'))
# Verify lint dashboard parses
t1 = env.get_template('browser/lint_dashboard.html')
# Verify inference panel parses
t2 = env.get_template('browser/inference_panel.html')
print('Both templates parse successfully')
# Check structural elements exist
import re
with open('backend/app/templates/browser/lint_dashboard.html') as f:
    lint = f.read()
assert 'lint-dashboard-sidebar' in lint, 'Missing lint sidebar'
assert 'lint-dashboard-main' in lint, 'Missing lint main'
assert 'lint-dashboard-body' in lint, 'Missing lint body'
with open('backend/app/templates/browser/inference_panel.html') as f:
    inf = f.read()
assert 'inference-sidebar' in inf, 'Missing inference sidebar'
assert 'inference-main' in inf, 'Missing inference main'
assert 'inference-body' in inf, 'Missing inference body'
print('All structural elements present')
"
    </automated>
  </verify>
  <done>Both templates restructured with sidebar (left) + main content (right) layout. All htmx attributes preserved. Filter class naming conventions unchanged so hx-include selectors still work.</done>
</task>

<task type="auto">
  <name>Task 2: Update CSS for vertical split layout and improve inference card presentation</name>
  <files>frontend/static/css/workspace.css, backend/app/inference/router.py</files>
  <action>
**CSS changes in `workspace.css`:**

1. **Lint Dashboard vertical split** -- update the `.lint-dashboard` section (around line 3469):

```css
.lint-dashboard-body {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.lint-dashboard-sidebar {
    width: 25%;
    min-width: 180px;
    max-width: 280px;
    padding: 10px 12px;
    border-right: 1px solid var(--color-border);
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.lint-dashboard-sidebar-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.lint-dashboard-sidebar-group label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-text-muted);
}

.lint-dashboard-sidebar select,
.lint-dashboard-sidebar input {
    width: 100%;
    font-size: 0.78rem;
    padding: 4px 8px;
    border: 1px solid var(--color-border);
    border-radius: 4px;
    background: var(--color-bg);
    color: var(--color-text);
}

.lint-dashboard-main {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
}
```

Remove the old `.lint-dashboard-filters` flex-row layout (lines ~3490-3513) since filters are now in the sidebar. Keep the filter-level styles that still apply.

2. **Inference Panel vertical split** -- update the `.inference-panel` section (around line 3185):

```css
.inference-body {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.inference-sidebar {
    width: 25%;
    min-width: 180px;
    max-width: 280px;
    padding: 10px 12px;
    border-right: 1px solid var(--color-border);
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.inference-sidebar-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.inference-sidebar-group label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-text-muted);
}

.inference-sidebar select,
.inference-sidebar input {
    width: 100%;
}

.inference-main {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
}
```

Remove the old `.inference-panel-header` and `.inference-filters` horizontal flex styles. Move header elements (refresh btn, spinner) into sidebar styling.

3. **Responsive fallback** -- add a media query for narrow panels:

```css
@media (max-width: 600px) {
    .lint-dashboard-body,
    .inference-body {
        flex-direction: column;
    }
    .lint-dashboard-sidebar,
    .inference-sidebar {
        width: 100%;
        max-width: none;
        border-right: none;
        border-bottom: 1px solid var(--color-border);
    }
}
```

4. **Inference card layout** -- replace the dense table rendering with card-based presentation. Add new CSS:

```css
.inference-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--color-border-subtle, var(--color-border));
    transition: background 0.1s;
    font-size: 0.8125rem;
}

.inference-card:hover {
    background: var(--color-surface-raised, var(--color-surface));
}

.inference-card-triple {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
}

.inference-card-subject,
.inference-card-object {
    color: var(--color-text);
    text-decoration: none;
    font-weight: 500;
}

.inference-card-subject:hover,
.inference-card-object:hover {
    text-decoration: underline;
    color: var(--color-accent);
}

.inference-card-predicate {
    color: var(--color-text-muted);
    font-family: var(--font-mono, monospace);
    font-size: 0.72rem;
}

.inference-card-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
}

.inference-card-type-badge {
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 3px;
    background: var(--color-bg-secondary, var(--color-surface-recessed));
    color: var(--color-text-muted);
    white-space: nowrap;
}

.inference-card-actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
}

.inference-card:hover .inference-card-actions {
    opacity: 1;
}

.inference-card.status-dismissed {
    opacity: 0.5;
}
```

**Router changes in `router.py`:**

Update `_build_triple_row()` to render cards instead of table rows. Change the function to output `div.inference-card` elements instead of `<tr>` elements.

Update `_render_triples_list_html()` and the run endpoint response to wrap cards in a simple container div instead of a `<table>`. The summary div remains unchanged.

Updated `_build_triple_row()` (rename to `_build_triple_card()`):
```python
def _build_triple_card(t):
    h = t["triple_hash"]
    s_display = _compact_iri(t["subject"])
    p_display = _compact_iri(t["predicate"])
    o_display = _compact_iri(t["object"])
    status_class = f"status-{t['status']}"

    actions = ""
    if t["status"] == "active":
        actions = (
            f'<div class="inference-card-actions">'
            f'<button class="btn btn-xs" '
            f'hx-post="/api/inference/triples/{h}/dismiss" '
            f'hx-target="closest .inference-card" hx-swap="outerHTML">Dismiss</button> '
            f'<button class="btn btn-xs btn-primary" '
            f'hx-post="/api/inference/triples/{h}/promote" '
            f'hx-target="closest .inference-card" hx-swap="outerHTML">Promote</button>'
            f'</div>'
        )
    elif t["status"] == "dismissed":
        actions = '<div class="inference-card-actions" style="opacity:1"><span class="text-muted">Dismissed</span></div>'
    elif t["status"] == "promoted":
        actions = '<div class="inference-card-actions" style="opacity:1"><span class="text-muted">Promoted</span></div>'

    return (
        f'<div id="triple-{h}" class="inference-card {status_class}">'
        f'<div class="inference-card-triple">'
        f'<span class="inference-card-subject">{s_display}</span>'
        f'<span class="inference-card-predicate">{p_display}</span>'
        f'<span class="inference-card-object">{o_display}</span>'
        f'</div>'
        f'<div class="inference-card-meta">'
        f'<span class="inference-card-type-badge">{t["entailment_type"]}</span>'
        f'</div>'
        f'{actions}'
        f'</div>'
    )
```

Update `_render_triple_rows()` to call `_build_triple_card()`. Update the container HTML in `_render_triples_list_html()` and the run endpoint to use `<div class="inference-cards">` instead of `<table>`. Remove the `<thead>` header row -- column headers are unnecessary in the card layout since each card's structure is self-explanatory (subject -> predicate -> object).

Also update `_render_grouped_triples_html()` similarly -- replace table wrappers with div containers.

Update `_render_triple_row_html()` (the single-row swap endpoint) to call `_build_triple_card()` so dismiss/promote htmx swaps return the same card markup.

IMPORTANT: The `hx-target="closest tr"` in the old table rows must change to `hx-target="closest .inference-card"` in the new card layout. This is handled by changing the target in `_build_triple_card()`.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
# Check CSS has new classes
with open('frontend/static/css/workspace.css') as f:
    css = f.read()
for cls in ['lint-dashboard-body', 'lint-dashboard-sidebar', 'lint-dashboard-main',
            'inference-body', 'inference-sidebar', 'inference-main',
            'inference-card', 'inference-card-triple', 'inference-card-predicate']:
    assert cls in css, f'Missing CSS class: {cls}'
print('All CSS classes present')

# Check router renders cards not tables
with open('backend/app/inference/router.py') as f:
    router = f.read()
assert 'inference-card' in router, 'Router not rendering cards'
assert 'inference-card-triple' in router, 'Router missing triple container'
print('Router renders card layout')

# Verify Python syntax
import py_compile
py_compile.compile('backend/app/inference/router.py', doraise=True)
print('Router compiles OK')
"
    </automated>
  </verify>
  <done>Both panels display filters/controls in a left sidebar (25% width) and results in the main area (75% width). Inference results use a card-based layout with subject-predicate-object inline flow, type badge, and hover-reveal actions. Responsive fallback stacks vertically below 600px.</done>
</task>

</tasks>

<verification>
1. Open workspace in browser, open bottom panel
2. Click LINT tab -- filters should appear in left sidebar, results table on right
3. Click INFERENCE tab -- refresh button and filters in left sidebar, card-based results on right
4. Resize browser narrow -- panels should stack vertically
5. Filter interactions still work (htmx selectors unchanged)
6. Inference dismiss/promote buttons still work via htmx swap
</verification>

<success_criteria>
- Both panels use left-sidebar (25%) + right-results (75%) layout
- Inference results render as cards instead of table rows
- All htmx interactions (filtering, dismiss, promote) still function
- Layout degrades gracefully at narrow widths
</success_criteria>

<output>
After completion, create `.planning/quick/36-vertical-split-layout-for-lint-and-infer/36-SUMMARY.md`
</output>
