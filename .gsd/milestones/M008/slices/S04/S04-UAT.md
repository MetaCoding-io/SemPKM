# S04: E2E Tests & User Guide — UAT

**Milestone:** M008
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 produces test files and documentation. Verification is structural (files exist, sections present, tests pass individually). No new runtime behavior to verify in a live browser — S01–S03 UATs covered the live features.

## Preconditions

- Docker test stack running from the worktree directory (for E2E tests)
- `backend/.venv` exists with pytest installed (for unit tests)
- Node.js and Playwright installed in `e2e/` (for E2E tests)

## Smoke Test

Run `ls e2e/tests/17-spatial-canvas/*.spec.ts | wc -l` — should return `5`. Run `grep '^## ' docs/guide/27-spatial-canvas.md | wc -l` — should return `14`.

## Test Cases

### 1. Property flip E2E spec passes

1. `cd e2e && npx playwright test tests/17-spatial-canvas/canvas-property-flip.spec.ts --project=chromium --reporter=list`
2. **Expected:** 2/2 tests pass — "Canvas properties API" and "Canvas property flip UI"

### 2. Embeds E2E spec passes

1. `cd e2e && npx playwright test tests/17-spatial-canvas/canvas-embeds.spec.ts --project=chromium --reporter=list`
2. **Expected:** 2/2 tests pass — "Canvas embeds API" and "Canvas embeds UI"

### 3. Existing canvas E2E specs not regressed

1. `cd e2e && npx playwright test tests/17-spatial-canvas/canvas-api.spec.ts --project=chromium --reporter=list`
2. `cd e2e && npx playwright test tests/17-spatial-canvas/canvas-resize.spec.ts --project=chromium --reporter=list`
3. **Expected:** All tests pass. (Note: run specs individually with ~60s between to stay within rate limit.)

### 4. Backend unit tests still pass

1. `cd backend && .venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v`
2. **Expected:** 69 tests pass (26 properties + 32 embeds + 11 resize), <1s runtime

### 5. Chapter 27 has all M008 feature sections

1. `grep '^## ' docs/guide/27-spatial-canvas.md`
2. **Expected:** Output includes `## Resizing Nodes`, `## Property Flip`, `## Live Embeds` among 14 total sections

### 6. Chapter 27 "What Gets Saved" updated

1. `grep -A 15 'What Gets Saved' docs/guide/27-spatial-canvas.md`
2. **Expected:** List includes "Node dimensions (width and height)", "Property flip state", "Embed configurations"

### 7. Toolbar table includes Embed entry

1. `grep 'Embed' docs/guide/27-spatial-canvas.md | head -5`
2. **Expected:** At least one line showing Embed in the toolbar table row

### 8. Nav footer chain intact

1. `tail -3 docs/guide/27-spatial-canvas.md`
2. **Expected:** Contains links to Chapter 26 (previous) and Chapter 28 (next)

### 9. Glossary entries placed alphabetically

1. `grep -n 'Embed Node\|Property Flip' docs/guide/appendix-d-glossary.md`
2. **Expected:** "Embed Node" appears between "Edge" and "Entailment" entries. "Property Flip" appears between "PKCE" and "Property" entries.

### 10. No conflict markers anywhere

1. `grep -rn "^<<<<<<< " backend/ frontend/ e2e/ docs/ models/ --include="*.py" --include="*.html" --include="*.js" --include="*.css" --include="*.ts" --include="*.md" --include="*.jsonld"`
2. **Expected:** Zero results

## Edge Cases

### Rate-limited full suite run

1. `cd e2e && npx playwright test tests/17-spatial-canvas/ --project=chromium --reporter=list`
2. **Expected:** First 4 tests (2 specs) pass. Subsequent specs may fail with auth errors (429 Too Many Requests) due to 5/min magic-link rate limit. This is a known environment constraint, not a test bug.

### Property flip spec — backward compatibility

1. In the property flip UI test, the test imports a node state without `showProperties` field
2. **Expected:** Node loads in markdown mode (not property table). No errors in console.

### Embeds spec — max-8 enforcement

1. In the embeds UI test, the test attempts to add a 9th embed after 8 are placed
2. **Expected:** 9th embed rejected. Total embed count stays at 8.

## Failure Signals

- E2E test failures with "Magic link request did not return a token" → rate limit hit, not test bug. Space runs apart.
- E2E test failures with "locator not found" for `.spatial-node-flip` or `.canvas-embed-picker-btn` → S02/S03 feature code missing or Docker stack not running M008 code.
- Missing sections in Chapter 27 → `grep '^## ' docs/guide/27-spatial-canvas.md` shows fewer than 14 headings.
- Glossary out of order → entries appear outside their expected alphabetical position.

## Requirements Proved By This UAT

- None directly — this UAT proves E2E test coverage and documentation completeness. CANVAS-01–05 functional validation is covered by S01–S03 UATs.

## Not Proven By This UAT

- Firefox E2E test execution (only Chromium tested due to Firefox auth fixture flaking)
- Full 5-spec suite run under rate limit (individual + pair runs verified instead)
- Picker item click interaction in E2E (JS API workaround used — picker click race condition in headless mode)

## Notes for Tester

- Run E2E specs individually with ~60s between each spec to stay within the 5/min magic-link rate limit.
- The Docker stack must be started from the worktree directory (`/home/james/Code/SemPKM/.gsd/worktrees/M007`) for volume mounts to pick up M008 code. Starting from the main repo directory will serve pre-M008 code.
- Backend unit tests require no Docker — they run against pure functions with no triplestore.
