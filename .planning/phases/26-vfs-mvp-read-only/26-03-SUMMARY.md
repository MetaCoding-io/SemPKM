---
phase: 26-vfs-mvp-read-only
plan: 03
subsystem: vfs, webdav
tags: [wsgidav, a2wsgi, ttl-cache, cachetools, webdav, fastapi-mount, wsgi-middleware]

# Dependency graph
requires:
  - phase: 26-01
    provides: "SyncTriplestoreClient, ApiToken model, nginx /dav/ proxy, wsgidav package"
  - phase: 26-02
    provides: "SemPKMDAVProvider, collection classes, ResourceFile, SemPKMWsgiAuthenticator"
provides:
  - "wsgidav mounted at /dav in FastAPI via WSGIMiddleware -- full WebDAV read-only VFS operational"
  - "TTLCache (30s, 256 entries) for directory listing results -- prevents SPARQL on every PROPFIND"
  - "User guide documenting WebDAV mount for macOS, Windows, and Linux"
affects: [27-vfs-write-auth]

# Tech tracking
tech-stack:
  added: []
  patterns: [ttl-cache-with-thread-lock, wsgi-mount-via-a2wsgi, readonly-wsgidav-config]

key-files:
  created:
    - backend/app/vfs/cache.py
    - docs/guide/23-vfs.md
  modified:
    - backend/app/main.py
    - backend/app/vfs/collections.py
    - backend/app/vfs/auth.py
    - docs/guide/index.html

key-decisions:
  - "TTL cache uses threading.Lock for write safety in wsgidav's WSGI thread pool"
  - "wsgidav readonly=True config enforces read-only at framework level (returns 403 via collection classes before wsgidav's 405)"
  - "Cache keys use path-style strings: root:models, model:{id}:types, type:{id}:{label}"

patterns-established:
  - "TTL cache pattern: module-level TTLCache + Lock singleton shared across all DAV collection instances"
  - "WSGI-in-ASGI pattern: WsgiDAVApp wrapped in a2wsgi.WSGIMiddleware, mounted via app.mount('/dav', ...)"

requirements-completed: [VFS-01, VFS-02]

# Metrics
duration: 12min
completed: 2026-03-01
---

# Phase 26 Plan 03: VFS Mount + Cache + Verification Summary

**wsgidav mounted at /dav with TTL-cached directory listings, end-to-end verified (PROPFIND, GET, read-only enforcement, auth), plus user guide for macOS/Windows/Linux WebDAV mount**

## Performance

- **Duration:** 12 min (across two sessions, split by human-verify checkpoint)
- **Started:** 2026-03-01T05:48:04Z
- **Completed:** 2026-03-01T06:16:00Z
- **Tasks:** 3 (+ post-checkpoint docs)
- **Files modified:** 6

## Accomplishments
- Created TTL cache module (30s TTL, 256 max entries) with thread-safe writes for SPARQL listing results
- Wired cache into RootCollection, ModelCollection, and TypeCollection to prevent SPARQL on every PROPFIND
- Mounted wsgidav at /dav in FastAPI main.py via a2wsgi WSGIMiddleware with readonly=True
- Validated full end-to-end: PROPFIND returns 207 with model dirs, GET returns Markdown+frontmatter, PUT returns 403, unauthenticated returns 401
- Created comprehensive user guide (docs/guide/23-vfs.md) with OS-specific mount instructions
- Added chapters 21-23 to the guide sidebar index

## Task Commits

Each task was committed atomically:

1. **Task 1: TTL cache module and wire into collections** - `83eb4f1` (feat)
2. **Task 2: Mount wsgidav in main.py** - `a9891ef` (feat)
3. **Task 3: End-to-end WebDAV verification** - checkpoint, approved by user
4. **Post-checkpoint: User guide docs** - `6c3f72e` (docs)

## Files Created/Modified
- `backend/app/vfs/cache.py` - TTLCache singleton with threading.Lock for directory listing results
- `backend/app/vfs/collections.py` - Updated RootCollection, ModelCollection, TypeCollection to check cache before SPARQL
- `backend/app/main.py` - Added wsgidav mount at /dav with WSGIMiddleware, SemPKMDAVProvider, and readonly config
- `backend/app/vfs/auth.py` - Minor fix: removed stale database_url import replaced with settings reference
- `docs/guide/23-vfs.md` - User guide for WebDAV VFS mount (token generation, macOS/Windows/Linux instructions, file format, troubleshooting)
- `docs/guide/index.html` - Added chapters 21 (SPARQL Console), 22 (Keyword Search), 23 (VFS) to sidebar

## Decisions Made
- TTL cache uses `threading.Lock` for write safety -- cachetools.TTLCache is not thread-safe for writes, and wsgidav calls from a WSGI thread pool
- Cache keys follow path convention (`root:models`, `model:{id}:types`, `type:{id}:{label}`) for easy invalidation in future write support
- wsgidav `readonly=True` config is set, but collection classes raise HTTP_FORBIDDEN (403) first -- this is acceptable since both block writes (user verified PUT returns 403 not 405)
- User guide file named `23-vfs.md` following existing chapter numbering convention

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] auth.py database_url import fix**
- **Found during:** Task 2 (Mount wsgidav in main.py)
- **Issue:** `SemPKMWsgiAuthenticator.__init__` referenced `database_url` from config dict but needed `sempkm_db_url` key matching the wsgidav config
- **Fix:** Aligned the config key reference in auth.py with the `sempkm_db_url` key used in main.py dav_config
- **Files modified:** backend/app/vfs/auth.py
- **Committed in:** a9891ef (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor alignment fix, no scope creep.

### Noted Variance

PUT returns 403 (Forbidden) instead of plan's expected 405 (Method Not Allowed). This occurs because the collection classes raise `HTTP_FORBIDDEN` before wsgidav's `readonly` config can return 405. The user confirmed this is acceptable -- writes are blocked either way.

## Issues Encountered
None beyond the noted 403 vs 405 variance.

## User Setup Required

None - no external service configuration required. API token generation is documented in the user guide.

## Next Phase Readiness
- Full read-only VFS stack is operational and verified
- Phase 27 (VFS Write + Auth) can build on this foundation to add write support
- Phase 28 (UI Polish + Integration Testing) can test WebDAV alongside other features
- Cache invalidation hooks will be needed when write support is added (cache keys are structured for this)

## Self-Check: PASSED

All 6 files verified present. All 3 task commits verified in git log.

---
*Phase: 26-vfs-mvp-read-only*
*Completed: 2026-03-01*
