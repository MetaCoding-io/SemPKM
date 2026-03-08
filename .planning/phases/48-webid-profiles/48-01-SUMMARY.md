---
phase: 48-webid-profiles
plan: 01
subsystem: auth
tags: [webid, ed25519, cryptography, fernet, rdf, foaf, settings]

requires:
  - phase: none
    provides: n/a
provides:
  - WebID data model (5 new User columns via migration 005)
  - Ed25519 key generation and Fernet-encrypted storage
  - RDF profile graph builder (FOAF + W3C Security Vocabulary)
  - 6 API endpoints for WebID profile management
  - Settings UI for username claim, key management, link editing, publish toggle
affects: [48-02-public-profile, 49-indieauth]

tech-stack:
  added: [ed25519, w3c-security-vocabulary]
  patterns: [webid-uri-format, fernet-key-encryption-per-domain]

key-files:
  created:
    - backend/migrations/versions/005_webid_columns.py
    - backend/app/webid/__init__.py
    - backend/app/webid/service.py
    - backend/app/webid/schemas.py
    - backend/app/webid/router.py
    - backend/app/templates/browser/_webid_settings.html
  modified:
    - backend/app/auth/models.py
    - backend/app/main.py
    - backend/app/templates/browser/settings_page.html

key-decisions:
  - "Used separate KDF salt (sempkm-webid-keys-v1) from LLM encryption to isolate key derivation domains"
  - "Username immutable after creation -- enforced at API level with 400 error"
  - "Profile links stored as JSON string in Text column (not separate table)"

patterns-established:
  - "WebID URI format: {base_url}/users/{username}#me"
  - "Key node URI format: {webid_uri}-key"
  - "Fernet domain isolation: each encrypted-at-rest feature uses its own KDF salt"

requirements-completed: [WBID-01, WBID-05]

duration: 3min
completed: 2026-03-08
---

# Phase 48 Plan 01: WebID Data Model & Settings Summary

**Ed25519 key pair generation with Fernet-encrypted storage, RDF profile graph builder, 6 API endpoints, and Settings UI for WebID profile management**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T05:30:54Z
- **Completed:** 2026-03-08T05:34:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Alembic migration 005 adds 5 WebID columns to users table (username, public_key_pem, private_key_encrypted, webid_links, webid_published)
- WebID service generates Ed25519 key pairs, encrypts private keys with Fernet, computes SHA-256 fingerprints, and builds FOAF+Security RDF graphs
- 6 API endpoints handle profile retrieval, username claim, link management, publish/unpublish, and key regeneration
- Settings page has WebID Profile category with full UI for username setup, key display, link editing, and publish toggle

## Task Commits

Each task was committed atomically:

1. **Task 1: Database migration, User model columns, and WebID service** - `24ffff4` (feat)
2. **Task 2: Settings API endpoints and Settings UI partial** - `fb42c0e` (feat)

## Files Created/Modified
- `backend/migrations/versions/005_webid_columns.py` - Adds username, public_key_pem, private_key_encrypted, webid_links, webid_published to users table
- `backend/app/auth/models.py` - Extended User model with 5 WebID columns
- `backend/app/webid/__init__.py` - Module init
- `backend/app/webid/service.py` - Key generation, encryption, fingerprint, RDF graph builder
- `backend/app/webid/schemas.py` - Pydantic schemas for username validation and link management
- `backend/app/webid/router.py` - 6 API endpoints for WebID profile management
- `backend/app/main.py` - Registered webid_router
- `backend/app/templates/browser/_webid_settings.html` - WebID settings UI partial
- `backend/app/templates/browser/settings_page.html` - Added WebID Profile category

## Decisions Made
- Used separate KDF salt (`sempkm-webid-keys-v1`) from LLM encryption to isolate key derivation domains
- Username immutable after creation -- enforced at API level with 400 error
- Profile links stored as JSON string in Text column (not separate table) for simplicity
- Key fingerprint format: SHA-256 of DER bytes, colon-separated hex

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data model and service layer ready for Plan 02 (public profile endpoint with content negotiation)
- `build_profile_graph()` produces the RDF graph that Plan 02 will serialize to Turtle/JSON-LD
- Username and publishing state stored in SQL, ready for public profile resolution

## Self-Check: PASSED

All 9 files verified present. Both task commits (24ffff4, fb42c0e) verified in git log.

---
*Phase: 48-webid-profiles*
*Completed: 2026-03-08*
