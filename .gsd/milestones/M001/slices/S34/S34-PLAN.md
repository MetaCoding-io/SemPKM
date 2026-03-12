# S34: E2e Test Coverage

**Goal:** Fix existing E2E tests that skip or target wrong endpoints: rewrite SPARQL console tests for the actual admin page, fix VFS WebDAV auth to use Basic auth with API tokens (wsgidav does NOT accept session cookies), and verify FTS tests pass as-is.
**Demo:** Fix existing E2E tests that skip or target wrong endpoints: rewrite SPARQL console tests for the actual admin page, fix VFS WebDAV auth to use Basic auth with API tokens (wsgidav does NOT accept session cookies), and verify FTS tests pass as-is.

## Must-Haves


## Tasks

- [x] **T01: 34-e2e-test-coverage 01** `est:4min`
  - Fix existing E2E tests that skip or target wrong endpoints: rewrite SPARQL console tests for the actual admin page, fix VFS WebDAV auth to use Basic auth with API tokens (wsgidav does NOT accept session cookies), and verify FTS tests pass as-is.

Purpose: Remove all test.skip() calls from SPARQL/FTS/VFS test suites so regressions cause test failures instead of silent skips.
Output: Working SPARQL and VFS test files; FTS confirmed passing.
- [x] **T02: 34-e2e-test-coverage 02** `est:9min`
  - Write new Playwright E2E tests covering v2.3 user-visible features: fuzzy FTS toggle, carousel view switching, named workspace layout save/restore, and dockview panel management assertions.

Purpose: Ensure v2.3 features have regression coverage so future changes don't break fuzzy search, carousel views, named layouts, or dockview panel operations without detection.
Output: Three new test files covering TEST-04 requirements including dockview panel management.

## Files Likely Touched

- `e2e/tests/05-admin/sparql-console.spec.ts`
- `e2e/tests/vfs-webdav.spec.ts`
- `e2e/tests/08-search/fuzzy-toggle.spec.ts`
- `e2e/tests/03-navigation/named-layouts.spec.ts`
- `e2e/tests/02-views/carousel-views.spec.ts`
