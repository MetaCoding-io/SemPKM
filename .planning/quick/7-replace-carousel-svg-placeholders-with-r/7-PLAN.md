---
phase: quick-7
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/screenshots/01-workspace-overview-dark.png
  - docs/screenshots/08-graph-view-dark.png
  - docs/screenshots/12-dark-mode-graph.png
  - docs/screenshots/06-table-view-dark.png
  - docs/screenshots/03-object-edit-form-dark.png
  - docs/index.html
autonomous: true
requirements: [QUICK-7]

must_haves:
  truths:
    - "Carousel has 6 slides in the correct order"
    - "Slide 1 shows real workspace overview screenshot (not SVG)"
    - "Slide 2 is the existing Graph Visualization SVG unchanged"
    - "Slides 3 and 4 show real graph screenshots with multiple-layouts captions"
    - "Slide 5 shows real table view screenshot (not SVG)"
    - "Slide 6 shows real edit form screenshot (not SVG)"
    - "All img src paths resolve correctly from docs/index.html to docs/screenshots/"
  artifacts:
    - path: "docs/screenshots/01-workspace-overview-dark.png"
      provides: "Workspace overview screenshot for GitHub Pages"
    - path: "docs/screenshots/08-graph-view-dark.png"
      provides: "Graph view screenshot for GitHub Pages"
    - path: "docs/screenshots/12-dark-mode-graph.png"
      provides: "Dark mode graph screenshot for GitHub Pages"
    - path: "docs/screenshots/06-table-view-dark.png"
      provides: "Table view screenshot for GitHub Pages"
    - path: "docs/screenshots/03-object-edit-form-dark.png"
      provides: "Edit form screenshot for GitHub Pages"
    - path: "docs/index.html"
      provides: "Updated carousel with 6 slides"
  key_links:
    - from: "docs/index.html carousel slides"
      to: "docs/screenshots/*.png"
      via: "src='../screenshots/FILENAME.png'"
      pattern: "src=\"\\.\\./screenshots/"
---

<objective>
Replace 3 of the 4 carousel SVG placeholders with real screenshots and add 2 new graph slides, giving the carousel 6 total slides that showcase the actual application.

Purpose: The docs site currently shows hand-drawn SVG mockups. Real screenshots communicate the product far more convincingly.
Output: 5 PNG files copied to docs/screenshots/, and docs/index.html carousel updated from 4 SVG slides to 6 slides (1 SVG kept, 5 real images).
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
  <name>Task 1: Copy screenshots to docs/screenshots/</name>
  <files>
    docs/screenshots/01-workspace-overview-dark.png
    docs/screenshots/08-graph-view-dark.png
    docs/screenshots/12-dark-mode-graph.png
    docs/screenshots/06-table-view-dark.png
    docs/screenshots/03-object-edit-form-dark.png
  </files>
  <action>
    Create the docs/screenshots/ directory and copy the five required PNG files from e2e/screenshots/ into it:

    mkdir -p /home/james/Code/SemPKM/docs/screenshots
    cp /home/james/Code/SemPKM/e2e/screenshots/01-workspace-overview-dark.png /home/james/Code/SemPKM/docs/screenshots/
    cp /home/james/Code/SemPKM/e2e/screenshots/08-graph-view-dark.png /home/james/Code/SemPKM/docs/screenshots/
    cp /home/james/Code/SemPKM/e2e/screenshots/12-dark-mode-graph.png /home/james/Code/SemPKM/docs/screenshots/
    cp /home/james/Code/SemPKM/e2e/screenshots/06-table-view-dark.png /home/james/Code/SemPKM/docs/screenshots/
    cp /home/james/Code/SemPKM/e2e/screenshots/03-object-edit-form-dark.png /home/james/Code/SemPKM/docs/screenshots/

    Do not copy any other files. Do not modify e2e/screenshots/ in any way.
  </action>
  <verify>
    ls /home/james/Code/SemPKM/docs/screenshots/ — must list exactly these 5 files:
    01-workspace-overview-dark.png, 03-object-edit-form-dark.png, 06-table-view-dark.png, 08-graph-view-dark.png, 12-dark-mode-graph.png
  </verify>
  <done>All 5 PNGs exist in docs/screenshots/ with non-zero file sizes</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite carousel in docs/index.html to 6 slides</name>
  <files>docs/index.html</files>
  <action>
    Replace the entire carousel-track content (lines 946–1367 in docs/index.html — from the opening `<div class="carousel-track" id="carouselTrack">` comment block through the closing `</div>` before the carousel buttons) with 6 slides in this exact order:

    **Slide 1 — Object Browser (real screenshot, replaces SVG slide 1):**
    ```html
    <!-- Slide 1: Object Browser -->
    <div class="carousel-slide">
      <img src="../screenshots/01-workspace-overview-dark.png" alt="SemPKM workspace overview showing object browser with sidebar navigation, tabbed editor pane, and property inspector">
      <div class="carousel-caption">
        <h3>Object Browser</h3>
        <p>Inspect any object with its properties, relationships, and live SHACL validation status.</p>
      </div>
    </div>
    ```

    **Slide 2 — Graph Visualization (keep existing SVG exactly as-is):**
    Copy the entire existing slide 2 block verbatim from the source file (lines 1023–1239), including all SVG markup and the existing caption "Graph Visualization". Do not alter a single character of this slide.

    **Slide 3 — Graph View screenshot (new real image):**
    ```html
    <!-- Slide 3: Graph View -->
    <div class="carousel-slide">
      <img src="../screenshots/08-graph-view-dark.png" alt="SemPKM graph view showing knowledge graph with tree layout and node tooltips">
      <div class="carousel-caption">
        <h3>Graph View</h3>
        <p>Multiple graph layouts — tree, force-directed, and radial — for better usability across different graph shapes.</p>
      </div>
    </div>
    ```

    **Slide 4 — Dark Mode Graph screenshot (new real image):**
    ```html
    <!-- Slide 4: Dark Mode Graph -->
    <div class="carousel-slide">
      <img src="../screenshots/12-dark-mode-graph.png" alt="SemPKM graph visualization in dark mode showing force-directed layout">
      <div class="carousel-caption">
        <h3>Dark Mode Graph</h3>
        <p>Switch between layouts to best fit your data — tree hierarchies, force clusters, or radial expansions.</p>
      </div>
    </div>
    ```

    **Slide 5 — SPARQL-Powered Tables (real screenshot, replaces SVG slide 3):**
    ```html
    <!-- Slide 5: SPARQL-Powered Tables -->
    <div class="carousel-slide">
      <img src="../screenshots/06-table-view-dark.png" alt="SemPKM table view showing SPARQL query results as a sortable filterable table">
      <div class="carousel-caption">
        <h3>SPARQL-Powered Tables</h3>
        <p>Write SPARQL queries and see results as sortable, filterable tables with live data from your graph.</p>
      </div>
    </div>
    ```

    **Slide 6 — SHACL-Driven Forms (real screenshot, replaces SVG slide 4):**
    ```html
    <!-- Slide 6: SHACL-Driven Forms -->
    <div class="carousel-slide">
      <img src="../screenshots/03-object-edit-form-dark.png" alt="SemPKM SHACL-driven edit form with auto-generated fields and real-time validation">
      <div class="carousel-caption">
        <h3>SHACL-Driven Forms</h3>
        <p>Forms auto-generated from SHACL shapes with real-time validation, type pickers, and constraint hints.</p>
      </div>
    </div>
    ```

    The img src paths must be `../screenshots/FILENAME.png` (relative — docs/index.html is inside docs/, screenshots are in docs/screenshots/).
    The carousel buttons and dots div after the track remain untouched.
    No changes to CSS or JavaScript.
  </action>
  <verify>
    grep -c 'carousel-slide' /home/james/Code/SemPKM/docs/index.html
    — must output 6 (one opening div per slide)

    grep 'src="../screenshots/' /home/james/Code/SemPKM/docs/index.html
    — must show 5 img tags with the correct filenames

    grep -c '&lt;svg' /home/james/Code/SemPKM/docs/index.html | grep -v carousel
    — the SVG in slide 2 must still be present (grep for 'Graph Visualization' in carousel caption)
  </verify>
  <done>
    - 6 carousel-slide divs in docs/index.html
    - 5 img tags pointing to ../screenshots/ paths
    - 1 SVG block (slide 2 Graph Visualization) unchanged
    - All carousel captions present with correct text
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

1. File count: `ls docs/screenshots/ | wc -l` → 5
2. Slide count: `grep -c 'class="carousel-slide"' docs/index.html` → 6
3. Image paths: `grep 'src="\.\.\/screenshots\/' docs/index.html` → 5 lines
4. SVG preserved: `grep -A2 'Graph Visualization' docs/index.html` → shows SVG slide caption intact
5. Slide 3+4 captions reference layouts: `grep 'layouts' docs/index.html` → 2 matches
</verification>

<success_criteria>
- docs/screenshots/ contains exactly 5 PNG files
- docs/index.html carousel has 6 slides in order: Object Browser (img), Graph Visualization (SVG), Graph View (img), Dark Mode Graph (img), SPARQL-Powered Tables (img), SHACL-Driven Forms (img)
- All img src attributes use the path ../screenshots/FILENAME.png
- The Graph Visualization SVG slide (slide 2) is byte-for-byte identical to the original
- No CSS or JS changes in docs/index.html
</success_criteria>

<output>
After completion, create `.planning/quick/7-replace-carousel-svg-placeholders-with-r/7-SUMMARY.md` with what was done, files changed, and any notes.
</output>
