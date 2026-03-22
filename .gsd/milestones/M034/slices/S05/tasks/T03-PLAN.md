---
estimated_steps: 4
estimated_files: 1
skills_used:
  - best-practices
  - review
---

# T03: Command palette integration for templates and review workflows

**Slice:** S05 — Task Templates & Review Workflows
**Milestone:** M034

## Description

Add task template and review workflow entries to the ninja-keys command palette. "Create from Template" is a parent entry whose children are dynamically populated from the template API (same pattern as "Persona: Switch To..." and "Layout: Restore..."). Review workflow launchers are static entries that fetch the workflow ID by name from `/api/workflow`, then open the stepper via `openWorkflowTab()`.

## Steps

1. **Add "Create from Template" parent entry** to the `ninja.data` base array in `frontend/static/js/workspace.js` (around line 1415, in the existing ninja.data initialization block):
   ```javascript
   {
     id: 'create-from-template',
     title: 'Create from Template',
     section: 'Objects',
     children: []  // populated by _refreshTemplatePaletteItems
   }
   ```

2. **Add `_refreshTemplatePaletteItems(ninja)` function** following the `_refreshPersonaPaletteItems` pattern (around line 2631):
   - `fetch('/api/task-templates')` to get template list
   - Filter out existing `template-` prefixed entries from `ninja.data`
   - For each template, push a child entry with `parent: 'create-from-template'`
   - Handler: `fetch('/api/task-templates/{id}/instantiate', { method: 'POST' })` → parse response → `openTab(result.iri, template.title)` to open the created task
   - Update parent's `children` array with child IDs
   - Assign `ninja.data = newData`

3. **Add review workflow launcher entries** to the `ninja.data` base array:
   ```javascript
   { id: 'run-weekly-review', title: 'Run Weekly Review', section: 'Workflows',
     handler: function() { _launchReviewWorkflow('Weekly Review'); } },
   { id: 'run-monthly-review', title: 'Run Monthly Review', section: 'Workflows',
     handler: function() { _launchReviewWorkflow('Monthly Review'); } },
   { id: 'run-quarterly-review', title: 'Run Quarterly Review', section: 'Workflows',
     handler: function() { _launchReviewWorkflow('Quarterly Review'); } },
   { id: 'run-yearly-review', title: 'Run Yearly Review', section: 'Workflows',
     handler: function() { _launchReviewWorkflow('Yearly Review'); } }
   ```
   Add `_launchReviewWorkflow(name)` helper that:
   - `fetch('/api/workflow')` → find workflow by name match
   - If found: `openWorkflowTab(workflow.id, workflow.name)`
   - If not found: `showToast('Review workflow not found. Is the PPV model installed?', 4000)`

4. **Call `_refreshTemplatePaletteItems(ninja)`** during the ninja-keys initialization (around line 1651, alongside the existing `_refreshLayoutPaletteItems(ninja)` and `_refreshPersonaPaletteItems(ninja)` calls).

## Must-Haves

- [ ] "Create from Template" parent entry in command palette with dynamic children from API
- [ ] `_refreshTemplatePaletteItems` follows the `_refreshPersonaPaletteItems` pattern exactly
- [ ] 4 review workflow launcher entries in "Workflows" section
- [ ] `_launchReviewWorkflow` gracefully handles missing workflows (PPV model not installed)
- [ ] Template instantiation handler opens the created task in a dockview tab

## Verification

- `rg "Create from Template" frontend/static/js/workspace.js` — entry exists
- `rg "Run Weekly Review" frontend/static/js/workspace.js` — entry exists
- `rg "_refreshTemplatePaletteItems" frontend/static/js/workspace.js` — function defined and called
- `rg "_launchReviewWorkflow" frontend/static/js/workspace.js` — helper defined
- `node -e "require('acorn').parse(require('fs').readFileSync('frontend/static/js/workspace.js','utf8'),{ecmaVersion:2020,sourceType:'script'}); console.log('OK')"` — JS syntax valid (or equivalent `node --check` approach)

## Inputs

- `frontend/static/js/workspace.js` — ninja-keys initialization (line ~1404), `_refreshPersonaPaletteItems` pattern (line ~2631), `openWorkflowTab` function (line ~889)
- `backend/app/task_templates/router.py` — API endpoints: `GET /api/task-templates` (list), `POST /api/task-templates/{id}/instantiate` (returns `{results: [{iri, ...}]}`)
- `backend/app/workflow/router.py` — `GET /api/workflow` returns `[{id, name, ...}]`

## Expected Output

- `frontend/static/js/workspace.js` — updated with template palette entries, review workflow launchers, `_refreshTemplatePaletteItems`, and `_launchReviewWorkflow`
