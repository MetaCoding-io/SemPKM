---
id: T03
parent: S09
milestone: M005
provides:
  - User guide documentation for M005 features: hierarchical tags, tag autocomplete, model refresh, operations log
key_files:
  - docs/guide/04-workspace-interface.md
  - docs/guide/05-working-with-objects.md
  - docs/guide/10-managing-mental-models.md
  - docs/guide/14-system-health-and-debugging.md
key_decisions:
  - Operations Log section placed under Debug Tools before Troubleshooting, with cross-reference from Chapter 10's Refresh section
  - Tag autocomplete documented as a subsection under Editing Properties (h4) rather than a standalone section
patterns_established:
  - Feature documentation follows existing chapter style: descriptive prose, bullet lists for behavior, blockquote tips, and cross-references to related chapters
observability_surfaces:
  - none (documentation-only task)
duration: 12m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T03: User guide documentation updates for M005 features

**Updated four user guide chapters to document hierarchical tag tree, tag autocomplete, model artifact refresh, and operations log**

## What Happened

Added documentation sections to four existing user guide chapters covering all user-visible M005 features:

1. **Chapter 04 (Workspace Interface):** Expanded the "By Tag" row in the Explorer Modes table to mention hierarchical `/` nesting. Added a new "Hierarchical Tags" subsection describing folder structure from `/` segments, count badges, lazy expansion, and tags-as-both-folders-and-values behavior.

2. **Chapter 05 (Working with Objects):** Added a "Tag Autocomplete" subsection under Editing Properties covering the type-ahead dropdown, frequency-ordered suggestions (up to 30), click-to-fill behavior, and the "+ Add" button for multi-value tags. Included a tip about using autocomplete to maintain naming consistency.

3. **Chapter 10 (Managing Mental Models):** Added a full "Refreshing Model Artifacts" section after the removal section. Covers when to use refresh, what it preserves (user data, seed data) vs. replaces (ontology, shapes, views, rules), transactional safety, Admin Portal workflow with confirmation dialog, and the link to Operations Log for audit trail.

4. **Chapter 14 (System Health and Debugging):** Added an "Operations Log" subsection under Debug Tools, after the Event Log. Covers access (Admin > Operations Log, `/admin/ops-log`), owner role requirement, entry fields (timestamp, description, type badge, actor, status, duration), failed operation error expansion, activity type filter dropdown, cursor-based pagination with "Load more", and PROV-O vocabulary internals.

## Verification

All must-have checks passed:

- `grep -c "hierarchical\|nested\|sub-folder" docs/guide/04-workspace-interface.md` → 5 (≥3 ✓)
- `grep -c "autocomplete\|suggestion" docs/guide/05-working-with-objects.md` → 4 (≥3 ✓)
- `grep -c "Refresh\|refresh" docs/guide/10-managing-mental-models.md` → 22 (≥5 ✓)
- `grep -c "Operations Log\|ops.log\|PROV-O" docs/guide/14-system-health-and-debugging.md` → 8 (≥5 ✓)

Slice-level doc grep checks all return the expected files:

- `grep -l "hierarchical\|nested.*tag\|sub-folder"` → docs/guide/04-workspace-interface.md ✓
- `grep -l "autocomplete\|suggestions"` → docs/guide/05-working-with-objects.md ✓
- `grep -l "Refresh.*Artifact\|refresh_artifacts"` → docs/guide/10-managing-mental-models.md ✓
- `grep -l "Operations Log\|ops-log\|PROV-O"` → docs/guide/14-system-health-and-debugging.md ✓

No broken internal markdown links found across all four files.

## Diagnostics

None — documentation-only task. Verify content with grep commands above or by reading the markdown files directly.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/04-workspace-interface.md` — Expanded By Tag mode description + added Hierarchical Tags subsection
- `docs/guide/05-working-with-objects.md` — Added Tag Autocomplete subsection under Editing Properties
- `docs/guide/10-managing-mental-models.md` — Added Refreshing Model Artifacts section after model removal
- `docs/guide/14-system-health-and-debugging.md` — Added Operations Log subsection under Debug Tools
