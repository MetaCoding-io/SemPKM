import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for SemPKM E2E tests.
 *
 * Tests run against an isolated Docker Compose stack on port 3901.
 * Start the test environment before running: npm run env:start
 */
export default defineConfig({
  testDir: './tests',
  /* Run tests sequentially — the app is stateful and tests share a Docker stack */
  fullyParallel: false,
  /* Retry once to catch flaky htmx timing issues */
  retries: 1,
  /* Single worker — shared Docker state across tests */
  workers: 1,
  /* Reporter config */
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.TEST_BASE_URL || 'http://localhost:3901',
    /* Collect trace on first retry for debugging */
    trace: 'on-first-retry',
    /* Screenshot on failure for CI artifacts */
    screenshot: 'only-on-failure',
    /* Video on failure for debugging flaky tests */
    video: 'retain-on-failure',
    /* Generous timeout for Docker-based tests */
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  /* Global timeout per test */
  timeout: 60_000,
  /* Global setup: verify test Docker stack is healthy */
  globalSetup: './fixtures/test-harness.ts',
  /* Test output directory */
  outputDir: './test-results',
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'screenshots',
      testMatch: /screenshots\/.*\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        /* No retries for screenshot capture — deterministic output */
        screenshot: 'off',
        video: 'off',
        trace: 'off',
      },
      retries: 0,
    },
    {
      name: 'federation',
      testMatch: /18-federation\/.*\.spec\.ts/,
      use: {
        baseURL: 'http://localhost:3911',
        /* No browser needed — federation tests are API-only */
        trace: 'on-first-retry',
        screenshot: 'off',
        video: 'off',
      },
      /* Sequential execution, single worker — stateful cross-instance flow */
      fullyParallel: false,
      retries: 0,
    },
  ],
});
