/**
 * Schema.org → SemPKM mapper.
 *
 * Maps schema.org JSON-LD entities (from the page extractor) to SemPKM
 * type IRIs and SHACL form field paths. Runs in the popup context as a
 * normal ES module — not in the page context.
 *
 * @module shared/schema-mapper
 */

// ── Type mapping table ────────────────────────────────────────────

/**
 * Schema.org type → SemPKM type IRI.
 * Keys are bare schema.org type names (already normalized).
 */
const TYPE_MAP = {
  Person:           'urn:sempkm:model:crm:Contact',
  Organization:     'urn:sempkm:model:crm:Company',
  Article:          'urn:sempkm:model:basic-pkm:Note',
  NewsArticle:      'urn:sempkm:model:basic-pkm:Note',
  BlogPosting:      'urn:sempkm:model:basic-pkm:Note',
  ScholarlyArticle: 'urn:sempkm:model:research:Paper',
};

// ── Cross-namespace property mapping table ────────────────────────

/**
 * Schema.org property name → SemPKM SHACL path IRI.
 * Used when the schema.org property doesn't live under https://schema.org/.
 */
const CROSS_NS_MAP = {
  givenName:     'urn:sempkm:model:crm:firstName',
  familyName:    'urn:sempkm:model:crm:lastName',
  email:         'urn:sempkm:model:crm:email',
  telephone:     'urn:sempkm:model:crm:phone',
  jobTitle:      'https://schema.org/jobTitle',
  name:          'http://purl.org/dc/terms/title',
  headline:      'http://purl.org/dc/terms/title',
  url:           'https://schema.org/url',
  datePublished: 'https://schema.org/datePublished',
};

// ── normalizeSchemaType ───────────────────────────────────────────

/**
 * Normalize a raw schema.org @type value to a bare type name.
 *
 * Strips `https://schema.org/`, `http://schema.org/`, and `schema:` prefixes.
 * If rawType is an array, returns the first recognized (non-empty) type.
 *
 * @param {string|string[]|null|undefined} rawType
 * @returns {string|null} Bare type name (e.g. "Person") or null
 */
export function normalizeSchemaType(rawType) {
  if (rawType == null) return null;

  if (Array.isArray(rawType)) {
    for (const item of rawType) {
      const normalized = normalizeSchemaType(item);
      if (normalized) return normalized;
    }
    return null;
  }

  const s = String(rawType)
    .replace('https://schema.org/', '')
    .replace('http://schema.org/', '')
    .replace('schema:', '');

  return s || null;
}

// ── suggestType ───────────────────────────────────────────────────

/**
 * Suggest a SemPKM type IRI based on schema.org entities.
 *
 * Iterates through the extracted schema.org entities and checks each @type
 * against the type mapping table. Only suggests types that exist in the
 * provided availableTypes list.
 *
 * @param {Array<Object>} schemaOrgEntities - Array from extractor's schemaOrg field
 * @param {Array<{iri: string}>} availableTypes - Type objects from /api/types
 * @returns {{ typeIri: string, schemaEntity: Object }|null}
 */
export function suggestType(schemaOrgEntities, availableTypes) {
  if (!Array.isArray(schemaOrgEntities) || !Array.isArray(availableTypes)) {
    return null;
  }

  const availableIris = new Set(availableTypes.map((t) => t.iri));

  for (const entity of schemaOrgEntities) {
    const bareType = normalizeSchemaType(entity['@type']);
    if (!bareType) continue;

    const sempkmIri = TYPE_MAP[bareType];
    if (sempkmIri && availableIris.has(sempkmIri)) {
      return { typeIri: sempkmIri, schemaEntity: entity };
    }
  }

  return null;
}

// ── mapSchemaOrgToFormValues ──────────────────────────────────────

/**
 * Map a schema.org entity's properties to SHACL form field paths.
 *
 * Produces a { path: value } object suitable for setting `[data-path]`
 * form inputs rendered by the SHACL renderer.
 *
 * Two mapping levels:
 * 1. Direct namespace: schema.org property name matches the SHACL path's
 *    local name under `https://schema.org/` (e.g. `url` → `https://schema.org/url`).
 * 2. Cross-namespace: explicit mapping table for properties that map to
 *    IRIs in other namespaces (e.g. `givenName` → `urn:sempkm:model:crm:firstName`).
 *
 * @param {Object} schemaEntity - One schema.org JSON-LD entity
 * @param {Array<{path: string}>} shapeProperties - SHACL shape's properties array
 * @returns {Object} Map of SHACL path → scalar value
 */
export function mapSchemaOrgToFormValues(schemaEntity, shapeProperties) {
  if (!schemaEntity || !Array.isArray(shapeProperties)) {
    return {};
  }

  // Build a set of valid paths for fast lookup
  const validPaths = new Set(shapeProperties.map((p) => p.path));

  // Build a map of local-name → full schema.org path for direct namespace matching
  const schemaLocalNameMap = new Map();
  for (const prop of shapeProperties) {
    if (prop.path.startsWith('https://schema.org/')) {
      const localName = prop.path.replace('https://schema.org/', '');
      schemaLocalNameMap.set(localName, prop.path);
    }
  }

  const result = {};

  for (const [key, rawValue] of Object.entries(schemaEntity)) {
    // Skip JSON-LD keywords
    if (key.startsWith('@')) continue;

    // Resolve the value — handle nested author-like objects
    let value = rawValue;
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      // Extract name from nested objects (e.g. author: { name: "..." })
      if (value.name) {
        value = value.name;
      } else {
        continue; // Skip non-scalar objects without a name
      }
    }

    // Skip arrays and non-scalar values
    if (Array.isArray(value)) continue;
    if (value !== null && typeof value === 'object') continue;
    if (value == null) continue;

    // Convert to string for form inputs
    const strValue = String(value);

    // Try cross-namespace mapping first (higher priority for specific mappings)
    const crossPath = CROSS_NS_MAP[key];
    if (crossPath && validPaths.has(crossPath)) {
      // Don't overwrite if already set (first mapping wins)
      if (!(crossPath in result)) {
        result[crossPath] = strValue;
      }
    }

    // Try direct namespace match (schema.org property → schema.org SHACL path)
    const directPath = schemaLocalNameMap.get(key);
    if (directPath && !(directPath in result)) {
      result[directPath] = strValue;
    }
  }

  return result;
}
