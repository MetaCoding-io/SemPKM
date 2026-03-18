---
id: T04
parent: S03
milestone: M013
provides:
  - User guide Chapter 31 documenting all four API surface endpoints with request/response examples, authentication, CORS, and error handling
key_files:
  - docs/guide/31-api-surface.md
  - docs/guide/README.md
  - docs/guide/30-personas.md
  - docs/guide/appendix-d-glossary.md
key_decisions:
  - Documented CORS as a reverse-proxy configuration concern rather than built-in middleware, since no CORSMiddleware is configured in the backend
patterns_established:
  - Guide chapters follow the navigation chain pattern: previous chapter footer links to next, README TOC lists all chapters, glossary entries cross-reference chapter numbers
observability_surfaces:
  - none — documentation-only task
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: User guide documentation

**Added Chapter 31 (API Surface) to user guide covering all four M013 endpoints with request/response examples, authentication methods, CORS guidance, and three glossary entries**

## What Happened

Created `docs/guide/31-api-surface.md` with full documentation of all four API surface endpoints: instance discovery (`GET /.well-known/sempkm`), available types (`GET /api/types`), SHACL shapes (`GET /api/shapes/{type_iri}`), and context query (`POST /api/context-query`). Each endpoint includes purpose, example curl requests, example JSON responses, and field description tables.

The authentication section covers both session cookies (for web UI) and Bearer API tokens (for external clients), with auth resolution order documented. The CORS section accurately reflects the current state — no built-in CORSMiddleware, so CORS is handled at the reverse proxy layer with a sample nginx config. Error responses section covers standard HTTP status codes with examples.

Updated README.md TOC to include Chapter 31, updated Chapter 30's navigation footer to link to Chapter 31, and added three glossary entries (API Surface, Context Query, Instance Discovery) with cross-references back to Chapter 31.

## Verification

- `ls docs/guide/31-api-surface.md` — file exists ✅
- `grep "31" docs/guide/README.md` — chapter in TOC ✅
- `grep "API Surface\|Context Query\|Instance Discovery" docs/guide/appendix-d-glossary.md` — all three entries present ✅
- Navigation chain verified: Ch30 → Ch31 → Appendix A ✅
- All four endpoints have Example Request and Example Response sections (8 total) ✅
- Authentication section covers both session and Bearer token methods ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ls docs/guide/31-api-surface.md` | 0 | ✅ pass | <1s |
| 2 | `grep "31" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 3 | `grep "API Surface\|Context Query\|Instance Discovery" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |

## Diagnostics

Documentation-only task — no runtime surfaces. Verify accuracy by comparing endpoint examples against `backend/app/api/router.py` response models. Broken guide links can be detected by checking `](*.md)` references resolve to existing files in `docs/guide/`.

## Deviations

- CORS section documents reverse-proxy configuration instead of `Access-Control-Allow-Origin: *` as a built-in feature, because no CORSMiddleware is configured in the backend codebase. This is more accurate than the plan's implication that CORS is built-in.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/31-api-surface.md` — new Chapter 31 documenting the API surface (all four endpoints)
- `docs/guide/README.md` — added Chapter 31 to table of contents
- `docs/guide/30-personas.md` — updated navigation footer to link to Chapter 31
- `docs/guide/appendix-d-glossary.md` — added API Surface, Context Query, Instance Discovery entries
- `.gsd/milestones/M013/slices/S03/tasks/T04-PLAN.md` — added Observability Impact section
