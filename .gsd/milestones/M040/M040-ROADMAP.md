# M040: Cleanup - Documentation, UI Fixes & Bug Squashing

**Vision:** Every M034 planning feature has user guide documentation, and all 8 orphaned guide chapters are reachable from the guide navigation.

## Success Criteria

- A user can find documentation for calendar editing, timeline/Gantt, recurring tasks, task templates, and review workflows in the user guide
- Chapter 7 covers all 7 renderers: Table, Cards, Graph, Kanban, Calendar, Timeline, and Map
- Chapter 28 covers task templates and review workflows alongside existing dashboard/workflow docs
- All `.md` files in `docs/guide/` are linked from README.md, index.html, and guide.html
- Zero chapter number collisions exist on disk
- Glossary (Appendix D) includes terms for all M034 concepts

## Key Risks / Unknowns

- Chapter renumbering in S02 could break cross-references between existing chapters — mitigated by grepping all inter-chapter links before and after

## Verification Classes

- Contract verification: `grep` checks for section existence, three-file sync diff, cross-reference integrity
- Integration verification: none (pure documentation, no code changes)
- Operational verification: none
- UAT / human verification: spot-check that documented UI paths match actual app behavior

## Milestone Definition of Done

This milestone is complete only when all are true:

- Chapter 7 contains Calendar View, Timeline/Gantt View, and Map View sections
- Chapter 7 or 28 contains recurring tasks, task templates, review workflow documentation
- Cross-view drag and composable planning are documented in context with the calendar section
- All 8 orphan files have unique chapter numbers and appear in all 3 nav files
- `grep -rn "^[0-9]*-" docs/guide/README.md | sort` shows no duplicate chapter numbers
- Every `.md` file in `docs/guide/` (excluding README.md and appendices) has a corresponding entry in README.md, index.html, and guide.html
- Appendix D glossary includes Calendar View, Timeline View, Recurrence, Task Template, Review Workflow
- No broken cross-references: `grep -rn '\[Chapter [0-9]' docs/guide/` resolves to real files

## Requirement Coverage

- Covers: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08, DOC-09
- Partially covers: none
- Leaves for later: UI bug fixes, polish items (future slices as issues are identified)
- Orphan risks: none — all 9 candidate requirements are mapped

## Slices

- [ ] **S01: M034 Feature Documentation** `risk:low` `depends:[]`
  > After this: user guide chapter 7 documents Calendar, Timeline, and Map views; chapter 28 documents task templates and review workflows; glossary has new terms; all 3 nav files are updated for any new entries
- [ ] **S02: Orphan Chapter Integration & Renumbering** `risk:low` `depends:[]`
  > After this: all 8 orphan guide files have unique chapter numbers and are linked in README.md, index.html, and guide.html; zero chapter number collisions on disk

<!--
  S01 and S02 are independent — neither depends on the other. S01 is ordered first
  because it's the core deliverable that motivated this milestone. S02 is housekeeping
  that can proceed in parallel or after S01. Neither has meaningful technical risk;
  the work is content authoring and file renaming.
-->

## Boundary Map

### S01

Produces:
- Updated `docs/guide/07-browsing-and-visualizing.md` with Calendar, Timeline, and Map sections
- Updated `docs/guide/28-dashboards-and-workflows.md` with Task Templates and Review Workflows sections
- Updated `docs/guide/appendix-d-glossary.md` with new terms
- Updated `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html` if new chapters added

Consumes:
- nothing (first slice, extends existing chapters)

### S02

Produces:
- 8 renamed orphan files with unique chapter numbers (41–48 range)
- Updated `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html` with all orphan entries

Consumes:
- nothing (independent of S01; works with current chapter numbering on disk)
