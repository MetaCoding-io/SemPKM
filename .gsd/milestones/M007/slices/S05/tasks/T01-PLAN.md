---
estimated_steps: 4
estimated_files: 4
---

# T01: Write dashboard & workflow guide page, update glossary and README

**Slice:** S05 — Dashboard & Workflow User Guide
**Milestone:** M007

## Description

Write the user guide page for dashboards and workflows (shipped in M006 but never documented). This is a documentation-only task — no code changes. The page follows existing guide conventions (ch. 27 is the style reference) and covers both features comprehensively. Supporting changes: glossary entries, README TOC update, prev/next navigation link fixes.

## Steps

1. **Write `docs/guide/28-dashboards-and-workflows.md`** with two major sections:
   - **Dashboards section** covering:
     - What dashboards are (multi-block layout pages combining views, forms, markdown, objects)
     - The 5 layout templates: single, sidebar-main, grid-2x2, grid-3, top-bottom — use a `| Layout | Description |` table
     - The 6 block types: view-embed, markdown, object-embed, create-form, sparql-result, divider — use a `| Block Type | Description |` table
     - Creating a dashboard: step-by-step numbered list (click + in DASHBOARDS sidebar → builder form → pick layout → add blocks → save)
     - Editing a dashboard (pencil icon on dashboard tab header)
     - Deleting a dashboard (trash icon in explorer, confirm dialog)
     - Cross-view context filtering: explain emits_context on source block, listens_to_context variable on consumer block, row click → context IRI → filtered re-fetch. Use a practical example (e.g., project list on left, filtered notes on right).
   - **Workflows section** covering:
     - What workflows are (ordered step sequences guiding multi-step processes)
     - The 3 step types: view, dashboard, form — use a `| Step Type | Description |` table
     - Creating a workflow: step-by-step (click + in WORKFLOWS sidebar → builder form → add steps → save)
     - Running a workflow (click workflow in explorer → stepper UI with numbered indicators, prev/next navigation, context passing between steps)
     - Editing a workflow (edit from builder)
     - Deleting a workflow (trash icon in explorer)
   - **Explorer sidebar** brief section describing the DASHBOARDS and WORKFLOWS sections with + buttons, listing behavior, and trash icons.
   - **Dashboard vs. Workflow comparison table** at the end.
   - Use ch. 27 formatting conventions throughout: `# Chapter 28: Dashboards and Workflows` heading, `##` sections, `| Control | Action |` tables, numbered lists for procedures, `> **Note:**` and `> **Tip:**` blockquotes.
   - Add `**Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)` footer.

2. **Add glossary entries** to `docs/guide/appendix-d-glossary.md` in alphabetical order:
   - **Block** — A content unit within a dashboard. Six types: view-embed, markdown, object-embed, create-form, sparql-result, and divider. See Chapter 28.
   - **Cross-View Context** — A dashboard mechanism where selecting a row in one block filters data in other blocks. Source blocks emit context (an IRI), consumer blocks bind it to a SPARQL variable. See Chapter 28.
   - **Dashboard** — A configurable multi-block layout page that combines views, markdown, object embeds, forms, and SPARQL results into a single workspace tab. See Chapter 28.
   - **Layout** (dashboard) — The CSS Grid template that arranges blocks on a dashboard. Five options: single, sidebar-main, grid-2x2, grid-3, and top-bottom.
   - **Step** (workflow) — An individual stage in a workflow. Three types: view (opens a view), dashboard (opens a dashboard), and form (opens a create form). See Chapter 28.
   - **Workflow** — An ordered sequence of steps that guides users through a multi-step process, with a stepper UI for navigation. Steps can be views, dashboards, or forms. See Chapter 28.

3. **Update `docs/guide/README.md`** — add `28. [Dashboards and Workflows](28-dashboards-and-workflows.md)` under Part VIII (Discovery and Integration), after ch. 27.

4. **Update `docs/guide/27-spatial-canvas.md`** — change the `**Next:**` link from `[Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)` to `[Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md)`.

## Must-Haves

- [ ] Guide page covers all 5 dashboard layouts and 6 block types
- [ ] Guide page covers cross-view context filtering with practical example
- [ ] Guide page covers all 3 workflow step types and stepper runner
- [ ] Guide page covers explorer DASHBOARDS/WORKFLOWS sidebar sections
- [ ] 6 glossary entries added alphabetically (Block, Cross-View Context, Dashboard, Layout, Step, Workflow)
- [ ] README lists chapter 28 in Part VIII
- [ ] Prev/next navigation: ch. 27 → ch. 28 → Appendix A

## Verification

- `test -f docs/guide/28-dashboards-and-workflows.md` passes
- `grep -c "## " docs/guide/28-dashboards-and-workflows.md` shows multiple section headings
- `grep "28-dashboards" docs/guide/README.md` shows TOC entry
- `grep "Dashboard" docs/guide/appendix-d-glossary.md` shows glossary entry
- `grep "Workflow" docs/guide/appendix-d-glossary.md` shows glossary entry  
- `grep "Cross-View Context" docs/guide/appendix-d-glossary.md` shows glossary entry
- `grep "28-dashboards" docs/guide/27-spatial-canvas.md` shows updated next link
- `grep "27-spatial-canvas" docs/guide/28-dashboards-and-workflows.md` shows prev link

## Inputs

- `docs/guide/27-spatial-canvas.md` — style reference for conventions (control tables, step-by-step procedures, blockquotes, prev/next footer)
- `docs/guide/appendix-d-glossary.md` — existing glossary to extend alphabetically
- `docs/guide/README.md` — table of contents to update

**Source material for content** (read these to write accurate documentation):
- `backend/app/dashboard/models.py` — VALID_LAYOUTS, VALID_BLOCK_TYPES, field descriptions
- `backend/app/templates/browser/dashboard_builder.html` — layout picker, block config fields, view-embed context options
- `backend/app/templates/browser/dashboard_page.html` — CSS Grid layout, block rendering, context event wiring
- `backend/app/dashboard/router.py` — render_block() for each block type's behavior
- `backend/app/workflow/models.py` — VALID_STEP_TYPES, field descriptions
- `backend/app/templates/browser/workflow_runner.html` — stepper bar, prev/next navigation
- `backend/app/templates/browser/workflow_builder.html` — step config fields
- `backend/app/templates/browser/workspace.html` lines 72–103 — DASHBOARDS and WORKFLOWS sidebar sections

## Observability Impact

Documentation-only task — no runtime behavior changes. No new signals, logs, or failure states. Verification is purely file-system based (file existence, grep for content). A future agent inspects this task by checking whether the guide file exists and contains the expected sections via the verification commands listed above.

## Expected Output

- `docs/guide/28-dashboards-and-workflows.md` — new guide page (~300-500 lines) covering dashboards and workflows comprehensively
- `docs/guide/appendix-d-glossary.md` — 6 new entries inserted alphabetically
- `docs/guide/README.md` — chapter 28 added to Part VIII
- `docs/guide/27-spatial-canvas.md` — Next link updated to point to chapter 28
