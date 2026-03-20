---
estimated_steps: 5
estimated_files: 2
---

# T03: Add dismissible CTA banner conditional on demo_mode

**Slice:** S03 — Demo tour + dashboard + CTA banner
**Milestone:** M025

## Description

Add a "Try SemPKM" call-to-action banner to the workspace that appears only in demo mode. The banner is dismissible and shows after the demo tour completes or on subsequent visits. It provides a link to the GitHub repository for self-hosting instructions.

**Skills:** Follow CLAUDE.md rules for Lucide icons in flex containers (CSS sizing, flex-shrink: 0, stroke: currentColor).

## Steps

1. **Add CTA banner HTML to workspace.html** — Inside the `{% if demo_mode %}` block (added by T01), add a banner div after the auto-start script. Place it just before `{% endblock %}` at the end of the content block. Structure:
   ```html
   <div class="demo-cta-banner" id="demo-cta-banner" style="display: none;">
     <div class="demo-cta-content">
       <i data-lucide="rocket"></i>
       <div class="demo-cta-text">
         <strong>Ready to try SemPKM?</strong>
         <span>Install with Docker in 2 minutes. Self-hosted, privacy-first personal knowledge management.</span>
       </div>
       <a href="https://github.com/SemPKM/SemPKM" target="_blank" rel="noopener" class="demo-cta-button">
         <i data-lucide="github"></i>
         Get Started
       </a>
       <button class="demo-cta-dismiss" onclick="dismissDemoCta()" title="Dismiss">
         <i data-lucide="x"></i>
       </button>
     </div>
   </div>
   ```
   The banner starts hidden (`display: none`) and is shown via JavaScript.

2. **Add CTA banner show/dismiss JavaScript** — In the same `{% if demo_mode %}` script block in workspace.html (or a new one), add:
   ```javascript
   function dismissDemoCta() {
     var banner = document.getElementById('demo-cta-banner');
     if (banner) {
       banner.classList.add('demo-cta-hiding');
       setTimeout(function() { banner.style.display = 'none'; }, 300);
     }
     localStorage.setItem('sempkm_demo_cta_dismissed', '1');
   }

   function showDemoCta() {
     if (localStorage.getItem('sempkm_demo_cta_dismissed') === '1') return;
     var banner = document.getElementById('demo-cta-banner');
     if (banner) {
       banner.style.display = '';
       // Re-initialize Lucide icons inside the banner
       if (window.lucide) lucide.createIcons({ nodes: [banner] });
     }
   }

   // Show CTA if tour is already done (returning visitor)
   if (localStorage.getItem('sempkm_demo_tour_done') === '1') {
     setTimeout(showDemoCta, 500);
   }

   // Listen for tour completion event (first-time visitor)
   document.addEventListener('sempkm:demo-tour-done', function() {
     setTimeout(showDemoCta, 500);
   });
   ```

3. **Add CSS styles for `.demo-cta-banner`** in `frontend/static/css/workspace.css`:
   ```css
   /* Demo CTA Banner */
   .demo-cta-banner {
     position: fixed;
     bottom: 0;
     left: 0;
     right: 0;
     z-index: 50;
     background: var(--color-bg-elevated, #1e293b);
     border-top: 1px solid var(--color-border, #334155);
     padding: 12px 24px;
     animation: slideUpCta 0.3s ease-out;
   }

   .demo-cta-banner.demo-cta-hiding {
     animation: slideDownCta 0.3s ease-in forwards;
   }

   @keyframes slideUpCta {
     from { transform: translateY(100%); }
     to { transform: translateY(0); }
   }

   @keyframes slideDownCta {
     from { transform: translateY(0); }
     to { transform: translateY(100%); }
   }

   .demo-cta-content {
     display: flex;
     align-items: center;
     gap: 16px;
     max-width: 960px;
     margin: 0 auto;
   }

   .demo-cta-content > svg {
     width: 24px;
     height: 24px;
     flex-shrink: 0;
     stroke: var(--color-accent, #3b82f6);
   }

   .demo-cta-text {
     flex: 1;
     min-width: 0;
   }

   .demo-cta-text strong {
     color: var(--color-text, #f1f5f9);
     display: block;
     margin-bottom: 2px;
   }

   .demo-cta-text span {
     color: var(--color-text-muted, #94a3b8);
     font-size: 0.875rem;
   }

   .demo-cta-button {
     display: inline-flex;
     align-items: center;
     gap: 6px;
     padding: 8px 16px;
     background: var(--color-accent, #3b82f6);
     color: white;
     border-radius: 6px;
     text-decoration: none;
     font-weight: 500;
     font-size: 0.875rem;
     white-space: nowrap;
     flex-shrink: 0;
   }

   .demo-cta-button:hover {
     filter: brightness(1.1);
   }

   .demo-cta-button svg {
     width: 16px;
     height: 16px;
     flex-shrink: 0;
     stroke: currentColor;
   }

   .demo-cta-dismiss {
     background: none;
     border: none;
     cursor: pointer;
     padding: 4px;
     color: var(--color-text-muted, #94a3b8);
     flex-shrink: 0;
   }

   .demo-cta-dismiss:hover {
     color: var(--color-text, #f1f5f9);
   }

   .demo-cta-dismiss svg {
     width: 16px;
     height: 16px;
     flex-shrink: 0;
     stroke: currentColor;
   }
   ```

4. **Ensure Lucide icons render** — The banner uses `data-lucide` icons (rocket, github, x). Since the banner is injected into the DOM outside the normal htmx flow, call `lucide.createIcons({ nodes: [banner] })` after making the banner visible (already handled in step 2's `showDemoCta()` function).

5. **Verify** — Check that:
   - CSS file contains `.demo-cta-banner` styles
   - Template contains the banner div conditional on `demo_mode`
   - Banner has proper z-index (50, below ninja-keys at 100+)
   - Lucide icon SVGs use CSS sizing (not inline styles) per CLAUDE.md rules
   - Dismiss button sets localStorage flag

## Must-Haves

- [ ] CTA banner div in workspace.html conditional on `{% if demo_mode %}`
- [ ] Banner starts hidden, shown after tour completion or on returning visits
- [ ] Dismiss button hides banner and sets localStorage flag to prevent re-showing
- [ ] CSS follows CLAUDE.md Lucide icon rules (flex-shrink: 0, CSS sizing, stroke: currentColor)
- [ ] z-index: 50 (below ninja-keys modal layer)
- [ ] `sempkm:demo-tour-done` event listener triggers banner display
- [ ] Slide-up/slide-down animation

## Verification

- `grep "demo-cta-banner" frontend/static/css/workspace.css` — CSS styles present
- `grep "demo-cta-banner" backend/app/templates/browser/workspace.html` — HTML present
- `grep "demo_cta_dismissed" backend/app/templates/browser/workspace.html` — dismiss logic present
- `grep "z-index: 50" frontend/static/css/workspace.css` — correct z-index
- `grep "flex-shrink: 0" frontend/static/css/workspace.css` — Lucide icon rule present (for CTA SVGs)
- `grep "sempkm:demo-tour-done" backend/app/templates/browser/workspace.html` — event listener wired

## Observability Impact

- **New runtime signal:** `console.log('[SemPKM] CTA banner shown')` when banner becomes visible — confirms the show logic triggered.
- **Inspection surface:** `localStorage.getItem('sempkm_demo_cta_dismissed')` — returns `'1'` if banner was dismissed; delete to re-show.
- **DOM inspection:** `document.getElementById('demo-cta-banner')` — check `style.display` to verify visibility state.
- **Failure visibility:** Banner not appearing after tour → check if `sempkm:demo-tour-done` event fires (logged in tutorials.js), check if `sempkm_demo_cta_dismissed` localStorage flag is set (prevents re-showing), check if `demo_mode` template variable is truthy (banner HTML only rendered when true).

## Inputs

- `backend/app/templates/browser/workspace.html` — T01 already added a `{% if demo_mode %}` block with the auto-start script. The CTA banner HTML and show/dismiss JS go inside this same conditional block.
- `frontend/static/css/workspace.css` — Existing workspace styles. Add CTA banner styles at the end of the file.
- T01's tour dispatches `sempkm:demo-tour-done` custom event on completion — the CTA banner listens for this to show itself.

## Expected Output

- `backend/app/templates/browser/workspace.html` — CTA banner div + show/dismiss JavaScript added inside the `{% if demo_mode %}` block
- `frontend/static/css/workspace.css` — `.demo-cta-banner` styles (~80 lines) appended at end of file
