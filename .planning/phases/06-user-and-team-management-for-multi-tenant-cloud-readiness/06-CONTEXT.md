# Phase 6: User and Team Management for Multi-Tenant Cloud Readiness - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add user identity, role-based access, and instance management to transform single-user SemPKM into a system that supports multiple users per instance with an owner/member/guest model. Each deployment remains one instance = one triplestore (no multi-project abstraction). The cloud hosting model (orchestrating many isolated instances) is infrastructure-level, not application-level multi-tenancy.

This phase retrofits authentication and authorization into the existing API and event model built in Phases 1-2, adds user/session management backed by SQLite (local) or PostgreSQL (cloud), and delivers a setup wizard for first-run configuration.

</domain>

<decisions>
## Implementation Decisions

### Architecture Model
- **One instance = one project = one triplestore** — no multi-project abstraction within an instance
- No "project" entity — the instance itself is the unit of organization
- All users in an instance share the same knowledge data (no object-level privacy)
- Cloud service orchestrates many isolated instances, each with its own RDF4J repository
- Cloud uses shared API tier routing to per-customer RDF4J stores (not fully isolated containers)
- One shared PostgreSQL for all cloud user accounts, instance metadata, and membership

### Authentication & Identity
- **Passwordless only** — no passwords stored in SQL database (security by design if DB is leaked)
- **Local first-run**: Setup wizard in browser, one-time setup token shown in terminal. Owner enters token to claim the instance. Long-lived session after that. No SMTP needed for initial setup.
- **SMTP setup deferred**: Only required when owner wants to invite other users. Not part of initial install.
- **Cloud**: Magic link emails from day one (cloud service handles email delivery)
- **User-first onboarding** (cloud): User signs up with email first, then creates an instance
- **Sessions**: Configurable duration, default 30 days
- **API access**: Session-based only — no separate API tokens/keys
- **DNS verification** required for custom domains (both local self-hosted and cloud)

### Roles (Owner / Member / Guest)
- **Owner** (exactly one per instance): Full control — manage users, install/remove Mental Models, configure instance, billing, transfer ownership
- **Member**: Read/write knowledge data (create, edit, query objects). Soft-delete only (archive). Cannot install/remove models or manage users.
- **Guest**: Read-only access to all data and instance info. Can run SPARQL SELECT queries. Cannot create, edit, or delete anything.
- One user identity across many instances (like GitHub orgs)
- Users added via email invitation (owner sends invite)

### Permission Enforcement
- **Writes always go through command API** — role enforcement happens here
- **SPARQL endpoint**: Authenticated access only. All roles (including guest) can query. No write access via SPARQL.
- **RDF4J port not exposed** to host in Docker — only backend container talks to triplestore
- Members can soft-delete (archive) objects; only owner can permanently delete or restore
- Mental Model management (install/remove) is owner-only

### User Provenance
- **Events track user identity** — each event records which user performed the action
- Objects show "created by" and "last modified by"
- This requires retroactively enriching the event model from Phase 1

### SQL Database
- **SQLite for local installs, PostgreSQL for cloud** — identical schema, same ORM/data layer, two connection strings
- Database holds: user accounts, sessions, instance config, membership/roles, invitation state
- No knowledge data in SQL — that stays in the triplestore

### Rework Required (Phases 1-2)
- **Event store**: Add user identity (provenance) to event model — currently events don't track who performed them
- **Command API**: Add auth middleware — currently unauthenticated. Enforce role-based access per command type
- **SPARQL endpoint**: Add authentication — currently open. At minimum verify user is a member/guest of this instance
- **SHACL validation**: Minimal changes — reports reference commits which will now carry user identity

### Claude's Discretion
- ORM/library choice for SQLite+PostgreSQL dual backend
- Session token implementation (JWT vs opaque tokens vs signed cookies)
- Magic link token expiration and security details
- Setup wizard UI design and flow
- Database migration tooling choice
- How to handle the owner's long-lived local session (refresh strategy)

</decisions>

<specifics>
## Specific Ideas

- Cloud domains: `<name>.sempkm.io` subdomains or custom domains with DNS verification
- The SQL database should be safe if leaked — no passwords, no secrets. Only emails, roles, session metadata.
- Local single-user experience should be near-zero friction — docker-compose up, enter setup token, start working
- SMTP is a progressive enhancement: needed only when sharing, not for solo use

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness*
*Context gathered: 2026-02-22*
