---
estimated_steps: 5
estimated_files: 1
---

# T02: Add Task Templates and Review Workflows to chapter 28

**Slice:** S01 — M034 Feature Documentation
**Milestone:** M040

## Description

Extend chapter 28 (Dashboards and Workflows) with two new sections: Task Templates and Review Workflows. Task Templates covers creating, editing, deleting templates, the "Create from Template" command palette entry, and batch instantiation using @slot: references. Review Workflows covers the 4 seeded PPV review workflows, launching them from the command palette, and stepping through workflow stages.

## Steps

1. Read `backend/app/task_templates/router.py` and `backend/app/task_templates/service.py` to document the template CRUD and instantiation flow
2. Read `backend/app/dashboard/seed.py` to document the 4 seeded PPV review workflows (Weekly, Monthly, Quarterly, and the sample two-step)
3. Write Task Templates section covering: what templates are, creating a template (which fields are saved), editing/deleting, using "Create from Template" via Alt+K palette, batch instantiation behavior
4. Write Review Workflows section covering: the seeded workflows, what each one reviews, how to launch from palette, step progression through blocks
5. Verify sections reference correct UI paths and match actual codebase behavior

## Must-Haves

- [ ] Task Templates section with CRUD and "Create from Template" palette usage
- [ ] Review Workflows section with the 4 seeded workflows documented
- [ ] Sections follow existing chapter 28 patterns (heading levels, description style)

## Verification

- `grep -q "Task Templates" docs/guide/28-dashboards-and-workflows.md`
- `grep -q "Review Workflow" docs/guide/28-dashboards-and-workflows.md`
- `grep -q "Create from Template" docs/guide/28-dashboards-and-workflows.md`
- `wc -l docs/guide/28-dashboards-and-workflows.md` shows growth (target: 400+ lines, up from 301)

## Inputs

- `docs/guide/28-dashboards-and-workflows.md` — existing chapter to extend
- `backend/app/task_templates/router.py` — template CRUD endpoints
- `backend/app/task_templates/service.py` — template service logic
- `backend/app/dashboard/seed.py` — seeded workflow definitions

## Expected Output

- `docs/guide/28-dashboards-and-workflows.md` — extended with Task Templates and Review Workflows sections
