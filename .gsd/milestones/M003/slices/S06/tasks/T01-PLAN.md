---
estimated_steps: 6
estimated_files: 3
---

# T01: Backend comment operations — RDF vocabulary, EventStore handlers, SPARQL queries, and tree assembly

**Slice:** S06 — Threaded Object Comments
**Milestone:** M003

## Description

Create the complete backend data layer for threaded comments: a FastAPI sub-router (`comments.py`) with endpoints for creating, retrieving, and soft-deleting comments. Comments are first-class RDF resources stored via EventStore operations in `urn:sempkm:current`. The flat SPARQL query retrieves all comments for an object; Python assembles the thread tree. Unit tests validate tree assembly (a pure function) and operation building.

## Steps

1. **Create `backend/app/browser/comments.py`** — New sub-router following the `favorites.py` pattern exactly:
   - `comments_router = APIRouter(tags=["comments"])`
   - Import: `get_current_user`, `require_role`, `_validate_iri`, `get_icon_service`, EventStore deps
   - Helper: `_build_comment_create_operation(comment_iri, object_iri, body, author_uri, reply_to=None)` → returns `Operation` with `comment.create` type, building triples for `rdf:type sempkm:Comment`, `sempkm:commentOn`, `sempkm:commentBody`, `sempkm:commentedBy`, `sempkm:commentedAt`, and optional `sempkm:replyTo`
   - Helper: `_build_comment_delete_operation(comment_iri, old_body, old_author)` → returns `Operation` with `comment.delete` type, `materialize_deletes` for old body + old author triples, `materialize_inserts` for new body `Literal("[deleted]")`
   - Helper: `_build_comment_tree(flat_comments)` → pure function that takes a list of `{iri, body, author, timestamp, reply_to}` dicts and returns a nested tree structure. Root comments (no reply_to) are top-level; children grouped under parent's `replies` list. Order by timestamp within each level.

2. **Implement GET endpoint** — `GET /browser/object/{iri}/comments`:
   - Validate IRI via `_validate_iri()`
   - SPARQL query against `urn:sempkm:current`: SELECT `?comment ?body ?author ?timestamp ?replyTo` WHERE comment has `sempkm:commentOn <{iri}>`, OPTIONAL `commentedBy` and `replyTo`
   - Parse bindings into flat list of dicts
   - Batch-resolve author display names from SQL `users` table (single query: `SELECT id, display_name FROM users WHERE id IN (...)` extracting UUIDs from `urn:sempkm:user:{uuid}` URIs)
   - Call `_build_comment_tree()` on flat list
   - Render `browser/partials/comments_section.html` template with tree and count

3. **Implement POST endpoint** — `POST /browser/object/{iri}/comments`:
   - Auth: `require_role("owner", "member")`
   - Form params: `body: str`, optional `reply_to: str`
   - Validate object IRI and optional reply_to IRI
   - Mint comment IRI: `mint_object_iri(base_namespace, "Comment")`
   - Build author URI: `URIRef(f"urn:sempkm:user:{user.id}")`
   - Build operation via `_build_comment_create_operation()`
   - Commit via `EventStore.commit([operation], performed_by=author_uri)`
   - Return HTML response with `HX-Trigger: commentsRefreshed` header

4. **Implement DELETE endpoint** — `DELETE /browser/comments/{comment_iri}`:
   - Auth: `require_role("owner", "member")`
   - Validate comment_iri
   - SPARQL query to fetch current body and author of the comment
   - Verify the comment exists (404 if not)
   - Build soft-delete operation: replace body with "[deleted]", remove author triple
   - Commit via EventStore
   - Return HTML response with `HX-Trigger: commentsRefreshed` header

5. **Wire router** — In `backend/app/browser/router.py`:
   - Add `from .comments import comments_router`
   - Add `router.include_router(comments_router)` after favorites_router

6. **Write unit tests** — `backend/tests/test_comments.py`:
   - Test `_build_comment_tree()` with: empty list, single comment, flat list (no replies), threaded (parent + replies), deep nesting (3+ levels), multiple roots with interleaved replies
   - Test `_build_comment_create_operation()` produces correct triples for top-level and reply comments
   - Test `_build_comment_delete_operation()` produces correct materialize_inserts/deletes for soft-delete
   - All tests are pure-function unit tests — no triplestore or server needed

## Must-Haves

- [ ] `comments_router` created and wired into `browser/router.py`
- [ ] GET endpoint returns threaded comments as HTML partial
- [ ] POST endpoint creates comment via EventStore with `comment.create` operation
- [ ] DELETE endpoint soft-deletes (replaces body with "[deleted]", removes author)
- [ ] `_build_comment_tree()` pure function tested with 6+ scenarios
- [ ] All SPARQL queries scoped to `GRAPH <urn:sempkm:current>` or `FROM <urn:sempkm:current>`
- [ ] Author display names resolved from SQL users table, not stored in RDF
- [ ] Comment IRI minted via `mint_object_iri(base_namespace, "Comment")`

## Verification

- `docker compose exec backend .venv/bin/pytest backend/tests/test_comments.py -v` — all tests pass
- Manual curl: `POST /browser/object/{iri}/comments` with body → 200 with HX-Trigger header
- Manual curl: `GET /browser/object/{iri}/comments` → HTML with comment data
- Manual curl: `DELETE /browser/comments/{iri}` → 200 with HX-Trigger header

## Observability Impact

- Signals added/changed: `logger.debug` on comment create/delete with comment_iri, object_iri, author; EventStore audit trail for all mutations
- How a future agent inspects this: Query `SELECT ?c ?body WHERE { GRAPH <urn:sempkm:current> { ?c a sempkm:Comment } }` via SPARQL console; check EventStore event graphs for `comment.create`/`comment.delete` operations
- Failure state exposed: HTTP 400 (invalid IRI), 404 (comment not found for delete), 500 (EventStore commit failure with logged traceback)

## Inputs

- `backend/app/browser/favorites.py` — reference pattern for sub-router structure
- `backend/app/commands/handlers/edge_create.py` — reference pattern for first-class RDF resource creation via Operation
- `backend/app/events/store.py` — EventStore.commit() API and Operation dataclass
- `backend/app/rdf/iri.py` — mint_object_iri() for Comment IRI minting
- `backend/app/rdf/namespaces.py` — SEMPKM namespace for comment predicates
- `backend/app/browser/_helpers.py` — _validate_iri() for input validation

## Expected Output

- `backend/app/browser/comments.py` — complete sub-router with 3 endpoints and 3 helper functions
- `backend/app/browser/router.py` — updated with comments_router include
- `backend/tests/test_comments.py` — 10+ unit tests for tree assembly and operation building
