# Phase 47: Obsidian Batch Import - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute the configured Obsidian import, creating RDF objects with correct bodies, properties, type assignments, wiki-link edges, and tag values via the Command API. Users see real-time progress during import and a summary with browse capability after completion. Supports re-import with deduplication for iterative workflows.

</domain>

<decisions>
## Implementation Decisions

### Wiki-link Resolution
- Predicate: `dcterms:references` for all wiki-link-derived edges
- Direction: One-way only (source note → target note)
- Unresolved targets (notes not in import, e.g., skipped groups): Skip the edge, collect in unresolved links report shown in post-import summary
- Aliases: When wiki-link uses alias syntax (`[[note|display text]]`), store the display text as `rdfs:label` annotation on the edge
- Resolution strategy: Match wiki-link text against note filenames (sans extension) within the import set

### Tag Resolution
- Representation: Plain literal property values, NOT edges to Concept objects
- Property: `schema:keywords` (one value per tag, multi-valued)
- Nested tags: Preserve full path (e.g., `#project/active` → `"project/active"`)
- Format: Strip `#` prefix — store semantic content only
- Tags from both frontmatter `tags:` field and inline `#tag` syntax are treated identically

### Batching and Progress
- Batch strategy: Per-object batches — each object gets one Command API call containing `object.create` + `body.set` + property values
- Second pass: Edge creation (wiki-links) as separate per-edge or small-batch commands after all objects exist
- Progress UX: Progress bar with live scrolling log via SSE broadcast (reuse scan progress pattern)
- Progress events: Object count (X/N), current note filename, phase indicator (objects → edges)
- Post-import: Summary screen showing counts (created, skipped-errors, skipped-existing, edges created, unresolved links) + "Browse Imported Objects" button
- Import directory: Keep on disk until user explicitly discards (existing discard endpoint)

### Error Handling
- Strategy: Skip failures and continue — log each failure, report all in post-import summary
- No rollback: Successfully imported objects remain even if later objects fail
- Summary categories: Created (N), Skipped-errors (N with details), Skipped-existing (N), Edges created (N), Unresolved links (N with list)

### Re-import Support
- User can go back to mapping, adjust, and re-run import
- Deduplication: Store original vault file path as `sempkm:importSource` property on each imported object
- On re-import: Query for existing objects with matching `sempkm:importSource` values, skip those
- Summary distinguishes "skipped (already imported)" from "skipped (error)"

### Claude's Discretion
- Exact SSE event format and update frequency
- Command API batch composition details (how many commands per batch call)
- Edge batch sizing for wiki-link pass
- "Browse Imported Objects" button behavior (open nav tree, table view, etc.)
- Error detail formatting in summary
- How to handle edge cases (empty body notes, notes with only frontmatter, etc.)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VaultScanResult` / `NoteTypeGroup` / `MappingConfig`: Phase 45-46 data models with `to_dict()`/`from_dict()` — import executor reads these
- `ScanBroadcast` / `SSEEvent` / `stream_sse()`: Phase 45 SSE broadcast pattern — reuse for import progress
- Command API (`POST /api/commands`): Accepts single or batch commands, atomic per-batch, returns `CommandResponse` with per-command IRIs
- `ObjectCreateParams`: type (IRI), slug (optional), properties dict
- `BodySetParams`: iri, body (markdown)
- `EdgeCreateParams`: source, target, predicate, optional properties
- Obsidian router (`backend/app/obsidian/router.py`): Existing endpoints for all wizard steps — add import execution endpoints here
- Preview template (`partials/preview.html`): Has disabled "Import" button ready to be wired up

### Established Patterns
- Command API batch: All commands in a batch share one event graph, committed atomically
- IRI minting: `mint_object_iri()` handles slug-based or random IRI generation
- Predicate resolution: Compact IRIs (e.g., `dcterms:references`) expanded via `COMMON_PREFIXES`
- SSE broadcast: asyncio.Queue fan-out, 30s keepalive, `scan_complete`/`scan_error` terminal events

### Integration Points
- Preview "Import" button: Currently disabled in `partials/preview.html` — wire to import endpoint
- Import directory: `/app/data/imports/{user_id}/{timestamp}/` contains `scan_result.json`, `mapping_config.json`, extracted vault
- Nav tree refresh: After import, sidebar nav tree needs refresh to show new objects (htmx trigger)
- Validation queue: Import will trigger async SHACL validation for each created object

</code_context>

<specifics>
## Specific Ideas

- Progress log should feel like a terminal/build output — scrolling text showing each note being imported
- Summary layout similar to scan results dashboard (big stat numbers at top, expandable details below)
- Unresolved links list should be useful — show which note had the link and what it was trying to link to
- "Browse Imported Objects" button should make it easy to immediately verify the import worked

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 47-obsidian-batch-import*
*Context gathered: 2026-03-08*
