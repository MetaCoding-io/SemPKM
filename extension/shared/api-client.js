/**
 * SemPKM API client for the browser extension.
 *
 * Single point of contact between the extension and the SemPKM backend.
 * All methods use fetch() with Authorization: Bearer header.
 *
 * @module shared/api-client
 */

/**
 * Custom error class for SemPKM API errors.
 * Carries HTTP status and parsed detail from the backend response.
 */
export class SemPKMError extends Error {
  /**
   * @param {string} message - Human-readable error description
   * @param {number} status - HTTP status code
   * @param {string|null} detail - Parsed error detail from backend JSON
   */
  constructor(message, status, detail = null) {
    super(message);
    this.name = 'SemPKMError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * SemPKM API client.
 *
 * Usage:
 *   const client = new SemPKMClient('http://localhost:4000', 'my-api-key');
 *   const info = await client.connect();
 *   const types = await client.getTypes();
 */
export class SemPKMClient {
  /**
   * @param {string} instanceUrl - Base URL of the SemPKM instance (no trailing slash)
   * @param {string} apiKey - Bearer token for API authentication
   */
  constructor(instanceUrl, apiKey) {
    // Strip trailing slash for consistent URL construction
    this.instanceUrl = instanceUrl.replace(/\/+$/, '');
    this.apiKey = apiKey;
  }

  /**
   * Build standard headers for all API requests.
   * @returns {Headers}
   */
  _headers() {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Make a fetch request and handle errors uniformly.
   * @param {string} path - URL path (appended to instanceUrl)
   * @param {RequestInit} [options] - fetch options
   * @returns {Promise<any>} Parsed JSON response
   * @throws {SemPKMError} On non-ok response
   */
  async _request(path, options = {}) {
    const url = `${this.instanceUrl}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this._headers(),
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let detail = null;
      try {
        const errorBody = await response.json();
        detail = errorBody.detail || errorBody.error || JSON.stringify(errorBody);
      } catch {
        // Response body wasn't JSON — use status text
        detail = response.statusText;
      }
      throw new SemPKMError(
        `API request failed: ${response.status} ${detail}`,
        response.status,
        detail,
      );
    }

    return response.json();
  }

  /**
   * Test connection to the SemPKM instance.
   * GET /.well-known/sempkm
   *
   * @returns {Promise<{version: string, endpoints: Object, capabilities: string[], auth: Object}>}
   * @throws {SemPKMError} If the instance is unreachable or credentials are invalid
   */
  async connect() {
    return this._request('/.well-known/sempkm');
  }

  /**
   * Fetch all available types from installed Mental Models.
   * GET /api/types
   *
   * @returns {Promise<Array<{iri: string, label: string, icon: string|null, icon_color: string|null, model_id: string|null, model_name: string|null}>>}
   */
  async getTypes() {
    const data = await this._request('/api/types');
    return data.types;
  }

  /**
   * Fetch SHACL property shapes for a specific type.
   * GET /api/shapes/{typeIri}
   *
   * @param {string} typeIri - Full IRI of the type (e.g. "urn:sempkm:model:basic-pkm:Note")
   * @returns {Promise<{shape_iri: string, target_class: string, label: string, groups: Array, properties: Array, helptext: string|null}>}
   */
  async getShape(typeIri) {
    return this._request(`/api/shapes/${encodeURIComponent(typeIri)}`);
  }

  /**
   * Create a new object via the commands endpoint.
   * POST /api/commands with {command: "object.create", params}
   *
   * @param {Object} params - Object creation parameters
   * @param {string} params.type - RDF type IRI or local name
   * @param {string} [params.slug] - Optional human-readable slug
   * @param {Object} [params.properties] - Predicate → value pairs
   * @returns {Promise<{results: Array<{iri: string, event_iri: string, command: string}>, event_iri: string, timestamp: string}>}
   */
  async createObject(params) {
    return this._request('/api/commands', {
      method: 'POST',
      body: JSON.stringify({
        command: 'object.create',
        params,
      }),
    });
  }

  /**
   * Create a typed edge between objects via the commands endpoint.
   * POST /api/commands with {command: "edge.create", params}
   *
   * @param {Object} params - Edge creation parameters
   * @param {string} params.source - Source object IRI
   * @param {string} params.target - Target object IRI
   * @param {string} params.predicate - Relationship type IRI
   * @param {Object} [params.properties] - Optional edge annotations
   * @returns {Promise<{results: Array, event_iri: string, timestamp: string}>}
   */
  async createEdge(params) {
    return this._request('/api/commands', {
      method: 'POST',
      body: JSON.stringify({
        command: 'edge.create',
        params,
      }),
    });
  }

  /**
   * Search for related objects by page context (title, keywords).
   * POST /api/context-query
   *
   * @param {string} query - Search text used as both title and keywords
   * @returns {Promise<Array<{iri: string, label: string, type_iri: string|null, type_label: string|null, match_type: string, snippet: string|null}>>}
   */
  async searchObjects(query) {
    const data = await this._request('/api/context-query', {
      method: 'POST',
      body: JSON.stringify({
        title: query,
        keywords: query,
      }),
    });
    return data.results;
  }

  /**
   * Query for objects related to the current page context.
   * Sends each field separately so the backend can weight them independently.
   * POST /api/context-query
   *
   * @param {Object} params - Context fields (at least one required by backend)
   * @param {string} [params.url] - Page URL to match against schema:url properties
   * @param {string} [params.title] - Page title for label/title matching
   * @param {string} [params.keywords] - Extracted keywords for broader matching
   * @returns {Promise<{results: Array<{iri: string, label: string, type_iri: string|null, type_label: string|null, match_type: string, snippet: string|null}>, total: number}>}
   */
  async contextQuery({ url, title, keywords } = {}) {
    const body = {};
    if (url) body.url = url;
    if (title) body.title = title;
    if (keywords) body.keywords = keywords;

    return this._request('/api/context-query', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }
}
