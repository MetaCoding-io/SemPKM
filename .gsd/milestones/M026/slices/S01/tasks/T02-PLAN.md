---
estimated_steps: 5
estimated_files: 2
---

# T02: Browser verification at 3 responsive breakpoints and fix issues

**Slice:** S01 — Homepage rewrite with outcome-focused messaging
**Milestone:** M026

## Description

Open the T01-produced `docs/index.html` in a browser and verify correct rendering at desktop (1200px+), tablet (768px), and mobile (375px) viewports. Fix any layout bugs, overflow issues, unreadable text, broken animations, or inaccessible CTAs discovered during visual inspection. This is the quality gate before S02 builds persona pages on top of the S01 foundation.

## Steps

1. **Start a local file server** to serve the `docs/` directory (Python `http.server` or similar) so the browser can load the page with correct relative paths for CSS and screenshots.

2. **Desktop verification (1200px+)**: Navigate to the homepage. Verify:
   - Hero text is centered and readable with gradient accent
   - Both CTAs ("Try the Demo" + "Self-host") are visible and styled correctly
   - Persona selector shows 3 cards in a horizontal row
   - Competitive comparison table is fully visible with all columns
   - Mental Models / Domain Kits cards display in a grid
   - Feature overview cards are in a multi-column grid
   - Footer links are present
   - Canvas animation (if present) renders without errors
   - Nav links work (anchor scrolling, persona dropdown)

3. **Tablet verification (768px)**: Resize viewport to 768px width. Verify:
   - Nav collapses to hamburger menu (if applicable) or remains readable
   - Persona cards may go to 2-column or single-column — must be usable
   - Comparison table is scrollable horizontally or adapts layout
   - Feature cards reflow to fewer columns
   - CTAs remain tappable (min 44px touch target)
   - No horizontal overflow on the page body

4. **Mobile verification (375px)**: Resize viewport to 375px width. Verify:
   - Hero text doesn't overflow or get cut off
   - Persona cards stack vertically
   - Comparison table is usable (horizontal scroll with sticky first column, or stacked layout)
   - All CTAs are full-width and tappable
   - Font sizes are readable (≥ 14px body text)
   - Nav hamburger menu opens and closes correctly
   - No content extends beyond viewport width

5. **Fix any issues found**: Edit `docs/styles.css` and/or `docs/index.html` to resolve rendering problems. Common fixes: media query breakpoint adjustments, font-size scaling, flex-wrap rules, table overflow handling, padding/margin tweaks for small screens.

## Must-Haves

- [ ] Homepage renders correctly at 1200px+ width — all sections visible, no layout breaks
- [ ] Homepage renders correctly at 768px width — responsive layout, no overflow
- [ ] Homepage renders correctly at 375px width — mobile layout, all CTAs tappable
- [ ] No horizontal scroll on the page body at any viewport width
- [ ] Nav persona dropdown/links accessible at all widths
- [ ] Competitive comparison table usable on mobile (scrollable or adapted)

## Verification

- Browser screenshot at 1200px shows: hero, persona cards (3 across), comparison table, domain kits, features, CTAs
- Browser screenshot at 768px shows: readable layout, no overflow, CTAs visible
- Browser screenshot at 375px shows: stacked mobile layout, all content reachable, CTAs full-width
- `grep -rn "^<<<<<<< " docs/ --include="*.html" --include="*.css"` returns zero results (no conflict markers)

## Inputs

- `docs/index.html` — T01 output, rewritten homepage with linked CSS
- `docs/styles.css` — T01 output, shared CSS design system with responsive breakpoints
- `docs/screenshots/` — existing screenshot images referenced by the page

## Expected Output

- `docs/styles.css` — potentially updated with responsive fixes (media query corrections, mobile layout adjustments)
- `docs/index.html` — potentially updated with structural fixes (additional wrapper divs for scroll containment, class adjustments)
- Both files render correctly at all 3 breakpoints with no layout issues

## Observability Impact

- **What changes:** CSS media queries and potentially HTML structure are adjusted to fix responsive rendering issues discovered during visual inspection.
- **How to inspect:** Open `docs/index.html` in a browser and resize viewport to 375px, 768px, and 1200px+ widths. At each breakpoint, verify no horizontal overflow (`document.documentElement.scrollWidth <= document.documentElement.clientWidth`), all sections are visible, and CTAs are clickable/tappable.
- **Failure visibility:** Layout breaks are visually obvious — horizontal scrollbars, overlapping text, invisible buttons, or content extending beyond the viewport. Check browser console for JS errors from the canvas animation or IntersectionObserver. Run `document.querySelectorAll('.fade-in.visible').length` after scrolling to confirm animations fire.
- **Diagnostic commands:** `grep -c '@media' docs/styles.css` shows the number of responsive breakpoints. `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('OK')"` confirms HTML well-formedness after any structural edits.
