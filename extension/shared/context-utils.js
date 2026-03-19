/**
 * Pure utility functions for context overlay result processing.
 *
 * This module works in three environments:
 *   - Service worker: importScripts('../shared/context-utils.js') → globalThis.SemPKMContextUtils
 *   - Sidebar (ES module): import via thin wrapper
 *   - Node.js tests: require('./extension/shared/context-utils.js')
 *
 * @module shared/context-utils
 */

// ---------------------------------------------------------------------------
// rankResults — sort by match_type priority and truncate
// ---------------------------------------------------------------------------

/**
 * Rank context query results by match_type priority: url > title > keyword.
 * Within each group, original order is preserved. Returns top 10.
 *
 * @param {Array<{iri: string, label: string, type_iri: string, type_label: string, match_type: string, snippet: string|null}>} results
 * @returns {Array} Sorted copy, max 10 items
 */
function rankResults(results) {
  const PRIORITY = { url: 0, title: 1 };

  const sorted = results.slice().sort((a, b) => {
    const pa = PRIORITY[a.match_type] ?? 2;
    const pb = PRIORITY[b.match_type] ?? 2;
    return pa - pb;
  });

  return sorted.slice(0, 10);
}

// ---------------------------------------------------------------------------
// groupByType — cluster results by type_label
// ---------------------------------------------------------------------------

/**
 * Group ranked results by type_label, preserving first-seen order.
 * Null/undefined type_label is grouped as "Other".
 *
 * @param {Array<{type_label: string|null, type_iri: string|null}>} results
 * @returns {Array<{typeLabel: string, typeIri: string|null, results: Array}>}
 */
function groupByType(results) {
  const groups = new Map(); // typeLabel → {typeLabel, typeIri, results}

  for (const item of results) {
    const label = item.type_label || 'Other';
    if (!groups.has(label)) {
      groups.set(label, {
        typeLabel: label,
        typeIri: item.type_iri || null,
        results: [],
      });
    }
    groups.get(label).results.push(item);
  }

  return Array.from(groups.values());
}

// ---------------------------------------------------------------------------
// LRUCache — Map-based least-recently-used cache
// ---------------------------------------------------------------------------

/**
 * Simple LRU cache backed by a Map (which preserves insertion order).
 * On get(), the key is deleted and re-set to move it to most-recent.
 * On set() at capacity, the oldest entry (first key) is evicted.
 */
class LRUCache {
  /**
   * @param {number} [maxSize=100] - Maximum number of entries
   */
  constructor(maxSize = 100) {
    this._maxSize = maxSize;
    this._map = new Map();
  }

  /**
   * Get a cached value. Promotes key to most-recent on access.
   * @param {string} key
   * @returns {*} Cached value or undefined
   */
  get(key) {
    if (!this._map.has(key)) return undefined;
    const value = this._map.get(key);
    // Promote to most-recent by delete + re-set
    this._map.delete(key);
    this._map.set(key, value);
    return value;
  }

  /**
   * Store a value. Evicts the oldest entry if at capacity.
   * @param {string} key
   * @param {*} value
   */
  set(key, value) {
    // If key already exists, delete first to update insertion order
    if (this._map.has(key)) {
      this._map.delete(key);
    } else if (this._map.size >= this._maxSize) {
      // Evict oldest (first key in Map iteration order)
      const oldestKey = this._map.keys().next().value;
      this._map.delete(oldestKey);
    }
    this._map.set(key, value);
  }

  /**
   * Check if key exists in cache.
   * @param {string} key
   * @returns {boolean}
   */
  has(key) {
    return this._map.has(key);
  }

  /** Remove all entries. */
  clear() {
    this._map.clear();
  }

  /** Current number of entries. */
  get size() {
    return this._map.size;
  }
}

// ---------------------------------------------------------------------------
// Module export — works in importScripts, Node.js require, and globalThis
// ---------------------------------------------------------------------------

const SemPKMContextUtils = { rankResults, groupByType, LRUCache };

if (typeof globalThis !== 'undefined') globalThis.SemPKMContextUtils = SemPKMContextUtils;
if (typeof module !== 'undefined' && module.exports) module.exports = SemPKMContextUtils;
