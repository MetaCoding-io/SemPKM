---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Data Discovery
status: unknown
last_updated: "2026-03-01T07:30:00.000Z"
progress:
  total_phases: 16
  completed_phases: 14
  total_plans: 40
  completed_plans: 38
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.
**Current focus:** v2.2 Data Discovery — Phase 27: VFS Write + Auth (3/3 plans complete)

## Current Position

Phase: 27 of 28 (VFS Write + Auth)
Plan: 3 of 3 complete
Status: In Progress
Last activity: 2026-03-01 — Completed 27-03 (VFS Settings UI — WebDAV endpoint + API token management)

Progress: [##############################] 100% (Phase 27)

## v2.2 Phase Structure

| Phase | Name | Requirements | Depends On | Status |
|-------|------|--------------|------------|--------|
| 23 | SPARQL Console | SPARQL-01, SPARQL-02, SPARQL-03 | Nothing | Complete (2/2 plans) |
| 24 | FTS Keyword Search | FTS-01, FTS-02, FTS-03 | Nothing (JAR prereq) | Complete (2/2 plans) |
| 25 | CSS Token Expansion | — (v2.3 prep) | Nothing | Complete (1/1 plans) |
| 26 | VFS MVP Read-Only | VFS-01, VFS-02 | Nothing (self-contained) | Complete (3/3 plans) |
| 27 | VFS Write + Auth | VFS-03 | Phase 26 | Complete (3/3 plans) |
| 28 | UI Polish + Integration Testing | POLSH-01, POLSH-02, POLSH-03, POLSH-04 | Phases 23, 24, 26 | Not started |

## Accumulated Context

### Key Decisions

All v2.2 architectural decisions committed in v2.1. See .planning/DECISIONS.md for full rationale.

- DEC-01: RDF4J LuceneSail for FTS — zero new containers, SPARQL-native, ships with RDF4J 5.0.1
- DEC-02: @zazuko/yasgui v4.5.0 CDN for SPARQL Console — MIT, zero backend changes
- DEC-03: wsgidav + a2wsgi for VFS — HTTP-only, Docker-compatible, no SYS_ADMIN required
- DEC-04: dockview-core for UI shell — Phase A in v2.3; CSS token expansion complete (108 tokens, two-tier architecture)
- DEC-05: Yasgui CDN loaded at top of workspace block content, not base.html — workspace-only dependency
- DEC-06: Lazy Yasgui init via DOMContentLoaded + tab click handler — prevents JS errors when panel closed
- CSS-01: Token count expanded to 108 in :root (vs ~91 estimate) — comprehensive two-tier primitive/semantic architecture
- VFS-01: SyncTriplestoreClient mirrors async TriplestoreClient API with httpx.Client for WSGI thread pool use
- VFS-02: API tokens use SHA-256 hash storage; plaintext returned exactly once on creation
- VFS-03: verify_api_token_sync uses disposable sync SQLAlchemy engine per call for WSGI thread safety
- VFS-04: SPARQL queries use urn:sempkm: namespace (not https://sempkm.org/ontology/) and REPLACE regex .*[/:#] for URN local names
- VFS-05: DAV provider hierarchy: Root->Model->Type->Resource with lazy file map caching per TypeCollection
- VFS-06: TTL cache uses threading.Lock for write safety in wsgidav's WSGI thread pool; cache keys use path-style strings
- VFS-07: wsgidav readonly=True config set, but collection classes return 403 before wsgidav's 405 -- both block writes
- VFS-08: ApiToken uses hard-delete for revocation (not soft-delete via revoked_at) — cleaner list queries, no filter needed
- VFS-09: environ["sempkm.user_id"] set in SemPKMWsgiAuthenticator.basic_auth_user for DAV provider write path user context
- VFS-10b: begin_write/end_write wsgidav hooks used for write path (not write_data which does not exist in this wsgidav version)
- VFS-11b: set_event_store() injection method on DAVProvider — event_store wired at lifespan startup, not module load time
- VFS-12: SHA-256 ETag on ResourceFile; wsgidav handles If-Match/412 automatically via evaluate_http_conditionals before begin_write
- VFS-10: VFS settings CSS added to settings.css (not style.css) following project file layout convention
- VFS-11: VFS token generation uses fetch() instead of htmx to capture and display plaintext token once in-place
- FTS-01: LuceneSail config uses RDF4J 5.x unified namespace (config:lucene.indexDir, config:delegate) — verified from container-generated config
- FTS-02: Graph-scoped FTS via SPARQL GRAPH clause, not config-level reindexQuery (not supported in RDF4J 5.x config)
- FTS-03: Inline SVG type icons in ninja-keys search results (not IconService) -- simpler client-side mapping, no extra API call
- FTS-04: ninja-keys change event with e.detail.search confirmed as correct API for live search interception in v1.2.2

### Pending Todos

1. Add edit form helptext property to SHACL types (ui) — carried from v2.0

### Known Tech Debt

- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code
- Bottom panel SPARQL tab placeholder replaced with Yasgui (Phase 23 Plan 01)

### Blockers/Concerns

- None — Phase 27 complete; all 3 plans done

## Session Continuity

Last session: 2026-03-01
Stopped at: Completed 27-02-PLAN.md (VFS Write Path — body.set via WebDAV PUT)
Resume: Phase 27 plans 01, 02, 03 all complete. Proceed with Phase 28 (UI Polish + Integration Testing).
