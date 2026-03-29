---
id: S01
parent: M045
milestone: M045
provides:
  - SSRF guard utility (backend/app/security/ssrf.py) reusable by any new outbound HTTP code path
  - Namespace filter utility (backend/app/federation/namespace_filter.py) for federation triple validation
  - Security audit events for model lifecycle (model_installed, model_uninstalled)
requires:
  []
affects:
  - S03
key_files:
  - backend/app/security/__init__.py
  - backend/app/security/ssrf.py
  - backend/app/federation/schemas.py
  - backend/app/federation/router.py
  - backend/app/federation/service.py
  - backend/app/federation/namespace_filter.py
  - backend/app/admin/router.py
  - backend/app/services/webhooks.py
  - backend/tests/test_ssrf_guard.py
  - backend/tests/test_federation_integrity.py
  - backend/tests/test_model_audit.py
key_decisions:
  - D372: Federation SHA-256 hash backward-compat — always include hash in exports, verify when present, warn when absent, never reject hashless patches
  - SSRF check order: loopback → link-local → multicast → private → reserved for most specific error category
  - Namespace filter applied to both inserts and deletes (not just inserts as originally planned)
  - OWL/SHACL blocked type list covers 9 class IRIs for comprehensive ontology injection prevention
  - Admin router uses local _client_ip + _security_audit helper pattern mirroring auth/router.py
patterns_established:
  - validate_outbound_url() in backend/app/security/ssrf.py — shared SSRF guard for any outbound HTTP call
  - filter_federation_triples() in backend/app/federation/namespace_filter.py — namespace allow/deny filtering for incoming RDF triples
  - _security_audit() fire-and-forget pattern in admin/router.py — mirrors auth/router.py pattern for audit logging without blocking the parent operation
observability_surfaces:
  - SSRF blocks logged at WARNING level with reason and blocked URL
  - Namespace-filtered triples logged at WARNING with count of rejected triples
  - Federation hash mismatch logged at ERROR
  - Missing federation hash logged at WARNING
  - Model install/uninstall events written to SecurityAuditLog table
drill_down_paths:
  - .gsd/milestones/M045/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M045/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M045/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-28T23:36:42.776Z
blocker_discovered: false
---

# S01: SSRF Guards, Federation Integrity & Audit Extension

**Closed SSRF vectors in all 4 outbound HTTP code paths, added SHA-256 integrity and namespace filtering to federation sync, and wired model install/uninstall security audit events — 50 tests prove all behaviors.**

## What Happened

Three tasks delivered three complementary security hardening layers:

**T01 — SSRF Guard (23 tests):** Created `backend/app/security/ssrf.py` with `validate_outbound_url()` that parses URLs, rejects non-http(s) schemes, checks hostnames against a blocked list (localhost, 0.0.0.0, ::1), resolves DNS, and validates all resolved IPs against loopback/link-local/multicast/private/reserved categories. Wired into all 4 outbound HTTP code paths: `FederationService.sync_shared_graph()`, `_post_to_inbox()`, `_discover_inbox_from_profile()`, and `WebhookService.dispatch()`. The federation sync router catches ValueError and returns HTTP 400. Check order is loopback → link-local → multicast → private → reserved for most specific error messages.

**T02 — Federation Integrity (17 tests):** Added optional `content_hash` field to `PatchExportResponse` (backward-compatible per D372). Export router computes SHA-256 of patch_text. `sync_shared_graph()` verifies hash if present (rejects on mismatch), logs WARNING if absent. Created `namespace_filter.py` with `filter_federation_triples()` that rejects triples in `urn:sempkm:*` (except `urn:sempkm:shared:*`), `owl:#`, `sh:#` namespaces, and `rdf:type` assertions for 9 OWL/SHACL class IRIs. Applied to both inserts AND deletes in sync (plan only mentioned inserts — deletes need filtering too to prevent malicious DELETE triples targeting system namespaces).

**T03 — Model Audit Events (10 tests):** Added `log_security_event` import and `_client_ip`/`_security_audit` helper functions to the admin router, mirroring the auth router pattern. Wired fire-and-forget audit calls into `admin_models_install()` and `admin_models_remove()` success paths. Audit failures cannot break model operations — all calls wrapped in try/except.

## Verification

All 50 slice tests pass: `cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py tests/test_federation_integrity.py tests/test_model_audit.py -v` → 50 passed in 1.22s. Verified all modified modules import cleanly. SSRF guard wired into 4 outbound paths (confirmed by grep). Namespace filter wired into sync service for both inserts and deletes. Security audit wired into admin router install and uninstall handlers.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01: Added bare ::1 to blocked hostnames (urlparse strips IPv6 brackets). Reordered IP checks for more specific error messages. Used globally-routable test IPs instead of RFC 5737 documentation ranges which Python 3.14 classifies as private. T02: Applied namespace filtering to both inserts AND deletes (plan only mentioned inserts). T03: None.

## Known Limitations

SSRF guard resolves DNS at validation time — a DNS rebinding attack could return a safe IP during validation and a private IP during the actual HTTP request. Mitigation would require pinning the resolved IP for the connection (httpx does not support this natively). Documented as acceptable risk for the current threat model.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/security/__init__.py` — New package init for security utilities
- `backend/app/security/ssrf.py` — SSRF validation utility — validate_outbound_url() resolves DNS and rejects loopback/private/reserved IPs
- `backend/app/federation/schemas.py` — Added optional content_hash field to PatchExportResponse
- `backend/app/federation/router.py` — Compute SHA-256 hash on federation export, HTTP 400 for SSRF-blocked URLs
- `backend/app/federation/service.py` — SSRF validation on 3 outbound paths, hash verification on import, namespace filtering on sync
- `backend/app/federation/namespace_filter.py` — New module — filter_federation_triples() rejects system-namespace triples
- `backend/app/admin/router.py` — Added _security_audit helper, wired model_installed and model_uninstalled audit events
- `backend/app/services/webhooks.py` — SSRF validation before webhook dispatch
- `backend/tests/test_ssrf_guard.py` — 23 tests for SSRF guard
- `backend/tests/test_federation_integrity.py` — 17 tests for federation integrity and namespace filtering
- `backend/tests/test_model_audit.py` — 10 tests for model audit events
