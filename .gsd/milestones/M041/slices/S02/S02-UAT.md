# S02: Frontend Code Quality Audit — UAT

**Preconditions:**
- The file `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` exists
- The SemPKM repository is at the state where the audit was conducted
- `rg`, `fd`, `grep`, `wc` are available on PATH

---

## TC-01: Findings file structure completeness

**Steps:**
1. Run `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`
2. Run `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`
3. Run `grep -c "Detection command:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`
4. Verify the file has 5 top-level dimension sections by running `grep "^## " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`

**Expected:**
- Step 1: ≥ 21 (21 individual finding headings)
- Step 2: ≥ 21 (each finding has a Severity line)
- Step 3: ≥ 15 (most findings have detection commands; some informational findings may not)
- Step 4: Output includes: "JS Structure & Global State", "DOM & Event Patterns", "CSS Architecture & Theming", "Jinja2 Template Hygiene", "htmx Consistency"

---

## TC-02: Every finding has category, severity, effort, and file references

**Steps:**
1. For each `### Finding` block, verify presence of **Severity:** (Critical/High/Medium/Low), **Effort:** (Small/Medium/Large), **Category:** line
2. Spot-check 5 findings for specific file references (e.g., `workspace.js`, `copilot.js`, `object_form.html`)
3. Verify no finding has a generic "various files" without at least one concrete filename

**Expected:**
- All 21 findings have Severity, Effort, and Category fields
- File references are specific (e.g., `frontend/static/js/workspace.js`, `backend/app/templates/browser/guide.html`) not generic

---

## TC-03: JS monolith finding (JS-01) is accurate

**Steps:**
1. Run `wc -l frontend/static/js/workspace.js`
2. Run `grep -cE "function\s+\w+\(|=\s*function\s*\(|=>\s*\{" frontend/static/js/workspace.js`

**Expected:**
- Step 1: ~5,409 lines (within ±100 of reported value)
- Step 2: ~170 functions (within ±20 of reported value)

---

## TC-04: Event listener imbalance finding (DOM-01) is reproducible

**Steps:**
1. Run `rg "addEventListener" frontend/static/js/ -n --count`
2. Run `rg "removeEventListener" frontend/static/js/ -n --count`
3. Sum the counts from each command

**Expected:**
- addEventListener total: ~208 (within ±15)
- removeEventListener total: ~20 (within ±5)
- Imbalance: ~188 (within ±20)

---

## TC-05: Fetch error handling finding (DOM-03) is reproducible

**Steps:**
1. Run `rg "fetch\(" frontend/static/js/ --count` to get total fetch calls
2. Run `rg "\.catch\(" frontend/static/js/ --count` to see catch usage
3. Spot-check `workspace.js` by running `rg "fetch\(" frontend/static/js/workspace.js -A10 -n` and manually verifying that several fetch calls lack `.catch()` or `resp.ok` checks

**Expected:**
- Total fetch calls: ~131 (within ±15)
- workspace.js fetches: ~49 (within ±10)
- Manual spot-check confirms at least 5 fetch calls in workspace.js without error handling

---

## TC-06: CSS hardcoded color finding (CSS-01) three-tier classification is correct

**Steps:**
1. Run `rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/ -n | wc -l` — total hex instances
2. Run `rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/ -n | grep "var(--" | wc -l` — var() fallback context
3. Run `rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/theme.css -n | wc -l` — theme definitions
4. Subtract steps 2 and 3 from step 1 to get standalone hardcoded count

**Expected:**
- Total: ~499 (within ±30)
- var() fallbacks: ~360 (within ±30)
- Theme definitions: ~55 (within ±10)
- Standalone: ~84 (within ±20)

---

## TC-07: Jinja2 namespace() hack finding (TPL-02) is reproducible

**Steps:**
1. Run `rg "namespace\(" backend/app/templates/ -n`
2. Verify each match uses Jinja2 `namespace()` for cross-scope variable mutation
3. Run `rg "\.append\(" backend/app/templates/ -n`

**Expected:**
- Step 1: ~7 matches in files like `object_read.html`, `object_form.html`, `object_tab.html`, `object_embed.html`, `property_mapping.html`
- Step 3: ~10 matches across templates like `dashboard_builder.html`, `saved_queries_explorer.html`, `scan_results.html`

---

## TC-08: htmx trigger pattern diversity (HTMX-02) is reproducible

**Steps:**
1. Run `rg 'hx-trigger="([^"]*)"' backend/app/templates/ -or '$1' | sed 's/.*://' | sort | uniq -c | sort -rn`
2. Count distinct trigger patterns

**Expected:**
- At least 10 distinct trigger patterns visible
- `change` is the most common (~21)
- `click once` is second (~16)
- `load` is third (~14)
- At least one instance of `delay:200ms` and `delay:300ms` showing the inconsistency

---

## TC-09: Notion/Obsidian template duplication finding (TPL-03) spot-check

**Steps:**
1. Run `diff backend/app/templates/notion/partials/upload_form.html backend/app/templates/obsidian/partials/upload_form.html | grep -c "^[<>]"`
2. Run `diff backend/app/templates/notion/partials/import_progress.html backend/app/templates/obsidian/partials/import_progress.html | grep -c "^[<>]"`

**Expected:**
- upload_form.html diff: ~18 lines (files are ~90% identical)
- import_progress.html diff: ~10 lines (files are ~95% identical)

---

## TC-10: Hardcoded URL count (TPL-04) is reproducible

**Steps:**
1. Run `rg '(href|action|hx-get|hx-post|hx-put|hx-delete|hx-patch)="/' backend/app/templates/ --count | awk -F: '{sum+=$2} END{print sum}'`
2. Run `rg "url_for" backend/app/templates/ --count`

**Expected:**
- Step 1: ~349 hardcoded URLs (within ±30)
- Step 2: 0 url_for() calls

---

## Edge Cases

### EC-01: Findings file is not a valid report if detection commands fail

**Steps:**
1. Pick 3 detection commands from different findings and run them
2. Verify each returns non-empty output and the count is within ±20% of the reported value

**Expected:**
- All 3 commands execute successfully (exit code 0 or 1 for grep with matches)
- Counts are within ±20% of reported values — if code has changed since audit, differences are expected and indicate which findings need re-verification

### EC-02: CSS variable adoption percentage is correctly calculated

**Steps:**
1. Run `rg "var(--" frontend/static/css/ --count | awk -F: '{sum+=$2} END{print sum}'`
2. Run the standalone hex count from TC-06 step 4
3. Calculate var_count / (var_count + standalone_hex_count) × 100

**Expected:**
- Result: ~89.7% (within ±2%)
