---
estimated_steps: 39
estimated_files: 2
skills_used: []
---

# T02: Body editor writing surface with CSS-token-driven CM6 theme

Replace hardcoded hex colors in the CM6 editor themes with CSS `var()` tokens, collapse dual light/dark theme into a single definition, and add writing-surface polish.

## 1. Collapse CM6 Themes to Single Definition

Currently `editor.js` defines two separate themes (`darkEditorTheme` at line 18, `lightEditorTheme` at line 26) with hardcoded hex values. Since CM6's `EditorView.theme()` accepts CSS including `var()` references, a single theme using CSS tokens auto-adapts when `data-theme` changes on `<html>`.

**Replace both theme definitions with a single unified theme:**
```javascript
var editorTheme = EditorView.theme({
  '&': { backgroundColor: 'var(--color-surface)', color: 'var(--color-text)' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--color-accent)' },
  '.cm-gutters': {
    backgroundColor: 'var(--color-surface-raised)',
    color: 'var(--color-text-faint)',
    borderRight: '1px solid var(--color-border)'
  },
  '.cm-activeLineGutter': { backgroundColor: 'var(--color-surface-recessed)' },
  '.cm-activeLine': { backgroundColor: 'var(--color-surface-recessed)' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
    backgroundColor: 'var(--color-surface-hover)'
  }
});
```

**Remove `themeCompartment` machinery:**
- Delete the `Compartment` import from the CM_Markdown destructure (line 13)
- Delete `themeCompartment` variable (line 16)
- Delete `darkEditorTheme` and `lightEditorTheme` definitions (lines 18-31)
- Delete `getCurrentTheme()` function (lines 35-38)
- Replace `themeCompartment.of(getCurrentTheme())` in `initEditor()` (line 74) with just `editorTheme`
- Delete `switchEditorThemes()` function (lines 238-250) — CSS vars auto-adapt, no reconfigure needed
- Set `window.SemPKM.switchEditorThemes` to a no-op function or remove it entirely

**Check callers of `switchEditorThemes`:** Search for all references. If `theme.js` or another file calls `switchEditorThemes(isDark)` on theme toggle, that call becomes a no-op (CSS vars handle it). Either remove the call or leave the no-op stub.

## 2. Writing Surface CSS Polish

In `workspace.css`, enhance `.codemirror-container` and CM6 elements:

- Change `.codemirror-container` border from `1px solid var(--color-border)` to `1px solid var(--color-border-subtle)` for a softer look
- Add `.codemirror-container .cm-content { padding-left: 8px; }` for breathing room
- Add `.codemirror-container .cm-editor { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; }` for proportional prose font

## Constraints
- After changes, `grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/static/js/editor.js` must return 0 results
- K014: No standalone hex values — all colors via CSS var() tokens
- The `Compartment` import may still be needed if other code uses compartments — check before removing
- The `{ dark: true }` option on the old theme affected CM6's base styles. The unified theme should omit this since both modes use the same CSS rule — CM6 will use its default base which works with CSS variables

## Inputs

- ``frontend/static/js/editor.js` — current dual theme definitions (lines 16-38, 74, 238-250)`
- ``frontend/static/css/workspace.css` — `.codemirror-container` styling (line 2550)`
- ``frontend/static/css/theme.css` — CSS token definitions for `--color-surface`, `--color-text`, `--color-surface-raised`, etc.`

## Expected Output

- ``frontend/static/js/editor.js` — single unified CM6 theme using CSS var() tokens, themeCompartment removed, switchEditorThemes is no-op or removed`
- ``frontend/static/css/workspace.css` — softer editor border, left padding on `.cm-content`, proportional font on `.cm-editor``

## Verification

grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/static/js/editor.js | grep -v '// ' | wc -l | grep -q '^0$' && grep -q 'color-surface' frontend/static/js/editor.js && grep -q 'border-subtle\|border-faint' frontend/static/css/workspace.css && echo 'PASS'
