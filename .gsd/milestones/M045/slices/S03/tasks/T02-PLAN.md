---
estimated_steps: 30
estimated_files: 1
skills_used: []
---

# T02: Rewrite security-model.md with complete 44-finding disposition and new security features

Update `docs/security-model.md` to serve as the comprehensive security reference for SemPKM, documenting all 44 M042 findings with their dispositions and all new security features added in M043-M045.

## Steps

1. Read the existing `docs/security-model.md` (123 lines) to understand current structure.
2. Read `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` to get all 44 finding IDs and descriptions.
3. Read S01 and S02 summaries (inlined in context) for details on M045 features.
4. Update existing sections:
   - Security Event Audit Trail: change model_installed/model_uninstalled from "(future)" to current — these are implemented in M045/S01
   - App Platform Trust Model: add per-app JWT key isolation (HMAC-SHA256 derivation)
   - Federation: add SSRF protection, SHA-256 hash integrity, namespace filtering
5. Add new sections:
   - **SSRF Protection**: `validate_outbound_url()` utility, 4 code paths protected (federation sync, inbox post, inbox discovery, webhook dispatch), DNS resolution + IP category checking
   - **Federation Integrity**: SHA-256 content hash on exports, verification on imports, namespace filtering (urn:sempkm:* except shared, OWL/SHACL class injection prevention)
   - **ZIP Upload Protection**: `validate_zip_contents()` checks (uncompressed size ≤2GB, file count ≤50k, compression ratio ≤100:1), wired into Obsidian and Notion importers
   - **Docker Hardening**: non-root UID 1000, no-new-privileges, cap_drop ALL, no --reload in production
   - **Weak Key Rejection**: startup guard rejects known weak SECRET_KEY values in non-demo mode
   - **Cloud Security Headers**: HSTS (2-year max-age, includeSubDomains, preload), CSP without stale CDN domains
6. Add **M042 Security Audit Findings Disposition** section with a table mapping all 44 F-XXX IDs to their resolution status (Fixed by M043/M044/M045, or By Design/Documented) with brief descriptions.
7. Add **Dependency Scanning** section documenting:
   - `pip-audit` for Python dependencies (install: `pip install pip-audit`, run: `pip-audit`)
   - `npm audit` for JavaScript dependencies (run from frontend/)
   - Recommendation for `.github/dependabot.yml` configuration
   - Note that no CI pipeline currently exists — these are manual commands
8. Verify the final document: all 44 F-XXX IDs present, all new M045 sections present, model audit events no longer marked "future".

## Must-Haves

- [ ] All 44 F-XXX finding IDs (F-001 through F-044) appear in the disposition table
- [ ] New sections for: SSRF Protection, Federation Integrity, ZIP Upload Protection, Docker Hardening, Weak Key Rejection, Cloud Security Headers
- [ ] Model install/uninstall audit events updated from future to current
- [ ] Dependency scanning documented with pip-audit and npm audit commands
- [ ] Per-app JWT isolation documented
- [ ] Document is well-structured markdown with no broken formatting

## Inputs

- ``docs/security-model.md` — existing 123-line security documentation to update`
- ``.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` — source of truth for all 44 findings with IDs, descriptions, and severities`
- ``.gsd/milestones/M045/slices/S01/S01-SUMMARY.md` — S01 completed work details (SSRF, federation integrity, model audit)`
- ``.gsd/milestones/M045/slices/S02/S02-SUMMARY.md` — S02 completed work details (Docker, ZIP, weak key, per-app JWT, CSP, HSTS)`

## Expected Output

- ``docs/security-model.md` — comprehensive security reference with all 44 finding dispositions, new feature sections, and dependency scanning docs`

## Verification

grep -c 'F-0' docs/security-model.md | xargs -I{} test {} -ge 44 && echo 'All 44 findings present' && grep -q 'SSRF' docs/security-model.md && grep -q 'ZIP' docs/security-model.md && grep -q 'pip-audit' docs/security-model.md && grep -q 'HMAC-SHA256' docs/security-model.md && grep -q 'no-new-privileges' docs/security-model.md && echo 'All sections verified'
