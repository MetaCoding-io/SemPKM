# S05: Dashboard & Workflow User Guide — Research

**Date:** 2026-03-15

## Summary

This is a documentation-only slice. Dashboards and workflows shipped in M006 (S03–S07) but no user guide pages were written — DOCS-04 is the last active requirement in this milestone. The work is straightforward: write one or two markdown pages following the established guide conventions (numbered chapters, consistent heading structure, toolbar/control tables, step-by-step instructions) and update the glossary and README index.

All code exists and is validated. No code changes needed. The research just maps what needs documenting and where it fits in the existing guide structure.

## Recommendation

Write a single page `docs/guide/28-dashboards-and-workflows.md` covering both features. They're closely related (workflows embed dashboards as steps, both live in the same explorer sidebar section, both use the same builder pattern). A single page with two major sections is cleaner than two thin pages. Update `docs/guide/README.md` to add the entry and `docs/guide/appendix-d-glossary.md` to add Dashboard, Workflow, Block, and Step terms.

## Implementation Landscape

### Key Files

- `docs/guide/README.md` — Table of contents. Add entry for chapter 28 under Part VIII (Discovery and Integration) or a new Part.
- `docs/guide/appendix-d-glossary.md` — Add glossary entries for Dashboard, Workflow, Block (dashboard), Step (workflow), Layout (dashboard), Cross-View Context.
- `docs/guide/28-dashboards-and-workflows.md` — **New file.** The guide page itself.
- `docs/guide/27-spatial-canvas.md` — Reference for writing style, heading structure, tone, and conventions (tables for controls, step-by-step procedures, tips in blockquotes).

### Content to Document

**Dashboards section:**
1. What dashboards are (multi-block layout pages that combine views, forms, markdown, objects)
2. The 5 layout templates: single, sidebar-main, grid-2x2, grid-3, top-bottom
3. The 6 block types: view-embed, markdown, object-embed, create-form, sparql-result, divider
4. Creating a dashboard (+ button in DASHBOARDS sidebar section → builder form)
5. Editing a dashboard (pencil button on dashboard header)
6. Deleting a dashboard (trash icon in explorer, confirm dialog)
7. Cross-view context filtering: emits_context on source block, listens_to_context variable on consumer block, row click → context IRI → filtered re-fetch

**Workflows section:**
1. What workflows are (ordered step sequences guiding users through multi-step processes)
2. The 3 step types: view, dashboard, form
3. Creating a workflow (+ button in WORKFLOWS sidebar section → builder form)
4. Running a workflow (click workflow in explorer → stepper UI with prev/next navigation)
5. Editing a workflow (edit from builder)
6. Deleting a workflow (trash icon in explorer)

**Explorer sidebar sections:**
- DASHBOARDS section with + button, list of dashboards, click to open, trash to delete
- WORKFLOWS section with + button, list of workflows, click to run, trash to delete

### Source Material for Content

| Feature | Code Location | What to Reference |
|---------|--------------|-------------------|
| Dashboard model | `backend/app/dashboard/models.py` | VALID_LAYOUTS, VALID_BLOCK_TYPES, field descriptions |
| Dashboard builder | `backend/app/templates/browser/dashboard_builder.html` | Layout picker, block config fields, view-embed context options |
| Dashboard rendering | `backend/app/templates/browser/dashboard_page.html` | CSS Grid layout, block lazy-loading, context event wiring |
| Dashboard blocks | `backend/app/dashboard/router.py` → `render_block()` | Each block type's rendering behavior |
| Workflow model | `backend/app/workflow/models.py` | VALID_STEP_TYPES, field descriptions |
| Workflow runner | `backend/app/templates/browser/workflow_runner.html` | Stepper bar, prev/next nav, step content loading |
| Workflow builder | `backend/app/templates/browser/workflow_builder.html` | Step config fields, view/dashboard select population |
| Explorer sections | `backend/app/templates/browser/workspace.html` lines 72–103 | DASHBOARDS and WORKFLOWS sidebar sections |
| Tab opening | `frontend/static/js/workspace.js` lines 721–818 | `openDashboardTab`, `openWorkflowTab`, builder tab functions |

### Build Order

1. **Write `28-dashboards-and-workflows.md`** — the main deliverable. Follow ch. 27's style: introduction → feature sections with tables and step-by-step instructions.
2. **Update `appendix-d-glossary.md`** — add terms alphabetically.
3. **Update `README.md`** — add entry to table of contents.

### Verification Approach

- File exists at `docs/guide/28-dashboards-and-workflows.md`
- All internal links resolve (cross-references to other guide pages)
- Glossary entries added for: Dashboard, Workflow, Block (dashboard block), Cross-View Context
- README.md lists chapter 28
- `docs/` volume mount means the page is immediately accessible at runtime without Docker rebuild

## Constraints

- Guide pages are plain Markdown served via docs volume mount — no build step.
- Existing style: chapters use `# Chapter N: Title` heading, sections with `##`, control tables with `| Control | Action |` format, step-by-step with numbered lists, tips/notes in `> **Note:**` blockquotes.
- Previous/Next navigation links at page bottom must chain correctly (27 → 28 → appendix-a or next chapter).
