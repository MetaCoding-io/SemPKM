---
phase: quick-6
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/guide/index.html
autonomous: true
requirements:
  - QUICK-6
must_haves:
  truths:
    - "Left sidebar lists all chapters and appendices grouped by part"
    - "Clicking a chapter loads the markdown article into the right panel without a page navigation"
    - "Right panel renders markdown with syntax-highlighted code blocks"
    - "Active chapter is visually highlighted in the sidebar"
    - "Page works as a static file on GitHub Pages (relative URL fetch of .md files)"
    - "Initial load shows the first chapter (01-what-is-sempkm.md) pre-loaded"
  artifacts:
    - path: "docs/guide/index.html"
      provides: "Two-panel markdown reader (sidebar + content)"
      contains: "marked.umd.js CDN script, renderMarkdownFromUrl equivalent"
  key_links:
    - from: "sidebar nav links"
      to: "content panel"
      via: "click handler calling loadArticle(filename)"
      pattern: "fetch.*\\.md"
    - from: "fetch response"
      to: "#guide-content"
      via: "marked.parse + innerHTML"
      pattern: "innerHTML.*rawHtml"
---

<objective>
Transform docs/guide/index.html from a static hub page (grid of links to .md files) into a two-panel markdown reader:
- Left sidebar: chapter/appendix list grouped by part, clicking loads the article
- Right panel: rendered markdown content via marked.js CDN (same CDN as the app uses)

Purpose: Provides a readable, self-contained guide experience on GitHub Pages without a build step.
Output: Single transformed docs/guide/index.html.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<interfaces>
<!-- CDN scripts used by the app (from backend/app/templates/base.html lines 36-40) -->
<!-- Use these exact CDN URLs — pinned versions, already proven to work in the app -->

marked.js (UMD, globals: globalThis.marked, globalThis.markedHighlight):
  https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js
  https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js

highlight.js:
  https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js
  stylesheet: https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css

DOMPurify:
  https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js

<!-- renderMarkdownFromUrl pattern (from frontend/static/js/markdown-render.js) -->
<!-- Inline this logic directly — no external JS file reference in the static HTML -->

function getMarked():
  - Lazily construct Marked with markedHighlight integration
  - globalThis.marked.Marked constructor + globalThis.markedHighlight.markedHighlight
  - hljs.highlight(code, { language }) for syntax highlighting

function renderMarkdownFromUrl(url, targetId):
  - target.innerHTML = '<p class="docs-loading">Loading...</p>'
  - fetch(url) -> response.text() -> md.parse(rawText)
  - DOMPurify.sanitize(rawHtml) if available
  - target.innerHTML = rawHtml
  - catch -> target.innerHTML = '<p class="docs-error">Failed to load document.</p>'

<!-- Chapter list (all 26 .md files in docs/guide/, from directory listing) -->
Part I   — Introduction:       01-what-is-sempkm.md, 02-core-concepts.md, 03-installation-and-setup.md
Part II  — Workspace:          04-workspace-interface.md, 05-working-with-objects.md, 06-edges-and-relationships.md, 07-browsing-and-visualizing.md, 08-keyboard-shortcuts.md
Part III — Mental Models:      09-understanding-mental-models.md, 10-managing-mental-models.md
Part IV  — Administration:     11-user-management.md, 12-webhooks.md, 13-settings.md, 14-system-health-and-debugging.md
Part V   — Event Log:          15-event-log.md
Part VI  — Advanced Topics:    16-data-model.md, 17-command-api.md, 18-sparql-endpoint.md, 19-creating-mental-models.md
Part VII — Deployment:         20-production-deployment.md
Appendices:                    appendix-a-environment-variables.md, appendix-b-keyboard-shortcuts.md, appendix-c-command-api-reference.md, appendix-d-glossary.md, appendix-e-troubleshooting.md, appendix-f-faq.md

<!-- Existing CSS variables to reuse (already in the file's <style> block) -->
--bg-primary: #0a0a0f
--bg-secondary: #12121a
--bg-card: #16161f
--bg-card-hover: #1c1c28
--border-subtle: #1e1e2e
--text-primary: #e8e8f0
--text-secondary: #9898b0
--accent-blue: #e8772e      (actually orange — used for active/accent states)
--accent-purple: #f59e0b
--accent-gradient: linear-gradient(135deg, #e8772e, #f59e0b)
--font-stack / --font-mono / --radius / --radius-sm
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Transform index.html into two-panel reader</name>
  <files>docs/guide/index.html</files>
  <action>
Replace the entire content of docs/guide/index.html. Keep ALL existing CSS variables and the nav/footer HTML unchanged. Replace the guide-hero + guide-section body content and add the two-panel reader layout. Inline the markdown rendering JS (do not reference external .js files).

LAYOUT STRUCTURE (replaces everything between nav and footer):

```html
<div class="reader-layout">
  <aside class="reader-sidebar" id="reader-sidebar">
    <!-- part groups, each with nav links -->
  </aside>
  <main class="reader-content" id="reader-content">
    <div id="guide-content" class="markdown-body docs-content">
      <p class="docs-loading">Loading...</p>
    </div>
  </main>
</div>
```

SIDEBAR: Build the sidebar as a `<nav>` with part groups. Each group has:
- A `<div class="sidebar-part-label">Part N — Title</div>` heading (not a link)
- A `<ul class="sidebar-chapter-list">` with `<li><a href="#" data-file="filename.md">N. Chapter Title</a></li>` items
- Appendices section at the end, same pattern
- All existing chapter names and file names from the current chapter-list links in the file

ACTIVE STATE: clicking a link adds class `sidebar-link-active` to it and removes from others.

CSS to add to the existing `<style>` block (use existing CSS vars, no new color values):

```css
/* ── Reader Layout ── */
.reader-layout {
  display: flex;
  min-height: calc(100vh - 64px);  /* subtract nav height */
  margin-top: 64px;                /* push below fixed nav */
  max-width: var(--max-width);
  margin-left: auto;
  margin-right: auto;
  padding: 0 1.5rem;
  gap: 0;
}

.reader-sidebar {
  width: 260px;
  min-width: 260px;
  border-right: 1px solid var(--border-subtle);
  padding: 2rem 0;
  position: sticky;
  top: 64px;
  height: calc(100vh - 64px);
  overflow-y: auto;
}

.reader-content {
  flex: 1;
  padding: 2rem 2.5rem;
  min-width: 0;  /* prevent flex overflow */
  overflow-y: auto;
}

.sidebar-part-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-blue);
  padding: 1.2rem 1rem 0.4rem;
}

.sidebar-part-label:first-child {
  padding-top: 0;
}

.sidebar-chapter-list {
  list-style: none;
}

.sidebar-chapter-list a {
  display: block;
  padding: 0.4rem 1rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
  border-radius: 0;
  transition: background 0.15s, color 0.15s;
  border-left: 2px solid transparent;
}

.sidebar-chapter-list a:hover {
  background: var(--bg-card);
  color: var(--text-primary);
}

.sidebar-chapter-list a.sidebar-link-active {
  color: var(--accent-blue);
  border-left-color: var(--accent-blue);
  background: var(--bg-card);
  font-weight: 600;
}

/* ── Markdown body (adapted from app's workspace.css, using local vars) ── */
.markdown-body {
  font-family: var(--font-stack);
  font-size: 0.95rem;
  line-height: 1.7;
  color: var(--text-primary);
}

.markdown-body h1, .markdown-body h2, .markdown-body h3,
.markdown-body h4, .markdown-body h5, .markdown-body h6 {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.markdown-body h1 { font-size: 1.8rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.3em; }
.markdown-body h2 { font-size: 1.4rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.3em; }
.markdown-body h3 { font-size: 1.15rem; }

.markdown-body p { margin: 0.8em 0; }

.markdown-body pre {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  overflow-x: auto;
  font-size: 0.85rem;
}

.markdown-body code {
  font-family: var(--font-mono);
  font-size: 0.85em;
}

.markdown-body :not(pre) > code {
  background: var(--bg-secondary);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
}

.markdown-body blockquote {
  border-left: 3px solid var(--border-subtle);
  padding: 0.5em 1em;
  color: var(--text-secondary);
  margin: 0.8em 0;
}

.markdown-body img { max-width: 100%; border-radius: var(--radius-sm); }

.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.8em 0;
}

.markdown-body th, .markdown-body td {
  border: 1px solid var(--border-subtle);
  padding: 6px 12px;
  text-align: left;
}

.markdown-body th { background: var(--bg-card); font-weight: 600; }

.markdown-body ul, .markdown-body ol { padding-left: 2em; margin: 0.8em 0; }
.markdown-body li { margin: 0.3em 0; }

.markdown-body a { color: var(--accent-blue); }
.markdown-body a:hover { color: var(--accent-purple); text-decoration: underline; }

.docs-loading { color: var(--text-secondary); font-style: italic; padding: 2rem 0; }
.docs-error   { color: #f87171; font-style: italic; padding: 2rem 0; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .reader-layout {
    flex-direction: column;
    padding: 0;
  }
  .reader-sidebar {
    width: 100%;
    min-width: unset;
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
    position: static;
    height: auto;
    max-height: 240px;
    padding: 1rem 1.5rem;
  }
  .reader-content {
    padding: 1.5rem;
  }
}
```

REMOVE from existing CSS: the old `.guide-hero`, `.guide-section`, `.guide-grid`, `.part-card`, `.part-label`, `.part-title`, `.chapter-list`, `.appendix-card`, `.appendix-grid`, `.fade-in`, `.section-label`, `.section-title`, `.section-subtitle`, `section { padding }`, `.container` rules — they are replaced by the reader layout above. Keep nav CSS, footer CSS, responsive nav CSS, and all `:root` variables.

JAVASCRIPT (replace the existing script block):

```html
<script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>

<script>
(function () {
  'use strict';

  var _marked = null;

  function getMarked() {
    if (_marked) return _marked;
    if (typeof globalThis.marked === 'undefined' ||
        typeof globalThis.markedHighlight === 'undefined') return null;
    var Marked = globalThis.marked.Marked;
    var markedHighlight = globalThis.markedHighlight.markedHighlight;
    _marked = new Marked(markedHighlight({
      emptyLangClass: 'hljs',
      langPrefix: 'hljs language-',
      highlight: function (code, lang) {
        if (typeof hljs === 'undefined') return code;
        var language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language: language }).value;
      }
    }));
    return _marked;
  }

  function loadArticle(filename, linkEl) {
    var target = document.getElementById('guide-content');
    if (!target) return;

    // Update active state
    document.querySelectorAll('.sidebar-chapter-list a').forEach(function (a) {
      a.classList.remove('sidebar-link-active');
    });
    if (linkEl) linkEl.classList.add('sidebar-link-active');

    target.innerHTML = '<p class="docs-loading">Loading...</p>';
    target.scrollTop = 0;
    document.querySelector('.reader-content').scrollTop = 0;

    fetch(filename)
      .then(function (r) { return r.text(); })
      .then(function (rawText) {
        var md = getMarked();
        if (!md) { target.textContent = rawText; return; }
        var rawHtml = md.parse(rawText);
        if (typeof DOMPurify !== 'undefined') rawHtml = DOMPurify.sanitize(rawHtml);
        target.innerHTML = rawHtml;
      })
      .catch(function () {
        target.innerHTML = '<p class="docs-error">Failed to load document.</p>';
      });
  }

  // Wire up sidebar links
  document.querySelectorAll('.sidebar-chapter-list a[data-file]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      loadArticle(a.getAttribute('data-file'), a);
    });
  });

  // Mobile nav toggle (preserve existing behavior)
  var toggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', function () { navLinks.classList.toggle('open'); });
    navLinks.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { navLinks.classList.remove('open'); });
    });
  }

  // Load first chapter on init
  var firstLink = document.querySelector('.sidebar-chapter-list a[data-file]');
  if (firstLink) loadArticle(firstLink.getAttribute('data-file'), firstLink);
})();
</script>
```

Use `github-dark.min.css` (not `github.min.css`) for highlight.js — matches the dark theme of the page. The app uses `github.min.css` because it has its own dark variables; this standalone page needs the explicitly dark variant.

URL hash support (optional if time permits, skip if adds complexity): could update `location.hash` to `#filename` on article load and read it on init to restore state. Skip this — keep it simple, first chapter always loads.
  </action>
  <verify>Open docs/guide/index.html directly in a browser (file:// or a local static server). Confirm: sidebar shows all 7 parts + appendices, clicking a chapter link renders its markdown in the right panel, code blocks have syntax highlighting, active link is highlighted in orange, first chapter loads automatically on page open.</verify>
  <done>Two-panel reader works as a standalone static HTML file: sidebar nav + markdown rendering panel, dark-themed, all 26 chapters accessible, no build step required.</done>
</task>

</tasks>

<verification>
- docs/guide/index.html opens without errors in browser (file:// URL or GitHub Pages)
- All part labels and chapter names visible in left sidebar
- Clicking chapter link fetches and renders the corresponding .md file
- Code blocks render with dark syntax highlighting
- Active chapter link is visually distinct (orange left border + text)
- Page is responsive: sidebar stacks above content on narrow viewports
- No console errors from CDN script loading
</verification>

<success_criteria>
docs/guide/index.html is a two-panel markdown reader:
1. Left sidebar: all 26 chapters grouped by part, clicking loads article inline
2. Right panel: rendered markdown with syntax-highlighted code blocks
3. Works as a static file (GitHub Pages compatible — no server required)
4. Matches existing dark theme CSS variables
5. First chapter auto-loads on page open
</success_criteria>

<output>
After completion, create `.planning/quick/6-transform-docs-guide-index-html-into-a-t/6-SUMMARY.md` with what was built, key decisions, and files modified.
</output>
