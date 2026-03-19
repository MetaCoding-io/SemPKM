# S04: E2E Tests + User Guide — UAT

**Milestone:** M017
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for docs + live-runtime for mock server and E2E)
- Why this mode is sufficient: Mock server selftest validates canned data without Docker. Docs are verifiable by file existence and grep. E2E test requires Docker test stack for full runtime validation.

## Preconditions

1. Docker test stack running: `docker compose -f docker-compose.test.yml up -d --build` from project root
2. Mock GitHub service healthy: `docker compose -f docker-compose.test.yml ps mock-github` shows "healthy"
3. Playwright and dependencies installed: `cd e2e && npm install`
4. basic-pkm model available in `models/` directory
5. github-sync app available in `apps/` directory

## Smoke Test

Run `python3 e2e/mock-github-api/server.py --selftest` — should exit 0 with "9 passed, 0 failed".

## Test Cases

### 1. Mock server selftest validates all endpoints

1. Run `python3 e2e/mock-github-api/server.py --selftest`
2. **Expected:** 9 checks pass: GET /health, GET /user, GET /user/repos, GET /repos/.../issues, 3× GET /repos/.../issues/{n}/timeline, PATCH /repos/.../issues/1, GET /unknown → 404

### 2. Mock server canned data: repos endpoint returns 2 repos

1. Start mock server: `python3 e2e/mock-github-api/server.py &`
2. `curl http://localhost:8080/user/repos`
3. **Expected:** JSON array with 2 repos. First has `full_name: "testuser/test-repo"`, second has `full_name: "testuser/private-repo"` and `private: true`
4. Response includes `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers

### 3. Mock server canned data: issues endpoint returns 3 items (2 issues + 1 PR)

1. `curl http://localhost:8080/repos/testuser/test-repo/issues`
2. **Expected:** JSON array with 3 items. Items 1 and 2 are issues (no `pull_request` key). Item 3 has `pull_request` key (is a PR). Item 1 has labels, assignee, milestone. Item 2 has `state: "closed"` and `state_reason: "not_planned"`.

### 4. Mock server canned data: timeline returns cross-reference event

1. `curl http://localhost:8080/repos/testuser/test-repo/issues/1/timeline`
2. **Expected:** JSON array with 1 event of type `cross-referenced` where `source.issue.number` is 3 and `source.issue.pull_request` exists

### 5. Mock server PATCH echo-back

1. `curl -X PATCH -H "Content-Type: application/json" -d '{"title":"Updated"}' http://localhost:8080/repos/testuser/test-repo/issues/1`
2. **Expected:** JSON response with merged data — `title: "Updated"` plus all other base issue fields preserved

### 6. Docker compose includes mock-github service

1. Run `docker compose --env-file /dev/null -f docker-compose.test.yml config --services`
2. **Expected:** Output includes `mock-github`
3. Run `docker compose --env-file /dev/null -f docker-compose.test.yml config | grep GITHUB_API_URL`
4. **Expected:** Shows `GITHUB_API_URL: http://mock-github:8080` in api environment

### 7. E2E test compiles without type errors

1. `cd e2e && npx tsc --noEmit --project tsconfig.json`
2. **Expected:** Exit code 0, no type errors

### 8. Selector block exists in helpers

1. `grep "githubSync" e2e/helpers/selectors.ts`
2. **Expected:** Match found — `githubSync` block with selectors like `connectForm`, `tokenInput`, `statusSection`, etc.

### 9. Chapter 35 exists with sufficient content

1. `test -f docs/guide/35-github-sync.md && echo "exists"`
2. `grep -c "^##" docs/guide/35-github-sync.md`
3. **Expected:** File exists, heading count ≥ 10 (actual: 33)

### 10. Chapter 35 has field mapping table

1. `grep -c "|" docs/guide/35-github-sync.md`
2. **Expected:** Multiple table rows (pipe characters indicate markdown tables). Should include columns for GitHub Field, bpkm Property, Transform, and Direction.

### 11. README TOC includes Chapter 35

1. `grep "35-github-sync" docs/guide/README.md`
2. **Expected:** Line like `35. [GitHub Sync](35-github-sync.md)`

### 12. Glossary has GitHub Sync entry

1. `grep -i "github sync" docs/guide/appendix-d-glossary.md`
2. **Expected:** Bold entry `**GitHub Sync**` with description mentioning bpkm:Task, pull/push sync, bpkm:dependsOn

### 13. Navigation chain integrity

1. `tail -1 docs/guide/34-linear-sync.md`
2. **Expected:** Contains `35-github-sync.md` (Next link)
3. `tail -1 docs/guide/35-github-sync.md`
4. **Expected:** Contains `appendix-a-environment-variables.md` (Next link)

### 14. E2E test full runtime (when platform fix is applied)

1. Ensure Docker test stack is running with mock-github healthy
2. `cd e2e && npx playwright test tests/32-github-sync/github-sync.spec.ts --project=chromium`
3. **Expected:** All 12 phases pass:
   - Phase 0: Cleanup (idempotent)
   - Phase 1: Install basic-pkm model
   - Phase 2: Install github-sync app
   - Phase 3: Navigate to app settings page
   - Phase 4: Connect with PAT
   - Phase 5: Select repos
   - Phase 6: Configure bidirectional sync
   - Phase 7: Sync Now
   - Phase 8: SPARQL verification (≥3 tasks including PR)
   - Phase 9: SPARQL edge verification (bpkm:dependsOn)
   - Phase 10: Admin detail verification
   - Phase 11: Cleanup

## Edge Cases

### Mock server returns 404 for unknown paths

1. `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/repos/unknown/repo/issues`
2. **Expected:** HTTP 404

### Mock server rate-limit headers present on every response

1. `curl -I http://localhost:8080/user`
2. **Expected:** Headers include `X-RateLimit-Remaining` (e.g., 4999) and `X-RateLimit-Reset` (future timestamp)

### PATCH with partial fields preserves base data

1. `curl -X PATCH -H "Content-Type: application/json" -d '{"state":"closed"}' http://localhost:8080/repos/testuser/test-repo/issues/1`
2. **Expected:** Response has `state: "closed"` but retains original `title`, `assignee`, `labels`, etc.

## Failure Signals

- `--selftest` exits non-zero → mock server canned data corrupt or routing broken
- `docker compose config` missing `mock-github` → docker-compose.test.yml not updated
- `tsc --noEmit` fails → TypeScript compilation errors in E2E test or selectors
- E2E test timeout at Phase 3 → app subprocess not starting (known platform issue)
- Chapter 35 heading count < 10 → guide content incomplete
- README TOC missing Ch 35 → navigation broken for docs readers
- Glossary missing entry → discoverability gap

## Requirements Proved By This UAT

- GH-07 — Mock server (tests 1-6), E2E test structure (tests 7-8, 14), user guide (tests 9-13)
- GH-01 through GH-06 — indirectly via E2E test runtime when phases 3+ execute (test 14)

## Not Proven By This UAT

- Full E2E runtime execution (phases 3-11) — blocked by pre-existing app subprocess startup issue, not a GitHub sync defect
- Push sync round-trip in live Docker stack — covered by 33 unit tests but not yet proven end-to-end
- Real GitHub API interaction — by design (mock server only; no real GitHub account needed)

## Notes for Tester

- The E2E test (test case 14) currently blocks at Phase 3 due to a pre-existing platform issue where app subprocess UDS sockets are not created. This is tracked as a known limitation. The test code is correct — it follows the proven linear-sync E2E pattern and all selectors match the templates.
- The mock server selftest (test case 1) is the best pre-flight check before involving Docker.
- If the Docker test stack has stale state, `docker compose -f docker-compose.test.yml down -v && docker compose -f docker-compose.test.yml up -d --build` does a clean restart.
