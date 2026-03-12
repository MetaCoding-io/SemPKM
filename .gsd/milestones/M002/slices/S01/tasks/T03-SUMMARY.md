---
id: T03
parent: S01
milestone: M002
provides:
  - BASE_NAMESPACE production guidance in deployment docs
  - BASE_NAMESPACE checklist item in production checklist
key_files:
  - docs/guide/20-production-deployment.md
key_decisions:
  - Placed Namespace Configuration section immediately before Production Checklist (after Resetting the Instance) since namespace is a deployment concern, not an operational one
patterns_established:
  - none
observability_surfaces:
  - none (documentation only)
duration: 10m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Document BASE_NAMESPACE production guidance

**Added "Namespace Configuration" section to the production deployment guide explaining IRI collision risks of the default `example.org` namespace, and added `BASE_NAMESPACE` to the production checklist.**

## What Happened

Added a new `## Namespace Configuration` section to `docs/guide/20-production-deployment.md` before the Production Checklist. The section covers:

1. What `BASE_NAMESPACE` controls (IRI prefix for all objects and named graphs)
2. Why the default `https://example.org/data/` is dangerous in production (IRI collisions during federation, data migration, and linked data interoperability)
3. How to set it correctly (use a domain you control, must end with `/`, must be a valid IRI)
4. The critical warning: set it before creating any data — changing it later orphans existing objects
5. Example configurations for single and multi-instance deployments

Also added `BASE_NAMESPACE` as a checklist item in the Production Checklist, immediately after the `SECRET_KEY` item.

## Verification

All task-level and slice-level checks passed:

- `grep -c 'BASE_NAMESPACE' docs/guide/20-production-deployment.md` → **9** (≥3 required)
- `grep -A1 'Namespace Configuration' docs/guide/20-production-deployment.md` → section heading exists
- `grep 'BASE_NAMESPACE' docs/guide/20-production-deployment.md | grep -i 'checklist\|example.org\|collision\|set'` → covers all key topics
- Heading order verified: Namespace Configuration appears before Production Checklist

Slice-level verification (all T01–T03 checks):
- `rg 'escape_sparql_regex' backend/app/views/service.py` → both call sites use shared function ✓
- `rg 'logger\.info.*Magic link token' backend/app/auth/router.py` → inside conditional branches ✓
- `grep 'require_role.*owner' backend/app/debug/router.py | wc -l` → 2 ✓
- `grep 'slowapi' backend/pyproject.toml` → dependency present ✓
- `grep 'limiter.limit' backend/app/auth/router.py | wc -l` → 2 ✓
- `grep 'BASE_NAMESPACE' docs/guide/20-production-deployment.md` → section exists ✓

## Diagnostics

None — documentation-only task. Future agents can inspect by reading `docs/guide/20-production-deployment.md`.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/20-production-deployment.md` — added Namespace Configuration section and BASE_NAMESPACE checklist item
