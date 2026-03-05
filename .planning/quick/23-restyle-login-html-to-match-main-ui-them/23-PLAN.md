---
phase: 23-restyle-login
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/static/login.html
  - frontend/static/css/style.css
autonomous: true
requirements: [QUICK-23]
must_haves:
  truths:
    - "Login page respects user's stored theme preference (light/dark/system)"
    - "Login page has a visually polished background instead of flat white"
    - "Login page card feels integrated with the main app design language"
  artifacts:
    - path: "frontend/static/login.html"
      provides: "Theme-aware login page with anti-FOUC script"
      contains: "sempkm_theme"
    - path: "frontend/static/css/style.css"
      provides: "Enhanced auth page styles"
      contains: "auth-container"
  key_links:
    - from: "frontend/static/login.html"
      to: "frontend/static/css/theme.css"
      via: "link stylesheet"
      pattern: "theme\\.css"
---

<objective>
Restyle the login page to feel like part of the SemPKM application rather than a plain white page.

Purpose: The login page is the first thing users see. It should reflect the app's polished dark-theme-capable aesthetic.
Output: A theme-aware login page with subtle background treatment, better visual hierarchy, and an accent-colored brand mark.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/static/login.html
@frontend/static/css/style.css (lines 1909-1997 — auth section)
@frontend/static/css/theme.css
@frontend/static/js/theme.js
@backend/app/templates/base.html (lines 1-15 — anti-FOUC pattern)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add theme awareness and visual polish to login page</name>
  <files>frontend/static/login.html, frontend/static/css/style.css</files>
  <action>
Two files to modify:

**login.html changes:**

1. Add `class="no-transition"` to the `<html>` tag (matches base.html pattern).

2. Add the anti-FOUC inline script in `<head>` BEFORE any stylesheet links. Copy the exact pattern from base.html / 403.html:
```js
<script>
  var s=localStorage.getItem('sempkm_theme');
  var t=(s==='dark')?'dark':(s==='light')?'light':
    (window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  document.documentElement.setAttribute('data-theme',t);
</script>
```

3. Add `<link rel="stylesheet" href="/css/theme.css">` BEFORE the existing style.css link (theme.css defines the CSS variables that style.css consumes).

4. Add `<script src="/js/theme.js"></script>` after the existing script tags in `<head>` so the full theme system (including system-preference media query listener) runs on the login page too.

5. Replace the plain text brand `<div class="auth-brand">SemPKM</div>` with an SVG-based brand mark — a small inline SVG icon (a simple graph/node icon representing semantic knowledge) followed by the text. Use an inline SVG consisting of 3 small circles connected by lines (like a mini knowledge graph), sized at 28x28px, colored with `currentColor` so it inherits the accent color. Structure:
```html
<div class="auth-brand">
  <svg class="auth-brand-icon" width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
    <circle cx="14" cy="6" r="3" fill="currentColor" stroke="none"/>
    <circle cx="6" cy="22" r="3" fill="currentColor" stroke="none"/>
    <circle cx="22" cy="22" r="3" fill="currentColor" stroke="none"/>
    <line x1="14" y1="9" x2="6" y2="19"/>
    <line x1="14" y1="9" x2="22" y2="19"/>
    <line x1="9" y1="22" x2="19" y2="22"/>
  </svg>
  SemPKM
</div>
```

**style.css auth section changes (lines 1909-1997):**

6. Update `.auth-container` background from flat `var(--color-bg)` to a subtle radial gradient that adds visual interest:
```css
.auth-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 1.5rem;
  background:
    radial-gradient(ellipse at 20% 50%, var(--color-accent-subtle) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, var(--color-primary-subtle) 0%, transparent 50%),
    var(--color-bg);
}
```

7. Update `.auth-card` to add elevated shadow and slightly more padding:
```css
.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 2.5rem 2rem 2rem;
  box-shadow: var(--shadow-elevated);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}
```

8. Update `.auth-brand` to be a flex row with the icon, using accent color:
```css
.auth-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.3rem;
  color: var(--color-accent);
  letter-spacing: -0.02em;
  margin-bottom: 0.25rem;
}
```
Note: changed from `--color-primary` to `--color-accent` to match the app's teal accent theme.

9. Add a new `.auth-brand-icon` rule:
```css
.auth-brand-icon {
  flex-shrink: 0;
}
```

10. Add a subtle top accent bar on the card via pseudo-element:
```css
.auth-card::before {
  content: '';
  display: block;
  width: 40px;
  height: 3px;
  background: var(--color-accent);
  border-radius: 2px;
  margin-bottom: 1.25rem;
}
```

11. Polish the submit button to use accent color instead of primary (matching the brand):
```css
.auth-btn {
  width: 100%;
  padding: 0.65rem 1rem;
  font-size: 0.95rem;
  margin-top: 0.5rem;
  border-radius: 8px;
  background: var(--color-accent);
  border: none;
  color: var(--color-on-accent);
  cursor: pointer;
  font-weight: 500;
  transition: background 0.15s ease;
}

.auth-btn:hover {
  background: var(--color-accent-hover);
}
```

12. Style the input field for better integration:
```css
.auth-card input[type="text"],
.auth-card input[type="email"] {
  font-size: 0.95rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface-recessed);
  color: var(--color-text);
  width: 100%;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.auth-card input[type="text"]:focus,
.auth-card input[type="email"]:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-focus-shadow);
}
```

13. Add `.auth-container` to the transition list in theme.css crossfade section (line ~241 area in theme.css) — actually, just add it to the style.css auth section with:
```css
.auth-container,
.auth-card,
.auth-card input {
  transition: background-color 150ms ease, color 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
}
```

All colors use existing CSS variables from theme.css so dark mode works automatically via `html[data-theme="dark"]` overrides already in place.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && grep -q "sempkm_theme" frontend/static/login.html && grep -q "theme.css" frontend/static/login.html && grep -q "radial-gradient" frontend/static/css/style.css && grep -q "auth-brand-icon" frontend/static/css/style.css && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>
    - Login page loads with correct theme (dark/light) from localStorage on first paint (no flash)
    - Background shows subtle gradient blobs instead of flat color
    - Card has elevated shadow, accent top bar, rounded corners
    - Brand shows graph icon + "SemPKM" in accent color
    - Submit button uses accent color with hover state
    - Input fields have recessed background, accent focus ring
    - All styling works in both light and dark themes via CSS variables
  </done>
</task>

</tasks>

<verification>
1. Open http://localhost:3901/login in browser — page should show polished card with gradient background
2. Open DevTools, run `document.documentElement.setAttribute('data-theme', 'dark')` — all elements should switch to dark palette
3. Run `document.documentElement.setAttribute('data-theme', 'light')` — returns to light palette
4. Verify no inline styles on SVG icon per CLAUDE.md guidelines (icon uses currentColor)
</verification>

<success_criteria>
- Login page detects and applies stored theme preference on load without FOUC
- Background has subtle gradient treatment in both light and dark modes
- Card has elevated shadow, accent bar, and graph icon brand mark
- All colors come from CSS variables (no hardcoded hex in login.html)
- Visual quality matches the polish level of the main workspace UI
</success_criteria>

<output>
After completion, create `.planning/quick/23-restyle-login-html-to-match-main-ui-them/23-SUMMARY.md`
</output>
