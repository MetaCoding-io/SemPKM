/**
 * Global setup for E2E tests.
 *
 * Verifies the test Docker stack is running and healthy before tests execute.
 * Does NOT start/stop Docker — that's handled by the npm scripts so
 * developers can keep the stack running across test iterations.
 *
 * When ONLY the 'federation' project is being run (via --project=federation),
 * checks the federation instances instead of the regular test stack.
 */
import { request, type FullConfig } from '@playwright/test';

const MAX_RETRIES = 15;
const RETRY_DELAY_MS = 2000;

async function checkHealth(url: string, label: string): Promise<void> {
  for (let i = 0; i < MAX_RETRIES; i++) {
    try {
      const context = await request.newContext();
      const response = await context.get(url);
      await context.dispose();

      if (response.ok()) {
        console.log(`  ✓ ${label} healthy after ${i + 1} attempts.`);
        return;
      }
    } catch {
      // Connection refused or network error — keep retrying
    }

    if (i < MAX_RETRIES - 1) {
      console.log(`  Attempt ${i + 1}/${MAX_RETRIES} for ${label} — retrying in ${RETRY_DELAY_MS}ms...`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }

  throw new Error(
    `${label} not healthy after ${MAX_RETRIES} attempts.`
  );
}

async function globalSetup(config: FullConfig) {
  // When TEST_FEDERATION=1, check federation instances instead of regular test stack.
  // Set automatically when running: TEST_FEDERATION=1 npx playwright test --project=federation
  // Or detect from command line args: --project=federation
  const isFederation = process.env.TEST_FEDERATION === '1' ||
    process.argv.some(arg => arg === 'federation' || arg === '--project=federation');

  if (isFederation) {
    console.log('\nVerifying federation test environment...');
    await checkHealth('http://localhost:3911/api/health', 'Federation Instance A');
    await checkHealth('http://localhost:3912/api/health', 'Federation Instance B');
    console.log('Federation environment ready.\n');
  } else {
    const baseURL = process.env.TEST_BASE_URL || 'http://localhost:3901';
    console.log(`\nVerifying test environment at ${baseURL}...`);
    await checkHealth(`${baseURL}/api/health`, 'Test environment');
    console.log('');
  }
}

export default globalSetup;
