---
phase: quick-27
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/templates/components/_sidebar.html
autonomous: true
requirements: [QUICK-27]

must_haves:
  truths:
    - "User popover shows a 'Clear & Reload' button"
    - "Clicking the button clears localStorage and reloads the page"
  artifacts:
    - path: "backend/app/templates/components/_sidebar.html"
      provides: "Clear & Reload button in user popover"
      contains: "localStorage.clear"
  key_links:
    - from: "backend/app/templates/components/_sidebar.html"
      to: "localStorage API + location.reload()"
      via: "onclick handler"
      pattern: "localStorage\\.clear.*location\\.reload"
---

<objective>
Add a "Clear & Reload" button to the user popover menu in the sidebar for quick localStorage debugging.

Purpose: Gives devs a one-click way to clear localStorage (panel positions, sidebar state, etc.) and reload, useful when layout or state gets corrupted.
Output: Updated _sidebar.html with new popover item.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/templates/components/_sidebar.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Clear and Reload button to user popover</name>
  <files>backend/app/templates/components/_sidebar.html</files>
  <action>
In the user popover (`#user-popover`), add a new button BEFORE the final `popover-divider` + logout section (i.e., between the theme row and the last divider, around line 159).

Add this markup:

```html
<button class="popover-item" onclick="localStorage.clear(); location.reload();">
    <i data-lucide="trash-2" class="popover-icon"></i>
    <span>Clear &amp; Reload</span>
</button>
```

Place it right after the closing `</div>` of `.popover-theme-row` (line 159) and before the `<div class="popover-divider"></div>` on line 160. This groups it visually with the other utility actions, separated from the danger-zone logout by the divider.

Do NOT add any CSS -- the existing `.popover-item` and `.popover-icon` classes already handle layout, sizing, hover states, and flex-shrink for icons.
  </action>
  <verify>
    <automated>grep -c "localStorage.clear" backend/app/templates/components/_sidebar.html | grep -q "1" && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>User popover contains a "Clear & Reload" button between the theme row and logout that calls localStorage.clear() then location.reload()</done>
</task>

</tasks>

<verification>
- Open the app, click user avatar in sidebar lower-left
- Popover shows "Clear & Reload" with trash icon between theme buttons and logout
- Clicking it clears localStorage and reloads the page
</verification>

<success_criteria>
- Button visible in user popover with correct label and icon
- onclick handler calls localStorage.clear() then location.reload()
- Existing popover items unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/27-add-clear-and-reload-button-to-user-menu/27-SUMMARY.md`
</output>
