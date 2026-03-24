# S02 UAT: Configuration, Infrastructure & Supply Chain Findings

**Milestone:** M042
**Slice:** S02

## Preconditions

- `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` exists
- No source code was modified by this slice (analysis-only)

## Test Cases

### 1. A05 Security Misconfiguration Coverage

1. Open `S02-FINDINGS.md` and locate the `## A05:` section.
2. Verify findings F-021 through F-027 exist (7 findings).
3. For F-021 (missing headers): cross-reference `frontend/nginx.conf` — confirm no `add_header X-Frame-Options`, `add_header Content-Security-Policy`, or `add_header Strict-Transport-Security` directives exist.
4. For F-022 (CORS double-header): confirm `nginx.conf` lines 74/96/116/122 add `Access-Control-Allow-Origin: *` AND `backend/app/main.py` lines 633–649 configure CORSMiddleware.
5. For F-025 (error disclosure): spot-check one of the listed files — e.g. `grep 'detail=str(e)' backend/app/auth/router.py` should return a match.
6. **Expected:** All 7 findings reference real file paths with accurate line numbers. Each finding has severity, exploit scenario, and remediation.

### 2. A09 Logging & Monitoring Coverage

1. Locate the `## A09:` section.
2. Verify findings F-028 through F-030 exist (3 findings).
3. For F-028 (plaintext token logging): run `grep -n 'Magic link token' backend/app/auth/router.py` — confirm the logger.info call includes `%s` for the token value.
4. For F-029 (absent audit trail): run `rg 'security_event|audit_log|auth_event' backend/app/` — confirm zero matches.
5. **Expected:** Logging gaps are specific and verifiable. F-029 is High severity given zero security event visibility.

### 3. A06 CDN Dependency Inventory Completeness

1. Locate the `## A06:` section and F-031.
2. Verify the CDN dependency inventory table lists libraries from at least these templates: `base.html`, `workspace.html`, `calendar_view.html`, `map_view.html`, `timeline_view.html`.
3. Run `rg 'integrity=' backend/app/templates/ frontend/static/` — confirm zero matches (validates the "zero SRI" claim).
4. For F-032 (unpinned deps): verify DOMPurify is listed as unpinned — check `workspace.html` for a CDN URL without a version number in the path.
5. **Expected:** Inventory is comprehensive (25+ entries). SRI status column shows "None" for every entry.

### 4. A08 Data Integrity Coverage

1. Locate the `## A08:` section.
2. Verify findings F-035 through F-037 exist (3 findings).
3. For F-035 (zip-bomb): run `grep -n 'extractall' backend/app/obsidian/router.py backend/app/notion/router.py` — confirm both files call `extractall()` with no preceding size checks.
4. For F-036 (unsigned federation): run `rg 'signature|hash|hmac|digest' backend/app/federation/` — confirm no content-level signing (HTTP Signature for request auth doesn't count).
5. **Expected:** Both ZIP import endpoints and federation sync identified as lacking integrity protections.

### 5. Severity Summary Table Accuracy

1. Scroll to the `## Summary — Findings by Severity` section.
2. Count findings by severity — verify: 5 High, 8 Medium, 4 Low = 17 total.
3. Verify every finding ID (F-021 through F-037) appears exactly once in the summary tables.
4. Check the "Top Remediation Priorities" list has at least 5 entries with rationale.
5. **Expected:** Counts are consistent with the individual findings. No finding is missing or double-counted.

### 6. Finding Format Consistency

1. Pick any 3 findings at random.
2. For each, verify it contains: severity rating, OWASP category, affected file(s) with line numbers, exploit scenario, localhost mitigation note (where relevant), and remediation guidance.
3. **Expected:** Format is consistent with S01's established finding structure.

## Edge Cases

### 7. Finding Number Continuity with S01

1. Check the last finding number in S01-FINDINGS.md (should be F-020).
2. Verify S02-FINDINGS.md starts at F-021.
3. **Expected:** No gaps or overlaps in finding numbering between S01 and S02.

### 8. No Source Code Modifications

1. Run `git diff --name-only` for any files outside `.gsd/`.
2. **Expected:** Zero non-`.gsd/` files modified. This is an analysis-only milestone.

## Failure Signals

- Any finding references a file path that doesn't exist
- Line numbers in findings don't match the actual code
- A CDN-loaded library is missing from the inventory
- The severity summary count doesn't match the individual finding count
- Finding numbers overlap with S01 or have gaps
