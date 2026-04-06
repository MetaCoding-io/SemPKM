---
estimated_steps: 9
estimated_files: 2
skills_used: []
---

# T03: E2E tests for URL sync and history navigation

Write Playwright E2E tests proving the URL sync and history navigation work.

1. Create e2e/tests/55-browser-history/history.spec.ts
2. Test cases:
   a. Open an object → URL contains ?tab= with the object IRI
   b. Open object A, open object B → URL shows B → page.goBack() → URL shows A, tab A is active → page.goForward() → URL shows B, tab B is active
   c. Navigate to /browser/?tab=<iri> → object tab opens with correct content
   d. Open two objects, close one, press back → URL updates correctly (no error from missing panel)
3. Use existing E2E helpers (openTab from dockview.ts, SEL selectors)
4. Add history-related selectors to selectors.ts if needed

## Inputs

- `e2e/helpers/dockview.ts (openTab helper)`
- `e2e/helpers/selectors.ts`
- `T01+T02 implementation`

## Expected Output

- `e2e/tests/55-browser-history/history.spec.ts`

## Verification

cd e2e && npx playwright test tests/55-browser-history/history.spec.ts --headed
