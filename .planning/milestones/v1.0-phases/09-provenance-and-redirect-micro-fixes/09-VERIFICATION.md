---
phase: 09-provenance-and-redirect-micro-fixes
verified: 2026-02-23T06:00:00Z
status: passed
score: 2/2 must-haves verified
re_verification: false
---

# Phase 9: Provenance and Redirect Micro-Fixes Verification Report

**Phase Goal:** Close the 2 remaining low-severity integration gaps from the v1.0 re-audit: add performed_by_role to API command commit path and honor ?next= in invite acceptance redirect
**Verified:** 2026-02-23T06:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | API command endpoint records performed_by_role in event metadata alongside performed_by user IRI | VERIFIED | `backend/app/commands/router.py` line 124: `event_store.commit(operations, performed_by=user_iri, performed_by_role=user.role)` — kwarg present and passed to EventStore.commit() which accepts `performed_by_role: str | None = None` (store.py line 78) |
| 2 | Invite acceptance redirects to ?next= URL when present instead of always redirecting to / | VERIFIED | `frontend/static/js/auth.js` lines 309-313: handleInviteAccept success path reads `new URLSearchParams(window.location.search)`, calls `params.get("next")`, redirects to `nextUrl || "/"` — consistent with login (lines 168-172) and magic link verify (lines 235-239) paths |

**Score:** 2/2 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/commands/router.py` | API command endpoint with full user provenance (performed_by + performed_by_role) — contains `performed_by_role=user.role` | VERIFIED | File exists; line 124 contains `performed_by_role=user.role` in the `event_store.commit()` call; substantive implementation (full commit pipeline, not a stub) |
| `frontend/static/js/auth.js` | Invite acceptance with ?next= redirect support — contains `nextUrl` | VERIFIED | File exists; `nextUrl` appears at lines 170, 237, 311 (login, verify, invite paths); handleInviteAccept success path at lines 309-313 implements the full pattern |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/commands/router.py` | `backend/app/events/store.py` | `EventStore.commit()` call with `performed_by_role` kwarg | WIRED | Pattern `event_store.commit.*performed_by_role` matches at line 124; EventStore.commit() signature at store.py:74-79 accepts `performed_by_role: str | None = None` and records it as a triple at line 149 |
| `frontend/static/js/auth.js` | invite.html URL params | `URLSearchParams` reading `?next=` in `handleInviteAccept` | WIRED | Pattern `params.get.*next` matches at lines 170, 237, 311; invite path (line 310-312) reads `new URLSearchParams(window.location.search)` then `nextParams.get("next")` and redirects accordingly |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PROV-02-partial | 09-01-PLAN.md | API command write path omits performed_by_role in EventStore.commit() | SATISFIED | `commands/router.py` line 124 now passes `performed_by_role=user.role`; gap defined in v1.0-MILESTONE-AUDIT.md lines 14-20; browser/router.py also verified (lines 211, 527, 630) — no regression |
| AUTH-03-cosmetic | 09-01-PLAN.md | handleInviteAccept does not honor ?next= after invitation acceptance | SATISFIED | auth.js lines 309-313 implement ?next= reading in handleInviteAccept; confirmed already present from Phase 7 Plan 01 (commit 8af1e65); no code change needed in Phase 9 |

**Note on requirement ID source:** PROV-02-partial and AUTH-03-cosmetic are gap-closure IDs defined in `.planning/v1.0-MILESTONE-AUDIT.md` (lines 14-27), not in REQUIREMENTS.md. REQUIREMENTS.md covers the 32 canonical v1 requirements (CORE-*, SHCL-*, MODL-*, VIEW-*, OBJ-*, INFR-*, ADMN-*). These two IDs are sub-requirement audit items tracking partial satisfaction of integration contracts from Phase 7 scope. No orphaned requirements — REQUIREMENTS.md has no Phase 9 entries because Phase 9 closes audit gaps, not canonical requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO, FIXME, HACK, PLACEHOLDER, or stub patterns detected in either modified file. The commands/router.py change is additive (one kwarg added to an existing call); auth.js change was already correct from Phase 7.

---

### Human Verification Required

None. Both changes are:

1. A single kwarg addition to a server-side function call — verifiable by grep.
2. A ?next= URL parameter read and redirect — verifiable by reading the JavaScript.

No visual UI behavior, real-time flow, or external service dependency involved.

---

### Commit Verification

| Task | Commit | Status |
|------|--------|--------|
| Task 1: Add performed_by_role to API command EventStore.commit() | `a5bfae6` | VERIFIED — commit exists in git log with message `feat(09-01): add performed_by_role to API command EventStore.commit()` |
| Task 2: Verify invite acceptance ?next= redirect | No commit | EXPECTED — plan stated no code change needed; code already correct from commit `8af1e65` (Phase 7 Plan 01) |

---

### Consistency Check: All EventStore.commit() Write Paths

| File | Line(s) | performed_by | performed_by_role | Status |
|------|---------|--------------|-------------------|--------|
| `backend/app/browser/router.py` | 211, 527, 630 | user_iri | user.role | VERIFIED (pre-existing) |
| `backend/app/commands/router.py` | 124 | user_iri | user.role | VERIFIED (Phase 9 addition) |

All user-initiated write paths now pass full provenance. System-initiated writes (model auto-install) correctly omit both fields.

### Consistency Check: All auth success ?next= paths in auth.js

| Function | Lines | Pattern | Status |
|----------|-------|---------|--------|
| handleLoginForm | 168-172 | `params.get("next")` → `nextUrl \|\| "/"` | VERIFIED |
| handleVerifyToken | 235-239 | `nextParams.get("next")` → `nextUrl \|\| "/"` | VERIFIED |
| handleInviteAccept | 309-313 | `nextParams.get("next")` → `nextUrl \|\| "/"` | VERIFIED |

All three auth success paths are consistent.

---

## Summary

Phase 9 achieved its goal fully. Both micro-fixes are confirmed in the actual codebase:

1. **PROV-02-partial closed:** `backend/app/commands/router.py` line 124 now passes `performed_by_role=user.role` to `EventStore.commit()`, achieving parity with the browser write path. The change is wired end-to-end: the kwarg flows from the route handler to EventStore which records it as a triple in the event named graph.

2. **AUTH-03-cosmetic closed:** `frontend/static/js/auth.js` handleInviteAccept already contained the ?next= redirect pattern from Phase 7 Plan 01 (commit 8af1e65). Phase 9 Task 2 correctly followed the verification-only path — no code change was needed, and none was made.

All v1.0 milestone audit gap-closure work is complete. No anti-patterns, no stubs, no broken wiring.

---

_Verified: 2026-02-23T06:00:00Z_
_Verifier: Claude (gsd-verifier)_
