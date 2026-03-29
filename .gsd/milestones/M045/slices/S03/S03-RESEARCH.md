# S03 Research: Regression Verification & Documentation

## Summary

This is a low-risk verification and documentation slice. No new security code is written — the work is (1) confirming all M043+M044+M045 fixes hold via test runs, (2) updating `docs/security-model.md` with the complete 44-finding disposition, and (3) documenting dependency scanning. All patterns are established; this is straightforward execution.

## Recommendation

Three tasks: (T01) run the full unit test regression suite and fix any failures in M045-modified files, (T02) update `docs/security-model.md` with all 44 finding dispositions and the new security features, (T03) document dependency scanning and create a final audit checklist.

## Implementation Landscape

### Current Test Inventory

**M045-specific tests (78 tests across 5 files):**
- `tests/test_ssrf_guard.py` — 23 tests (SSRF URL validation)
- `tests/test_federation_integrity.py` — 17 tests (SHA-256 hash, namespace filtering)
- `tests/test_model_audit.py` — 10 tests (model install/uninstall audit events)
- `tests/test_zip_validator.py` — 16 tests (ZIP bomb protection)
- `tests/test_app_token_isolation.py` — 12 tests (per-app JWT, weak key rejection)

**M043-specific tests (relevant regression baseline):**
- `tests/test_sparql_injection_regression.py` — 18 tests (exact M042 audit payloads)
- `tests/test_sparql_builder.py` — 66 tests (safe_iri, escape, values_clause)
- `tests/test_magic_link_hardening.py` — single-use tokens
- `tests/test_token_scopes.py` — API token scope enforcement
- `tests/test_session_management.py` — session cap, revoke-all
- `tests/test_security_hardening.py` — rate limits, error disclosure, auth logging

**Full backend suite:** ~5,514 tests collected (2 collection errors in caldav_sync unrelated to M045).

**E2E suite:** 122 spec files across 20+ test directories. Runs against Docker test stack on port 3901.

### security-model.md — Current State

The file exists at `docs/security-model.md` (123 lines). It was created during M043/S04 and covers:
- Authorization architecture (roles, data ownership model)
- Authentication (magic links, API tokens)
- Security event audit trail (table of event types — but lists model_installed/uninstalled as "future")
- Rate limiting (table of endpoint limits)
- SPARQL security (defenses)
- Federation (brief)
- Secret management (brief)
- App platform trust model (brief)

**Missing from current security-model.md:**
- SSRF protection (new in M045/S01)
- Federation integrity (SHA-256 hash, namespace filtering — M045/S01)
- ZIP bomb protection (M045/S02)
- Docker hardening (non-root, no-new-privileges, cap_drop — M045/S02)
- Per-app JWT key isolation (M045/S02)
- Weak SECRET_KEY rejection (M045/S02)
- HSTS on cloud deployment (M045/S02)
- CSP stale CDN domain cleanup (M045/S02)
- Complete 44-finding disposition table referencing M042 findings
- Dependency scanning documentation
- Model install/uninstall audit events (currently "future" in doc but implemented in M045/S01)

### M042 Findings Disposition Map

All 44 findings have a clear disposition. The grouping:

| Category | Count | Disposition |
|----------|-------|-------------|
| Fixed by M043 | 20 | F-001, F-003, F-004, F-006–F-010, F-012, F-013, F-016, F-017, F-021, F-022, F-025, F-027, F-028, F-029 (partial), F-030, F-038 |
| Fixed by M044 | 3 | F-031, F-032, F-033 (CDN deps vendored) |
| Fixed by M045/S01 | 4 | F-029 (completion), F-036, F-037, F-043, F-044 |
| Fixed by M045/S02 | 7 | F-023, F-024, F-026, F-034 (documented), F-035, F-042, CSP stale, HSTS |
| By design / documented | 10 | F-002, F-005, F-011, F-014, F-015, F-018, F-019, F-020, F-039, F-040, F-041 |

### Dependency Scanning

No CI pipeline exists. No GitHub Actions workflows. No Dependabot config. The task is to document the commands and workflow:
- `pip-audit` (not currently installed in venv)
- `npm audit` (available via npm)
- GitHub Dependabot YAML config (`.github/dependabot.yml`)

Since there's no CI, the documentation should specify manual commands and recommend Dependabot setup.

### Docker Test Stack

`docker-compose.test.yml` already has M045 hardening (security_opt, cap_drop). E2E tests run against port 3901. The auth fixture uses a fixed secret key (`e2e-test-secret-key-do-not-use-in-production`) which is in the `_WEAK_KEYS` set but allowed because the test stack doesn't set `DEMO_MODE=false` without also setting a safe key — actually, the test compose sets `SECRET_KEY` directly and doesn't trigger the weak-key guard because the check only fires in non-demo mode. Need to verify this during T01.

## Key Files

| File | Role in S03 |
|------|-------------|
| `docs/security-model.md` | Primary deliverable — update with all 44 finding dispositions + new features |
| `backend/tests/test_sparql_injection_regression.py` | Run for regression verification |
| `backend/tests/test_ssrf_guard.py` | Run for M045/S01 verification |
| `backend/tests/test_federation_integrity.py` | Run for M045/S01 verification |
| `backend/tests/test_model_audit.py` | Run for M045/S01 verification |
| `backend/tests/test_zip_validator.py` | Run for M045/S02 verification |
| `backend/tests/test_app_token_isolation.py` | Run for M045/S02 verification |
| `backend/tests/test_security_hardening.py` | Run for M043 regression verification |
| `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` | Source of truth for all 44 findings |
| `backend/Dockerfile` | Verify non-root user, no --reload |
| `docker-compose.yml` | Verify security_opt, cap_drop |
| `Caddyfile.cloud` | Verify HSTS, clean CSP |

## Task Decomposition

### T01: Run Full Security Test Regression Suite (~30 min)
Run all security-related test files and the broader backend suite. Fix any failures in M045-modified files. Verify Docker hardening via grep checks on Dockerfiles and compose files.

**Verification:** All security test files pass. `pytest tests/test_sparql_injection_regression.py tests/test_sparql_builder.py tests/test_ssrf_guard.py tests/test_federation_integrity.py tests/test_model_audit.py tests/test_zip_validator.py tests/test_app_token_isolation.py tests/test_security_hardening.py -v` → all pass.

### T02: Update security-model.md with Complete Finding Dispositions (~45 min)
Rewrite `docs/security-model.md` to include:
1. All existing sections (updated where stale — e.g., audit events no longer "future")
2. New sections: SSRF Protection, Federation Integrity, ZIP Upload Protection, Docker Hardening, Per-App JWT Isolation
3. Complete 44-finding disposition table mapping each F-XXX to its resolution
4. Dependency scanning documentation (pip-audit commands, npm audit, Dependabot recommendation)

**Files modified:** `docs/security-model.md`

**Verification:** All 44 F-XXX IDs appear in the document. New sections cover all M045 features. `wc -l docs/security-model.md` shows significant growth from current 123 lines.

### T03: Final Audit Checklist & Dependency Scanning Docs (~20 min)
Create a verification checklist covering all 44 findings with pass/fail status. Document dependency scanning commands. Verify PostHog CSP requirements are documented.

**Files modified:** `docs/security-model.md` (dependency scanning section), possibly a separate `docs/security-audit-checklist.md` if the disposition table in T02 doesn't serve this purpose.

**Verification:** A checklist or table exists showing all 44 findings with clear status (fixed/by-design/documented).

## Constraints

- No new security code — this is verification and documentation only.
- E2E suite requires Docker test stack running. If the stack can't be started (resource/time constraint), unit test regression is sufficient evidence — M043's lesson learned noted that per-slice unit tests adequately cover regression concerns.
- The 2 collection errors in `test_caldav_sync_engine.py` are pre-existing and unrelated to M045.

## Risks

None significant. This is documentation and test execution against already-implemented code. The only minor risk is discovering a test failure that indicates a regression — but with 78 M045-specific tests already passing at slice completion, this is unlikely.
