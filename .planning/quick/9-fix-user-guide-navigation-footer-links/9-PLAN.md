---
phase: quick-9
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/guide/README.md
  - docs/guide/01-what-is-sempkm.md
  - docs/guide/02-core-concepts.md
  - docs/guide/03-installation-and-setup.md
  - docs/guide/04-workspace-interface.md
  - docs/guide/05-working-with-objects.md
  - docs/guide/06-edges-and-relationships.md
  - docs/guide/07-browsing-and-visualizing.md
  - docs/guide/08-keyboard-shortcuts.md
  - docs/guide/09-understanding-mental-models.md
  - docs/guide/10-managing-mental-models.md
  - docs/guide/11-user-management.md
  - docs/guide/12-webhooks.md
  - docs/guide/13-settings.md
  - docs/guide/14-system-health-and-debugging.md
  - docs/guide/15-event-log.md
  - docs/guide/16-data-model.md
  - docs/guide/17-command-api.md
  - docs/guide/18-sparql-endpoint.md
  - docs/guide/19-creating-mental-models.md
  - docs/guide/20-production-deployment.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/appendix-b-keyboard-shortcuts.md
  - docs/guide/appendix-c-command-api-reference.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-e-troubleshooting.md
  - docs/guide/appendix-f-faq.md
autonomous: true
requirements: [QUICK-9]

must_haves:
  truths:
    - "Every guide page has a consistent navigation footer"
    - "Previous/Next links match the canonical page order from README.md table of contents"
    - "First page (README.md) has only Next link, last page (appendix-f-faq.md) has only Previous link"
    - "All interior pages have both Previous and Next links"
  artifacts:
    - path: "docs/guide/README.md"
      provides: "Footer with Next link only"
    - path: "docs/guide/appendix-f-faq.md"
      provides: "Footer with Previous link only"
  key_links:
    - from: "each page's Previous link"
      to: "the preceding page in canonical order"
      via: "relative markdown link"
    - from: "each page's Next link"
      to: "the following page in canonical order"
      via: "relative markdown link"
---

<objective>
Standardize navigation footer links across all 27 user guide pages so every page has consistent "Previous:" and "Next:" links matching the canonical order defined in README.md.

Purpose: Currently the guide pages have inconsistent footers -- some have "Next:" with prose paragraphs, some have informal link lists, some have "See Also" sections, and some have "What is Next" sections with different formatting. This makes navigation unreliable. Standardize to a clean, consistent format.

Output: All 27 guide markdown files updated with standardized navigation footers.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

The canonical page order (from README.md table of contents) is:

| # | File | Title |
|---|------|-------|
| 1 | README.md | SemPKM User Guide |
| 2 | 01-what-is-sempkm.md | Chapter 1: What is SemPKM? |
| 3 | 02-core-concepts.md | Chapter 2: Core Concepts |
| 4 | 03-installation-and-setup.md | Chapter 3: Installation and Setup |
| 5 | 04-workspace-interface.md | Chapter 4: The Workspace Interface |
| 6 | 05-working-with-objects.md | Chapter 5: Working with Objects |
| 7 | 06-edges-and-relationships.md | Chapter 6: Edges and Relationships |
| 8 | 07-browsing-and-visualizing.md | Chapter 7: Browsing and Visualizing Data |
| 9 | 08-keyboard-shortcuts.md | Chapter 8: Keyboard Shortcuts and Command Palette |
| 10 | 09-understanding-mental-models.md | Chapter 9: Understanding Mental Models |
| 11 | 10-managing-mental-models.md | Chapter 10: Managing Mental Models |
| 12 | 11-user-management.md | Chapter 11: User Management |
| 13 | 12-webhooks.md | Chapter 12: Webhooks |
| 14 | 13-settings.md | Chapter 13: Settings |
| 15 | 14-system-health-and-debugging.md | Chapter 14: System Health and Debugging |
| 16 | 15-event-log.md | Chapter 15: Understanding the Event Log |
| 17 | 16-data-model.md | Chapter 16: The Data Model |
| 18 | 17-command-api.md | Chapter 17: The Command API |
| 19 | 18-sparql-endpoint.md | Chapter 18: The SPARQL Endpoint |
| 20 | 19-creating-mental-models.md | Chapter 19: Creating Mental Models |
| 21 | 20-production-deployment.md | Chapter 20: Production Deployment |
| 22 | appendix-a-environment-variables.md | Appendix A: Environment Variable Reference |
| 23 | appendix-b-keyboard-shortcuts.md | Appendix B: Keyboard Shortcut Reference |
| 24 | appendix-c-command-api-reference.md | Appendix C: Command API Reference |
| 25 | appendix-d-glossary.md | Appendix D: Glossary |
| 26 | appendix-e-troubleshooting.md | Appendix E: Troubleshooting |
| 27 | appendix-f-faq.md | Appendix F: FAQ |
</context>

<tasks>

<task type="auto">
  <name>Task 1: Standardize navigation footers on all 27 guide pages</name>
  <files>
    docs/guide/README.md
    docs/guide/01-what-is-sempkm.md
    docs/guide/02-core-concepts.md
    docs/guide/03-installation-and-setup.md
    docs/guide/04-workspace-interface.md
    docs/guide/05-working-with-objects.md
    docs/guide/06-edges-and-relationships.md
    docs/guide/07-browsing-and-visualizing.md
    docs/guide/08-keyboard-shortcuts.md
    docs/guide/09-understanding-mental-models.md
    docs/guide/10-managing-mental-models.md
    docs/guide/11-user-management.md
    docs/guide/12-webhooks.md
    docs/guide/13-settings.md
    docs/guide/14-system-health-and-debugging.md
    docs/guide/15-event-log.md
    docs/guide/16-data-model.md
    docs/guide/17-command-api.md
    docs/guide/18-sparql-endpoint.md
    docs/guide/19-creating-mental-models.md
    docs/guide/20-production-deployment.md
    docs/guide/appendix-a-environment-variables.md
    docs/guide/appendix-b-keyboard-shortcuts.md
    docs/guide/appendix-c-command-api-reference.md
    docs/guide/appendix-d-glossary.md
    docs/guide/appendix-e-troubleshooting.md
    docs/guide/appendix-f-faq.md
  </files>
  <action>
For each of the 27 guide pages, replace the existing navigation footer with a standardized format. The footer should appear at the very end of the file, separated by `---`.

**Standard footer format (interior pages with both Previous and Next):**

```markdown
---

**Previous:** [Chapter 4: The Workspace Interface](04-workspace-interface.md) | **Next:** [Chapter 6: Edges and Relationships](06-edges-and-relationships.md)
```

**First page format (README.md -- Next only):**

```markdown
---

**Next:** [Chapter 1: What is SemPKM?](01-what-is-sempkm.md)
```

**Last page format (appendix-f-faq.md -- Previous only):**

```markdown
---

**Previous:** [Appendix E: Troubleshooting](appendix-e-troubleshooting.md)
```

**What to remove/replace on each page:**

The existing footers are inconsistent. Each page currently ends with one of these patterns that must be replaced:

1. **"What is Next" section** (chapters 01, 02, 03, 07, 08, 09, 11, 12, 13, 14, 19, 20): Has a `## What is Next` or `## What is Next` heading followed by a prose paragraph and a bare link. Remove the entire "What is Next" section (heading, paragraph, and link) and replace with the standardized footer.

2. **"Next Steps" section** (chapters 15, 16, 17): Has a `## Next Steps` heading followed by a paragraph and link. Remove and replace.

3. **Inline "Next:" line** (chapters 04, 05, 06): Has `---` then `**Next:** [Title](link)` at the bottom. Keep the `---` separator, replace the Next line with the full Previous + Next footer.

4. **"See Also" section** (appendices a, b, c, d, e): Has a `## See Also` heading with a bullet list of related links. KEEP the "See Also" section intact. Add the navigation footer AFTER the See Also section.

5. **Bare link list at bottom** (chapter 10): Has informal bullet list of links. Remove and replace with standardized footer.

6. **Closing paragraph with link** (chapter 18): Has a closing paragraph with inline link. Remove that closing paragraph and replace with standardized footer.

7. **README.md**: Currently ends with the appendix links list. Add the navigation footer after the last appendix link.

**The complete mapping of Previous/Next for each page:**

| Page | Previous | Next |
|------|----------|------|
| README.md | (none) | [Chapter 1: What is SemPKM?](01-what-is-sempkm.md) |
| 01-what-is-sempkm.md | [SemPKM User Guide](README.md) | [Chapter 2: Core Concepts](02-core-concepts.md) |
| 02-core-concepts.md | [Chapter 1: What is SemPKM?](01-what-is-sempkm.md) | [Chapter 3: Installation and Setup](03-installation-and-setup.md) |
| 03-installation-and-setup.md | [Chapter 2: Core Concepts](02-core-concepts.md) | [Chapter 4: The Workspace Interface](04-workspace-interface.md) |
| 04-workspace-interface.md | [Chapter 3: Installation and Setup](03-installation-and-setup.md) | [Chapter 5: Working with Objects](05-working-with-objects.md) |
| 05-working-with-objects.md | [Chapter 4: The Workspace Interface](04-workspace-interface.md) | [Chapter 6: Edges and Relationships](06-edges-and-relationships.md) |
| 06-edges-and-relationships.md | [Chapter 5: Working with Objects](05-working-with-objects.md) | [Chapter 7: Browsing and Visualizing Data](07-browsing-and-visualizing.md) |
| 07-browsing-and-visualizing.md | [Chapter 6: Edges and Relationships](06-edges-and-relationships.md) | [Chapter 8: Keyboard Shortcuts and Command Palette](08-keyboard-shortcuts.md) |
| 08-keyboard-shortcuts.md | [Chapter 7: Browsing and Visualizing Data](07-browsing-and-visualizing.md) | [Chapter 9: Understanding Mental Models](09-understanding-mental-models.md) |
| 09-understanding-mental-models.md | [Chapter 8: Keyboard Shortcuts and Command Palette](08-keyboard-shortcuts.md) | [Chapter 10: Managing Mental Models](10-managing-mental-models.md) |
| 10-managing-mental-models.md | [Chapter 9: Understanding Mental Models](09-understanding-mental-models.md) | [Chapter 11: User Management](11-user-management.md) |
| 11-user-management.md | [Chapter 10: Managing Mental Models](10-managing-mental-models.md) | [Chapter 12: Webhooks](12-webhooks.md) |
| 12-webhooks.md | [Chapter 11: User Management](11-user-management.md) | [Chapter 13: Settings](13-settings.md) |
| 13-settings.md | [Chapter 12: Webhooks](12-webhooks.md) | [Chapter 14: System Health and Debugging](14-system-health-and-debugging.md) |
| 14-system-health-and-debugging.md | [Chapter 13: Settings](13-settings.md) | [Chapter 15: Understanding the Event Log](15-event-log.md) |
| 15-event-log.md | [Chapter 14: System Health and Debugging](14-system-health-and-debugging.md) | [Chapter 16: The Data Model](16-data-model.md) |
| 16-data-model.md | [Chapter 15: Understanding the Event Log](15-event-log.md) | [Chapter 17: The Command API](17-command-api.md) |
| 17-command-api.md | [Chapter 16: The Data Model](16-data-model.md) | [Chapter 18: The SPARQL Endpoint](18-sparql-endpoint.md) |
| 18-sparql-endpoint.md | [Chapter 17: The Command API](17-command-api.md) | [Chapter 19: Creating Mental Models](19-creating-mental-models.md) |
| 19-creating-mental-models.md | [Chapter 18: The SPARQL Endpoint](18-sparql-endpoint.md) | [Chapter 20: Production Deployment](20-production-deployment.md) |
| 20-production-deployment.md | [Chapter 19: Creating Mental Models](19-creating-mental-models.md) | [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) |
| appendix-a-environment-variables.md | [Chapter 20: Production Deployment](20-production-deployment.md) | [Appendix B: Keyboard Shortcut Reference](appendix-b-keyboard-shortcuts.md) |
| appendix-b-keyboard-shortcuts.md | [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) | [Appendix C: Command API Reference](appendix-c-command-api-reference.md) |
| appendix-c-command-api-reference.md | [Appendix B: Keyboard Shortcut Reference](appendix-b-keyboard-shortcuts.md) | [Appendix D: Glossary](appendix-d-glossary.md) |
| appendix-d-glossary.md | [Appendix C: Command API Reference](appendix-c-command-api-reference.md) | [Appendix E: Troubleshooting](appendix-e-troubleshooting.md) |
| appendix-e-troubleshooting.md | [Appendix D: Glossary](appendix-d-glossary.md) | [Appendix F: FAQ](appendix-f-faq.md) |
| appendix-f-faq.md | [Appendix E: Troubleshooting](appendix-e-troubleshooting.md) | (none) |

**Important rules:**
- Keep ALL existing content (body text, headings, See Also sections on appendices) -- only modify the navigation footer area
- For appendices that have "## See Also" sections: KEEP the See Also section, add the nav footer AFTER it
- For chapters with "## What is Next" or "## Next Steps" sections: REMOVE the entire section (heading + all content under it) and replace with the nav footer
- For chapter 10 (Managing Mental Models): Remove the closing paragraph that starts "You now understand..." and the bullet list below it, replace with nav footer
- For chapter 18 (SPARQL Endpoint): Remove the closing paragraph starting "You now have the tools..." and replace with nav footer
- Ensure each file ends with a single trailing newline after the footer
- The `---` separator before the footer should be on its own line with blank lines before and after it
  </action>
  <verify>
Run a script to check every guide file has the expected footer pattern:
```bash
cd /home/james/Code/SemPKM && for f in docs/guide/README.md docs/guide/01-what-is-sempkm.md docs/guide/02-core-concepts.md docs/guide/03-installation-and-setup.md docs/guide/04-workspace-interface.md docs/guide/05-working-with-objects.md docs/guide/06-edges-and-relationships.md docs/guide/07-browsing-and-visualizing.md docs/guide/08-keyboard-shortcuts.md docs/guide/09-understanding-mental-models.md docs/guide/10-managing-mental-models.md docs/guide/11-user-management.md docs/guide/12-webhooks.md docs/guide/13-settings.md docs/guide/14-system-health-and-debugging.md docs/guide/15-event-log.md docs/guide/16-data-model.md docs/guide/17-command-api.md docs/guide/18-sparql-endpoint.md docs/guide/19-creating-mental-models.md docs/guide/20-production-deployment.md docs/guide/appendix-a-environment-variables.md docs/guide/appendix-b-keyboard-shortcuts.md docs/guide/appendix-c-command-api-reference.md docs/guide/appendix-d-glossary.md docs/guide/appendix-e-troubleshooting.md docs/guide/appendix-f-faq.md; do last=$(tail -2 "$f" | head -1); if echo "$last" | grep -qE '^\*\*Previous:\*\*|\*\*Next:\*\*'; then echo "OK: $(basename $f)"; else echo "FAIL: $(basename $f) -> $last"; fi; done
```
All 27 files should show "OK".
  </verify>
  <done>All 27 guide pages have consistent Previous/Next navigation footers. README.md has Next only, appendix-f-faq.md has Previous only, all others have both. No "What is Next", "Next Steps", or inconsistent link patterns remain.</done>
</task>

</tasks>

<verification>
1. Every guide page ends with a standardized `**Previous:** ... | **Next:** ...` footer (or just one direction for first/last pages)
2. The link chain is unbroken: following Next from README.md through every page reaches appendix-f-faq.md, and following Previous back reaches README.md
3. No orphaned "What is Next", "Next Steps", or informal closing link patterns remain
4. Appendix "See Also" sections are preserved intact above the nav footer
</verification>

<success_criteria>
- All 27 files have the standardized navigation footer as their last non-empty line
- Following the Next chain from README.md visits all 27 pages in order
- Following the Previous chain from appendix-f-faq.md visits all 27 pages in reverse order
- No duplicate navigation patterns (old + new) exist in any file
</success_criteria>

<output>
After completion, create `.planning/quick/9-fix-user-guide-navigation-footer-links/9-SUMMARY.md`
</output>
