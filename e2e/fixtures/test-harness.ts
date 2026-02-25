/**
 * Global setup for E2E tests.
 *
 * Verifies the test Docker stack is running and healthy before tests execute.
 * Does NOT start/stop Docker — that's handled by the npm scripts so
 * developers can keep the stack running across test iterations.
 */
import { request } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';
const HEALTH_URL = `${BASE_URL}/api/health`;
const MAX_RETRIES = 15;
const RETRY_DELAY_MS = 2000;

async function globalSetup() {
  console.log(`\nVerifying test environment at ${BASE_URL}...`);

  for (let i = 0; i < MAX_RETRIES; i++) {
    try {
      const context = await request.newContext();
      const response = await context.get(HEALTH_URL);
      await context.dispose();

      if (response.ok()) {
        console.log(`Test environment healthy after ${i + 1} attempts.\n`);
        return;
      }
    } catch {
      // Connection refused or network error — keep retrying
    }

    if (i < MAX_RETRIES - 1) {
      console.log(`  Attempt ${i + 1}/${MAX_RETRIES} — retrying in ${RETRY_DELAY_MS}ms...`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }

  throw new Error(
    `Test environment not healthy after ${MAX_RETRIES} attempts.\n` +
    `Start it with: cd e2e && npm run env:start`
  );
}

export default globalSetup;
