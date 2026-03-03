---
phase: 32-carousel-views-and-view-bug-fixes
verified: 2026-03-03T07:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 32: Carousel Views and View Bug Fixes Verification Report

**Phase Goal:** Object types with multiple manifest-declared views expose a tab bar; users switch views instantly; concept cards group-by works; broken view switch buttons are gone
**Verified:** 2026-03-03T07:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

Success criteria taken from ROADMAP.md `success_criteria` array (4 criteria), cross-mapped to
13 testable must-haves drawn from the two PLAN frontmatter `must_haves` blocks.

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | For a type with multiple manifest views, a tab bar appears above the view body listing each view by name | VERIFIED | `carousel_tab_bar.html` renders `.carousel-tab-bar` when `all_specs\|length > 1`; hidden otherwise |
| 2  | Clicking a carousel tab switches the view content instantly (no page reload) | VERIFIED | `switchCarouselView()` calls `htmx.ajax('GET', url, { target: viewBody, swap: 'outerHTML', select: '.carousel-view-body' })` |
| 3  | The active carousel tab is visually indicated with a bottom border accent | VERIFIED | `.carousel-tab.active` sets `border-bottom-color: var(--color-primary)` in `views.css:106` |
| 4  | Active tab selection persists per type IRI in localStorage across sessions | VERIFIED | `sempkm_carousel_view` JSON map stored in `localStorage` in `switchCarouselView()`; restored via `restoreCarouselView()` on load |
| 5  | If the saved view no longer exists in the manifest, the first view is shown silently | VERIFIED | `restoreCarouselView()` deletes stale entry and returns without switching (lines 1776–1781 workspace.js) |
| 6  | Types with only one view spec show no carousel tab bar | VERIFIED | `{% if all_specs\|length > 1 %}` guard in `carousel_tab_bar.html:5` |
| 7  | Tab labels use prettified display names: "Table View", "Cards View", "Graph View" | VERIFIED | `DISPLAY_NAMES = {'table': 'Table View', 'card': 'Cards View', 'graph': 'Graph View'}` in template; `DISPLAY_NAMES.get(s.renderer_type, s.label)` renders each tab |
| 8  | While a view fetches server data, a spinner shows in the view body area; the tab bar stays interactive | VERIFIED | `view-loading-indicator` div appended to `viewBody` in `switchCarouselView()`; spinner CSS with `carousel-spin` keyframe animation in `views.css`; tab bar is outside `.carousel-view-body` swap target so it stays interactive |
| 9  | The carousel tab bar is outside the htmx swap target (switching views replaces only the view body, not the tab bar) | VERIFIED | Two-container pattern: `{% include "browser/carousel_tab_bar.html" %}` precedes `<div class="carousel-view-body">` in all three view templates; `switchCarouselView` targets `.carousel-view-body` not `.group-editor-area` |
| 10 | Cards group-by select changes the displayed grouping without page reload (htmx swap works inside dockview panel) | VERIFIED | `cards_view.html:11` — `hx-target="closest .group-editor-area"` on group-by select |
| 11 | Pagination prev/next/page-number links and jump-to-page work inside dockview panels | VERIFIED | All 5 `hx-target` attributes in `pagination.html` use `closest .group-editor-area`; inline JS `onkeydown`/`onclick` use `this.closest('.group-editor-area')` |
| 12 | Cards groups render as collapsible accordion sections with count in header, all expanded by default | VERIFIED | `cards_view.html:69–84` — `.card-group-section` with `.card-group-header`, `.card-group-chevron`, `.card-group-count`; no `collapsed` class on initial render |
| 13 | The old view-type-switcher buttons are completely gone from the view toolbar | VERIFIED | Zero matches for `switchViewType`, `view-type-switcher`, `view-type-btn` across templates, CSS, and JS |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/templates/browser/carousel_tab_bar.html` | Jinja2 partial rendering carousel tab bar from `all_specs` context; inline `restoreCarouselView` call | VERIFIED | File exists, 23 lines, substantive: conditional render, display names map, `onclick` wires to `switchCarouselView`, inline script calls `restoreCarouselView` |
| `backend/app/templates/browser/view_toolbar.html` | View toolbar without view-type-switcher; htmx target uses `closest .group-editor-area` | VERIFIED | `.view-type-switcher` div gone; filter input `hx-target="closest .group-editor-area"`; `afterSwap` listener checks `.classList.contains('group-editor-area')` |
| `backend/app/templates/browser/cards_view.html` | Accordion group sections with chevron, count, and collapsible body; htmx target fix; carousel include and view-body wrapper | VERIFIED | Line 1: `{% include "browser/carousel_tab_bar.html" %}`; line 2: `<div class="carousel-view-body">`; lines 69–84: accordion markup with `.card-group-section`; group-by select has `closest .group-editor-area` |
| `backend/app/templates/browser/table_view.html` | carousel include, `.carousel-view-body` wrapper, sort headers use `closest .group-editor-area` | VERIFIED | Line 1: include; line 2: wrapper; `hx-target="closest .group-editor-area"` on sort headers |
| `backend/app/templates/browser/graph_view.html` | carousel include and `.carousel-view-body` wrapper | VERIFIED | Line 1: include; line 2: wrapper; line 43: closing `</div>` |
| `backend/app/templates/browser/pagination.html` | All `hx-target` attributes use `closest .group-editor-area`; inline JS targets `this.closest(...)` | VERIFIED | 5 declarative `hx-target` attributes all use `closest .group-editor-area`; `onkeydown` and `onclick` JS use `.closest('.group-editor-area')` |
| `backend/app/templates/browser/search_suggestions.html` | "Create new" hx-target updated from `#editor-area` | VERIFIED | `hx-target="closest .group-editor-area"` at line 22 |
| `backend/app/views/service.py` | "Ungrouped" replaces "(No value)"; sorted to end of group list | VERIFIED | Line 660: `group_vals = ["Ungrouped"]`; line 668: sort key `(x[0] == "Ungrouped", x[0])` |
| `frontend/static/css/views.css` | Carousel tab bar styles, active bottom-border accent, loading spinner, accordion CSS, old view-type-switcher CSS removed | VERIFIED | `.carousel-tab-bar`, `.carousel-tab`, `.carousel-tab.active` (border-bottom-color primary), `.carousel-view-body`, `.view-loading-indicator`, `.view-loading-spinner`, `@keyframes carousel-spin`, `.card-group-section`, `.card-group-body`, `.card-group-body.collapsed` (grid-template-rows 0fr) all present; no `.view-type-switcher` or `.view-type-btn` |
| `frontend/static/js/workspace.js` | `switchCarouselView()`, `restoreCarouselView()` defined and exposed on `window`; `sempkm_carousel_view` localStorage key; no `_carouselSwitching` flag | VERIFIED | Both functions defined (lines 1719–1787); `window.switchCarouselView` and `window.restoreCarouselView` assigned at lines 1802–1803; `sempkm_carousel_view` key used in 4 places; `_carouselSwitching` count: 0 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `carousel_tab_bar.html` | `workspace.js switchCarouselView()` | `onclick="switchCarouselView(this, ...)"` on each tab button | WIRED | line 12 of `carousel_tab_bar.html`; function defined at workspace.js:1719 and exposed on `window` at line 1802 |
| `carousel_tab_bar.html` | `workspace.js restoreCarouselView()` | Inline `<script>` calls `restoreCarouselView(...)` on load | WIRED | lines 17–21 of `carousel_tab_bar.html`; function defined at workspace.js:1766 and exposed on `window` at line 1803 |
| `workspace.js` | `localStorage` | `sempkm_carousel_view` JSON key | WIRED | `localStorage.getItem('sempkm_carousel_view')` and `localStorage.setItem(...)` in both `switchCarouselView` and `restoreCarouselView` |
| `table_view.html` / `cards_view.html` / `graph_view.html` | `carousel_tab_bar.html` | `{% include "browser/carousel_tab_bar.html" %}` Jinja2 include | WIRED | Line 1 of each view template |
| `cards_view.html` group-by select | `.group-editor-area` container | `hx-target="closest .group-editor-area"` | WIRED | `cards_view.html:11` |
| `pagination.html` | `.group-editor-area` container | `hx-target="closest .group-editor-area"` (5 links) + `this.closest('.group-editor-area')` (2 inline JS) | WIRED | Confirmed in `pagination.html:14, 30, 44, 56, 64, 76, 78` |
| `switchCarouselView()` | `.carousel-view-body` swap target | `htmx.ajax(..., { target: viewBody, swap: 'outerHTML', select: '.carousel-view-body' })` | WIRED | workspace.js:1762; `viewBody` resolved via `bar.parentElement.querySelector('.carousel-view-body')` at line 1746 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BUG-01 | 32-01-PLAN.md | User sees correctly grouped concept cards when group-by is applied | SATISFIED | Accordion group rendering in `cards_view.html`; "Ungrouped" label and end-sort in `service.py`; htmx target fixed so group-by select swap works inside dockview panels |
| BUG-03 | 32-01-PLAN.md | Broken view switch buttons are removed from the object view (replaced by VIEW-02 carousel tab bar) | SATISFIED | `view-type-switcher` div, `switchViewType()` JS, and `.view-type-btn` CSS are all absent; zero matches confirmed by grep |
| VIEW-02 | 32-02-PLAN.md | Object types with multiple manifest-declared views show a tab bar above the view body; user can switch between views; active view persists per type IRI | SATISFIED | `carousel_tab_bar.html` partial; two-container pattern in all view templates; `switchCarouselView()` with htmx + `restoreCarouselView()` with localStorage persistence |

No orphaned requirements: REQUIREMENTS.md maps exactly VIEW-02, BUG-01, BUG-03 to Phase 32, matching both PLAN frontmatter declarations.

### Anti-Patterns Found

None detected in the modified files. Specific scans:

- Zero `TODO`, `FIXME`, `XXX`, `HACK`, `PLACEHOLDER` comments in modified files
- Zero `return null` / `return {}` / `return []` stub returns in new template or JS code
- No `console.log`-only handler implementations
- No remaining `#editor-area` htmx targets in `backend/app/templates/browser/`
- No remaining `switchViewType`, `view-type-switcher`, `view-type-btn` identifiers anywhere
- No `_carouselSwitching` flag (confirming two-container pattern is clean)
- Lucide SVG chevron icon in `.card-group-chevron svg` correctly uses `flex-shrink: 0` and `stroke: currentColor` per CLAUDE.md rules

### Human Verification Required

The following behaviors cannot be verified by static code analysis:

#### 1. Carousel tab bar renders and switches views in a running browser

**Test:** Open the app, navigate to a type with multiple views (e.g., Concepts which has Table and Cards views). Verify the carousel tab bar appears above the view body. Click each tab.
**Expected:** Tab bar is visible; clicking a tab replaces only the view body content with the new view; the tab bar itself does not flash or re-render; active tab gains bottom-border accent.
**Why human:** DOM rendering and htmx swap behavior require a live browser.

#### 2. Loading spinner appears during view switch

**Test:** With browser DevTools Network throttling (e.g., Slow 3G), click a carousel tab.
**Expected:** A spinner overlay appears inside the view body area while the new view loads; the tab bar remains clickable during load; the spinner disappears when the view renders.
**Why human:** Requires network throttling and visual confirmation.

#### 3. localStorage persistence survives page reload

**Test:** Open a type with multiple views, click to the Cards view tab, then reload the page (F5).
**Expected:** After reload, the Cards view is shown (not the default Table view); the correct tab is active.
**Why human:** Requires a real browser session with localStorage.

#### 4. Cards accordion collapses and expands

**Test:** Open the Concepts Cards view with a group-by predicate selected (e.g., "Type"). Verify groups render as accordion sections with a chevron and count. Click a group header.
**Expected:** The card grid collapses smoothly (CSS grid-template-rows animation). Click again to expand.
**Why human:** Requires visual inspection of the animation and DOM state toggle.

#### 5. "Ungrouped" section appears at end for objects missing the group-by value

**Test:** Open a Cards view with group-by active when some objects lack the group-by property.
**Expected:** An "Ungrouped" section appears at the bottom of the group list (after alphabetically sorted named groups).
**Why human:** Requires seed data with partial coverage of the group-by predicate.

### Gaps Summary

None. All 13 must-haves are VERIFIED at all three levels (exists, substantive, wired). All four commits referenced in the SUMMARYs (87e38c8, 3cd2baf, fc94dad, a554263) exist in git history. All three requirement IDs (VIEW-02, BUG-01, BUG-03) are satisfied and cross-referenced correctly. No orphaned requirements found.

---

_Verified: 2026-03-03T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
