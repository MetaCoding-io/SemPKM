---
estimated_steps: 5
estimated_files: 2
---

# T02: Extend user guide with data quality rules and lint filter documentation

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M030

## Description

Extend Chapter 14 ("System Health and Debugging") with 5 new sections documenting the data quality rules, suppress/dismiss workflow, preset management, and lint settings. Add 4 glossary entries to Appendix D and update the existing "Lint Dashboard" entry.

Since we're extending Chapter 14 (not adding a new chapter), the three navigation files (README.md, index.html, guide.html) don't need chapter-level updates — only the glossary additions need adding to appendix-d.

**Content comes from S01-S03 summaries.** The 10 data quality rules from S02, the filter API and UI from S03, and the pipeline fix context from S01 provide all the information needed.

## Steps

1. **Read the current Chapter 14 ending.** The existing "Global Lint Dashboard" section ends at ~line 394 with a tip about SHACL shapes. The Troubleshooting section follows. New sections should be inserted between the "Using the Dashboard for Data Cleanup" section and the Troubleshooting section — they extend the lint dashboard documentation naturally.

2. **Add "Data Quality Rules" section** after the existing "Using the Dashboard for Data Cleanup" section (~line 393). Include a table of all 10 rules with columns: Rule Name, Severity, Model, What It Detects, How to Fix. The 10 rules are:

   | Rule | Severity | Model | Detects | Fix |
   |------|----------|-------|---------|-----|
   | CommaInTagsValidation | Warning | basic-pkm | Tags containing commas (should be separate tags) | Remove commas; use individual tag values |
   | EmptyBodyValidation | Info | basic-pkm | Notes or Concepts with no body content | Add body content |
   | ConceptNoDefinitionValidation | Info | basic-pkm | Concepts missing a definition | Add a skos:definition |
   | TitlelessObjectValidation | Warning | basic-pkm | Objects with no title | Add a title |
   | OrphanObjectValidation | Info | basic-pkm | Objects with zero connections | Add relationships to other objects |
   | DuplicateUrlValidation | Info | basic-pkm | Same-type objects sharing a URL | Merge duplicates or differentiate URLs |
   | EmptyBodyValidation (zk) | Info | zettelkasten | Fleeting/Literature/Permanent/Structure Notes with no body | Add note content |
   | StaleProjectValidation | Info | ppv | Projects never modified | Edit or archive stale projects |
   | ActionItemNoProjectValidation | Warning | ppv | Action items not linked to a project | Link to a project |
   | ProjectNoGoalValidation | Warning | ppv | Projects not linked to a goal | Link to a goal outcome |
   | ClaimNoRationaleValidation | Info | research | Claims with no rationale | Add a rationale |

   Explain the three severity levels (Violation, Warning, Info) and how data quality rules use Warning and Info (never Violation — violations come from structural SHACL shapes).

3. **Add "Suppressing Rule Types" section.** Document: click the eye-off button on any rule row in the lint dashboard → all results for that rule disappear → "N rules suppressed" badge appears in sidebar → to un-suppress, go to Lint Settings. Explain when to use: when a rule is noisy and irrelevant to your workflow.

4. **Add "Dismissing Individual Results" section.** Document: click the × button on a specific warning/info result in the per-object lint panel → that result disappears for that object only → other results for the same rule remain → "N dismissed" indicator shows. Note that violations cannot be dismissed (they represent structural issues that must be fixed). Explain when to use: when a specific finding is intentionally not applicable to one object.

5. **Add "Filter Presets" section.** Document: "Save Current" button in dashboard sidebar → saves all current suppressions as a named preset → dropdown to switch between presets → "No preset" to clear → applying a preset replaces all current suppressions. Explain the workflow: configure suppressions, save as preset, switch between presets for different review contexts.

6. **Add "Lint Settings" section.** Document: "Manage Filters" link in dashboard sidebar → settings page with three sections: Suppressions (remove individual / clear all), Dismissals (grouped by object, remove individual / clear all), Presets (apply / rename / delete). Explain this is the management hub for all filter state.

7. **Update glossary.** Add to `docs/guide/appendix-d-glossary.md` in alphabetical order:
   - **Data Quality Rules** — SHACL-AF validation rules that detect data hygiene issues (empty bodies, orphan objects, comma-in-tags, etc.) at Warning or Info severity. Unlike structural SHACL constraints, data quality rules are advisory — they highlight potential issues but don't indicate broken data. See Chapter 14.
   - **Lint Dismissal** — Hiding a specific lint finding for one object. The finding remains visible for other objects with the same issue. Managed via the × button on warning/info results in the lint panel, or from Lint Settings. See Chapter 14.
   - **Lint Preset** — A named set of suppressed rules that can be saved, switched between, and applied to quickly configure lint filtering for different review contexts. See Chapter 14.
   - **Lint Suppression** — Hiding all lint results from a specific rule type across the entire knowledge base. Suppressions are per-user and don't affect other users. Managed from the lint dashboard or Lint Settings. See Chapter 14.
   
   Update the existing **Lint Dashboard** entry to mention filtering capabilities (suppress, dismiss, presets).

## Must-Haves

- [ ] Data Quality Rules table with all 10 rules (name, severity, model, description, fix)
- [ ] Suppressing Rule Types section with workflow description
- [ ] Dismissing Individual Results section noting violations cannot be dismissed
- [ ] Filter Presets section with save/apply/switch workflow
- [ ] Lint Settings section documenting the management page
- [ ] 4 new glossary entries in alphabetical order in appendix-d
- [ ] Existing Lint Dashboard glossary entry updated

## Verification

- `wc -l docs/guide/14-system-health-and-debugging.md` shows >550 lines (was 429)
- `grep -c "Lint Suppression\|Lint Dismissal\|Lint Preset\|Data Quality" docs/guide/appendix-d-glossary.md` returns ≥4
- Content accuracy: section headings, rule names, severity levels, and workflow descriptions match the S01-S03 implementation

## Inputs

- `docs/guide/14-system-health-and-debugging.md` — existing Chapter 14 with "Global Lint Dashboard" section ending at ~line 394
- `docs/guide/appendix-d-glossary.md` — existing glossary with "Lint Dashboard" and "Lint" entries
- S02 summary — 10 data quality rules with names, severities, models, and trigger conditions
- S03 summary — filter CRUD: suppress/dismiss/preset API and UI, lint settings management, D283 (violations not dismissable)

## Observability Impact

- **No runtime signals:** This task adds documentation only — no code changes, no new logs or endpoints.
- **Inspection surface:** `wc -l docs/guide/14-system-health-and-debugging.md` to confirm line count increased. `grep` on appendix-d for new glossary terms.
- **Future agent verification:** Read the Chapter 14 file and search for section headings: "Data Quality Rules", "Suppressing Rule Types", "Dismissing Individual Results", "Filter Presets", "Lint Settings".

## Expected Output

- `docs/guide/14-system-health-and-debugging.md` — extended with 5 new sections (~150+ lines of new content) between the lint dashboard section and troubleshooting
- `docs/guide/appendix-d-glossary.md` — 4 new entries (Data Quality Rules, Lint Dismissal, Lint Preset, Lint Suppression) + updated Lint Dashboard entry
