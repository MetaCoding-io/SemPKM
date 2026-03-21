---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T01: Add help text to all builder fields and simplify workflow view step

**Slice:** S06 — Dashboard & Workflow Builder UX
**Milestone:** M031

## Description

Two related template-only changes to improve builder usability. First, add `<small class="field-help">` elements to every field in both the dashboard and workflow builders. Second, simplify the workflow "view" step by removing the redundant renderer dropdown (each view spec already carries its `renderer_type`).

## Steps

1. **Add help text to dashboard builder fields.** Open `backend/app/templates/browser/dashboard_builder.html`. For each form field — Name, Description, Layout — add a `<small class="field-help">` element after the input/textarea. Then in the `getTypeConfigHTML()` JavaScript function, add help text strings inside each block type's config HTML:
   - `view-embed`: Add help text for "View Spec" (`The view definition to embed. It determines what data and columns appear.`), "Renderer" (`How the view is rendered: as a table, cards, or graph.`). The "Emits context" and "Context variable" fields already have help text — leave those.
   - `markdown`: Add help text for "Content" (`Text content in Markdown format. Supports paragraphs and basic formatting.`)
   - `create-form`: Add help text for "Target Class IRI" (`The RDF type IRI for the object creation form (e.g. a class from your model).`)
   - `object-embed`: Add help text for "Object IRI" (`The IRI of a specific object to display in this block.`)
   - `sparql-result`: Add help text for "SPARQL Query" (`A SELECT query whose first result value is displayed as a metric.`) and "Label" (`A short label shown above the query result value.`)
   - The top-level static HTML fields use `<small class="field-help">` directly in the HTML. The JS-generated block config fields add help text as `'<small class="field-help">...</small>'` string concatenation.

2. **Add help text to workflow builder fields.** Open `backend/app/templates/browser/workflow_builder.html`. For the top-level fields — Name, Description — add `<small class="field-help">` elements. For the step label input (inside the row header), add help text. In `getTypeConfigHTML()`:
   - `view`: Add help text for "View" (`Choose a view to display. The view's own renderer (table/cards/graph) will be used.`)
   - `dashboard`: Add help text for "Dashboard" (`Choose an existing dashboard to embed as this step.`)
   - `form`: Add help text for "Target Class IRI" (`The RDF type IRI for the create form.`)

3. **Remove the renderer dropdown from the workflow view step.** In `workflow_builder.html`, modify the `case 'view':` branch of `getTypeConfigHTML()`:
   - Remove the entire renderer `<select>` element (the `step-config-renderer` with `data-key="renderer_type"` and its table/card/graph options).
   - Add a hidden input: `<input type="hidden" class="step-config-renderer-auto" data-key="renderer_type" value="' + (config.renderer_type || 'table') + '">`.
   - Add a `<span class="renderer-badge"></span>` next to the view select to show the renderer type as read-only text.
   - Update the view spec `<select>` to have an `onchange` handler that: looks up the selected IRI in `_cachedViews`, finds its `renderer_type`, sets the hidden input value, and updates the badge text. Pattern: `onchange="window._wfUpdateRendererFromView(this)"`.

4. **Add the `_wfUpdateRendererFromView` helper function** in the workflow builder `<script>` block:
   ```javascript
   window._wfUpdateRendererFromView = function(selectEl) {
     var row = selectEl.closest('.block-row');
     var hiddenRenderer = row.querySelector('[data-key="renderer_type"]');
     var badge = row.querySelector('.renderer-badge');
     var selectedIri = selectEl.value;
     var rendererType = 'table'; // default
     if (_cachedViews && selectedIri) {
       var match = _cachedViews.find(function(v) { return (v.spec_iri || v.iri) === selectedIri; });
       if (match && match.renderer_type) rendererType = match.renderer_type;
     }
     if (hiddenRenderer) hiddenRenderer.value = rendererType;
     if (badge) badge.textContent = '(' + rendererType + ')';
   };
   ```
   Also call this function after populating the view select for existing steps (in `_wfBuilderAddStep` and `_wfBuilderTypeChanged` after `populateViewSelect` resolves).

## Must-Haves

- [ ] Every user-visible field in the dashboard builder has a `<small class="field-help">` with descriptive content
- [ ] Every user-visible field in the workflow builder has a `<small class="field-help">` with descriptive content
- [ ] The workflow "view" step has NO renderer `<select>` dropdown — only a single view picker
- [ ] The renderer_type is auto-set from the selected view spec's metadata via hidden input
- [ ] Existing save logic still works (the hidden input has `data-key="renderer_type"` so the save collector picks it up)

## Verification

- `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` returns ≥ 10
- `grep -c 'field-help' backend/app/templates/browser/workflow_builder.html` returns ≥ 5
- `grep -c 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` returns 0 (old renderer select removed)
- `grep -q 'renderer-badge' backend/app/templates/browser/workflow_builder.html` succeeds (new badge element present)
- `grep -q '_wfUpdateRendererFromView' backend/app/templates/browser/workflow_builder.html` succeeds (auto-set function present)

## Inputs

- `backend/app/templates/browser/dashboard_builder.html` — existing dashboard builder template (442 lines)
- `backend/app/templates/browser/workflow_builder.html` — existing workflow builder template (391 lines)

## Expected Output

- `backend/app/templates/browser/dashboard_builder.html` — updated with help text on all fields
- `backend/app/templates/browser/workflow_builder.html` — updated with help text on all fields; view step renderer dropdown replaced with auto-set hidden input + badge
