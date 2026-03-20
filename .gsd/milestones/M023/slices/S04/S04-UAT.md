# S04: E2E Tests + User Guide — UAT

**Milestone:** M023
**Written:** 2026-03-19

## UAT Type

- UAT mode: mixed (artifact-driven for docs/selectors/test structure, live-runtime for mock server selftest)
- Why this mode is sufficient: The mock server selftest proves endpoint correctness offline. The E2E test structure is validated by pattern conformance to the proven GitHub/Linear templates. User guide content is verified by grep-based cross-reference checks.

## Preconditions

- Working directory is the M023 worktree
- Python 3.12+ available for mock server selftest
- Docker Compose available (for full E2E execution — not required for artifact verification)

## Smoke Test

Run `python3 e2e/mock-jira-api/server.py --selftest` — should exit 0 with 12/12 checks passing.

## Test Cases

### 1. Mock Jira API selftest passes

1. Run `python3 e2e/mock-jira-api/server.py --selftest`
2. **Expected:** Exit code 0, output shows 12 ✓ checks, 0 failures. All 7 endpoints validated (health, myself, projects, search, user, issue get, issue update) plus error paths.

### 2. Mock server canned data structure is correct

1. Run `python3 -c "import sys; sys.path.insert(0,'e2e/mock-jira-api'); from server import _PROJECTS, _ISSUES, _USERS; print(len(_PROJECTS), len(_ISSUES), len(_USERS))"`
2. **Expected:** Output is `2 3 1` (2 projects, 3 issues, 1 user lookup entry)

### 3. PROJ-1 has Blocks issue link to PROJ-3

1. Run selftest and check PROJ-1 issue data
2. **Expected:** PROJ-1's `fields.issuelinks` contains an entry with `type.name="Blocks"` and `inwardIssue.key="PROJ-3"`

### 4. PROJ-3 is an Epic type

1. Run selftest check for PROJ-3
2. **Expected:** PROJ-3's `fields.issuetype.name` is `"Epic"` (capitalized)

### 5. Docker service configuration is correct

1. Run `grep -A15 "mock-jira:" docker-compose.test.yml`
2. **Expected:** Service block shows python:3.12-slim image, volume mount `./e2e/mock-jira-api:/app:ro`, healthcheck on `/health`, sempkm-test network
3. Run `grep "JIRA_API_URL" docker-compose.test.yml`
4. **Expected:** `JIRA_API_URL: http://mock-jira:8080` in api service environment
5. Run `grep -A5 "depends_on" docker-compose.test.yml | grep "mock-jira"`
6. **Expected:** `mock-jira:` appears in api service depends_on with `condition: service_healthy`

### 6. jiraSync selectors are complete

1. Run `grep -A20 "jiraSync" e2e/helpers/selectors.ts`
2. **Expected:** Block contains selectors for: emailInput, tokenInput, siteUrlInput, connectBtn, connectStatus, siteUrl, projectCheckbox, saveProjectsBtn, syncDirectionBidirectional, saveConfigBtn, syncNowBtn, syncStats (at least 12 entries)

### 7. E2E test has all 12 phases

1. Run `grep "Phase" e2e/tests/41-jira-sync/jira-sync.spec.ts`
2. **Expected:** Phases 0 through 11 present (including 9b), totaling ≥10 phase references
3. Phase 0: cleanup (app ID `jira-sync`)
4. Phase 4: connects with 3 fields (email, token, siteUrl)
5. Phase 8: SPARQL counts Tasks (≥2, not ≥3 — PROJ-3 Epic maps to Milestone)
6. Phase 9: ASK query for bpkm:Milestone
7. Phase 9b: ASK query for bpkm:dependsOn
8. Test timeout is 240s

### 8. Chapter 36 has all required sections

1. Run `grep "^##" docs/guide/36-jira-sync.md`
2. **Expected:** Sections include: Prerequisites, Installing, Connecting, Project Selection, JQL Filter, Sync Configuration, Field Mapping, Push Sync, Epic→Milestone, Issue Links, Troubleshooting (at minimum)

### 9. Field mapping tables are present

1. Run `grep -c "|" docs/guide/36-jira-sync.md`
2. **Expected:** Multiple table rows (status mapping: 3 statusCategory.key values; priority mapping: 8 Jira names; field mapping table)

### 10. Cross-references are complete

1. Run `grep "36.*Jira" docs/guide/README.md`
2. **Expected:** Chapter 36 entry in TOC
3. Run `grep -ci "jira sync\|statusCategory\|atlassian document format" docs/guide/appendix-d-glossary.md`
4. **Expected:** At least 3 glossary entries
5. Run `grep "JIRA_API_URL" docs/guide/appendix-a-environment-variables.md`
6. **Expected:** JIRA_API_URL entry present

### 11. Navigation chain is correct

1. Run `grep "Chapter 36" docs/guide/35-github-sync.md`
2. **Expected:** Ch 35's Next link points to Chapter 36
3. Run `grep "Chapter 35" docs/guide/36-jira-sync.md`
4. **Expected:** Ch 36's Previous link points to Chapter 35
5. Run `grep "Appendix A" docs/guide/36-jira-sync.md`
6. **Expected:** Ch 36's Next link points to Appendix A

## Edge Cases

### Mock server handles unknown paths

1. Run selftest — check the "GET /unknown → 404" check
2. **Expected:** Returns `{"message": "Not Found"}` with 404 status

### Mock server handles PUT to unknown issue

1. Run selftest — check the "PUT /rest/api/3/issue/UNKNOWN-1 → 404" check
2. **Expected:** Returns 404 for non-existent issue key

### POST search parses JSON body

1. Selftest sends POST with `{"jql": "...", "startAt": 0, "maxResults": 50}`
2. **Expected:** Server parses JSON body correctly, returns filtered issues based on JQL project key

## Failure Signals

- `python3 e2e/mock-jira-api/server.py --selftest` exits non-zero → mock server has bugs
- `jiraSync` selector block missing from selectors.ts → E2E test can't find form elements
- `JIRA_API_URL` missing from docker-compose.test.yml → app won't find mock server
- Missing `mock-jira` in depends_on → api container may start before mock is ready
- Chapter 36 missing sections → incomplete user documentation
- Navigation chain broken → users can't navigate between chapters

## Requirements Proved By This UAT

- JIRA-12 — Mock server selftest proves endpoint correctness; E2E test structure proves lifecycle coverage; Chapter 36 proves user-facing documentation completeness

## Not Proven By This UAT

- Full E2E execution against Docker Compose stack (requires standing up the complete test infrastructure with all services)
- Actual sync behavior end-to-end (covered by S01–S03 unit tests, but not re-proven here at integration level)
- Real-world ADF document conversion quality (covered by S01's 95 unit tests with realistic ADF samples)

## Notes for Tester

- The mock server selftest is the most trustworthy artifact — it validates all 7 endpoints without Docker.
- The E2E test file follows the exact same structure as `github-sync.spec.ts` and `linear-sync.spec.ts` — if those tests pass against their respective Docker stacks, this one will too given correct selectors and mock data.
- Chapter 36 navigation chain goes Ch 35 (GitHub) → Ch 36 (Jira) → Appendix A. This is correct — Ch 35's footer was updated from "Next: Appendix A" to "Next: Chapter 36".
- The E2E test expects ≥2 Tasks (not ≥3) because PROJ-3 is an Epic that maps to bpkm:Milestone, not bpkm:Task.
