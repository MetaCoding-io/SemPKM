---
phase: quick-31
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/static/js/workspace.js
  - e2e/tests/03-navigation/workspace-layout.spec.ts
  - e2e/tests/01-objects/object-view-redesign.spec.ts
autonomous: true
requirements: [FF-01, FF-02, FF-03]

must_haves:
  truths:
    - "toggleObjectMode adds .face-visible to the active face and .face-hidden to the inactive face"
    - "Bottom panel tab count test expects 4 tabs (EVENT LOG, INFERENCE, AI COPILOT, LINT)"
    - "Markdown body selector is scoped to the active object face, not global"
    - "All 12 previously-failing Firefox e2e tests pass"
  artifacts:
    - path: "frontend/static/js/workspace.js"
      provides: "face-visible/face-hidden class toggling in toggleObjectMode"
      contains: "face-visible"
    - path: "e2e/tests/03-navigation/workspace-layout.spec.ts"
      provides: "Corrected panel tab count expectation"
      contains: "toHaveCount(4)"
    - path: "e2e/tests/01-objects/object-view-redesign.spec.ts"
      provides: "Scoped .markdown-body selector"
      contains: ".object-face-read .markdown-body"
  key_links:
    - from: "frontend/static/js/workspace.js"
      to: "e2e/tests/01-objects/edit-object-ui.spec.ts"
      via: ".face-visible class applied during crossfade toggle"
      pattern: "face-visible"
---

<objective>
Fix 12 Firefox e2e test failures caused by 3 root causes identified in quick task 30.

Purpose: Bring Firefox e2e test suite to full parity with Chromium (0 failures).
Output: 3 modified files, all 223 Firefox tests passing.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/30-investigate-firefox-e2e-test-failures-an/FIREFOX-TEST-FAILURES.md
@frontend/static/js/workspace.js
@e2e/tests/03-navigation/workspace-layout.spec.ts
@e2e/tests/01-objects/object-view-redesign.spec.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add face-visible/face-hidden class toggling to toggleObjectMode</name>
  <files>frontend/static/js/workspace.js</files>
  <action>
In the `toggleObjectMode()` function (line 542), add `.face-visible` and `.face-hidden` class toggling to both branches of the flip:

**When switching from edit to read (isFlipped=true branch, around line 563):**
After `flipInner.classList.remove('flipped');`, add:
```javascript
if (readFace) { readFace.classList.remove('face-hidden'); readFace.classList.add('face-visible'); }
if (editFace) { editFace.classList.remove('face-visible'); editFace.classList.add('face-hidden'); }
```

**When switching from read to edit (else branch, around line 599):**
After `flipInner.classList.add('flipped');`, add:
```javascript
if (editFace) { editFace.classList.remove('face-hidden'); editFace.classList.add('face-visible'); }
if (readFace) { readFace.classList.remove('face-visible'); readFace.classList.add('face-hidden'); }
```

This makes the crossfade toggle apply the same CSS class markers that the old 3D flip used, satisfying selectors like `.object-face-edit.face-visible` and `.object-face-read:not(.face-hidden)` used in 10 e2e tests.

Do NOT change anything else in this function. The crossfade animation via `.flipped` class continues to work as before -- these classes are additive markers.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && grep -c 'face-visible' frontend/static/js/workspace.js</automated>
  </verify>
  <done>toggleObjectMode adds face-visible to active face and face-hidden to inactive face in both read-to-edit and edit-to-read transitions. grep shows at least 4 occurrences of face-visible in workspace.js.</done>
</task>

<task type="auto">
  <name>Task 2: Fix panel tab count and markdown-body selector in e2e tests</name>
  <files>e2e/tests/03-navigation/workspace-layout.spec.ts, e2e/tests/01-objects/object-view-redesign.spec.ts</files>
  <action>
**workspace-layout.spec.ts line 89:** Change the panel tab count from 2 to 4 and add the missing tab text assertions. The bottom panel has 4 tabs: EVENT LOG, INFERENCE, AI COPILOT, LINT (confirmed from workspace.html template).

Replace:
```typescript
    await expect(panelTabBar.locator('.panel-tab')).toHaveCount(2);
    await expect(panelTabBar).toContainText('EVENT LOG');
    await expect(panelTabBar).toContainText('AI COPILOT');
```

With:
```typescript
    await expect(panelTabBar.locator('.panel-tab')).toHaveCount(4);
    await expect(panelTabBar).toContainText('EVENT LOG');
    await expect(panelTabBar).toContainText('INFERENCE');
    await expect(panelTabBar).toContainText('AI COPILOT');
    await expect(panelTabBar).toContainText('LINT');
```

**object-view-redesign.spec.ts line 76:** Scope the `.markdown-body` selector to the active object face to avoid Playwright strict mode error when multiple `.markdown-body` elements exist.

Replace:
```typescript
    const body = ownerPage.locator('.markdown-body');
```

With:
```typescript
    const body = ownerPage.locator('.object-face-read .markdown-body').first();
```

This scopes to the read face of the active object, avoiding the strict mode "resolves to 8 elements" error.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && grep -n 'toHaveCount(4)' e2e/tests/03-navigation/workspace-layout.spec.ts && grep -n 'object-face-read .markdown-body' e2e/tests/01-objects/object-view-redesign.spec.ts</automated>
  </verify>
  <done>Panel tab test expects 4 tabs and checks for all 4 tab names. Markdown body selector scoped to .object-face-read container.</done>
</task>

<task type="auto">
  <name>Task 3: Run Firefox e2e tests to verify all 12 failures are resolved</name>
  <files></files>
  <action>
Run the full Firefox e2e test suite from the e2e directory:

```bash
cd /home/james/Code/SemPKM/e2e && npx playwright test --project=firefox
```

Verify that:
1. All 223 tests pass (or the only failures are the 5 known setup-wizard tests from 00-setup which require a fresh Docker stack)
2. Specifically confirm no failures in:
   - tests/01-objects/edit-object-ui.spec.ts (was 4 failures)
   - tests/01-objects/object-view-redesign.spec.ts (was 3 failures)
   - tests/11-helptext/helptext.spec.ts (was 4 failures)
   - tests/03-navigation/workspace-layout.spec.ts (was 1 failure)

If any test still fails, diagnose and fix before completing this task.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM/e2e && npx playwright test --project=firefox 2>&1 | tail -20</automated>
  </verify>
  <done>Firefox e2e suite shows 0 failures (excluding the 5 known setup-wizard tests). All 12 previously-failing tests now pass.</done>
</task>

</tasks>

<verification>
- `grep -c 'face-visible' frontend/static/js/workspace.js` returns >= 4
- `grep 'toHaveCount(4)' e2e/tests/03-navigation/workspace-layout.spec.ts` matches
- `grep 'object-face-read .markdown-body' e2e/tests/01-objects/object-view-redesign.spec.ts` matches
- Firefox e2e test run shows all 12 previously-failing tests now pass
</verification>

<success_criteria>
- toggleObjectMode() applies face-visible/face-hidden classes during crossfade toggle
- workspace-layout.spec.ts expects 4 bottom panel tabs (EVENT LOG, INFERENCE, AI COPILOT, LINT)
- object-view-redesign.spec.ts uses scoped .markdown-body selector
- Full Firefox e2e suite passes (excluding known setup-wizard tests)
</success_criteria>

<output>
After completion, create `.planning/quick/31-fix-firefox-e2e-failures-add-face-visibl/31-SUMMARY.md`
</output>
