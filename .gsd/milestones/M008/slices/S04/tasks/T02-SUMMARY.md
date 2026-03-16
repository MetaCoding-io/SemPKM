---
id: T02
parent: S04
milestone: M008
provides:
  - Chapter 27 documentation for node resizing, property flip, and live embeds
  - Glossary entries for "Embed Node" and "Property Flip"
  - Updated "What Gets Saved", Toolbar table, and comparison table for M008 features
  - New practical workflow example "Building a Research Dashboard on Canvas"
key_files:
  - docs/guide/27-spatial-canvas.md
  - docs/guide/appendix-d-glossary.md
key_decisions: []
patterns_established:
  - Feature documentation follows existing chapter style: section heading → explanation → bullet details → persistence note → tip callout
observability_surfaces:
  - grep '^## ' docs/guide/27-spatial-canvas.md — lists all section headings (should include Resizing Nodes, Property Flip, Live Embeds)
  - grep -n 'Embed Node\|Property Flip' docs/guide/appendix-d-glossary.md — confirms glossary entries exist at expected positions
  - tail -3 docs/guide/27-spatial-canvas.md — confirms nav footer chain ch.26 → ch.27 → ch.28 intact
duration: 20m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: User Guide Chapter 27 Update and Glossary

**Extended chapter 27 with three new feature sections (Resizing Nodes, Property Flip, Live Embeds), updated existing sections, and added two glossary entries.**

## What Happened

Updated `docs/guide/27-spatial-canvas.md` with all M008 canvas features:

1. **Node Anatomy** — added Flip button (between Expand and Delete) and resize handles description
2. **Toolbar table** — added Embed row
3. **Resizing Nodes** section — corner/edge/bottom handles, 24px grid snapping, 160px/80px min constraints, 260px default, persistence, backward compat
4. **Property Flip** section — flip button behavior, property table contents (type label, SHACL-derived rows, multi-value pills, boolean ✓/✗, inferred properties, dash for empty), persistence with re-fetch on reload
5. **Live Embeds** section — embed concept, 4-type table (View/Dashboard/SPARQL/Object Read), toolbar picker flow (3 tabs), explorer drag-drop, max 8 limit, default 400×300 size, resizable, live updates
6. **What Gets Saved** — added node dimensions, property flip state, embed configurations
7. **Comparison table** — added Embeds row (No vs live iframes)
8. **Practical Workflows** — added "Building a Research Dashboard on Canvas" workflow example

Updated `docs/guide/appendix-d-glossary.md` with two entries in alphabetical order:
- **Embed Node** (after Edge, before Entailment)
- **Property Flip** (after PKCE, before Property)

## Verification

- **Section headings**: All 14 `##` sections present including 3 new ones (Resizing Nodes, Property Flip, Live Embeds)
- **Nav footer**: ch.26 → ch.27 → ch.28 chain intact on both chapter and glossary files
- **Glossary placement**: "Embed Node" at line 28 (between Edge/Entailment), "Property Flip" at line 91 (between PKCE/Property)
- **Table formatting**: Toolbar table, embed types table, and comparison table all have consistent pipe-column markdown
- **No broken references**: All feature descriptions match implemented behavior from S01-S03 summaries
- **Line count**: 252 lines total (117 new lines added)

### Slice-level verification status (T02 is final task):
- `docs/guide/27-spatial-canvas.md` — ✅ markdown renders cleanly, navigation chain intact
- Glossary entries alphabetically placed — ✅ confirmed
- E2E tests (from T01) — not re-run (docs-only task, no code changes)
- Backend unit tests (from T01) — not re-run (docs-only task, no code changes)

## Diagnostics

- `grep '^## ' docs/guide/27-spatial-canvas.md` — lists all section headings for quick structural check
- `grep -n 'Embed Node\|Property Flip' docs/guide/appendix-d-glossary.md` — confirms glossary entries at expected line numbers
- `wc -l docs/guide/27-spatial-canvas.md` — should be ~252 lines

## Deviations

None — all 10 plan steps followed as specified.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/27-spatial-canvas.md` — Extended with 3 new feature sections, updated Node Anatomy, Toolbar, What Gets Saved, comparison table, and practical workflows (~117 new lines)
- `docs/guide/appendix-d-glossary.md` — Added "Embed Node" and "Property Flip" entries in alphabetical order
