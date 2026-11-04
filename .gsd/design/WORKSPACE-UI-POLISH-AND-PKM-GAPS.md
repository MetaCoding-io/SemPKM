# Workspace UI Polish and PKM Capability Gaps

> **Status:** Proposed (not yet scheduled into a milestone)
> **Date:** 2026-11-04
> **Scope:** Two related backlogs from a design review of the main workspace: (1) UI polish that moves the workspace from "engineering demo" to "product" without a redesign, and (2) table-stakes PKM capabilities that Obsidian, Notion, Roam and Logseq users expect and SemPKM does not have yet.
> **Companion material:** Annotated screenshot review with mockups at https://claude.ai/artifact/CVqJEAQWq7u8HaWNXpLGx5 · Memory palace research in `reports/Memory palace mode design research.md` (PR #66)
> **How reviewed:** Checked-in screenshots under `docs/screenshots/`, the shell template, token system and workspace CSS on `main` as of 2026-11-03. Not reviewed against a running stack.

---

## Summary

The bones are good: the two-tier token system in `theme.css` is disciplined, the Dockview IDE layout is coherent, and the login page and markdown read view already look professional. What holds the product back is **leakage** rather than visual language: the data model's internals (shape names, QNames, predicates, command names, raw JSON error bodies) show through everywhere, the shell still reads as a developer console, and a few button conventions are inverted. Severity below reflects how much a finding costs a first-time user's trust, not how hard it is to fix.

Several High items are one-line or one-file changes. Together they are one small milestone.

---

## Part 1 — UI polish findings

### A. Stop showing the graph's internals to users

| Sev | Finding | Where | Proposed change |
|-----|---------|-------|-----------------|
| High | Explorer labels types by SHACL shape name ("Person Shape", "Note Shape", "Deal Shape") | `backend/app/templates/browser/nav_tree.html` renders `type.label`; `ShapesService` already does `form.label.removesuffix(" Shape")` for the type picker (`services/shapes.py:570`) but the nav-tree path does not | Resolve type labels through `LabelService` for the target class, falling back to the shape label with the suffix stripped. One code path for every place a type name appears. |
| High | Raw QNames and predicates: `bpkm:Concept` folders in VIEWS, `bpkm:Note` toolbar badge, `bpkm:hasNote` / `sempkm:source` in Relations, truncated IRIs on inbound rows | `views_explorer.html`, `object_tab.html` (toolbar badge), relations panel rendering in `workspace.js`, `views/service.py` `_local_name()` fallbacks | Humanise every class and predicate by default (label precedence already exists in `LabelService`). Put the IRI in a tooltip plus a copy action. Treat `_local_name()` as a last resort and title-case it (`hasNote` → "Has note"). |
| High | API error bodies rendered as content: with the type-picker tab open, Relations and Lint show the literal text `{"detail":"Invalid IRI"}` | `workspace.js` right-pane loaders (`relations-content`, `lint-content`) swap the response body regardless of status | Only swap on 2xx; on 4xx/5xx or non-object tabs render the quiet empty state. Add an htmx `hx-target-error` or a `beforeSwap` guard for the right pane. |
| Med | Event log rows show command names ("edge.create", "body.set,object.create") that overlap the label column | `templates/browser/event_log.html` | Map command names to verbs (Created, Edited body, Linked, Unlinked) and give the grid fixed column widths with ellipsis. |

### B. Information architecture of the shell

| Sev | Finding | Where | Proposed change |
|-----|---------|-------|-----------------|
| High | Two full-width rails before any content (app sidebar 220px + Explorer). At 1440px about a third of the screen is navigation | `components/_sidebar.html`, `--sidebar-width` / `--sidebar-collapsed-width` in `theme.css` | Default the app sidebar to the 48px icon rail; expand on hover or Alt+\. The Explorer becomes the real left pane. |
| High | Admin, Meta, Apps and Debug groups are shown to every user, including API docs, Health Check and a disabled "CLI Console — coming soon" link | `components/_sidebar.html` | Admin under the user menu or a gear; Debug behind a developer toggle in Settings; the three importers under one Import entry; remove the "coming soon" link. |
| Med | Details pane stacks three identical "No object selected" states, plus Inbox and Collaboration even when federation is not configured | `browser/workspace.html` right pane, `partials/inbox_panel.html`, `partials/collaboration_panel.html` | One empty state when nothing is selected; render federation sections only when federation is enabled on the instance. |
| Med | OBJECTS header shows five action icons at rest. The CSS hover rule was overridden to `opacity: 1` | `workspace.css` `.explorer-header-actions` | Reveal on hover or focus-within; keep only "+" always visible. |
| Low | Types with zero instances take a full row | `nav_tree.html`, nav tree query | Show counts; fold empty types under "More types". |

### C. Action semantics

| Sev | Finding | Where | Proposed change |
|-----|---------|-------|-----------------|
| High | In edit mode Cancel is a filled green button and Save is an outlined red one; readers see Cancel as primary and Save as destructive | `workspace.css` `.mode-toggle`, `.btn-save`; `object_tab.html` toolbar | Save = single filled primary; Cancel = ghost button. Destructive red reserved for Delete. |
| Med | Three emphasis colours compete: blue `--color-primary` (tree active row), teal `--color-accent` (tabs), success green (Edit button) | `theme.css`, `workspace.css` | Pick one hue for interactive emphasis; demote the other to decorative use; never use `--color-success` for a mode toggle. |
| Low | Stray "◁▷" glyph beside the edit heading, orange square icons on every form group card, bordered "Form Guide" box above every form | `forms/object_form.html` and related partials | Remove the glyph, use plain uppercase group labels, make Form Guide a small help link. |
| Low | Two logos: hexagon in the sidebar, triangle-of-nodes mark on the login page | `_sidebar.html`, `frontend/static/login.html` | Pick one. |

### D. Per-screen polish

| Sev | Finding | Where | Proposed change |
|-----|---------|-------|-----------------|
| Med | Cards view: cards about 250px tall containing only a title | `cards_view.html`, `views.css` | Type chip, two-line excerpt, tags, modified date, relation count; roughly a third of the height. |
| Med | Graph view: dim overlapping labels under nodes, rotated always-on edge labels, unlabelled identical diamonds | `graph.js` Cytoscape style | Labels beside nodes with a halo; node colour by type using the tree icon colours; edge labels on hover/selection only; `fit()` on load. |
| Med | Spatial canvas toolbar: title and description wrap into a narrow column; "Save as" button clipped | `canvas_page.html`, canvas CSS in `workspace.css` | Real toolbar row; description moves to a tooltip. |
| Med | Read view truncates long values; inferred side column clips pills | `object_read.html`, `.property-table` CSS | Wrapping key/value list with inferred values marked inline (template already marks inline; CSS still clips). |
| Med | Reference tooltip left behind at the bottom of the editor across several captures | `ref_tooltip.html`, popover dismissal in `workspace.js` | Dismiss on tab switch, scroll and Escape. |
| Med | Markdown editor toolbar is "B I H 🔗" with an emoji link icon | `object_tab.html` editor toolbar | Lucide icons; add headings, lists, code, quote, link-to-object. |
| Med | Flip card for read/edit has caused three bleed-through bugs (see CLAUDE.md) and hides click-to-edit | `workspace.js` `toggleObjectMode`, `.object-face*` CSS | Consider click-to-edit on the body with inline property editing and an explicit "Edit properties" sheet; removes the global Edit/Save mode. Larger change; separate slice. |

### E. Typography, contrast, accessibility

| Sev | Finding | Where | Proposed change |
|-----|---------|-------|-----------------|
| High | No `:focus-visible` rule anywhere in the workspace CSS and twelve `outline: none` declarations; keyboard users lose the focus ring | `workspace.css`, `forms.css` | One global `:focus-visible` rule using `--color-focus-shadow`; remove bare `outline: none` or pair each with a visible replacement. |
| Med | Faint text fails WCAG AA: light `#999` on white, dark `#5c6370` on `#282c34` | `theme.css` `--color-text-faint` (used in ~65 places) | Raise one step: light `#767676` or darker, dark `#7d8799` or lighter. |
| Med | No `prefers-reduced-motion` handling; the 600ms flip is exactly what it exists for | `workspace.css` | Reduce the flip to a crossfade under reduced motion. |
| Med | One system font at ~13px with similar weights everywhere; tab title, toolbar title and body heading compete | `style.css` `--font-sans`, `theme.css` font tokens | Define a type scale; markdown body at ~16px with a 68ch measure; consider one deliberate typeface. |
| Low | Two media queries cover the whole workspace; desktop only | `workspace.css` | Tablet layout turning the two side panes into drawers. |

### Suggested slicing (one milestone)

1. **Labels and errors** — A.1 to A.4. Mostly backend label resolution plus two template fixes.
2. **Shell and semantics** — B.1 to B.4, C.1, C.2, E.1, E.2, E.3. CSS and sidebar template; no backend.
3. **Views and editor polish** — D.1 to D.6, C.3, C.4.
4. **Click-to-edit** (optional, larger) — D.7, E.4.

---

## Part 2 — What a PKM user expects today that SemPKM can't do

Status was checked by searching the codebase on 2026-11-03. "Verify" means not confirmed either way from source.

| Capability | Status | What exists / what is missing | Proposed scope |
|------------|--------|-------------------------------|----------------|
| Linking while writing | **Missing** | No `[[` autocomplete in the body editor, no slash commands, no "create note from link". Links exist only through form reference fields. `@codemirror/autocomplete` is already a dependency. | CodeMirror completion source backed by the Lucene search endpoint; `[[Label]]` resolves to an object IRI on save and creates a typed edge (default predicate per model, e.g. `bpkm:relatedNote`); unresolved links offer "create Note". Render as `.ref-pill` in read mode. |
| Daily notes / journal | **Missing** | No dated note with prev/next navigation or calendar entry point. | "Today" command (Alt+D) opening or creating a Note with `dcterms:date`; prev/next in the toolbar; calendar view already exists for navigation. |
| Quick capture | **Missing** | Palette → type picker → form is four steps for a fleeting note. | Global hotkey opens a one-field capture box; creates a Fleeting Note (zettelkasten) or Note (basic-pkm) tagged `inbox`; Explorer "Inbox" section. |
| Transclusion / embeds in a note | Partial | Embeds exist for canvas and dashboards, not inside a note body. | `![[Label]]` renders the target's read view inline via the existing `object_embed.html`. |
| Backlinks and unlinked mentions | Partial | Relations panel covers typed, directional backlinks well. Unlinked mentions not surfaced. | Lucene phrase query for the object's label across bodies; "Unlinked mentions" section in Relations with one-click link. |
| Hover previews | Partial | `ref_tooltip.html` shows type and name only. | Add the first ~200 chars of body or description to the tooltip payload. |
| Outline, word count, heading navigation | **Missing** | | Table of contents derived from rendered headings in the read view; word count in the editor status. |
| Home screen | **Missing** | Empty workspace says "Select an object from the Explorer". | Dockview watermark becomes Home: recent, favourites, today's note, quick capture, inbox count. |
| Per-note history | Partial | Event log with diff and undo is a developer surface. | "History" tab on the object: readable diffs, restore, filtered to that IRI (events module already supports per-event diff/undo). |
| Spaced repetition / review | **Missing** | | Out of scope here; see memory palace research "review walk" and the zettelkasten model. |
| Offline and mobile editing | **Missing** | Mobile app reports context only; no service worker. | Not proposed now. |
| Vault export as Markdown folder | Verify | WebDAV/VFS projects objects as files. | One-click ZIP export of the VFS projection from Settings. |
| Images / attachments in the editor | Verify | No confirmed drop-to-upload path into the body editor. | Drop → VFS resource → markdown image link. |
| Per-type note templates | Partial | Task templates and PPV review workflows exist. | Template body per SHACL shape applied on create. |

### Suggested slicing (two milestones)

- **PKM table stakes:** wikilink autocomplete, quick capture, daily notes, home screen. These four remove the biggest friction for Obsidian/Roam/Logseq switchers (see `.gsd/design/USER-CONVERSION-STRATEGY.md`, Tier 1 persona).
- **Reading and recall aids:** hover previews with excerpt, unlinked mentions, outline and word count, History tab, transclusion, per-type templates, Markdown export.

---

## Not in scope

- Memory palace mode: covered by `reports/Memory palace mode design research.md`.
- Generic views consolidation: already queued ("Rethink Views: Generic Views with Query Binding").
