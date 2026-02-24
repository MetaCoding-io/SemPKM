---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: [docs/index.html]
autonomous: true
requirements: []
must_haves:
  truths:
    - "Copyright notice displays in docs site footer"
    - "Notice includes 'Copyright MetaCoding Solutions, LLC 2016'"
    - "Copyright symbol (©) is properly rendered"
  artifacts:
    - path: "docs/index.html"
      provides: "Updated footer with copyright notice"
      contains: "Copyright MetaCoding Solutions, LLC 2016"
  key_links:
    - from: "docs/index.html footer"
      to: "copyright display"
      via: "footer-left div"
      pattern: "footer-left.*Copyright"
---

<objective>
Add copyright notice to the docs site footer.

Purpose: Establish legal ownership attribution on the public-facing documentation.
Output: Updated docs/index.html with proper copyright notice.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
Project: SemPKM — Semantics-Native Personal Knowledge Management
Current state: docs/index.html exists with footer element requiring copyright update
Target: Add "Copyright MetaCoding Solutions, LLC 2016" with proper copyright symbol
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update footer copyright notice in docs/index.html</name>
  <files>docs/index.html</files>
  <action>
Update the footer copyright line at line 1421 in docs/index.html.

Current: `<div class="footer-left">&copy; 2026 SemPKM. All rights reserved.</div>`

Replace with: `<div class="footer-left">&copy; Copyright MetaCoding Solutions, LLC 2016. All rights reserved.</div>`

The &copy; HTML entity will render the proper copyright symbol (©). Update only the copyright text in the footer-left div, preserve all other footer structure and styling.
  </action>
  <verify>
grep -n "Copyright MetaCoding Solutions" /home/james/Code/SemPKM/docs/index.html
</verify>
  <done>
Footer displays "© Copyright MetaCoding Solutions, LLC 2016. All rights reserved." with proper copyright symbol and company attribution.
  </done>
</task>

</tasks>

<verification>
After completion:
1. Verify grep finds the copyright text in docs/index.html
2. Confirm the HTML entity &copy; is present (will render as © symbol)
3. Visual inspection: footer displays proper copyright in browser
</verification>

<success_criteria>
- [ ] docs/index.html footer line contains "Copyright MetaCoding Solutions, LLC 2016"
- [ ] Copyright symbol (©) renders properly via &copy; entity
- [ ] All footer structure and other content preserved
- [ ] File committed to git
</success_criteria>

<output>
After completion, create `.planning/quick/1-add-copyright-notice-to-docs-site/1-SUMMARY.md` documenting the copyright notice update.
</output>
