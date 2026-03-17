---
depends_on: [M014]
---

# M015: Browser Extension Phase 2 — Knowledge Context Overlay

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Add a sidebar panel to the browser extension that shows what you already know about the page you're browsing. The extension quietly queries your SemPKM graph using page URL, title, and keywords, then displays related objects with counts, types, and in-context actions (link, add evidence, quick capture). A badge on the extension icon shows the match count.

## Why This Milestone

Every existing web clipper is a one-way pipe: web → notes. Phase 2 makes browsing a bidirectional conversation with your knowledge graph. While reading an article about event sourcing, you see "You have 3 notes and 1 claim related to this topic." This is the killer differentiator — no competitor does this.

## User-Visible Outcome

### When this milestone is complete, the user can:

- See a badge on the extension icon showing how many related objects exist for the current page
- Open a sidebar showing related objects grouped by type (Notes, Concepts, Claims, etc.)
- Click "Open" to view any related object in SemPKM
- Click "Link to this page" to create a typed relationship between the page and an existing object
- See "This page may contain relevant evidence" when viewing a page related to an unsupported Claim
- Click "Add Evidence" to highlight text and create an Evidence object linked to an existing Claim
- Configure auto-context checking (on/off, delay, timeout)

### Entry point / environment

- Entry point: Extension sidebar (toggle via Alt+K or badge click)
- Environment: Chrome/Firefox extension
- Live dependencies involved: SemPKM instance via M013 API endpoints

## Completion Class

- Contract complete means: sidebar renders with grouped results, badge updates, in-context actions create objects/edges
- Integration complete means: context queries return relevant results from real graph data, links created from sidebar appear in SemPKM's relations panel
- Operational complete means: debounced queries, caching per URL, graceful timeout handling

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User visits a page whose URL exists as a `schema:url` property on a Note — badge shows "1 related", sidebar shows the Note
- User visits a page about a topic matching a Concept label — sidebar shows the Concept and linked Notes
- User clicks "Link to this page" on a Concept — edge appears in SemPKM's relations panel
- Auto-context fires 2 seconds after page load, with results cached for the session
- User disables auto-context in settings, badge only appears on manual check

## Risks and Unknowns

- **Query performance** — Context queries against large graphs must return within 500ms. FTS keyword matching is fast; entity extraction from page content is slower. Tier 1-2 matching (URL + title keywords) should be sufficient for launch.
- **False positives** — Common words in page titles may match too many objects. Need ranking/relevance scoring.
- **Sidebar injection** — Injecting a sidebar into arbitrary web pages may conflict with page CSS. Shadow DOM isolation recommended.

## Existing Codebase / Prior Art

- `.gsd/design/BROWSER-EXTENSION-DESIGN.md` — Phase 2 spec: context matching strategy (4 tiers), sidebar UI mockup, performance considerations
- M014 — Phase 1 extension (popup, settings, API client)
- M013 — `/api/context-query` endpoint

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New: EXT-07 (context badge), EXT-08 (sidebar), EXT-09 (in-context actions), EXT-10 (evidence capture)

## Scope

### In Scope

- Context matching Tiers 1-2: URL exact match, title keyword FTS match
- Sidebar panel with grouped results by type
- Badge count on extension icon
- In-context actions: Open, Link to page, Add Evidence
- Auto-context with configurable delay and timeout
- Per-URL result caching
- Shadow DOM isolation for sidebar
- Settings for auto-context behavior

### Out of Scope / Non-Goals

- Tier 3-4 context matching (entity extraction, semantic similarity) — M028
- AI-powered suggestions — M028
- Inline page annotations/highlights
- Real-time graph subscriptions (polling/manual refresh only)

## Technical Constraints

- Sidebar must not break page layout (absolute positioning or Shadow DOM)
- Context queries have 500ms timeout with graceful degradation
- Badge updates debounced (2s after page load)
- Must work on same pages as Phase 1 popup without conflicts

## Integration Points

- **M013 /api/context-query** — primary context matching endpoint
- **M013 /api/sparql** — fallback for custom context queries
- **POST /api/commands** — creating edges from in-context actions
- **Phase 1 extension** — shared auth, API client, settings infrastructure
