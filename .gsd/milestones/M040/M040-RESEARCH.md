# M040: Cleanup — Documentation, UI Fixes & Bug Squashing — Research

## Executive Summary

M040 is primarily a documentation debt milestone. The core work is writing user guide content for 7 M034 features (editable calendar, timeline/Gantt, recurring tasks, recurrence editor, task templates, review workflows, cross-view drag) and fixing a growing chapter numbering/orphan problem. The codebase research reveals no blocking technical risks — the features are already built and tested. The risk is organizational: the guide has accumulated 8 orphan files with duplicate chapter numbers, and the three-file sync rule (README.md, index.html, guide.html) has drifted.

## Codebase Findings

### M034 Features Needing Documentation

Seven distinct user-visible features were shipped without guide coverage (confirmed by zero grep hits across all guide files):

| Feature | Key Files | Complexity |
|---------|-----------|------------|
| **Editable calendar** (drag-to-reschedule, resize-to-change-duration, click-to-create) | `frontend/static/js/calendar.js` (276 lines), `calendar_view.html` | Medium — interaction-heavy, multiple gestures |
| **Timeline/Gantt view** (Frappe Gantt, dependency arrows, zoom levels, drag-to-reschedule) | `timeline_view.html` (160 lines), `backend/app/views/service.py` | Medium — new renderer with configuration |
| **Cross-view drag** (kanban → calendar scheduling, scope-changed event propagation) | `calendar.js`, `kanban.js`, `workspace.js` | Low — describes workflow, not configuration |
| **Recurring tasks & recurrence editor** (RRULE, presets, EXDATE, virtual instances) | `recurrence-editor.js` (640 lines), `views/service.py` | High — RFC 5545 concepts, UI has presets + custom mode |
| **Task templates** (RDF CRUD, batch instantiation via @slot:, command palette) | `backend/app/task_templates/` (608 lines total) | Medium — CRUD + instantiation flow |
| **PPV review workflows** (4 seeded workflows, palette launchers) | `backend/app/dashboard/seed.py`, `workspace.js` | Low — describes seeded content |
| **Composable planning** (calendar + kanban side-by-side, scope binding) | Cross-cutting | Low — describes a usage pattern, not a feature |

### Chapter 7 Current State

`docs/guide/07-browsing-and-visualizing.md` (295 lines) covers: Table View, Card View, Graph View, Kanban View, View Toolbar, Saved Views, Multiple View Instances. It does **not** cover Calendar View, Map View, or Timeline View — these are the 3 renderers added after the chapter was last updated. The chapter structure (headings for each renderer) naturally accommodates new sections.

### Three-File Sync Problem

The KNOWLEDGE.md rule about three guide files is correct but understates the current drift:

| File | Purpose | Chapters listed |
|------|---------|----------------|
| `docs/guide/README.md` | Markdown TOC (source of truth) | 38 chapters + 6 appendices |
| `docs/guide/index.html` | Static docs site sidebar | Same as README (+ duplicate entries for ch 25-26) |
| `backend/app/templates/guide.html` | In-app Docs & Tutorials page | Same as README |

All three files list the **same** chapters and are in sync with each other. But **8 guide files on disk are not listed in any of the three**:

| Orphan File | Content | Collision |
|-------------|---------|-----------|
| `32-rss-reader.md` (305 lines) | RSS Reader app guide | Collides with `32-browser-extension.md` |
| `36-google-calendar-sync.md` (377 lines) | Google Calendar Sync | Collides with `36-jira-sync.md` |
| `37-todoist-sync.md` (358 lines) | Todoist Sync | Collides with `37-monday-sync.md` |
| `38-outlook-calendar-sync.md` (484 lines) | Outlook Calendar Sync | Collides with `38-hosted-demo.md` |
| `39-caldav-calendar-sync.md` (368 lines) | CalDAV Calendar Sync | Collides with `39-notion-import.md` (also orphan) |
| `39-notion-import.md` (272 lines) | Notion Import wizard | Collides with `39-caldav-calendar-sync.md` |
| `40-ai-features.md` (201 lines) | AI extension features | Collides with `40-asana-sync.md` (also orphan) |
| `40-asana-sync.md` (351 lines) | Asana Sync | Collides with `40-ai-features.md` |
| `29-mental-model-catalog.md` | Mental Model Catalog | Collides with `29-app-platform.md` |

These are real, authored content files (200-484 lines each) that are simply invisible to users. Total: ~2,716 lines of authored documentation unreachable from any navigation.

### Chapter Numbering Assessment

Current highest linked chapter number: 38 (Hosted Demo). On-disk highest: 40 (AI Features, Asana Sync — both orphaned). After renumbering all orphans and adding M034 content, the guide will likely reach chapter ~48-50.

### Glossary Gaps

`appendix-d-glossary.md` has no entries for: Calendar View (editable), Timeline View, Gantt, Recurrence/RRULE, Task Template, Review Workflow, Scope Propagation, Cross-View Drag.

### Keyboard Shortcuts Appendix

`appendix-b-keyboard-shortcuts.md` has no M034-specific shortcuts. The features use standard palette commands (`Alt+K` → "Create from Template") rather than dedicated shortcuts, so this may not need updates.

## Existing Patterns to Reuse

### Guide Chapter Structure

Every existing renderer section in chapter 7 follows the same pattern:
1. Opening description (what the view shows)
2. "Opening the [X] View" subsection
3. Feature-specific subsections (sorting, filtering, grouping, etc.)
4. Interaction details (clicking, dragging)

M034 features should follow this pattern exactly.

### Sync App Guide Pattern

The orphaned sync app chapters (Google Calendar, Todoist, Outlook, CalDAV, Asana) all follow a consistent template matching the linked sync chapters (Linear, GitHub, Jira, Monday.com):
1. Overview paragraph
2. Connecting your account
3. Configuration options
4. Sync behavior details
5. Troubleshooting

### Three-File Update Checklist

From KNOWLEDGE.md: when adding chapters, update all three files:
1. `docs/guide/README.md` — markdown links
2. `docs/guide/index.html` — `<a data-file="...">` entries in sidebar
3. `backend/app/templates/guide.html` — `<button hx-get="/guide/...">` entries

## Constraints

1. **No code changes needed.** All M034 features are implemented and tested. This is pure documentation work.
2. **Chapter renumbering is inherently risky.** Every cross-reference between chapters (`See [Chapter X](...)`) breaks if numbers change. Need to audit all inter-chapter links after renumbering.
3. **The orphan files have real content.** They aren't stubs — they're 200-484 line authored chapters. The fix is linking them, not rewriting them.
4. **The guide.html template uses hardcoded buttons.** It's a Jinja2 template with individual `<button>` elements per chapter — no auto-generation from README.md.

## Natural Slice Boundaries

### Slice 1: M034 Feature Documentation (core deliverable)

Add documentation for all 7 M034 features. Two placement options:

**Option A: Expand chapter 7.** Calendar, Timeline, and Map views are renderers like Table/Cards/Graph/Kanban — they fit naturally as new sections in the existing chapter. Recurring tasks and templates could go in a new "Task Planning" subsection. Review workflows belong in chapter 28 (Dashboards and Workflows). Cross-view drag and scope propagation are interaction patterns that belong in whichever chapter discusses the calendar.

**Option B: New dedicated chapter(s).** Create "Planning & Time-Blocking" as a new chapter covering calendar editing, timeline, recurring tasks, templates, review workflows, and composable planning as a coherent feature group.

**Recommendation: Option A.** The calendar and timeline are renderers — they belong in the renderers chapter (7). Task templates and review workflows are planning tools built on the workflow system — they belong in chapter 28. Cross-view drag is a calendar interaction. This preserves the existing chapter structure without creating a thin standalone chapter.

### Slice 2: Orphan Integration & Renumbering

Fix the 8 orphan files: assign unique chapter numbers, link them in all 3 navigation files, fix the `29-mental-model-catalog.md` collision. This requires:
- Renumbering orphan files to non-colliding numbers
- Adding entries to README.md, index.html, guide.html
- Auditing cross-references for broken links

### Ordering: S01 before S02

S01 (M034 docs) is the core deliverable and can be done without renumbering — new sections in existing chapters don't change chapter numbers. S02 (orphan fix) is lower-risk but higher-touch (8 files, 3 nav files, cross-reference audit).

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Cross-reference breakage during renumbering | Medium | Grep for all `Chapter \d+` and `\d+-.*\.md` patterns before and after |
| Orphan file content may be stale | Low | Spot-check a few orphans against codebase reality |
| Chapter 7 becomes too long after adding 3 renderers | Low | Currently 295 lines; adding ~150-200 lines for 3 renderers keeps it under 500 |
| Missing map view docs (M033 gap, not M034) | Low | While we're adding calendar/timeline to ch7, adding map view is low marginal cost |

## Candidate Requirements

The following should be tracked as requirements for this milestone:

| ID | Description | Source |
|----|-------------|--------|
| DOC-01 | Calendar view editing docs (drag-to-reschedule, resize, click-to-create) in chapter 7 | M034 gap |
| DOC-02 | Timeline/Gantt view docs (dependency arrows, zoom, drag-to-reschedule) in chapter 7 | M034 gap |
| DOC-03 | Recurring tasks and recurrence editor docs in chapter 7 or new section | M034 gap |
| DOC-04 | Task templates and "Create from Template" docs in chapter 28 | M034 gap |
| DOC-05 | PPV review workflow docs in chapter 28 | M034 gap |
| DOC-06 | Cross-view drag and scope propagation docs in chapter 7 | M034 gap |
| DOC-07 | Composable planning usage pattern described in chapter 7 or 28 | M034 gap |
| DOC-08 | 8 orphan guide files linked in all 3 navigation files with unique chapter numbers | Accumulated drift |
| DOC-09 | Glossary entries for M034 concepts (calendar editing, timeline, recurrence, templates, review workflows) | M034 gap |

### Advisory (not candidate requirements)

- **Map view docs (M033 gap):** Chapter 7 is also missing Map View documentation from M033. Adding it while editing chapter 7 is low marginal cost but is technically out of M034 scope.
- **Orphan content staleness audit:** The 8 orphan files were written by auto-mode agents and may reference UI paths or features that have changed. A light verification pass would catch stale content but is lower priority than linking them.
- **Appendix B (keyboard shortcuts):** M034 features use command palette entries, not dedicated shortcuts. No appendix update needed unless we want to document the palette commands explicitly.

## What Should Be Proven First

1. **Chapter 7 expansion works structurally.** Add calendar and timeline sections, verify the chapter reads coherently with 7 renderers instead of 4.
2. **Three-file sync is restored.** After S01, all 3 nav files should list the same chapters. After S02, all files on disk should be linked.

## Verification Approach

- For doc content: verify UI paths, keyboard shortcuts, and feature descriptions match the actual codebase implementation
- For three-file sync: automated diff check — every `.md` file in `docs/guide/` should appear in all 3 nav files
- For cross-references: `grep -r 'Chapter \d\+' docs/guide/` should produce no broken references
- For glossary: spot-check that new terms are defined and cross-linked
