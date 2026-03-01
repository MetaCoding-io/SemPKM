# Phase 26: VFS MVP Read-Only - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement a read-only WebDAV endpoint at `/dav/` using wsgidav + a2wsgi ASGI/WSGI bridge. Objects are browsable as Markdown files organized in a nested `/model/type/` directory structure. Requires API token auth (designed and implemented here since native OS WebDAV clients cannot use session cookies). Creates `SyncTriplestoreClient` for use in the WSGI thread pool.

</domain>

<decisions>
## Implementation Decisions

### Directory Structure
- Nested by model + type: `/dav/{model-id}/{type-label}/` e.g. `/dav/basic-pkm/Note/`, `/dav/basic-pkm/Project/`
- Hardcoded for MVP — no user-configurable path mapping in v2.2
- MountSpec vocabulary design noted for future (user said "just nested by model+type, no config yet")
- Type folders contain one `.md` file per object, named by object label (slugified)

### Authentication
- API token Basic auth REQUIRED even for read-only (no unauthenticated access)
- Username: SemPKM username, Password: revocable API token
- Custom wsgidav HTTPAuthenticator validates against token store
- Token model and generation endpoint built in this phase (required to test Phase 26)
- Full Settings UI for token management deferred to Phase 27

### SyncTriplestoreClient
- New sync (non-async) HTTP client wrapping the triplestore
- Required because wsgidav runs in a WSGI thread pool — cannot use httpx.AsyncClient
- Implements the same queries as the async client but using `httpx.Client` (sync)

### File Format
- Each object rendered as: YAML frontmatter block + markdown body
- Frontmatter: type IRI, object IRI, label, key SHACL-declared properties
- Body: object body content (same as workspace editor content)
- File extension: `.md`

### Read-Only Enforcement
- No write operations: PUT, DELETE, MOVE, COPY all return 405 Method Not Allowed
- Strictly read-only MVP — write path is Phase 27

### Three Required Python Packages
- `wsgidav>=4.3.3,<5.0`
- `a2wsgi>=1.10`
- `python-frontmatter>=1.1.0`

### Claude's Discretion
- TTL cache strategy for directory listings (avoid SPARQL on every PROPFIND)
- Object file naming when label conflicts exist within a type folder
- nginx proxy configuration for `/dav/` path

</decisions>

<specifics>
## Specific Ideas

- wsgidav is mounted as an ASGI sub-app via a2wsgi within main.py (not a separate service)
- nginx must proxy `/dav/` to the FastAPI app — need to add location block
- DECISIONS.md (DEC-03) specifies this approach was chosen specifically because FUSE requires SYS_ADMIN Docker cap (rejected for managed hosting compatibility)

</specifics>

<deferred>
## Deferred Ideas

- User-configurable VFS path mappings (MountSpec) — future phase
- Mental Model manifest-declared VFS paths — future phase
- Write path — Phase 27
- Full Settings UI for token management — Phase 27

</deferred>

---

*Phase: 26-vfs-mvp-read-only*
*Context gathered: 2026-02-28*
