# Zettel Tree Viewer — Folgezettel / Train-of-Thought Navigation

**Status:** Research / Early Design (lightweight design doc — not yet scheduled)
**Date:** 2026-10-10
**Tracking issue:** https://github.com/MetaCoding-io/SemPKM/issues/64
**Context:** SemPKM — Semantic Personal Knowledge Management, `zettelkasten` Mental Model

---

## 1. Why this doc exists

Two external references prompted this:

1. **Michael Ashcroft, X post, 2026-10-09** — <https://x.com/m_ashcroft/status/2108626231889367065>
   > "I have vibe coded a Zettelkasten viewer, which solves the problem of seeing all of my notes as a flat list in Obsidian. Now it's much easier to navigate and see trains of thought."
   Screenshot: <https://pbs.twimg.com/media/HUNYMnbWwAAHLir.jpg?name=orig>
   A follow-up post by the same author ("pretty cool") shows a second, deeper tree (the `2.1a` / `2.2a1b1a` meditation notes).

2. **Santi Younger, "Branch Writing" (paid Obsidian plugin)** — <https://platform.santiyounger.com/branch-writing>
   Card-based writing where structure emerges as you write; blocks are dragged or moved with shortcuts; card boundaries are stored as hidden comments in the Markdown so the document stays a plain document.

Both solve the same problem SemPKM currently has for the `zettelkasten` model: **permanent notes are only visible as a flat list, a table, a card grid, or a force-directed graph**. None of those show a *train of thought* — the Luhmann-style branching sequence (`4.1 → 4.1b → 4.1b1 → 4.1b1a → 4.1b1a1`) that is the whole point of Folgezettel numbering.

---

## 2. What the reference UI does (observed from the screenshot)

The Ashcroft viewer is a **top-down branching tree of note cards**, one card per zettel, laid out by Folgezettel ID.

| Element | Observed behaviour |
|---|---|
| **Section header** | Top-left: `4  SECTION 4  — NO HEADING NOTE`. The tree is scoped to one top-level section (the integer prefix). Sections without a heading note are flagged rather than hidden. |
| **Card** | Small fixed-width card: monospace ID in the corner (`4.1b1a1`), then the note's title/first line in 2–3 lines, truncated. |
| **Layout** | Children hang *below* their parent. Siblings (`4.1a`, `4.1b`) sit side by side in the same row. Each new letter/number suffix is one level deeper. A vertical gutter line on the left of each card marks the branch. |
| **Connectors** | Orthogonal (elbow) lines from parent bottom-edge to child top-edge; sibling cards share a horizontal bus. |
| **Selection** | Clicking a card highlights it (gold border) and opens a **detail pane** on the right. |
| **Detail pane** | Full note body, plus three sections: **CHAIN** (the Folgezettel ancestry — `4.1b1a  Even the most faceless bureaucracy…` with a *previous* link), **SEE** (outgoing explicit links, "No see links."), **LINKED FROM** (backlinks, "Nothing links here yet."). Header buttons: `Zoom`, `Train`, `Open`, `Obsidian`, close. |
| **"Train"** | Presumably re-roots the tree on the selected note so only its chain and descendants are shown (the "train of thought"). |
| **"Zoom"** | Presumably zooms the canvas to fit the selected subtree. |
| **Dimming** | Cards not on the selected chain are rendered at lower opacity, so the active train reads as a bright path through a dim tree. |

Branch Writing contributes one further idea worth borrowing: **the structure is a view, not a separate data structure**. Moving a card re-numbers it; nothing is exported or duplicated.

---

## 3. Why it fits SemPKM

The `zettelkasten` Mental Model already carries everything the layout needs:

| Need | Already in the model |
|---|---|
| Folgezettel ordering | `zk:sequenceId` — "Luhmann-style alphanumeric sequence identifier for ordering permanent notes (e.g. `1a2b3`)" (`models/zettelkasten/ontology/zettelkasten.jsonld`) |
| Explicit "follows" relation | `zk:followsFrom` (argumentation link) |
| Provenance chain (fleeting → literature → permanent) | `zk:processedInto`, `zk:derivedFrom`, `zk:developedInto` / `zk:developedFrom` |
| SEE / LINKED FROM | `zk:supports`, `zk:contradicts`, `zk:relatedTo`, `zk:includedInStructure`, plus the generic backlink query the object tab already uses |
| Grouping into sections | `zk:StructureNote` + `zk:includes` can act as the "section" when no integer prefix is used |

So this is almost entirely a **renderer** problem. No new predicates are required for v1.

Renderers are pluggable (`backend/app/views/registry.py` → `RENDERER_REGISTRY`, with `register_renderer()` for model-contributed types) and the toolbar lists whatever is registered. A `tree` (or `zettel-tree`) renderer slots in beside `table`, `card`, `graph`, `kanban`, etc. The existing `hierarchy_tree.html` / `hierarchy_children.html` partials (`backend/app/browser/workspace.py`) show the htmx lazy-expansion pattern for nested children, which v1 can reuse for the data path even if the visual layout is new.

---

## 4. Proposed design (v1)

### 4.1 Data model

Parent is derived, not stored. Given a `zk:sequenceId`, the parent ID is the ID with its last alphanumeric run stripped:

```
4.1b1a1 → 4.1b1a → 4.1b1 → 4.1b → 4.1 → 4
2.2a1b1a → 2.2a1b1 → 2.2a1b → 2.2a1 → 2.2a → 2.2 → 2
```

Rule: alternate runs of digits and letters; the first segment before the `.` (if present) is the section. Implement once in Python (`backend/app/views/service.py` or a small `folgezettel.py` helper) with unit tests covering: missing `.`, multi-digit runs (`4.12b`), multi-letter runs (`4.1aa`), and IDs whose parent does not exist (render under a synthetic "orphan" root, never drop them).

Fallback when a note has **no** `zk:sequenceId` but has `zk:followsFrom`: treat `followsFrom` as the parent edge. Cycles are cut at the first repeat.

### 4.2 Backend

- New renderer `tree` registered in `RENDERER_REGISTRY` with template `browser/tree_view.html`.
- One SPARQL query over `urn:sempkm:current` returning `(uri, label, sequenceId, followsFrom, body-snippet)` for the view's target class, with the standard view-spec filters applied.
- Python builds the forest (list of roots, each with ordered children sorted by natural Folgezettel order, i.e. `4.1b2` before `4.1b10`) and passes it to Jinja. Depth is unbounded; the template recurses.
- Endpoint shape follows the other renderers in `backend/app/views/router.py` (`view_type: "tree"`).

### 4.3 Frontend

- **Template** `browser/tree_view.html`: nested `<ul>/<li>` of `.zt-card` elements. Pure CSS tree (CSS grid or flex rows per sibling group, `::before`/`::after` pseudo-elements for the elbow connectors). No canvas library for v1.
- **CSS** `frontend/static/css/tree-view.css` (one file per renderer, per `CODEBASE.md`). Card: ID in monospace muted text, title clamped to 3 lines, left gutter border in the type colour from the model manifest.
- **JS** `frontend/static/js/tree-view.js` (IIFE on `window.SemPKM`): selection, chain highlighting (add `.on-chain` to ancestors, `.dimmed` to everything else), and the detail pane.
- **Detail pane**: reuse the existing object embed (`browser/object_embed.html`) loaded via htmx into a right-hand panel, then add three sections underneath: **Chain** (derived ancestors, each a link that re-selects), **See** (outgoing `zk:*` object properties), **Linked from** (backlinks). `Open` opens the normal object tab in the workspace.
- **Train mode**: toggle that re-roots the rendered forest on the selected note (ancestors collapsed into a breadcrumb at the top, descendants fully expanded).
- Lucide icons follow the `CLAUDE.md` rule: sized in CSS with `flex-shrink: 0`, `stroke: currentColor`.

### 4.4 Interaction

| Action | Result |
|---|---|
| Click card | Select; highlight chain; load detail pane |
| `↑ ↓ ← →` | Move to parent / first child / previous sibling / next sibling |
| `Enter` | Open as object tab |
| `T` | Toggle Train mode on the selection |
| Section dropdown | Scope the forest to one top-level section (default: all sections, collapsed to depth 2) |
| Drag card onto another (v2) | Re-number subtree under the new parent (emits `UpdateObject` commands for `zk:sequenceId`) — this is the Branch Writing idea and is the only write path |

---

## 5. Scope split

**v1 — read-only tree renderer** (ships the value in the screenshot)
- Folgezettel parser + tests
- `tree` renderer, template, CSS, JS
- Detail pane with Chain / See / Linked from
- Train mode + keyboard nav
- Default `tree` view spec added to `models/zettelkasten/views/zettelkasten.jsonld` for `zk:PermanentNote`
- E2E: render seed data, select a card, assert chain highlight and detail pane content

**v2 — structural editing**
- Drag-to-reparent with subtree re-numbering
- "Insert sibling after" / "Insert child" quick-create from a card (pre-fills `zk:sequenceId` and `zk:followsFrom`)
- Auto-assign the next free Folgezettel ID when a permanent note is created from the tree

**Out of scope for now**
- Generic tree renderer for any `owl:TransitiveProperty` (nice later, but the Folgezettel-specific parser is what makes the layout useful)
- Replacing the Cytoscape graph view

---

## 6. Open questions

1. **Where does the section (integer prefix) come from when users don't number that way?** Option A: require `N.` prefix. Option B: treat each `zk:StructureNote` as a section via `zk:includes`. Lean: support both, prefer `StructureNote` when present.
2. **Should `followsFrom` and `sequenceId` disagree?** They can. v1 trusts `sequenceId` and shows a lint warning (SHACL-AF rule in `models/zettelkasten/rules/`) when `followsFrom` points at a note that is not the derived parent.
3. **Card body preview** — title only (as in the screenshot) or first ~100 chars of `zk:body`? Start with title; add a density toggle if asked.
4. **Mobile** — the tree is wide. Fall back to an indented outline below a breakpoint rather than trying to scale the elbows.

---

## 7. Tracking

GitHub issue: https://github.com/MetaCoding-io/SemPKM/issues/64
