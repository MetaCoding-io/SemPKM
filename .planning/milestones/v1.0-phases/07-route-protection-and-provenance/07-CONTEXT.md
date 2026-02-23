# Phase 7: Route Protection and Provenance - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Enforce server-side authentication and authorization on all browser, views, and admin HTML routes using the existing auth system (get_current_user, require_role). Record user provenance in event metadata for browser-originated writes. Also includes a quick audit of API routes to verify none are accidentally unprotected.

</domain>

<decisions>
## Implementation Decisions

### Auth failure UX on HTML routes
- Unauthenticated users hitting browser/views/admin routes get a 302 redirect to /login.html
- Redirect preserves the original URL via query parameter (e.g. /login.html?next=/browser/object/some-iri) so users return there after login
- Authenticated users who lack the required role (e.g. member accessing /admin/) see a simple styled 403 HTML page
- 403 page matches app styling — "Access Denied" heading, explanation of why, link back to workspace

### Role mapping to endpoints
- Browser READ endpoints (object viewing, tree navigation, search, relations, lint, types): require authentication only (get_current_user) — any logged-in user can read
- Browser WRITE endpoints (POST create, POST save, POST body): require owner or member role via require_role("owner", "member")
- Views READ endpoints (table, card, graph, menu, available): same as browser reads — any authenticated user
- Admin routes (all of them — read and write): strictly owner-only via require_role("owner")
- Quick audit of API routes to verify consistent auth coverage

### Provenance detail level
- Browser writes must pass performed_by (user IRI) to EventStore.commit() — currently missing
- Also record the user's role at time of action via a separate RDF predicate (EVENT_PERFORMED_BY_ROLE)
- EventStore.commit() signature adds an explicit performed_by_role parameter — callers pass both user IRI and role
- System operations (model installs, seed data) get a well-known system IRI (urn:sempkm:system) instead of remaining anonymous

### HTMX error handling
- When an HTMX partial request gets a 401 (session expired), swap an inline error into the target area: "Session expired" message with a login link to /login.html
- When an HTMX request gets a 403, same pattern: inline "Access denied" message in the target area
- Implemented as per-endpoint responses (each protected route returns an HTML error fragment when auth fails), not a global HTMX handler

### Claude's Discretion
- Exact styling of the 403 error page
- HTMX error fragment HTML/CSS details
- How to handle the /login.html?next= redirect-back flow (may need frontend changes)
- Whether to use a shared auth dependency that returns HTML errors for HTMX vs JSON for API, or handle separately

</decisions>

<specifics>
## Specific Ideas

- The existing auth dependencies (get_current_user, require_role) in auth/dependencies.py are well-structured — reuse them directly on the unprotected routes
- EventStore.commit() already accepts performed_by: URIRef | None — extend the signature, don't replace it
- The /api/commands endpoint already demonstrates the correct pattern for passing performed_by with user IRI
- System attribution should use a consistent well-known IRI (urn:sempkm:system) so absence of performed_by is never ambiguous

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-route-protection-and-provenance*
*Context gathered: 2026-02-22*
