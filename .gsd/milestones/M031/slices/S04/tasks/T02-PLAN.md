---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T02: Kanban template, CSS, drag-drop JS, and view wiring

**Slice:** S04 — Kanban Renderer
**Milestone:** M031

## Description

Create the frontend for the kanban view: a Jinja2 template rendering status columns with draggable cards, CSS for the board layout, a JS module handling HTML5 drag-drop with dockview isolation and status patching via `object.patch`, and all wiring (explorer sidebar entry, base.html script tag, workspace.js label).

## Steps

1. **Create `kanban_view.html` template**
   - Path: `backend/app/templates/browser/kanban_view.html`
   - Follow the exact same opening pattern as `cards_view.html`:
     ```jinja2
     {% if is_generic | default(false) %}
     {% include "browser/type_filter_pills.html" %}
     {% endif %}
     {% include "browser/view_toolbar.html" %}
     ```
   - If `columns` is empty or not defined (no type selected / no status property):
     ```html
     <div class="view-empty-state">
       <p>{{ empty_message | default("Select a type with status values to use Kanban View.") }}</p>
     </div>
     ```
   - When columns exist, render the kanban board:
     ```html
     <div class="kanban-board" data-status-predicate="{{ status_field.path }}">
       {% for col in columns %}
       <div class="kanban-column" data-status="{{ col.value }}">
         <div class="kanban-column-header">
           <span class="kanban-column-title">{{ col.label }}</span>
           <span class="kanban-column-count">{{ col.items | length }}</span>
         </div>
         <div class="kanban-column-body">
           {% for item in col.items %}
           <div class="kanban-card" draggable="true" data-iri="{{ item.iri }}">
             <span class="kanban-card-title" onclick="openTab('{{ item.iri }}', '{{ item.label | replace("'", "\\'") }}'); return false;">{{ item.label }}</span>
           </div>
           {% endfor %}
         </div>
       </div>
       {% endfor %}
     </div>
     ```
   - At the bottom, add initialization script: `<script>if (typeof initKanban === 'function') { initKanban(document.querySelector('.kanban-board')); }</script>`
   - Template context variables (from T01's router branch): `columns`, `status_field`, `empty_message`, `type_label`, `type_iri`, `selected_type`, `types`, `model_view_specs`, `scope_query`, `user_saved_queries`, `model_saved_queries`, `is_generic`, `renderer`, `spec`, `pagination_base_url`, `pag_extra`, `sort_col`, `sort_dir`, `current_filter`, `page_size`

2. **Add kanban CSS to `views.css`**
   - Path: `frontend/static/css/views.css` — append at the end of the file
   - Key classes and their styles:
     ```css
     /* ── Kanban Board ── */
     .kanban-board { display: flex; gap: 12px; padding: 12px; overflow-x: auto; height: 100%; align-items: flex-start; }
     .kanban-column { min-width: 250px; max-width: 300px; flex-shrink: 0; background: var(--color-surface-raised); border-radius: 8px; display: flex; flex-direction: column; max-height: 100%; }
     .kanban-column-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid var(--color-border); font-weight: 600; }
     .kanban-column-title { font-size: 0.85rem; text-transform: capitalize; }
     .kanban-column-count { font-size: 0.75rem; color: var(--color-text-muted); background: var(--color-surface); border-radius: 10px; padding: 2px 8px; }
     .kanban-column-body { overflow-y: auto; flex: 1; padding: 8px; min-height: 60px; }
     .kanban-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; cursor: grab; transition: box-shadow 0.15s, border-color 0.15s; }
     .kanban-card:hover { border-color: var(--color-border-strong); box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
     .kanban-card.dragging { opacity: 0.5; cursor: grabbing; }
     .kanban-card-title { font-size: 0.85rem; cursor: pointer; color: var(--color-text); }
     .kanban-card-title:hover { color: var(--color-primary); text-decoration: underline; }
     .kanban-column.drag-over { background: var(--color-surface-hover, var(--color-surface-raised)); border: 2px dashed var(--color-primary); }
     ```
   - Use existing CSS custom properties from the theme (check what `--color-surface-raised`, `--color-border`, etc. resolve to by looking at existing usage in `views.css`)

3. **Create `kanban.js` drag-drop module**
   - Path: `frontend/static/js/kanban.js`
   - Self-contained module (~80–100 lines):
     ```javascript
     function initKanban(boardEl) {
       if (!boardEl) return;
       // Attach listeners to cards and columns
       boardEl.querySelectorAll('.kanban-card').forEach(function(card) {
         card.addEventListener('dragstart', onDragStart, false);
         card.addEventListener('dragend', onDragEnd, false);
       });
       boardEl.querySelectorAll('.kanban-column-body').forEach(function(col) {
         col.addEventListener('dragover', onDragOver, false);
         col.addEventListener('dragleave', onDragLeave, false);
         col.addEventListener('drop', onDrop, false);
       });
     }
     ```
   - `onDragStart(e)`: set `e.dataTransfer.setData('text/plain', card.dataset.iri)`, add `.dragging` class, call `e.stopPropagation()` to prevent dockview from intercepting
   - `onDragEnd(e)`: remove `.dragging` class
   - `onDragOver(e)`: `e.preventDefault()`, `e.stopPropagation()`, add `.drag-over` class to the closest `.kanban-column`
   - `onDragLeave(e)`: remove `.drag-over` class from the closest `.kanban-column`
   - `onDrop(e)`: `e.preventDefault()`, `e.stopPropagation()`, remove `.drag-over`, read IRI from `dataTransfer`, get target column's `data-status` (go up to `.kanban-column`), get predicate from board's `data-status-predicate`, call `patchStatus(iri, predicate, newStatus, cardEl, targetBody)`
   - `patchStatus(iri, predicate, newStatus, cardEl, targetBody)`:
     - Optimistic DOM move: `targetBody.appendChild(cardEl)`
     - Update column counts (both source and target)
     - POST to `/api/commands`:
       ```javascript
       fetch('/api/commands', {
         method: 'POST',
         headers: {'Content-Type': 'application/json'},
         body: JSON.stringify({
           command: 'object.patch',
           params: { iri: iri, properties: { [predicate]: newStatus } }
         })
       })
       ```
     - On success: `document.dispatchEvent(new CustomEvent('sempkm:command-executed'))`
     - On failure: `console.error(...)`, show toast if available, revert DOM move
   - Helper `_updateColumnCounts(boardEl)`: recount `.kanban-card` in each `.kanban-column-body` and update the `.kanban-column-count` span
   - Export: `window.initKanban = initKanban;`

4. **Wire kanban.js into base.html**
   - Add `<script src="{{ 'kanban.js' | asset_url }}"></script>` in `backend/app/templates/base.html` — insert after the `graph.js` line (line ~149)

5. **Add explorer entry and workspace.js label**
   - In `backend/app/templates/browser/views_explorer.html`, add a new Kanban View leaf after the Graph View entry, following the exact same pattern:
     ```html
     <a class="tree-leaf view-leaf" href="#"
        draggable="true"
        ondragstart="event.dataTransfer.setData('text/plain', 'Kanban View'); event.dataTransfer.effectAllowed = 'copy'; window.__canvasDragPayload = {type:'view', id:'generic-kanban', label:'Kanban View', url:'/browser/views/generic/kanban?embed=1'};"
        onclick="openGenericViewTab('kanban'); return false;">
         <span class="tree-leaf-icon">&#9707;</span>
         <span class="tree-leaf-label">Kanban View</span>
     </a>
     ```
   - In `frontend/static/js/workspace.js`, find the `var labels = { table: 'Table View', card: 'Cards View', graph: 'Graph View' };` line inside `openGenericViewTab()` (around line 3232) and add `kanban: 'Kanban View'`

## Must-Haves

- [ ] `kanban_view.html` renders type filter pills, view toolbar, and kanban board with columns and cards
- [ ] Empty state message shown when no type selected or no status property
- [ ] Kanban CSS provides flex column layout with horizontal scroll, drag states
- [ ] `kanban.js` handles drag-drop with `stopPropagation()` to prevent dockview interference
- [ ] Drop triggers `object.patch` POST to `/api/commands` with correct predicate and status value
- [ ] `sempkm:command-executed` event dispatched after successful patch
- [ ] Optimistic DOM card move on drop (with revert on failure)
- [ ] `kanban.js` loaded via `base.html` script tag
- [ ] "Kanban View" appears in explorer sidebar
- [ ] `openGenericViewTab('kanban')` creates a correctly labeled tab

## Verification

- `test -f backend/app/templates/browser/kanban_view.html` — template exists
- `test -f frontend/static/js/kanban.js` — JS module exists
- `grep -q 'Kanban View' backend/app/templates/browser/views_explorer.html` — explorer entry present
- `grep -q 'kanban' frontend/static/js/workspace.js` — label in openGenericViewTab
- `grep -q 'kanban.js' backend/app/templates/base.html` — script loaded
- `grep -q 'kanban-board' frontend/static/css/views.css` — CSS exists
- `grep -q 'initKanban' frontend/static/js/kanban.js` — init function defined
- `grep -q 'stopPropagation' frontend/static/js/kanban.js` — dockview isolation present

## Inputs

- `backend/app/views/router.py` — T01 added kanban branch that renders `kanban_view.html` with context variables
- `backend/app/views/service.py` — T01 added `execute_kanban_query()` returning `columns`, `status_field`, `total` data
- `backend/app/templates/browser/cards_view.html` — reference template pattern (type pills + toolbar includes)
- `backend/app/templates/browser/view_toolbar.html` — toolbar include with scope dropdown and variant select
- `backend/app/templates/browser/type_filter_pills.html` — type pills include
- `backend/app/templates/browser/views_explorer.html` — add kanban leaf entry
- `backend/app/templates/base.html` — add kanban.js script tag
- `frontend/static/js/workspace.js` — add kanban label to openGenericViewTab()
- `frontend/static/css/views.css` — add kanban CSS
- `frontend/static/js/app.js` — reference for object.patch command payload format (line ~174)

## Expected Output

- `backend/app/templates/browser/kanban_view.html` — new kanban view template
- `frontend/static/css/views.css` — modified with kanban board/column/card styles
- `frontend/static/js/kanban.js` — new drag-drop module
- `backend/app/templates/base.html` — modified with kanban.js script tag
- `backend/app/templates/browser/views_explorer.html` — modified with Kanban View leaf
- `frontend/static/js/workspace.js` — modified with kanban label in openGenericViewTab()
