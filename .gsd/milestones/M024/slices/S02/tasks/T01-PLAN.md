---
estimated_steps: 8
estimated_files: 6
---

# T01: Column mapping configuration routes, templates, and client extension

**Slice:** S02 — Column mapping configuration UI + pull sync
**Milestone:** M024

## Description

Build the column mapping configuration UI — the novel, highest-risk work in this slice. Monday.com's fully customizable columns require a multi-step setup wizard where users map Monday.com columns to bpkm properties via type-filtered dropdowns, then map custom status/priority labels to bpkm enum values.

Also extends `MondayClient` to include `group { id title }` in the items query (needed by the sync engine in T02) and adds a `get_subitems()` method.

**Relevant skills:** None specific needed; follows htmx + Jinja2 template patterns established in the codebase.

## Steps

1. **Add `COLUMN_TYPE_COMPATIBILITY` constant to `app.py`** (or a helper section at top of file). This dict maps bpkm property short names to lists of compatible Monday.com column types:
   ```python
   COLUMN_TYPE_COMPATIBILITY = {
       "taskStatus": ["status"],
       "priority": ["status", "color"],
       "dueDate": ["date", "timeline"],
       "assignedTo": ["people"],
       "description": ["text", "long_text"],
       "estimatedEffort": ["numbers"],
       "tags": ["tags", "dropdown"],
       "dependency": ["dependency"],
   }
   ```
   Also add a human-readable labels dict for the template:
   ```python
   BPKM_PROPERTY_LABELS = {
       "taskStatus": "Status",
       "priority": "Priority",
       "dueDate": "Due Date",
       "assignedTo": "Assignee",
       "description": "Description",
       "estimatedEffort": "Estimated Effort",
       "tags": "Tags",
   }
   ```
   And bpkm taskStatus/priority enum values:
   ```python
   BPKM_STATUS_VALUES = ["todo", "in-progress", "done", "blocked", "cancelled"]
   BPKM_PRIORITY_VALUES = ["critical", "high", "medium", "low"]
   ```

2. **Add `configure-columns` GET route to `app.py`**. Route: `/_fragments/settings/configure-columns`. Query params: `board_id`. Steps: fetch board columns via `client.get_board_columns(int(board_id))`, filter columns for each bpkm property using `COLUMN_TYPE_COMPATIBILITY`, read existing mapping from settings (key: `column_mapping_{board_id}`), render `configure_columns.html` with the columns, compatibility data, existing mapping, and board_id. If no board_id provided, return an error message.

3. **Add `save-column-mapping` POST route to `app.py`**. Route: `/_fragments/settings/save-column-mapping`. Form fields: `board_id` + one field per bpkm property (e.g., `mapping_taskStatus`, `mapping_priority`, etc.). Build the column_mapping dict from form values (skip empty selections). Save as JSON string to settings key `column_mapping_{board_id}`. Return the connect_status fragment.

4. **Add `configure-labels` GET route to `app.py`**. Route: `/_fragments/settings/configure-labels`. Query params: `board_id`. Steps: read column mapping from settings to find which column IDs are mapped to `taskStatus` and `priority`. Fetch board columns via `get_board_columns()`. For the status column, parse its `settings_str` JSON to extract `labels` dict (e.g., `{"0": "", "1": "Working on it", "2": "Done", "5": "Stuck"}`). For the priority column, same pattern. Read existing label mappings from settings (key: `label_mapping_{board_id}`). Render `configure_labels.html` with status labels, priority labels, existing mappings, and bpkm enum values.

   **Important:** `settings_str` is a JSON *string*, not a dict. Must parse with `json.loads()`. Handle empty/malformed `settings_str` gracefully (return empty labels list). The empty string label `""` in Monday.com means "Default / Not Started" — show it in the UI with that label.

5. **Add `save-label-mapping` POST route to `app.py`**. Route: `/_fragments/settings/save-label-mapping`. Form fields: `board_id` + `status_label_{index}` for each status label + `priority_label_{index}` for each priority label. Build `status_label_mapping` and `priority_label_mapping` dicts from form values. Save as JSON to settings key `label_mapping_{board_id}`. Return the connect_status fragment.

6. **Create `configure_columns.html` template**. Location: `apps/monday-sync/frontend/templates/configure_columns.html`. Structure:
   ```html
   <div id="connect-content" class="monday-sync-settings">
     <h3>Column Mapping — {{ board_name }}</h3>
     <p class="section-hint">Map Monday.com columns to SemPKM task properties. Only compatible column types are shown.</p>
     <form hx-post="/app/monday-sync/_fragments/settings/save-column-mapping"
           hx-target="#connect-content" hx-swap="innerHTML">
       <input type="hidden" name="board_id" value="{{ board_id }}">
       {% for bpkm_prop, label in property_labels.items() %}
       <div class="mapping-row">
         <label>{{ label }}</label>
         <select name="mapping_{{ bpkm_prop }}" class="config-select">
           <option value="">— None —</option>
           {% for col in compatible_columns[bpkm_prop] %}
           <option value="{{ col.id }}"
                   {% if current_mapping.get(bpkm_prop) == col.id %}selected{% endif %}>
             {{ col.title }} ({{ col.type }})
           </option>
           {% endfor %}
         </select>
       </div>
       {% endfor %}
       <div class="form-actions">
         <button type="submit" class="btn btn-primary">Save Column Mapping</button>
         <a href="#" class="btn-link"
            hx-get="/app/monday-sync/_fragments/connect"
            hx-target="#connect-content" hx-swap="innerHTML">Cancel</a>
       </div>
     </form>
   </div>
   ```
   Use the `current_mapping` context to pre-select existing mappings.

7. **Create `configure_labels.html` template**. Location: `apps/monday-sync/frontend/templates/configure_labels.html`. Structure:
   ```html
   <div id="connect-content" class="monday-sync-settings">
     <h3>Label Mapping — {{ board_name }}</h3>
     <p class="section-hint">Map Monday.com status and priority labels to SemPKM values.</p>
     <form hx-post="/app/monday-sync/_fragments/settings/save-label-mapping"
           hx-target="#connect-content" hx-swap="innerHTML">
       <input type="hidden" name="board_id" value="{{ board_id }}">
       
       {% if status_labels %}
       <fieldset class="mapping-fieldset">
         <legend>Status Labels</legend>
         {% for idx, label_text in status_labels %}
         <div class="mapping-row">
           <span class="source-label">{{ label_text if label_text else "Default / Not Started" }}</span>
           <select name="status_label_{{ idx }}" class="config-select">
             {% for val in bpkm_status_values %}
             <option value="{{ val }}"
                     {% if current_status_mapping.get(label_text, "") == val %}selected{% endif %}>
               {{ val }}
             </option>
             {% endfor %}
           </select>
         </div>
         {% endfor %}
       </fieldset>
       {% endif %}
       
       {% if priority_labels %}
       <fieldset class="mapping-fieldset">
         <legend>Priority Labels</legend>
         {% for idx, label_text in priority_labels %}
         <div class="mapping-row">
           <span class="source-label">{{ label_text if label_text else "Default" }}</span>
           <select name="priority_label_{{ idx }}" class="config-select">
             <option value="">— None —</option>
             {% for val in bpkm_priority_values %}
             <option value="{{ val }}"
                     {% if current_priority_mapping.get(label_text, "") == val %}selected{% endif %}>
               {{ val }}
             </option>
             {% endfor %}
           </select>
         </div>
         {% endfor %}
       </fieldset>
       {% endif %}
       
       <div class="form-actions">
         <button type="submit" class="btn btn-primary">Save Label Mapping</button>
         <a href="#" class="btn-link"
            hx-get="/app/monday-sync/_fragments/connect"
            hx-target="#connect-content" hx-swap="innerHTML">Cancel</a>
       </div>
     </form>
   </div>
   ```

8. **Update `connect_status.html`** — After the board selection section, add a "Column Mapping" section per selected board:
   ```html
   {# ── Column Mapping ── #}
   {% if selected_boards %}
   <section class="column-mapping-section">
     <h4>Column Mapping</h4>
     <p class="section-hint">Configure how Monday.com columns map to SemPKM task properties.</p>
     {% for board in boards if board.id | string in selected_boards %}
     <div class="board-mapping-row">
       <span class="board-name">{{ board.name }}</span>
       {% if board.id | string in configured_boards %}
       <span class="mapping-status mapping-configured">✓ Configured</span>
       {% else %}
       <span class="mapping-status mapping-pending">Not configured</span>
       {% endif %}
       <a class="btn btn-sm"
          hx-get="/app/monday-sync/_fragments/settings/configure-columns?board_id={{ board.id }}"
          hx-target="#connect-content"
          hx-swap="innerHTML">Configure Columns</a>
       {% if board.id | string in configured_boards %}
       <a class="btn btn-sm"
          hx-get="/app/monday-sync/_fragments/settings/configure-labels?board_id={{ board.id }}"
          hx-target="#connect-content"
          hx-swap="innerHTML">Configure Labels</a>
       {% endif %}
     </div>
     {% endfor %}
   </section>
   {% endif %}
   ```
   Update `_render_connect_status()` in `app.py` to compute `configured_boards` — a set of board_id strings that have a `column_mapping_{board_id}` key in settings. Pass it to the template.

9. **Extend `MondayClient.get_board_items()`** — Add `group { id title }` to the GraphQL items query. Current query:
   ```
   items { id name column_values { id text type value } }
   ```
   Change to:
   ```
   items { id name group { id title } column_values { id text type value } }
   ```
   This is a one-field addition to the query string. Both the paginated and non-paginated variants need it.

10. **Add `get_subitems()` method to MondayClient** — Method signature: `async def get_subitems(self, item_ids: list[int]) -> list[dict]`. GraphQL query: `{ items(ids: [...]) { id subitems { id name group { id title } column_values { id text type value } } } }`. Returns a flat list of subitem dicts, each augmented with `parent_item_id` from the outer item.

11. **Add CSS for column mapping forms** — Append to `styles.css`:
   ```css
   /* ── Column Mapping ── */
   .monday-sync-settings .column-mapping-section { margin-bottom: 1.5rem; }
   .monday-sync-settings .column-mapping-section h4 { /* same as other h4s */ }
   .monday-sync-settings .mapping-row {
     display: flex; align-items: center; gap: 0.75rem;
     padding: 0.4rem 0; border-bottom: 1px solid var(--color-border, #333);
   }
   .monday-sync-settings .mapping-row label { min-width: 140px; font-size: 0.85rem; font-weight: 600; }
   .monday-sync-settings .mapping-row select { flex: 1; }
   .monday-sync-settings .mapping-fieldset { border: 1px solid var(--color-border, #333); border-radius: 6px; padding: 1rem; margin-bottom: 1rem; }
   .monday-sync-settings .mapping-fieldset legend { font-size: 0.85rem; font-weight: 600; padding: 0 0.5rem; }
   .monday-sync-settings .source-label { min-width: 160px; font-size: 0.85rem; }
   .monday-sync-settings .board-mapping-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.4rem 0; }
   .monday-sync-settings .mapping-status { font-size: 0.8rem; }
   .monday-sync-settings .mapping-configured { color: #3fb950; }
   .monday-sync-settings .mapping-pending { color: var(--color-text-muted, #888); }
   .monday-sync-settings .btn-sm { padding: 0.25rem 0.6rem; font-size: 0.8rem; }
   .monday-sync-settings .btn-link { color: var(--color-link, #5e9ed6); font-size: 0.85rem; text-decoration: none; }
   ```

## Must-Haves

- [ ] `COLUMN_TYPE_COMPATIBILITY` constant is correct — each bpkm property maps to the right Monday.com column types
- [ ] `configure-columns` GET route fetches board columns and renders type-filtered dropdowns
- [ ] `save-column-mapping` POST route saves per-board mapping as JSON in settings
- [ ] `configure-labels` GET route parses `settings_str` to discover status/priority labels
- [ ] `save-label-mapping` POST route saves label mappings as JSON in settings
- [ ] `configure_columns.html` template exists with dropdown per bpkm property
- [ ] `configure_labels.html` template exists with status/priority label mapping
- [ ] `connect_status.html` shows "Configure Columns" link per selected board with status indicator
- [ ] `get_board_items` query now includes `group { id title }`
- [ ] `get_subitems` method exists on MondayClient
- [ ] All htmx URLs use `/app/monday-sync/` prefix per KNOWLEDGE.md
- [ ] All Python files pass `ast.parse()` syntax check
- [ ] Empty/malformed `settings_str` handled gracefully (no crash)

## Verification

- `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` — passes
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/monday_client.py').read())"` — passes
- `ls apps/monday-sync/frontend/templates/configure_columns.html apps/monday-sync/frontend/templates/configure_labels.html` — both exist
- `grep -c "group {" apps/monday-sync/services/monday_client.py` — at least 2 (paginated + non-paginated query variants)
- `grep -c "get_subitems" apps/monday-sync/services/monday_client.py` — at least 1
- `grep -c "configure-columns" apps/monday-sync/app.py` — at least 2 (route + handler)
- `grep "COLUMN_TYPE_COMPATIBILITY" apps/monday-sync/app.py` — present
- Existing S01 tests still pass: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py tests/test_monday_person_matcher.py -v`

## Observability Impact

- **New settings keys visible in state:** `column_mapping_{board_id}` (JSON dict of bpkm property → Monday.com column ID) and `label_mapping_{board_id}` (JSON dict with `status_label_mapping` and `priority_label_mapping` sub-dicts). Both are inspectable via the SDK state client.
- **Failure surfaces:** Column mapping routes return HTML error messages for missing `board_id`, missing columns, or malformed `settings_str`. Errors are visible in the rendered htmx fragment — no silent failures.
- **Logging:** All save operations log at INFO level via the `monday_sync` logger with the board_id and number of mapped fields. Failed `settings_str` parsing logs at WARNING with the board_id.
- **Template inspection:** `configured_boards` set passed to `connect_status.html` shows which boards have column mappings — agents can verify mapping completeness by checking the "✓ Configured" vs "Not configured" indicators.

## Inputs

- `apps/monday-sync/app.py` — existing routes from S01 (6 routes: connect, credentials, disconnect, boards, sync-config, sync-now)
- `apps/monday-sync/services/monday_client.py` — existing client with 10 convenience methods
- `apps/monday-sync/frontend/templates/connect_status.html` — existing connected state template
- `apps/monday-sync/frontend/static/styles.css` — existing scoped CSS
- S01 summary: field mapper accepts `column_mapping`, `status_label_mapping`, `priority_label_mapping` as parameters; `get_board_columns()` returns column metadata with `id`, `title`, `type`, `settings_str`

## Expected Output

- `apps/monday-sync/app.py` — 4 new routes + COLUMN_TYPE_COMPATIBILITY + BPKM_PROPERTY_LABELS + _render_connect_status updated with configured_boards
- `apps/monday-sync/services/monday_client.py` — group field in items query, get_subitems() method
- `apps/monday-sync/frontend/templates/configure_columns.html` — NEW column mapping form
- `apps/monday-sync/frontend/templates/configure_labels.html` — NEW label mapping form
- `apps/monday-sync/frontend/templates/connect_status.html` — updated with column mapping section
- `apps/monday-sync/frontend/static/styles.css` — updated with column mapping styles
