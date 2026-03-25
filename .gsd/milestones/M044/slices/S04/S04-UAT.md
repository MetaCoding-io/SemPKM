# S04: CSS Theme Completion & Utilities — UAT

**Milestone:** M044
**Written:** 2026-03-25T21:03:11.362Z

## Preconditions
- Docker dev stack running (`docker compose up -d`)
- Access to browser at http://localhost:3000
- At least one Mental Model installed with sample data

## Test Cases

### TC-01: Theme Variable Adoption Metrics
**Steps:**
1. Run: `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l`
2. Run: `rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l`
3. Run: `rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'`

**Expected:**
- Step 1 returns 0 (≤10 threshold)
- Step 2 returns 0 (≤20 threshold)
- Step 3 returns zero results (exit code 1)

### TC-02: Light Mode — Workspace Page
**Steps:**
1. Navigate to http://localhost:3000/browser/
2. Ensure theme is set to light mode
3. Inspect sidebar navigation — explorer sections, type list with icons
4. Open an object tab — verify form fields, buttons, accent colors
5. Open SPARQL console — verify syntax highlighting, run button, results table

**Expected:**
- All accent colors (teal) render correctly, no gray/black substitutions
- Buttons have visible hover states
- Panel borders and backgrounds are properly themed
- No invisible elements or missing colors

### TC-03: Dark Mode — Workspace Page
**Steps:**
1. Switch to dark mode via Settings or theme toggle
2. Repeat all Step 3-5 checks from TC-02

**Expected:**
- Dark backgrounds with proper contrast
- Accent colors auto-adapt (slightly brighter teal on dark background)
- No washed-out or invisible text
- Panel borders visible against dark backgrounds

### TC-04: Light Mode — Settings Page
**Steps:**
1. Navigate to Settings page
2. Inspect form controls, toggle switches, category navigation
3. Check "Modified" badge styling
4. Verify button colors (primary, danger, default)

**Expected:**
- All form elements properly themed
- Badge colors render with correct accent/warning tones
- Button hover states work

### TC-05: Dark Mode — Settings Page
**Steps:**
1. Switch to dark mode
2. Repeat all checks from TC-04

**Expected:**
- Form elements have proper dark-mode contrast
- Badges adapt colors automatically
- No color artifacts from removed dark-mode override blocks

### TC-06: Import Wizard Pages
**Steps:**
1. Navigate to an import page (Notion, Obsidian, or VFS)
2. Inspect stepper progress bar — active step, completed step, pending step
3. Check stat cards, detected types list, folder badges
4. Switch between light and dark mode

**Expected:**
- Stepper active step uses accent color, completed step uses green checkmark
- Stat cards have proper background tints in both modes
- Type list items have correctly colored folder badges

### TC-07: BMC View (Business Model Canvas)
**Steps:**
1. Open a BMC view for a type that has one
2. Verify 9 section colors render with distinct pastel tints
3. Switch to dark mode

**Expected:**
- Each BMC section has a distinct color tint (key partners=blue, key activities=indigo, etc.)
- Dark mode sections have brighter tints on dark backgrounds
- No gray/transparent sections where color should appear

### TC-08: Quadrant View
**Steps:**
1. Open a quadrant view
2. Verify 4 quadrant colors render distinctly (green, yellow, red, blue)
3. Switch between light and dark mode

**Expected:**
- Each quadrant has its own background tint
- Items within quadrants have proper contrast
- Dark mode quadrants auto-adapt without missing color

### TC-09: OKR View
**Steps:**
1. Open an OKR view
2. Verify status color coding (on-track=green, at-risk=amber, behind=red)
3. Progress bars render with correct fill colors
4. Switch between light and dark mode

**Expected:**
- Status indicators use correct semantic colors
- Progress bars visible in both themes

### TC-10: Decision Matrix View
**Steps:**
1. Open a decision matrix view
2. Verify rating cells have color gradients (red-to-green scale)
3. Check medal styling (gold, silver, bronze)
4. Switch between light and dark mode

**Expected:**
- Rating cells show proper color scale
- Medal colors render (gold, silver, bronze)
- Dark mode auto-adapts cell tints

### TC-11: Breakpoint Verification
**Steps:**
1. Run: `rg '@media.*max-width' frontend/static/css/`
2. Verify all entries use either 600px or 768px

**Expected:**
- Only 600px and 768px breakpoints present
- No 640px, 800px, or other non-standard values
