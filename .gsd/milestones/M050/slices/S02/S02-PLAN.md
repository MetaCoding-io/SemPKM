# S02: Toolbar Cleanup + View Polish

**Goal:** Clean up remaining view polish issues: calendar dark mode nav icons visible, timeline popover dismisses on Escape/click-outside.
**Demo:** After this: View toolbar is clean — no View Variants dropdown. Calendar dark mode shows visible nav buttons. Timeline popover dismisses on Escape/click-outside.

## Tasks
- [x] **T01: Added 8 FC6 button custom properties to dark mode .fc block and removed 3 redundant direct-property override selectors for visible calendar nav icons** — ## Description

The FullCalendar 6.1.17 prev/next nav buttons use an icon font (`fcicons`) where the icon color is inherited from the button's `color` property. In dark mode, FC6's `.fc .fc-button-primary { color: var(--fc-button-text-color) }` wins the specificity battle over the direct `color` override in `[data-theme="dark"] .fc .fc-button`. The fix is to set FC6's custom properties (`--fc-button-text-color`, `--fc-button-bg-color`, etc.) in the existing dark mode block, then simplify or remove the now-redundant direct-property overrides.

## Steps

1. Read `frontend/static/css/views.css` lines 1376–1412 (the dark mode FC block).
2. Add FC6 button custom properties to the `[data-theme="dark"] .fc` block (lines ~1376):
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
3. Remove the now-redundant direct-property override blocks:
   - `[data-theme="dark"] .fc .fc-button` (lines ~1388–1392) — custom properties handle bg, border, color
   - `[data-theme="dark"] .fc .fc-button:hover` (lines ~1394–1396) — custom property handles hover bg
   - `[data-theme="dark"] .fc .fc-button-active` (lines ~1398–1402) — custom property handles active state
4. Verify with grep that the custom properties are set and the direct overrides are gone.

## Must-Haves

- [ ] `--fc-button-text-color` set in dark mode `.fc` block
- [ ] `--fc-button-bg-color` set in dark mode `.fc` block
- [ ] `--fc-button-active-bg-color` set in dark mode `.fc` block
- [ ] No remaining `[data-theme="dark"] .fc .fc-button {` direct-property block (custom properties replace it)

## Verification

- `grep -c 'fc-button-text-color' frontend/static/css/views.css` returns >= 1
- `grep -c 'fc-button-bg-color' frontend/static/css/views.css` returns >= 1
- `grep -c 'fc-button-active-text-color' frontend/static/css/views.css` returns >= 1
- The `[data-theme="dark"] .fc` block contains all 8 button custom properties
  - Estimate: 15m
  - Files: frontend/static/css/views.css
  - Verify: grep -c 'fc-button-text-color' frontend/static/css/views.css && grep -c 'fc-button-bg-color' frontend/static/css/views.css && grep -c 'fc-button-active-text-color' frontend/static/css/views.css
- [x] **T02: Added click-outside and Escape dismiss handlers for Frappe Gantt popup in timeline view with dockview cleanup registration** — ## Description

Frappe Gantt 1.2.2 shows a `.popup-wrapper` on bar click but has no built-in dismiss mechanism. Users must click another bar to close the popup — there's no Escape or click-outside support. The fix adds document-level event listeners after `new Gantt(...)` and registers cleanup via `window.registerCleanup` for the dockview panel destroy lifecycle.

The Gantt instance is a local variable inside the `initTimeline()` function's `.then()` callback, so the dismiss handlers must be added in that same scope, after the `new Gantt(...)` call.

## Steps

1. Read `backend/app/templates/browser/timeline_view.html` to confirm the Gantt init location and popup structure.
2. After the `new Gantt(...)` call (around line 93) and the `SemPKM.debug(...)` log line, add:
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
           var pw = el.querySelector('.popup-wrapper');
           if (pw && !pw.classList.contains('hide')) {
               gantt.hide_popup();
           }
       }
   }
   document.addEventListener('click', onDocClick);
   document.addEventListener('keydown', onDocKeydown);
   ```
3. After the event listeners, add cleanup registration:
   ```javascript
   if (typeof window.registerCleanup === 'function') {
       window.registerCleanup('timeline-container', function() {
           document.removeEventListener('click', onDocClick);
           document.removeEventListener('keydown', onDocKeydown);
       });
   }
   ```
4. The click handler excludes `.bar-wrapper` clicks to avoid immediately dismissing the popup when clicking a bar (which opens it). The Escape handler checks that the popup is visible before calling `hide_popup()` to avoid no-op calls.
5. Verify with grep that `hide_popup`, `Escape`, and `registerCleanup` all appear in the template.

## Must-Haves

- [ ] Document `click` listener calls `gantt.hide_popup()` when clicking outside `.popup-wrapper` and outside `.bar-wrapper`
- [ ] Document `keydown` listener calls `gantt.hide_popup()` on Escape when popup is visible
- [ ] Both listeners registered via `document.addEventListener`
- [ ] Cleanup registered via `window.registerCleanup('timeline-container', ...)` to remove both listeners

## Verification

- `grep -c 'hide_popup' backend/app/templates/browser/timeline_view.html` returns >= 2 (click + Escape handlers)
- `grep -c 'Escape' backend/app/templates/browser/timeline_view.html` returns >= 1
- `grep -c 'registerCleanup' backend/app/templates/browser/timeline_view.html` returns >= 1
  - Estimate: 15m
  - Files: backend/app/templates/browser/timeline_view.html
  - Verify: grep -c 'hide_popup' backend/app/templates/browser/timeline_view.html && grep -c 'Escape' backend/app/templates/browser/timeline_view.html && grep -c 'registerCleanup' backend/app/templates/browser/timeline_view.html
