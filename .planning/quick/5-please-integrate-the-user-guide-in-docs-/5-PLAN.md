---
phase: quick-5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/guide/index.html
  - docs/index.html
autonomous: true
requirements: [QUICK-5]

must_haves:
  truths:
    - "docs/index.html nav bar has a User Guide link"
    - "docs/guide/index.html exists and lists all 26 guide files in sections"
    - "Each chapter link opens the corresponding markdown file"
    - "Guide index page matches the marketing site design (dark theme, same CSS variables)"
  artifacts:
    - path: "docs/guide/index.html"
      provides: "Standalone guide index page with full chapter listing"
      contains: "appendix"
    - path: "docs/index.html"
      provides: "Nav link to guide/index.html"
      contains: "guide/index.html"
  key_links:
    - from: "docs/index.html nav"
      to: "docs/guide/index.html"
      via: "href"
      pattern: "guide/index.html"
    - from: "docs/guide/index.html chapters"
      to: "docs/guide/*.md"
      via: "href"
      pattern: "\\.md"
---

<objective>
Integrate the user guide (docs/guide/*.md, 26 files) into the marketing website (docs/index.html) by:
1. Creating docs/guide/index.html — a styled guide hub listing all chapters and appendices
2. Adding a "User Guide" nav link in docs/index.html pointing to the guide hub

Purpose: Users landing on the marketing site can navigate directly to the user guide. The guide hub gives a clean entry point to all 26 documentation files.
Output: docs/guide/index.html (new), docs/index.html (nav + footer updated)
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
  <name>Task 1: Create docs/guide/index.html — guide hub page</name>
  <files>docs/guide/index.html</files>
  <action>
Create a standalone HTML page at docs/guide/index.html that:

1. Reuses the exact same CSS design tokens and visual language from docs/index.html (dark theme: --bg-primary: #0a0a0f, --bg-secondary: #12121a, --bg-card: #16161f, --border-subtle: #1e1e2e, --accent-gradient: linear-gradient(135deg, #e8772e, #f59e0b), same font stack). Copy only the relevant CSS (nav, footer, container, section, section-label, section-title, btn styles) — do NOT copy the hero canvas animation or carousel.

2. Include a nav bar matching docs/index.html: logo "Sem<span>PKM</span>", links: Features (../index.html#features), Screenshots (../index.html#screenshots), Deploy (../index.html#deploy), Get Started (../index.html#signup), and a highlighted "User Guide" active link (current page).

3. A hero/header section (no canvas animation) with:
   - Section label: "Documentation"
   - H1: "SemPKM User Guide"
   - Subtitle: "Complete documentation covering setup, workspace, Mental Models, administration, advanced topics, and deployment."

4. Guide content in a single section with a two-column grid (1 col on mobile) of chapter groups. Use the Part structure from docs/guide/README.md:

   Part I: Introduction and Getting Started
   - 1. What is SemPKM? → 01-what-is-sempkm.md
   - 2. Core Concepts → 02-core-concepts.md
   - 3. Installation and Setup → 03-installation-and-setup.md

   Part II: Using the Workspace
   - 4. The Workspace Interface → 04-workspace-interface.md
   - 5. Working with Objects → 05-working-with-objects.md
   - 6. Edges and Relationships → 06-edges-and-relationships.md
   - 7. Browsing and Visualizing Data → 07-browsing-and-visualizing.md
   - 8. Keyboard Shortcuts and Command Palette → 08-keyboard-shortcuts.md

   Part III: Mental Models
   - 9. Understanding Mental Models → 09-understanding-mental-models.md
   - 10. Managing Mental Models → 10-managing-mental-models.md

   Part IV: Administration
   - 11. User Management → 11-user-management.md
   - 12. Webhooks → 12-webhooks.md
   - 13. Settings → 13-settings.md
   - 14. System Health and Debugging → 14-system-health-and-debugging.md

   Part V: The Event Log
   - 15. Understanding the Event Log → 15-event-log.md

   Part VI: Advanced Topics
   - 16. The Data Model → 16-data-model.md
   - 17. The Command API → 17-command-api.md
   - 18. The SPARQL Endpoint → 18-sparql-endpoint.md
   - 19. Creating Mental Models → 19-creating-mental-models.md

   Part VII: Deployment and Operations
   - 20. Production Deployment → 20-production-deployment.md

   Appendices (separate group at bottom)
   - A. Environment Variable Reference → appendix-a-environment-variables.md
   - B. Keyboard Shortcut Reference → appendix-b-keyboard-shortcuts.md
   - C. Command API Reference → appendix-c-command-api-reference.md
   - D. Glossary → appendix-d-glossary.md
   - E. Troubleshooting → appendix-e-troubleshooting.md
   - F. FAQ → appendix-f-faq.md

   Each Part is a card (bg-card, border-subtle, border-radius var(--radius)) with:
   - Part label in accent color (section-label style)
   - Part title in text-primary
   - Chapter list as styled anchor links (full width, padding 0.5rem 0.75rem, hover bg-card-hover)

5. Footer matching docs/index.html: copyright line, links to GitHub, back to docs (../index.html).

6. All links to .md files are relative (e.g., href="01-what-is-sempkm.md"). On GitHub Pages, .md files render natively. No JavaScript needed.

7. Include IntersectionObserver fade-in script (same as docs/index.html) and mobile nav toggle script.
  </action>
  <verify>Open docs/guide/index.html in a browser (file:// or via python -m http.server). All 20 chapters and 6 appendices are listed. Chapter links resolve to .md files. Page is dark-themed and visually consistent with docs/index.html.</verify>
  <done>docs/guide/index.html exists, lists all 26 guide files in Parts I-VII + Appendices, uses same dark theme as marketing site.</done>
</task>

<task type="auto">
  <name>Task 2: Add User Guide link to docs/index.html nav and footer</name>
  <files>docs/index.html</files>
  <action>
Make two targeted edits to docs/index.html:

1. Nav bar (around line 779-783): Add "User Guide" link to the nav-links ul, before the "Get Started" CTA:
   ```html
   <li><a href="guide/index.html">User Guide</a></li>
   ```
   Insert after the Deploy link and before the signup CTA.

2. Footer links (around line 1422-1426): Add "User Guide" to the footer-links ul:
   ```html
   <li><a href="guide/index.html">User Guide</a></li>
   ```
   Insert before the existing footer links.

No other changes to docs/index.html. Do not touch the CSS, hero, sections, or scripts.
  </action>
  <verify>grep -c "guide/index.html" docs/index.html returns 2 (nav + footer).</verify>
  <done>docs/index.html nav and footer both contain href="guide/index.html". Clicking the link in a browser opens the guide hub page.</done>
</task>

</tasks>

<verification>
- docs/guide/index.html exists and contains all 26 chapter/appendix links
- grep -c "guide/index.html" /home/james/Code/SemPKM/docs/index.html returns 2
- grep "appendix" /home/james/Code/SemPKM/docs/guide/index.html returns 6 appendix links
</verification>

<success_criteria>
From docs/index.html, a visitor can click "User Guide" in the nav, land on docs/guide/index.html which shows all 7 Parts and 6 Appendices, and click any chapter to open that markdown file. The guide hub page is visually consistent with the marketing site (same dark theme, same design tokens).
</success_criteria>

<output>
After completion, create .planning/quick/5-please-integrate-the-user-guide-in-docs-/5-SUMMARY.md
</output>
