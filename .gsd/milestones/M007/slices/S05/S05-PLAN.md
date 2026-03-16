# S05: Dashboard & Workflow User Guide

**Goal:** Document dashboards and workflows in the user guide so users can create, edit, run, and understand these features without reading source code.
**Demo:** `docs/guide/28-dashboards-and-workflows.md` exists with complete coverage of dashboard creation/editing/rendering/cross-view-context and workflow creation/running/editing. Glossary has new terms. README lists chapter 28. Prev/next navigation links chain correctly.

## Must-Haves

- Guide page covers all 5 dashboard layout templates and 6 block types
- Guide page covers cross-view context filtering (emits_context → listens_to_context)
- Guide page covers all 3 workflow step types and the stepper runner UI
- Guide page covers explorer sidebar sections (DASHBOARDS, WORKFLOWS) with + buttons
- Glossary entries for: Dashboard, Workflow, Block, Step, Cross-View Context
- README.md table of contents includes chapter 28
- Prev/next links: ch. 27 → ch. 28 → Appendix A

## Verification

- `test -f docs/guide/28-dashboards-and-workflows.md` — file exists
- `grep -c "Dashboard" docs/guide/28-dashboards-and-workflows.md` — returns substantial count
- `grep -c "Workflow" docs/guide/28-dashboards-and-workflows.md` — returns substantial count
- `grep "28-dashboards" docs/guide/README.md` — chapter listed in TOC
- `grep "Dashboard" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "Workflow" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "Cross-View Context" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "28-dashboards" docs/guide/27-spatial-canvas.md` — prev/next link updated
- `grep "27-spatial-canvas" docs/guide/28-dashboards-and-workflows.md` — prev link present
- `grep "appendix-a" docs/guide/28-dashboards-and-workflows.md` — next link present

## Tasks

- [x] **T01: Write dashboard & workflow guide page, update glossary and README** `est:1h`
  - Why: DOCS-04 requires user-facing documentation for dashboards and workflows. This is the entire deliverable — one guide page plus supporting index/glossary updates and navigation link fixes.
  - Files: `docs/guide/28-dashboards-and-workflows.md` (new), `docs/guide/appendix-d-glossary.md`, `docs/guide/README.md`, `docs/guide/27-spatial-canvas.md`
  - Do:
    1. Write `28-dashboards-and-workflows.md` following ch. 27's style conventions (control tables, numbered step-by-step procedures, `> **Note:**` blockquotes, `> **Tip:**` tips). Two major sections: Dashboards (layouts, block types, builder, editing, deleting, cross-view context) and Workflows (step types, builder, runner with stepper navigation, editing, deleting). Include explorer sidebar coverage (DASHBOARDS/WORKFLOWS sections with + buttons). End with a comparison table (Dashboard vs. Workflow).
    2. Add glossary entries alphabetically in `appendix-d-glossary.md` for: Block, Cross-View Context, Dashboard, Layout (dashboard), Step (workflow), Workflow.
    3. Add chapter 28 entry to `README.md` under Part VIII (Discovery and Integration).
    4. Update ch. 27 `**Next:**` link from Appendix A to chapter 28. Add `**Previous:** ch. 27` and `**Next:** Appendix A` footer to chapter 28.
  - Verify: All 10 verification commands in the slice plan pass.
  - Done when: Guide page has complete dashboard and workflow documentation with correct navigation links, glossary has all 6 new entries, README lists chapter 28.

## Observability / Diagnostics

This is a documentation-only slice — no runtime code changes. Observability is limited to file-system verification:

- **File existence:** `test -f docs/guide/28-dashboards-and-workflows.md`
- **Content completeness:** `grep -c` checks for section headings, key terms
- **Link integrity:** `grep` checks for prev/next navigation links across ch. 27, ch. 28, and appendix references
- **Glossary correctness:** `grep` checks for each new glossary entry in alphabetical position
- **Failure visibility:** If any grep/test command returns empty or zero, the specific missing content is identified by which check failed

No runtime signals, structured logs, or error states apply — this slice produces only static Markdown files.

## Files Likely Touched

- `docs/guide/28-dashboards-and-workflows.md` (new)
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/README.md`
- `docs/guide/27-spatial-canvas.md`
