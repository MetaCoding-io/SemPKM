---
phase: 26-vfs-mvp-read-only
verified: 2026-03-01T07:00:00Z
status: human_needed
score: 9/9 automated must-haves verified
re_verification: false
human_verification:
  - test: "WebDAV client connects and shows directory listing"
    expected: "PROPFIND /dav/ returns 207 Multi-Status XML with model directories (e.g., basic-pkm); macOS Finder or cadaver lists them as folders"
    why_human: "Requires a live Docker stack with valid ApiToken — cannot verify HTTP responses programmatically without running containers"
  - test: "Object file content has YAML frontmatter with required fields"
    expected: "GET /dav/basic-pkm/Note/{slug}.md returns file starting with ---\\ntype_iri: ...\\nobject_iri: ...\\nlabel: ... with a YAML block and optional Markdown body below"
    why_human: "Requires live SPARQL query against real triplestore data — cannot simulate without running containers"
  - test: "Read-only enforcement — PUT returns 403"
    expected: "PUT to /dav/basic-pkm/Note/test.md returns HTTP 403 (Forbidden); DELETE and MOVE also blocked"
    why_human: "Requires live wsgidav stack to exercise the write-rejection path; note SUMMARY documented 403 vs planned 405 — human should confirm 403 is correct and acceptable"
  - test: "Unauthenticated PROPFIND returns 401"
    expected: "curl -X PROPFIND http://localhost:3901/dav/ -H 'Depth: 1' returns 401 Unauthorized, not 404 or 200"
    why_human: "Requires live Docker stack"
  - test: "TTL cache prevents redundant SPARQL — second PROPFIND is faster"
    expected: "Second PROPFIND /dav/ within 30s returns without SPARQL query to triplestore (check backend logs)"
    why_human: "Requires log inspection on a live system"
---

# Phase 26: VFS MVP Read-Only — Verification Report

**Phase Goal:** Users can mount SemPKM objects as files via a WebDAV endpoint, browsing and reading object bodies as Markdown files with SHACL-derived frontmatter using any WebDAV client (macOS Finder, Windows Explorer, Linux Nautilus)
**Verified:** 2026-03-01T07:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Success Criteria (from ROADMAP.md)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can connect a WebDAV client to `/dav/` and see a directory of objects | ? HUMAN | Code path complete: nginx `/dav/` proxies → FastAPI → wsgidav → `SemPKMDAVProvider` → `RootCollection` SPARQL query. Needs live stack to confirm 207 response. |
| 2 | Each object appears as a `.md` file with SHACL-derived frontmatter (type, IRI, title, key predicates) | ? HUMAN | `ResourceFile._render()` builds `{type_iri, object_iri, label}` in frontmatter, adds `_PREDICATE_LABELS` mapped fields and extra props under `properties` key. Wired and substantive — needs live data to confirm output format. |
| 3 | Opening a file shows the current state — not stale or cached data | ? HUMAN | TTL cache is 30s keyed by path for *directory listings* only; individual `ResourceFile._render()` re-queries SPARQL on each new request instance. Cache architecture is correct for currency, but needs live verification. |
| 4 | WebDAV mount is read-only — no writes, no DELETE, no MOVE succeed | ? HUMAN | All collection classes raise `HTTP_FORBIDDEN`, `ResourceFile.begin_write()` raises `HTTP_FORBIDDEN`, and `readonly=True` in wsgidav config. SUMMARY notes PUT returns 403 (not 405 as planned) — human should confirm 403 is accepted. |

**Automated score: 9/9 must-haves verified (code-level). 4/4 success criteria need human confirmation on live stack.**

---

## Required Artifacts

### Plan 26-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/pyproject.toml` | wsgidav, a2wsgi, python-frontmatter declared | VERIFIED | Lines 25-27: `"wsgidav>=4.3.3,<5.0"`, `"a2wsgi>=1.10"`, `"python-frontmatter>=1.1.0"` |
| `backend/app/triplestore/sync_client.py` | SyncTriplestoreClient with sync `query()` | VERIFIED | 37 lines, `httpx.Client(timeout=30.0)`, POST form-encoded, Accept JSON, `raise_for_status()`, `close()` |
| `backend/app/auth/models.py` | ApiToken ORM class with `token_hash`, `revoked_at` | VERIFIED | Lines 79-96: `class ApiToken(Base)` with all required columns: `id`, `user_id` FK CASCADE, `name`, `token_hash` (VARCHAR 64 unique indexed), `created_at`, `last_used_at`, `revoked_at` |
| `backend/migrations/versions/003_api_tokens.py` | Alembic migration creating api_tokens table | VERIFIED | `revision="003"`, `down_revision="002"`, `upgrade()` creates table with all columns, indexes, FK constraint, `downgrade()` drops it |
| `backend/app/auth/service.py` | `create_api_token`, `verify_api_token`, `verify_api_token_sync` | VERIFIED | All three methods exist at lines 189, 208, 232 — SHA-256 hashing, plaintext returned once |
| `backend/app/auth/router.py` | POST `/tokens` endpoint returning `{token, id, name, created_at}` | VERIFIED | Lines 234-265: `status_code=201`, `CreateTokenResponse` with `token` field, requires `get_current_user` dependency |
| `frontend/nginx.conf` | `/dav/` location block with Authorization passthrough | VERIFIED | Lines 76-96: `proxy_pass http://api:8000/dav/`, `proxy_set_header Authorization $http_authorization`, `proxy_pass_header Authorization`, WebDAV headers, 300s timeouts |

### Plan 26-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/vfs/__init__.py` | Package marker | VERIFIED | Exists (empty file, confirmed by `ls`) |
| `backend/app/vfs/provider.py` | `SemPKMDAVProvider` routing by path depth | VERIFIED | Extends `DAVProvider`, dispatches 0/1/2/3 path parts to Root/Model/Type/ResourceFile correctly |
| `backend/app/vfs/collections.py` | `RootCollection`, `ModelCollection`, `TypeCollection` | VERIFIED | All three classes present (312 lines), SPARQL queries use correct `urn:sempkm:` namespace, slugification with SHA-256 deduplication, read-only enforcement on all write methods |
| `backend/app/vfs/resources.py` | `ResourceFile` rendering Markdown+frontmatter | VERIFIED | Extends `DAVNonCollection`, `_render()` builds frontmatter dict with `type_iri/object_iri/label`, uses `python-frontmatter`, `_cached_content` caches per instance, `begin_write()` raises `HTTP_FORBIDDEN` |
| `backend/app/vfs/auth.py` | `SemPKMWsgiAuthenticator` validating via sync SQLAlchemy | VERIFIED | Extends `BaseDomainController`, `basic_auth_user()` creates sync SQLAlchemy engine, SHA-256 hash check against `ApiToken`, joins `User` table for email match, `revoked_at.is_(None)` filter |

### Plan 26-03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/vfs/cache.py` | `TTLCache(maxsize=256, ttl=30)` with `threading.Lock` | VERIFIED | Module-level `listing_cache`, `_cache_lock`, `cached_get_member_names()` helper used by all three collection classes |
| `backend/app/main.py` | `app.mount("/dav", ...)` with `WsgiDAVApp` | VERIFIED | Lines 394-421: imports `WsgiDAVApp`, `WSGIMiddleware`, `SemPKMDAVProvider`, `SemPKMWsgiAuthenticator`; config has `readonly=True`, `sempkm_db_url`; `app.mount("/dav", _asgi_dav_app)` |
| `docs/guide/23-vfs.md` | User guide with "Connect to Server" instructions | VERIFIED | 117 lines, covers token generation, macOS Finder "Connect to Server", Windows Map Network Drive, Linux Nautilus; file format section present |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/nginx.conf` | `http://api:8000/dav/` | `proxy_pass` in `/dav/` location block | WIRED | `location /dav/` with `proxy_pass http://api:8000/dav/` at line 77 |
| `backend/app/main.py` | `backend/app/vfs/provider.py` | `WsgiDAVApp` config references `SemPKMDAVProvider` | WIRED | `_dav_provider = SemPKMDAVProvider(...)`, passed into `provider_mapping: {"/": _dav_provider}` |
| `backend/app/vfs/auth.py` | `backend/app/auth/models.py` | Sync SQLAlchemy session verifying `token_hash` | WIRED | `from app.auth.models import ApiToken, User` inside `basic_auth_user()`; joins User, checks `ApiToken.token_hash` and `revoked_at.is_(None)` |
| `backend/app/vfs/collections.py` | `backend/app/triplestore/sync_client.py` | `SyncTriplestoreClient.query()` for SPARQL SELECT | WIRED | `from app.triplestore.sync_client import SyncTriplestoreClient`; all three collection classes call `self._client.query(...)` |
| `backend/app/vfs/collections.py` | `backend/app/vfs/cache.py` | `cached_get_member_names()` in `get_member_names()` | WIRED | `from app.vfs.cache import cached_get_member_names`; used in `RootCollection`, `ModelCollection`, `TypeCollection.get_member_names()` |
| `backend/app/vfs/resources.py` | `backend/app/vfs/collections.py` | `ResourceFile` reconstructs `TypeCollection` to get object metadata | WIRED | `from app.vfs.collections import TypeCollection` inside `_get_object_info()`; calls `tc.get_object_by_filename()` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VFS-01 | 26-01, 26-02, 26-03 | User can mount SemPKM objects as files via WebDAV (read-only) | SATISFIED (code-level) | Full stack: nginx proxy → wsgidav → `SemPKMDAVProvider` → collections → `ResourceFile`; all write methods raise `HTTP_FORBIDDEN`; `readonly=True` in config |
| VFS-02 | 26-01, 26-02, 26-03 | Object bodies rendered as Markdown files with SHACL-derived frontmatter | SATISFIED (code-level) | `ResourceFile._render()` builds YAML frontmatter with `type_iri`, `object_iri`, `label`, mapped predicates via `_PREDICATE_LABELS`; uses `python-frontmatter.dumps()` |

Both requirements have REQUIREMENTS.md status `[x]` (marked complete). VFS-03 is correctly out of scope for Phase 26 (assigned to Phase 27).

---

## Anti-Patterns Found

No TODO/FIXME/HACK/placeholder comments found in any VFS or auth files. No stub implementations detected. No empty return values. All required methods are fully implemented.

One notable variance (documented in SUMMARY, not a blocker):
- PUT returns HTTP 403 (Forbidden) instead of 405 (Method Not Allowed). This is because collection `create_empty_resource()` raises `HTTP_FORBIDDEN` before wsgidav's `readonly=True` config can intercept. User confirmed acceptable — writes are blocked either way.

---

## Human Verification Required

All automated checks passed. The following require a live Docker stack to confirm the system actually functions end-to-end.

### 1. WebDAV Directory Listing

**Test:** `curl -X PROPFIND http://localhost:3901/dav/ -u "email@example.com:<api-token>" -H "Depth: 1" -s`
**Expected:** HTTP 207 Multi-Status XML containing directory entries for installed models (e.g., `basic-pkm`)
**Why human:** Requires live Docker stack with valid ApiToken credential

### 2. Object File Content

**Test:** `curl "http://localhost:3901/dav/basic-pkm/Note/{slug}.md" -u "email@example.com:<api-token>" -s`
**Expected:** File beginning with `---` YAML frontmatter containing `type_iri`, `object_iri`, `label` fields, followed by optional Markdown body
**Why human:** Requires live triplestore with seed data

### 3. Read-Only Enforcement

**Test:** `curl -X PUT "http://localhost:3901/dav/basic-pkm/Note/test.md" -u "email@example.com:<api-token>" -d "test" -s -o /dev/null -w "%{http_code}"`
**Expected:** 403 (per SUMMARY — not 405 as originally planned; confirm 403 is acceptable)
**Why human:** Requires live wsgidav stack to exercise the write-rejection code path

### 4. Authentication Enforcement

**Test:** `curl -X PROPFIND http://localhost:3901/dav/ -H "Depth: 1" -s -o /dev/null -w "%{http_code}"`
**Expected:** 401 Unauthorized (not 404 or 200)
**Why human:** Requires live Docker stack

### 5. TTL Cache Behavior

**Test:** Send two PROPFIND requests within 30s, observe backend logs
**Expected:** Second request does not generate a SPARQL query to the triplestore
**Why human:** Requires log inspection on a live system to confirm cache hit

---

## Gaps Summary

No code-level gaps found. All artifacts are present, substantive, and wired. All 9 plan must-haves pass static analysis. All commit hashes (6044d92, c594c5b, 6b81083, 8713f37, 2c7a62d, d7903da, 83eb4f1, a9891ef, 6c3f72e) exist in git history.

The `human_needed` status reflects that the phase goal — "browsable by native OS file managers" — is an end-to-end behavior requiring a live stack. The code is complete and properly wired; human verification confirms the assembled system actually works as intended.

---

_Verified: 2026-03-01T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
