---
phase: quick-30
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/30-investigate-firefox-e2e-test-failures-an/FIREFOX-TEST-FAILURES.md
autonomous: true
requirements: [QUICK-30]

must_haves:
  truths:
    - "Summary document exists with all 12 failing tests documented"
    - "Root causes are grouped and explained with actionable fix guidance"
    - "Pass/fail statistics are accurate (211/223 pass, 12 fail)"
  artifacts:
    - path: ".planning/quick/30-investigate-firefox-e2e-test-failures-an/FIREFOX-TEST-FAILURES.md"
      provides: "Complete Firefox e2e test failure analysis"
      min_lines: 60
  key_links: []
---

<objective>
Create a summary document of Firefox e2e test failures with root cause analysis and fix guidance.

Purpose: Document the 12 failing Firefox tests (out of 223) so fixes can be planned and prioritized.
Output: FIREFOX-TEST-FAILURES.md with grouped failures, root causes, and suggested fixes.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Firefox test failure summary document</name>
  <files>.planning/quick/30-investigate-firefox-e2e-test-failures-an/FIREFOX-TEST-FAILURES.md</files>
  <action>
Create FIREFOX-TEST-FAILURES.md documenting the Firefox e2e test investigation results.

Structure the document with:

1. **Overview**: 223 total tests, 211 passed, 12 failed (5.4% failure rate). Tests run with `npx playwright test --project=firefox` from `/home/james/Code/SemPKM/e2e/`.

2. **Root Cause 1: `.object-face-edit.face-visible` selector timeout (9 tests)**
   - All 9 tests wait for `.object-face-edit.face-visible` after clicking the mode toggle button
   - The object read/edit view uses opacity crossfade (not 3D flip) — see MEMORY.md "Object Read/Edit Toggle — Crossfade"
   - In Firefox, the `.face-visible` class may not be applied or the selector may not match due to timing differences
   - List all 9 tests with file:line and test name
   - Suggested fix direction: Investigate whether the crossfade JS in workspace.js `toggleObjectMode()` correctly adds `.face-visible` class in Firefox, or whether tests need a different wait selector

   Tests:
   - edit-object-ui.spec.ts:150 — Cancel button text when entering edit mode
   - edit-object-ui.spec.ts:246 — multi-value reference field persist after save
   - edit-object-ui.spec.ts:319 — title change updates tab bar label after save
   - edit-object-ui.spec.ts:370 — title change updates object toolbar title after save
   - object-view-redesign.spec.ts:221 — shared collapse state carries to edit mode
   - object-view-redesign.spec.ts:274 — 3D flip to edit mode still works after redesign
   - helptext.spec.ts:52 — edit form has helptext toggle
   - helptext.spec.ts:68 — form-level helptext expands and collapses
   - helptext.spec.ts:94 — field-level helptext toggles
   - helptext.spec.ts:112 — helptext contains formatted markdown

3. **Root Cause 2: Strict mode `.markdown-body` resolves to multiple elements (1 test)**
   - object-view-redesign.spec.ts:66 — Markdown body visible immediately, properties collapsed
   - Playwright strict mode requires unique selector, but `.markdown-body` matches 8 elements in Firefox
   - Suggested fix: Scope the selector more narrowly (e.g., `.object-face-read .markdown-body` or use nth/first)

4. **Root Cause 3: Panel tab count mismatch (1 test)**
   - workspace-layout.spec.ts:84 — bottom panel exists with EVENT LOG, AI COPILOT tabs
   - Expected 2 tabs but found 4
   - Suggested fix: Investigate what extra tabs appear in Firefox; may be duplicate panel initialization

5. **Priority recommendation**: Root Cause 1 is highest priority (9/12 failures, single root cause). Fixing the crossfade toggle or test selectors would resolve 75% of Firefox failures.
  </action>
  <verify>
    <automated>test -f /home/james/Code/SemPKM/.planning/quick/30-investigate-firefox-e2e-test-failures-an/FIREFOX-TEST-FAILURES.md && wc -l /home/james/Code/SemPKM/.planning/quick/30-investigate-firefox-e2e-test-failures-an/FIREFOX-TEST-FAILURES.md | awk '{if ($1 >= 60) print "OK"; else print "FAIL: too short"}'</automated>
  </verify>
  <done>FIREFOX-TEST-FAILURES.md exists with all 12 tests documented, grouped by 3 root causes, with fix guidance</done>
</task>

</tasks>

<verification>
- Document exists at expected path
- All 12 failing tests are listed
- 3 root causes are identified and explained
- Fix suggestions are actionable
</verification>

<success_criteria>
- FIREFOX-TEST-FAILURES.md created with complete failure analysis
- Statistics match: 211/223 pass, 12 fail
- Each failure has file:line, test name, root cause, and fix direction
</success_criteria>

<output>
After completion, create `.planning/quick/30-investigate-firefox-e2e-test-failures-an/30-SUMMARY.md`
</output>
