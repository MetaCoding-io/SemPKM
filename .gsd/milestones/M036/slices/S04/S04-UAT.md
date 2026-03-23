# S04 UAT: Extended Framework Library

## Preconditions

- Docker Compose stack running (`docker compose up -d`)
- `business-planning` model installed via Admin > Mental Models
- User authenticated to the workspace

---

## Test Case 1: SWOT Analysis — Quadrant Renderer with Framework Labels

**Steps:**
1. Navigate to workspace, click "+" to create a new object
2. Select type `bp:SWOTAnalysis`, give it title "Product Launch SWOT"
3. Create 4 `bp:SWOTItem` objects linked via `bp:belongsToSWOT`:
   - "Strong brand" with nature=internal, valence=positive
   - "Small team" with nature=internal, valence=negative
   - "Growing market" with nature=external, valence=positive
   - "Price competition" with nature=external, valence=negative
4. Open the quadrant view for SWOTItem type

**Expected:**
- Quadrant labels show "Strengths" (internal+positive), "Weaknesses" (internal+negative), "Opportunities" (external+positive), "Threats" (external+negative)
- Each item appears in its correct quadrant
- Dragging "Strong brand" from Strengths to Weaknesses updates `bp:valence` from "positive" to "negative"

---

## Test Case 2: BCG Matrix — Quadrant Labels

**Steps:**
1. Create a `bp:BCGMatrix` titled "Portfolio Review"
2. Create 2 `bp:BCGItem` objects:
   - "Cloud Product" with marketGrowth=high, marketShare=high
   - "Legacy Tool" with marketGrowth=low, marketShare=low
3. Open the quadrant view for BCGItem

**Expected:**
- Quadrant labels show "Stars ⭐" (high growth + high share), "Question Marks ❓" (high growth + low share), "Cash Cows 💰" (low growth + high share), "Dogs 🐕" (low growth + low share)
- "Cloud Product" in Stars quadrant, "Legacy Tool" in Dogs quadrant

---

## Test Case 3: Porter's Five Forces — Table View with Enum Dropdown

**Steps:**
1. Create a `bp:PorterAnalysis` titled "Industry Analysis"
2. Create a `bp:PorterForce` titled "New Entrants"
3. In the create/edit form, verify `bp:forceType` shows a dropdown with exactly 5 options: Competitive Rivalry, Supplier Power, Buyer Power, Threat of Substitution, Threat of New Entrants
4. Set forceType to "Threat of New Entrants", intensity to "High"
5. Open the PorterForce table view

**Expected:**
- Form shows dropdown select (not free-text) for forceType and intensity fields
- Table view lists the force with correct type and intensity columns

---

## Test Case 4: RACI Matrix — Enum Constraints

**Steps:**
1. Create a `bp:RACIMatrix` titled "Platform Rewrite"
2. Create a `bp:RACIEntry` titled "API Design"
3. Verify `bp:raciRole` dropdown has exactly 4 options: Responsible, Accountable, Consulted, Informed
4. Set role to "Responsible", save

**Expected:**
- SHACL form renders raciRole as a dropdown, not free-text
- Saved entry appears in table view with correct role value

---

## Test Case 5: Balanced Scorecard — Perspective Enum

**Steps:**
1. Create a `bp:BalancedScorecard` titled "Strategy Scorecard"
2. Create a `bp:BSCItem` titled "Customer Satisfaction"
3. Verify `bp:bscPerspective` dropdown has exactly 4 options: Financial, Customer, Internal Process, Learning & Growth
4. Fill in measure ("NPS Score") and target ("80")

**Expected:**
- All fields render correctly in SHACL form
- Table view shows perspective, measure, and target columns

---

## Test Case 6: Lean Canvas — 9 Section Types

**Steps:**
1. Create a `bp:LeanCanvas` titled "Startup Canvas"
2. Create a `bp:LeanCanvasSection` titled "Problem Statement"
3. Verify `bp:leanSectionType` dropdown has exactly 9 options: Problem, Customer Segments, Unique Value Proposition, Solution, Channels, Revenue Streams, Cost Structure, Key Metrics, Unfair Advantage

**Expected:**
- All 9 Lean Canvas sections available in the dropdown
- Saving with sectionType + content renders correctly in table view

---

## Test Case 7: Seed Data Populated After Install

**Steps:**
1. After model install, navigate to table views for each extended type
2. Check each type has seed instances

**Expected:**
- SWOTItem: 3 seed items across different quadrants
- BCGItem: 3 seed items
- AnsoffItem: 2 seed items
- StakeholderItem: 3 seed items
- RiskItem: 2 seed items
- PorterForce: 3 seed items with different force types
- PESTLEFactor: 3 seed items with different categories
- BSCItem: 2 seed items in different perspectives
- RACIEntry: 3 seed items with different roles
- VCActivity: 2 seed items (primary + support)
- LeanCanvasSection: 2 seed items with different section types

---

## Test Case 8: Manifest Icons Render Correctly

**Steps:**
1. Open the object browser explorer, expand each extended framework type
2. Verify each type has a distinct Lucide icon

**Expected:**
- All 22 new types (11 containers + 11 items) show icons in the explorer sidebar
- No types show the default/fallback icon
- Icons are visually distinguishable (e.g., crosshair for SWOT, git-branch for BCG, etc.)

---

## Test Case 9: Quadrant Data Endpoint Works for All Quadrant Types

**Steps:**
1. Open browser dev tools, navigate to each quadrant type's data endpoint:
   - `/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:SWOTItem`
   - `/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:BCGItem`
   - `/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:AnsoffItem`
   - `/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:StakeholderItem`
   - `/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:RiskItem`

**Expected:**
- Each returns valid JSON with `quadrants` array of 4 entries
- Each quadrant has a `label` matching the framework (e.g., "Strengths" not "nature: internal / valence: positive")
- Seed items appear in their correct quadrants

---

## Edge Cases

### E1: Generic Label Fallback
If a new quadrant type is added to shapes but NOT to `_QUADRANT_LABELS`/`_AXIS_KEYWORD_PAIRS`, the label should fall back to "AxisName: value / AxisName: value" format — not crash.

### E2: Dark Mode
All table views and quadrant views for extended types should render correctly in dark mode (no invisible text, no broken borders).

### E3: Model Reinstall
Uninstalling and reinstalling the business-planning model should preserve all 32 types with correct shapes, views, and seed data.
