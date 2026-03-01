---
phase: 20-architecture-decision-commit
plan: 03
subsystem: planning
tags: [webdav, wsgidav, a2wsgi, vfs, architecture-decision]

# Dependency graph
requires:
  - phase: 20-architecture-decision-commit
    provides: "Research validation context (phase-22-vfs RESEARCH.md)"
provides:
  - "Committed VFS architectural decision: wsgidav + a2wsgi WSGI/ASGI bridge for WebDAV"
  - "FUSE explicitly ruled out with Docker SYS_ADMIN rationale"
  - "v2.2 Handoff section with Phase 22a/22b first steps and prerequisites"
affects:
  - 21-research-synthesis
  - 22-vfs-implementation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decision section at file top + Handoff section at file bottom pattern for RESEARCH.md files"

key-files:
  created: []
  modified:
    - ".planning/research/phase-22-vfs/RESEARCH.md"

key-decisions:
  - "(20-03) wsgidav + a2wsgi WSGI/ASGI bridge chosen for WebDAV VFS — Docker-compatible, HTTP-only, no kernel-level access required"
  - "(20-03) FUSE explicitly ruled out: requires SYS_ADMIN Docker cap prohibited by AWS Fargate, Fly.io, Railway managed hosting"
  - "(20-03) Read-only first MVP: defer write path (diff engine, ETag concurrency, python-frontmatter round-trips) to Phase 22d"
  - "(20-03) Three new Python packages required: wsgidav>=4.3.3,<5.0, a2wsgi>=1.10, python-frontmatter>=1.1.0"
  - "(20-03) SyncTriplestoreClient needed: DAVProvider runs in WSGI thread pool, cannot use httpx.AsyncClient"
  - "(20-03) API token Basic auth pattern committed (username=SemPKM username, password=revocable token) — design deferred to Phase 22c"

patterns-established:
  - "Decision at top / Handoff at bottom: RESEARCH.md files get Decision (committed choice) prepended and v2.X Handoff (implementation steps) appended"

requirements-completed: [DEC-03]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 20 Plan 03: VFS Architecture Decision Summary

**wsgidav + a2wsgi WSGI/ASGI bridge committed as the VFS WebDAV implementation approach, FUSE ruled out for Docker incompatibility, with a v2.2 Handoff section specifying Phase 22a/22b first steps**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T02:40:02Z
- **Completed:** 2026-03-01T02:41:48Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Prepended committed architectural decision to VFS RESEARCH.md: wsgidav v4.3.x + a2wsgi bridge with SemPKMDAVProvider mapping MountSpec definitions to SPARQL-backed directories
- Documented rationale covering Docker compatibility, native OS client support, minimal new dependencies, and read-only-first risk mitigation
- Explicitly ruled out FUSE (SYS_ADMIN Docker cap), async WebDAV from scratch (no production library), nginx WebDAV module (static only), and OpenSearch sidecar
- Appended v2.2 Handoff section with three new Python packages, nginx proxy block prerequisite, SyncTriplestoreClient requirement, API token auth design gap, and Phase 22a/22b ordered first steps

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Decision section to VFS RESEARCH.md** - `5f9c683` (docs)
2. **Task 2: Add v2.2 Handoff section to VFS RESEARCH.md** - `d6dbfbd` (docs)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `.planning/research/phase-22-vfs/RESEARCH.md` - Prepended Decision section (lines 1-20) and appended v2.2 Handoff section (lines 730-776)

## Decisions Made
- wsgidav + a2wsgi chosen over FUSE, async from scratch, nginx WebDAV module, and OpenSearch sidecar
- Read-only first MVP strategy: write path deferred to Phase 22d
- Three new packages needed: wsgidav, a2wsgi, python-frontmatter
- SyncTriplestoreClient required since WSGI thread pool cannot use async httpx
- API token Basic auth pattern is the design target (implementation deferred to Phase 22c)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- VFS decision committed, ready for Phase 21 Research Synthesis
- Phase 22 VFS implementation has clear prerequisites and Phase 22a first steps documented
- Remaining decision track (DEC-04) in Phase 20 Plan 04 before synthesis can proceed

## Self-Check: PASSED

- FOUND: `.planning/research/phase-22-vfs/RESEARCH.md`
- FOUND: `.planning/phases/20-architecture-decision-commit/20-03-SUMMARY.md`
- FOUND commit: `5f9c683` (Task 1)
- FOUND commit: `d6dbfbd` (Task 2)

---
*Phase: 20-architecture-decision-commit*
*Completed: 2026-03-01*
