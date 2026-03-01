# Phase 24: FTS Keyword Search - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable full-text keyword search across all RDF literal values using RDF4J LuceneSail. Search is surfaced exclusively through the existing Ctrl+K command palette (ninja-keys). A dedicated `GET /api/search` endpoint serves structured JSON. No new search UI surfaces beyond Ctrl+K.

</domain>

<decisions>
## Implementation Decisions

### LuceneSail JAR Verification
- Plan 24-01 MUST verify the LuceneSail JAR exists in the running Docker image before writing SearchService code
- If JAR is absent: extend the Dockerfile (add JAR download/copy step) before proceeding
- If JAR is present: proceed directly to config and service code
- This is the critical prerequisite noted in DECISIONS.md — do not skip verification

### Search UI Surface
- Ctrl+K command palette only — no dedicated search panel or workspace tab
- Results appear inline in the existing ninja-keys palette UI
- Result format: type icon + object label + matching snippet (three pieces, compact)

### Search Scope
- Scoped to `urn:sempkm:current` graph only — event graphs excluded from search
- All literal values indexed (not just titles/labels) — broad coverage

### Search API Design
- `GET /api/search?q={query}` returns structured JSON
- Response includes: IRI, type, label, matching snippet, score
- Endpoint accessible to authenticated users (session cookie auth)

### Ctrl+K Integration
- FTS results appear as a new category in the command palette results
- Clicking a result calls `openTab()` with the object IRI (same as nav tree)
- Results ranked by LuceneSail relevance score

### Claude's Discretion
- Minimum query length before FTS fires (1 char, 2 chars, or debounced)
- Number of results shown in palette (10, 20, configurable)
- Whether to debounce search or fire on each keystroke

</decisions>

<specifics>
## Specific Ideas

- DECISIONS.md specifies LuceneSail as the committed approach — zero new containers, SPARQL-native FTS via `<http://www.openrdf.org/contrib/lucenesail#>` predicates
- Three implementation prerequisites from DECISIONS.md: (1) verify JAR, (2) validate Turtle config for RDF4J 5.x unified namespace, (3) validate FROM clause graph scoping
- Existing ninja-keys (Ctrl+K) already has a category system — FTS results slot in as a new "Search" category

</specifics>

<deferred>
## Deferred Ideas

- Dedicated search results panel/workspace tab — deferred, Ctrl+K sufficient for v2.2
- Faceted search / filter by type — future phase
- pgvector / semantic search — explicitly deferred until keyword FTS validated (DECISIONS.md DEC-01)

</deferred>

---

*Phase: 24-fts-keyword-search*
*Context gathered: 2026-02-28*
