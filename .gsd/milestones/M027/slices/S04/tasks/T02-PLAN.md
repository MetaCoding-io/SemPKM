---
estimated_steps: 4
estimated_files: 6
---

# T02: Write user guide chapter and update navigation files

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M027

## Description

Write Chapter 39: Notion Import as a user guide chapter documenting the full 7-step Notion import wizard workflow. Follow Chapter 24 (Obsidian Onboarding, 232 lines) as the structural template, adapted for Notion's database/column/relation model. Update all three navigation files per the KNOWLEDGE.md rule "User guide has THREE files that must stay in sync."

## Steps

1. **Write `docs/guide/39-notion-import.md`** following Chapter 24's structure. Sections:

   - **Introduction** — What Notion import does: uploads a Notion workspace ZIP export and imports databases as typed objects, columns as properties, relations as edges. Preserves markdown bodies.
   - **Prerequisites** — (1) A Mental Model installed (link to Ch 10), (2) A Notion ZIP export (instructions: Settings & members → Export all workspace content → Export format: Markdown & CSV → ZIP download)
   - **Step 1: Upload** — Navigate to Tools > Import Notion from sidebar (or command palette "Import > Notion"). Upload ZIP. One import per user at a time. Can discard to start over.
   - **Step 2: Review Scan Results** — Stat cards showing database count, page count. Database column summaries with type badges (text, number, date, select, multi_select, checkbox, url, relation). Standalone pages listed. Detected cross-database relations shown with match percentage. Warnings for malformed CSV or empty databases.
   - **Step 3: Type Mapping** — Map each database to a Mental Model type. Standalone pages get a separate type mapping. Skip databases by leaving "— Skip —" selected.
   - **Step 4: Property Mapping** — Map CSV columns to RDF predicates. Columns grouped by type. Auto-suggest pre-selects matching SHACL property names. Relation-type columns excluded (handled in next step).
   - **Step 5: Relation Mapping** — Map detected cross-database relations to edge predicates. Only appears when relations were detected in scan. Shows source→target with match percentage badge.
   - **Step 6: Preview** — Review mapping summary table. Sample object cards show how data will look. Confirm or go back to adjust mappings.
   - **Step 7: Import** — Click Import. SSE progress bar shows object creation (Pass 1) then relation resolution (Pass 2). Import Complete summary with stat cards: Created, Edges, Skipped, Duration. Collapsible sections for unresolved relations and errors.
   - **After Import** — Browse Imported Objects button opens workspace. Import More for additional ZIPs. Discard to clean up.
   - **How Notion Concepts Map to SemPKM** — Comparison table:
     | Notion Concept | SemPKM Equivalent |
     | Database | Type (from Mental Model) |
     | Row/Page | Object |
     | Property/Column | RDF Predicate |
     | Relation | Edge |
     | Standalone Page | Object (content type) |
     | Select/Multi-select | Enum / Tags |
   - **Troubleshooting** — Common issues: "No databases detected" (check ZIP has CSV files), "0 types available" (install a Mental Model first), "Unresolved relations" (duplicate titles in target database), "Import takes too long" (large exports are normal, watch SSE progress)
   - **See Also** — Link to Ch 10 (Mental Models), Ch 24 (Obsidian Import), Appendix A (env vars)
   - **Navigation footer** — Previous: Ch 38 | Next: Appendix A

2. **Update `docs/guide/README.md`** — Add line after the Ch 38 entry:
   ```
   39. [Notion Import](39-notion-import.md)
   ```

3. **Update all three navigation files:**
   - `docs/guide/index.html` — Add `<li><a href="#" data-file="39-notion-import.md">39. Notion Import</a></li>` after the Ch 38 line (line ~481)
   - `backend/app/templates/guide.html` — Add a `<button>` entry after the Ch 38 button and before the Appendix A button:
     ```html
     <button class="docs-chapter-item"
             hx-get="/guide/39-notion-import.md"
             hx-target="#app-content"
             hx-swap="innerHTML"
             hx-push-url="true">
       <i data-lucide="file-text"></i>
       <span>39. Notion Import</span>
     </button>
     ```
   - `docs/guide/38-hosted-demo.md` — Change the "Next" link from Appendix A to Chapter 39:
     ```
     **Previous:** [Chapter 37: Monday.com Sync](37-monday-sync.md) | **Next:** [Chapter 39: Notion Import](39-notion-import.md)
     ```
   - `docs/guide/appendix-d-glossary.md` — Add glossary entry:
     ```
     **Notion Import**
     A built-in import wizard that converts a Notion workspace ZIP export (Markdown & CSV format) into SemPKM objects. Databases become typed objects, columns become properties, and Notion relations become edges. Supports cross-database relation resolution by title matching. See [Chapter 39: Notion Import](39-notion-import.md).
     ```

4. **Verify navigation chain is complete:** Ch 37 → Ch 38 → Ch 39 → Appendix A (check Previous/Next links on each).

## Must-Haves

- [ ] `docs/guide/39-notion-import.md` exists with Prerequisites, 7 wizard steps, concept mapping table, troubleshooting, navigation footer
- [ ] `docs/guide/README.md` has Ch 39 TOC entry
- [ ] `docs/guide/index.html` has Ch 39 sidebar entry
- [ ] `backend/app/templates/guide.html` has Ch 39 in-app button
- [ ] `docs/guide/38-hosted-demo.md` "Next" link points to Ch 39
- [ ] `docs/guide/appendix-d-glossary.md` has "Notion Import" entry

## Verification

- `test -f docs/guide/39-notion-import.md` — file exists
- `wc -l docs/guide/39-notion-import.md` — at least 150 lines (comparable to Ch 24's 232)
- `grep "39-notion-import" docs/guide/README.md` — returns TOC entry
- `grep "39-notion-import" docs/guide/index.html` — returns sidebar entry
- `grep "39-notion-import" backend/app/templates/guide.html` — returns in-app button
- `grep "Chapter 39" docs/guide/38-hosted-demo.md` — navigation link present
- `grep "Notion Import" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "Appendix A" docs/guide/39-notion-import.md` — "Next" link to Appendix A present
- `grep -rn "^<<<<<<< " docs/guide/39-notion-import.md` — zero conflict markers

## Inputs

- `docs/guide/24-obsidian-onboarding.md` — Structural template (232 lines). Adapt the section structure for Notion's 7-step wizard.
- `docs/guide/38-hosted-demo.md` — Previous chapter. "Next" link must be updated to point to Ch 39.
- `docs/guide/README.md` — TOC file. Add entry after line 67 (Ch 38).
- `docs/guide/index.html` — Sidebar HTML. Add `<li>` after line ~481 (Ch 38).
- `backend/app/templates/guide.html` — In-app page. Add `<button>` after line ~390 (Ch 38).
- `docs/guide/appendix-d-glossary.md` — Glossary. Add "Notion Import" entry near "Monday.com Sync" alphabetically.
- S01/S02/S03 summaries — Feature descriptions for each wizard step.

## Expected Output

- `docs/guide/39-notion-import.md` — ~200-line user guide chapter with 7 wizard steps, concept mapping table, and troubleshooting
- `docs/guide/README.md` — Updated with Ch 39 TOC entry
- `docs/guide/index.html` — Updated with Ch 39 sidebar link
- `backend/app/templates/guide.html` — Updated with Ch 39 in-app button
- `docs/guide/38-hosted-demo.md` — "Next" link updated to Ch 39
- `docs/guide/appendix-d-glossary.md` — "Notion Import" glossary entry added

## Observability Impact

This task is documentation-only — no runtime signals change. The guide chapter is served as a static Markdown file rendered by the `/guide/<filename>` endpoint. Observability:

- **Serving:** The chapter is served at `/guide/39-notion-import.md` via the same guide template as all other chapters. A 404 on this URL means the file is missing from the `docs/guide/` volume mount.
- **Navigation sync:** If Ch 39 appears in the sidebar but clicking it returns a blank page, check that all three navigation files (`README.md`, `index.html`, `guide.html`) reference `39-notion-import.md` with the correct filename.
- **Failure state:** No new error paths. The only failure mode is a missing or misnamed file, visible as a 404 in browser DevTools network tab.
