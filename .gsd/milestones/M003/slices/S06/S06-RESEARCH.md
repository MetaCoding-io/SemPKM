# S06: Threaded Object Comments — Research

**Date:** 2026-03-12

## Summary

S06 adds threaded comments to any RDF object, stored in the knowledge graph via EventStore operations. Comments use a `sempkm:Comment` type with `replyTo` threading, authored by authenticated users. The right-pane "Details" panel gains a new "Comments" section below "Relations" and "Lint", loaded via htmx. The backend follows the established sub-router pattern (`browser/comments.py`) and the EventStore `Operation` pattern used by all other writes.

The primary risk — query performance for nested threads — is manageable because comments live in `urn:sempkm:current` and are queried per-object (small result sets). RDF has no native recursion, but 3-level nesting can be handled with a flat query + client-side tree assembly rather than recursive SPARQL, which is the recommended approach.

The slice is independent (no dependencies on S01–S05) and touches only new files plus small additions to existing integration points (workspace.html, workspace.js, workspace.css, router.py).

## Recommendation

**Flat query + client-side tree assembly.** Query all comments for an object in a single SPARQL SELECT, return them flat with `replyTo` parent references, and assemble the tree in Python before rendering in the Jinja2 template. This avoids recursive SPARQL (which RDF4J supports via `property paths` but poorly for arbitrary-depth tree assembly with metadata) and keeps the query simple and fast.

**Follow the favorites sub-router pattern** exactly: new `browser/comments.py` with `comments_router`, included in `browser/router.py`. Comments are stored as RDF triples in `urn:sempkm:current` via `EventStore.commit()` with new operation types (`comment.create`, `comment.delete`). Reply is just a `comment.create` with a `replyTo` triple.

**Comment IRI minting:** Use `mint_object_iri(base_namespace, "Comment")` — comments are first-class RDF resources with their own IRIs, same pattern as Edge resources.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| RDF triple persistence + audit trail | `EventStore.commit()` with `Operation` dataclass | Atomic event graph + current state materialization. All other writes use this. |
| IRI minting | `mint_object_iri(base_namespace, "Comment")` | Consistent IRI pattern (`{namespace}/Comment/{uuid}`) |
| User identity in RDF | `URIRef(f"urn:sempkm:user:{user.id}")` | Same pattern as all other EventStore commits — `performed_by` |
| Predicate resolution | `_resolve_predicate()` from `commands/handlers/object_create.py` | Handles compact IRIs, full IRIs, and bare local names |
| Value serialization | `_to_rdf_value()` from `commands/handlers/object_create.py` | Handles datetime detection, URI vs literal |
| Auth / role checking | `get_current_user`, `require_role("owner", "member")` | Session-based auth dependencies |
| Right-pane section rendering | `<details class="right-section">` pattern | Drag-drop panel sections with collapsible headers |
| htmx partial loading | `loadRightPaneSection()` pattern in `workspace.js` | Fetch + swap into `#comments-content` |

## Existing Code and Patterns

- `backend/app/events/store.py` — `EventStore.commit()` is the write path. New operation types (`comment.create`, `comment.delete`) are just string labels; no registration needed. The Operation dataclass provides `data_triples`, `materialize_inserts`, and `materialize_deletes`.
- `backend/app/browser/favorites.py` — **Reference implementation for a new browser sub-router.** Shows: router creation, dependency injection, htmx response with `HX-Trigger`, template rendering. Follow this exactly.
- `backend/app/browser/router.py` — Sub-router coordinator. Add `from .comments import comments_router` and `router.include_router(comments_router)`.
- `backend/app/templates/browser/workspace.html` lines 158–182 — Right pane structure with `<details class="right-section" data-panel-name="...">` blocks. Add a new "Comments" section here.
- `frontend/static/js/workspace.js` lines 245–273 — `loadRightPaneSection()` function fetches HTML partials for right-pane sections. Add `comments` section support here.
- `backend/app/commands/handlers/edge_create.py` — Pattern for creating first-class RDF resources with SEMPKM namespace predicates (`SEMPKM.source`, `SEMPKM.target`, etc.). Comments follow the same pattern with `SEMPKM.commentBody`, `SEMPKM.commentOn`, etc.
- `backend/app/rdf/iri.py` — `mint_object_iri()` for Comment IRI minting. No new mint function needed.
- `backend/app/rdf/namespaces.py` — `SEMPKM = Namespace("urn:sempkm:")` — comment predicates are `SEMPKM.commentBody`, `SEMPKM.commentOn`, `SEMPKM.replyTo`, `SEMPKM.commentedBy`, `SEMPKM.commentedAt`. These are dynamic attributes on the rdflib `Namespace` object (no explicit definition needed).
- `backend/app/auth/models.py` — `User` model with `id` (UUID), `email`, `display_name`, `username`. Used for author attribution — resolve display name from user_id in comment render.
- `frontend/static/css/workspace.css` lines 555–610 — `.right-section`, `.right-section-header`, `.right-section-body` CSS. Comment section uses identical structure.

## Constraints

- **RDF storage, not SQL** — D022 mandates comments stored in RDF via EventStore. Comments are knowledge about objects — they belong in the knowledge graph.
- **Threaded, not flat** — D023 mandates threaded with `replyTo` nesting. Flat comments are not acceptable.
- **Event-sourced writes** — All comment mutations must flow through `EventStore.commit()` for immutable audit trail, consistent with all other writes.
- **htmx + vanilla JS** — No React or other JS frameworks. Comment UI must follow htmx partial rendering pattern.
- **Auth required** — Comments require authenticated user (`get_current_user`). Write operations require `require_role("owner", "member")`.
- **IRI validation** — All IRI inputs must pass `_validate_iri()` before SPARQL interpolation (injection prevention).
- **Lucide icon sizing** — Per CLAUDE.md, Lucide SVGs in flex containers need `flex-shrink: 0` via CSS, not inline styles.
- **Current graph scope** — All comment SPARQL queries must use `GRAPH <urn:sempkm:current>` scoping, consistent with all other reads.

## Common Pitfalls

- **Recursive SPARQL for threading** — RDF4J supports property paths (`+`/`*`) but they don't carry metadata (author, timestamp) along the path. Do NOT attempt recursive SPARQL queries for tree assembly. Use a flat query returning all comments for an object, then build the tree in Python.
- **Naive GROUP_CONCAT for reply chains** — SPARQL `GROUP_CONCAT` can't represent tree structure. A flat SELECT with `?replyTo` optional binding is simpler and lets Python assemble the tree.
- **Comment deletion with children** — Deleting a comment with replies needs a policy: either delete the entire subtree (cascade) or mark as "[deleted]" while preserving replies. Recommendation: soft-delete by replacing body with "[deleted]" and clearing author, preserving the comment IRI and thread structure. This avoids orphaned reply chains.
- **HX-Trigger timing** — The favorites pattern uses `HX-Trigger: commentsRefreshed` header on mutation responses + `hx-trigger="load, commentsRefreshed from:body"` on the comments section. This ensures the comment list refreshes after add/delete without full page reload.
- **SPARQL injection in comment body** — Comment body text must be stored as `Literal(body_text)` via rdflib, not interpolated into SPARQL strings. The `_serialize_rdf_term()` function in `store.py` handles escaping. Never build SPARQL strings with raw user text.
- **User display name resolution** — Comments store `sempkm:commentedBy <urn:sempkm:user:{uuid}>`. Display names must be resolved from SQL `users` table at render time, not stored in RDF (names change). Batch-resolve with a single SQL query.
- **Timestamp timezone** — Use `datetime.now(timezone.utc).isoformat()` with `XSD.dateTime` datatype, consistent with EventStore pattern.

## Open Risks

- **Comment count at scale** — If an object accumulates hundreds of comments, the flat query + Python tree assembly could get slow. Mitigation: paginate with a `LIMIT` clause and "load more" button. Not needed for MVP but worth planning the query to support it (add `ORDER BY ?timestamp LIMIT 100 OFFSET 0`).
- **Cross-user comment visibility** — All comments are visible to all authenticated users (per requirements). No per-comment ACLs. If multi-tenancy is added later, comments would need graph-level scoping.
- **Comment edit** — The requirements mention create, reply, and (implicit) delete. Comment editing is not explicitly required. Recommendation: skip edit in S06, add later if needed. This avoids the complexity of edit history tracking.

## RDF Vocabulary Design

Comment resources stored in `urn:sempkm:current`:

```turtle
<{base}/Comment/{uuid}> a sempkm:Comment ;
    sempkm:commentOn <{object_iri}> ;        # which object this comment is about
    sempkm:commentBody "The comment text" ;    # plain text body
    sempkm:commentedBy <urn:sempkm:user:{uuid}> ; # author
    sempkm:commentedAt "2026-03-12T22:00:00Z"^^xsd:dateTime ;  # timestamp
    sempkm:replyTo <{base}/Comment/{parent_uuid}> .  # optional: thread parent
```

Operation types:
- `comment.create` — creates comment triples (with or without `replyTo`)
- `comment.delete` — soft-deletes by replacing body with "[deleted]" and removing author

SPARQL query pattern (flat, all comments for an object):
```sparql
SELECT ?comment ?body ?author ?timestamp ?replyTo
FROM <urn:sempkm:current>
WHERE {
    ?comment a sempkm:Comment ;
             sempkm:commentOn <{object_iri}> ;
             sempkm:commentBody ?body ;
             sempkm:commentedAt ?timestamp .
    OPTIONAL { ?comment sempkm:commentedBy ?author }
    OPTIONAL { ?comment sempkm:replyTo ?replyTo }
}
ORDER BY ?timestamp
```

Tree assembly in Python: group by `replyTo`, build nested dict, render via recursive Jinja2 macro.

## UI Design

**Right-pane "Comments" section:**
- New `<details class="right-section" data-panel-name="comments">` in workspace.html
- Header: "Comments" with count badge
- Body: threaded comment list with indentation per nesting level
- Each comment shows: author name, relative timestamp ("2 hours ago"), body text, "Reply" button
- Reply form: textarea + "Post" button, appears inline below the comment being replied to
- New top-level comment: textarea at top of comments section
- Empty state: "No comments yet. Be the first to comment."

**Nesting depth rendering:**
- Each reply level indented with `margin-left` (e.g. 20px per level)
- Cap visual indentation at 4 levels (deeper replies still work but don't indent further)
- Thread lines: thin left border connecting reply chains

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (198 installs) | available — but codebase already has extensive htmx patterns to follow |
| FastAPI | `0xdarkmatter/claude-mods@python-fastapi-patterns` (30 installs) | available — low install count, codebase patterns are sufficient |
| SPARQL | `letta-ai/skills@sparql-university` (36 installs) | available — low install count, not directly relevant to this implementation |

None of these skills are needed — the codebase has strong existing patterns for all technologies involved.

## Sources

- EventStore pattern: `backend/app/events/store.py` (Operation dataclass, commit flow)
- Sub-router pattern: `backend/app/browser/favorites.py` (reference implementation)
- Edge resource pattern: `backend/app/commands/handlers/edge_create.py` (first-class RDF resources)
- Right-pane section pattern: `backend/app/templates/browser/workspace.html` lines 158–182
- Right-pane loading pattern: `frontend/static/js/workspace.js` `loadRightPaneSection()`
- Decisions D022 (RDF storage), D023 (threaded model): `.gsd/DECISIONS.md`
- Requirements CMT-01, CMT-02: `.gsd/REQUIREMENTS.md`
