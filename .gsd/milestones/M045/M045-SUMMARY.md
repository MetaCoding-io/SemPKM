---
id: M045
title: "Security Hardening — OWASP Remediation"
status: complete
completed_at: 2026-03-29T00:33:56.425Z
key_decisions:
  - D372: Federation SHA-256 hash backward-compat — always include hash in exports, verify when present, warn when absent, never reject hashless patches. Allows gradual rollout across federation peers.
  - D373: Per-app JWT signing key derivation via HMAC-SHA256(platform_key, app_id) — deterministic, no extra storage. A compromised app token cannot forge tokens for other apps.
  - D374: Cloud compose overlay inherits security_opt/cap_drop from base — no duplication needed, compose merge handles it.
key_files:
  - backend/app/security/ssrf.py — SSRF validation utility for all outbound HTTP paths
  - backend/app/security/zip_validator.py — ZIP bomb protection via central directory inspection
  - backend/app/federation/namespace_filter.py — Namespace allow/deny filtering for incoming RDF triples
  - backend/app/federation/schemas.py — Added content_hash field to PatchExportResponse
  - backend/app/federation/service.py — SSRF validation, hash verification, namespace filtering on sync
  - backend/app/apps/tokens.py — Per-app JWT key derivation via HMAC-SHA256
  - backend/app/main.py — Weak SECRET_KEY startup rejection
  - backend/app/admin/router.py — Model install/uninstall security audit events
  - backend/Dockerfile — Non-root user (UID 1000), removed --reload from production CMD
  - docker-compose.yml — no-new-privileges and cap_drop on all services
  - Caddyfile.cloud — Cleaned CSP, added HSTS
  - docs/security-model.md — Comprehensive 44-finding disposition document
  - backend/tests/test_ssrf_guard.py — 23 SSRF tests
  - backend/tests/test_federation_integrity.py — 17 federation integrity tests
  - backend/tests/test_zip_validator.py — 16 ZIP validation tests
  - backend/tests/test_app_token_isolation.py — 12 token isolation and weak key tests
  - backend/tests/test_model_audit.py — 10 model audit event tests
lessons_learned:
  - SSRF DNS rebinding: validate_outbound_url() resolves DNS at validation time, but a DNS rebinding attack could return a safe IP then a private IP on the actual connection. httpx doesn't support IP pinning natively. Documented as acceptable risk — proper mitigation requires a custom transport that pins the resolved IP.
  - Namespace filtering must cover both inserts AND deletes in federation sync — the original plan only mentioned inserts, but malicious DELETE triples targeting system namespaces are equally dangerous.
  - Docker compose overlay files inherit security_opt/cap_drop from the base compose — adding duplicate directives causes validation errors. Only declare in the base file.
  - Central directory inspection (zipfile.infolist()) is the correct way to check ZIP contents without extraction — avoids decompression bombs while still detecting oversized payloads, excessive file counts, and suspicious compression ratios.
  - Per-app secret derivation via HMAC-SHA256(platform_key, app_id) eliminates the need for per-app key storage while ensuring token isolation — a compromised app's token is useless against other apps.
---

# M045: Security Hardening — OWASP Remediation

**Closed all 14 remaining M042 security audit findings — SSRF guards on all outbound HTTP paths, federation integrity (SHA-256 hash + namespace filtering), ZIP bomb protection, non-root Docker containers, per-app JWT isolation, weak key rejection, and HSTS/CSP hardening — bringing the total to 33/44 fixed with 218 security tests proving the full posture.**

## What Happened

M045 was the final security remediation milestone, picking up the 14 findings left open after M043 (SPARQL injection, auth hardening) and M044 (frontend namespace cleanup, Jinja2 computation removal). The work split across three slices executed sequentially.

**S01 — SSRF Guards, Federation Integrity & Audit Extension** tackled the highest-risk items. A new `backend/app/security/ssrf.py` module provides `validate_outbound_url()` which resolves DNS and rejects loopback, link-local, multicast, private, and reserved IP addresses. This was wired into all 4 outbound HTTP code paths: `FederationService.sync_shared_graph()`, `_post_to_inbox()`, `_discover_inbox_from_profile()`, and `WebhookService.dispatch()`. Federation integrity got two layers: SHA-256 content hashing on exports (backward-compatible per D372 — verify when present, warn when absent) and namespace filtering via `filter_federation_triples()` that blocks `urn:sempkm:*` (except shared namespace), OWL, and SHACL class IRIs from both inserts and deletes. Model install/uninstall events were wired into the security audit log following the existing `_security_audit()` fire-and-forget pattern. 50 tests cover all behaviors.

**S02 — Docker Hardening & Infrastructure Security** addressed container and startup security. The backend Dockerfile creates a `sempkm` user (UID 1000) with `USER sempkm` after all root-requiring build steps. All 6 docker-compose files got `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]` on every api and frontend service. A new `zip_validator.py` checks uncompressed size, file count, and compression ratio via central directory inspection before extraction — wired into both Obsidian and Notion importers. Weak SECRET_KEY values are rejected at startup in non-demo mode. Per-app JWT signing keys use HMAC-SHA256 derivation (D373) so a compromised app token can't forge tokens for other apps. Caddyfile.cloud lost three stale CDN domains from CSP and gained HSTS with 2-year max-age. 28 tests cover ZIP validation and token isolation.

**S03 — Regression Verification & Documentation** ran all 218 security tests (78 M045 + 140 M043) with zero failures, verified Docker hardening across all compose files, and expanded `docs/security-model.md` from 123 to ~400 lines with a complete 44-finding disposition table (33 fixed, 5 by design, 2 positive/no action, 4 open infrastructure items).

## Success Criteria Results

Success criteria are derived from the "After this" column for each slice in the roadmap, since no explicit success criteria section was present.

**S01 Criteria:**
- ✅ Federation sync endpoint rejects loopback/private URLs with 400 — `validate_outbound_url()` in `ssrf.py` wired into `federation/service.py`, router catches ValueError and returns HTTP 400. 23 unit tests prove rejection of loopback, private, link-local, multicast, and reserved IPs.
- ✅ Federation export includes SHA-256 hash — `content_hash` field added to `PatchExportResponse` in `schemas.py`, computed in `router.py`. 17 tests verify hash presence, verification, and mismatch rejection.
- ✅ Namespace-filtered import rejects system-namespace triples — `filter_federation_triples()` in `namespace_filter.py` blocks `urn:sempkm:*` (except shared), OWL, SHACL class IRIs. Applied to both inserts and deletes.
- ✅ Model install/uninstall events appear in SecurityAuditLog — `_security_audit()` helper in `admin/router.py` fires `model_installed` and `model_uninstalled` events. 10 tests confirm.

**S02 Criteria:**
- ✅ docker compose up starts with non-root containers — `USER sempkm` in Dockerfile, `no-new-privileges:true` and `cap_drop: [ALL]` in all 6 compose files.
- ✅ ZIP upload of oversized archive returns clear error — `validate_zip_contents()` in `zip_validator.py` checks size/count/ratio. Wired into Obsidian and Notion importers. 16 tests prove all rejection criteria.
- ✅ Startup refuses weak SECRET_KEY in non-demo mode — `_WEAK_KEYS` set in `main.py`, `SystemExit(1)` on match. 12 tests including demo-mode bypass.
- ✅ Caddyfile.cloud CSP has no stale CDN domains — grep confirms zero matches for unpkg.com, cdn.jsdelivr.net, cdnjs.cloudflare.com. HSTS header present with 2-year max-age.

**S03 Criteria:**
- ✅ All 218 security tests pass (78 M045 + 140 M043) — confirmed by running both batches with zero failures.
- ✅ security-model.md documents all 44 finding dispositions — 447 lines, 49 F-XXX references, disposition table with resolution status for all findings.
- ✅ Dependency scanning documented — pip-audit, npm audit, and Dependabot recommendations in security-model.md.

## Definition of Done Results

- ✅ All 3 slices marked complete ([x]) in M045-ROADMAP.md
- ✅ All 3 slice summaries exist (S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md)
- ✅ Source code committed to main — 35 non-screenshot files changed with 2129 insertions across 8 M045 commits
- ✅ 78 M045-specific tests pass (verified live: 78 passed in 1.54s)
- ✅ Cross-slice integration: S03 consumed S01 and S02 outputs correctly — ran all tests from both slices as regression, verified Docker hardening, and documented all findings
- ✅ No blocker discovered in any slice

## Requirement Outcomes

No formal requirements changed status during M045. The SEC-01 through SEC-05 requirements from M002 remain validated and were not affected by M045 work.

M045's scope was defined as audit finding remediation (F-001 through F-044 from M042's security audit) rather than tracked requirements. All 44 findings are now dispositioned: 33 fixed across M043/M044/M045, 5 by design, 2 positive/no action, 4 open infrastructure items (F-012 automated dependency scanning CI, F-018 rate limit tuning, F-023 CSP nonce adoption, F-039 CORS origin tightening).

## Deviations

S01/T01: Added bare ::1 to blocked hostnames (urlparse strips IPv6 brackets), reordered IP checks for more specific error messages, used globally-routable test IPs instead of RFC 5737 documentation ranges. S01/T02: Applied namespace filtering to both inserts AND deletes (plan only covered inserts). S02/T01: Cloud compose overlay inherits security directives from base compose instead of duplicating them (avoids validation errors). No other deviations.

## Follow-ups

Set up GitHub Actions CI with pip-audit and npm audit (covers F-012 automated dependency scanning). Configure Dependabot for automated PR-based dependency updates. Consider addressing the 4 remaining open findings (F-012, F-018, F-023, F-039) in a future infrastructure milestone. Consider CSP nonce adoption (F-023) to eliminate inline script allowances. Consider CORS origin tightening (F-039) for production deployments.
