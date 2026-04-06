---
estimated_steps: 27
estimated_files: 4
skills_used: []
---

# T03: Multi-panel OBJECTS sections with independent configurations

Enable multiple independent OBJECTS explorer sections with a Duplicate button. Refactor ID-based DOM access to class-based section-scoped access.

Steps:
1. Refactor `frontend/static/js/explorer-config.js` DOM access:
   - Replace all `_el('explorer-config-type')` etc. with section-scoped helpers: `_sectionEl(sectionRoot, '.explorer-config-type')` using `sectionRoot.querySelector()`.
   - Change all element IDs in `explorer_config_panel.html` to classes (e.g., `id="explorer-config-type"` → `class="explorer-config-type"`).
   - Keep the primary section's `id="section-objects"` for backward compat.
   - Each function (`applyExplorerConfig`, `resetExplorerConfig`, `loadSelectedConfig`, etc.) takes an optional `sectionRoot` parameter (defaults to `document.getElementById('section-objects')`).
   - The config state (_configActive, _optionsData) becomes per-section. Use a Map keyed by section element or section index.
2. Add 'Duplicate' button in OBJECTS section header in `backend/app/templates/browser/workspace.html`:
   - Button in the header-actions span, next to the existing gear/refresh/plus buttons.
   - onclick calls `window.SemPKM.duplicateExplorerSection()`.
3. Implement `duplicateExplorerSection()` in `explorer-config.js`:
   - Clones the section-objects element structure.
   - Assigns a unique suffix (e.g., `section-objects-1`) to the clone's ID.
   - Inserts the clone after the original section in the sidebar.
   - Initializes config options for the clone (reuses cached _optionsData).
   - Each clone gets its own config state, tree body, and selector.
   - Clone's tree starts empty or with default nav_tree.
   - Add a 'Close' button in the cloned section header (to remove it).
4. Update `frontend/static/css/explorer-config.css` for multi-panel styling (duplicate sections visually distinct or identical).
5. Ensure each section's config selector and config builder operate independently — changing type in section A doesn't affect section B.

Constraints:
- Primary section retains `id="section-objects"` for any code that references it directly.
- Duplicated sections use the existing drag-reorder (`data-panel-name`) and `explorer-section` patterns.
- Each section's active config (localStorage UUID) is stored with a section-scoped key (e.g., `sempkm_explorer_active_config_0`, `sempkm_explorer_active_config_1`).
- The `refreshExplorerTree()` export should continue to work on the primary section for backward compat. Add `refreshExplorerTreeForSection(sectionRoot)` for section-specific refresh.
- The summary bar, config panel, and tree body are all section-scoped — no cross-section state leaking.

## Inputs

- ``frontend/static/js/explorer-config.js` — T02's extended module with save/load/selector`
- ``backend/app/templates/browser/explorer_config_panel.html` — T02's updated panel template`
- ``backend/app/templates/browser/workspace.html` — existing workspace template with OBJECTS section`
- ``frontend/static/css/explorer-config.css` — T02's extended styles`

## Expected Output

- ``frontend/static/js/explorer-config.js` — refactored to section-scoped DOM access, duplicateExplorerSection added`
- ``backend/app/templates/browser/explorer_config_panel.html` — IDs changed to classes for multi-panel`
- ``backend/app/templates/browser/workspace.html` — Duplicate button added to OBJECTS header`
- ``frontend/static/css/explorer-config.css` — multi-panel styles added`

## Verification

Browser verification: click Duplicate → second OBJECTS section appears → configure each with different type filter/group → both render independently → close duplicate section → original unaffected. refreshExplorerTree() still works on primary section.
