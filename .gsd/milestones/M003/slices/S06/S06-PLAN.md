# S06: Threaded Object Comments

**Goal:** Users can add threaded comments on any object, stored in RDF via EventStore, displayed in the right-pane Details panel with author attribution and timestamps.
**Demo:** Open an object → post a comment → reply to it → see threaded display with author names and relative timestamps. Delete a comment → body shows "[deleted]" but thread structure preserved.

## Must-Haves

- Comment RDF vocabulary: `sempkm:Comment` type with `commentBody`, `commentOn`, `replyTo`, `commentedBy`, `commentedAt` predicates
- EventStore operations: `comment.create` and `comment.delete` (soft-delete replaces body with "[deleted]")
- `GET /browser/object/{iri}/comments` returns threaded comment HTML partial
- `POST /browser/object/{iri}/comments` creates a comment (with optional `reply_to` for threading)
- `DELETE /browser/comments/{comment_iri}` soft-deletes a comment
- Comments section in right-pane Details panel, loaded via `loadRightPaneSection()` pattern
- Threaded display with indentation (capped at 4 visual levels), author names, relative timestamps
- Reply form appears inline below the comment being replied to
- Auth required for all operations; write operations require owner/member role
- Flat SPARQL query with Python-side tree assembly (no recursive SPARQL)
- All comment SPARQL queries scoped to `GRAPH <urn:sempkm:current>`

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker Compose stack with RDF4J triplestore)
- Human/UAT required: no (pytest unit tests + Playwright E2E cover all requirements)

## Verification

- `backend/tests/test_comments.py` — unit tests for comment tree assembly, soft-delete logic, IRI minting
- `e2e/tests/21-comments/comments.spec.ts` — E2E: post comment, reply, see threaded display, delete, verify "[deleted]" placeholder
- `docker compose exec backend .venv/bin/pytest backend/tests/test_comments.py -v` passes
- `npx playwright test e2e/tests/21-comments/` passes

## Observability / Diagnostics

- Runtime signals: `logger.debug("Comment created: comment_iri=%s, object_iri=%s, author=%s")` and similar for delete; EventStore audit trail captures all mutations
- Inspection surfaces: `GET /browser/object/{iri}/comments` returns full comment tree HTML; SPARQL console can query `sempkm:Comment` instances directly in `urn:sempkm:current`
- Failure visibility: HTTP 400/404 with descriptive error for invalid IRI, missing object, or missing comment; EventStore commit failures surface as 500 with logged stack trace
- Redaction constraints: comment body is user-generated content but not sensitive; no secrets in comment flow

## Integration Closure

- Upstream surfaces consumed: `EventStore.commit()` for writes, `TriplestoreClient.query()` for reads, `get_current_user`/`require_role` for auth, `loadRightPaneSection()` JS pattern, `<details class="right-section">` HTML/CSS pattern, `mint_object_iri()` for IRI minting
- New wiring introduced in this slice: `comments_router` sub-router included in `browser/router.py`, new "Comments" `<details>` section in workspace.html right pane, `loadRightPaneSection()` extended with `comments` section, `HX-Trigger: commentsRefreshed` event loop
- What remains before the milestone is truly usable end-to-end: S07 (ontology viewer), S08 (class creation), S09 (admin stats), S10 (E2E gaps)

## Tasks

- [x] **T01: Backend comment operations — RDF vocabulary, EventStore handlers, SPARQL queries, and tree assembly** `est:1h30m`
  - Why: Creates the entire backend data layer — comment creation, threading, soft-delete, flat SPARQL retrieval, and Python tree assembly. This is the foundation all other tasks build on.
  - Files: `backend/app/browser/comments.py`, `backend/app/browser/router.py`, `backend/tests/test_comments.py`
  - Do: Create `comments.py` sub-router following the favorites.py pattern. Implement `POST /browser/object/{iri}/comments` (creates comment via EventStore with `comment.create` operation), `DELETE /browser/comments/{comment_iri}` (soft-delete via `comment.delete`), `GET /browser/object/{iri}/comments` (flat SPARQL query + Python tree assembly → renders Jinja2 template). Comment IRI via `mint_object_iri(base_namespace, "Comment")`. Tree assembly: flat query returns all comments for object, group by `replyTo`, build nested structure, pass to template. Batch-resolve user display names from SQL. Include router in `browser/router.py`. Write unit tests for tree assembly function (pure function), soft-delete operation building, and IRI validation.
  - Verify: `docker compose exec backend .venv/bin/pytest backend/tests/test_comments.py -v` — all tests pass
  - Done when: Comment CRUD endpoints exist, tree assembly is tested, router is wired

- [x] **T02: Comment UI — Jinja2 templates, CSS, and workspace.js integration** `est:1h`
  - Why: Builds the user-facing comment display and interaction — the "Comments" right-pane section, threaded rendering, reply forms, and htmx refresh wiring. Without this, the backend endpoints have no UI surface.
  - Files: `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/partials/comments_section.html`, `backend/app/templates/browser/partials/comment_thread.html`, `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`
  - Do: Add "Comments" `<details class="right-section" data-panel-name="comments">` to workspace.html right pane (after lint, before inbox). Create `comments_section.html` partial with top-level comment form (textarea + Post button via htmx POST) and comment list container. Create `comment_thread.html` with recursive Jinja2 macro for nested rendering — each comment shows author name, relative timestamp, body text, Reply button, and Delete button (if author). Reply form appears inline on Reply click (JS toggle). Indentation via `margin-left: min(level * 20px, 80px)` (cap at 4 levels). Thread connector lines via left border. Extend `loadRightPaneSection()` in workspace.js to handle `comments` section (URL: `/browser/object/{iri}/comments`). Add `commentsRefreshed` htmx trigger support. CSS: `.comment-item`, `.comment-meta`, `.comment-body`, `.comment-actions`, `.comment-reply-form`, `.comment-thread-line` styles following `.right-section` conventions. Lucide icons with `flex-shrink: 0` per CLAUDE.md.
  - Verify: Start Docker stack → open an object → "Comments" section visible in right pane with empty state message → post a comment → it appears with author name and timestamp
  - Done when: Comments section renders in right pane, posting/replying/deleting works through the UI, thread nesting displays correctly with indentation

- [x] **T03: E2E test coverage for comments** `est:45m`
  - Why: Proves CMT-01 and CMT-02 requirements are met with automated verification. Exercises the full stack: post comment, reply, threaded display, soft-delete.
  - Files: `e2e/tests/21-comments/comments.spec.ts`
  - Do: Create E2E spec covering: (1) post a top-level comment on an object — verify it appears with author name and timestamp, (2) reply to that comment — verify threaded indentation, (3) post a second top-level comment — verify ordering, (4) delete a comment that has replies — verify body shows "[deleted]" but replies preserved, (5) empty state — object with no comments shows "No comments yet" message. Follow existing E2E patterns (login helper, object creation via UI or API fixture).
  - Verify: `npx playwright test e2e/tests/21-comments/ --headed` — all tests pass against running Docker stack
  - Done when: All 5 E2E scenarios pass, CMT-01 and CMT-02 requirements are exercised

## Files Likely Touched

- `backend/app/browser/comments.py` (new — comment sub-router)
- `backend/app/browser/router.py` (add comments_router include)
- `backend/app/templates/browser/workspace.html` (add Comments section to right pane)
- `backend/app/templates/browser/partials/comments_section.html` (new — comment section partial)
- `backend/app/templates/browser/partials/comment_thread.html` (new — threaded comment macro)
- `frontend/static/js/workspace.js` (extend loadRightPaneSection for comments)
- `frontend/static/css/workspace.css` (comment-specific styles)
- `backend/tests/test_comments.py` (new — unit tests)
- `e2e/tests/21-comments/comments.spec.ts` (new — E2E tests)
