# T01: 34-e2e-test-coverage 01

**Slice:** S34 — **Milestone:** M001

## Description

Fix existing E2E tests that skip or target wrong endpoints: rewrite SPARQL console tests for the actual admin page, fix VFS WebDAV auth to use Basic auth with API tokens (wsgidav does NOT accept session cookies), and verify FTS tests pass as-is.

Purpose: Remove all test.skip() calls from SPARQL/FTS/VFS test suites so regressions cause test failures instead of silent skips.
Output: Working SPARQL and VFS test files; FTS confirmed passing.

## Must-Haves

- [ ] "SPARQL console tests run and pass against /admin/sparql without any test.skip()"
- [ ] "FTS keyword search tests run and pass without any test.skip()"
- [ ] "WebDAV VFS tests run and pass against /dav/ without any test.skip()"

## Files

- `e2e/tests/05-admin/sparql-console.spec.ts`
- `e2e/tests/vfs-webdav.spec.ts`
