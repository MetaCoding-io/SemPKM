---
phase: quick-8
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/guide/images/  # new directory with 20 copied PNGs
  - docs/guide/04-workspace-interface.md
  - docs/guide/05-working-with-objects.md
  - docs/guide/07-browsing-and-visualizing.md
  - docs/guide/08-keyboard-shortcuts.md
  - docs/guide/09-understanding-mental-models.md
  - docs/guide/10-managing-mental-models.md
  - docs/guide/11-user-management.md
  - docs/guide/12-webhooks.md
  - docs/guide/13-settings.md
autonomous: true
requirements: [QUICK-8]

must_haves:
  truths:
    - "Every guide chapter that has a relevant screenshot includes at least one inline image"
    - "All 20 light-mode (+ 2 dark-only) screenshots are present in docs/guide/images/"
    - "Image paths in markdown resolve correctly relative to each guide file"
    - "No dark-mode variants are copied (except 11-dark-mode and 12-dark-mode-graph which are dark-only)"
  artifacts:
    - path: "docs/guide/images/"
      provides: "Directory of screenshots for the user guide"
    - path: "docs/guide/04-workspace-interface.md"
      provides: "Images for workspace overview, multiple tabs, bottom panel, command palette"
    - path: "docs/guide/05-working-with-objects.md"
      provides: "Images for object read, edit, type picker, create form, lint panel"
    - path: "docs/guide/07-browsing-and-visualizing.md"
      provides: "Images for table, card, and graph views"
    - path: "docs/guide/13-settings.md"
      provides: "Images for settings page, dark mode screenshots"
  key_links:
    - from: "docs/guide/*.md"
      to: "docs/guide/images/*.png"
      via: "relative markdown image syntax ![alt](images/filename.png)"
      pattern: "!\\[.*\\]\\(images/.*\\.png\\)"
---

<objective>
Copy e2e screenshots into the user guide images directory and insert markdown image references into each relevant guide chapter at contextually appropriate locations.

Purpose: The user guide chapters have prose content with HTML comment placeholders indicating where screenshots should go, but no actual images are referenced. The e2e test suite generates high-quality screenshots of every major UI feature. Connecting these gives users visual context for every chapter.

Output: 20 PNG files in `docs/guide/images/`, 9 guide chapters updated with inline image references.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@e2e/screenshots/README.md
@docs/guide/04-workspace-interface.md
@docs/guide/05-working-with-objects.md
@docs/guide/07-browsing-and-visualizing.md
@docs/guide/08-keyboard-shortcuts.md
@docs/guide/09-understanding-mental-models.md
@docs/guide/10-managing-mental-models.md
@docs/guide/11-user-management.md
@docs/guide/12-webhooks.md
@docs/guide/13-settings.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Copy screenshots to docs/guide/images/</name>
  <files>docs/guide/images/</files>
  <action>
Create directory `docs/guide/images/` and copy all light-mode screenshots from `e2e/screenshots/` into it. Also copy the two dark-only screenshots (11-dark-mode.png and 12-dark-mode-graph.png). Do NOT copy any `-dark` variant files (those ending in `-dark.png`).

Files to copy (20 total):
- 01-workspace-overview.png
- 02-object-read-project.png
- 03-object-edit-form.png
- 04-type-picker.png
- 05-create-note-form.png
- 06-table-view.png
- 07-cards-view.png
- 08-graph-view.png
- 09-command-palette.png
- 10-settings-page.png
- 11-dark-mode.png (dark-only, no light variant)
- 12-dark-mode-graph.png (dark-only, no light variant)
- 13-admin-models.png
- 14-admin-webhooks.png
- 15-multiple-tabs.png
- 16-lint-panel.png
- 17-object-read-person.png
- 18-object-read-concept.png
- 19-login-page.png
- 20-bottom-panel.png

Use: `mkdir -p docs/guide/images && cp e2e/screenshots/{list}.png docs/guide/images/`
  </action>
  <verify>ls docs/guide/images/*.png | wc -l returns 20</verify>
  <done>20 PNG files exist in docs/guide/images/, no dark variants copied</done>
</task>

<task type="auto">
  <name>Task 2: Insert image references into guide chapters</name>
  <files>
    docs/guide/04-workspace-interface.md
    docs/guide/05-working-with-objects.md
    docs/guide/07-browsing-and-visualizing.md
    docs/guide/08-keyboard-shortcuts.md
    docs/guide/09-understanding-mental-models.md
    docs/guide/10-managing-mental-models.md
    docs/guide/11-user-management.md
    docs/guide/12-webhooks.md
    docs/guide/13-settings.md
  </files>
  <action>
Read each guide chapter and replace the existing HTML comment placeholders (`<!-- Screenshot: ... -->`) with markdown image references. Where no placeholder exists but a screenshot is relevant, insert the image reference at the contextually appropriate location (after the relevant heading or introductory paragraph).

Use the format: `![Descriptive alt text](images/filename.png)`

Specific insertions per chapter:

**04-workspace-interface.md:**
- Line 7 (after intro paragraph): Replace `<!-- Screenshot: full workspace... -->` with `![Full workspace showing sidebar, explorer tree, editor area, and details panel](images/01-workspace-overview.png)`
- After the "Editor Groups" subsection intro (~line 122-123 area, after "each with its own tab bar and content area"): Insert `![Multiple tabs open across editor groups](images/15-multiple-tabs.png)`
- Line 183 area: Replace `<!-- Screenshot: bottom panel... -->` with `![Bottom panel open showing Event Log tab](images/20-bottom-panel.png)`
- Line 215 area: Replace `<!-- Screenshot: command palette... -->` with `![Command palette overlay with searchable commands](images/09-command-palette.png)`

**05-working-with-objects.md:**
- Line 18 area: Replace `<!-- Screenshot: type picker... -->` with `![Type picker showing available object types as cards](images/04-type-picker.png)`
- Line 36 area: Replace `<!-- Screenshot: create form... -->` with `![Create form for a new Note with required Title field](images/05-create-note-form.png)`
- Line 74 area: Replace `<!-- Screenshot: a Note in read mode... -->` with `![Project object in read-only mode showing properties](images/02-object-read-project.png)`
- Line 125 area: Replace `<!-- Screenshot: an object in edit mode... -->` with `![Object edit form with SHACL-driven properties and markdown editor](images/03-object-edit-form.png)`
- Line 222 area: Replace `<!-- Screenshot: lint panel... -->` with `![Lint panel showing SHACL validation results](images/16-lint-panel.png)`
- After the "Reading an Object" section, add additional examples. Insert after the property table description (~line 95 area): `![Person object in read-only mode](images/17-object-read-person.png)` with a brief intro line like "Here is another example showing a Person object:"

**07-browsing-and-visualizing.md:**
- Line 39 area: Replace `<!-- Screenshot: Table View... -->` with `![Table view with sortable columns showing project data](images/06-table-view.png)`
- Line 88 area: Replace `<!-- Screenshot: Card View... -->` with `![Card view rendering objects as visual cards in a grid](images/07-cards-view.png)`
- Line 131 area: Replace `<!-- Screenshot: Graph View... -->` with `![Interactive graph visualization with typed and colored nodes](images/08-graph-view.png)`

**08-keyboard-shortcuts.md:**
- Line 43 area: Replace `<!-- Screenshot: Command palette... -->` with `![Command palette open with search results and keyboard shortcuts](images/09-command-palette.png)`

**09-understanding-mental-models.md:**
- After the "Basic PKM Mental Model" heading (~line 82 area), insert an image showing a Concept object as an example of mental model types: `![Concept object showing SKOS-based properties from the Basic PKM model](images/18-object-read-concept.png)`

**10-managing-mental-models.md:**
- Line 17 area: Replace `<!-- Screenshot: Admin Portal... -->` with `![Admin portal showing Mental Models management page](images/13-admin-models.png)`
- Line 29 area: Replace `<!-- Screenshot: Models management... -->` with (remove this placeholder since 13-admin-models already covers it, or keep as a second reference if contextually different)
- Line 65 area: Replace `<!-- Screenshot: Install Model form... -->` with (already covered by 13-admin-models screenshot above; remove the placeholder comment)

**11-user-management.md:**
- After the "Passwordless Design" section (~line 12 area, after describing the login flow), insert: `![Passwordless login page](images/19-login-page.png)`

**12-webhooks.md:**
- Line 84 area: Replace `<!-- Screenshot: Admin Portal... -->` with `![Admin portal webhooks configuration page](images/14-admin-webhooks.png)`
- Line 90 area: Replace `<!-- Screenshot: Webhook configuration... -->` with (remove duplicate placeholder -- 14-admin-webhooks already covers this)

**13-settings.md:**
- Line 14 area: Replace `<!-- Screenshot: Settings page... -->` with `![Settings page with category sidebar and settings controls](images/10-settings-page.png)`
- Line 87 area: Replace `<!-- Screenshot: A settings row... -->` with (no separate screenshot for this; remove the placeholder comment)
- After the "Three Theme Modes" table (~line 105 area), insert: `![Workspace in dark mode with object open](images/11-dark-mode.png)` and `![Graph view in dark mode](images/12-dark-mode-graph.png)` with a brief intro like "Here is how the workspace looks in dark mode:"

IMPORTANT: When replacing `<!-- Screenshot: ... -->` comments, delete the entire HTML comment line and insert the markdown image reference in its place. When a placeholder has no matching screenshot, simply delete the comment line.
  </action>
  <verify>grep -c '!\[' docs/guide/04-workspace-interface.md docs/guide/05-working-with-objects.md docs/guide/07-browsing-and-visualizing.md docs/guide/08-keyboard-shortcuts.md docs/guide/09-understanding-mental-models.md docs/guide/10-managing-mental-models.md docs/guide/11-user-management.md docs/guide/12-webhooks.md docs/guide/13-settings.md — should show at least 1 image per file, and grep -c 'Screenshot:' across all files should return 0 (all placeholders replaced or removed)</verify>
  <done>All 9 guide chapters contain image references, all HTML comment placeholders are removed, and all 20 screenshots are referenced at least once across the guide</done>
</task>

</tasks>

<verification>
1. `ls docs/guide/images/*.png | wc -l` returns 20
2. `grep -r '!\[' docs/guide/*.md | grep 'images/' | wc -l` returns >= 20 total image references
3. `grep -r '<!-- Screenshot:' docs/guide/*.md` returns no results (all placeholders replaced)
4. Each image path resolves: for any `images/XX.png` referenced, `ls docs/guide/images/XX.png` succeeds
</verification>

<success_criteria>
- 20 screenshots present in docs/guide/images/
- 9 guide chapters updated with contextual image references
- Zero HTML comment placeholders remaining in guide files
- All image paths use consistent relative format: images/filename.png
</success_criteria>

<output>
After completion, create `.planning/quick/8-review-e2e-screenshots-and-integrate-the/8-SUMMARY.md`
</output>
