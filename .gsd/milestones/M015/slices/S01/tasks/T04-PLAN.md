---
estimated_steps: 5
estimated_files: 1
---

# T04: Add Node.js unit tests for ranking, grouping, and LRU cache

**Slice:** S01 — Context queries, badge count, and sidebar with grouped results
**Milestone:** M015

## Description

Contract verification for the pure logic in `context-utils.js`. Uses Node.js built-in `node:test` and `node:assert` — no external dependencies. Tests exercise the three exported functions (`rankResults`, `groupByType`, `LRUCache`) with edge cases.

This is the slice's primary automated verification — the sideload testing is manual, but these tests can run in CI.

## Steps

1. **Create `extension/tests/test-context-utils.js`:**
   - Import: `const { describe, it } = require('node:test'); const assert = require('node:assert');`
   - Load the module: `require('../shared/context-utils.js');` then `const { rankResults, groupByType, LRUCache } = globalThis.SemPKMContextUtils;`

2. **Write `rankResults` tests (≥6 tests):**
   - URL matches sort before title matches: input `[{match_type:'title'}, {match_type:'url'}]` → first result is url
   - Title matches sort before keyword matches
   - Full ordering: mix of url/title/keyword → output order is all url, all title, all keyword
   - Preserves order within same match_type: two keyword results maintain original relative order
   - Truncates to 10: input 15 results → output length is 10
   - Empty input: `rankResults([])` → returns `[]`
   - Does not mutate input: original array unchanged after call
   - Unknown match_type treated as lowest priority (after keyword)

3. **Write `groupByType` tests (≥5 tests):**
   - Groups by `type_label`: 2 Notes + 1 Concept → 2 groups, first group has 2 items
   - Null `type_label` grouped as "Other": result with `type_label: null` → appears in "Other" group
   - Undefined `type_label` also grouped as "Other"
   - Preserves first-seen order: if first result is Note, second is Concept → Note group comes first
   - Each group has `typeLabel`, `typeIri` (from first result in group), and `results` array
   - Empty input: `groupByType([])` → returns `[]`

4. **Write `LRUCache` tests (≥6 tests):**
   - Basic set/get: `cache.set('a', 1); assert.strictEqual(cache.get('a'), 1)`
   - Missing key returns undefined: `cache.get('nonexistent')` → `undefined`
   - `has()` returns true for existing, false for missing
   - Max size eviction: create cache with maxSize=3, set 4 items → first item evicted
   - `get()` promotes entry: set a,b,c (maxSize=3), get('a'), set('d') → 'b' evicted (not 'a', because get promoted it)
   - `clear()` removes all: set items, clear, has() returns false for all
   - Update in place: `set('a', 1)` then `set('a', 2)` → `get('a')` returns 2, size is still 1

5. **Run and verify:**
   - `node --test extension/tests/test-context-utils.js` — all ≥17 tests pass
   - No external dependencies needed

## Must-Haves

- [ ] ≥6 tests for `rankResults` covering ordering, truncation, empty input, and immutability
- [ ] ≥5 tests for `groupByType` covering grouping, null type_label, ordering, and empty input
- [ ] ≥6 tests for `LRUCache` covering CRUD, eviction, promotion, and clear
- [ ] All tests pass with `node --test`
- [ ] No external dependencies — only `node:test` and `node:assert`

## Verification

- `node --test extension/tests/test-context-utils.js` — all tests pass, 0 failures
- Test count ≥ 17

## Observability Impact

- **New signal:** `node --test extension/tests/test-context-utils.js` — CI-runnable test suite reporting pass/fail counts for all three context-utils exports
- **Inspection:** Test output uses Node.js TAP-like reporter showing individual test names and durations; `--test-reporter spec` for verbose output
- **Failure visibility:** Any regression in `rankResults`, `groupByType`, or `LRUCache` surfaces as a named test failure with assertion details (expected vs actual)
- **No runtime signals changed** — this task adds offline verification only, no changes to service worker or sidebar logging

## Inputs

- `extension/shared/context-utils.js` — T02's pure functions module exporting `rankResults`, `groupByType`, `LRUCache` via `globalThis.SemPKMContextUtils` and `module.exports`

## Expected Output

- `extension/tests/test-context-utils.js` — ≥17 passing unit tests covering all three exported functions
