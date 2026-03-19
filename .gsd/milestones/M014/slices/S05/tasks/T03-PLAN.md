---
estimated_steps: 5
estimated_files: 4
---

# T03: User guide chapter + glossary + README TOC

**Slice:** S05 — Cross-browser, keyboard shortcut, E2E tests + user guide
**Milestone:** M014

## Description

Write the user guide chapter documenting the browser extension — installation for both Chrome and Firefox, API key generation, configuration, capture workflows, auto-population, context menu, relationship picker, keyboard shortcut, and troubleshooting. Update the README TOC, glossary, and navigation chain.

This is documentation-only work. No code changes. The chapter should be useful to a self-hosted SemPKM user who has never seen the extension before and needs to go from zero to capturing objects.

## Steps

1. **Write `docs/guide/32-browser-extension.md`** with these 11 sections:

   **1. Overview** — What the browser extension does (capture typed, schema-validated objects from any web page). Mention Chrome and Firefox support, SHACL-driven forms, auto-population, relationship creation.

   **2. Installation (Chrome)** — Sideload from `extension/` directory:
   - Open `chrome://extensions`
   - Enable Developer Mode
   - Click "Load unpacked" → select the `extension/` directory
   - Extension icon appears in toolbar
   - Note about `manifest.json` being the Chrome manifest

   **3. Installation (Firefox)** — Sideload using Firefox manifest:
   - Copy `manifest.firefox.json` to `manifest.json` (or use a symlink) in a separate directory, OR explain the temporary install process
   - Open `about:debugging#/runtime/this-firefox`
   - Click "Load Temporary Add-on" → select `manifest.firefox.json`
   - Note: temporary add-ons are removed on browser restart (this is Firefox's sideload limitation)
   - Note the gecko ID requirement

   **4. Generating an API Key** — Admin walkthrough:
   - Navigate to Admin > API Keys (or `/admin/api-keys`)
   - Click "Create API Key" — enter a name
   - Copy the plaintext token (shown only once)
   - Reference Chapter 31 for API endpoint details

   **5. Configuration** — Extension settings page:
   - Click extension icon → gear icon, or right-click → "Options"
   - Instance URL: `http://localhost:3000` (or production URL)
   - API Key: paste the key from step 4
   - Test Connection: green = OK, red = check URL/key
   - Default Type: optionally pre-select a type
   - Capture preferences: auto-fill title/URL, include selection

   **6. Capturing Objects** — Main workflow:
   - Click extension icon (or press Alt+S)
   - Select a type from the dropdown (grouped by Mental Model)
   - Fill in the dynamic form (SHACL-driven, varies by type)
   - Click Save
   - Green toast = success, object appears in workspace

   **7. Auto-population** — How page data fills the form:
   - Title extracted from page metadata (og:title, document.title)
   - URL from current page
   - Selected text fills the body/notes field
   - Settings control which auto-fill features are active

   **8. Schema.org JSON-LD** — Automatic field mapping:
   - Pages with schema.org JSON-LD (Person, Article, Organization)
   - Extension auto-suggests matching SemPKM type
   - Properties mapped to form fields (e.g., givenName → firstName)
   - Works with news sites, blogs, LinkedIn profiles, etc.

   **9. Context Menu** — Right-click capture:
   - Select text on any page
   - Right-click → "Save to SemPKM"
   - Popup opens with selected text pre-filled in body
   - Select type, fill remaining fields, save

   **10. Relationship Picker** — Linking existing objects:
   - Object reference fields show search-as-you-type
   - Type a few characters to search existing objects
   - Results filtered by expected type
   - Select to create a relationship (edge) on save

   **11. Keyboard Shortcut** — Alt+S:
   - Default: Alt+S opens the popup
   - Customize in Chrome: `chrome://extensions/shortcuts`
   - Customize in Firefox: `about:addons` → gear icon → "Manage Extension Shortcuts"

   **12. Troubleshooting** — Common issues:
   - "Cannot reach instance" → check URL, ensure SemPKM is running
   - "Invalid API key" → regenerate in Admin > API Keys
   - "No types available" → install a Mental Model first
   - Extension icon grayed out → check permissions
   - Firefox temporary add-on removed on restart → re-load

   Add navigation footer: Previous: Chapter 31 | Next: Appendix A

2. **Update `docs/guide/README.md` TOC.** Add Chapter 32 after the Chapter 31 line:
   ```
   32. [Browser Extension](32-browser-extension.md)
   ```

3. **Add glossary entries to `docs/guide/appendix-d-glossary.md`.** Add in alphabetical order:

   **API Token** — A secret key generated in the Admin panel that allows external clients (like the browser extension) to authenticate with your SemPKM instance without a session cookie. Tokens are created at Admin > API Keys and shown only once. See [Chapter 32: Browser Extension](32-browser-extension.md).

   **Browser Extension** — A Chrome/Firefox extension that captures typed, schema-validated objects from any web page directly into your SemPKM knowledge graph. Supports SHACL-driven forms, auto-population from page metadata and schema.org JSON-LD, relationship creation, and keyboard shortcuts. See [Chapter 32: Browser Extension](32-browser-extension.md).

4. **Update navigation chain.** In `docs/guide/31-api-surface.md`, change the "Next" link from Appendix A to Chapter 32. The new Chapter 32 will have Previous: Ch 31, Next: Appendix A.

5. **Verify all links and structure.** Check that the file exists, all 11+ section headings are present, README has the link, glossary has both entries, and navigation prev/next links point correctly.

## Must-Haves

- [ ] `docs/guide/32-browser-extension.md` exists with all sections (Overview through Troubleshooting)
- [ ] README TOC has Chapter 32 link
- [ ] Glossary has "API Token" and "Browser Extension" entries with cross-references to Chapter 32
- [ ] Navigation chain: Ch 31 → Ch 32 → Appendix A (prev/next links in all three files are correct)

## Verification

- `test -f docs/guide/32-browser-extension.md && echo "exists"` returns "exists"
- `grep -c "^##" docs/guide/32-browser-extension.md` returns 11 or more (section headings)
- `grep "32.*Browser Extension" docs/guide/README.md` matches
- `grep "API Token" docs/guide/appendix-d-glossary.md` matches
- `grep "Browser Extension" docs/guide/appendix-d-glossary.md` matches
- `grep "32-browser-extension" docs/guide/31-api-surface.md` matches (updated next link)
- `grep "31-api-surface" docs/guide/32-browser-extension.md` matches (previous link)
- `grep "appendix-a" docs/guide/32-browser-extension.md` matches (next link)

## Observability Impact

Documentation-only task — no runtime signals change. A future agent can verify this task by checking file existence and content:
- `test -f docs/guide/32-browser-extension.md` confirms the chapter was created
- `grep -c "^##" docs/guide/32-browser-extension.md` confirms section count
- Navigation chain integrity is verifiable by grepping prev/next links across the three connected files (Ch 31, Ch 32, Appendix A)

No failure state to persist — documentation is a static artifact.

## Inputs

- `docs/guide/31-api-surface.md` — Current last chapter before appendices, needs next link updated
- `docs/guide/README.md` — TOC, needs Ch 32 entry added after Ch 31
- `docs/guide/appendix-d-glossary.md` — Glossary, needs two new entries in alphabetical order
- Extension functionality from S01-S04 summaries — all features documented in the chapter
- Extension file structure: `extension/manifest.json`, `extension/manifest.firefox.json`, `extension/options/`, `extension/popup/`

## Expected Output

- `docs/guide/32-browser-extension.md` — New: complete user guide chapter with 11+ sections
- `docs/guide/README.md` — Updated: Chapter 32 in TOC
- `docs/guide/appendix-d-glossary.md` — Updated: two new glossary entries
- `docs/guide/31-api-surface.md` — Updated: navigation "Next" link points to Chapter 32
