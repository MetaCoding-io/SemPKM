# Chapter 31: API Surface

The **API surface** is a set of JSON endpoints that external clients — browser
extensions, mobile apps, CLI tools, and integrations — use to interact with a
SemPKM instance programmatically. These endpoints let you discover the instance,
query available types and shapes, and find related objects by URL or keywords.

The API surface is distinct from the [Command API](17-command-api.md) (which
handles writes) and the [SPARQL endpoint](18-sparql-endpoint.md) (which handles
ad-hoc queries). The API surface provides structured, opinionated read endpoints
designed for common integration patterns.

---

## Authentication

All API surface endpoints require authentication. Two methods are supported:

### Session Cookies (Web UI)

When you are logged into the SemPKM web interface, your browser automatically
sends a `sempkm_session` cookie with every request. No additional configuration
is needed — the API surface accepts this cookie for authentication.

This method is primarily used by htmx-driven UI interactions and browser-based
JavaScript that runs on the same origin as the SemPKM instance.

### Bearer API Tokens (External Clients)

External clients (browser extensions, mobile apps, scripts) authenticate via
a Bearer token in the `Authorization` header:

```
Authorization: Bearer your-api-token-here
```

**How to generate a token:**

1. Log in to the SemPKM web interface.
2. Navigate to **Settings** (gear icon in the sidebar or via the command palette).
3. Under the **API Keys** section, click **Generate New Key**.
4. Copy the token immediately — it is only shown once.
5. Store the token securely (e.g., in your extension's encrypted storage or
   a keychain).

**Auth resolution order:** If both a session cookie and a Bearer token are
present, the session cookie takes priority. If the cookie is invalid or absent,
the Bearer token is tried next. If neither succeeds, the endpoint returns
HTTP 401.

---

## Instance Discovery

```
GET /.well-known/sempkm
```

The discovery endpoint is the first endpoint an external client should call. It
returns a JSON document describing the instance: its version, available
endpoints, supported authentication methods, and enabled capabilities.

### Example Request

```bash
curl -H "Authorization: Bearer $TOKEN" \
     https://sempkm.example.com/.well-known/sempkm
```

### Example Response

```json
{
  "version": "0.1.0",
  "endpoints": {
    "types": "/api/types",
    "shapes": "/api/shapes/{type_iri}",
    "context_query": "/api/context-query",
    "sparql": "/api/sparql",
    "commands": "/api/commands"
  },
  "auth": {
    "session": true,
    "api_key": true,
    "indieauth": "/auth/authorize"
  },
  "capabilities": [
    "types",
    "shapes",
    "context-query",
    "sparql",
    "commands"
  ]
}
```

### Fields

| Field            | Type   | Description                                                             |
|------------------|--------|-------------------------------------------------------------------------|
| `version`        | string | SemPKM application version                                             |
| `endpoints`      | object | Map of endpoint names to their URL paths                                |
| `auth`           | object | Supported auth methods (`session`, `api_key`, `indieauth`)              |
| `capabilities`   | array  | List of enabled capabilities on this instance                           |

Use the `endpoints` map to discover URLs dynamically rather than hardcoding
paths. This allows the API to evolve without breaking existing clients.

---

## Available Types

```
GET /api/types
```

Returns all types defined by installed Mental Models. Each type includes its IRI,
human-readable label, Lucide icon name, icon color, and the model it belongs to.

Use this endpoint to populate type pickers, display object type badges, or
discover which types are available before creating objects via the Command API.

### Example Request

```bash
curl -H "Authorization: Bearer $TOKEN" \
     https://sempkm.example.com/api/types
```

### Example Response

```json
{
  "types": [
    {
      "iri": "urn:sempkm:model:basic-pkm:Note",
      "label": "Note",
      "icon": "sticky-note",
      "icon_color": "#f59e0b",
      "model_id": "basic-pkm",
      "model_name": "Basic PKM"
    },
    {
      "iri": "urn:sempkm:model:basic-pkm:Project",
      "label": "Project",
      "icon": "folder-kanban",
      "icon_color": "#3b82f6",
      "model_id": "basic-pkm",
      "model_name": "Basic PKM"
    }
  ]
}
```

### Fields

| Field          | Type         | Description                                              |
|----------------|--------------|----------------------------------------------------------|
| `iri`          | string       | The type's full IRI (globally unique identifier)         |
| `label`        | string       | Human-readable type name                                 |
| `icon`         | string\|null | Lucide icon name (e.g., `"sticky-note"`, `"user"`)       |
| `icon_color`   | string\|null | CSS color for the icon (e.g., `"#f59e0b"`)               |
| `model_id`     | string\|null | ID of the Mental Model that defines this type            |
| `model_name`   | string\|null | Human-readable name of the Mental Model                  |

---

## SHACL Shapes

```
GET /api/shapes/{type_iri}
```

Returns the SHACL property shapes for a specific type — the form structure,
field constraints, and validation rules needed to build a dynamic editing
interface.

### URL Encoding

The `{type_iri}` parameter is a full IRI and must be URL-encoded when it
contains special characters. For example:

```
GET /api/shapes/urn:sempkm:model:basic-pkm:Note
```

Most IRIs using the `urn:` scheme do not require encoding, but HTTP URLs
used as type IRIs must encode colons and slashes:

```
GET /api/shapes/https%3A%2F%2Fexample.org%2Fontology%2FMyType
```

### Example Request

```bash
curl -H "Authorization: Bearer $TOKEN" \
     https://sempkm.example.com/api/shapes/urn:sempkm:model:basic-pkm:Note
```

### Example Response

```json
{
  "shape_iri": "urn:sempkm:model:basic-pkm:NoteShape",
  "target_class": "urn:sempkm:model:basic-pkm:Note",
  "label": "Note",
  "helptext": "A freeform note for capturing ideas and information.",
  "groups": [
    {
      "iri": "urn:sempkm:model:basic-pkm:CoreGroup",
      "label": "Core Properties",
      "order": 1.0
    }
  ],
  "properties": [
    {
      "path": "http://purl.org/dc/terms/title",
      "name": "Title",
      "datatype": "http://www.w3.org/2001/XMLSchema#string",
      "target_class": null,
      "order": 1.0,
      "group": "urn:sempkm:model:basic-pkm:CoreGroup",
      "min_count": 1,
      "max_count": 1,
      "in_values": [],
      "default_value": null,
      "description": "The title of the note",
      "helptext": null
    },
    {
      "path": "urn:sempkm:model:basic-pkm:status",
      "name": "Status",
      "datatype": null,
      "target_class": null,
      "order": 2.0,
      "group": "urn:sempkm:model:basic-pkm:CoreGroup",
      "min_count": 0,
      "max_count": 1,
      "in_values": ["active", "archived"],
      "default_value": "active",
      "description": "Current status of the note",
      "helptext": "Set to 'archived' to hide from default views."
    }
  ]
}
```

### Fields

**Shape (top-level):**

| Field           | Type         | Description                                     |
|-----------------|--------------|-------------------------------------------------|
| `shape_iri`     | string       | IRI of the SHACL node shape                     |
| `target_class`  | string       | The type IRI this shape describes                |
| `label`         | string       | Human-readable shape name                       |
| `helptext`      | string\|null | Help text for the type as a whole                |
| `groups`        | array        | Property group definitions (form sections)       |
| `properties`    | array        | Property shape definitions (form fields)         |

**Property groups:**

| Field    | Type   | Description                                    |
|----------|--------|------------------------------------------------|
| `iri`    | string | Group IRI                                      |
| `label`  | string | Group heading shown in the form                |
| `order`  | number | Sort order (lower values appear first)         |

**Properties:**

| Field          | Type         | Description                                         |
|----------------|--------------|-----------------------------------------------------|
| `path`         | string       | Property IRI (the RDF predicate)                    |
| `name`         | string       | Human-readable field label                          |
| `datatype`     | string\|null | XSD datatype IRI (e.g., `xsd:string`, `xsd:date`)  |
| `target_class` | string\|null | For object properties: the expected target type IRI |
| `order`        | number       | Sort order within the group                         |
| `group`        | string\|null | IRI of the property group this field belongs to     |
| `min_count`    | integer      | Minimum cardinality (0 = optional, 1+ = required)  |
| `max_count`    | integer\|null| Maximum cardinality (null = unlimited)              |
| `in_values`    | array        | Allowed values for dropdown fields (empty = free)   |
| `default_value`| string\|null | Default value for new objects                       |
| `description`  | string\|null | Short description of the property                   |
| `helptext`     | string\|null | Extended help text shown on hover or in tooltips    |

### Error: Type Not Found

If no shape exists for the given type IRI, the endpoint returns HTTP 404:

```json
{
  "detail": "No shape found for type: urn:sempkm:model:example:Unknown"
}
```

---

## Context Query

```
POST /api/context-query
```

The context query endpoint finds objects in your knowledge graph that are related
to a given page context. This is the primary endpoint for browser extensions —
send the current page's URL, title, and/or keywords, and receive matching objects
from your SemPKM instance.

### Request Body

```json
{
  "url": "https://example.com/article/semantic-web",
  "title": "Introduction to the Semantic Web",
  "keywords": "RDF SPARQL linked data"
}
```

All fields are optional, but **at least one** must be provided. If the body is
empty or all fields are null, the endpoint returns HTTP 400.

| Field      | Type         | Description                                             |
|------------|--------------|---------------------------------------------------------|
| `url`      | string\|null | URL to match exactly against object property values     |
| `title`    | string\|null | Page title — used for full-text keyword search          |
| `keywords` | string\|null | Additional keywords for full-text search                |

### Matching Behavior

The endpoint uses two matching strategies, run in parallel and deduplicated:

1. **URL matching (SPARQL):** Searches for any object that has a property value
   exactly equal to the given URL string. This catches objects that reference
   the URL as a source, citation, or link. Results have `match_type: "url"`.

2. **Keyword matching (LuceneSail FTS):** Combines the `title` and `keywords`
   fields into a search string and runs full-text search via LuceneSail. Results
   have `match_type: "keyword"` (or `"title"` if only `title` was provided
   without `keywords`).

If the same object is found by both URL match and keyword match, the URL match
takes priority (first-match-wins deduplication).

Results are enriched with labels (via the label service) and types (via a SPARQL
`rdf:type` query).

### Example Request

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "keywords": "semantic web"}' \
     https://sempkm.example.com/api/context-query
```

### Example Response

```json
{
  "results": [
    {
      "iri": "urn:sempkm:data:Note/semantic-web-overview",
      "label": "Semantic Web Overview",
      "type_iri": "urn:sempkm:model:basic-pkm:Note",
      "type_label": "Note",
      "match_type": "url",
      "snippet": null
    },
    {
      "iri": "urn:sempkm:data:Concept/linked-data",
      "label": "Linked Data",
      "type_iri": "urn:sempkm:model:basic-pkm:Concept",
      "type_label": "Concept",
      "match_type": "keyword",
      "snippet": "...linked data principles and the semantic web..."
    }
  ],
  "total": 2
}
```

### Response Fields

| Field        | Type         | Description                                       |
|--------------|--------------|---------------------------------------------------|
| `results`    | array        | Array of matching objects                         |
| `total`      | integer      | Total number of results                           |

**Each result:**

| Field        | Type         | Description                                         |
|--------------|--------------|-----------------------------------------------------|
| `iri`        | string       | Object's IRI                                        |
| `label`      | string       | Human-readable label (falls back to IRI if unknown) |
| `type_iri`   | string\|null | Type IRI of the object (if resolved)                |
| `type_label` | string\|null | Human-readable type label (if resolved)             |
| `match_type` | string       | How the object was found: `"url"`, `"keyword"`, or `"title"` |
| `snippet`    | string\|null | Text snippet from FTS match (null for URL matches)  |

### Empty Results

When no objects match the query, the endpoint returns HTTP 200 with an empty
results array — not HTTP 404:

```json
{
  "results": [],
  "total": 0
}
```

### Validation Error

If the request body is empty or all fields are null:

```json
HTTP 400

{
  "detail": "At least one of url, title, or keywords is required"
}
```

### Graceful Degradation

Each matching stage (URL match, keyword match, label resolution, type resolution)
is independently fault-tolerant. If SPARQL fails, keyword matching still runs.
If full-text search fails, URL matches are still returned. Partial results are
always returned rather than failing the entire request. Failures are logged
server-side at WARNING level.

---

## Cross-Origin Access (CORS)

Browser extensions that make cross-origin requests to your SemPKM instance need
proper CORS headers. How CORS is handled depends on your deployment:

**Reverse proxy (recommended):** Configure your reverse proxy (nginx, Caddy,
Traefik) to add `Access-Control-Allow-Origin` and related headers for the
API surface routes. For browser extensions that use a unique origin, use
`Access-Control-Allow-Origin: *` since extensions do not send cookies by
default (they use Bearer tokens instead).

Example nginx configuration for the API surface:

```nginx
location ~ ^/(\.well-known/sempkm|api/) {
    # CORS for browser extensions
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

    proxy_pass http://backend:8000;
}
```

**Browser extensions:** Extensions using Manifest V3 typically do not need CORS
at all — they can use the `host_permissions` field in `manifest.json` to make
requests to the SemPKM instance directly. Only extensions that make requests
from content scripts (running in the page's origin) need CORS headers.

---

## Error Responses

All API surface endpoints follow a consistent error format. Errors return a JSON
body with a `detail` field:

```json
{
  "detail": "Human-readable error message"
}
```

### Standard Status Codes

| Code | Meaning       | When                                                       |
|------|---------------|------------------------------------------------------------|
| 400  | Bad Request   | Missing required fields (e.g., empty context-query body)   |
| 401  | Unauthorized  | No session cookie or Bearer token, or token is invalid     |
| 403  | Forbidden     | Authenticated but insufficient permissions                 |
| 404  | Not Found     | Resource not found (e.g., no shape for a type IRI)         |
| 500  | Server Error  | Unexpected error (e.g., triplestore unavailable)           |

### Example: Unauthenticated Request

```bash
curl -i https://sempkm.example.com/api/types
```

```
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"detail": "Not authenticated"}
```

### Example: Invalid API Token

```bash
curl -i -H "Authorization: Bearer invalid-token" \
     https://sempkm.example.com/api/types
```

```
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"detail": "Invalid or expired API token"}
```

---

## Quick Reference

| Endpoint                       | Method | Purpose                                  |
|--------------------------------|--------|------------------------------------------|
| `/.well-known/sempkm`         | GET    | Instance discovery                       |
| `/api/types`                   | GET    | List available types                     |
| `/api/shapes/{type_iri}`       | GET    | Get form structure for a type            |
| `/api/context-query`           | POST   | Find related objects by URL/keywords     |

---

**Previous:** [Chapter 30: Workspace Personas](30-personas.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
