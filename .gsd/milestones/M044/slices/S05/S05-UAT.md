# S05: Template Hygiene & Deduplication — UAT

**Milestone:** M044
**Written:** 2026-03-25T22:00:00.301Z

## Preconditions
- Backend running with all templates accessible
- At least one Mental Model installed with objects

## Test Cases

### TC1: Object View Templates Render Correctly
1. Navigate to any object in the workspace
2. **Expected:** Object read view renders with property groups, required/optional sections visible
3. Click Edit to switch to form mode
4. **Expected:** Form renders with required fields marked, optional fields in collapsible section, grouped properties in their groups
5. Open the object in embed mode (via edge click or search)
6. **Expected:** Embed view renders identically to previous behavior

### TC2: Saved Queries Explorer
1. Open the Explorer sidebar, expand SAVED QUERIES section
2. **Expected:** Queries appear split into model-defined and user-created groups
3. Click a saved query
4. **Expected:** Query results render in the workspace tab

### TC3: Dashboard Builder
1. Navigate to Dashboard → New Dashboard
2. **Expected:** Block type selector shows categories (Visualization, Data, Text, Layout) with correct grouping
3. Add blocks from different categories
4. **Expected:** Builder renders all block options correctly

### TC4: Admin Models Page
1. Navigate to Admin → Models
2. Click a model to view its detail
3. **Expected:** Properties list shows both object and datatype properties merged correctly

### TC5: Context Rules Settings
1. Navigate to Settings → Context Rules
2. **Expected:** Rules display with conditions section visible only when conditions exist

### TC6: Notion Importer Flow
1. Navigate to Notion import page
2. **Expected:** Step bar renders with 7 steps (includes Relations step)
3. Upload a Notion export file
4. **Expected:** Upload form accepts file, scan trigger page renders
5. After scan completes, view scan results
6. **Expected:** Warning categories display correctly grouped
7. Proceed through type mapping, property mapping
8. **Expected:** Property mapping shows auto-matched fields with IRI values
9. Complete import
10. **Expected:** Import summary shows counts, skip stats, and discard option

### TC7: Obsidian Importer Flow
1. Navigate to Obsidian import page
2. **Expected:** Step bar renders with 6 steps (no Relations step)
3. Upload an Obsidian vault export
4. **Expected:** Upload form accepts file with correct labels
5. Complete import flow
6. **Expected:** Import summary shows counts with "links" label (not "relations")

### TC8: Guide Page Data-Driven Rendering
1. Navigate to Docs & Tutorials page (/guide)
2. **Expected:** All sections visible: Interactive Tutorials (2 cards), User Guide (55 chapters organized in sections), External References (3 links)
3. Click an Interactive Tutorial card
4. **Expected:** Tour launches correctly
5. Click a chapter button
6. **Expected:** Chapter content loads via htmx
7. Scroll to appendix chapters
8. **Expected:** Appendix chapters have distinct styling (docs-chapter-appendix class)
9. Click an External Reference link
10. **Expected:** Opens in new tab

### TC9: Cross-Importer Partial Sharing Verification
1. Compare Notion and Obsidian step bars visually
2. **Expected:** Both use same layout but different step counts (7 vs 6)
3. Compare upload forms
4. **Expected:** Notion shows "Notion workspace" label, Obsidian shows no importer label
5. Compare import summaries
6. **Expected:** Notion shows "unresolved relations" section, Obsidian shows "unresolved links" section

### Edge Cases
- Object with zero properties: form should render empty state correctly
- Object with only required properties: optional section should be empty/hidden
- Guide page with JavaScript disabled: chapter buttons should still render (static HTML from Jinja2 loop)
- Importer with zero warnings: warning_categories section should be hidden
