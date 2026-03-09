# Phase 52: Bug Fixes & Security - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix known regressions (event log compound events, missing undo for object.create) and lint dashboard filter layout, then gate SPARQL access by user role. No new features — fix what's broken and close the security gap.

</domain>

<decisions>
## Implementation Decisions

### SPARQL Role Gating
- **Guest:** No SPARQL access. Hide the SPARQL console tab entirely from the bottom panel (don't render the tab).
- **Member:** SPARQL access to current materialized graph only. `all_graphs` parameter rejected — no toggle shown. If member tries to use `FROM` or `GRAPH` clauses targeting event/named graphs, return 403 Forbidden.
- **Owner:** Full SPARQL access including `all_graphs=true`. No restrictions.
- **Error handling:** Always return HTTP 403 for any SPARQL permission violation (no differentiated status codes).
- **Implementation pattern:** Use existing `require_role()` dependency from `auth/dependencies.py` — proven pattern used in admin routes.

### Event Log Fixes
- **Compound events:** Events like "body.set,object.create" currently show no bubble, no diff, no undo because the template doesn't match compound operation types. Fix: display as "object.create" (primary action) with an expandable detail section showing that body was also set.
- **Undo for object.create:** Currently unavailable. Implement via a compensating event that soft-archives the object (not hard delete). The undo creates an explicit compensating event preserving the audit trail — data is hidden, not destroyed.
- **Scope:** These two issues (compound event display + object.create undo) are the known bugs. If other diff issues surface during investigation, fix them too.

### Lint Dashboard Layout
- **Problem:** Filter controls (dropdowns + search input) stretch too wide or overflow.
- **Fix:** Remove hard-coded `200px` on search input. Make filter controls responsive with `flex-wrap: wrap` so they flow to a second line on narrow viewports. All controls should always be visible.
- **Verification:** Include an interactive Playwright session to reproduce and verify the fix across viewport sizes.

### Standing Requirements
- Every wave/phase must update E2E tests and user guide if user-visible behavior changes. This is reinforced from PROJECT.md Standing Requirements.

### Claude's Discretion
- Exact CSS values for filter control sizing
- How to detect the "primary" operation in compound event types
- Soft-archive implementation details (RDF predicate choice, UI indicator)

</decisions>

<specifics>
## Specific Ideas

- Compound events should show the primary action as the bubble label, with expandable detail for secondary operations
- Soft-archive for undo should use a compensating event, not a direct delete — preserving the full audit trail
- Lint fix should be verified with a Playwright interactive session, not just eyeballed

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `require_role()` dependency in `backend/app/auth/dependencies.py` (lines 87-107) — proven pattern for role gating
- `build_compensation()` in `backend/app/events/query.py` (lines 299-415) — existing compensating event builder to extend
- `difflib.unified_diff` in query.py — proven diff computation for body.set

### Established Patterns
- SPARQL graph scoping via `scope_to_current_graph()` in `sparql/client.py` (lines 19-73) — already handles FROM injection
- Event detail template (`event_detail.html`) — renders 5 operation types with if/elif blocks
- Admin routes use `Depends(require_role("owner"))` — direct model to follow

### Integration Points
- `sparql/router.py` GET/POST endpoints (lines 77-125) — add role dependency here
- `all_graphs` parameter on line 28, 49 of client.py — guard with role check
- Bottom panel tab rendering — conditionally hide SPARQL tab for guests
- Event query service — extend to handle compound operation types
- Lint dashboard CSS in `workspace.css` (lines 3542-3685) — fix filter toolbar

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 52-bug-fixes-security*
*Context gathered: 2026-03-09*
