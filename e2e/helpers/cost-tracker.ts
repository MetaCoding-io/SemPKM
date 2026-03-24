/**
 * Token counting and budget cap for cloud-tier LLM tests.
 *
 * Tracks prompt and completion tokens across a test run, estimates
 * costs based on configurable per-1k-token pricing, and enforces a
 * per-run budget cap to prevent runaway cloud API charges.
 *
 * Default pricing: gpt-4o-mini ($0.15/1M prompt, $0.60/1M completion)
 *
 * Usage:
 *   import { CostTracker, printCostReport } from '../helpers/cost-tracker';
 *
 *   const tracker = new CostTracker({ budgetUsd: 0.50 });
 *   tracker.addPromptTokens(500);
 *   tracker.addCompletionTokens(200);
 *   tracker.assertBudget(); // throws if over budget
 *   printCostReport(tracker);
 */

export interface CostTrackerOptions {
  /** Maximum spend allowed per test run in USD. Default: $1.00 */
  budgetUsd?: number;
  /** Cost per 1,000 prompt tokens in USD. Default: $0.00015 (gpt-4o-mini) */
  costPer1kPromptTokens?: number;
  /** Cost per 1,000 completion tokens in USD. Default: $0.0006 (gpt-4o-mini) */
  costPer1kCompletionTokens?: number;
}

export interface CostReport {
  promptTokens: number;
  completionTokens: number;
  totalCostUsd: number;
  budgetUsd: number;
  budgetRemaining: number;
}

export class CostTracker {
  private promptTokens = 0;
  private completionTokens = 0;
  private readonly budgetUsd: number;
  private readonly costPer1kPromptTokens: number;
  private readonly costPer1kCompletionTokens: number;

  constructor(options: CostTrackerOptions = {}) {
    this.budgetUsd = options.budgetUsd ?? 1.0;
    this.costPer1kPromptTokens = options.costPer1kPromptTokens ?? 0.00015;
    this.costPer1kCompletionTokens = options.costPer1kCompletionTokens ?? 0.0006;
  }

  /** Accumulate prompt token count. */
  addPromptTokens(count: number): void {
    this.promptTokens += count;
  }

  /** Accumulate completion token count. */
  addCompletionTokens(count: number): void {
    this.completionTokens += count;
  }

  /**
   * Rough-estimate completion tokens from response content.
   * Uses ~4 chars per token heuristic (same as CopilotService).
   */
  estimateCompletionTokensFromContent(content: string): number {
    return Math.ceil(content.length / 4);
  }

  /** Compute total estimated cost in USD from accumulated tokens. */
  totalCostUsd(): number {
    const promptCost = (this.promptTokens / 1000) * this.costPer1kPromptTokens;
    const completionCost =
      (this.completionTokens / 1000) * this.costPer1kCompletionTokens;
    return promptCost + completionCost;
  }

  /**
   * Throws if total cost exceeds budget.
   * Call after each cloud API interaction to fail fast.
   */
  assertBudget(): void {
    const cost = this.totalCostUsd();
    if (cost > this.budgetUsd) {
      throw new Error(
        `Budget exceeded: $${cost.toFixed(4)} / $${this.budgetUsd.toFixed(2)} ` +
          `(${this.promptTokens} prompt + ${this.completionTokens} completion tokens)`,
      );
    }
  }

  /** Return a summary object for logging or assertions. */
  report(): CostReport {
    const cost = this.totalCostUsd();
    return {
      promptTokens: this.promptTokens,
      completionTokens: this.completionTokens,
      totalCostUsd: cost,
      budgetUsd: this.budgetUsd,
      budgetRemaining: this.budgetUsd - cost,
    };
  }
}

/**
 * Log a formatted cost report to the console.
 * Useful as a teardown hook in cloud-tier test suites.
 */
export function printCostReport(tracker: CostTracker): void {
  const r = tracker.report();
  console.log('\n┌─────────────────────────────────┐');
  console.log('│    LLM Cloud Cost Report        │');
  console.log('├─────────────────────────────────┤');
  console.log(`│ Prompt tokens:     ${String(r.promptTokens).padStart(10)} │`);
  console.log(`│ Completion tokens: ${String(r.completionTokens).padStart(10)} │`);
  console.log(`│ Total cost:       $${r.totalCostUsd.toFixed(4).padStart(9)} │`);
  console.log(`│ Budget:           $${r.budgetUsd.toFixed(2).padStart(9)} │`);
  console.log(`│ Remaining:        $${r.budgetRemaining.toFixed(4).padStart(9)} │`);
  console.log('└─────────────────────────────────┘\n');
}
