---
estimated_steps: 46
estimated_files: 1
skills_used: []
---

# T02: Add timeline popover dismiss on Escape and click-outside with cleanup registration

## Description

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

## Inputs

- ``backend/app/templates/browser/timeline_view.html` — existing timeline template with Gantt init at line 93, no popup dismiss or cleanup logic`

## Expected Output

- ``backend/app/templates/browser/timeline_view.html` — click-outside dismiss, Escape dismiss, and registerCleanup added after Gantt init`

## Verification

grep -c 'hide_popup' backend/app/templates/browser/timeline_view.html && grep -c 'Escape' backend/app/templates/browser/timeline_view.html && grep -c 'registerCleanup' backend/app/templates/browser/timeline_view.html
