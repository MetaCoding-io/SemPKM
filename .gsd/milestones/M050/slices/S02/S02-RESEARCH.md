# S02 Research: Toolbar Cleanup + View Polish

**Date:** 2026-04-05
**Depth:** Light — two isolated CSS/JS fixes on known code

## Summary

S01 already delivered the View Variants removal and pill-to-dropdown migration. S02 has exactly two remaining deliverables:

1. **Calendar dark mode nav icons invisible** — FullCalendar 6.1.17 uses an icon font (`fcicons`) for prev/next chevrons. Icon color comes from `color: var(--fc-button-text-color)` on `.fc-button-primary`. The dark mode block in `views.css` overrides `color` directly on `.fc .fc-button`, but FC6's `.fc .fc-button-primary` rule wins the specificity battle via the CSS custom property. **Fix:** Add `--fc-button-text-color`, `--fc-button-bg-color`, `--fc-button-border-color`, and hover/active variants to the `[data-theme="dark"] .fc` custom properties block.

2. **Timeline popover doesn't dismiss on Escape/click-outside** — Frappe Gantt 1.2.2 shows a `.popup-wrapper` (positioned absolute inside the gantt container) on bar click. It has no built-in click-outside or Escape dismiss. The Gantt instance has `hide_popup()`. **Fix:** After `new Gantt(...)`, attach a document-level `click` listener (dismiss if click target is outside `.popup-wrapper`) and a `keydown` listener for Escape. Register cleanup via `window.registerCleanup` keyed to `timeline-container`.

## Recommendation

Two tasks:

**T01: Calendar dark mode nav icon fix** — CSS-only change in `views.css`. Override FC6 custom properties (`--fc-button-text-color`, `--fc-button-bg-color`, `--fc-button-border-color`, hover/active variants) in the existing `[data-theme="dark"] .fc` block. Remove the now-redundant `.fc .fc-button` direct-property overrides (they're shadowed by the custom properties).

**T02: Timeline popover dismiss** — JS change in `timeline_view.html`. After the `new Gantt(...)` call inside `initTimeline()`, add click-outside and Escape handlers that call `gantt.hide_popup()`. Register cleanup to remove the document-level listeners when the panel is destroyed.

## Implementation Landscape

### Calendar Dark Mode (T01)

| What | Where | Notes |
|------|-------|-------|
| Dark mode FC overrides | `frontend/static/css/views.css:1376-1405` | Existing `[data-theme="dark"] .fc` block has page/border/event colors but NOT button text/bg custom properties |
| FC6 button custom properties | Built into `fullcalendar-f9fa1add.min.js` | Defaults: `--fc-button-text-color: #fff`, `--fc-button-bg-color: #2c3e50`, `--fc-button-border-color: #2c3e50`, `--fc-button-hover-bg-color: #1e2b37`, `--fc-button-active-bg-color: #1a252f` |
| Icon mechanism | FC6 icon font `fcicons` via `::before` pseudo-elements | `fc-icon-chevron-left` = `\e900`, `fc-icon-chevron-right` = `\e901`. Color inherited from parent button's `color` property |
| Current dark button rule | `[data-theme="dark"] .fc .fc-button` sets `background`, `border-color`, `color` directly | Loses to `.fc .fc-button-primary { color: var(--fc-button-text-color) }` because the custom property resolves independently |

**Fix approach:** Add to existing `[data-theme="dark"] .fc` block:
```css
--fc-button-text-color: var(--color-text);
--fc-button-bg-color: var(--color-bg-secondary);
--fc-button-border-color: var(--color-border);
--fc-button-hover-bg-color: var(--color-bg-hover);
--fc-button-hover-border-color: var(--color-border);
--fc-button-active-bg-color: var(--color-accent);
--fc-button-active-border-color: var(--color-accent);
--fc-button-active-text-color: var(--color-on-accent);
```
Then the direct-property overrides on `.fc .fc-button`, `.fc-button:hover`, `.fc-button-active` can be simplified or removed since the custom properties now handle everything.

### Timeline Popover Dismiss (T02)

| What | Where | Notes |
|------|-------|-------|
| Timeline template | `backend/app/templates/browser/timeline_view.html` | Inline `<script>` with `initTimeline()` function |
| Gantt instance | `var gantt = new Gantt(...)` at line 93 | Local variable inside `initTimeline()` — dismiss handler must be added in same scope |
| Popup structure | `.popup-wrapper` inside `.gantt-container` | Has `.hide` class when hidden. `gantt.hide_popup()` toggles it |
| Popup trigger | `mouseup` on bar (click mode, which is the default `popup_on: "click"`) | No built-in dismiss mechanism |
| Cleanup pattern | `window.registerCleanup(elementId, fn)` from `cleanup.js` | Timeline template currently has NO cleanup registration — should add it |
| dockview panel lifecycle | Panel `dispose()` calls `window.runCleanup(el.id)` on the panel root | The `timeline-container` ID is the target for cleanup registration |

**Fix approach:** After `new Gantt(...)`:
```javascript
// Dismiss popup on click-outside
function onDocClick(e) {
    var pw = el.querySelector('.popup-wrapper');
    if (pw && !pw.classList.contains('hide') && !pw.contains(e.target) && !e.target.closest('.bar-wrapper')) {
        gantt.hide_popup();
    }
}
// Dismiss popup on Escape
function onDocKeydown(e) {
    if (e.key === 'Escape') {
        gantt.hide_popup();
    }
}
document.addEventListener('click', onDocClick);
document.addEventListener('keydown', onDocKeydown);

// Register cleanup for dockview panel lifecycle
if (typeof window.registerCleanup === 'function') {
    window.registerCleanup('timeline-container', function() {
        document.removeEventListener('click', onDocClick);
        document.removeEventListener('keydown', onDocKeydown);
    });
}
```

The click handler excludes `.bar-wrapper` clicks to avoid dismissing the popup immediately when clicking a bar (which opens it).

### Verification

- **T01:** Visual — open calendar view in dark mode, verify prev/next chevron icons are visible. Automated: grep for `--fc-button-text-color` in `views.css` dark mode block.
- **T02:** Behavioral — open timeline, click a bar to show popup, press Escape → popup disappears. Click outside → popup disappears. Automated: grep for `hide_popup\|Escape` in timeline_view.html.

### Skill Discovery

No external technologies — FullCalendar and Frappe Gantt are already bundled. No skill search needed.
