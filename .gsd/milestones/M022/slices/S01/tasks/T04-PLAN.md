---
estimated_steps: 8
estimated_files: 2
---

# T04: Custom field discovery, mapping UI, and configuration persistence

**Slice:** S01 — OAuth + project selection + custom field mapping UI
**Milestone:** M022

## Description

This is the novel, highest-risk task — the "configure before sync" pattern that distinguishes Asana from all six prior sync apps. Asana has no native status or priority fields; these come from custom enum fields or section names that vary per workspace. The user must explicitly configure how their Asana setup maps to bpkm properties before sync can run.

The flow: user selects projects (T03) → clicks "Discover Fields" → app calls `client.get_custom_fields()` and `client.get_sections()` for each selected project → presents mapping UI → user configures status source (completed_only / custom_field / section), maps enum values or section names to bpkm:taskStatus values, selects priority field and maps enum values to bpkm:priority values, optionally selects story points field → saves configuration to StateClient.

The configuration is consumed by the field_mapper (S02) at sync time. This task only builds the discovery + UI + persistence — no actual sync.

## Steps

1. Add field discovery route to `apps/asana-sync/app.py`:
   - Route `/_fragments/settings/discover-fields` (POST):
     - Read `selected_projects` JSON from StateClient.
     - For each project: call `client.get_custom_fields(project_gid)` and `client.get_sections(project_gid)`.
     - Union custom fields across projects (deduplicate by GID). Track which projects each field appears in.
     - Separate fields by type: `enum_fields` (resource_subtype="enum"), `number_fields` (resource_subtype="number").
     - Collect all section names across selected projects (deduplicate by GID, track project).
     - Store discovered data in StateClient as JSON: `discovered_enum_fields`, `discovered_number_fields`, `discovered_sections`.
     - Re-render connect_status.html with discovered field data.

2. Add field mapping save route to `apps/asana-sync/app.py`:
   - Route `/_fragments/settings/field-mapping` (POST):
     - Read form data: `status_source` (completed_only/custom_field/section), `status_field_gid`, status mapping pairs (`status_map_{enum_option_name}` → bpkm value), `priority_field_gid`, priority mapping pairs (`priority_map_{enum_option_name}` → bpkm value), `story_points_field_gid`.
     - Build `status_mapping` dict: `{"EnumOptionName": "bpkm-status-value", ...}` (only when status_source is custom_field or section).
     - Build `priority_mapping` dict: `{"EnumOptionName": "bpkm-priority-value", ...}`.
     - Persist all to StateClient as separate JSON keys: `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid`.
     - Re-render connect_status.html with saved configuration.

3. Update `_render_connect_status()` in app.py to load all mapping configuration from StateClient and pass to template:
   - `discovered_enum_fields`, `discovered_number_fields`, `discovered_sections` (from discovery).
   - `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid` (from saved config).
   - `fields_discovered` boolean flag (true when discovered_enum_fields is non-empty).

4. Extend `apps/asana-sync/frontend/templates/connect_status.html` with field mapping sections after the project selection section:

   **"Discover Fields" button** — visible after projects are selected:
   ```html
   <section class="discover-section">
     <h4>Field Configuration</h4>
     <p class="section-hint">Discover custom fields from your selected projects to configure status and priority mapping.</p>
     <form hx-post="/app/asana-sync/_fragments/settings/discover-fields"
           hx-target="#connect-content" hx-swap="innerHTML">
       <button type="submit" class="btn btn-primary">Discover Fields</button>
     </form>
   </section>
   ```

   **Field Mapping form** — visible after discovery, wraps all mapping sections in one form that POSTs to `/_fragments/settings/field-mapping`:

   **(a) Status Mapping section:**
   - Radio group for `status_source`: "Completed only" (completed_only), "Custom field" (custom_field), "Section-based" (section).
   - When `custom_field`: show dropdown of discovered enum fields to select `status_field_gid`. Below it, show the selected field's enum options with bpkm:taskStatus value dropdown for each (options: todo, in-progress, done, blocked, cancelled).
   - When `section`: show discovered section names with bpkm:taskStatus value dropdown for each.
   - When `completed_only`: no additional UI (just completed=true→done, else→todo).
   - Pre-select saved values if configuration already exists.

   **(b) Priority Mapping section:**
   - Dropdown of discovered enum fields to select `priority_field_gid` (or "None — no priority mapping").
   - When a field is selected: show its enum options with bpkm:priority value dropdown for each (options: low, medium, high, critical).
   - Pre-select saved values.

   **(c) Story Points section:**
   - Dropdown of discovered number fields to select `story_points_field_gid` (or "None").
   - Pre-select saved value.

   **Save Configuration button** at bottom of form.

5. Add JavaScript to connect_status.html for conditional display:
   - Show/hide enum field selector and mapping table based on status_source radio selection.
   - When status_source is "custom_field" and user selects a different enum field from dropdown, update the mapping table rows to show that field's enum options. Use `data-options` attribute on the field selector options containing JSON-encoded enum option names.
   - When status_source is "section", show section mapping table instead.
   - Minimal inline `<script>` — no external JS file needed. This is a configuration form, not a dynamic SPA.

6. Add CSS to `styles.css` for the mapping UI:
   - `.mapping-table` — bordered table with label + dropdown columns.
   - `.status-source-radios` — radio group styling.
   - `.field-selector` — dropdown styling consistent with existing config-select.
   - `.discover-section`, `.mapping-section` — section spacing.

7. Verify:
   - `python -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — no syntax errors.
   - `grep -c 'status_source' apps/asana-sync/frontend/templates/connect_status.html` — status source radios present.
   - `grep -c 'priority_field_gid' apps/asana-sync/frontend/templates/connect_status.html` — priority field selector present.
   - `grep -c 'story_points_field_gid' apps/asana-sync/frontend/templates/connect_status.html` — story points selector present.
   - All htmx URLs use `/app/asana-sync/` prefix.
   - T01 and T02 tests still pass: `python -m pytest backend/tests/test_asana_auth.py backend/tests/test_asana_client.py -v`

8. Commit: `feat(asana-sync): add custom field discovery, mapping UI, and configuration persistence`

## Must-Haves

- [ ] Field discovery route that unions custom fields across selected projects
- [ ] Status source selection: completed_only / custom_field / section
- [ ] Status mapping table: enum option names → bpkm:taskStatus dropdowns (when custom_field or section)
- [ ] Priority mapping: enum field selector + enum option names → bpkm:priority dropdowns
- [ ] Story points mapping: number field selector
- [ ] All configuration persisted as JSON in StateClient (status_source, status_field_gid, status_mapping, priority_field_gid, priority_mapping, story_points_field_gid)
- [ ] Conditional display: mapping tables appear/change based on status_source selection
- [ ] Pre-population of saved configuration on page load
- [ ] All htmx URLs use `/app/asana-sync/` prefix

## Verification

- `python -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — no syntax errors
- `grep 'status_source' apps/asana-sync/frontend/templates/connect_status.html` — status source UI present
- `grep 'priority_field_gid' apps/asana-sync/frontend/templates/connect_status.html` — priority field UI present
- `grep 'story_points_field_gid' apps/asana-sync/frontend/templates/connect_status.html` — story points UI present
- `grep '/app/asana-sync/' apps/asana-sync/frontend/templates/connect_status.html | wc -l` — all htmx URLs use prefix
- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_auth.py backend/tests/test_asana_client.py -v` — no regressions

## Inputs

- `apps/asana-sync/app.py` (from T03) — app shell with existing routes and `_render_connect_status()` helper
- `apps/asana-sync/frontend/templates/connect_status.html` (from T03) — status page to extend with mapping sections
- `apps/asana-sync/services/asana_client.py` (from T02) — `get_custom_fields()` and `get_sections()` methods
- `.gsd/milestones/M022/M022-RESEARCH.md` — state shape example showing JSON structure for all mapping keys
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §1 — Asana status normalization (3 modes), priority mapping, custom field strategy table
- T03 summary — app.py route structure and template variables

## Observability Impact

- **Logger:** `asana.sync.app` logs field discovery events (project count, field counts by type, section count) and field mapping saves (status_source, field counts)
- **StateClient keys:** `discovered_enum_fields`, `discovered_number_fields`, `discovered_sections` — JSON arrays persisted after discovery; inspectable via `ctx.state.get(key)`
- **StateClient keys:** `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid` — JSON values persisted after mapping save
- **Failure visibility:** `AsanaAPIError` during field discovery is caught and logged at WARNING; the status page still renders without field data. Form validation errors for missing status_source are returned as HTML alerts.
- **Inspection:** `fields_discovered` boolean template var controls whether the mapping form is shown — a `False` value after clicking "Discover Fields" indicates API failures or no custom fields on selected projects

## Expected Output

- `apps/asana-sync/app.py` — extended with discover-fields and field-mapping routes, updated _render_connect_status() (~400+ lines total)
- `apps/asana-sync/frontend/templates/connect_status.html` — complete with project selection + field discovery + status/priority/story-points mapping UI sections
- `apps/asana-sync/frontend/static/styles.css` — extended with mapping table and field selector styles
