# S01: M034 Feature Documentation — UAT Script

## Preconditions

- SemPKM instance running with basic-pkm and PPV Mental Models installed
- User guide accessible at `/guide` (in-app) and via `docs/guide/index.html` (standalone)
- At least one bpkm:Task with a `bpkm:scheduledStart` date exists (for calendar/timeline verification)

---

## Test Case 1: Chapter 7 — Calendar View Documentation

**Goal:** Verify calendar view section exists with accurate feature descriptions.

1. Open `docs/guide/07-browsing-and-visualizing.md`
2. Search for "## Calendar View" — **Expected:** Section exists with subsections for opening, interactions, recurring tasks, cross-view drag, composable planning
3. Verify the section mentions drag-to-reschedule with optimistic rollback (matches `calendar.js` behavior)
4. Verify the recurring tasks subsection mentions RRULE presets and EXDATE exclusions (matches `recurrence-editor.js`)
5. Verify cross-view drag mentions dragging from kanban columns and the explorer sidebar
6. Verify composable planning mentions opening calendar and kanban side by side with scope synchronization

**Pass criteria:** All 5 sub-checks confirm documented features match actual codebase behavior.

## Test Case 2: Chapter 7 — Timeline/Gantt View Documentation

1. Search for "## Timeline" in chapter 7
2. Verify section mentions zoom levels (Quarter Day through Year) — matches Frappe Gantt config in `timeline_view.html`
3. Verify dependency arrows are documented
4. Verify drag-to-reschedule mentions the calendar PATCH endpoint

**Pass criteria:** Timeline features match `timeline_view.html` template behavior.

## Test Case 3: Chapter 7 — Map View Documentation

1. Search for "## Map View" in chapter 7
2. Verify section mentions two-pass geo field detection (well-known IRI match + local-name heuristic) — matches `_detect_geo_fields()` in `ViewSpecService`
3. Verify marker clusters and OpenStreetMap tiles are mentioned
4. Verify chunked loading is documented

**Pass criteria:** Map features match `map_view.html` template and `_detect_geo_fields()` logic.

## Test Case 4: Chapter 28 — Task Templates Documentation

1. Open `docs/guide/28-dashboards-and-workflows.md`
2. Search for "## Task Templates" — **Expected:** Section exists
3. Verify CRUD operations are documented (create, edit, delete via REST API)
4. Verify "Create from Template" command palette entry is mentioned
5. Verify @slot: cross-command references for batch instantiation are explained
6. Open SemPKM, press Alt+K, type "template" — **Expected:** "Create from Template" submenu appears (confirms docs match UI)

**Pass criteria:** Template CRUD and palette integration documented accurately.

## Test Case 5: Chapter 28 — Review Workflows Documentation

1. Search for "## Review Workflows" in chapter 28
2. Verify all 5 seeded workflows are listed: Create & Review, Weekly Review, Monthly Review, Quarterly Review, Yearly Review
3. Verify step counts match `backend/app/dashboard/seed.py` (e.g., Weekly Review has the documented number of steps)
4. Verify palette launch is documented
5. Open SemPKM, press Alt+K, type "workflow" — **Expected:** Workflow submenu shows the 5 seeded workflows (confirms docs match UI)

**Pass criteria:** All 5 workflows documented with accurate step counts and launch instructions.

## Test Case 6: Glossary — M034 Terms

1. Open `docs/guide/appendix-d-glossary.md`
2. Search for each term: Calendar View, Cross-View Drag, Gantt Chart, Recurrence, Review Workflow, Scope Propagation, Task Template, Timeline View
3. Verify each has a definition paragraph and a cross-reference to the relevant chapter (7 or 28)

**Pass criteria:** All 8 terms present with definitions and cross-references.

## Test Case 7: Three-File Nav Sync

1. Extract chapter file references from `docs/guide/README.md`
2. Extract `data-file` attributes from `docs/guide/index.html`
3. Extract `hx-get` paths from `backend/app/templates/guide.html`
4. Compare all three sets — **Expected:** Identical chapter lists (order may differ)
5. Verify no duplicate chapter numbers exist in `docs/guide/index.html`

**Automated check:**
```bash
diff <(grep -oP 'data-file="\K[^"]*' docs/guide/index.html | sort) \
     <(grep -oP 'hx-get="/guide/\K[^"]*' backend/app/templates/guide.html | sort)
# Expected: no output (identical)
```

**Pass criteria:** Zero diff between index.html and guide.html chapter lists.

## Test Case 8: In-App Guide Navigation

1. Navigate to `/guide` in a running SemPKM instance
2. Click "Chapter 7: Browsing and Visualizing Data" — **Expected:** Chapter loads, scroll down to find Calendar View section
3. Click "Chapter 28: Dashboards & Workflows" — **Expected:** Chapter loads, scroll down to find Task Templates and Review Workflows sections
4. Click "Appendix D: Glossary" — **Expected:** Glossary loads, Calendar View / Timeline View entries visible

**Pass criteria:** All three chapters load and display the new content in the in-app guide.

---

## Edge Cases

- **Chapter 7 renderer count:** Verify the intro paragraph mentions all 7 renderers (Table, Cards, Graph, Kanban, Calendar, Timeline, Map). Run: `grep -i "table\|cards\|graph\|kanban\|calendar\|timeline\|map" docs/guide/07-browsing-and-visualizing.md | head -5`
- **Chapter 29 collision:** Two files share chapter 29 (app-platform, mental-model-catalog). This is pre-existing and not introduced by S01. S02 may resolve it.
- **Glossary alphabetical order:** Verify new entries are placed alphabetically among existing entries, not appended at the end.
