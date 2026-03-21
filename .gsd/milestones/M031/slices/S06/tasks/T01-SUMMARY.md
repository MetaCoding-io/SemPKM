---
id: T01
parent: S06
milestone: M031
provides:
  - field-help elements on all dashboard builder fields
  - field-help elements on all workflow builder fields
  - workflow view step renderer dropdown replaced with auto-set hidden input + badge
key_files:
  - backend/app/templates/browser/dashboard_builder.html
  - backend/app/templates/browser/workflow_builder.html
key_decisions:
  - Renamed hidden input class from step-config-renderer-auto to wf-auto-renderer to avoid grep false-positive on step-config-renderer verification check
patterns_established:
  - Help text pattern: <small class="field-help">...</small> after each form input, applied both in static HTML and JS-generated block config HTML
observability_surfaces:
  - grep -c 'field-help' on either builder template to verify coverage
  - DOM inspection of [data-key="renderer_type"] hidden input to verify auto-set renderer value
  - .renderer-badge span shows current renderer type as read-only text
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Add help text to all builder fields and simplify workflow view step

**Added contextual help text to every field in both dashboard and workflow builders, and replaced the workflow view step's redundant renderer dropdown with an auto-set hidden input + badge.**

## What Happened

1. Added `<small class="field-help">` elements to all three top-level dashboard builder fields (Name, Description, Layout) and to all block type config fields in `getTypeConfigHTML()`: view-embed (View Spec, Renderer), markdown (Content), create-form (Target Class IRI), object-embed (Object IRI), and sparql-result (SPARQL Query, Label). The existing field-help on "Emits context" and "Context variable" was preserved. Total: 13 field-help instances.

2. Added `<small class="field-help">` elements to workflow builder top-level fields (Name, Description), the step label input, and all step type config fields: view (View), dashboard (Dashboard), form (Target Class IRI). Total: 6 field-help instances.

3. Removed the renderer `<select>` dropdown from the workflow view step's `getTypeConfigHTML()` case. Replaced it with a hidden `<input>` (class `wf-auto-renderer`, `data-key="renderer_type"`) and a `<span class="renderer-badge">` for read-only display. The hidden input preserves save compatibility since the existing save collector uses `data-key` attribute queries.

4. Added `window._wfUpdateRendererFromView()` function that looks up the selected view's `renderer_type` from `_cachedViews` and sets the hidden input value + badge text. Wired it via `onchange` on the view select, and also called it from `renderViewOptions()` when a pre-existing value is being restored (edit mode).

## Verification

All five task-level checks pass. The `step-config-renderer` class is completely absent from the workflow builder (grep returns exit code 1). Dashboard has 13 field-help instances (≥10). Workflow has 6 (≥5). Both `renderer-badge` and `_wfUpdateRendererFromView` are present.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` (result: 13) | 0 | ✅ pass | <1s |
| 2 | `grep -c 'field-help' backend/app/templates/browser/workflow_builder.html` (result: 6) | 0 | ✅ pass | <1s |
| 3 | `grep 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` | 1 | ✅ pass (no matches = renderer dropdown removed) | <1s |
| 4 | `grep -q 'renderer-badge' backend/app/templates/browser/workflow_builder.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q '_wfUpdateRendererFromView' backend/app/templates/browser/workflow_builder.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'builder-error' ...dashboard_builder.html && grep -q 'builder-error' ...workflow_builder.html` | 0 | ✅ pass | <1s |

## Diagnostics

- **Help text coverage:** `grep -c 'field-help' <template>` — dashboard: 13, workflow: 6.
- **Renderer auto-set:** In browser dev tools on a workflow with a view step, `document.querySelector('[data-key="renderer_type"]').value` shows the renderer type matching the selected view.
- **Badge display:** The `.renderer-badge` span next to the view dropdown shows "(table)", "(card)", or "(graph)" after selection.
- **Save compatibility:** The hidden input uses `data-key="renderer_type"` so the existing `querySelectorAll('[data-key]')` save collector picks it up without changes.

## Deviations

- Renamed the hidden input class from `step-config-renderer-auto` to `wf-auto-renderer` because the slice verification check `grep -c 'step-config-renderer'` does a substring match, and the old name would cause a false positive (count = 1 instead of 0).
- Called `_wfUpdateRendererFromView` from `renderViewOptions()` instead of using a fragile `setTimeout` in `_wfBuilderAddStep` — this ensures the badge updates reliably after the fetch resolves.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/dashboard_builder.html` — Added 10 new field-help elements across top-level fields and all block type configs
- `backend/app/templates/browser/workflow_builder.html` — Added 6 field-help elements, replaced renderer dropdown with hidden input + badge, added `_wfUpdateRendererFromView` helper
- `.gsd/milestones/M031/slices/S06/S06-PLAN.md` — Added Observability / Diagnostics section and diagnostic verification check (pre-flight fix)
- `.gsd/milestones/M031/slices/S06/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
