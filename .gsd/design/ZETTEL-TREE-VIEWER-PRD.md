# Zettel Tree Viewer — Product Requirements Document

**Date:** 2026-10-10
**Status:** Draft (not yet scheduled into a milestone)
**Tracking issue:** https://github.com/MetaCoding-io/SemPKM/issues/64
**Depends on:** Views renderer registry (`backend/app/views/registry.py`), `zettelkasten` Mental Model, Workspace object tab/embed
**Owner:** James (jquacinella)

---

## Table of Contents

1. [Problem](#1-problem)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Users and Use Cases](#3-users-and-use-cases)
4. [Reference UI](#4-reference-ui)
5. [Requirements](#5-requirements)
6. [UX Specification](#6-ux-specification)
7. [Technical Approach](#7-technical-approach)
8. [Success Metrics](#8-success-metrics)
9. [Phasing](#9-phasing)
10. [Open Questions](#10-open-questions)
11. [References](#11-references)

---

## 1. Problem

Users of the `zettelkasten` Mental Model build chains of permanent notes using Luhmann-style sequence IDs (`4.1 → 4.1b → 4.1b1 → 4.1b1a1`). SemPKM can only show those notes as a flat table, a card grid, or a force-directed graph. None of those surfaces the **train of thought**: which note a given note continues, which notes branch off it, and where the chain ends. Users fall back to reading IDs by eye in a sorted table.

Michael Ashcroft's recent Obsidian viewer (see §4) shows the fix is a dedicated branching-tree layout plus a detail pane that explains each note's position in the chain. This PRD specifies the SemPKM equivalent.

## 2. Goals and Non-Goals

**Goals**

- G1. Let a user see every permanent note in a section as a branching tree keyed on its sequence ID, at a glance.
- G2. Let a user follow one train of thought from root to leaf without leaving the view.
- G3. Show, for any selected note, its chain (ancestors), explicit outgoing links, and backlinks.
- G4. Ship as a standard view renderer so it appears in the view toolbar and can be saved as a view spec like any other.
- G5. (Phase 2) Let a user restructure the tree by moving a note, re-numbering its subtree automatically.

**Non-Goals**

- Replacing the Cytoscape graph view or the canvas.
- A generic tree renderer for arbitrary transitive properties (may follow later, but the Folgezettel parser is what makes this layout useful).
- Rendering fleeting or literature notes in the tree. They remain reachable from the detail pane via provenance links.
- Any change to the `zettelkasten` ontology or SHACL shapes in Phase 1.

## 3. Users and Use Cases

| Persona | Need |
|---|---|
| **Zettelkasten practitioner** (primary) | Reviews a section of notes weekly to find where thinking has stalled and which branches are thin. |
| **Writer drafting from notes** | Follows one chain top to bottom to turn it into a draft; needs the ancestors visible while reading the leaf. |
| **New SemPKM user evaluating the ZK model** | Wants to see that the model "gets" Zettelkasten within the first session, not just a table of notes. |

User stories:

- US1. As a practitioner, I open the Permanent Notes view, switch to **Tree**, and see sections `1`, `2`, `3`… each as a tree of cards so I can spot where branches are thin.
- US2. As a practitioner, I click a card and see its full body plus the chain above it, so I can tell whether the note actually follows from its parent.
- US3. As a writer, I press **Train** on a leaf note and the view shows only that note's chain and descendants, so I can read one argument without noise.
- US4. As a practitioner, I use arrow keys to walk parent/child/sibling so I never need the mouse to traverse a chain.
- US5. (Phase 2) As a practitioner, I drag `4.1b2` under `4.1a` and it becomes `4.1a1` (with its children re-numbered), with no manual ID editing.
- US6. (Phase 2) As a practitioner, I click "+ child" on `4.1b` and a new permanent note is created with ID `4.1b1` (next free) and `followsFrom` set, so continuing a thought is one click.

## 4. Reference UI

**Michael Ashcroft, X, 2026-10-09** — <https://x.com/m_ashcroft/status/2108626231889367065>, screenshot <https://pbs.twimg.com/media/HUNYMnbWwAAHLir.jpg?name=orig>.

> "I have vibe coded a Zettelkasten viewer, which solves the problem of seeing all of my notes as a flat list in Obsidian. Now it's much easier to navigate and see trains of thought."

Observed behaviour:

| Element | Behaviour |
|---|---|
| Section header | `4  SECTION 4  — NO HEADING NOTE`. Tree is scoped to one integer section. A section with no heading note is flagged, not hidden. |
| Card | Fixed-width; monospace ID top-left (`4.1b1a1`); title clamped to 2–3 lines. |
| Layout | Children hang below the parent; siblings share a row; each suffix run is one level deeper; left gutter line per card. |
| Connectors | Orthogonal elbows from parent bottom to child top; siblings share a horizontal bus. |
| Selection | Gold border on the selected card; non-chain cards dimmed. |
| Detail pane (right) | Full body; **CHAIN** (ancestors, with *previous* link), **SEE** (outgoing links), **LINKED FROM** (backlinks). Buttons: Zoom, Train, Open, Obsidian, close. |

**Santi Younger, Branch Writing** (paid Obsidian plugin) — <https://platform.santiyounger.com/branch-writing>. Relevant idea: structure is a view over plain notes; moving a block re-orders it and "nothing breaks"; markers are stored invisibly so the document stays a document. This informs Phase 2 (reparenting rewrites `sequenceId`, nothing else).

## 5. Requirements

Numbering follows `.gsd/REQUIREMENTS.md` conventions so these can be promoted when scheduled. Priority: **P0** must ship in Phase 1; **P1** should ship in Phase 1; **P2** Phase 2.

### 5.1 Functional

#### ZT-01 — Tree renderer registered as a view type
- Class: functional · Priority: P0
- Description: A `tree` renderer exists in `RENDERER_REGISTRY` and appears in the view toolbar for any view spec whose target class has `zk:sequenceId` on its shape.
- Validation: Open Permanent Notes view → toolbar lists **Tree**; selecting it renders `browser/tree_view.html`. A view spec with `renderer: "tree"` round-trips through save/load.

#### ZT-02 — Folgezettel parent derivation
- Class: functional · Priority: P0
- Description: Parent ID is derived by stripping the last alphanumeric run: `4.1b1a1 → 4.1b1a → 4.1b1 → 4.1b → 4.1 → 4`. Runs alternate digits/letters; multi-digit (`4.12b`) and multi-letter (`4.1aa`) runs are single tokens. Section = integer before the first `.`.
- Validation: Unit tests cover the examples above plus `2.2a1b1a`, an ID with no `.`, and an ID whose derived parent does not exist.

#### ZT-03 — Natural ordering of siblings
- Class: functional · Priority: P0
- Description: Siblings sort by Folgezettel order (`4.1b2` before `4.1b10`; `4.1a` before `4.1b`), not lexically.
- Validation: Unit test with `[4.1b10, 4.1b2, 4.1b1]` yields `[4.1b1, 4.1b2, 4.1b10]`.

#### ZT-04 — Orphans are shown, never dropped
- Class: functional · Priority: P0
- Description: A note whose derived parent has no object is rendered under a synthetic "Unattached" root for its section, with a visible marker. A note with no `sequenceId` falls back to `zk:followsFrom` as its parent edge; cycles are cut at the first repeat.
- Validation: Seed one note with ID `9.3c` and no `9.3` → it renders under "Unattached" in section 9. Seed two notes that `followsFrom` each other → both render, no infinite loop.

#### ZT-05 — Section scoping
- Class: functional · Priority: P0
- Description: A section selector scopes the forest to one integer prefix. Default shows all sections, each collapsed to depth 2. When `zk:StructureNote`s exist, each StructureNote is offered as a section via `zk:includes` in addition to integer prefixes.
- Validation: Selecting section `4` shows only `4.*` cards. Selecting a StructureNote shows only the notes it includes.

#### ZT-06 — Card content
- Class: functional · Priority: P0
- Description: Each card shows the sequence ID (monospace, muted), the note label (standard RDF label precedence), clamped to 3 lines, and a left gutter in the type colour from the model manifest.
- Validation: Visual check against seed data; label precedence matches `CLAUDE.md` rule.

#### ZT-07 — Selection and chain highlighting
- Class: functional · Priority: P0
- Description: Clicking a card selects it. The selected card, its ancestors, and its descendants are highlighted; all other cards are dimmed. Selection is reflected in the URL (`?selected=<uri>`) so it survives reload and deep-links.
- Validation: E2E: select `4.1b1a1` → `4.1b1a`, `4.1b1`, `4.1b`, `4.1` carry `.on-chain`; `4.1a` carries `.dimmed`. Reload preserves selection.

#### ZT-08 — Detail pane
- Class: functional · Priority: P0
- Description: Selecting a card opens a right-hand pane containing the object embed (`browser/object_embed.html`) and three sections: **Chain** (ancestors, each clickable to re-select), **See** (outgoing `zk:*` object properties, grouped by predicate label), **Linked from** (backlinks). Empty sections show an explicit empty state ("No outgoing links", "Nothing links here yet").
- Validation: E2E: select a note with one `supports` link and one backlink → See lists one entry, Linked from lists one entry; select an isolated note → both empty states render.

#### ZT-09 — Open in workspace
- Class: functional · Priority: P0
- Description: An **Open** action on the detail pane (and `Enter` on a selected card) opens the note as a normal object tab in the workspace.
- Validation: E2E: press Enter on a selected card → `sempkm:tab-activated` fires with `isObjectTab: true` and the tab title is the note label.

#### ZT-10 — Train mode
- Class: functional · Priority: P1
- Description: A **Train** toggle re-roots the rendered forest on the selected note: ancestors collapse to a breadcrumb row at the top; the selected note and all descendants render fully expanded. Toggling off restores the section view with selection intact.
- Validation: E2E: Train on `4.1b` → cards rendered are exactly `4.1b` and its descendants; breadcrumb reads `4 › 4.1 › 4.1b`.

#### ZT-11 — Keyboard navigation
- Class: functional · Priority: P1
- Description: With focus in the tree: `↑` parent, `↓` first child, `←`/`→` previous/next sibling, `Enter` open, `T` toggle Train, `Esc` clear selection/close pane.
- Validation: E2E walks `4.1 → ↓ → 4.1a → → → 4.1b → ↓ → 4.1b1 → ↑ → 4.1b`.

#### ZT-12 — Default view spec in the model bundle
- Class: functional · Priority: P1
- Description: `models/zettelkasten/views/zettelkasten.jsonld` ships a `tree` view spec for `zk:PermanentNote` named "Trains of Thought".
- Validation: Fresh install of `zettelkasten` → "Trains of Thought" appears in My Views and renders seed data as a tree.

#### ZT-13 — Reparent by drag (Phase 2)
- Class: functional · Priority: P2
- Description: Dragging a card onto another card makes it the last child of the target. The dragged subtree is re-numbered (`4.1b2*` → `4.1a1*`) via `UpdateObject` commands on `zk:sequenceId`, one event per note, in a single command batch. `zk:followsFrom` on the moved root is updated to the new parent; descendants' `followsFrom` is untouched.
- Validation: E2E drag → event log shows N `UpdateObject` events; tree re-renders with new IDs; undo (reverse batch) restores the original.

#### ZT-14 — Quick-create child / sibling (Phase 2)
- Class: functional · Priority: P2
- Description: Hover/focus actions "+ child" and "+ sibling" open the PermanentNote form pre-filled with the next free sequence ID and `followsFrom` set to the parent.
- Validation: On `4.1b` with children `4.1b1`, `4.1b2`: "+ child" pre-fills `4.1b3`; "+ sibling" pre-fills `4.1c`.

#### ZT-15 — Lint rule for chain/ID disagreement (Phase 2)
- Class: functional · Priority: P2
- Description: A SHACL-AF warning in `models/zettelkasten/rules/` fires when `zk:followsFrom` points at a note that is not the derived parent by `sequenceId`.
- Validation: Lint panel shows the warning on a seeded conflicting note; clears after fixing either value.

### 5.2 Non-functional

#### ZT-20 — Render performance
- Class: non-functional · Priority: P0
- Description: A section with 500 notes renders (server response + first paint) in under 1 s on the dev stack; 2,000 notes across all sections with depth-2 collapse in under 2 s.
- Validation: Timed E2E against a generated fixture.

#### ZT-21 — Pure CSS layout, no new runtime dependency
- Class: non-functional · Priority: P0
- Description: Tree layout and connectors are CSS (`frontend/static/css/tree-view.css`); interaction is a vanilla IIFE (`frontend/static/js/tree-view.js`) on `window.SemPKM`. No new CDN or npm dependency.
- Validation: Code review; `package.json` diff empty.

#### ZT-22 — Theme and icon conventions
- Class: non-functional · Priority: P0
- Description: Colours come from `theme.css` tokens and work in light and dark. Lucide icons sized in CSS with `flex-shrink: 0` and `stroke: currentColor` per `CLAUDE.md`.
- Validation: Visual check in both themes; no inline icon sizing in the template.

#### ZT-23 — Responsive fallback
- Class: non-functional · Priority: P1
- Description: Below 768 px the tree renders as an indented outline (same DOM, different CSS) rather than a horizontal tree.
- Validation: Viewport 375 px → no horizontal scroll; nesting visible via indentation.

#### ZT-24 — Accessibility
- Class: non-functional · Priority: P1
- Description: Tree uses `role="tree"` / `role="treeitem"` with `aria-level`, `aria-expanded`, `aria-selected`; the detail pane is `aria-live="polite"`. Keyboard model in ZT-11 is the WAI-ARIA tree pattern.
- Validation: axe scan in E2E reports no violations on the view.

## 6. UX Specification

**Layout.** Two-pane: tree canvas (fills available width, scrolls both axes) and a collapsible detail pane on the right (default 360 px, resizable via the existing panel drag-drop). A header row holds: section selector, Train toggle, expand/collapse-all, density toggle (title-only vs title + first 100 chars of `zk:body`).

**Card states.** `default` · `on-chain` (full opacity, accent gutter) · `selected` (accent border, `aria-selected`) · `dimmed` (40 % opacity) · `unattached` (dashed border, "no parent" badge) · `collapsed` (chevron, child count badge).

**Connectors.** Elbow lines drawn with `::before`/`::after` on the `<li>` using `border-left`/`border-top`, 1 px, `--color-border`; on-chain connectors use `--color-accent`.

**Detail pane sections.** Object embed → **Chain** (list, nearest ancestor first, each row `ID · label`, with a "previous" affordance) → **See** (grouped by predicate label) → **Linked from** (grouped by predicate label). Header actions: Zoom (scroll tree so selection is centred), Train, Open, close.

**Empty states.** No notes with `sequenceId` in the target class → "No sequence IDs yet. Add a Sequence ID to a permanent note to see it here." with a link to the ZK model docs.

## 7. Technical Approach

- **Backend.** New `tree` entry in `RENDERER_REGISTRY` (`backend/app/views/registry.py`). One SPARQL query over `urn:sempkm:current` returning `(uri, label, sequenceId, followsFrom, type)` filtered by the view spec; a `folgezettel.py` helper (parser, parent derivation, natural sort) builds the forest; the renderer branch in `backend/app/views/service.py` / `router.py` passes `sections[]` to Jinja. Detail pane sections are a second htmx endpoint `GET /ui/tree/detail/{uri}` returning the three lists.
- **Frontend.** `browser/tree_view.html` (recursive macro producing `<ul role="tree">`), `tree-view.css`, `tree-view.js`. Selection state in the URL; pane content loaded via htmx; `sempkm:tab-activated` used for Open.
- **Model bundle.** Default view spec in `models/zettelkasten/views/zettelkasten.jsonld`.
- **Phase 2 writes** go through `POST /api/commands` as a batch of `UpdateObject` events, so they are event-sourced and undoable like every other write.

## 8. Success Metrics

- Tree view is used in ≥ 30 % of sessions that open the Permanent Notes view within 30 days of release (PostHog `view_rendered` with `renderer=tree`).
- Median time from opening the view to opening an object tab from it is under 10 s (proxy for "found the note I wanted").
- Zero P0/P1 bugs filed against ZT-02/ZT-03 (parsing) in the first release.

## 9. Phasing

| Phase | Requirements | Deliverable |
|---|---|---|
| **1 — Read-only tree** | ZT-01…ZT-12, ZT-20…ZT-24 | Renderer, detail pane, Train, keyboard nav, default view spec, E2E |
| **2 — Structural editing** | ZT-13…ZT-15 | Drag-to-reparent with renumbering, quick-create, lint rule |

## 10. Open Questions

1. **Section source.** Integer prefix (`4.`) vs `zk:StructureNote`. ZT-05 proposes both; confirm the StructureNote mapping is intuitive before building it.
2. **Title-only vs body preview** on cards by default. ZT-06 says title; the density toggle covers the rest. Confirm.
3. **Sibling-order for letters past `z`.** Luhmann used `aa`, `ab`; some tools use `z1`. ZT-02 assumes multi-letter runs are single tokens (`aa` sorts after `z`). Confirm.
4. **Should Train mode be a view-spec setting** (persisted) or session-only? Leaning session-only in Phase 1.

## 11. References

- Michael Ashcroft, "I have vibe coded a Zettelkasten viewer…", X, 2026-10-09 — <https://x.com/m_ashcroft/status/2108626231889367065>
- Santi Younger, *Branch Writing* — <https://platform.santiyounger.com/branch-writing>
- `models/zettelkasten/README.md` — Sequence ID field; `models/zettelkasten/ontology/zettelkasten.jsonld` — `zk:sequenceId`, `zk:followsFrom`
- `backend/app/views/registry.py` — renderer registry
- `.gsd/design/VIEWS-RETHINK.md` — prior views design context
