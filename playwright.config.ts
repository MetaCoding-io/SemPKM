/**
 * Root-level Playwright config — enables running tests from the project root:
 *   npx playwright test e2e/tests/...
 *
 * Adjusts relative paths from e2e/playwright.config.ts so they resolve
 * correctly when the CWD is the repository root.
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.TEST_BASE_URL || 'http://localhost:3901',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  timeout: 60_000,
  globalSetup: './e2e/fixtures/test-harness.ts',
  outputDir: './e2e/test-results',
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
});
