# S01: Injection, Access Control & Authentication Findings — UAT

**Milestone:** M042
**Written:** 2026-03-23

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This is a static analysis slice — no code was modified and no runtime behavior changed. Verification is against the produced findings document, not against a running system.

## Preconditions

- `S01-FINDINGS.md` exists at `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`
- `T01-SPARQL-TRIAGE.md` exists at `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md`
- No source code files were modified by this slice

## Smoke Test

Open `S01-FINDINGS.md` and confirm it has three major sections (`## A01`, `## A03`, `## A07`) with numbered findings (F-001 through F-020) and a summary table at the bottom.

## Test Cases

### 1. SPARQL Injection Classification Completeness

1. Open `T01-SPARQL-TRIAGE.md`
2. Count all modules listed in the classification table
3. Cross-reference against `rg "f\".*SELECT|f\".*INSERT|f\".*<\{" backend/app/ -l` output
4. **Expected:** Every module that constructs SPARQL via f-strings appears in the table with a classification (confirmed-exploitable, likely-exploitable, or safe) and reasoning

### 2. Confirmed-Exploitable Findings Have Exploit Scenarios

1. Open `S01-FINDINGS.md`
2. Locate F-006 (views type param), F-007 (apps iri param), F-008 (VFS mount write injection)
3. **Expected:** Each has a concrete "Exploit Scenario" section showing the exact HTTP request or payload that would trigger the injection, with the resulting SPARQL query fragment

### 3. Access Control Finding Accuracy

1. Open `backend/app/browser/apps.py`
2. Check each of the 6 endpoints listed in F-001 (`apps_explorer`, `app_page`, `right_pane_sections`, `views_explorer_apps`, `app_view_tab`, `commands_list`)
3. **Expected:** None of these endpoint function signatures include `Depends(get_current_user)` or equivalent auth dependency. The two endpoints listed as OK (`catalog`, `catalog/{app_id}`) DO have auth.

### 4. Auth/Session Findings Match Codebase

1. Open `backend/app/auth/tokens.py` — verify magic link tokens have no server-side revocation (F-012)
2. Open `backend/app/auth/service.py` — verify `create_session()` has no concurrent session limit (F-013), token uses `secrets.token_urlsafe(32)` (F-014)
3. Open `backend/app/auth/router.py` — verify cookie flags match F-015 (httponly=True, samesite="lax", secure=settings.cookie_secure)
4. Open `backend/app/auth/dependencies.py` — verify API tokens return full User with no scope check (F-016)
5. **Expected:** Each finding's description matches what is actually in the code

### 5. Rate Limiting Coverage Map

1. Run `rg "limiter\." backend/app/ -l` to find all files with rate limiting decorators
2. **Expected:** Only `backend/app/auth/router.py` has rate limiting (on magic-link and verify endpoints), matching F-017's claim that SPARQL, copilot, commands, and token creation have no limits

### 6. Non-SPARQL Injection Assessment

1. Run `rg "shell=True" backend/app/` — should return zero matches
2. Run `rg "\.execute\(f\"" backend/app/` — should return zero matches (no raw SQL f-strings)
3. Run `rg "\|safe" backend/app/templates/ -l` — should return zero matches (no Jinja2 safe filter)
4. **Expected:** All three return zero results, confirming T01's non-SPARQL injection "safe" assessment

### 7. Finding Format Completeness

1. For each of the 20 findings (F-001 through F-020), verify presence of:
   - **Severity:** line
   - **OWASP Category:** line
   - **Affected Files:** line
   - Either **Exploit Scenario** section or **Assessment** section
   - **Remediation:** section
2. **Expected:** All 20 findings have all required fields. Info-level positive findings (F-014, F-019, F-020) may use "Assessment" instead of "Exploit Scenario"

### 8. CORS Analysis Accuracy

1. Open `frontend/nginx.conf` — verify `add_header Access-Control-Allow-Origin "*" always` on `/api/` responses (F-003)
2. Open `backend/app/main.py` — verify CORS middleware defaults to `allow_origins=["*"]` when `CORS_ORIGINS` is empty
3. **Expected:** Both add `*` — F-003's claim about header duplication is correct

## Edge Cases

### Setup Endpoint Window

1. Read `backend/app/api/setup_routes.py`
2. Confirm `POST /api/setup/configure-instance` has no auth dependency
3. Confirm the only guard is `_check_user_data_exists()` returning 409 after data exists
4. **Expected:** F-004 correctly identifies the first-run window vulnerability and its mitigation

### CORS + Bearer Token Interaction

1. Review F-003's claim that `Access-Control-Allow-Origin: *` does NOT enable `credentials: include` in fetch
2. Verify per CORS spec: when `Access-Control-Allow-Origin` is `*`, `credentials: include` is rejected by the browser
3. **Expected:** F-003 correctly states session cookies are protected by SameSite=Lax, and only Bearer tokens are usable cross-origin

### Demo Mode Guest Access

1. Open `backend/app/auth/dependencies.py`
2. Verify `get_current_user` returns synthetic guest when `settings.demo_mode` is True
3. Verify guest UUID is `00000000-0000-0000-0000-000000000000`
4. **Expected:** F-019 correctly describes the demo mode behavior and residual risk

## Failure Signals

- Any finding whose "Affected Files" reference doesn't exist in the codebase — indicates stale analysis
- Any confirmed-exploitable SPARQL module that actually uses `_validate_iri()` — indicates incorrect classification
- Any "safe" module that actually has unvalidated user input in f-string SPARQL — indicates missed vulnerability
- Severity counts in the summary table not matching the actual findings — indicates assembly error

## Requirements Proved By This UAT

- SEC-01 through SEC-05 are re-assessed (gaps identified in SPARQL validation, rate limiting, cookie config docs)

## Not Proven By This UAT

- No remediation was applied — fixes will be a future milestone scoped from the complete M042 report
- No dynamic/runtime testing was performed — findings are based on static code analysis
- SPARQL injection exploitability is assessed by code reading, not by actually executing the crafted payloads against a running instance

## Notes for Tester

- The findings are severity-rated for **cloud deployment with federation enabled** (the most exposed model). Most findings are non-issues for localhost-only instances — the "Localhost Mitigation" notes on each finding document this.
- The SPARQL injection classification in T01-SPARQL-TRIAGE.md has more detailed per-module analysis than the summary in S01-FINDINGS.md. Consult T01 for full data-flow traces.
- F-011 (user-submitted SPARQL via `/api/sparql`) is classified as "confirmed-exploitable (by design)" — this is intentional, not a bug. The SPARQL console is a user-facing feature. The residual risks (DoS via expensive queries, no result size limits) are documented.
