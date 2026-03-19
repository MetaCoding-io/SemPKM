---
estimated_steps: 6
estimated_files: 4
---

# T03: Write user guide Chapter 33 and update navigation chain

**Slice:** S03 — Settings, E2E tests, and user guide
**Milestone:** M015

## Description

Write user guide Chapter 33 documenting the context overlay feature. Follow the voice, structure, and formatting conventions of Chapter 32 (Browser Extension). Update the navigation chain so ch32 links to ch33, ch33 links to appendix-a, README TOC includes ch33, and glossary has entries for the new concepts.

## Steps

1. **Read Chapter 32** — `docs/guide/32-browser-extension.md` fully, for voice, structure, heading style, code formatting, and navigation footer pattern.

2. **Read the glossary** — `docs/guide/appendix-d-glossary.md` to see existing entry format.

3. **Write `docs/guide/33-context-overlay.md`** with these sections:
   - **Introduction** — brief overview of the context overlay (what it does, why it's useful)
   - **Opening the Sidebar** — Alt+K shortcut, or "Show Context" from popup (both browsers)
   - **Badge Count** — badge appears ~2s after page load, shows number of related objects, "!" on error, configurable delay
   - **How Matching Works** — three signals: URL match (highest confidence, green badge), title match (blue), keyword match (gray). Client-side ranking, top 10 results.
   - **Grouped Results** — results grouped by type with collapsible sections, match-type badges
   - **Actions** section with subsections:
     - **Open** — opens the object in SemPKM in a new tab
     - **Link to this page** — creates a `schema:url` edge from the object to the current page, visible in SemPKM's Relations panel
     - **Add Evidence** — appears only on Claim-type results. Capture flow: click button → highlight text on page → click Capture → Evidence object created and linked to the Claim via `res:supports` edge
   - **Settings** — three controls on the options page: auto-check toggle, check delay, request timeout
   - **Cross-Browser Notes** — Chrome uses Side Panel API (sidebar alongside page), Firefox uses sidebar_action (similar UX). Alt+K works in both.
   - **Caching** — URL→results cached per session in service worker memory. Cache cleared on service worker restart (~30s idle in MV3). No persistent cache.
   - **Troubleshooting** section:
     - Sidebar shows "No related objects found" → check that objects in SemPKM have `schema:url` or titles matching the page
     - Badge shows "!" → check connection settings, verify API key is valid
     - Sidebar doesn't open → verify Alt+K shortcut isn't overridden by another extension
     - Evidence capture says "No text selected" → select text on the page before clicking Capture
     - Results don't appear after 5 seconds → check contextCheckDelay setting, try clicking Refresh in sidebar header
   - **Navigation footer**: `Previous: [Chapter 32: Browser Extension](32-browser-extension.md) | Next: [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

4. **Update Chapter 32 footer** — In `docs/guide/32-browser-extension.md`, change the last line from:
   ```
   **Previous:** [Chapter 31: API Surface](31-api-surface.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```
   to:
   ```
   **Previous:** [Chapter 31: API Surface](31-api-surface.md) | **Next:** [Chapter 33: Context Overlay](33-context-overlay.md)
   ```

5. **Update README TOC** — In `docs/guide/README.md`, add `33. [Context Overlay](33-context-overlay.md)` after the Chapter 32 entry in Part VIII.

6. **Add glossary entries** — In `docs/guide/appendix-d-glossary.md`, add:
   - **Context Overlay** — The browser extension feature that shows related objects from your SemPKM knowledge graph when browsing any web page. Includes the context badge and knowledge sidebar. See [Chapter 33](33-context-overlay.md).
   - **Context Badge** — The extension icon badge showing the count of related objects found for the current page. Appears ~2s after page load when auto-context is enabled.
   - **Knowledge Sidebar** — The side panel (Chrome) or sidebar (Firefox) showing related objects from SemPKM grouped by type, with actions to open, link, or add evidence. Opened via Alt+K.

## Must-Haves

- [ ] Chapter 33 at `docs/guide/33-context-overlay.md` with all sections listed above
- [ ] Chapter 32 footer links to Chapter 33
- [ ] Chapter 33 footer links back to Chapter 32 and forward to Appendix A
- [ ] README.md TOC includes Chapter 33
- [ ] Glossary has entries for Context Overlay, Context Badge, Knowledge Sidebar
- [ ] Voice and formatting match Chapter 32 conventions

## Verification

- `test -f docs/guide/33-context-overlay.md` — file exists
- `grep "Chapter 33" docs/guide/32-browser-extension.md` — footer updated
- `grep "33-context-overlay" docs/guide/README.md` — TOC updated
- `grep -c "Context Overlay\|Knowledge Sidebar\|Context Badge" docs/guide/appendix-d-glossary.md` ≥ 3
- Chapter 33 navigation footer references both ch32 (previous) and appendix-a (next)

## Inputs

- `docs/guide/32-browser-extension.md` — voice, structure, and formatting reference
- `docs/guide/README.md` — current TOC structure
- `docs/guide/appendix-d-glossary.md` — existing glossary entry format
- S01 summary — sidebar architecture, badge behavior, Alt+K shortcut, settings keys
- S02 summary — Link to page action (schema:url edge), Add Evidence action (content script capture)
- Roadmap success criteria — specific user-facing behaviors to document

## Expected Output

- `docs/guide/33-context-overlay.md` — complete chapter (~150-250 lines)
- `docs/guide/32-browser-extension.md` — footer updated
- `docs/guide/README.md` — TOC includes Chapter 33
- `docs/guide/appendix-d-glossary.md` — three new entries
