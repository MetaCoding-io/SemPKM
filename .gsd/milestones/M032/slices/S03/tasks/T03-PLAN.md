---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T03: Add builder config panel, save serialization, and CSS for form-group

**Slice:** S03 — Multi-Object Form Groups
**Milestone:** M032

## Description

Wire the form-group block type into the dashboard builder UI so users can configure it, and add CSS styles for the rendered form-group block. The config panel needs to let users add/remove shape entries, each with a type IRI picker, slot ID, and optional edge-linking config. The save logic needs a special case for form-group blocks to serialize the nested `shapes` array from DOM elements (since `shapes` is a list of objects, not simple `[data-key]` values).

## Steps

1. **Add `case 'form-group':` in `getTypeConfigHTML()` in `backend/app/templates/browser/dashboard_builder.html`**:
   - Render a config panel with:
     - A container div `.form-group-shapes-config` that holds shape entries.
     - An "Add Shape" button that appends new shape entries.
     - Each shape entry includes:
       - Type IRI picker (reuse `_builderClassSearch` autocomplete pattern from `create-form` block).
       - Slot ID text input (auto-generated from type name, editable).
       - Optional "Links to" section: target slot ID dropdown (populated from other shapes in the group) + predicate IRI input.
       - A remove button to delete the entry.
     - Render initial entries from `config.shapes` if editing an existing block.
   - Use the existing `reference-field` + `builder-class-search` pattern for the type IRI picker (same as create-form config).

2. **Add special-case save serialization in `_builderSave()` for form-group blocks**:
   - After the generic `[data-key]` collection loop, check if `typeName === 'form-group'`.
   - If so, override `block.config` by reading the `.form-group-shapes-config` DOM:
     - For each `.shape-entry` element, read: type_iri (from hidden input), label (from text input), slot_id (from text input), and optional edge_to (slot_id + predicate from sub-inputs).
     - Build the `shapes` array: `[{type_iri, label, slot_id, edge_to: {slot_id, predicate}}]`.
     - Set `block.config = {shapes: shapesArray}`.
   - This overrides the generic `[data-key]` config which can't handle nested arrays.

3. **Add CSS styles in `frontend/static/css/workspace.css`**:
   - `.dashboard-block-form-group` — scrollable container: `overflow-y: auto; height: 100%; padding: 12px;`
   - `.form-group-section` — sub-form section: margin-bottom, border-left accent
   - `.form-group-section summary` — styled summary with font-weight, icon
   - `.form-group-section .edge-badge` — small badge showing "→ links to {parent}"
   - `.form-group-submit` — submit button row: `text-align: right; padding-top: 12px; border-top`
   - `.form-group-message` — success/error message styling
   - Dashboard page scoped: `.dashboard-page .dashboard-block-form-group` — ensure height: 100%
   - GridStack scoped: `.grid-stack-item-content .suggestions-dropdown` — `z-index: 1000; position: absolute;` to prevent dropdown clipping
   - Builder config styles: `.form-group-shapes-config .shape-entry` — layout for shape config entries
   - Lucide icons inside form-group: `.dashboard-block-form-group svg` — `width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor;` (per CLAUDE.md rule)

4. **Verify** by checking that the config panel code and CSS exist in the files.

## Must-Haves

- [ ] Builder config panel for form-group with add/remove shape entries
- [ ] Type IRI picker using existing class autocomplete pattern
- [ ] Slot ID input per shape entry
- [ ] Edge-to config (target slot + predicate) per shape entry
- [ ] Save serialization reads nested shapes from DOM and builds `{shapes: [...]}` config
- [ ] CSS for form-group block rendering (scrollable, sub-form sections, dropdown z-index)
- [ ] Lucide icons in form-group use CSS sizing with `flex-shrink: 0` (CLAUDE.md rule)

## Verification

- `grep -q "case 'form-group'" backend/app/templates/browser/dashboard_builder.html` — config panel exists
- `grep -q "form-group" frontend/static/css/workspace.css` — CSS added
- `grep -q "shape-entry\|shapes-config" backend/app/templates/browser/dashboard_builder.html` — shape entry UI exists
- `grep -q "form-group-section\|form-group-submit" frontend/static/css/workspace.css` — block-level CSS exists

## Inputs

- `backend/app/templates/browser/dashboard_builder.html` — existing builder with `getTypeConfigHTML()` switch and `_builderSave()` function
- `frontend/static/css/workspace.css` — existing CSS with stat-card, chart, heading block styles
- `backend/app/templates/browser/blocks/block_form_group.html` — template from T02 (CSS targets its class names)

## Expected Output

- `backend/app/templates/browser/dashboard_builder.html` — modified with form-group config panel + save serialization
- `frontend/static/css/workspace.css` — modified with form-group CSS styles

## Observability Impact

- **Builder config inspection**: Opening a dashboard in the builder that contains a form-group block renders shape entries in `.form-group-shapes-config` with populated type IRI, label, slot ID, and edge config fields — visible in the DOM via DevTools.
- **Save serialization**: `_builderSave()` logs the dashboard payload to console via existing `console.info('[dashboard-builder] Saved dashboard')`, which now includes the serialized `shapes` array in form-group block configs.
- **Visual styling**: Form-group blocks rendered on dashboards use `.dashboard-block-form-group` styles with scrollable container, collapsible sub-form sections, and edge badges. Missing styles would be immediately visible as unstyled layout.
- **GridStack dropdown clipping**: `.grid-stack-item-content .suggestions-dropdown` gets `z-index: 1000; position: absolute;` to prevent autocomplete dropdowns from being clipped by grid stack item overflow.
