# S03 Research: Design, Crypto, SSRF & Final Report Assembly

**Slice:** S03 — Design, Crypto, SSRF & Final Report Assembly (A02, A04, A10 + Top 10)
**Milestone:** M042 — Security Audit
**Depth:** Targeted — known codebase, remaining three OWASP categories are well-scoped, plus mechanical assembly of the final report from S01+S02 artifacts.

## Summary

S03 completes the OWASP Top 10 coverage by analyzing the three remaining categories — A02 (Cryptographic Failures), A04 (Insecure Design), A10 (Server-Side Request Forgery) — and then assembles the complete `M042-SECURITY-FINDINGS.md` report from S01 + S02 findings plus these new findings, capped with a prioritized Top 10 summary.

The research identifies **6 new findings** across A02/A04/A10. Combined with S01's 20 and S02's 17, the final report will contain **~43 findings** spanning all 10 OWASP categories.

## A02: Cryptographic Failures — Analysis

### What's Good (Not Findings)

- **API token hashing:** SHA-256 hash stored, plaintext never persisted (`auth/service.py`)
- **Session token entropy:** 256-bit via `secrets.token_urlsafe(32)` — adequate
- **Fernet encryption for secrets:** Both LLM API keys (`services/llm.py`) and WebID private keys (`webid/service.py`) use Fernet with PBKDF2HMAC key derivation, SHA-256, 100,000 iterations — good
- **Ed25519 for federation signatures:** Modern curve, adequate key length (`webid/service.py`)
- **PKCE S256 in IndieAuth:** Proper RFC 7636 implementation (`indieauth/service.py`)
- **Magic link tokens:** itsdangerous URLSafeTimedSerializer with salt separation ("magic-link" vs "invitation") — adequate
- **Secret key auto-generation:** `secrets.token_urlsafe(64)` — 512-bit entropy — excellent

### Findings

**F-038: Secret Key File Written Without Restrictive Permissions**
- `auth/tokens.py` `_get_secret_key()` auto-generates `data/.secret-key` via `key_path.write_text(key)` with no `os.chmod()` call. File inherits umask-default permissions (typically 0o644 — world-readable). This file is the root of all Fernet encryption and token signing.
- Severity: Medium (cloud), Low (single-user Docker)
- Affected: `backend/app/auth/tokens.py` lines 33-39
- Same applies to setup token file at `data/.setup-token`

**F-039: No Key Rotation Mechanism for Fernet Encryption Keys**
- The secret key is generated once and never rotated. PBKDF2 salts are hardcoded strings (`sempkm-llm-config-v1`, `sempkm-webid-keys-v1`). If the secret key is compromised, all encrypted LLM API keys and WebID private keys are immediately recoverable with no ability to rotate without re-encrypting all stored secrets.
- Severity: Low (acceptable for current scale)
- Affected: `backend/app/services/llm.py`, `backend/app/webid/service.py`, `backend/app/auth/tokens.py`

**F-040: Cookie `secure` Flag Defaults to True but Deployment Docs Instruct `COOKIE_SECURE=false`**
- `config.py` defaults `cookie_secure: bool = True`. However, the deployment documentation and docker-compose files for local dev set `COOKIE_SECURE=false` for HTTP. This is correct behavior (secure cookies don't work over HTTP), but there's no runtime warning when `secure=False` is used with a non-localhost base URL, meaning a cloud deployment could accidentally run with insecure cookies.
- Severity: Info (informational — the code default is correct)
- Affected: `backend/app/config.py:56`, `backend/app/auth/router.py:52`

### A02 Summary
The cryptographic posture is solid. Token entropy, hashing, encryption, and key derivation all use appropriate algorithms and parameters. The main gaps are operational: file permissions on the secret key and no rotation mechanism. No critical or high findings.

## A04: Insecure Design — Analysis

### App Platform Subprocess Isolation

The app platform runs third-party (user-installed) Python applications as **unsandboxed subprocesses** via `asyncio.create_subprocess_exec()` in `apps/manager.py`:

- Apps run with the **same OS user and filesystem access** as the main backend process
- No seccomp, AppArmor, namespace isolation, capability dropping, or chroot
- Apps communicate via Unix domain sockets (`/tmp/sempkm-app-{app_id}.sock`)
- The SDK provides `HttpClient` with domain enforcement (`allowed_domains` via fnmatch), but this is **advisory** — an app can import `httpx` directly and bypass the SDK
- App JWT tokens use the platform's main secret key for HS256 signing — a compromised app can forge tokens for other apps

This is by design for the current "install from local disk" model where the user trusts the app code. It becomes a vulnerability if a future app marketplace allows installing untrusted code.

### Demo Mode Design

`DEMO_MODE=true` bypasses all authentication, returning a synthetic guest user with "member" role for every request. This is gated by an env var only. Findings:
- The synthetic user has `role="member"` — can read all data but can't access `require_role("owner")` endpoints (admin, model install, debug). This is correct.
- Demo nginx config (`nginx.demo.conf`) blocks mutation HTTP methods (POST/PUT/DELETE/PATCH) at the reverse proxy level — defense in depth.
- No finding needed beyond F-019 (already documented in S01).

### Federation Trust Model

Federation accepts RDF patches from remote instances with HTTP Signature verification but no content-level validation. Already covered in S02 as F-036 and F-037.

### Findings

**F-041: App Platform Subprocesses Run Without OS-Level Isolation**
- App subprocesses share the backend's full OS context: filesystem, network, process space. The SDK's `HttpClient` domain restriction is advisory (Python apps can bypass it). An app can read the secret key file (`data/.secret-key`), access the SQLite database, read environment variables, and make arbitrary network requests.
- Severity: Medium (current model: trusted local installs), High (if marketplace model added)
- Affected: `backend/app/apps/manager.py` (lines 204-210), `backend/sdk/sempkm_app_sdk/clients/http.py`

**F-042: App JWT Tokens Share Platform Secret — Cross-App Forgery Possible**
- All app tokens are signed with the same `get_secret()` key. An app that extracts the secret key (F-041 makes this trivial) can forge valid JWT tokens for any other app, impersonating the platform itself.
- Severity: Medium (coupled with F-041)
- Affected: `backend/app/apps/tokens.py`

### A04 Summary
The app platform is the primary insecure design finding. The design is rational for the current trust model (owner installs apps from local disk) but lacks defense-in-depth. The federation trust model gaps are already documented in S02.

## A10: Server-Side Request Forgery (SSRF) — Analysis

### Outbound HTTP Inventory

The backend makes outbound HTTP requests from these paths:

| Module | URL Source | SSRF Risk | Mitigation |
|--------|-----------|-----------|------------|
| `federation/service.py` | `remote_instance_url` from user JSON body or auto-discovered from shared graph members | **High** — user-controlled URL | None — no allowlist, no IP block |
| `indieauth/service.py` `fetch_client_info()` | `client_id` URL from OAuth flow | **Medium** — user-controlled | ✅ Loopback IP check via `ipaddress.is_loopback` |
| `browser/settings.py` `/llm/test`, `/llm/models`, `/llm/chat/stream` | `api_base_url` from InstanceConfig (owner-configured) | **Low** — owner-only config | Owner-only endpoints (`require_role("owner")`) |
| `services/webhooks.py` `dispatch()` | `target_url` from RDF config (owner-configured) | **Low** — owner-only config | No IP validation, but owner-configurable |
| `services/prefixes.py` `import_lov_prefixes()` | Hardcoded LOV API URL | **None** — not user-controlled | Fixed URL |
| `apps/proxy.py` | UDS only (no network) | **None** | Unix domain socket, no TCP |
| `triplestore/client.py` | Internal triplestore URL from config | **None** — not user-controlled | Config-only |
| `sparql/client.py` | Blocks `SERVICE` clauses for member role | **Mitigated** | Explicit clause blocking |
| `sparql/mirror_router.py` | `endpoint_url` from request body | **Mitigated** — owner-only + allowlist | Endpoint allowlist + owner role |
| SDK `HttpClient` | App-controlled URLs | **Mitigated** — domain allowlist in SDK | fnmatch domain enforcement |

### Findings

**F-043: Federation Sync Endpoint Allows Arbitrary Outbound HTTP Requests (SSRF)**
- `POST /federation/{graph_id}/sync` accepts `remote_instance_url` from the JSON request body. This URL is passed directly to `httpx.AsyncClient.get()` in `federation/service.py` line 658 with no validation: no IP blocklist, no scheme restriction, no internal network guard. An authenticated user can make the server fetch any URL, including internal services (169.254.169.254 metadata, localhost services, internal Docker network).
- IndieAuth has an SSRF guard (`ipaddress.is_loopback` check) but federation does not.
- Severity: High (cloud deployment)
- Affected: `backend/app/federation/router.py:230`, `backend/app/federation/service.py:658`

**F-044: Webhook Dispatch Sends POST to Owner-Configured URLs Without IP Validation**
- Webhook `target_url` is stored in the triplestore by an owner. The `dispatch()` method sends HTTP POST to this URL with no IP blocklist check. While owner-only configuration mitigates the risk (the owner would be attacking their own instance), in a multi-user scenario, an owner could configure webhooks to probe internal networks.
- Severity: Low (owner-only config)
- Affected: `backend/app/services/webhooks.py` dispatch method

### A10 Summary
The main SSRF finding is the federation sync endpoint (F-043), which accepts arbitrary URLs from authenticated users with no validation. The IndieAuth service has proper SSRF guards that should be used as a pattern. Other outbound HTTP paths are either owner-only configured or use fixed URLs.

## Report Assembly Plan

### Structure of M042-SECURITY-FINDINGS.md

The final report combines S01 + S02 + S03 findings into a single document:

1. **Executive Summary** — total findings by severity, coverage statement
2. **OWASP Top 10 Coverage** — one section per category (A01–A10), each containing:
   - Category description
   - Findings for that category (incorporated verbatim from S01/S02/S03)
   - Category assessment (reviewed + specific findings, or reviewed + no findings)
3. **Backend Hardening Assessment** — cross-cutting areas:
   - Secret management (draws from F-038, F-039)
   - Session lifecycle (draws from F-012, F-013, F-015)
   - API token management (draws from F-016)
   - Debug/shell endpoint exposure (references S01 auth scan)
   - Federation auth (draws from F-020, F-036, F-037, F-043)
   - File upload handling (draws from F-027, F-035)
4. **Infrastructure Security Assessment** — cross-cutting:
   - nginx configuration (F-021, F-022)
   - Docker security (F-023, F-024)
   - Deployment hardening (F-026)
5. **SPARQL Injection Classification Summary** — the 33-module table from S01
6. **Prioritized Top 10 Findings** — the 10 highest-severity findings with effort estimates
7. **Appendix: CDN Dependency Inventory** — the detailed table from S02

### Finding Number Assignment

- S01: F-001 through F-020 (A01, A03, A07)
- S02: F-021 through F-037 (A05, A06, A08, A09)
- S03: F-038 through F-044 (A02, A04, A10)
- Total: 44 findings

### Top 10 Prioritization — Candidates

Ranking by severity (cloud deployment baseline) × exploitability × blast radius:

| Rank | Finding | Severity | Category | Effort |
|------|---------|----------|----------|--------|
| 1 | F-021: Zero HTTP security headers | High | A05 | 1-2h (nginx config) |
| 2 | F-006: SPARQL injection via views `type` param | High | A03 | 2-4h (add _validate_iri) |
| 3 | F-007: SPARQL injection via apps `iri` param | High | A03 | 1-2h (add _validate_iri) |
| 4 | F-008: SPARQL write injection via VFS mount | High | A03 | 2-3h (add _validate_iri) |
| 5 | F-043: Federation SSRF — arbitrary outbound HTTP | High | A10 | 2-4h (IP blocklist + scheme validation) |
| 6 | F-031: Zero SRI on all CDN dependencies | High | A06 | 4-8h (compute + add hashes to all templates) |
| 7 | F-028: Magic link tokens logged in plaintext | High | A09 | 30min (mask in log output) |
| 8 | F-029: No security event audit trail | High | A09 | 4-8h (add security event logger) |
| 9 | F-032: Unpinned CDN dependencies (incl. DOMPurify) | High | A06 | 1-2h (pin versions) |
| 10 | F-001: Missing auth on 6 browser app endpoints | Medium | A01 | 30min (add Depends) |

### Severity Distribution (All 44 Findings)

| Severity | Count |
|----------|-------|
| High | 8 (F-006, F-007, F-008, F-021, F-028, F-029, F-031, F-032) + 1 new (F-043) = 9 |
| Medium | ~14 |
| Low | ~13 |
| Info | ~8 |

## Recommendation

### Task Decomposition

This slice has two distinct work items:

**T01: A02, A04, A10 Findings Document** — Write findings F-038 through F-044 in the same format as S01/S02 findings. Short task — 6 findings, all research is complete above. Write to a working file or directly into the final report.

**T02: Final Report Assembly (M042-SECURITY-FINDINGS.md)** — Assemble the complete report:
1. Write the executive summary and structural framing
2. Copy/integrate S01-FINDINGS.md sections (A01, A03, A07) verbatim
3. Copy/integrate S02-FINDINGS.md sections (A05, A06, A08, A09) verbatim
4. Add A02, A04, A10 sections from T01 findings
5. Write backend hardening and infrastructure security cross-cutting sections
6. Copy the SPARQL injection classification table from S01
7. Write the prioritized Top 10 summary with effort estimates
8. Add CDN dependency inventory as appendix from S02
9. Verify all 10 OWASP categories present, all findings have required fields

These could be a single task (T01) since T02 is pure mechanical assembly, or two tasks if the planner wants to separate analysis from assembly for clearer verification gates.

## Implementation Landscape

### Input Artifacts
- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — 578 lines, 20 findings (A01, A03, A07)
- `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` — 778 lines, 17 findings (A05, A06, A08, A09)
- S01 SPARQL injection triage: `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md`

### Output Artifact
- `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` — the milestone's sole deliverable

### Key Constraints
- **No source code modifications** — this is analysis-only
- **Finding format standardization** — every finding must have: severity, OWASP category, affected files, exploit scenario, remediation guidance, localhost mitigation note
- **Severity baseline** — cloud deployment with federation (same as S01/S02)
- The report must be self-contained — a reader should not need to reference S01/S02 documents

### Verification Commands (from roadmap)
```bash
test -f .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -c "## A0" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md  # should be 10
grep -q "A01" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A02" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A03" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A04" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A05" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A06" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A07" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A08" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A09" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "A10" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "Top 10" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -c "^### F-" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md  # should be ~44
grep -c "Severity:" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md  # should match finding count
```
