# S05: Dashboard & Workflow User Guide — UAT

**Milestone:** M007
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Documentation-only slice — no runtime code, no server needed. All deliverables are static Markdown files verifiable by reading their content and checking structural links.

## Preconditions

- Repository checkout available with `docs/guide/` directory
- No server or Docker needed

## Smoke Test

Open `docs/guide/28-dashboards-and-workflows.md` — it should have two major sections (Dashboards, Workflows) with numbered procedures, control tables, and a comparison table at the end.

## Test Cases

### 1. Chapter 28 exists and has complete dashboard coverage

1. Open `docs/guide/28-dashboards-and-workflows.md`
2. Verify a "Dashboards" section exists with subsections for:
   - Layout templates (all 5: single, sidebar-main, grid-2x2, grid-3, top-bottom)
   - Block types (all 6: view-embed, markdown, object-embed, create-form, sparql-result, divider)
   - Creating a dashboard (numbered steps)
   - Editing and deleting
   - Cross-view context filtering (emits_context → listens_to_context)
3. **Expected:** All subsections present with substantive content (not stubs). Layout templates listed in a table or list. Block types described with what each does.

### 2. Chapter 28 has complete workflow coverage

1. Open `docs/guide/28-dashboards-and-workflows.md`
2. Verify a "Workflows" section exists with subsections for:
   - Step types (all 3: view, dashboard, form)
   - Creating a workflow (numbered steps)
   - Running a workflow (stepper UI described)
   - Editing and deleting
3. **Expected:** All subsections present. Step types documented. Stepper runner UI navigation (prev/next, numbered indicators) described.

### 3. Explorer sidebar sections documented

1. Search `docs/guide/28-dashboards-and-workflows.md` for "Explorer" or "sidebar"
2. **Expected:** Guide explains how DASHBOARDS and WORKFLOWS sections appear in the left sidebar, including the + button to create new items and click-to-open behavior.

### 4. Comparison table present

1. Scroll to end of `docs/guide/28-dashboards-and-workflows.md` (before footer links)
2. **Expected:** A markdown table comparing Dashboard vs. Workflow (purpose, structure, interaction model).

### 5. README TOC includes chapter 28

1. Open `docs/guide/README.md`
2. Find Part VIII section
3. **Expected:** Entry `28. [Dashboards and Workflows](28-dashboards-and-workflows.md)` present.

### 6. Glossary has all 6 new entries

1. Open `docs/guide/appendix-d-glossary.md`
2. Search for each: Block, Cross-View Context, Dashboard, Layout, Step, Workflow
3. **Expected:** All 6 entries present in alphabetical order. Each has a definition and a cross-reference link to Chapter 28.

### 7. Navigation links chain correctly

1. Open `docs/guide/27-spatial-canvas.md` — check footer
2. **Expected:** Next link points to `28-dashboards-and-workflows.md`
3. Open `docs/guide/28-dashboards-and-workflows.md` — check footer
4. **Expected:** Previous link points to `27-spatial-canvas.md`, Next link points to `appendix-a-environment-variables.md`

## Edge Cases

### Glossary alphabetical order

1. Open `docs/guide/appendix-d-glossary.md`
2. Check that "Block" appears before "Canvas", "Cross-View Context" appears before "Dashboard", "Dashboard" appears before "Edge", "Layout" appears in L section, "Step" appears in S section, "Workflow" appears in W section.
3. **Expected:** All entries correctly alphabetized among existing entries.

### No broken internal links

1. In `28-dashboards-and-workflows.md`, check any internal cross-references (links to other guide pages or appendices)
2. **Expected:** All linked filenames correspond to actual files in `docs/guide/`.

## Failure Signals

- `28-dashboards-and-workflows.md` missing or empty
- Missing sections (e.g., no workflow coverage, no cross-view context)
- README TOC missing chapter 28 entry
- Glossary missing any of the 6 required entries
- Navigation chain broken (ch. 27 still points to Appendix A, or ch. 28 missing prev/next)
- Glossary entries out of alphabetical order

## Requirements Proved By This UAT

- DOCS-04 — Tests 1–7 prove complete dashboard/workflow documentation exists with glossary and navigation links, satisfying the acceptance criteria.

## Not Proven By This UAT

- Factual accuracy of documentation against live runtime (would require running the app and comparing UI to described procedures)
- Screenshot accuracy (no screenshots included in the guide)

## Notes for Tester

- This is a pure documentation slice. Everything can be verified by reading Markdown files — no server needed.
- The guide was written from actual source code (models, templates, routers), not from design docs, so descriptions should match the current implementation.
- Pay attention to the cross-view context section — it's the most technically nuanced part. Verify it explains both the emitter (row click in a block) and the consumer (SPARQL variable binding) sides.
