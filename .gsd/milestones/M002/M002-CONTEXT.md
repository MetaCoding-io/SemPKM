# M002: Hardening & Polish — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

## Project Description

SemPKM is a semantics-native PKM platform at v2.6 with ~54k LOC across Python/FastAPI backend and htmx/vanilla-web frontend. It has shipped 58 phases of feature work across 7 version milestones. This milestone addresses accumulated tech debt, security gaps, correctness bugs, and test coverage holes identified in the CONCERNS.md audit and Phase 58 verification, plus stress-tests the Obsidian import with a real vault.

## Why This Milestone

v1.0–v2.6 prioritized feature velocity. Several security, correctness, and maintainability issues accumulated:
- Security: auth endpoints unprotected against brute-force, magic link tokens logged in production, SPARQL escaping incomplete
- Correctness: unstable `hash()` in validation IRIs, fragile SPARQL scoping regex, broken federation Sync Now button
- Maintainability: 1956-line browser router monolith, zero backend unit tests, unpinned dependency versions
- Validation: Obsidian import never tested against a real vault (only a small test fixture)

All of these are cheaper to fix now than after more features are layered on top.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Import a real 905-note Obsidian vault (Ideaverse Pro 2.5) and see wiki-links resolved as edges, frontmatter as properties
- Click Sync Now in the federation UI and have it actually work (auto-discovers remote URL)
- Run two SemPKM instances locally for federation testing
- Trust that auth endpoints have rate limiting and magic link tokens aren't leaked to logs

### Entry point / environment

- Entry point: http://localhost:3000 (browser workspace), docker-compose CLI
- Environment: local dev (Docker Compose)
- Live dependencies involved: RDF4J triplestore, SQLite database

## Completion Class

- Contract complete means: all unit tests pass, all E2E tests pass, SPARQL escaping tested, IRI validation tested
- Integration complete means: federation E2E test passes between two real instances, Obsidian import completes with real vault
- Operational complete means: none (no new services or lifecycle changes)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- All existing E2E tests still pass after the browser router refactor (zero behavior change)
- Federation invite → sync flow works between two Docker instances
- Ideaverse Pro 2.5 vault imports with wiki-links resolving to edges (user-verified)
- Backend unit test suite runs and passes in CI-compatible fashion

## Risks and Unknowns

- Browser router refactor could break htmx wiring if routes aren't split carefully — mitigate by running full E2E suite after
- Federation dual-instance testing may have Docker networking complexity (two instances need to reach each other's APIs)
- Ideaverse vault may have edge cases the scanner doesn't handle (unusual frontmatter, nested wiki-links, non-UTF8 content)

## Existing Codebase / Prior Art

- `backend/app/browser/router.py` — the 1956-line monolith to split (33 route handlers across settings, LLM, workspace, nav tree, objects, events, search, views)
- `backend/app/auth/router.py` — magic link and auth endpoints (token logging at line 133)
- `backend/app/validation/report.py:175` — `hash()` fallback for validation IRI
- `backend/app/sparql/client.py` — `scope_to_current_graph()` regex-based detection
- `backend/app/views/service.py:189` — `source_model` empty string fallback
- `backend/app/federation/` — 2835 lines across 8 files, Sync Now bug in router.py/federation.js
- `backend/app/obsidian/` — scanner.py and executor.py for vault import
- `docker-compose.test.yml` — template for federation dual-instance compose file
- `.planning/codebase/CONCERNS.md` — the Feb 25 audit that sourced most items (some already fixed in v2.1+)
- `Ideaverse Pro 2.5.zip` — 905 .md files, ~4963 total files, LYT folder structure

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- SEC-01 through SEC-05 — security hardening (S01)
- COR-01 through COR-03 — correctness fixes (S02)
- TEST-01 through TEST-04 — backend test foundation (S03)
- REF-01 — browser router refactor (S04)
- DEP-01, DEP-02, PERF-01 — dependency pinning and cleanup (S05)
- FED-11 through FED-13 — federation bug fix and dual-instance testing (S06)
- OBSI-08 through OBSI-10 — Ideaverse import validation (S07)

## Scope

### In Scope

- Security: rate limiting, token logging fix, debug endpoint protection, SPARQL escaping, deployment docs
- Correctness: stable validation hash, SPARQL scoping hardening, source_model fix
- Testing: backend pytest infrastructure, unit tests for security-critical paths
- Refactoring: browser router split into sub-routers
- Dependencies: version pinning, lockfile
- Performance: event detail N+1 fix
- Federation: Sync Now bug fix, dual-instance docker-compose, E2E test
- Obsidian: Ideaverse vault import stress-test with user verification

### Out of Scope / Non-Goals

- New features (MCP server, admin charts, etc.)
- CRDT sync, automatic polling, fediverse interop
- Multi-tenant architecture changes
- Frontend framework changes
- Browser router behavior changes (refactor is structure-only)

## Technical Constraints

- Python 3.14 + FastAPI backend in Docker
- All changes must keep existing E2E tests passing
- Browser router refactor must preserve all URL paths exactly
- Federation testing requires Docker network connectivity between two instances
- Obsidian import is user-driven (manual UI interaction for S07)

## Integration Points

- RDF4J triplestore — SPARQL escaping and scoping changes affect all triplestore queries
- Docker Compose — federation test requires a second compose file with separate networks/ports
- Playwright E2E tests — must pass after every slice
- Frontend htmx — browser router split must keep all template paths and htmx targets intact

## Open Questions

- Rate limiting library choice (slowapi vs fastapi-limiter vs custom) — decide during S01 research
- Whether `scope_to_current_graph` should be rewritten as a proper SPARQL parser or just patched for the string-literal case — decide during S02
- How the federation test instances discover each other's URLs (docker network DNS vs hardcoded ports) — decide during S06 research
