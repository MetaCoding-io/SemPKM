---
estimated_steps: 5
estimated_files: 4
---

# T03: User guide documentation updates for M005 features

**Slice:** S09 — E2E Tests & Docs
**Milestone:** M005

## Description

Update four existing user guide chapters to document the new M005 features: hierarchical tag tree (TAG-04), tag autocomplete (TAG-05), model schema refresh (MIG-01), and operations log (LOG-01). All changes are additive — new sections and expanded descriptions, no removal of existing content.

## Steps

1. **Chapter 04 — Workspace Interface** (`docs/guide/04-workspace-interface.md`): Expand the "By Tag" row in the Explorer Modes table to mention hierarchical nesting with `/` delimiter. Add a new subsection "Hierarchical Tags" after the Explorer Modes table, describing:
   - Tags containing `/` (e.g., `garden/cultivate`, `architect/build`) render as nested folder hierarchies in the By Tag explorer
   - Top-level segments appear as root folders; sub-segments appear when expanding the parent folder
   - Count badges on folders show the total number of tagged objects at that level and below
   - Folders expand lazily — sub-folders and objects load on click
   - Tags that are both a value and a folder prefix show both child folders and directly tagged objects

2. **Chapter 05 — Working with Objects** (`docs/guide/05-working-with-objects.md`): Add a "Tag Autocomplete" paragraph in the editing section (after the existing tags mention around line 111 or in the "Editing Properties" section). Cover:
   - When editing an object with tag properties (`schema:keywords` or model-specific tag fields), an autocomplete dropdown appears as you type
   - Suggestions are ordered by frequency (most-used tags first), limited to 30 results
   - Click a suggestion to fill the value; type a new tag value freely if no suggestion matches
   - The "+ Add" button creates additional tag inputs, each with its own autocomplete

3. **Chapter 10 — Managing Mental Models** (`docs/guide/10-managing-mental-models.md`): Add a "Refreshing Model Artifacts" section after the existing model removal section. Cover:
   - The "Refresh" button on the Models page and model detail page reloads a model's ontology, shapes, views, and rules from disk
   - When to use it: after updating model files on disk, or if views/shapes seem out of date
   - What it preserves: all user data (objects, edges, events) and seed data remain untouched
   - What it replaces: ontology classes, SHACL shapes, view definitions, and rules are cleared and reloaded
   - The operation is transactional — if loading fails, the previous state is preserved
   - A confirmation dialog appears before refresh executes
   - Refresh activity is recorded in the Operations Log

4. **Chapter 14 — System Health and Debugging** (`docs/guide/14-system-health-and-debugging.md`): Add an "Operations Log" subsection under Debug Tools (before the "Troubleshooting Common Issues" section). Cover:
   - Access via Admin portal > Operations Log (or `/admin/ops-log`)
   - Requires owner role
   - Shows timestamped log of system activities: model installs, model removals, model refreshes, inference runs, validation runs
   - Each entry shows: time, activity description, activity type badge, actor, status (success/failed), duration
   - Failed activities show expandable error details
   - Filter by activity type via dropdown
   - Cursor-based pagination with "Load more" button
   - Brief note that entries use PROV-O vocabulary internally

5. Review all four files for consistent formatting, correct cross-references between chapters, and markdown validity

## Must-Haves

- [ ] Chapter 04 documents hierarchical tag tree with `/` nesting
- [ ] Chapter 05 documents tag autocomplete in edit forms
- [ ] Chapter 10 documents "Refreshing Model Artifacts" workflow
- [ ] Chapter 14 documents Operations Log under Debug Tools
- [ ] All additions are consistent with existing writing style and formatting

## Verification

- `grep -c "hierarchical\|nested\|sub-folder" docs/guide/04-workspace-interface.md` — returns ≥ 3
- `grep -c "autocomplete\|suggestion" docs/guide/05-working-with-objects.md` — returns ≥ 3
- `grep -c "Refresh\|refresh" docs/guide/10-managing-mental-models.md` — returns ≥ 5
- `grep -c "Operations Log\|ops.log\|PROV-O" docs/guide/14-system-health-and-debugging.md` — returns ≥ 5
- All files render valid markdown (no broken links within the chapter)

## Inputs

- `docs/guide/04-workspace-interface.md` — existing Explorer Modes table at line ~86
- `docs/guide/05-working-with-objects.md` — existing tags mention at line ~111, editing section at line ~152
- `docs/guide/10-managing-mental-models.md` — existing model installation and removal sections
- `docs/guide/14-system-health-and-debugging.md` — existing Debug Tools section
- S03 summary: hierarchical tag tree with build_tag_tree(), prefix param, lazy expansion
- S04 summary: tag-suggestions endpoint, frequency ordering, htmx:configRequest
- S05 summary: refresh_artifacts() with transactional CLEAR+INSERT, preserves seed/user data
- S02 summary: ops log with PROV-O, filter, cursor-based pagination, 4 activity types

## Expected Output

- `docs/guide/04-workspace-interface.md` — expanded By Tag mode description + Hierarchical Tags subsection
- `docs/guide/05-working-with-objects.md` — Tag Autocomplete paragraph in editing section
- `docs/guide/10-managing-mental-models.md` — new "Refreshing Model Artifacts" section
- `docs/guide/14-system-health-and-debugging.md` — new "Operations Log" subsection under Debug Tools

## Observability Impact

This task adds documentation only — no runtime signals, logs, or endpoints are introduced or changed. The observable artifact is the documentation content itself, verifiable via grep checks on the four updated guide chapters.
