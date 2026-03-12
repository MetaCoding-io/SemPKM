# M002: Hardening & Polish

**Vision:** Harden SemPKM's security, correctness, and maintainability foundations after 7 milestones of feature-first development. Fix known gaps, add backend test coverage, refactor the browser router monolith, pin dependencies, make federation actually work end-to-end between two instances, and stress-test the Obsidian import with a real 905-note vault.

## Success Criteria

- Auth endpoints resist brute-force (rate-limited) and magic link tokens aren't leaked to logs in production
- SPARQL escaping and IRI validation are covered by unit tests
- Browser router is split into focused sub-routers with zero behavior change (all E2E tests pass)
- Federation Sync Now button works; full invite → sync flow verified between two real instances
- Ideaverse Pro 2.5 vault imports successfully with wiki-links resolved and frontmatter mapped
- Dependencies are pinned and reproducible via lockfile

## Key Risks / Unknowns

- Browser router refactor could silently break htmx wiring — high impact if missed
- Federation dual-instance Docker networking may need custom configuration
- Ideaverse vault may contain edge cases the scanner doesn't handle (unusual frontmatter formats, deeply nested wiki-links)

## Proof Strategy

- Browser router refactor risk → retire in S04 by proving all existing E2E tests pass unchanged
- Federation networking risk → retire in S06 by proving two instances can sync via docker-compose
- Ideaverse edge cases → retire in S07 by completing import and verifying wiki-links/frontmatter in UI

## Verification Classes

- Contract verification: pytest unit tests (S03), E2E Playwright tests (all slices)
- Integration verification: dual-instance federation sync (S06), real vault import (S07)
- Operational verification: none
- UAT / human verification: Ideaverse import results (S07), federation UI flows (S06)

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 22 active requirements verified
- All existing E2E tests pass after every slice
- Backend unit test suite exists and passes
- Browser router is split with zero behavior change
- Federation works between two real Docker instances
- User has imported Ideaverse vault and confirmed wiki-links and frontmatter

## Requirement Coverage

- Covers: SEC-01–05, COR-01–03, TEST-01–04, REF-01, DEP-01–02, PERF-01, FED-11–13, OBSI-08–10
- Partially covers: none
- Leaves for later: MCP-01, ADMIN-01, ADMIN-02
- Orphan risks: none

## Slices

- [x] **S01: Security Hardening** `risk:medium` `depends:[]`
  > After this: auth endpoints have rate limiting, magic link tokens aren't logged in production, event console is owner-only, SPARQL filter text is properly escaped, and BASE_NAMESPACE deployment is documented.

- [x] **S02: Correctness Fixes** `risk:low` `depends:[]`
  > After this: validation report IRIs use stable hashing, scope_to_current_graph handles SPARQL keywords in string literals, and source_model is attributed correctly with multiple models.

- [x] **S03: Backend Test Foundation** `risk:medium` `depends:[S01,S02]`
  > After this: `backend/tests/` has pytest infrastructure with async fixtures, and unit tests cover SPARQL escaping, IRI validation, auth token logic, and scope_to_current_graph edge cases.

- [x] **S04: Browser Router Refactor** `risk:medium` `depends:[S03]`
  > After this: the 1956-line browser/router.py is split into domain sub-routers (settings, objects, events, search, LLM, views) — all existing E2E tests pass with zero URL changes.

- [x] **S05: Dependency Pinning & Cleanup** `risk:low` `depends:[]`
  > After this: pyproject.toml has pinned versions, uv.lock is committed, and event detail user lookup is batched instead of N+1.

- [x] **S06: Federation Bug Fix & Dual-Instance Testing** `risk:high` `depends:[S01]`
  > After this: Sync Now button auto-discovers remote URLs and works; docker-compose.federation-test.yml runs two instances; E2E test proves invite → accept → sync flow.

- [ ] **S07: Obsidian Ideaverse Import** `risk:medium` `depends:[]`
  > After this: user has uploaded Ideaverse Pro 2.5 (905 notes), mapped types, imported, and verified that wiki-links resolve to edges and frontmatter maps to properties. Any bugs found during import are fixed.

## Boundary Map

### S01 (Security Hardening)

Produces:
- Rate limiting middleware on `/api/auth/magic-link` and `/api/auth/verify`
- Conditional token logging (only when SMTP not configured)
- `require_role("owner")` on event console endpoint
- SPARQL filter text escaping function (reusable, tested in S03)
- BASE_NAMESPACE deployment documentation

Consumes:
- nothing (leaf node)

### S02 (Correctness Fixes)

Produces:
- Stable `hashlib`-based validation report IRI (replaces `hash()`)
- Hardened `scope_to_current_graph()` that handles string-literal edge cases
- Per-spec `source_model` attribution via model graph matching

Consumes:
- nothing (leaf node)

### S03 (Backend Test Foundation) → depends on S01, S02

Produces:
- `backend/tests/conftest.py` with async fixtures
- Unit tests for SPARQL escaping/serialization
- Unit tests for IRI validation
- Unit tests for auth token logic
- Unit tests for `scope_to_current_graph` edge cases

Consumes from S01:
- SPARQL filter text escaping function (to test)

Consumes from S02:
- Hardened `scope_to_current_graph()` (to test edge cases)
- Stable hash function (to test)

### S04 (Browser Router Refactor) → depends on S03

Produces:
- `backend/app/browser/settings.py` — settings + LLM sub-router
- `backend/app/browser/objects.py` — object CRUD sub-router
- `backend/app/browser/events.py` — event log sub-router
- `backend/app/browser/search.py` — search sub-router
- `backend/app/browser/views.py` — views sub-router
- `backend/app/browser/router.py` — thin coordinator importing sub-routers
- All E2E tests passing unchanged

Consumes from S03:
- Backend test infrastructure (confidence that refactor is safe)

### S05 (Dependency Pinning & Cleanup)

Produces:
- Pinned versions in `pyproject.toml`
- `uv.lock` committed
- Batched user lookup in event detail endpoint

Consumes:
- nothing (leaf node)

### S06 (Federation Bug Fix & Dual-Instance Testing) → depends on S01

Produces:
- Fixed `syncSharedGraph()` in federation.js (auto-discover remote URL)
- Fixed sync endpoint to auto-resolve remote URL from federation graph
- `docker-compose.federation-test.yml` with two complete instances
- Playwright E2E test for invite → accept → sync flow

Consumes from S01:
- Security hardening (rate limiting, etc.) should be in place before federation testing exercises auth flows

### S07 (Obsidian Ideaverse Import)

Produces:
- Verified import of Ideaverse Pro 2.5 vault (905 notes)
- Any bug fixes discovered during import
- User-confirmed wiki-link resolution and frontmatter mapping

Consumes:
- nothing (standalone — user-driven manual testing)
