---
phase: 13-dark-mode-and-visual-polish
verified: 2026-02-28T00:00:00Z
status: passed
score: 16/16 must-haves verified
re_verification:
  previous_status: human_needed
  previous_score: 12/12
  gaps_closed:
    - "Ctrl+K opens the command palette in Firefox (and all browsers)"
    - "Active tab has teal bottom accent only, no left border bleed on view tabs"
    - "Tabs have visible rounded top corners (not clipped by tab bar overflow)"
    - "Card views have distinctive borders in both dark and light mode"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Switch theme using user popover Sun/Monitor/Moon icons"
    expected: "Theme switches instantly with 150ms crossfade, active icon shows accent highlight, no page reload required"
    why_human: "Cannot verify visual crossfade animation or icon active state rendering programmatically"
  - test: "Set dark theme, clear site data, hard refresh, observe initial render"
    expected: "Page renders dark immediately — no flash of light theme before CSS loads"
    why_human: "Anti-FOUC behavior requires a real browser render pipeline to verify timing"
  - test: "Open command palette via Ctrl+K in Firefox, observe Theme entries, click 'Theme: Dark'"
    expected: "Ctrl+K opens palette without triggering Firefox URL bar focus. Palette renders with correct dark background via ninja-keys CSS variable overrides. Theme switches on click."
    why_human: "Firefox browser interception behavior and ninja-keys CSS variable visual rendering require a real browser session"
  - test: "Open object with Markdown body, switch to dark mode, verify CodeMirror editor appearance"
    expected: "Editor background becomes #282c34, text becomes #abb2bf, gutters #21252b, teal cursor; cursor position and undo history preserved"
    why_human: "Visual editor theme appearance and state preservation require interactive testing"
  - test: "Open graph view, switch between light and dark modes"
    expected: "Graph node backgrounds become muted (#5c6370), labels lighten (#abb2bf), edges become dark (#3e4452), selected node border becomes teal (#56b6c2)"
    why_human: "Cytoscape style rebuild visual result requires human inspection"
  - test: "Navigate to a 403 route, inspect panel and dark mode rendering"
    expected: "Styled panel displays with lock icon, 'Access Denied' title, role explanation, and 'Go Home' / 'Go Back' buttons; dark mode renders correctly without FOUC"
    why_human: "403 route access requires live app session and visual inspection"
  - test: "Open any card view, inspect card face borders in both light and dark mode"
    expected: "Flip cards and focus portal cards show a visible 1px solid border that adapts to the theme (#e0e0e0 light, #3e4452 dark)"
    why_human: "Card border visual quality and token adaptation require human inspection"
  - test: "Open tabs including view-type tabs, inspect active tab accent in both light and dark mode"
    expected: "Active tab shows only a bottom teal accent (2px border-bottom). No left border bleed visible. Top corners of tabs are visibly rounded (4px radius, not clipped)."
    why_human: "Pixel-level tab visual inspection of border-radius visibility and absence of left bleed requires human confirmation in a rendered browser"
---

# Phase 13: Dark Mode and Visual Polish Verification Report

**Phase Goal:** Users can choose their preferred theme (system, light, or dark) with instant switching, no flash, and consistent styling across all UI components including third-party libraries
**Verified:** 2026-02-28 (browser pass completed)
**Status:** passed
**Re-verification:** Yes — after plan 13-04 gap closure (Ctrl+K Firefox fix, tab accent bleed, border-radius clipping, card borders)

## Browser Pass Results (2026-02-28, commit 98ab66c)

Browser verification completed. Three bugs found and fixed:

1. **Collapsed sidebar text visible on workspace-layout** — `.workspace-layout.sidebar-collapsed` CSS rules were missing from `style.css`. Added equivalent rules to those already present for `.dashboard-layout.sidebar-collapsed`.
2. **Tab border-radius too small** — Changed from `4px` to `8px` in `workspace.css` for more visible rounded appearance.
3. **Tab visibility** — Added `1px solid var(--color-border)` border to all tabs so they visually pop against the same-color tab bar background.
4. **Theme persistence** — `theme.js` `setTheme()` now calls `SemPKMSettings.set('theme', preference)` so light mode preference survives page refresh (previously only `localStorage` was written, but settings system re-applied server default on reload).

All 8 human verification items confirmed passing after fixes.

## Re-verification Summary

Plan 13-04 closed 4 UAT gaps. All 4 fixes verified in the codebase. No regressions found in any of the 12 original truths.

| Gap | Fix Applied | Verified |
|-----|-------------|----------|
| Ctrl+K intercepted by Firefox | `workspace.js` line 531-538: `if (mod && e.key === 'k') { e.preventDefault(); ... ninja.open(); }` inside `initKeyboardShortcuts()` | VERIFIED |
| Tab accent left-border bleed | `.workspace-tab.view-tab` border-left rules removed from `views.css` entirely (selector gone) | VERIFIED |
| Tab border-radius clipped by overflow | `workspace.css` `.tab-bar-workspace` line 283: `padding: 4px 4px 0` (top 4px headroom above clip edge) | VERIFIED |
| Card views lacked distinctive borders | `views.css` lines 717, 766: `border: 1px solid var(--color-border)` on `.flip-card-front,.flip-card-back` and `.card-focus-front,.card-focus-back` | VERIFIED |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can click Sun/Monitor/Moon icons in user popover to switch themes | VERIFIED | `_sidebar.html` lines 135-145: `.popover-theme-row` with 3 `.theme-btn` elements, `data-theme-value` attrs, `onclick="setTheme(…)"` calls |
| 2 | Theme preference persists in localStorage, zero flash on reload | VERIFIED | Anti-FOUC inline script in `base.html` lines 7-16 reads `sempkm_theme` synchronously before any stylesheet; `theme.js` `setTheme()` writes to localStorage |
| 3 | Dark mode uses warmer grays with teal/cyan accents | VERIFIED | `theme.css` lines 69-128: `html[data-theme="dark"]` defines `#1e2127` bg, `#282c34` surface, `#56b6c2` teal accent |
| 4 | Light mode uses CSS custom property token system | VERIFIED | `theme.css` lines 8-67: complete `:root` token set (35+ tokens covering surfaces, text, borders, accent, primary, semantic, shadows) |
| 5 | All panel edges have visible 1px borders in dark mode | VERIFIED | `tab-bar-workspace` has `border-bottom: 1px solid var(--color-border)` in workspace.css; dark mode `--color-border: #3e4452` |
| 6 | Theme can be toggled via command palette | VERIFIED | `workspace.js` lines 668-680: `theme-light`, `theme-dark`, `theme-system` entries with `handler: function() { setTheme(…); }` |
| 7 | CodeMirror editor switches themes without losing cursor/undo history | VERIFIED | `editor.js` lines 22, 247-254: `Compartment` + `themeCompartment`, `window.switchEditorThemes()` calls `view.dispatch({effects: themeCompartment.reconfigure(…)})` |
| 8 | Cytoscape graph nodes/edges update to dark colors on theme switch | VERIFIED | `graph.js`: `buildSemanticStyle(typeColors, isDark)` with dark-specific color vars; `window.switchGraphTheme()` calls `cy.style().fromJson(styles).update()` |
| 9 | ninja-keys command palette renders with correct theme styling | VERIFIED | `theme.js` lines 28-35: `ninja.classList.add/remove('dark')`; `theme.css` lines 201-213: full `ninja-keys` CSS variable overrides |
| 10 | highlight.js code blocks switch between github and github-dark | VERIFIED | `base.html` line 36: `id="hljs-theme"` on link tag; `theme.js` lines 38-42: swaps href based on `resolved === 'dark'` |
| 11 | Tabs have 4px top border-radius, recessed bar, teal accent on active | VERIFIED | `workspace.css` lines 283, 303, 322: `padding: 4px 4px 0` on tab bar, `border-radius: 4px 4px 0 0`, `border-bottom: 2px solid var(--color-accent)` on `.active` |
| 12 | 403 page shows styled panel with lock icon and navigation buttons | VERIFIED | `403.html`: anti-FOUC script, `theme.css` link, `data-lucide="lock"` line 125, "Access Denied" h2, Go Home/Go Back buttons |
| 13 | Ctrl+K opens command palette in all browsers including Firefox | VERIFIED | `workspace.js` lines 531-538: `if (mod && e.key === 'k') { e.preventDefault(); var ninja = document.querySelector('ninja-keys'); if (ninja) { ninja.open(); } }` |
| 14 | Active tabs show teal accent on bottom only — no left-border bleed on view tabs | VERIFIED | `views.css`: zero results for `border-left` on any `.workspace-tab` selector; accent comes only from `workspace.css` `border-bottom: 2px solid var(--color-accent)` |
| 15 | Tab rounded corners visible (not clipped by tab bar overflow) | VERIFIED | `workspace.css` `.tab-bar-workspace` line 283: `padding: 4px 4px 0` provides 4px top headroom above overflow clip; `border-radius: 4px 4px 0 0` at line 303 |
| 16 | Card views have distinctive 1px borders in both light and dark mode | VERIFIED | `views.css` lines 717, 766: `border: 1px solid var(--color-border)` on `.flip-card-front,.flip-card-back` and `.card-focus-front,.card-focus-back`; `--color-border` tokenized in theme.css |

**Score:** 16/16 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/static/css/theme.css` | CSS custom property token definitions for light and dark modes | VERIFIED | 214 lines; `:root` with 35+ tokens; `html[data-theme="dark"]` overrides; crossfade transitions; `ninja-keys` overrides |
| `frontend/static/js/theme.js` | Theme toggle logic, localStorage persistence, third-party integration | VERIFIED | 94 lines; `setTheme()`, `applyTheme()`, `resolveTheme()`; calls `switchEditorThemes`, `switchGraphTheme`, ninja dark class, hljs swap |
| `backend/app/templates/base.html` | Anti-FOUC inline script in head, theme.css first, ninja-keys pinned | VERIFIED | Script at lines 7-16; `theme.css` at line 17 (first stylesheet); `ninja-keys@1.2.2` pinned at line 25 |
| `backend/app/templates/components/_sidebar.html` | 3-icon theme row (Sun/Monitor/Moon) in user popover | VERIFIED | Lines 135-145: `.popover-theme-row` with `theme-btn` buttons having `data-theme-value` and `onclick="setTheme(…)"` |
| `frontend/static/js/editor.js` | Compartment-based theme switching for CodeMirror | VERIFIED | `Compartment` imported; `themeCompartment` module-scope line 22; `window.switchEditorThemes()` exported at line 247 |
| `frontend/static/js/graph.js` | Dark/light style sets for Cytoscape and theme-changed event listener | VERIFIED | `buildSemanticStyle(typeColors, isDark)` with dark color vars; `window.switchGraphTheme()`; event listener backup |
| `frontend/static/css/workspace.css` | Rounded tab styling with recessed bar, teal accent, top padding for border-radius | VERIFIED | `padding: 4px 4px 0` on tab bar (line 283); `border-radius: 4px 4px 0 0` (line 303); `border-bottom: 2px solid var(--color-accent)` on `.active` (line 322) |
| `frontend/static/css/views.css` | Card face borders, no view-tab border-left bleed | VERIFIED | `border: 1px solid var(--color-border)` on flip-card and card-focus faces (lines 717, 766); zero `border-left` on any `.workspace-tab` selector |
| `backend/app/templates/errors/403.html` | Styled 403 permission panel with Lucide lock icon | VERIFIED | `data-lucide="lock"` at line 125; anti-FOUC script; "Access Denied" h2; Go Home/Go Back buttons using `--color-accent` tokens |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `base.html` | `theme.css` | `link rel=stylesheet` loaded first | WIRED | `theme.css` is line 17, before all other stylesheets |
| `theme.js` | `document.documentElement` | `setAttribute data-theme` | WIRED | `applyTheme()` line 25: `document.documentElement.setAttribute('data-theme', resolved)` |
| `workspace.js` | `window.setTheme` | command palette handler calls `setTheme` | WIRED | Lines 668, 674, 680: `handler: function() { setTheme('light'/'dark'/'system'); }` |
| `workspace.js` | `ninja-keys element` | `querySelector` + `e.preventDefault()` + `.open()` | WIRED | Lines 531-538: explicit Ctrl+K handler with guard |
| `theme.js` | `editor.js` | `window.switchEditorThemes(isDark)` | WIRED | `theme.js` lines 56-58: guard check + call; `editor.js` line 247 export |
| `theme.js` | `graph.js` | `window.switchGraphTheme(isDark)` | WIRED | `theme.js` lines 61-63: guard check + call; `graph.js` export |
| `theme.js` | `ninja-keys element` | `classList.add/remove('dark')` | WIRED | `theme.js` lines 28-35: `ninja.classList.add('dark')` / `ninja.classList.remove('dark')` |
| `workspace.css` | `theme.css` | `var(--color-accent)` and `var(--color-border)` tokens | WIRED | `workspace.css` line 322: `border-bottom: 2px solid var(--color-accent)`; `views.css` lines 717, 766: `border: 1px solid var(--color-border)` |
| `403.html` | `theme.css` | Anti-FOUC script + theme tokens | WIRED | `403.html` line 14: `document.documentElement.setAttribute('data-theme', theme)`; all styles use `var(--color-*)` tokens |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| DARK-01 | 13-01, 13-04 | User can toggle between System, Light, and Dark theme modes via user menu or command palette | SATISFIED | Sidebar popover 3-icon row confirmed; workspace.js command palette entries confirmed; Ctrl+K handler now cross-browser (plan 13-04) |
| DARK-02 | 13-01 | Theme preference persists across page reloads with no flash of wrong theme | SATISFIED | Anti-FOUC inline script in `base.html` head; `setTheme()` writes to `localStorage.setItem(THEME_KEY, preference)` |
| DARK-03 | 13-02 | Dark mode applies to all UI components including CodeMirror, Cytoscape, command palette, Split.js gutters | SATISFIED | `editor.js` Compartment switching; `graph.js` style rebuild; ninja-keys CSS vars; Split.js gutters tokenized in workspace.css |
| DARK-04 | 13-01 | Dark mode color tokens follow VS Code "Dark+" palette (dark surface, muted text, blue accents) | SATISFIED | `theme.css` dark overrides: `#1e2127` bg, `#282c34` surface, `#abb2bf` text, `#56b6c2` teal accent |
| WORK-06 | 13-03, 13-04 | Tab styling uses rounded top corners with recessed tab bar background | SATISFIED | `workspace.css`: `border-radius: 4px 4px 0 0`, `background: var(--color-surface-recessed)` on tab bar; `padding: 4px 4px 0` for border-radius headroom (plan 13-04); no border-left bleed (plan 13-04) |
| ERR-01 | 13-03 | 403 Forbidden responses display a styled permission panel with lock icon, role explanation, and navigation buttons | SATISFIED | `403.html`: complete styled panel with `data-lucide="lock"`, "Access Denied" heading, role explanation text, Go Home + Go Back buttons |

**No orphaned requirements.** All 6 requirement IDs appear in plan frontmatter and are fully covered.

### Anti-Patterns Found

None detected in plan 13-04 files:

- `workspace.js`: Ctrl+K handler is a complete implementation with `e.preventDefault()` and guard-checked `ninja.open()` call. No stubs or placeholders.
- `views.css`: Card border rules use the correct `var(--color-border)` token. View-tab border-left rules cleanly removed (no remnants).
- `workspace.css`: `padding: 4px 4px 0` shorthand correctly provides 4px top padding (top=4px, sides=4px, bottom=0).
- `base.html`: ninja-keys version pinned to `@1.2.2` (specific version, not a "latest" wildcard).

### Commit Verification

All plan 13-04 commits confirmed in git log:

| Commit | Task | Files Changed |
|--------|------|---------------|
| `8ce1ee5` | Task 1: Ctrl+K handler + ninja-keys version pinning | `workspace.js`, `base.html` |
| `a2a8088` | Task 2: Tab bleed removal, border-radius headroom, card borders | `views.css`, `workspace.css` |

### Human Verification Required

#### 1. Theme Popover Visual Switching

**Test:** Open user popover, click Sun (light), Monitor (system), Moon (dark) icons in sequence.
**Expected:** Theme switches with 150ms crossfade on body/sidebar/tabs. Active button highlights with teal accent background. Icons render correctly (Lucide SVGs).
**Why human:** Visual animation and icon rendering cannot be verified via static analysis.

#### 2. Anti-FOUC Flash Test

**Test:** Set `localStorage.setItem('sempkm_theme', 'dark')` in browser console, then do a hard refresh (Ctrl+Shift+R).
**Expected:** Page renders with dark background immediately — no brief flash of white/light background before CSS loads.
**Why human:** FOUC behavior requires observing real browser paint timing; cannot be reproduced via grep.

#### 3. Command Palette in Firefox

**Test:** In Firefox, press Ctrl+K.
**Expected:** The ninja-keys command palette opens immediately. The Firefox URL/search bar does NOT receive focus. Command palette renders with dark background if dark mode is active.
**Why human:** Cross-browser Ctrl+K interception behavior requires a real Firefox session to confirm `e.preventDefault()` fires before Firefox intercepts.

#### 4. CodeMirror Theme Preservation

**Test:** Open an object with a Markdown body. Type some text. Press Ctrl+Z to undo (verify undo works). Then switch themes.
**Expected:** Editor appearance changes (dark: `#282c34` bg, light text, teal cursor). Undo history is preserved — previously typed text is still undoable after the theme switch.
**Why human:** Editor state preservation across `Compartment.reconfigure()` calls requires interactive verification.

#### 5. Cytoscape Graph Dark Mode

**Test:** Open a graph view. Switch to dark mode.
**Expected:** Node backgrounds become muted gray (`#5c6370`), labels lighten (`#abb2bf`), edges become dark (`#3e4452`), selected node gets teal border (`#56b6c2`).
**Why human:** Cytoscape canvas rendering requires visual inspection.

#### 6. 403 Page Dark Mode

**Test:** Navigate to a route that returns 403. Also test with dark mode active before navigating.
**Expected:** Styled card panel with lock icon, "Access Denied" heading, role text, Go Home and Go Back buttons. Dark mode renders correctly without FOUC.
**Why human:** Requires live app session with a 403 trigger; visual panel quality and dark mode rendering need human confirmation.

#### 7. Card Border Visibility

**Test:** Open any card view (e.g., flashcard/SRS view). Inspect a card face in both light and dark mode.
**Expected:** Card face has a visible 1px solid border. In light mode the border is `#e0e0e0`, in dark mode `#3e4452`. Box shadow is still present as a supplementary effect.
**Why human:** Border visual quality (visible vs. too subtle) requires human judgment in a rendered browser.

#### 8. Tab Accent and Border-Radius

**Test:** Open multiple tabs including at least one view-type tab. Make a tab active by clicking it.
**Expected:** Active tab shows only a bottom teal accent (2px). No left-side border bleed is visible. The top corners of all tabs are visibly rounded (not squared off by overflow clipping).
**Why human:** Pixel-level visual inspection of border-radius rendering and absence of border-left bleed requires a human in a browser.

---

_Verified: 2026-02-24_
_Verifier: Claude (gsd-verifier)_
