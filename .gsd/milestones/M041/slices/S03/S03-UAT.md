# S03: Cross-Cutting Analysis & Report Assembly — UAT

**Milestone:** M041
**Written:** 2026-03-23

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: M041 produces a static analysis report (markdown file), not runtime features. Verification is structural inspection of the deliverable.

## Preconditions

- The repository is checked out at the commit containing S03 work
- Files exist: `.gsd/milestones/M041/M041-RECOMMENDATIONS.md`, `S01-BACKEND-FINDINGS.md`, `S02-FRONTEND-FINDINGS.md`, `S03-CROSS-CUTTING-FINDINGS.md`

## Smoke Test

Open `.gsd/milestones/M041/M041-RECOMMENDATIONS.md` and confirm it has a "Top 10 Highest-Impact Recommendations" section with 10 numbered entries, each having a severity and effort tag.

## Test Cases

### 1. Report structure completeness

1. Run `grep -c "^## " .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
2. **Expected:** ≥ 5 (actual: 7 — Metrics Summary, Top 10, Backend, Frontend, Cross-Cutting, Linting, Appendix)

### 2. All 12+ quality dimensions covered

1. Check for backend dimensions: `grep -q "Module Structure" M041-RECOMMENDATIONS.md` (also: Readability, Error Handling, Logging, Type Safety, SPARQL Construction, Async Patterns, FastAPI Patterns)
2. Check for frontend dimensions: `grep -q "JS Structure" M041-RECOMMENDATIONS.md` (also: DOM & Event, CSS Architecture, Jinja2 Template, htmx Consistency)
3. Check for cross-cutting dimensions: `grep -q "Dead Code" M041-RECOMMENDATIONS.md` (also: Code Duplication, Test Coverage Gaps, Tech Debt)
4. **Expected:** All 17 dimension headings present

### 3. Every finding has required annotations

1. Run `grep -c "Severity:" .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
2. Run `grep -c "Effort:" .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
3. Spot-check 3 random findings for file:line references
4. **Expected:** Severity count ≥ 30 (actual: 94), Effort count ≥ 30 (actual: 86), file references present in spot-checked findings

### 4. Top 10 prioritization is actionable

1. Read the Top 10 section
2. Verify #1 is SPARQL injection risk (highest runtime risk)
3. Verify each entry has: title, severity, effort, specific file references, and what to do
4. **Expected:** 10 entries ordered by runtime risk → correctness → maintainability. Each entry is specific enough to scope an implementation task.

### 5. Linting tool recommendations are concrete

1. Find the "Linting Tool Recommendations" section
2. Check for ruff config: a pyproject.toml `[tool.ruff]` block with specific rule sets
3. Check for ESLint config: mentions flat config format and the IIFE file structure
4. Check for Stylelint config
5. Check for combined setup estimate
6. **Expected:** All three tools recommended with specific configuration, not just "use ruff". Setup effort estimated (~2 hours total).

### 6. Detection commands are reproducible

1. Find the "Appendix: Detection Commands" section
2. Pick 2 commands at random and run them from the project root
3. **Expected:** Commands execute without error and produce output consistent with the findings they support

### 7. Backend and frontend balance

1. Count backend findings: `grep -c "^### " .gsd/milestones/M041/M041-RECOMMENDATIONS.md` within the Backend section
2. Count frontend findings similarly
3. **Expected:** Both sections are substantive (backend: 8 dimension subsections with ~40 findings; frontend: 5 dimension subsections with ~21 findings). Neither is placeholder.

## Edge Cases

### Empty findings dimension

1. Check if any dimension section contains zero findings
2. **Expected:** Every dimension section has at least one finding. Dead Code has the fewest (4 findings) because the codebase is clean on that dimension — this is a valid finding, not a gap.

### Cross-referencing findings across sections

1. Pick a finding from the Top 10 (e.g., #3 Auth test coverage)
2. Find the same topic in the Cross-Cutting > Test Coverage Gaps section
3. **Expected:** The detailed finding in the Cross-Cutting section provides more context than the Top 10 summary. They should be consistent, not contradictory.

## Failure Signals

- `M041-RECOMMENDATIONS.md` is missing or empty
- Any `grep` check returns 0 when expecting ≥ 5 or ≥ 30
- A dimension listed in the milestone success criteria has no corresponding section
- Top 10 entries lack file references or are generic advice without codebase specifics
- Detection commands fail to run or produce results inconsistent with the report

## Requirements Proved By This UAT

- none — M041 creates no requirements; it produces analysis input for a future execution milestone

## Not Proven By This UAT

- Whether the recommendations are correct in every detail — that requires human expert judgment
- Whether implementing the Top 10 would actually improve code quality — that's the execution milestone's job
- Whether the linting configs work as specified — they need to be installed and run

## Notes for Tester

- The report is 1034 lines — skim the Top 10 section first for the executive summary, then spot-check 2-3 detailed findings for specificity.
- The detection commands appendix is the highest-value artifact for reproducibility — running a few commands confirms the methodology is sound.
- Finding counts (84 total, 94 severity annotations) are correct as of assembly date. They will drift as the codebase evolves. The detection commands are the durable artifact.
