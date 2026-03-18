---
estimated_steps: 8
estimated_files: 5
---

# T04: User guide documentation for event log improvements and personas

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M012

## Description

Write and update user guide documentation covering all M012 features. This is the final documentation deliverable for the milestone. Two main areas: (1) update existing Chapter 15 (Event Log) with S01/S02 features, (2) create new Chapter 30 (Personas) for S03 features. Also update the table of contents, navigation chain, and glossary.

## Steps

1. **Update `docs/guide/15-event-log.md`** — Add four new sections to the existing chapter:

   - **"Predicate Labels" section** (after "Browsing the Timeline"): Event log detail view now shows human-readable labels for predicates (e.g. "Title" instead of `dcterms:title`). Labels are resolved from SHACL shape annotations. If a shape defines `sh:name` for a property, that name is used. Otherwise, the local name of the IRI is used.

   - **"Helptext Tooltips" section**: Hovering over a predicate label in the event detail view shows a tooltip with additional context from SHACL annotations (`sh:description` or `sempkm:editHelpText`). Predicates with helptext show a dotted underline indicator.

   - **"Autocomplete Filters" section**: The event log filter area has three autocomplete inputs — Operation Type, Predicate, and Object. Clicking or typing in a filter input shows a dropdown with suggestions drawn from actual event data. Selecting a suggestion applies the filter. Active filters appear as removable chips.

   - **"Body Diff Events" subsection** in the operation types table section: Add `body.diff` to the operation types table. Explain that when editing an existing body, only the changes are stored as a unified diff. The event log renders these with green (additions) and red (deletions) highlighting. First-time body creation still uses `body.set`.

2. **Create `docs/guide/30-personas.md`** — New chapter covering:

   - Introduction: What personas are (named workspace configurations that save your panel layout, sidebar arrangement, and explorer mode). Use cases: "Research" persona with reference panels open, "Writing" persona with minimal distraction.

   - **"Default Persona" section**: SemPKM automatically creates a "Default" persona the first time you load the workspace. This captures your initial workspace state.

   - **"Creating a Persona" section**: Via sidebar user popover → PERSONAS section → "+" button. Via command palette → "Persona: Create New...". The new persona captures the current workspace state.

   - **"Switching Personas" section**: Click a persona name in the sidebar selector. Or use Ctrl+K → "Persona: Switch To..." → select persona. Switching saves the current persona's state automatically before restoring the target persona.

   - **"Saving Persona State" section**: Click "Save" in the sidebar persona selector. Or Ctrl+K → "Persona: Save Current". State is also auto-saved when switching personas and when closing the browser tab.

   - **"Renaming and Deleting" section**: Rename via API (no UI yet — `PUT /api/personas/{id}`). Delete via sidebar. Deleting the active persona auto-activates another.

   - **"What's Saved" section**: Dockview panel layout (which tabs are open, their positions and sizes), sidebar panel positions, explorer mode selection. NOT saved: theme, font size, or other user settings (layout-only for v1).

   - Navigation footer: Previous → Chapter 29, Next → Appendix A

3. **Update `docs/guide/README.md`** — Add Chapter 30 to the Part VIII section:
   ```
   30. [Workspace Personas](30-personas.md)
   ```

4. **Update `docs/guide/29-mental-model-catalog.md` navigation chain** — Change the "Next" link from `Appendix A: Environment Variable Reference` to `Chapter 30: Workspace Personas`.

5. **Update `docs/guide/appendix-d-glossary.md`** — Add two entries in alphabetical position:
   - **Body Diff** — An incremental change record for object body content. When editing an existing body, SemPKM stores only the unified diff (additions and deletions) rather than the full replacement text. See [Chapter 15: Understanding the Event Log](15-event-log.md).
   - **Persona** — A named workspace configuration that stores panel layout, sidebar arrangement, and explorer mode. Switching personas instantly reconfigures the workspace. See [Chapter 30: Workspace Personas](30-personas.md).

## Must-Haves

- [ ] Chapter 15 has 4 new sections: predicate labels, helptext tooltips, autocomplete filters, body.diff
- [ ] `body.diff` added to the operation types table in Chapter 15
- [ ] Chapter 30 exists with complete persona documentation (7 sections + navigation)
- [ ] README.md TOC includes Chapter 30
- [ ] Chapter 29 navigation chain points to Chapter 30 (not Appendix A)
- [ ] Chapter 30 navigation chain: Previous → Chapter 29, Next → Appendix A
- [ ] Glossary has "Body Diff" and "Persona" entries

## Verification

- `grep "30-personas" docs/guide/README.md` — finds the TOC entry
- `tail -3 docs/guide/29-mental-model-catalog.md` — shows "Next" pointing to Chapter 30
- `head -5 docs/guide/30-personas.md` — shows Chapter 30 title
- `tail -3 docs/guide/30-personas.md` — shows Previous/Next navigation
- `grep -c "Persona\|Body Diff" docs/guide/appendix-d-glossary.md` — returns ≥ 2 (new entries)
- `grep "body.diff" docs/guide/15-event-log.md` — finds body.diff documentation

## Inputs

- `docs/guide/15-event-log.md` (226 lines) — existing chapter to update
- `docs/guide/README.md` (75 lines) — TOC to update
- `docs/guide/29-mental-model-catalog.md` — nav chain to update
- `docs/guide/appendix-d-glossary.md` — glossary to add entries
- S01 summary — event log feature details (labels, helptext, autocomplete patterns)
- S02 summary — body.diff feature details (incremental storage, unified diff rendering)
- S03 summary — persona feature details (CRUD, switching, command palette, auto-creation)

## Expected Output

- `docs/guide/15-event-log.md` — updated with 4 new sections (~80 lines added)
- `docs/guide/30-personas.md` — new file (~150-200 lines)
- `docs/guide/README.md` — 1 line added to TOC
- `docs/guide/29-mental-model-catalog.md` — navigation footer updated
- `docs/guide/appendix-d-glossary.md` — 2 new entries added
