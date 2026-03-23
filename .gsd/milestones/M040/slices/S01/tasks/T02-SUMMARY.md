---
id: T02
parent: S01
milestone: M040
provides:
  - Task Templates section in chapter 28 with CRUD, command palette usage, instantiation mechanics, and @slot: references
  - Review Workflows section in chapter 28 with 5 seeded workflows, palette launch, step progression, customization, and PPV dependency
key_files:
  - docs/guide/28-dashboards-and-workflows.md
key_decisions: []
patterns_established:
  - Documentation sections follow consistent pattern from T01: Opening → What It Contains → CRUD → UI Access → How It Works
observability_surfaces:
  - none
duration: 15m
verification_result: passed
completed_at: 2026-03-23T00:05:00-04:00
blocker_discovered: false
---

# T02: Add Task Templates and Review Workflows to chapter 28

**Added Task Templates and Review Workflows sections to chapter 28 with CRUD documentation, command palette usage, batch instantiation mechanics, and all 5 seeded review workflows.**

## What Happened

Read the four source files (`task_templates/router.py`, `task_templates/service.py`, `dashboard/seed.py`, and the command palette entries in `workspace.js`) to document features accurately from code rather than inventing descriptions.

Added two new `##` sections to chapter 28, growing it from 301 to 461 lines:

1. **Task Templates** — covering: what a template contains (title, target class, default properties, subtask definitions), creating templates via the REST API with example JSON, editing/deleting via PATCH/DELETE, using "Create from Template" via the Alt+K command palette (submenu auto-populated from API), and how instantiation works (batch command pipeline with @slot: references for cross-command IRI resolution, atomic commit, override merging). Includes a tip connecting templates to form groups.

2. **Review Workflows** — covering: all 5 seeded workflows (Create & Review, Weekly, Monthly, Quarterly, Yearly) with a table showing step counts and purpose, launching from the command palette's Workflows section, stepping through a review with the stepper bar/content area/navigation buttons, a walkthrough of a typical weekly review session, customization options (modify steps, change views, create your own), and PPV model dependency (which types and view specs are referenced). Includes a tip connecting review workflows to task templates.

Both sections were inserted before the existing "Dashboard vs. Workflow" comparison table, maintaining the chapter's structure of defining features before comparing them.

## Verification

All four task-level checks pass. Slice-level checks for chapter 28 also pass (line count 461 ≥ 400 target, "Task Template|Review Workflow" count 4 ≥ 2).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "Task Templates" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 2 | `grep -q "Review Workflow" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 3 | `grep -q "Create from Template" docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 4 | `wc -l docs/guide/28-dashboards-and-workflows.md` → 461 | 0 | ✅ pass (≥ 400) | <1s |
| 5 | `grep -c "Task Template\|Review Workflow" docs/guide/28-dashboards-and-workflows.md` → 4 | 0 | ✅ pass (≥ 2) | <1s |

## Diagnostics

This is a documentation-only task. No runtime signals, logs, or failure state to inspect. Verify content accuracy by comparing section text against the source files listed in the Inputs section of the task plan.

## Deviations

- The seed file defines 5 workflows (including "Yearly Review"), not 4 as the task plan stated. Documented all 5 for completeness.
- The task plan referenced "the 4 seeded PPV review workflows" — the actual count is 4 PPV-specific (Weekly, Monthly, Quarterly, Yearly) plus 1 generic sample (Create & Review), totaling 5 seeded workflows. Documented all of them.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/28-dashboards-and-workflows.md` — Extended with Task Templates and Review Workflows sections (301 → 461 lines)
