# M013: API Surface for External Clients — Research

**Date:** 2026-03-17
**Status:** Complete

## Key Findings

1. **Auth gap is the #1 risk.** `get_current_user` in `auth/dependencies.py` only checks session cookies. `AuthService.verify_api_token()` exists and is tested but has no FastAPI dependency wiring. Must build dual-auth dependency first.

2. **nginx blocks Bearer tokens.** The `/api/` proxy block doesn't forward `Authorization` header — only `/dav/` does. One-line fix required.

3. **Shape serialization is simpler than expected.** `ShapesService` returns plain Python dataclasses (`NodeShapeForm`, `PropertyShape`, `PropertyGroup`) that serialize cleanly via `dataclasses.asdict()`. No Pydantic migration needed.

4. **All data-layer services exist.** ShapesService, IconService, LabelService, SearchService, model registry — all tested and available on `app.state`. New endpoints are service-to-JSON wiring.

5. **Context-query is the only genuinely new logic.** URL matching via SPARQL + FTS keyword matching via SearchService, with result aggregation. Everything else is serialization of existing service outputs.

## Recommended Slice Boundaries

- S01: Auth + Well-Known + nginx (prove external plumbing)
- S02: Types + Shapes endpoints (read-only serialization)
- S03: Context-Query endpoint (new SPARQL + FTS logic)
- S04: E2E Tests + User Guide (standing requirements)

## Candidate Requirements: API-01 through API-08
