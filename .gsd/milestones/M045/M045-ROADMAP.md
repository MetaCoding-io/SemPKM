# M045: 

## Vision
Remediate all remaining M042 security audit findings — closing SSRF vectors, hardening Docker containers, adding federation integrity verification, extending audit logging, and protecting ZIP imports. M043 and M044 already resolved ~30 of 44 original findings; this milestone covers the remaining 14.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | SSRF Guards, Federation Integrity & Audit Extension | high | — | ✅ | Federation sync endpoint rejects loopback/private URLs with 400. Federation export includes SHA-256 hash. Namespace-filtered import rejects system-namespace triples. Model install/uninstall events appear in SecurityAuditLog. |
| S02 | Docker Hardening & Infrastructure Security | medium | — | ⬜ | docker compose up starts with non-root containers. ZIP upload of oversized archive returns clear error. Startup refuses weak SECRET_KEY in non-demo mode. Caddyfile.cloud CSP has no stale CDN domains. |
| S03 | Regression Verification & Documentation | low | S01, S02 | ⬜ | E2E test suite passes against hardened stack. security-model.md documents all 44 finding dispositions. Dependency scanning documented. |
