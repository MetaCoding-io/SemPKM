# Phase 27: VFS Write + Auth - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the Phase 26 WebDAV VFS with: (1) write path so editing `.md` files via WebDAV propagates body changes through the SemPKM event store, and (2) full Settings UI for API token management (generation, listing, revocation). Depends on Phase 26's read-only VFS and API token model.

</domain>

<decisions>
## Implementation Decisions

### Write Path Scope
- Body content only — editing the `.md` file body triggers a `body.set` event via the event store
- Frontmatter changes in the file are silently ignored on write (MVP simplicity)
- No property patching via frontmatter round-trip — deferred

### Token Lifecycle
- Manual revocation only — tokens do not expire automatically
- Tokens are permanent until the user explicitly revokes them from Settings
- Simpler implementation, user controls lifecycle

### Write Conflict Handling
- ETag-based concurrency: wsgidav sends `If-Match` header, server validates against current object version
- If mismatch: return 412 Precondition Failed (standard WebDAV behavior)
- Claude's discretion on exact ETag derivation (event log hash or timestamp)

### Settings UI
- "Virtual Filesystem" section added to Settings page
- Displays: WebDAV endpoint URL (copy-to-clipboard), API tokens table (name, created date, revoke button)
- Token generation: user provides a name/label, system generates token, shown once then hidden
- Revocation: immediate — invalidates all active WebDAV sessions using that token

### Authentication (from Phase 26)
- Phase 26 creates the token model and basic auth validator
- Phase 27 adds the full management UI on top of Phase 26's auth infrastructure

### Claude's Discretion
- Whether to show partial token value after creation (e.g., first 8 chars + `...`) or hide entirely
- ETag derivation strategy
- Whether revocation is immediate (in-memory check) or requires restart

</decisions>

<specifics>
## Specific Ideas

- `body.set` is an existing command in the write API — the DAV write path calls the same internal service as the workspace editor save
- API token Basic auth pattern from DECISIONS.md: username=SemPKM username, password=revocable token

</specifics>

<deferred>
## Deferred Ideas

- Frontmatter round-trip (property patching via DAV writes) — future phase
- Token expiry / TTL — not needed for v2.2, manual revocation is sufficient
- MOVE/COPY/DELETE object operations via WebDAV — scope creep, future

</deferred>

---

*Phase: 27-vfs-write-auth*
*Context gathered: 2026-02-28*
