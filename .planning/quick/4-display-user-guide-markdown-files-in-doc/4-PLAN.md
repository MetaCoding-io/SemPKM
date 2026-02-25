---
phase: quick-4
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/static/js/markdown-render.js
  - backend/app/browser/router.py
  - backend/app/templates/browser/docs_viewer.html
  - backend/app/templates/browser/docs_page.html
  - frontend/static/css/workspace.css
autonomous: true
requirements: []

must_haves:
  truths:
    - "Clicking a chapter link in the Documentation section loads rendered markdown inside the same workspace tab"
    - "Rendered markdown page shows a back button that returns to the Docs hub"
    - "All 20 main chapters and 6 appendices are listed with descriptive titles"
    - "Interactive Tutorials section is unchanged"
    - "External API reference links remain as-is"
  artifacts:
    - path: "backend/app/templates/browser/docs_viewer.html"
      provides: "Rendered markdown viewer template with back button and content div"
    - path: "frontend/static/js/markdown-render.js"
      provides: "renderMarkdownFromUrl() window global"
  key_links:
    - from: "docs_page.html chapter links"
      to: "/browser/docs/guide/{filename}"
      via: "hx-get with hx-target='closest .group-editor-area'"
      pattern: "hx-get.*browser/docs/guide"
    - from: "docs_viewer.html inline script"
      to: "docs-content div"
      via: "renderMarkdownFromUrl('/docs/guide/{filename}', 'docs-content')"
      pattern: "renderMarkdownFromUrl"
---

<objective>
Replace the stub Documentation section in the Docs & Tutorials hub with a full chapter list where
each chapter renders its markdown inline within the workspace tab via a dedicated viewer page.

Purpose: Users can read the full user guide without leaving the application or seeing raw markdown text.
Output: A working in-tab markdown reader covering all 27 guide files, with back-navigation to the hub.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/PROJECT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add renderMarkdownFromUrl to markdown-render.js</name>
  <files>frontend/static/js/markdown-render.js</files>
  <action>
    Add `window.renderMarkdownFromUrl(url, targetId)` to the existing IIFE in
    `frontend/static/js/markdown-render.js`, placed immediately after the existing
    `window.renderMarkdownBody` definition.

    The function must:
    1. Locate the target element via `document.getElementById(targetId)` — return early if missing.
    2. Set `target.innerHTML = '<p class="docs-loading">Loading...</p>'` as initial state.
    3. Use `fetch(url)` then `.text()` to retrieve the raw markdown.
    4. Call `getMarked()` (already defined in the IIFE scope) to get the Marked instance.
       If null (CDN not loaded), set `target.textContent = rawText` as fallback.
    5. Call `md.parse(rawText)` → sanitize with `DOMPurify.sanitize()` (same pattern as renderMarkdownBody) → set `target.innerHTML`.
    6. On fetch error (`.catch`), set `target.innerHTML = '<p class="docs-error">Failed to load document.</p>'`.

    The function must be exposed as `window.renderMarkdownFromUrl`. Keep the IIFE structure intact —
    do not change the existing `renderMarkdownBody` function.
  </action>
  <verify>Open browser console on the docs tab and run: `typeof window.renderMarkdownFromUrl` — must return `"function"`.</verify>
  <done>window.renderMarkdownFromUrl is a callable function that fetches a URL and renders markdown into a target element.</done>
</task>

<task type="auto">
  <name>Task 2: Add /browser/docs/guide/{filename} endpoint and docs_viewer.html template</name>
  <files>
    backend/app/browser/router.py
    backend/app/templates/browser/docs_viewer.html
  </files>
  <action>
    **router.py** — Add a new endpoint immediately after the existing `/docs` endpoint (line 98):

    ```python
    @router.get("/docs/guide/{filename:path}")
    async def docs_guide_viewer(
        filename: str,
        request: Request,
        user: User = Depends(get_current_user),
    ) -> HTMLResponse:
        """Render a single guide markdown file as a workspace tab fragment."""
        templates = request.app.state.templates
        return templates.TemplateResponse(request, "browser/docs_viewer.html", {
            "user": user,
            "filename": filename,
        })
    ```

    The `filename:path` path parameter type allows filenames with dots (e.g. `04-workspace-interface.md`).

    **docs_viewer.html** — Create `backend/app/templates/browser/docs_viewer.html` as:

    ```html
    <div id="docs-viewer" class="docs-viewer">

      <div class="docs-viewer-header">
        <button class="docs-back-btn"
                hx-get="/browser/docs"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="arrow-left"></i>
          <span>Back to Docs</span>
        </button>
      </div>

      <div id="docs-content" class="docs-content markdown-body">
        <p class="docs-loading">Loading...</p>
      </div>

    </div>

    <script>
    (function () {
      if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
      }
      var filename = {{ filename | tojson }};
      if (typeof window.renderMarkdownFromUrl === 'function') {
        window.renderMarkdownFromUrl('/docs/guide/' + filename, 'docs-content');
      }
    })();
    </script>
    ```

    Note: `{{ filename | tojson }}` safely encodes the filename as a JS string literal (handles any
    special characters). The Lucide re-init must run before `renderMarkdownFromUrl` since back button
    icon needs to be drawn.
  </action>
  <verify>
    In the running app, open the Docs tab, then navigate to any chapter. Verify:
    1. `GET /browser/docs/guide/01-what-is-sempkm.md` returns 200 with HTML fragment.
    2. The docs-viewer div appears in the tab.
    3. The back button is visible with an arrow-left icon.
  </verify>
  <done>Navigating to /browser/docs/guide/{filename} renders the viewer template; back button returns to docs hub via htmx.</done>
</task>

<task type="auto">
  <name>Task 3: Update docs_page.html chapter list and add viewer CSS</name>
  <files>
    backend/app/templates/browser/docs_page.html
    frontend/static/css/workspace.css
  </files>
  <action>
    **docs_page.html** — Replace the entire `<!-- Documentation Links section -->` `<section>` block
    (lines 43–71) with a new section that has two subsections: User Guide chapters and External References.

    Keep the Interactive Tutorials section (lines 8–40) completely unchanged.

    New Documentation section structure:

    ```html
    <!-- Documentation section -->
    <section class="docs-section">
      <h3 class="docs-section-title">User Guide</h3>
      <div class="docs-chapter-list">

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/01-what-is-sempkm.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="info"></i>
          <span>1. What is SemPKM?</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/02-core-concepts.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="layers"></i>
          <span>2. Core Concepts</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/03-installation-and-setup.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="download"></i>
          <span>3. Installation and Setup</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/04-workspace-interface.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="layout-dashboard"></i>
          <span>4. Workspace Interface</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/05-working-with-objects.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="box"></i>
          <span>5. Working with Objects</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/06-edges-and-relationships.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="git-branch"></i>
          <span>6. Edges and Relationships</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/07-browsing-and-visualizing.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="eye"></i>
          <span>7. Browsing and Visualizing</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/08-keyboard-shortcuts.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="keyboard"></i>
          <span>8. Keyboard Shortcuts</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/09-understanding-mental-models.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="brain"></i>
          <span>9. Understanding Mental Models</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/10-managing-mental-models.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="package"></i>
          <span>10. Managing Mental Models</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/11-user-management.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="users"></i>
          <span>11. User Management</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/12-webhooks.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="webhook"></i>
          <span>12. Webhooks</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/13-settings.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="settings"></i>
          <span>13. Settings</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/14-system-health-and-debugging.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="activity"></i>
          <span>14. System Health and Debugging</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/15-event-log.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="clock"></i>
          <span>15. Event Log</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/16-data-model.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="database"></i>
          <span>16. Data Model</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/17-command-api.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="terminal"></i>
          <span>17. Command API</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/18-sparql-endpoint.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="search-code"></i>
          <span>18. SPARQL Endpoint</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/19-creating-mental-models.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="plus-square"></i>
          <span>19. Creating Mental Models</span>
        </button>

        <button class="docs-chapter-item"
                hx-get="/browser/docs/guide/20-production-deployment.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="server"></i>
          <span>20. Production Deployment</span>
        </button>

        <button class="docs-chapter-item docs-chapter-appendix"
                hx-get="/browser/docs/guide/appendix-a-environment-variables.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="file-text"></i>
          <span>Appendix A: Environment Variables</span>
        </button>

        <button class="docs-chapter-item docs-chapter-appendix"
                hx-get="/browser/docs/guide/appendix-b-keyboard-shortcuts.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="file-text"></i>
          <span>Appendix B: Keyboard Shortcuts</span>
        </button>

        <button class="docs-chapter-item docs-chapter-appendix"
                hx-get="/browser/docs/guide/appendix-c-command-api-reference.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="file-text"></i>
          <span>Appendix C: Command API Reference</span>
        </button>

        <button class="docs-chapter-item docs-chapter-appendix"
                hx-get="/browser/docs/guide/appendix-d-glossary.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="book"></i>
          <span>Appendix D: Glossary</span>
        </button>

        <button class="docs-chapter-item docs-chapter-appendix"
                hx-get="/browser/docs/guide/appendix-e-troubleshooting.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="alert-triangle"></i>
          <span>Appendix E: Troubleshooting</span>
        </button>

        <button class="docs-chapter-item docs-chapter-appendix"
                hx-get="/browser/docs/guide/appendix-f-faq.md"
                hx-target="closest .group-editor-area"
                hx-swap="innerHTML">
          <i data-lucide="help-circle"></i>
          <span>Appendix F: FAQ</span>
        </button>

      </div>
    </section>

    <!-- External References section -->
    <section class="docs-section">
      <h3 class="docs-section-title">External References</h3>
      <div class="docs-links">
        <a href="/redoc" target="_blank" class="docs-link-item">
          <i data-lucide="file-text"></i>
          <span>API Reference (ReDoc)</span>
        </a>
        <a href="/docs" target="_blank" class="docs-link-item">
          <i data-lucide="file-code"></i>
          <span>API Reference (Swagger)</span>
        </a>
        <a href="/health" target="_blank" class="docs-link-item">
          <i data-lucide="activity"></i>
          <span>Health Check</span>
        </a>
      </div>
    </section>
    ```

    Note: Using `<button>` elements (not `<a>`) for htmx chapter items avoids default anchor navigation
    behavior that could fight htmx. Buttons with hx-get fire htmx requests cleanly.

    **workspace.css** — Append the following CSS at the end of the file (after the last `.docs-link-item`
    block, around line 2342):

    ```css
    /* Docs chapter list */
    .docs-chapter-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .docs-chapter-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 7px 12px;
      border-radius: 4px;
      color: var(--color-text-muted);
      background: none;
      border: none;
      cursor: pointer;
      font-size: 13px;
      text-align: left;
      width: 100%;
      transition: background 0.1s;
    }

    .docs-chapter-item:hover {
      background: var(--color-hover);
      color: var(--color-text);
    }

    .docs-chapter-item i,
    .docs-chapter-item svg {
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .docs-chapter-appendix {
      color: var(--color-text-faint, var(--color-text-muted));
      font-size: 12px;
    }

    /* Docs viewer (rendered markdown page) */
    .docs-viewer {
      padding: 24px 32px;
      max-width: 800px;
    }

    .docs-viewer-header {
      margin-bottom: 20px;
    }

    .docs-back-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 4px;
      background: none;
      border: 1px solid var(--color-border);
      color: var(--color-text-muted);
      font-size: 13px;
      cursor: pointer;
      transition: background 0.1s, color 0.1s;
    }

    .docs-back-btn:hover {
      background: var(--color-hover);
      color: var(--color-text);
    }

    .docs-back-btn i,
    .docs-back-btn svg {
      width: 14px;
      height: 14px;
    }

    .docs-content {
      line-height: 1.6;
    }

    .docs-loading {
      color: var(--color-text-muted);
      font-style: italic;
      font-size: 13px;
    }

    .docs-error {
      color: var(--color-error, #e05252);
      font-size: 13px;
    }
    ```
  </action>
  <verify>
    1. Open the Docs tab — the User Guide section lists all 20 chapters + 6 appendices.
    2. Click chapter "1. What is SemPKM?" — the tab content is replaced with the viewer showing rendered markdown.
    3. Click "Back to Docs" — the docs hub reappears with the chapter list intact.
    4. Confirm the Interactive Tutorials section (with the two tour cards) is unchanged.
    5. Confirm the External References section shows ReDoc, Swagger, and Health Check links.
  </verify>
  <done>
    Full chapter list renders in the Docs hub. Each chapter loads rendered markdown in-tab. Back button
    returns to hub. Interactive Tutorials and External References sections are unmodified.
  </done>
</task>

</tasks>

<verification>
End-to-end verification steps:
1. `cd /home/james/Code/SemPKM && docker compose logs --tail=20 app` — no startup errors.
2. Navigate to the workspace and open the Docs tab.
3. Verify 26 chapter/appendix buttons are visible (20 chapters + 6 appendices).
4. Click chapter 4 (Workspace Interface) — rendered HTML replaces the tab content.
5. Verify back button icon renders (Lucide arrow-left) and returns to hub on click.
6. Click a tour card to verify Interactive Tutorials still works.
7. Verify code blocks in chapters with code (e.g., appendix-c) show syntax highlighting.
</verification>

<success_criteria>
- All 26 user guide files are accessible as in-tab rendered markdown viewers
- Back navigation returns to the Docs hub without page reload
- Interactive Tutorials section functions identically to before
- No raw markdown or plain-text is shown to the user
- Dark mode renders correctly (markdown body uses inherited CSS custom properties)
</success_criteria>

<output>
After completion, create `.planning/quick/4-display-user-guide-markdown-files-in-doc/4-SUMMARY.md`
with a brief summary of what was implemented, files changed, and any decisions made.
</output>
