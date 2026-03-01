---
phase: 27-vfs-write-auth
plan: 02
subsystem: vfs-write
tags: [webdav, write-path, event-store, etag, concurrency]
dependency_graph:
  requires: [27-01]
  provides: [27-03]
  affects: [backend/app/vfs/]
tech_stack:
  added: []
  patterns:
    - begin_write/end_write wsgidav write hook pattern
    - asyncio.run() sync-to-async bridge for WSGI thread pool
    - ETag concurrency via wsgidav evaluate_http_conditionals
key_files:
  created:
    - backend/app/vfs/write.py
  modified:
    - backend/app/vfs/resources.py
    - backend/app/vfs/provider.py
    - backend/app/vfs/auth.py
    - backend/app/main.py
decisions:
  - id: WP-01
    summary: "Use begin_write/end_write hooks (not write_data) — wsgidav streams body via begin_write() returning a BytesIO buffer"
  - id: WP-02
    summary: "set_event_store() injection method on DAVProvider — avoids restructuring module-level DAV construction"
  - id: WP-03
    summary: "ETag concurrency delegated to wsgidav's evaluate_http_conditionals — If-Match/412 handled before begin_write() is called"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-01"
  tasks_completed: 4
  files_changed: 5
---

# Phase 27 Plan 02: VFS Write Path Summary

**One-liner:** WebDAV PUT writes propagate body content through `body.set` event store via `begin_write`/`end_write` hooks with SHA-256 ETag concurrency and frontmatter stripping.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 27-02-1 | Create vfs/write.py — body parsing and event store bridge | 5da1544 | backend/app/vfs/write.py |
| 27-02-2 | Add SHA-256 ETag support to ResourceFile | 2a391e9 | backend/app/vfs/resources.py |
| 27-02-3 | Implement write path with begin_write/end_write on ResourceFile | 5f657c5 | backend/app/vfs/resources.py |
| 27-02-4 | Wire EventStore into the wsgidav provider via app startup | 8ca3ac7 | backend/app/vfs/provider.py, backend/app/vfs/auth.py, backend/app/main.py |

## What Was Built

### vfs/write.py (new file)

Two functions:

**`parse_dav_put_body(raw_bytes: bytes) -> str`**
- Decodes bytes as UTF-8
- Detects YAML frontmatter (`---\n` or `---\r\n` opening delimiter)
- Scans for closing `---` delimiter and returns only the body content after it
- Handles both LF and CRLF line endings
- Falls back to full content if no frontmatter found

**`write_body_via_event_store(...)`**
- Bridges sync wsgidav WSGI thread to async `EventStore.commit()`
- Uses `asyncio.run()` — correct for WSGI thread pool where no event loop is running
- Inner `_commit_body_set()` creates `BodySetParams`, calls `handle_body_set()`, then `event_store.commit()`

### ResourceFile write path (modified)

- `get_etag()` upgraded from MD5 to SHA-256 (64-char hex digest)
- `begin_write()` replaced — no longer raises HTTP 403; returns a `BytesIO` buffer for wsgidav to stream the request body into
- `end_write()` added — reads buffer, calls `parse_dav_put_body()` to strip frontmatter, looks up object IRI via `_get_object_info()`, then calls `write_body_via_event_store()` with user context from environ
- `handle_delete()`, `handle_move()`, `handle_copy()` still raise HTTP 403
- `event_store` parameter added to constructor (default `None` for backward compat)

### SemPKMDAVProvider (modified)

- Added `set_event_store(event_store)` injection method
- `get_resource_inst()` passes `event_store` to each `ResourceFile` constructor

### main.py (modified)

- After `EventStore` creation in lifespan: `_dav_provider.set_event_store(event_store)`
- Removed `readonly: True` from `_dav_config` — PUT method is now allowed; DELETE/MOVE/COPY blocked at resource level

### auth.py (modified)

- `basic_auth_user()` now sets `environ["sempkm.user_role"]` alongside `user_id` and `user_email`
- Used by `end_write()` to record role in event provenance

## Implementation Note: wsgidav write interface

The plan referenced `write_data()` as the wsgidav hook. After inspecting the wsgidav source, the actual interface is `begin_write()`/`end_write()`:

- `begin_write(content_type=None)` must return a writable file-like object
- wsgidav writes request body chunks into it, then calls `end_write(with_errors=bool)`
- `write_data()` does not exist in this version of wsgidav

This deviation was handled automatically (Rule 1 — using correct API vs plan's incorrect assumption). The semantics are identical; the buffer-based approach is simpler than the plan's content_file approach.

Also: `If-Match` ETag validation is handled automatically by wsgidav's `_evaluate_if_headers()` before `begin_write()` is called — raising HTTP 412 Precondition Failed when the ETag doesn't match. No manual check needed in `begin_write()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - API Deviation] Used begin_write/end_write instead of write_data**
- **Found during:** Task 27-02-3
- **Issue:** Plan specified `write_data(content_file, content_type, content_length, dry_run)` but wsgidav's actual interface is `begin_write()` returning a writable buffer + `end_write()` callback
- **Fix:** Implemented `begin_write()` returning `io.BytesIO` buffer; `end_write()` reads buffer and commits via event store
- **Files modified:** backend/app/vfs/resources.py
- **Commit:** 5f657c5

**2. [Rule 2 - Missing wiring] set_event_store() injection vs config dict**
- **Found during:** Task 27-02-4
- **Issue:** DAV provider is constructed at module load time before lifespan runs; cannot inject event_store via constructor or config dict at creation time
- **Fix:** Added `set_event_store()` method to `SemPKMDAVProvider`; called in lifespan after EventStore creation
- **Files modified:** backend/app/vfs/provider.py, backend/app/main.py
- **Commit:** 8ca3ac7

## Self-Check: PASSED

Files created:
- backend/app/vfs/write.py — exists, contains `parse_dav_put_body` and `write_body_via_event_store`

Files modified:
- backend/app/vfs/resources.py — `begin_write()` + `end_write()` implemented, SHA-256 ETag
- backend/app/vfs/provider.py — `set_event_store()` added, event_store passed to ResourceFile
- backend/app/vfs/auth.py — `sempkm.user_role` set in environ
- backend/app/main.py — `set_event_store()` called in lifespan, `readonly: True` removed

Commits verified:
- 5da1544: feat(27-02): create vfs/write.py
- 2a391e9: feat(27-02): upgrade ResourceFile.get_etag() to SHA-256
- 5f657c5: feat(27-02): implement ResourceFile write path
- 8ca3ac7: feat(27-02): wire EventStore into DAV provider
