# S01: Injection, Access Control & Authentication Findings (A01, A03, A07)

**Goal:** Produce structured security findings for the three highest-risk OWASP categories — Injection (A03), Broken Access Control (A01), and Identification & Authentication Failures (A07) — with each finding severity-rated, mapped to affected files, and accompanied by exploit scenarios and remediation guidance.
**Demo:** `S01-FINDINGS.md` exists with per-category sections for A01, A03, A07; every finding has severity/OWASP/exploit/files/remediation; SPARQL injection modules individually classified as confirmed-exploitable, likely-exploitable, or safe.

## Must-Haves

- Every f-string SPARQL construction module (29 files) individually classified with data-flow reasoning
- Broken access control findings documenting any endpoint missing auth, any IDOR vector, CORS wildcard impact, and role enforcement gaps
- Authentication findings covering session lifecycle, cookie config, API token management, magic link flow, and rate limiting coverage
- Every finding has: OWASP category, severity (Critical/High/Medium/Low/Info), exploit scenario, affected files, remediation guidance
- Findings rated for cloud deployment with federation (most exposed model), with localhost mitigation notes where applicable

## Verification

- `test -f .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — file exists
- `grep -c "^### F-" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` returns >= 5 (at least 5 discrete findings)
- `grep -c "Severity:" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` matches finding count
- `grep -q "## A01" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — A01 section exists
- `grep -q "## A03" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — A03 section exists
- `grep -q "## A07" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — A07 section exists
- `grep -q "SPARQL Injection Classification" .gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — module classification table exists

## Tasks

- [x] **T01: SPARQL injection triage — classify all f-string SPARQL modules (A03)** `est:2h`
  - Why: SPARQL injection is the highest-risk injection vector in SemPKM. 29 modules use f-string SPARQL construction. Each needs data-flow analysis to determine if user-controlled input reaches the query string. This is the most time-intensive analysis in the slice.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/app/browser/objects.py`, `backend/app/browser/search.py`, `backend/app/browser/comments.py`, `backend/app/events/store.py`, `backend/app/events/query.py`, `backend/app/sparql/router.py`, `backend/app/sparql/query_service.py`, `backend/app/sparql/mirror.py`, `backend/app/sparql/client.py`, `backend/app/services/validation.py`, `backend/app/services/shapes.py`, `backend/app/services/models.py`, `backend/app/services/ops_log.py`, `backend/app/services/webhooks.py`, `backend/app/services/icons.py`, `backend/app/inference/service.py`, `backend/app/ontology/service.py`, `backend/app/rdf_import/executor.py`, `backend/app/admin/router.py`, `backend/app/models/registry.py`, `backend/app/vfs/strategies.py`, `backend/app/vfs/mount_router.py`, `backend/app/vfs/mount_collections.py`, `backend/app/browser/apps.py`, `backend/app/api/ai.py`, `backend/app/task_templates/service.py`, `backend/app/sparql/migrate_queries.py`, `backend/app/api/router.py`
  - Do: For each module, (1) find all f-string SPARQL constructions with `rg`, (2) trace each interpolated variable back to its origin — is it user HTTP input, internal IRI, config value, or system-generated? (3) classify as confirmed-exploitable (user input reaches f-string without sanitization), likely-exploitable (user input is 1-2 hops away), or safe (only internal/system values). (4) For confirmed/likely modules, write an exploit scenario showing how a crafted input could break out of the intended query. Also assess: Jinja2 template injection risk (autoescaping status), SQLAlchemy injection risk (ORM vs raw SQL), command injection via any shell/subprocess calls.
  - Verify: `grep -c "confirmed-exploitable\|likely-exploitable\|safe" .gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` returns >= 29 (one classification per module)
  - Done when: Every f-string SPARQL module is classified with reasoning, exploit scenarios written for exploitable paths, and non-SPARQL injection vectors (template, SQL, command) assessed

- [ ] **T02: Access control gaps + auth/session findings, assemble S01-FINDINGS.md (A01, A07)** `est:1h30m`
  - Why: A01 (Broken Access Control) and A07 (Auth Failures) cover the remaining two OWASP categories for this slice. Access control requires systematic scanning of every router for auth dependency presence and role enforcement. Auth requires reviewing session lifecycle, cookie settings, API token management, and rate limiting. This task also assembles the final S01-FINDINGS.md from its own analysis plus T01's SPARQL triage output.
  - Files: `backend/app/main.py`, `backend/app/auth/dependencies.py`, `backend/app/auth/router.py`, `backend/app/auth/models.py`, `backend/app/auth/service.py`, `backend/app/config.py`, `backend/app/auth/rate_limit.py`, `frontend/nginx.conf`, `backend/app/federation/inbox.py`, `backend/app/indieauth/router.py`, `backend/app/api/router.py`, `backend/app/sparql/router.py`, `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md`
  - Do: (1) Systematic auth scan: for every `include_router` in main.py, verify the router's endpoints have `Depends(get_current_user)` or `require_role`. Document any unprotected endpoint. (2) IDOR analysis: check if object access endpoints (objects, canvas, events, etc.) validate ownership or just require authentication. (3) CORS analysis: document the `Access-Control-Allow-Origin: *` configuration's interaction with session cookies and Bearer tokens. (4) Role enforcement: verify each role (owner/member/guest) has correct access boundaries, especially for SPARQL all_graphs, admin routes, federation. (5) Session lifecycle: review token generation entropy, expiry enforcement, concurrent session handling, revocation completeness. (6) Cookie security: document httponly/secure/samesite settings and any gaps. (7) API token management: review creation, hash storage, revocation, scope. (8) Rate limiting: check coverage beyond auth endpoints. (9) Assemble S01-FINDINGS.md incorporating T01's SPARQL triage results as the A03 section.
  - Verify: All S01-PLAN.md verification commands pass
  - Done when: S01-FINDINGS.md exists with A01/A03/A07 sections, every finding has severity/exploit/files/remediation, SPARQL triage table integrated, and findings rated for cloud deployment

## Files Likely Touched

- `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` (created — intermediate analysis)
- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md` (created — slice deliverable)
