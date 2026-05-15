# Notebook Sync & the Channel Concept

**Status:** Research / Early Design
**Date:** 2026-05-15
**Context:** SemPKM — Semantic Personal Knowledge Management

---

## 1. Motivation

Many SemPKM users keep a physical notebook for daily tasks, ideas, and journaling. The current system has no way to bridge that analog surface to the graph — paper stays paper, the graph stays digital, and the two drift apart.

This doc proposes a **Notebook channel**: a way to project the graph onto a physical notebook (via a digital twin view) and capture analog edits back via photo snapshots, mapped to typed objects in the graph.

Along the way it also introduces **"channel"** as a shared piece of vocabulary for talking about how the graph surfaces in different mediums (VFS, Obsidian, Notebook, reMarkable, voice, etc.). The vocabulary is intentionally just vocabulary today — there is no shared base class or adapter framework being proposed. If the pattern hardens across several channels, formalizing it in code later is straightforward and easy to defer.

---

## 2. The Channel Concept (vocabulary)

A **channel** is any surface where the graph shows up and where edits can flow back. Each channel is its own module; implementations have nothing structurally in common beyond the conceptual pattern.

### Four sub-patterns

Channels tend to fall into one of four shapes. These are useful for talking about channels and reasoning about their UX, not for unifying code.

| Pattern | Shape | Examples |
|---|---|---|
| **A. Lossy Capture** | freeform input → extractor → candidates → reconcile | Paper notebook, voice memo, email-in, screenshot, whiteboard photo |
| **B. Structured Sync** | schema mapping ↔ external system, identity by external ID | Obsidian vault, VFS, Calendar (CalDAV), GitHub Issues, CRM |
| **C. Render Out** | view spec → external format, mostly one-way | reMarkable PDF, public site, email digest, agenda print, RSS |
| **D. Quick-Capture Push** | single-shot input → graph, no review loop | Mobile home-screen widget, SMS bot, Slack `/capture`, watch shortcut |

### Current and proposed channels

| Channel | Status | Pattern(s) | Module |
|---|---|---|---|
| VFS (graph-as-files) | Implemented | B | `app/vfs` |
| Obsidian vault sync | Implemented | B | `app/obsidian` |
| Notebook (paper) | **This doc** | A | `app/notebook` (new) |
| reMarkable render | Proposed | C | future |
| Voice quick-capture | Proposed | A + D | future |
| Email-in | Proposed | A | future |
| Mobile quick-capture widget | Proposed | D | `mobile/` (existing dir) |
| Browser web-clipper | Proposed | A | `extension/` (existing dir) |
| Calendar bidirectional | Proposed | B | future |
| Apple Reminders / Todoist / Google Tasks | Proposed | B | future |
| SMS / Telegram bot | Speculative | D | future |
| Slack `/sempkm` | Speculative | A + D | future |
| Public site / digital garden | Speculative | C | future |
| Whiteboard photo | Speculative | A | future |
| Business card scan | Speculative | A | future |
| Kindle highlights sync | Speculative | B | future |
| GitHub Issues bidirectional | Speculative | B | future |

### When to formalize in code

If/when three or more channels of the same pattern exist, lifting their common shape into shared infrastructure becomes worthwhile. Likely candidates if/when that day comes:

- A shared **reconciliation service** for Pattern A channels (notebook, voice, email-in, screenshot all do "candidates vs current graph → commands")
- A shared **render contract** for Pattern C channels (reMarkable, public site, agenda print all need a "renderable view" menu)
- A shared **OAuth/webhook substrate** for true-remote Pattern B channels (Calendar, Reminders, Issues)

Until then, each channel stays self-contained. Don't pre-build.

### Cross-channel provenance (small shared addition)

One small shared addition is worth making upfront because it affects every channel: a **provenance bit** on objects so the UI can show "this task came from your notebook" or "last edited via Obsidian." This is a property, not a framework.

- `sempkm:capturedFromChannel <channelIri>` — origin channel
- `sempkm:lastEditChannel <channelIri>` — most recent channel to write
- `sempkm:Channel` instances in the graph for each configured channel (notebook, vault, vfs mount, etc.)

This unblocks the bidirectional conflict UI described later and costs almost nothing to add.

---

## 3. Notebook Channel — Detailed Spec

### 3.1 Core moves that simplify the problem

Two design decisions that eliminate whole classes of difficulty before they exist:

**Paper does not own time.** The app owns all temporal data — due dates, scheduled blocks, completion dates. Paper owns content and structure. No date inference from photos, no date headers parsed, no multi-day pages. The user fills in dates in the SemPKM dashboard.

**The user declares the page type at capture.** Instead of inferring layout from visual features (hard, brittle), the user picks "this is a task page" or "this is a project page" before the photo is taken. The page type is a named bundle of extraction rules. Template drift dissolves; mixed layouts in one notebook are fine.

### 3.2 Digital twin notebook (setup, one-time)

Before capturing anything, the user creates a **digital twin** of their notebook in the app:

- `nb:Notebook` — a name, optional color/cover image, ID
- `nb:Page` — explicit pages `P1..PN` created upfront, each assigned a **page type**
- `nb:PageType` — a named bundle of extraction rules. v1 ships with three:
  - `task` — bullet list with Bujo-style glyphs
  - `project` — title region + bullet list, items link to the named project
  - `freeform` — OCR the whole page to a single `bpkm:Note`, no structure attempted

Custom user-defined page types (with region drawing) are **v2**. v1 keeps it to the three built-ins.

### 3.3 Bujo glyph table → graph properties

The `task` and `project` page types use a glyph alphabet inspired by bullet journaling. Defaults:

| Glyph | Maps to |
|---|---|
| `•` task | `bpkm:Task` |
| `○` event | `bpkm:Event` |
| `–` note | `bpkm:Note` |
| `×` (filled) | `bpkm:Task` + `bpkm:status = completed` |
| `>` migrated | `bpkm:status = migrated` |
| `<` scheduled | (links to scheduled item; user fills time in app) |
| `*` priority | `bpkm:priority = high` |
| indent | `bpkm:partOf` parent line |

The glyph table is data, not code. v2 can let users customize it.

### 3.4 Capture flow

```
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Pick notebook  │→ │ Pick page (Pn) │→ │ Page type      │
│ (dropdown)     │  │ (dropdown)     │  │ pre-filled     │
└────────────────┘  └────────────────┘  └────────────────┘
                                                 │
                                                 ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Mobile camera  │→ │ Realtime page  │→ │ Snap → upload  │
│ viewfinder     │  │ outline +      │  │                │
│                │  │ region overlay │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
                                                 │
                                                 ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Deskew +       │→ │ VLM extraction │→ │ Reconcile vs   │
│ perspective    │  │ per page type  │  │ existing slots │
│ correct        │  │                │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
                                                 │
                                                 ▼
┌────────────────┐  ┌────────────────┐
│ Confirm UI     │→ │ POST /commands │
│ (diff view)    │  │ (batched)      │
└────────────────┘  └────────────────┘
```

### 3.5 Capture-time UX details

- **Capture sessions, not single shots.** Take multiple photos in a row, page-type prompt per shot, batch review at the end.
- **Realtime alignment overlay on mobile.** Camera viewfinder shows expected page outline + region zones for the chosen page type. Green when aligned within tolerance, red when not. Eliminates retake friction.
- **Template-drift detection for free.** If the overlay drifts consistently from the actual page content, app surfaces "your layout looks different — recalibrate?"
- **Tap-region affordance.** Tap a region in the overlay to see what rule will run ("this area = bujo-list, ~12 lines expected").
- **Hash-skip unchanged pages.** If extracted candidates are byte-identical to last scan, no-op silently. Lets users re-scan a whole notebook periodically without diff fatigue.
- **Scratch fallback.** Anything inside the photo but outside the page-type's rules drops to a `bpkm:Note` tagged `nb:unparsed`, linked to the snapshot. Nothing silently lost.

### 3.6 Identity & reconciliation

The hard problem in any Pattern A channel: **how do we know that the "buy milk" in today's photo is the same task as yesterday's?**

For the notebook channel, the answer is a composite key:

```
(notebookId, pageNumber, regionId, slotIndex)
```

- `notebookId` — from the digital twin (user picks at capture)
- `pageNumber` — from the digital twin (user picks at capture)
- `regionId` — from the page type's rule definitions
- `slotIndex` — line position within the region (1, 2, 3, …), derived from row grid or sequential Y-position

This sidesteps text-fuzzy-matching entirely. We're matching **geometry**, not handwriting. A smudged or rewritten line still resolves to the same slot.

**Reconciliation cases:**

- Key exists in graph, text unchanged, glyph unchanged → no-op
- Key exists, text/glyph changed → emit update command
- Key new (slot was empty last time, has content now) → emit create command
- Key existed, slot now empty → flag for archival (don't auto-delete; could be a torn-out page or temporary erasure)

Each created object carries `nb:capturedFromLine <slotIri>` linking it back to the snapshot for audit.

### 3.7 Ink accumulation on the same line

A real journal accumulates: today's task gets crossed out tomorrow, annotated next week, arrowed to next month. Reconciliation behavior is per-page-type:

- **Task page** — appended text treated as an edit to the task label. Prior versions live in the event log (free via event sourcing).
- **Project page** — appended text becomes a child `bpkm:Note` linked via `bpkm:partOf` to the project's relevant item.

Predictable per-type behavior beats per-line ambiguity.

### 3.8 Cross-page linking

Project pages have a title region. The title is the linking key for items on other pages that reference the project name. Fuzzy match with confirm-on-low-confidence, never silent auto-link.

---

## 4. Digital Twin Viewer

The twin viewer is a **paper-side view** of the graph — a navigation surface no other channel offers. It leverages spatial memory ("I know it was bottom-right of page 12") that table/kanban/graph views can't.

### 4.1 What it shows

For each scanned page, the viewer renders the corrected scan image with absolute-positioned clickable overlays per extracted line. Clicking a line navigates to the object in the workspace.

### 4.2 Drift visualization

The viewer renders **graph state** on top of the photo, not just the photo. If a task is `completed` in the graph but the ink shows it open, the overlay strikes it through anyway. Paper becomes a live document, not a static archive.

This subsumes the "to mark in notebook" reminder list — the user can see at a glance which lines need a pen stroke to bring paper in sync with the graph.

### 4.3 Reconciliation fallback surface

When extraction fails on a line (low confidence, unparseable), the twin viewer shows the cropped ink crop with a "couldn't parse — click to add manually" CTA. Nothing gets silently dropped.

### 4.4 Snapshot staleness

Each page shows "scanned N days ago" — sets expectations and prompts rescans of stale pages.

### 4.5 Storage

Photos accumulate; a few hundred KB compressed each, ~1GB/year for an active journaler. Retention policy: keep full-res for N months (configurable, default 6), then downsample to thumbnail + bbox metadata (which is what actually drives the twin viewer anyway).

---

## 5. Bidirectional Awareness

The paper and the app will get out of sync — that's inherent. We design for it explicitly.

### 5.1 The flag

Every editable object carries `sempkm:lastEditChannel <channelIri>` (the cross-channel provenance addition from §2). On reconciliation:

- App newer, paper unchanged → keep app version, surface in twin viewer drift overlay
- Paper newer → accept paper changes, update flag
- Both edited since last sync → conflict UI: show both versions, user picks (or merges)

### 5.2 "To mark in notebook" affordance

A dashboard listing tasks completed/edited in the app but still open/stale on paper. Lets the user batch-update their notebook with a pen while drinking coffee. Respects paper as the canonical analog state — the app never demands paper be updated, just makes it easy.

### 5.3 Photo as ground-truth artifact

Always store the cropped page image with extracted objects (`nb:capturedFrom`). When reconciliation gets weird, the user can click any object and see the source ink.

---

## 6. Out of Scope for v1

Explicit non-goals — note them as known limitations, don't fake support:

- **Marginalia, arrows, freehand sketches** — region-based extraction won't capture cross-line scribbles or doodles. They live only in the snapshot photo for v1.
- **Cross-page arrows / "see p.34" refs** — out of scope for v1.
- **Multi-day journal pages** — dates aren't inferred from paper; if a user writes "May 14" and "May 15" on one page, both get treated as the same page's content.
- **Automatic template matching from visual features** — v1 uses explicit page-type picker. CV-based layout inference is v2 at earliest.
- **Custom user-defined page types with region drawing** — v1 ships three built-in types only.
- **Reverse stroke-sync from reMarkable / e-ink** — that's a future channel, not part of notebook channel.
- **Local-only / on-device VLM inference** — v1 uses cloud VLM. Privacy-conscious users will need to wait for v2 or run a self-hosted model.

---

## 7. Open Design Questions

1. **Where the page-type editor lives in the UI** — new panel in the existing workspace, or a dedicated `/notebook` route?
2. **Where the twin viewer lives** — new panel, new top-level workspace tab, or dedicated `/notebook/<id>` route?
3. **Mobile capture surface** — extend the existing `mobile/` app, or web-based PWA capture? Realtime alignment overlay is meaningfully easier in native (ARKit/ARCore) than in a PWA.
4. **VLM provider** — pluggable like the rest of the stack, or Claude-only for v1?
5. **Should the existing Obsidian module be retrofitted** with the `sempkm:capturedFromChannel` / `sempkm:lastEditChannel` provenance properties, or left alone for v1? (Retrofitting is small and proves the pattern across channels.)
6. **Notebook covers vs. notebooks** — is a "notebook" in the digital twin one physical book, or can it represent a series (vol. 1, vol. 2)? Probably one book per `nb:Notebook` for v1, with cross-notebook linking handled at the graph level.

---

## 8. Suggested Build Order

1. **Provenance properties** — add `sempkm:Channel`, `sempkm:capturedFromChannel`, `sempkm:lastEditChannel` to the core. Optionally backfill Obsidian/VFS as channel instances.
2. **Digital twin notebook model** — `nb:Notebook`, `nb:Page`, `nb:PageType`, `nb:Snapshot`, `nb:LineSlot`, `nb:capturedFromLine`, `nb:capturedFrom`. New mental model bundle `notebook-sync`.
3. **Page-type editor UI** — minimal: create notebook, create pages, assign page types. No custom region drawing yet.
4. **Capture API** — `POST /api/notebook/snapshots` accepts photo + (notebookId, pageNumber, pageType), runs deskew + VLM extraction, returns candidate set without committing.
5. **Confirm UI** — review extracted candidates side-by-side with the photo crop, edit in place, approve → batched `POST /api/commands`.
6. **Reconciliation logic** — composite-key matching, diff generation, per-page-type append behavior.
7. **Twin viewer** — clickable overlays, drift visualization, staleness badges.
8. **Mobile capture flow** — alignment overlay, capture session batching. Native if feasible; PWA fallback otherwise.
9. **Bidirectional dashboard** — "to mark in notebook" list, conflict resolution UI.
