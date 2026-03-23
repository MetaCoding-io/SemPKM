---
id: T03
parent: S05
milestone: M034
provides:
  - "Create from Template" parent command in ninja-keys palette with dynamic children from template API
  - 4 review workflow launcher commands (Weekly/Monthly/Quarterly/Yearly) in "Workflows" section
  - _refreshTemplatePaletteItems function for dynamic template palette population
  - _launchReviewWorkflow helper for review workflow lookup and tab opening
key_files:
  - frontend/static/js/workspace.js
key_decisions:
  - Template instantiation handler calls POST /api/task-templates/{id}/instantiate and opens the first created_iris via openTab() — same tab-opening pattern as other object creation flows
  - Review workflow launchers fetch the full workflow list and find by name match rather than hardcoding IDs — resilient to ID changes across reinstalls
patterns_established:
  - _refreshTemplatePaletteItems follows the exact same pattern as _refreshPersonaPaletteItems (filter by prefix, build children, update parent's children array, reassign ninja.data)
  - _launchReviewWorkflow uses name-based lookup with user-friendly toast on failure ("Is the PPV model installed?")
observability_surfaces:
  - console.warn on template palette refresh failure
  - console.error + user toast on template instantiation or workflow launch failure
  - Browser console inspection via document.querySelector('ninja-keys').data.filter(d => d.id.startsWith('template-') || d.id.startsWith('run-'))
duration: 8m
verification_result: passed
completed_at: 2026-03-22T02:00:00-04:00
blocker_discovered: false
---

# T03: Command palette integration for templates and review workflows

**Added "Create from Template" parent command with dynamic API children and 4 review workflow launchers to the ninja-keys command palette**

## What Happened

Added 6 new command palette entries to `frontend/static/js/workspace.js`:

1. **"Create from Template"** — a parent entry in the "Objects" section with `children: []` populated dynamically by `_refreshTemplatePaletteItems(ninja)`. The function fetches `GET /api/task-templates`, creates child entries prefixed with `template-`, and wires each child's handler to call `POST /api/task-templates/{id}/instantiate` then open the created object via `openTab(primaryIri, templateTitle)`.

2. **4 review workflow launchers** — static entries in a "Workflows" section (Run Weekly/Monthly/Quarterly/Yearly Review), each calling `_launchReviewWorkflow(name)`. The helper fetches `GET /api/workflow`, finds the workflow by exact name match, and opens it via `openWorkflowTab(id, name)`. Missing workflows show a toast with guidance about the PPV model.

Both new functions follow established patterns: `_refreshTemplatePaletteItems` mirrors `_refreshPersonaPaletteItems` exactly (filter by prefix, collect child IDs, update parent's children array, reassign ninja.data). `_launchReviewWorkflow` uses the same error-handling style as other palette handlers (console.error + showToast).

The `_refreshTemplatePaletteItems(ninja)` call is placed in the init block alongside the existing `_refreshPersonaPaletteItems(ninja)` and `_refreshLayoutPaletteItems(ninja)` calls.

## Verification

All task-level checks pass:
- "Create from Template" entry confirmed in workspace.js
- "Run Weekly Review" entry confirmed
- `_refreshTemplatePaletteItems` defined and called during init
- `_launchReviewWorkflow` defined and wired to all 4 review handlers
- JS syntax validated via `new Function()` constructor (acorn not installed, equivalent check)

All slice-level checks pass for cumulative scope:
- Seed idempotency tests: 10/10 pass
- Named graph usage confirmed
- Palette entries confirmed
- Python syntax valid
- Structured logging confirmed
- Error responses confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg "Create from Template" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 2 | `rg "Run Weekly Review" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 3 | `rg "_refreshTemplatePaletteItems" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 4 | `rg "_launchReviewWorkflow" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 5 | `node -e "new Function(require('fs').readFileSync('frontend/static/js/workspace.js','utf8'))"` | 0 | ✅ pass | <1s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v` | 0 | ✅ pass (10/10) | 0.2s |
| 7 | `rg "urn:sempkm:task-templates" backend/app/task_templates/service.py` | 0 | ✅ pass | <1s |
| 8 | `python3 -c "import ast; ast.parse(open('backend/app/task_templates/service.py').read()); ast.parse(open('backend/app/task_templates/router.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 9 | `rg "logger\." backend/app/task_templates/service.py \| head -5` | 0 | ✅ pass | <1s |
| 10 | `rg "status_code=4" backend/app/task_templates/router.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect palette entries at runtime:** Open browser console → `document.querySelector('ninja-keys').data.filter(d => d.id.startsWith('template-') || d.id.startsWith('run-'))` shows loaded template children and review workflow entries
- **Template refresh failures:** Check console for `SemPKM: template palette refresh failed:` warning
- **Workflow launch failures:** Check console for `SemPKM: review workflow launch failed:` error; user sees toast with message
- **Instantiation failures:** Check console for `SemPKM: template instantiation failed:` error; user sees toast with error detail

## Deviations

- Task plan specified response field `results` but actual endpoint returns `created_iris` — adapted handler to use `result.created_iris[0]` per the real router implementation.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — added "Create from Template" parent entry, 4 review workflow launcher entries, `_refreshTemplatePaletteItems()` function, `_launchReviewWorkflow()` helper, and init call for template refresh
- `.gsd/milestones/M034/slices/S05/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
