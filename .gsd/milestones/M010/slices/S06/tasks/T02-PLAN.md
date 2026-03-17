---
estimated_steps: 5
estimated_files: 5
---

# T02: User guide Chapter 30 and navigation chain updates

**Slice:** S06 — E2E tests + user guide
**Milestone:** M010

## Description

Write the user guide Chapter 30 documenting the RSS Reader app for end users. Follow the established chapter style from chapters 27-29 (Spatial Canvas, Dashboards and Workflows, App Platform). Update the table of contents, navigation chain footers, and glossary.

## Steps

1. **Create `docs/guide/30-rss-reader.md`.** Write Chapter 30 following the structure and tone of chapters 27-29. The chapter should cover:

   ```markdown
   # Chapter 30: RSS Reader

   Introduction (what RSS Reader is, what it does, how it fits in SemPKM)

   ## Getting Started
   - Installing the rss-feeds Mental Model (Admin > Mental Models, path: rss-feeds)
   - Installing the RSS Reader app (Admin > Applications, path: rss-reader, wait for "running" status)
   - Opening the reader from the APPS sidebar section

   ## Subscribing to Feeds
   - Adding feeds by URL (click Subscribe, enter feed URL)
   - Feed discovery (paste a website URL, feed auto-detected)
   - Importing feeds from OPML (click Import OPML, select file, categories preserved as tags)

   ## The Reader Interface
   - Feed sidebar (feed list with unread count badges, error indicators)
   - Article list (filter tabs: All / Unread / Starred, article items with title/date/source)
   - Reading pane (clean typography, markdown-rendered body, star button, mark read/unread)

   ## Reading Articles
   - Opening an article (click in article list, auto-marks as read if setting enabled)
   - Starring and unstarring (click star button, persists across sessions)
   - Mark as read / unread
   - Keyboard navigation (j = next article, k = previous article)

   ## Workspace Integration
   - Unread Articles view (Views section in explorer)
   - Starred Articles view (Views section in explorer)
   - Related Articles in right pane (shows articles sharing tags or feed source with focused object)
   - Command palette entries: "Subscribe to Feed...", "Mark All as Read", "Open RSS Reader"
   - Custom article renderer (opening an Article from the object browser shows the reader layout, not the default SHACL form)

   ## Managing Feeds
   - Unsubscribing from a feed (click unsubscribe in feed sidebar)
   - Feed error indicators (connection failures shown per-feed)
   - Re-subscribing (subscribe with the same URL)

   ## Settings
   - Articles per page (default 50, range 10-200)
   - Mark read on open (default enabled)
   - Poll interval (configured in Admin > Applications > RSS Reader, default 5 minutes)

   ## Admin Monitoring
   - App status and lifecycle (running/stopped/error badges, start/stop/restart)
   - Task history for poll-feeds (Admin > Applications > RSS Reader detail page)
   - Permissions overview (what the RSS Reader can do: create objects, read SPARQL, fetch feeds)
   ```

   Target ≥150 lines. Use the same formatting conventions as ch.29: headers, tables, blockquote tips, code-style for UI element names.

   Footer: `**Previous:** [Chapter 29: App Platform](29-app-platform.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`.** Add Chapter 30 to the Part VIII section, after entry 29:

   ```markdown
   30. [RSS Reader](30-rss-reader.md)
   ```

3. **Update navigation footer in `docs/guide/29-app-platform.md`.** Change the last line from:

   ```
   **Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```

   to:

   ```
   **Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Chapter 30: RSS Reader](30-rss-reader.md)
   ```

4. **Update navigation footer in `docs/guide/appendix-a-environment-variables.md`.** Change the last line from:

   ```
   **Previous:** [Chapter 26: IndieAuth](26-indieauth.md) | **Next:** [Appendix B: Keyboard Shortcut Reference](appendix-b-keyboard-shortcuts.md)
   ```

   to:

   ```
   **Previous:** [Chapter 30: RSS Reader](30-rss-reader.md) | **Next:** [Appendix B: Keyboard Shortcut Reference](appendix-b-keyboard-shortcuts.md)
   ```

5. **Add glossary entries to `docs/guide/appendix-d-glossary.md`.** Insert in alphabetical order:

   **Article (RSS)** — An individual piece of content fetched from an RSS or Atom feed. Stored as an `rss:Article` object in the knowledge base with title, author, published date, feed source, and markdown body. Browsable in the object browser and searchable via Ctrl+K. See [Chapter 30: RSS Reader](30-rss-reader.md).

   **Feed Subscription** — A record of a user's subscription to an RSS, Atom, or JSON feed URL. The RSS Reader app polls subscriptions at a configurable interval and ingests new articles automatically. Managed through the reader sidebar or OPML import. See [Chapter 30: RSS Reader](30-rss-reader.md).

   **OPML** — (Outline Processor Markup Language) An XML format for exchanging lists of feed subscriptions between RSS readers. SemPKM's RSS Reader can import OPML files to create multiple feed subscriptions at once, preserving folder categories as tags. See [Chapter 30: RSS Reader](30-rss-reader.md).

   **Poll Interval** — The frequency at which the RSS Reader checks subscribed feeds for new articles. Configured per-app in Admin > Applications > RSS Reader. Default is 5 minutes. See [Chapter 30: RSS Reader](30-rss-reader.md).

## Must-Haves

- [ ] `docs/guide/30-rss-reader.md` exists with ≥150 lines
- [ ] Chapter covers all RSS Reader features: subscribe, reader UI, star/read, OPML, settings, workspace integration, admin
- [ ] README.md TOC includes Chapter 30
- [ ] Navigation chain correct: ch.29 footer → ch.30, ch.30 footer → Appendix A, Appendix A footer → ch.30 (Previous)
- [ ] ≥3 new glossary entries in appendix-d-glossary.md

## Verification

- `wc -l docs/guide/30-rss-reader.md` — ≥150 lines
- `grep "30-rss-reader" docs/guide/README.md` — present
- `grep "30-rss-reader" docs/guide/29-app-platform.md` — present in footer
- `grep "30-rss-reader" docs/guide/appendix-a-environment-variables.md` — present in footer
- `grep -c "See \[Chapter 30" docs/guide/appendix-d-glossary.md` — ≥3

## Inputs

- `docs/guide/29-app-platform.md` — previous chapter, style reference, footer to update
- `docs/guide/README.md` — table of contents to update
- `docs/guide/appendix-a-environment-variables.md` — footer to update (Previous link)
- `docs/guide/appendix-d-glossary.md` — add RSS glossary terms
- S03 Summary — Reader UI features: feed sidebar, article list, reading pane, star/read, keyboard nav (j/k), HX-Trigger conventions
- S04 Summary — Workspace contributions: related articles right pane, custom article renderer, command palette entries, navigate command
- S05 Summary — OPML import (file upload, categories as tags), settings (articlesPerPage, markReadOnOpen)
- S02 boundary — feed discovery, content extraction, conditional GET, per-feed error tracking

## Expected Output

- `docs/guide/30-rss-reader.md` — new file, ≥150 lines, complete RSS Reader user guide
- `docs/guide/README.md` — Chapter 30 added to TOC
- `docs/guide/29-app-platform.md` — footer updated (Next → Chapter 30)
- `docs/guide/appendix-a-environment-variables.md` — footer updated (Previous → Chapter 30)
- `docs/guide/appendix-d-glossary.md` — ≥3 new RSS-specific entries inserted alphabetically

## Observability Impact

This task is documentation-only — no runtime signals change. Future agents can verify correctness via:
- `wc -l docs/guide/30-rss-reader.md` — line count ≥150 confirms chapter exists with substance
- `grep "30-rss-reader" docs/guide/README.md docs/guide/29-app-platform.md docs/guide/appendix-a-environment-variables.md` — confirms navigation chain integrity across three files
- `grep -c "See \[Chapter 30" docs/guide/appendix-d-glossary.md` — confirms glossary entries reference the new chapter (≥3)
- Broken links are detectable by any Markdown link checker run over `docs/guide/` — all Chapter 30 cross-references use relative paths
