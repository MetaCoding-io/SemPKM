# Chapter 33: Context Overlay

The **Context Overlay** surfaces related knowledge from your SemPKM graph while
you browse the web. As you navigate to any page, the extension checks whether
your knowledge base contains objects related to that page — matching by URL,
title, or keywords — and shows the results in a sidebar panel.

Key capabilities:

- **Context badge** — the extension icon shows how many related objects exist
  for the current page, updating automatically as you browse
- **Knowledge sidebar** — a side panel listing related objects grouped by type,
  with match-confidence indicators
- **In-context actions** — open objects in SemPKM, link the current page to an
  object, or capture evidence from the page directly into your research workflow
- **Keyboard shortcut** — press **Alt+K** to open the sidebar instantly

The context overlay requires a configured connection to your SemPKM instance.
See [Chapter 32: Browser Extension](32-browser-extension.md) for setup
instructions.

---

## Opening the Sidebar

Press **Alt+K** from any web page to open the knowledge sidebar. The shortcut
works in both Chrome and Firefox.

You can also open the sidebar from the extension popup: click the SemPKM icon
in the toolbar and select **Show Context**.

The sidebar appears alongside the current page — in Chrome it uses the Side
Panel API (a native browser panel), and in Firefox it uses the sidebar area.
In both cases, the page content remains visible while you browse your related
knowledge.

> **Tip:** If Alt+K conflicts with another extension or system shortcut, see
> [Chapter 32: Browser Extension — Keyboard Shortcut](32-browser-extension.md#keyboard-shortcut)
> for instructions on customizing the shortcut in your browser.

---

## Badge Count

When auto-context checking is enabled (the default), the extension automatically
queries your SemPKM instance each time you navigate to a new page. After a
short delay (~2 seconds by default), a badge appears on the extension icon:

| Badge         | Meaning                                                   |
|---------------|-----------------------------------------------------------|
| **Number** (teal) | The count of related objects found for this page.     |
| **!** (red)       | The context query failed — check your connection settings. |
| *(empty)*         | No related objects found, or auto-context is disabled.    |

The badge updates per-tab — different tabs show different counts based on their
page content.

The delay before the first check is configurable in the extension settings
(see [Settings](#settings) below). This prevents the extension from firing
queries during rapid tab switching.

---

## How Matching Works

The context overlay sends three signals to the SemPKM API for each page:

1. **URL** — the full page URL, matched against `schema:url` properties in
   your knowledge graph
2. **Title** — the page title, matched via full-text search against object
   labels and titles
3. **Keywords** — extracted from the page's meta description and headings,
   matched via full-text keyword search

The API returns all matching objects, and the extension ranks them client-side
by match quality:

| Match Type   | Badge Color | Confidence | Example                                      |
|--------------|-------------|------------|----------------------------------------------|
| **URL**      | Green       | Highest    | You saved a Note with this exact URL          |
| **Title**    | Blue        | Medium     | A Project name matches the page title         |
| **Keyword**  | Gray        | Lower      | A Concept's description mentions page keywords|

The top 10 results are displayed in the sidebar. URL matches always appear
first, followed by title matches, then keyword matches.

---

## Grouped Results

Results in the sidebar are organized by type — Notes, Contacts, Projects, and
so on — with each type in a collapsible section. The section header shows the
type name and the number of results in that group.

Each result row displays:

- The object's title
- A colored badge indicating the match type (URL, title, or keyword)
- Action buttons (see [Actions](#actions) below)

Click a section header to expand or collapse the group. All groups start
expanded when the sidebar first loads.

---

## Actions

Each result in the sidebar offers actions that let you work with the related
object without leaving the current page.

### Open

Click **Open** to navigate to the object in your SemPKM workspace. This opens
a new browser tab pointing to the object's editor page, where you can view or
edit its properties, body, and relationships.

### Link to this page

Click **Link to this page** to create a `schema:url` edge from the object to
the current web page. This records a relationship between the knowledge object
and the URL you are browsing.

After linking, the edge is visible in the object's **Relations** panel in
SemPKM. The button shows "Linking…" while the API call is in progress and
displays a success or error toast when complete.

### Add Evidence

The **Add Evidence** button appears only on results whose type is **Claim**
(from the Research Workflow mental model). It captures text from the current
page as supporting evidence for the claim.

The capture flow:

1. Click **Add Evidence** on a Claim result.
2. A prompt panel appears in the sidebar with instructions.
3. Switch to the web page and highlight the text you want to capture.
4. Return to the sidebar and click **Capture**.
5. A preview of your selected text appears — verify it and confirm.
6. The extension creates an **Evidence** object with the selected text as its
   body and the page URL as its source, then links it to the Claim via a
   `res:supports` edge.

If the Evidence object is created but the linking step fails, the error toast
includes the Evidence IRI so you can link it manually in SemPKM.

> **Note:** You must select text on the page *before* clicking Capture. If no
> text is selected, the extension shows a "No text selected" message.

---

## Settings

Three settings on the extension Options page control context overlay behavior.
Open the Options page by clicking the SemPKM icon → gear icon (⚙), or by
right-clicking the extension icon → **Options**.

| Setting                | Default  | Description                                          |
|------------------------|----------|------------------------------------------------------|
| **Auto-check context** | ✅ On    | Automatically query for related objects on every page navigation. Disable to use manual checks only (via the sidebar Refresh button). |
| **Check delay**        | 2000 ms  | Milliseconds to wait after a page loads before querying. Higher values reduce unnecessary queries during rapid browsing. |
| **Request timeout**    | 5000 ms  | Maximum time to wait for a response from your SemPKM instance before marking the check as failed. |

Changes take effect immediately — no browser restart required.

---

## Cross-Browser Notes

The context overlay works in both Chrome and Firefox with minor platform
differences:

| Feature                | Chrome                                  | Firefox                                |
|------------------------|-----------------------------------------|----------------------------------------|
| **Sidebar technology** | Side Panel API (`chrome.sidePanel`)     | `sidebar_action` API                   |
| **Sidebar position**   | Right side of the browser window        | Left side (Firefox default)            |
| **Shortcut**           | Alt+K                                   | Alt+K                                  |
| **Badge API**          | `chrome.action.setBadgeText`            | `browser.action.setBadgeText`          |
| **Text capture**       | `chrome.scripting.executeScript`        | `browser.scripting.executeScript`      |

Both browsers use the same sidebar HTML, CSS, and JavaScript. The extension's
service worker handles API differences internally.

---

## Caching

Context query results are cached in the service worker's memory, keyed by
page URL. When you revisit a page in the same session, the sidebar loads
instantly from the cache instead of re-querying the API.

Cache behavior:

- **Capacity:** Up to 100 URLs (least-recently-used eviction).
- **Lifetime:** The cache lives only as long as the service worker is active.
  In Chrome's Manifest V3, the service worker shuts down after ~30 seconds of
  idle time, clearing the cache.
- **No persistent storage:** Results are never written to `chrome.storage` or
  disk. Re-querying is fast enough that persistence is unnecessary.
- **Manual refresh:** Click the **Refresh** button in the sidebar header to
  bypass the cache and re-query the API for the current page.

---

## Troubleshooting

### Sidebar shows "No related objects found"

The extension queried your SemPKM instance and received zero matches. This
means no objects in your knowledge graph have a URL, title, or keyword that
matches the current page.

- Verify that relevant objects exist in SemPKM with `schema:url` properties
  matching the page URL, or with titles that overlap with the page title.
- Try creating a Note in SemPKM with the page URL, then refresh the sidebar.

### Badge shows "!"

The context query failed. The most common causes:

- The SemPKM instance is not running. Check with `docker compose ps`.
- The Instance URL in extension settings is incorrect.
- The API key is invalid or expired. Generate a new one in
  **Settings > API Keys**.
- A firewall or proxy is blocking the request.

Open the extension's service worker console (`chrome://extensions` → click
**Inspect** on the SemPKM service worker) and look for `[SemPKM]` error
messages for details.

### Sidebar doesn't open with Alt+K

- Another extension may have claimed the Alt+K shortcut. Check your browser's
  extension shortcut settings (see
  [Chapter 32: Browser Extension — Keyboard Shortcut](32-browser-extension.md#keyboard-shortcut)).
- Try opening the sidebar manually from the extension popup instead.

### Evidence capture says "No text selected"

You must select (highlight) text on the web page before clicking **Capture** in
the sidebar. Switch to the page tab, drag to highlight the text you want, then
return to the sidebar and click Capture.

### Results don't appear after 5 seconds

- Check the **Check delay** setting in Options — a very high value delays the
  initial query.
- Click the **Refresh** button in the sidebar header to trigger an immediate
  query.
- Open the service worker console and look for `[SemPKM]` prefixed log
  messages to see whether the query was sent and what response was received.
- Verify the **Request timeout** setting is not too low for your network
  conditions.

---

**Previous:** [Chapter 32: Browser Extension](32-browser-extension.md) | **Next:** [Chapter 34: Linear Sync](34-linear-sync.md)
