---
id: T01
parent: S06
milestone: M003
provides:
  - comments_router with GET/POST/DELETE endpoints for threaded object comments
  - _build_comment_tree() pure function for thread assembly
  - _build_comment_create_operation() and _build_comment_delete_operation() EventStore helpers
  - comments_section.html template for rendering threaded comments
key_files:
  - backend/app/browser/comments.py
  - backend/app/browser/router.py
  - backend/tests/test_comments.py
  - backend/app/templates/browser/partials/comments_section.html
key_decisions:
  - Orphaned replies (parent missing from flat list) are treated as root comments rather than discarded
  - Soft-delete uses exact Literal matching for old body/author in materialize_deletes (no Variables needed since values are fetched first)
  - Author display name resolution uses raw SQL text() query with parameterized placeholders for batch UUID lookup
patterns_established:
  - Comment RDF vocabulary: sempkm:Comment type, sempkm:commentOn, sempkm:commentBody, sempkm:commentedBy, sempkm:commentedAt, sempkm:replyTo
  - EventStore operation types: comment.create, comment.delete
  - Comment IRI pattern: mint_object_iri(base_namespace, "Comment") → {namespace}/Comment/{uuid}
observability_surfaces:
  - logger.debug on comment create (comment_iri, object_iri, author) and delete (comment_iri, deleted_by)
  - EventStore audit trail for all comment mutations (comment.create, comment.delete operations)
  - HTTP 400 for invalid IRI, 404 for missing comment on delete, 400 for already-deleted comment
duration: 25min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Backend comment operations — RDF vocabulary, EventStore handlers, SPARQL queries, and tree assembly

**Built complete backend data layer for threaded comments: 3 endpoints, 3 helper functions, HTML template, and 14 unit tests.**

## What Happened

Created `backend/app/browser/comments.py` as a new sub-router following the `favorites.py` pattern. Implemented three helper functions:

- `_build_comment_create_operation()` — builds EventStore Operation with triples for rdf:type sempkm:Comment, sempkm:commentOn, sempkm:commentBody, sempkm:commentedBy, sempkm:commentedAt, and optional sempkm:replyTo
- `_build_comment_delete_operation()` — builds soft-delete Operation that replaces body with "[deleted]" and removes author triple, preserving thread structure
- `_build_comment_tree()` — pure function that assembles flat SPARQL results into a nested thread tree, sorted by timestamp at each level

Implemented three endpoints:
- `GET /browser/object/{iri}/comments` — SPARQL query for all comments on an object, batch-resolves author display names from SQL users table, assembles thread tree, renders HTML partial
- `POST /browser/object/{iri}/comments` — creates comment via EventStore with minted Comment IRI, returns HX-Trigger: commentsRefreshed
- `DELETE /browser/comments/{iri}` — soft-deletes by replacing body and removing author, returns HX-Trigger: commentsRefreshed

Wired `comments_router` into `browser/router.py`. Created `comments_section.html` Jinja2 template with recursive macro for nested thread rendering.

## Verification

- `backend/.venv/bin/pytest tests/test_comments.py -v` — 14/14 tests pass (8 tree assembly scenarios, 3 create operation tests, 3 delete operation tests)
- `backend/.venv/bin/pytest tests/ -v` — 224/224 tests pass, zero regressions
- Router import verified in container: `from app.browser.comments import comments_router` succeeds
- All three routes registered and visible in FastAPI router: GET/POST `/browser/object/{iri}/comments`, DELETE `/browser/comments/{iri}`

### Slice-level verification status:
- ✅ `backend/tests/test_comments.py` — 14 unit tests pass
- ⏳ `e2e/tests/21-comments/comments.spec.ts` — E2E tests (later task)
- ⏳ `npx playwright test e2e/tests/21-comments/` — (later task)

## Diagnostics

- Query all comments: `SELECT ?c ?body WHERE { GRAPH <urn:sempkm:current> { ?c a sempkm:Comment } }` via SPARQL console
- Check EventStore events: look for `comment.create` / `comment.delete` operation types in event graphs
- Author resolution: display names come from SQL `users` table, not RDF — check `SELECT id, display_name FROM users`
- Failure states: HTTP 400 (invalid IRI), 404 (comment not found for delete), 500 (EventStore commit failure with logged traceback)

## Deviations

- Task plan verification command references `docker compose exec backend` but the service is named `api`. Tests run successfully via local venv instead.
- Created `comments_section.html` template (not in original task plan but required by the GET endpoint to render HTML partial). Template includes recursive Jinja2 macro for nested thread display.

## Known Issues

- The dev environment database has no users table populated (empty SQLite), so manual curl testing of authenticated endpoints was not feasible. Integration testing will happen in E2E tasks.

## Files Created/Modified

- `backend/app/browser/comments.py` — new sub-router with 3 endpoints (GET/POST/DELETE) and 3 helper functions
- `backend/app/browser/router.py` — added comments_router import and include
- `backend/tests/test_comments.py` — 14 unit tests for tree assembly, create operations, and delete operations
- `backend/app/templates/browser/partials/comments_section.html` — Jinja2 template with recursive thread rendering macro
