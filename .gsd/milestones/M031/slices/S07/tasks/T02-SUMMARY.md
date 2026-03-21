---
id: T02
parent: S07
milestone: M031
provides:
  - Chapter 7 updated with 5 new sections replacing removed carousel documentation
  - Chapter 21 updated with Graph Visualization section for SPARQL triple-pattern results
  - Chapter 28 updated with 4 new sections documenting builder UX improvements
key_files:
  - docs/guide/07-browsing-and-visualizing.md
  - docs/guide/21-sparql-console.md
  - docs/guide/28-dashboards-and-workflows.md
key_decisions:
  - Grounded all documentation in actual template/JS implementations (view_toolbar.html, kanban_view.html, sparql-console.js, dashboard_builder.html, workflow_builder.html, seed.py) rather than relying solely on planner descriptions
patterns_established:
  - Documentation sections mirror actual UI component structure — each toolbar dropdown, view type, and builder feature gets its own H2/H3 section with concrete usage instructions
observability_surfaces:
  - grep-based verification checks provide binary pass/fail signals for content presence in each chapter
  - Section count metric (grep -c "^## ") quantifies chapter 7 coverage — must be >= 8
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Update user guide chapters 7, 21, and 28 for M031 features

**Replace carousel docs in ch7 with view toolbar/kanban/saved views/multi-instance sections, add graph visualization to ch21, add builder help text/autocomplete/simplified workflow/sample data to ch28.**

## What Happened

Updated three user guide chapters to document all M031 new and changed features:

1. **Chapter 7 (Browsing and Visualizing):** Rewrote the intro paragraph to remove carousel mention and describe the new view system. Deleted the entire "Carousel View Navigation" section (3 headings, ~13 lines). Inserted 5 new H2 sections: View Toolbar (with subsections for variant dropdown, scope dropdown, and save button), Kanban View (opening, type selection via SHACL sh:in, drag-and-drop), Saved Views (saving, accessing, managing), Multiple View Instances (deduplication rules, tab label differentiation), and Saved Queries in Explorer (scoped view opening, drag to spatial canvas).

2. **Chapter 21 (SPARQL Console):** Added "Graph Visualization" section after the Access section, documenting triple-pattern detection, Table/Graph tab switcher, Cytoscape.js node-link diagram rendering, dagre layout for small graphs (<30 nodes), fcose for larger graphs, and a usage tip with example query.

3. **Chapter 28 (Dashboards and Workflows):** Added 4 new H2 sections before Explorer Sidebar Sections: Builder Help Text (contextual field-help pattern with examples), IRI Autocomplete (class search and object search dropdowns), Simplified Workflow View Step (auto-set renderer with read-only badge), and Sample Dashboards and Workflows (Getting Started dashboard and Create & Review workflow from seed.py).

All documentation was grounded in actual implementation code — toolbar dropdowns match view_toolbar.html, kanban columns match kanban_view.html, graph tab details match sparql-console.js, help text examples match dashboard_builder.html, and sample data matches seed.py.

## Verification

All 8 task-level checks and all 7 slice-level checks pass. This is the final task in S07, so the full slice verification bar is met.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `! grep -qi "carousel" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 2 | `grep -q "## View Toolbar" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 3 | `grep -q "## Kanban View" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 4 | `grep -q "## Saved Views" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 5 | `grep -q "## Multiple View Instances" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 6 | `grep -q "## Graph Visualization" docs/guide/21-sparql-console.md` | 0 | ✅ pass | <1s |
| 7 | `grep -q "## IRI Autocomplete" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 8 | `grep -q "Sample" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 9 | `test -f e2e/tests/02-views/m031-views.spec.ts && ! test -f e2e/tests/02-views/carousel-views.spec.ts` | 0 | ✅ pass | <1s |
| 10 | `grep -q "Task:" e2e/fixtures/seed-data.ts` | 0 | ✅ pass | <1s |
| 11 | `! grep -q "carousel" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 12 | `grep -q "Kanban" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 13 | `grep -q "Graph Visualization" docs/guide/21-sparql-console.md` | 0 | ✅ pass | <1s |
| 14 | `grep -q "autocomplete\|Autocomplete" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 15 | `grep -c "^## " docs/guide/07-browsing-and-visualizing.md` (returns 10) | 0 | ✅ pass | <1s |

## Diagnostics

- **Content audit**: `grep -c "^## " docs/guide/07-browsing-and-visualizing.md` returns section count — must be ≥ 8 (currently 10).
- **Carousel residue**: `grep -rni "carousel" docs/guide/` detects any remaining carousel references across all guide chapters.
- **Section inventory**: `grep "^## " docs/guide/07-browsing-and-visualizing.md` lists all H2 headings for quick structure review.
- **No runtime signals**: These are static markdown files with no runtime observability.

## Deviations

- Added "Saved Queries in Explorer" as a standalone H2 section in chapter 7, as specified in the plan. The plan's insertion point ("after View Tabs and before Table View") was adapted since the carousel section occupied that space — the 5 new sections replaced the carousel section cleanly.
- The plan mentioned inserting the Graph Visualization section "after Saving and Managing Queries" but chapter 21 has no such heading. Inserted after the "Access" section instead, which is the last content section before the navigation footer.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/07-browsing-and-visualizing.md` — Removed carousel content, added View Toolbar, Kanban View, Saved Views, Multiple View Instances, and Saved Queries in Explorer sections
- `docs/guide/21-sparql-console.md` — Added Graph Visualization section documenting triple-pattern graph tab
- `docs/guide/28-dashboards-and-workflows.md` — Added Builder Help Text, IRI Autocomplete, Simplified Workflow View Step, and Sample Dashboards and Workflows sections
- `.gsd/milestones/M031/slices/S07/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
