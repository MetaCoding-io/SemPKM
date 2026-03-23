---
slice: S03
milestone: M036
type: UAT
---

# S03 UAT: OKR Progress + Decision Matrix Weighted Scoring

## Preconditions

1. Docker stack running (`docker compose up -d`)
2. `business-planning` model installed via Admin > Mental Models
3. Seed data loaded (1 Objective + 3 Key Results, 1 Decision Matrix + 3 Criteria + 3 Alternatives + 9 Scores)

---

## Test Case 1: OKR Objective with Progress Bars

**Steps:**
1. Navigate to workspace, open Views section
2. Select type `bp:Objective` or `bp:KeyResult` from the type picker
3. Switch to the "OKR Progress" view (renderer type `okr`)

**Expected:**
- One Objective card ("Improve Product Quality") with aggregate progress bar
- Three Key Results listed under the objective:
  - "Reduce Bug Count" — 80% green bar
  - "Increase Test Coverage" — 45% amber bar
  - "Customer Satisfaction Score" — 10% red bar
- Each KR shows currentValue / targetValue and percentage
- Objective-level progress bar shows ~45% (average of 80 + 45 + 10 = 135/3)

## Test Case 2: OKR Click-to-Edit currentValue

**Steps:**
1. In the OKR view from Test Case 1, click on a Key Result's current value number (e.g., the "80" in "80 / 100")
2. An inline input appears — change the value to "95"
3. Press Enter or click away (blur)

**Expected:**
- Value saves via `object.patch` API (check Network tab: PATCH to command endpoint)
- Progress bar updates client-side: fill width increases, still green (95%)
- KR row flashes briefly with success feedback (`.okr-save-ok` class)
- Objective aggregate progress recalculates on next view refresh

## Test Case 3: OKR Division-by-Zero Guard

**Steps:**
1. Create a new Key Result with `targetValue = 0` and `currentValue = 50`
2. Open the OKR view

**Expected:**
- Progress displays as 0% (not infinity, not error)
- Red progress bar (0% < 30%)
- No JavaScript errors in console

## Test Case 4: OKR Over-Target Clamping

**Steps:**
1. Create a Key Result with `currentValue = 150` and `targetValue = 100`
2. Open the OKR view

**Expected:**
- Progress displays as 100% (clamped, not 150%)
- Green progress bar (100% ≥ 70%)

## Test Case 5: Decision Matrix Weighted Scoring

**Steps:**
1. Navigate to workspace, select type `bp:Score` or `bp:Alternative`
2. Switch to the "Decision Matrix Scoring" view (renderer type `decision-matrix`)

**Expected:**
- Table shows 3 alternatives (Rust, Go, Python) as rows
- Column headers show 3 criteria: Performance (weight 8), Cost (weight 6), Ease of Use (weight 4)
- Each cell shows the score value
- Weighted Total column shows computed `Σ(weight × value)` for each alternative
- Alternatives ranked by weighted total descending
- Top 3 show rank badges: 🥇, 🥈, 🥉

## Test Case 6: Decision Matrix Column Sorting

**Steps:**
1. In the Decision Matrix view from Test Case 5, click on the "Performance" column header
2. Click again to reverse sort direction

**Expected:**
- First click sorts alternatives by Performance score ascending (sort-asc indicator on header)
- Second click sorts descending (sort-desc indicator)
- Rank badges update to reflect new sort order
- Click "Weighted Total" header to return to default ranking

## Test Case 7: Decision Matrix Tie Handling

**Steps:**
1. Create two alternatives with identical weighted totals (e.g., both score 7 on all criteria)
2. Open the Decision Matrix view

**Expected:**
- Both alternatives show the same rank number
- Next alternative after the tie skips (e.g., rank 1, 1, 3 — not 1, 1, 2)

## Test Case 8: Dark Mode Support

**Steps:**
1. Open OKR view, toggle to dark mode (theme toggle in workspace)
2. Open Decision Matrix view in dark mode

**Expected:**
- OKR: objective cards have dark backgrounds, progress bar colors adjust (darker green/amber/red), text remains readable, click-to-edit input styled for dark
- Decision Matrix: table header/body have dark backgrounds, rank badges adjust colors, score tinting visible against dark cells, sort indicators visible

## Test Case 9: Scope-Changed Sync

**Steps:**
1. Open OKR view showing Key Results
2. In another tab/panel, create a new Key Result linked to the same Objective
3. Trigger a scope change (type filter pill click or manual `sempkm:scope-changed` event)

**Expected:**
- OKR view re-fetches data via htmx
- New Key Result appears under its Objective
- Aggregate progress recalculates to include the new KR

## Test Case 10: Empty State

**Steps:**
1. Create a new type that has no OKR/Decision Matrix SHACL structure
2. Try to open it with the `okr` renderer (via URL param or ViewSpec)

**Expected:**
- Error template displayed explaining the type lacks required SHACL structure (currentValue/targetValue for OKR, value/alternative/criterion for Decision Matrix)
- No 500 error, no blank page

## Test Case 11: SPARQL Queryability

**Steps:**
1. Open SPARQL console
2. Run: `SELECT ?kr ?progress WHERE { ?kr a <urn:sempkm:model:bp:KeyResult> ; <urn:sempkm:model:bp:currentValue> ?cv ; <urn:sempkm:model:bp:targetValue> ?tv . BIND((?cv / ?tv * 100) AS ?progress) } ORDER BY DESC(?progress)`

**Expected:**
- Returns 3 rows with computed progress values matching the OKR view display
- Demonstrates that OKR data is fully SPARQL-queryable as structured RDF

## Test Case 12: JSON Data Endpoints

**Steps:**
1. `curl http://localhost:3901/browser/views/generic/okr/data?type=urn:sempkm:model:bp:KeyResult`
2. `curl http://localhost:3901/browser/views/generic/decision-matrix/data?type=urn:sempkm:model:bp:Score`

**Expected:**
- OKR endpoint returns JSON with `objectives` array (each with `key_results` and `progress`) and `ungrouped` array
- Decision Matrix endpoint returns JSON with `alternatives` array (each with `weighted_score` and `rank`) and `criteria` array
