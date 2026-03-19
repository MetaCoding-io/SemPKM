/**
 * Unit tests for context-utils.js pure functions.
 *
 * Run: node --test extension/tests/test-context-utils.js
 *
 * Uses only Node.js built-in test runner and assert — no external dependencies.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert');

// Load module — sets globalThis.SemPKMContextUtils and module.exports
require('../shared/context-utils.js');
const { rankResults, groupByType, LRUCache } = globalThis.SemPKMContextUtils;

// ---------------------------------------------------------------------------
// Helpers — minimal result object factories
// ---------------------------------------------------------------------------

function makeResult(overrides = {}) {
  return {
    iri: overrides.iri || 'urn:test:1',
    label: overrides.label || 'Test',
    type_iri: overrides.type_iri || 'urn:type:Note',
    type_label: overrides.type_label || 'Note',
    match_type: overrides.match_type || 'keyword',
    snippet: overrides.snippet || null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// rankResults
// ---------------------------------------------------------------------------

describe('rankResults', () => {
  it('url matches sort before title matches', () => {
    const input = [
      makeResult({ match_type: 'title', label: 'A' }),
      makeResult({ match_type: 'url', label: 'B' }),
    ];
    const ranked = rankResults(input);
    assert.strictEqual(ranked[0].label, 'B');
    assert.strictEqual(ranked[1].label, 'A');
  });

  it('title matches sort before keyword matches', () => {
    const input = [
      makeResult({ match_type: 'keyword', label: 'A' }),
      makeResult({ match_type: 'title', label: 'B' }),
    ];
    const ranked = rankResults(input);
    assert.strictEqual(ranked[0].label, 'B');
    assert.strictEqual(ranked[1].label, 'A');
  });

  it('full ordering: url > title > keyword', () => {
    const input = [
      makeResult({ match_type: 'keyword', label: 'K1' }),
      makeResult({ match_type: 'url', label: 'U1' }),
      makeResult({ match_type: 'title', label: 'T1' }),
      makeResult({ match_type: 'keyword', label: 'K2' }),
      makeResult({ match_type: 'url', label: 'U2' }),
    ];
    const ranked = rankResults(input);
    assert.deepStrictEqual(
      ranked.map((r) => r.label),
      ['U1', 'U2', 'T1', 'K1', 'K2']
    );
  });

  it('preserves order within same match_type', () => {
    const input = [
      makeResult({ match_type: 'keyword', label: 'First' }),
      makeResult({ match_type: 'keyword', label: 'Second' }),
      makeResult({ match_type: 'keyword', label: 'Third' }),
    ];
    const ranked = rankResults(input);
    assert.deepStrictEqual(
      ranked.map((r) => r.label),
      ['First', 'Second', 'Third']
    );
  });

  it('truncates to 10 results', () => {
    const input = Array.from({ length: 15 }, (_, i) =>
      makeResult({ match_type: 'keyword', label: `R${i}` })
    );
    const ranked = rankResults(input);
    assert.strictEqual(ranked.length, 10);
  });

  it('returns empty array for empty input', () => {
    const ranked = rankResults([]);
    assert.deepStrictEqual(ranked, []);
  });

  it('does not mutate the input array', () => {
    const input = [
      makeResult({ match_type: 'title', label: 'A' }),
      makeResult({ match_type: 'url', label: 'B' }),
    ];
    const snapshot = JSON.stringify(input);
    rankResults(input);
    assert.strictEqual(JSON.stringify(input), snapshot);
  });

  it('unknown match_type treated as lowest priority (same as keyword)', () => {
    const input = [
      makeResult({ match_type: 'unknown', label: 'X' }),
      makeResult({ match_type: 'url', label: 'U' }),
      makeResult({ match_type: 'keyword', label: 'K' }),
    ];
    const ranked = rankResults(input);
    // url first, then unknown and keyword share priority 2 — stable sort preserves relative order
    assert.strictEqual(ranked[0].label, 'U');
    // unknown and keyword both get priority 2, original order preserved among them
    assert.strictEqual(ranked[1].label, 'X');
    assert.strictEqual(ranked[2].label, 'K');
  });
});

// ---------------------------------------------------------------------------
// groupByType
// ---------------------------------------------------------------------------

describe('groupByType', () => {
  it('groups by type_label', () => {
    const input = [
      makeResult({ type_label: 'Note', label: 'N1' }),
      makeResult({ type_label: 'Note', label: 'N2' }),
      makeResult({ type_label: 'Concept', label: 'C1' }),
    ];
    const groups = groupByType(input);
    assert.strictEqual(groups.length, 2);
    assert.strictEqual(groups[0].typeLabel, 'Note');
    assert.strictEqual(groups[0].results.length, 2);
    assert.strictEqual(groups[1].typeLabel, 'Concept');
    assert.strictEqual(groups[1].results.length, 1);
  });

  it('null type_label grouped as "Other"', () => {
    const input = [makeResult({ type_label: null })];
    const groups = groupByType(input);
    assert.strictEqual(groups.length, 1);
    assert.strictEqual(groups[0].typeLabel, 'Other');
  });

  it('undefined type_label grouped as "Other"', () => {
    const input = [{ iri: 'urn:x', label: 'X', type_iri: null, match_type: 'keyword' }];
    // type_label is undefined — not present on the object
    const groups = groupByType(input);
    assert.strictEqual(groups.length, 1);
    assert.strictEqual(groups[0].typeLabel, 'Other');
  });

  it('preserves first-seen order', () => {
    const input = [
      makeResult({ type_label: 'Note', label: 'N1' }),
      makeResult({ type_label: 'Concept', label: 'C1' }),
      makeResult({ type_label: 'Note', label: 'N2' }),
    ];
    const groups = groupByType(input);
    assert.strictEqual(groups[0].typeLabel, 'Note');
    assert.strictEqual(groups[1].typeLabel, 'Concept');
  });

  it('each group has typeLabel, typeIri, and results array', () => {
    const input = [
      makeResult({ type_label: 'Note', type_iri: 'urn:type:Note', label: 'N1' }),
    ];
    const groups = groupByType(input);
    const group = groups[0];
    assert.strictEqual(group.typeLabel, 'Note');
    assert.strictEqual(group.typeIri, 'urn:type:Note');
    assert.ok(Array.isArray(group.results));
    assert.strictEqual(group.results.length, 1);
  });

  it('typeIri comes from the first result in the group', () => {
    const input = [
      makeResult({ type_label: 'Note', type_iri: 'urn:type:Note-v1', label: 'N1' }),
      makeResult({ type_label: 'Note', type_iri: 'urn:type:Note-v2', label: 'N2' }),
    ];
    const groups = groupByType(input);
    assert.strictEqual(groups[0].typeIri, 'urn:type:Note-v1');
  });

  it('returns empty array for empty input', () => {
    const groups = groupByType([]);
    assert.deepStrictEqual(groups, []);
  });
});

// ---------------------------------------------------------------------------
// LRUCache
// ---------------------------------------------------------------------------

describe('LRUCache', () => {
  it('basic set and get', () => {
    const cache = new LRUCache(10);
    cache.set('a', 1);
    assert.strictEqual(cache.get('a'), 1);
  });

  it('missing key returns undefined', () => {
    const cache = new LRUCache(10);
    assert.strictEqual(cache.get('nonexistent'), undefined);
  });

  it('has() returns true for existing, false for missing', () => {
    const cache = new LRUCache(10);
    cache.set('x', 42);
    assert.strictEqual(cache.has('x'), true);
    assert.strictEqual(cache.has('y'), false);
  });

  it('evicts oldest entry when at max size', () => {
    const cache = new LRUCache(3);
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    cache.set('d', 4); // should evict 'a'
    assert.strictEqual(cache.has('a'), false);
    assert.strictEqual(cache.get('b'), 2);
    assert.strictEqual(cache.get('c'), 3);
    assert.strictEqual(cache.get('d'), 4);
  });

  it('get() promotes entry — prevents eviction', () => {
    const cache = new LRUCache(3);
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    // Access 'a' to promote it to most-recent
    cache.get('a');
    // Now insert 'd' — should evict 'b' (oldest after promotion), not 'a'
    cache.set('d', 4);
    assert.strictEqual(cache.has('a'), true, 'a should survive (was promoted)');
    assert.strictEqual(cache.has('b'), false, 'b should be evicted (oldest)');
    assert.strictEqual(cache.has('c'), true);
    assert.strictEqual(cache.has('d'), true);
  });

  it('clear() removes all entries', () => {
    const cache = new LRUCache(10);
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    cache.clear();
    assert.strictEqual(cache.has('a'), false);
    assert.strictEqual(cache.has('b'), false);
    assert.strictEqual(cache.has('c'), false);
    assert.strictEqual(cache.size, 0);
  });

  it('update in place — overwrites value, size stays same', () => {
    const cache = new LRUCache(10);
    cache.set('a', 1);
    cache.set('a', 2);
    assert.strictEqual(cache.get('a'), 2);
    assert.strictEqual(cache.size, 1);
  });

  it('size reflects current entry count', () => {
    const cache = new LRUCache(10);
    assert.strictEqual(cache.size, 0);
    cache.set('a', 1);
    assert.strictEqual(cache.size, 1);
    cache.set('b', 2);
    assert.strictEqual(cache.size, 2);
    cache.clear();
    assert.strictEqual(cache.size, 0);
  });
});
