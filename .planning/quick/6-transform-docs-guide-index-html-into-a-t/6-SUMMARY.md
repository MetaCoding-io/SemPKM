---
phase: quick-6
plan: 1
subsystem: docs
tags: [docs, markdown-reader, github-pages, static-html, marked-js, highlight-js]
dependency_graph:
  requires: []
  provides: [docs/guide two-panel markdown reader]
  affects: [docs/guide/index.html]
tech_stack:
  added: [marked.js CDN, marked-highlight CDN, highlight.js CDN, DOMPurify CDN]
  patterns: [inline JS IIFE, fetch + innerHTML, sticky sidebar layout]
key_files:
  created: []
  modified:
    - docs/guide/index.html
decisions:
  - Use github-dark.min.css (not github.min.css) for highlight.js — dark-themed standalone page needs the explicitly dark variant; the app uses github.min.css because it has its own dark CSS custom properties
  - Remove fade-in/scroll animation entirely — reader layout does not need entrance animations; sidebar nav links load inline content rather than linking to full pages
  - Reuse all existing CSS custom properties (--bg-primary, --accent-blue, etc.) for consistent look matching the rest of docs site
  - highlight.js stylesheet placed in <head> (not after body scripts) to avoid unstyled code flash on first load
metrics:
  duration: "5min"
  completed: "2026-02-27"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 6: Transform docs/guide/index.html into a Two-Panel Markdown Reader Summary

**One-liner:** Replaced docs/guide static hub grid with a sticky-sidebar + marked.js markdown reader — 26 chapters across 7 parts + appendices, dark-themed, GitHub Pages compatible, no build step.

## What Was Built

`docs/guide/index.html` was transformed from a decorative hub page (grid cards linking to raw `.md` files) into a functional two-panel markdown reader:

- **Left sidebar (260px, sticky):** 7 named parts + Appendices section, each with chapter links using `data-file` attributes. Clicking any link calls `loadArticle(filename, linkEl)` which fetches and renders the `.md` file inline.
- **Right content panel (flex: 1):** `<div id="guide-content" class="markdown-body">` receives rendered HTML from marked.js + DOMPurify.
- **Auto-load:** First chapter (`01-what-is-sempkm.md`) loads automatically on page open via `var firstLink = document.querySelector('.sidebar-chapter-list a[data-file]')`.
- **Active state:** Clicked link gets `sidebar-link-active` class (orange left border + text), removed from all others on each click.
- **Syntax highlighting:** highlight.js 11.11.1 with `github-dark.min.css` — matches the dark page theme without requiring custom CSS overrides.
- **Responsive:** At `<= 768px`, sidebar shifts to full-width with `max-height: 240px` scrollable drawer above the content panel.

## CDN Scripts Used

All pinned to same versions as the app's `base.html`:
- `https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js`
- `https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js`
- `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js`
- `https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js`

## CSS Changes

**Removed:** `.guide-hero`, `.guide-section`, `.guide-grid`, `.part-card`, `.part-label`, `.part-title`, `.chapter-list`, `.appendix-card`, `.appendix-grid`, `.fade-in`, `.section-label`, `.section-title`, `.section-subtitle`, `section { padding }`, `.container`

**Added:** `.reader-layout`, `.reader-sidebar`, `.reader-content`, `.sidebar-part-label`, `.sidebar-chapter-list`, `.sidebar-chapter-list a`, `.sidebar-link-active`, `.markdown-body` and all sub-selectors, `.docs-loading`, `.docs-error`, responsive overrides for reader layout

**Preserved:** All `:root` CSS variables, nav CSS, footer CSS, responsive nav (hamburger menu), mobile nav `.nav-toggle`/`.nav-links.open` behavior

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `docs/guide/index.html` — FOUND
- commit `cd2e482` — FOUND
- 26/26 structural verification checks passed (all 26 `data-file` attrs, all CDN scripts, all CSS classes, auto-load, active state, nav, footer, CSS vars)
