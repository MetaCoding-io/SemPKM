---
estimated_steps: 3
estimated_files: 1
skills_used:
  - best-practices
---

# T04: Frontend auto-switch handler — SSE persona_switched event

**Slice:** S02 — Auto-Persona Rules Engine & Settings UI
**Milestone:** M037

## Description

Add a `persona_switched` event handler to the existing SSE EventSource in context-indicator.js. When the backend broadcasts a persona switch (triggered by rule evaluation in T02), the frontend calls `window.switchPersona(id)` to apply the workspace layout change and shows a brief notification indicating which rule triggered the switch. This closes the user-visible loop: context update → rule match → persona switch → UI update.

## Steps

1. Add `persona_switched` event listener to `frontend/static/js/context-indicator.js`:
   - In the `_initSSE()` function (or equivalent), after the existing `context_update` and `context_stale` listeners, add:
   ```javascript
   _sse.addEventListener('persona_switched', function (e) {
       try {
           var data = JSON.parse(e.data);
           var personaId = data.persona_id;
           var personaName = data.persona_name || 'Unknown';
           var ruleName = data.rule_name || '';
           
           if (typeof window.switchPersona === 'function') {
               window.switchPersona(personaId);
               _showAutoSwitchNotice(personaName, ruleName);
           } else {
               console.warn('[context-indicator] window.switchPersona not available');
           }
       } catch (err) {
           console.error('[context-indicator] persona_switched parse error:', err);
       }
   });
   ```
   - The `window.switchPersona` function is already exposed in `workspace.js` (confirmed: `window.switchPersona = switchPersona;` exists)

2. Add a `_showAutoSwitchNotice(personaName, ruleName)` function:
   - Create a small toast notification that appears briefly (3-4 seconds) near the context indicator or at the top of the workspace
   - Content: "Auto-switched to **{personaName}**" with optional rule name in smaller text
   - Use a simple DOM-created div with CSS animation (fade in, stay, fade out) — no dependency on a toast library
   - Style: subtle, non-blocking, matches the existing UI palette (use CSS variables from the theme)
   - Add CSS for the toast in the same file as an inline style element, or append a small block to `context-indicator.css`

3. Add toast CSS to `frontend/static/css/context-indicator.css`:
   - `.context-auto-switch-toast` — fixed/absolute positioned, semi-transparent background, rounded corners, z-index above workspace but below modals
   - Fade-in + fade-out keyframe animation
   - Auto-remove after animation completes (JS sets `setTimeout` to remove the DOM element)

## Must-Haves

- [ ] `persona_switched` SSE event listener registered on the existing EventSource
- [ ] Calls `window.switchPersona(persona_id)` on receiving the event
- [ ] Graceful fallback if `window.switchPersona` is undefined (log warning, don't crash)
- [ ] Brief toast notification showing persona name on auto-switch
- [ ] Toast auto-dismisses after ~3 seconds
- [ ] JSON parse errors caught and logged

## Verification

- Browser test: POST a context update matching a rule → observe persona_switched SSE event in browser Network tab → verify workspace persona actually changes → verify toast notification appears and auto-dismisses
- `grep -q "persona_switched" frontend/static/js/context-indicator.js` — handler exists
- `grep -q "switchPersona" frontend/static/js/context-indicator.js` — calls the switch function

## Inputs

- `frontend/static/js/context-indicator.js` — existing SSE EventSource setup (add persona_switched handler)
- `frontend/static/js/workspace.js` — exposes `window.switchPersona` (no changes needed, just consumed)
- `frontend/static/css/context-indicator.css` — existing indicator styles (add toast styles)

## Expected Output

- `frontend/static/js/context-indicator.js` — modified with persona_switched handler and toast function
- `frontend/static/css/context-indicator.css` — modified with auto-switch toast styles

## Observability Impact

- **New browser console signals:** `[context-indicator] window.switchPersona not available` warning when the workspace.js persona function hasn't loaded — indicates a script loading order issue. `[context-indicator] persona_switched parse error: <err>` when SSE payload is malformed.
- **Visual signal:** Auto-switch toast (`.context-auto-switch-toast`) appears at top-right of viewport for 3 seconds — visible confirmation that the SSE→switchPersona→UI loop completed. If the toast never appears after a context update that should trigger a rule, inspect the SSE stream in the Network tab for `persona_switched` events.
- **DOM inspection:** `document.querySelector('.context-auto-switch-toast')` returns the toast element while it's visible (null after auto-dismiss). Useful for E2E tests.
- **Failure visibility:** If `window.switchPersona` is undefined, the persona won't change but the console warning is logged — the toast is suppressed (no false positive UI signal).
