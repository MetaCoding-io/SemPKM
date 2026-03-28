# Chapter 32: Browser Extension

The **SemPKM Browser Extension** lets you capture typed, schema-validated objects
from any web page directly into your knowledge graph. Available for Chrome and
Firefox, the extension connects to your SemPKM instance via the
[API Surface](31-api-surface.md) and presents dynamic SHACL-driven forms that
match your installed Mental Models.

Key capabilities:

- **Type-aware capture** — select a type (Note, Contact, Project, etc.) and get
  a form with exactly the fields defined by that type's SHACL shape
- **Auto-population** — page title, URL, and selected text are extracted
  automatically and mapped to form fields
- **Schema.org mapping** — pages with schema.org JSON-LD metadata get
  automatic type suggestions and field pre-filling
- **Relationship picker** — search-as-you-type for linking new objects to
  existing ones in your knowledge graph
- **Keyboard shortcut** — press **Alt+S** to open the capture popup instantly

---

## Installation (Chrome)

The extension is sideloaded from the `extension/` directory in the SemPKM
repository. No Chrome Web Store listing is required.

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the `extension/` directory from your SemPKM checkout.
5. The SemPKM icon appears in the toolbar. Pin it for easy access.

The Chrome version uses `manifest.json` (Manifest V3 format) with a service
worker background script.

> **Tip:** After pulling updates to the extension code, revisit
> `chrome://extensions` and click the refresh icon on the SemPKM card to
> reload the updated files.

---

## Installation (Firefox)

Firefox uses a separate manifest file (`manifest.firefox.json`) that includes
Firefox-specific fields like the gecko add-on ID and uses `background.scripts`
instead of the Chrome `service_worker` format.

### Temporary Installation (Development)

1. Open `about:debugging#/runtime/this-firefox` in Firefox.
2. Click **Load Temporary Add-on…**
3. Navigate to the `extension/` directory and select `manifest.firefox.json`.
4. The extension loads and the icon appears in the toolbar.

> **Note:** Temporary add-ons are removed when Firefox restarts. You must
> re-load the extension each time you restart the browser. This is a Firefox
> platform limitation for unsigned add-ons.

### Permanent Installation

For persistent installation, the extension must be signed through
[addons.mozilla.org](https://addons.mozilla.org). The gecko ID
(`sempkm@sempkm.org`) is declared in `manifest.firefox.json` under
`browser_specific_settings.gecko.id` and must remain stable across versions.

---

## Generating an API Key

The extension authenticates with your SemPKM instance using a Bearer API token.
Generate one from the Admin panel:

1. Log in to SemPKM and navigate to **Settings** (gear icon in the sidebar).
2. Under the **API Keys** section, click **Generate New Key**.
3. Enter a descriptive name (e.g., "Chrome Extension").
4. Copy the token immediately — **it is shown only once**.
5. Store the token securely until you paste it into the extension settings.

The token is sent as an `Authorization: Bearer <token>` header with every API
request the extension makes. See [Chapter 31: API Surface](31-api-surface.md)
for details on how API authentication works.

---

## Configuration

Open the extension settings page:

- Click the SemPKM extension icon → click the **gear icon** (⚙), or
- Right-click the extension icon → **Options**

### Connection Settings

| Field          | Description                                                        |
|----------------|--------------------------------------------------------------------|
| **Instance URL** | The address of your SemPKM server (e.g., `http://localhost:4000`). |
| **API Key**    | The Bearer token from the previous step. Stored in `chrome.storage.local`. |

Click **Test Connection** to verify the extension can reach your instance. A
green status indicator means the connection is working. A red indicator means the
URL is unreachable or the API key is invalid — double-check both values.

### Capture Defaults

| Setting                       | Default | Description                                       |
|-------------------------------|---------|---------------------------------------------------|
| **Default Type**              | (none)  | Pre-select a type when opening the capture popup.  |
| **Auto-fill title**           | ✅ On   | Copy the page title into the Title field.          |
| **Auto-fill URL**             | ✅ On   | Copy the current page URL into URL fields.         |
| **Include selected text**     | ✅ On   | Copy highlighted text into the body/notes field.   |

The Default Type dropdown populates from your installed Mental Models after a
successful connection test.

---

## Capturing Objects

The core workflow is: **open popup → pick a type → fill the form → save**.

1. Navigate to any web page.
2. Click the SemPKM extension icon in the toolbar (or press **Alt+S**).
3. Select a type from the **Type** dropdown. Types are grouped by Mental Model.
4. The form dynamically renders fields based on the type's SHACL shape —
   text inputs, dropdowns, date pickers, and object reference fields appear
   as defined by your model.
5. Review the auto-populated fields (title, URL, selection) and fill in any
   remaining required fields.
6. Click **Save**.
7. A green success toast confirms the object was created. It is now visible in
   your workspace.

If save fails, an error message appears in the popup with details (e.g.,
network error, validation failure, missing required fields).

---

## Auto-population

When you open the popup, the extension runs a content script that extracts
metadata from the current page:

| Data Source         | Extracted Value                                    | Maps To           |
|---------------------|----------------------------------------------------|--------------------|
| `og:title` / `twitter:title` / `document.title` | Page title        | Title field        |
| `window.location.href` | Current URL                                  | URL fields         |
| `window.getSelection()` | Highlighted text                             | Body / notes field |
| `meta[name="author"]` / `meta[property="article:author"]` | Author name | Author fields |
| `meta[name="description"]` / `og:description` | Page description   | Description fields |

Auto-population respects your **Capture Defaults** settings — disable any
auto-fill behavior you don't want in the Options page.

---

## Schema.org JSON-LD Mapping

Many websites embed structured data using [schema.org](https://schema.org/)
JSON-LD. The extension detects these annotations and uses them to:

1. **Suggest a matching SemPKM type.** For example, a page with
   `"@type": "Person"` auto-suggests the CRM Contact type.
2. **Pre-fill form fields.** Schema.org properties are mapped to their
   corresponding SHACL property paths.

### Type Mappings

| Schema.org Type      | SemPKM Type           |
|----------------------|-----------------------|
| `Person`             | CRM: Contact          |
| `Organization`       | CRM: Company          |
| `Article`            | Basic PKM: Note       |
| `NewsArticle`        | Basic PKM: Note       |
| `BlogPosting`        | Basic PKM: Note       |
| `ScholarlyArticle`   | Research: Paper       |

### Property Mappings

Schema.org properties like `givenName`, `familyName`, `email`, `jobTitle`,
and `url` are mapped to corresponding SemPKM SHACL property paths. For
example, on a LinkedIn profile with `"givenName": "Alice"`, the extension
pre-fills the Contact's first name field.

If no matching SemPKM type is installed (e.g., the CRM model is not loaded), the
schema.org data is still extracted but the type suggestion is skipped.

---

## Context Menu

The extension declares the `contextMenus` permission for right-click capture
workflows. Select text on any page and use the browser's context menu to
initiate a capture with the selected text pre-filled.

> **Note:** The context menu integration depends on your installed Mental Models
> and configured capture defaults. If no default type is set, you will be
> prompted to select one in the popup.

---

## Relationship Picker

When a SHACL shape defines an **object reference** property (a field whose
`target_class` points to another SemPKM type), the form renders a
search-as-you-type field instead of a plain text input.

How it works:

1. Start typing in an object reference field (minimum 2 characters).
2. After a brief debounce (300ms), the extension searches your SemPKM instance
   for existing objects matching your query text.
3. Results appear in a dropdown, filtered to the expected type (e.g., only
   Contacts appear for a "contact" reference field).
4. Select a result to link the new object to the existing one.
5. The selected reference is shown with a label and a clear button (✕) to
   remove it.

On save, the extension creates both the new object and an edge connecting it
to the referenced object.

---

## Keyboard Shortcut

Press **Alt+S** to open the capture popup from any page — no mouse required.

### Customizing the Shortcut

**Chrome:**
1. Open `chrome://extensions/shortcuts`
2. Find "SemPKM Capture" in the list
3. Click the pencil icon next to "Activate the extension"
4. Press your preferred key combination
5. Click OK

**Firefox:**
1. Open `about:addons`
2. Click the gear icon (⚙) → **Manage Extension Shortcuts**
3. Find "SemPKM Capture" and set your preferred shortcut

> **Tip:** If Alt+S conflicts with another extension or system shortcut,
> `Ctrl+Shift+S` is a common alternative that avoids most conflicts.

---

## Troubleshooting

### "Cannot reach instance" or connection test fails

- Verify the **Instance URL** in extension settings matches your SemPKM server
  address (include the port, e.g., `http://localhost:4000`).
- Ensure SemPKM is running (`docker compose ps` should show healthy containers).
- Check that no firewall or proxy is blocking the connection.
- If using HTTPS, ensure the certificate is valid or accepted by the browser.

### "Invalid API key" or 401 errors

- The API key may have been deleted or expired. Generate a new one in
  **Settings > API Keys**.
- Ensure you copied the full token (no leading/trailing spaces).
- Verify the key works with a curl test:
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:4000/.well-known/sempkm
  ```

### "No types available" in the type dropdown

- At least one Mental Model must be installed. Go to **Admin > Mental Models**
  and install a model (e.g., Basic PKM).
- After installing a model, re-open the extension popup — types load fresh on
  each open.

### Extension icon is grayed out or missing

- **Chrome:** Check that the extension is enabled at `chrome://extensions`.
  Click the refresh icon to reload it.
- **Firefox:** Temporary add-ons are removed on restart. Re-load from
  `about:debugging#/runtime/this-firefox`.

### Form fields don't appear after selecting a type

- The SHACL shape for the selected type may not be loading. Open the popup's
  DevTools (right-click the popup → Inspect) and check the Console for errors.
- Verify the shape endpoint works: visit
  `http://localhost:4000/api/shapes/<type_iri>` in your browser.

### Auto-populated fields are empty

- Check that **Auto-fill title** and **Auto-fill URL** are enabled in the
  extension Options page.
- Some pages block content script execution (e.g., `chrome://` pages, PDF
  viewers). The extension cannot extract data from these pages.

### Firefox: extension disappears after restart

This is expected for temporary add-ons. Firefox only persists signed extensions
installed from addons.mozilla.org. For development use, re-load from
`about:debugging` after each restart.

---

**Previous:** [Chapter 31: API Surface](31-api-surface.md) | **Next:** [Chapter 33: Context Overlay](33-context-overlay.md)
