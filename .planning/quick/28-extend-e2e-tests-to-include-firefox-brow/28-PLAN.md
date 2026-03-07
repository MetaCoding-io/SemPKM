---
phase: quick-28
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - e2e/playwright.config.ts
  - e2e/package.json
autonomous: true
requirements: [QUICK-28]

must_haves:
  truths:
    - "Firefox project exists in Playwright config"
    - "npm run test:firefox runs the full test suite against Firefox"
    - "Existing chromium and screenshots projects are unaffected"
  artifacts:
    - path: "e2e/playwright.config.ts"
      provides: "Firefox project definition"
      contains: "name: 'firefox'"
    - path: "e2e/package.json"
      provides: "Firefox convenience scripts"
      contains: "test:firefox"
  key_links:
    - from: "e2e/package.json"
      to: "e2e/playwright.config.ts"
      via: "npm script --project=firefox flag"
      pattern: "--project=firefox"
---

<objective>
Add Firefox browser to the Playwright E2E test suite.

Purpose: Cross-browser testing catches Firefox-specific rendering and behavior bugs (e.g., the button-inside-label issue from 86aa41a). The config change adding the Firefox project is already uncommitted in the working tree.
Output: Updated playwright.config.ts (already done) and package.json with Firefox convenience scripts, committed.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@e2e/playwright.config.ts
@e2e/package.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Firefox convenience scripts to package.json</name>
  <files>e2e/package.json</files>
  <action>
Add Firefox-specific npm scripts to e2e/package.json, mirroring the existing chromium convenience scripts:

- `"test:firefox": "npx playwright test --project=firefox"` — run all tests against Firefox
- `"test:firefox:headed": "npx playwright test --project=firefox --headed"` — headed mode for debugging
- `"test:firefox:debug": "npx playwright test --project=firefox --debug"` — debug mode

Also add a `"test:all"` script that runs both chromium and firefox: `"npx playwright test --project=chromium --project=firefox"`

The existing `"test"` script MUST remain unchanged (`--project=chromium`) so the default fast path is unaffected.

The playwright.config.ts change is already done (uncommitted) — no modifications needed to that file.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM/e2e && node -e "const p = require('./package.json'); const s = p.scripts; console.assert(s['test:firefox'], 'missing test:firefox'); console.assert(s['test:all'], 'missing test:all'); console.assert(s['test'] === 'npx playwright test --project=chromium', 'default test changed'); console.log('OK')"</automated>
  </verify>
  <done>package.json has test:firefox, test:firefox:headed, test:firefox:debug, and test:all scripts. Default "test" script unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Verify Firefox test execution</name>
  <files>e2e/playwright.config.ts</files>
  <action>
Run the Firefox test suite to confirm tests pass. Execute from the e2e/ directory:

```
npx playwright test --project=firefox
```

If tests fail due to Firefox-specific issues:
- Check for known Firefox HTML parsing pitfalls (buttons inside labels — see CLAUDE.md)
- Check for timing differences (Firefox may need slightly longer waits for htmx swaps)
- If failures are in 00-setup tests (setup wizard), those are expected to fail on non-fresh stacks (same as chromium) — do not count these

If all non-setup tests pass, the task is done. If there are genuine Firefox-specific failures, document them but do NOT modify test files (tests are not to be modified per project conventions).
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM/e2e && npx playwright test --project=firefox 2>&1 | tail -20</automated>
  </verify>
  <done>Firefox test run completes. Non-setup tests pass (matching chromium pass rate of 124/129). Any Firefox-specific failures are documented.</done>
</task>

</tasks>

<verification>
- `npx playwright test --project=firefox` runs and produces results
- `npm run test:firefox` works as alias
- `npm run test` still runs chromium only (unchanged)
- `npm run test:all` runs both chromium and firefox
- playwright.config.ts has firefox project entry
</verification>

<success_criteria>
Firefox project is configured in Playwright, convenience scripts exist in package.json, and the Firefox test suite has been executed to establish a baseline pass rate.
</success_criteria>

<output>
After completion, create `.planning/quick/28-extend-e2e-tests-to-include-firefox-brow/28-SUMMARY.md`
</output>
