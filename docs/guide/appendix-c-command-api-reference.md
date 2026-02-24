# Appendix C: Command API Reference

This appendix provides a complete reference for the SemPKM Command API. All write operations go through a single endpoint: `POST /api/commands`. The API accepts either a single command object or an array of commands for atomic batch execution.

## Endpoint

```
POST /api/commands
Content-Type: application/json
```

**Authentication:** Requires an authenticated session with `owner` or `member` role.

**Batch semantics:** When an array of commands is submitted, all commands are committed atomically as a single event. If any command fails, none are applied.

## Request Format

### Single Command

```json
{
  "command": "object.create",
  "params": { ... }
}
```

### Batch (Array) of Commands

```json
[
  { "command": "object.create", "params": { ... } },
  { "command": "object.patch", "params": { ... } }
]
```

## Response Format

All successful responses return a `CommandResponse`:

```json
{
  "results": [
    {
      "iri": "https://example.org/data/Person/alice-chen",
      "event_iri": "urn:sempkm:event:2026-01-15T09:00:00.000Z:abc123",
      "command": "object.create"
    }
  ],
  "event_iri": "urn:sempkm:event:2026-01-15T09:00:00.000Z:abc123",
  "timestamp": "2026-01-15T09:00:00.000Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | One result per command in the request, in order. |
| `results[].iri` | string | The IRI of the created or modified resource. |
| `results[].event_iri` | string | The event graph IRI for this operation. |
| `results[].command` | string | The command type that was executed. |
| `event_iri` | string | The shared event graph IRI for the entire batch. |
| `timestamp` | string | ISO 8601 timestamp of the event. |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{ "error": "..." }` | Invalid request body, missing required fields, or malformed JSON. |
| 403 | `{ "error": "..." }` | Insufficient permissions (not authenticated, or wrong role). |
| 500 | `{ "error": "..." }` | Internal server error during command execution. |

---

## Command Types

### object.create

Creates a new RDF object with a minted IRI, a type triple, and property triples.

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | The RDF type local name (e.g., `"Person"`, `"Note"`, `"Project"`). Combined with `BASE_NAMESPACE` to form the full type IRI. |
| `slug` | string | No | Human-readable slug for the object IRI. If omitted, a UUID is generated. |
| `properties` | object | No | Key-value pairs of predicate-to-value mappings. Keys can be compact IRIs (e.g., `"dcterms:title"`), full IRIs, or bare local names. |

**Predicate Resolution:**

- Full IRIs (`http://...`, `https://...`, `urn:...`) are used as-is.
- Compact IRIs with known prefixes (`dcterms:title`, `foaf:name`, `schema:url`) are expanded using the system's common prefix mappings.
- Bare local names (`title`) are prefixed with `BASE_NAMESPACE`.

**Value Resolution:**

- Strings starting with `http://`, `https://`, or `urn:` are treated as IRI references.
- All other strings become RDF string literals.
- Numbers become typed numeric literals.
- Booleans become typed boolean literals.

**Example Request:**

```json
{
  "command": "object.create",
  "params": {
    "type": "Person",
    "slug": "alice-chen",
    "properties": {
      "foaf:name": "Alice Chen",
      "foaf:mbox": "alice@example.com",
      "schema:jobTitle": "Lead Developer",
      "schema:worksFor": "SemPKM Labs"
    }
  }
}
```

**Example Response:**

```json
{
  "results": [
    {
      "iri": "https://example.org/data/Person/alice-chen",
      "event_iri": "urn:sempkm:event:2026-01-15T09:00:00.000Z:a1b2c3",
      "command": "object.create"
    }
  ],
  "event_iri": "urn:sempkm:event:2026-01-15T09:00:00.000Z:a1b2c3",
  "timestamp": "2026-01-15T09:00:00.000Z"
}
```

---

### object.patch

Updates specified properties on an existing object. Only the listed properties are changed; all other properties remain untouched. For each property, the old value is deleted and the new value is inserted.

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iri` | string | Yes | The full IRI of the object to patch. |
| `properties` | object | Yes | Key-value pairs of predicate-to-new-value mappings. Same resolution rules as `object.create`. |

**Example Request:**

```json
{
  "command": "object.patch",
  "params": {
    "iri": "https://example.org/data/Person/alice-chen",
    "properties": {
      "schema:jobTitle": "Principal Architect",
      "schema:worksFor": "SemPKM Inc."
    }
  }
}
```

**Example Response:**

```json
{
  "results": [
    {
      "iri": "https://example.org/data/Person/alice-chen",
      "event_iri": "urn:sempkm:event:2026-02-10T14:30:00.000Z:d4e5f6",
      "command": "object.patch"
    }
  ],
  "event_iri": "urn:sempkm:event:2026-02-10T14:30:00.000Z:d4e5f6",
  "timestamp": "2026-02-10T14:30:00.000Z"
}
```

---

### body.set

Sets or replaces the Markdown body content of an object. Uses the `sempkm:body` predicate by default, but an alternative predicate can be specified (e.g., a model-specific body property like `bpkm:body`).

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iri` | string | Yes | The full IRI of the object. |
| `body` | string | Yes | The Markdown content to set as the body. |
| `predicate` | string | No | Override the body predicate. Defaults to `urn:sempkm:body`. If a model-specific predicate is provided, any leftover value under the canonical `sempkm:body` predicate is also cleaned up. |

**Example Request:**

```json
{
  "command": "body.set",
  "params": {
    "iri": "https://example.org/data/Note/architecture-decision",
    "body": "# Architecture Decision\n\nWe chose event sourcing for the persistence layer.\n\n## Key Points\n- Full audit trail\n- Temporal queries\n- Undo support"
  }
}
```

**Example Response:**

```json
{
  "results": [
    {
      "iri": "https://example.org/data/Note/architecture-decision",
      "event_iri": "urn:sempkm:event:2026-01-18T14:30:00.000Z:g7h8i9",
      "command": "body.set"
    }
  ],
  "event_iri": "urn:sempkm:event:2026-01-18T14:30:00.000Z:g7h8i9",
  "timestamp": "2026-01-18T14:30:00.000Z"
}
```

---

### edge.create

Creates a first-class edge resource with its own IRI. Edges represent typed relationships between objects and can carry optional annotation properties.

The edge resource stores:
- `rdf:type` as `sempkm:Edge`
- `sempkm:source` -- the source object IRI
- `sempkm:target` -- the target object IRI
- `sempkm:predicate` -- the relationship type IRI
- Any additional annotation properties

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | Full IRI of the source object. |
| `target` | string | Yes | Full IRI of the target object. |
| `predicate` | string | Yes | The relationship type. Can be a compact IRI (e.g., `"bpkm:hasParticipant"`) or full IRI. |
| `properties` | object | No | Optional annotation properties on the edge resource itself (e.g., a label, weight, or timestamp). |

**Example Request:**

```json
{
  "command": "edge.create",
  "params": {
    "source": "https://example.org/data/Project/sempkm-dev",
    "target": "https://example.org/data/Person/alice-chen",
    "predicate": "bpkm:hasParticipant",
    "properties": {
      "rdfs:label": "Lead Developer assignment"
    }
  }
}
```

**Example Response:**

```json
{
  "results": [
    {
      "iri": "https://example.org/data/edge/j0k1l2",
      "event_iri": "urn:sempkm:event:2026-01-15T09:05:00.000Z:m3n4o5",
      "command": "edge.create"
    }
  ],
  "event_iri": "urn:sempkm:event:2026-01-15T09:05:00.000Z:m3n4o5",
  "timestamp": "2026-01-15T09:05:00.000Z"
}
```

---

### edge.patch

Updates annotation properties on an existing edge resource. The structural properties (`source`, `target`, `predicate`) are immutable and cannot be changed after creation.

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iri` | string | Yes | The full IRI of the edge resource to patch. |
| `properties` | object | Yes | Key-value pairs of annotation properties to update. Same resolution rules as `object.patch`. |

**Example Request:**

```json
{
  "command": "edge.patch",
  "params": {
    "iri": "https://example.org/data/edge/j0k1l2",
    "properties": {
      "rdfs:label": "Architecture Lead assignment",
      "dcterms:modified": "2026-02-10T14:30:00Z"
    }
  }
}
```

**Example Response:**

```json
{
  "results": [
    {
      "iri": "https://example.org/data/edge/j0k1l2",
      "event_iri": "urn:sempkm:event:2026-02-10T14:35:00.000Z:p6q7r8",
      "command": "edge.patch"
    }
  ],
  "event_iri": "urn:sempkm:event:2026-02-10T14:35:00.000Z:p6q7r8",
  "timestamp": "2026-02-10T14:35:00.000Z"
}
```

---

## Batch Example

Create a Project, a Person, and link them together in a single atomic transaction:

```json
[
  {
    "command": "object.create",
    "params": {
      "type": "Project",
      "slug": "new-initiative",
      "properties": {
        "dcterms:title": "New Initiative",
        "urn:sempkm:model:basic-pkm:status": "active",
        "urn:sempkm:model:basic-pkm:priority": "high"
      }
    }
  },
  {
    "command": "object.create",
    "params": {
      "type": "Person",
      "slug": "dana-park",
      "properties": {
        "foaf:name": "Dana Park",
        "schema:jobTitle": "Project Manager"
      }
    }
  },
  {
    "command": "edge.create",
    "params": {
      "source": "https://example.org/data/Project/new-initiative",
      "target": "https://example.org/data/Person/dana-park",
      "predicate": "urn:sempkm:model:basic-pkm:hasParticipant"
    }
  }
]
```

All three commands share a single event graph and timestamp. If any one fails, none are applied.

## Common Prefix Mappings

These prefixes are recognized in compact IRIs throughout the Command API:

| Prefix    | Namespace                                      |
|-----------|------------------------------------------------|
| `rdf`     | `http://www.w3.org/1999/02/22-rdf-syntax-ns#`  |
| `rdfs`    | `http://www.w3.org/2000/01/rdf-schema#`         |
| `owl`     | `http://www.w3.org/2002/07/owl#`                |
| `xsd`     | `http://www.w3.org/2001/XMLSchema#`             |
| `sh`      | `http://www.w3.org/ns/shacl#`                   |
| `sempkm`  | `urn:sempkm:`                                   |
| `schema`  | `https://schema.org/`                           |
| `dcterms` | `http://purl.org/dc/terms/`                     |
| `skos`    | `http://www.w3.org/2004/02/skos/core#`          |
| `foaf`    | `http://xmlns.com/foaf/0.1/`                    |
| `prov`    | `http://www.w3.org/ns/prov#`                    |

> **Note:** Model-specific prefixes (like `bpkm:` for the Basic PKM model) are not included in the common prefix map. Use the full namespace IRI for model-specific properties (e.g., `urn:sempkm:model:basic-pkm:status` instead of `bpkm:status`).

## Webhook Events

After successful command execution, SemPKM dispatches webhook events for registered subscribers:

| Command | Webhook Event Type |
|---------|-------------------|
| `object.create` | `object.changed` |
| `object.patch` | `object.changed` |
| `body.set` | `object.changed` |
| `edge.create` | `edge.changed` |
| `edge.patch` | `edge.changed` |

Webhook payloads include the `event_iri`, `command` type, and `timestamp`.

## See Also

- [The Command API](17-command-api.md) -- conceptual guide to the command system
- [Webhooks](12-webhooks.md) -- configuring webhook integrations
- [The Data Model](16-data-model.md) -- how commands map to RDF triples and events
