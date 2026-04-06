---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T02: E2E tests for closed tab recovery

Write Playwright E2E tests proving closed tab recovery works.

1. Create e2e/tests/55-browser-history/closed-tab.spec.ts
2. Test cases:
   a. Open an object tab, close it, press Ctrl+Shift+T → tab reopens with same IRI
   b. Close 3 tabs in sequence, press Ctrl+Shift+T 3 times → all reopen in reverse order
   c. Press Ctrl+Shift+T with no closed tabs → no error, no new tab
   d. Close a tab, reopen it manually (click in explorer), then Ctrl+Shift+T → skips already-open tab
3. Use dockview.ts helpers for tab operations

## Inputs

- `e2e/helpers/dockview.ts`
- `T01 implementation`

## Expected Output

- `e2e/tests/55-browser-history/closed-tab.spec.ts`

## Verification

cd e2e && npx playwright test tests/55-browser-history/closed-tab.spec.ts --headed
