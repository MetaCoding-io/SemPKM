# Chapter 17: The Command API

All writes in SemPKM flow through a single endpoint: `POST /api/commands`. Whether
you click Save in the workspace or send a request from a script, the same command
pipeline processes the change, creates an immutable event, and updates the current
state graph atomically.

This chapter covers how to use the Command API for scripting, automation, and
integration. You will learn the available commands, their parameters, how batching
works, and how to authenticate.

---

## Overview

The Command API follows a simple pattern:

1. Send a `POST` request to `/api/commands` with a JSON body.
2. The body contains a `command` field (the discriminator) and a `params` object.
3. All commands in the request execute atomically -- they share a single event
   and transaction. If any command fails, none are applied.
4. The response contains a `results` array, the shared `event_iri`, and a
   `timestamp`.

### Single Command

```json
{
  "command": "object.create",
  "params": {
    "type": "Note",
    "slug": "standup-notes",
    "properties": {
      "rdfs:label": "Standup Notes"
    }
  }
}
```

### Batch Commands

Send an array of commands to execute them all in a single atomic transaction:

```json
[
  {
    "command": "object.create",
    "params": {
      "type": "Note",
      "slug": "standup-notes",
      "properties": {
        "rdfs:label": "Standup Notes"
      }
    }
  },
  {
    "command": "body.set",
    "params": {
      "iri": "https://example.org/data/Note/standup-notes",
      "body": "# Standup Notes\n\nDaily standup log."
    }
  }
]
```

All commands in a batch share a single event graph. If any command fails,
the entire batch is rolled back.

---

## Command Reference

### `object.create`

Creates a new object with a minted IRI, an `rdf:type` triple, and optional
property triples.

**Parameters:**

| Parameter    | Type              | Required | Description                                         |
|--------------|-------------------|----------|-----------------------------------------------------|
| `type`       | string            | Yes      | The type local name (e.g., `"Note"`, `"Person"`)     |
| `slug`       | string or null    | No       | Human-readable slug for the IRI; UUID if omitted      |
| `properties` | object            | No       | Predicate-value pairs (compact IRI or full IRI keys)  |

**IRI minting:** The new object's IRI follows the pattern
`{base_namespace}/{type}/{slug-or-uuid}`. For example, with the default
namespace and `type: "Note"`, `slug: "standup-notes"`:

```
https://example.org/data/Note/standup-notes
```

**Property keys** can use compact IRIs (`rdfs:label`, `schema:dateCreated`) or
full IRIs (`http://xmlns.com/foaf/0.1/name`). SemPKM resolves compact IRIs using
the built-in prefix registry. Bare local names (no colon) are treated as terms
under the base data namespace.

**Property values** are interpreted as follows:

- Strings starting with `http://`, `https://`, or `urn:` become IRI references.
- Other strings become RDF string literals.
- Numbers become typed literals (`xsd:integer` or `xsd:double`).
- Booleans become `xsd:boolean` literals.

**Example:**

```json
{
  "command": "object.create",
  "params": {
    "type": "Person",
    "slug": "alice",
    "properties": {
      "rdfs:label": "Alice Johnson",
      "schema:email": "alice@example.com"
    }
  }
}
```

---

### `object.patch`

Updates one or more properties on an existing object. Only the specified properties
are changed; all other properties remain untouched. For each property, the old
value is deleted and the new value is inserted.

**Parameters:**

| Parameter    | Type   | Required | Description                                           |
|--------------|--------|----------|-------------------------------------------------------|
| `iri`        | string | Yes      | The full IRI of the object to patch                    |
| `properties` | object | Yes      | Predicate-value pairs to update (same format as create) |

**Example -- rename a Project:**

```json
{
  "command": "object.patch",
  "params": {
    "iri": "https://example.org/data/Project/q1-planning",
    "properties": {
      "rdfs:label": "Q1 Planning 2026"
    }
  }
}
```

> **Note:** `object.patch` replaces the entire value for each specified
> predicate. If an object has multiple values for a predicate and you patch it,
> all existing values for that predicate are removed and replaced with the
> single new value.

---

### `body.set`

Sets or replaces the Markdown body content of an object. The body is stored as
a string literal under the `sempkm:body` predicate (or a model-specific body
predicate if overridden).

**Parameters:**

| Parameter   | Type           | Required | Description                                         |
|-------------|----------------|----------|-----------------------------------------------------|
| `iri`       | string         | Yes      | The full IRI of the object                            |
| `body`      | string         | Yes      | The Markdown content                                  |
| `predicate` | string or null | No       | Override the body predicate (defaults to `sempkm:body`) |

**Example:**

```json
{
  "command": "body.set",
  "params": {
    "iri": "https://example.org/data/Note/standup-notes",
    "body": "# Standup Notes\n\n## 2026-02-24\n\n- Completed API docs\n- Started testing"
  }
}
```

If the object already has a body, the old body is deleted and replaced. If a
`predicate` is specified and it differs from the canonical `sempkm:body`, any
leftover value under `sempkm:body` is also cleaned up to avoid duplication.

---

### `edge.create`

Creates a typed relationship between two objects. Edges in SemPKM are first-class
resources with their own IRIs, enabling annotation properties (e.g., weight,
notes, timestamps) on the relationship itself.

**Parameters:**

| Parameter    | Type   | Required | Description                                              |
|--------------|--------|----------|----------------------------------------------------------|
| `source`     | string | Yes      | The source object IRI                                     |
| `target`     | string | Yes      | The target object IRI                                     |
| `predicate`  | string | Yes      | The relationship type (compact or full IRI)                |
| `properties` | object | No       | Optional annotation properties on the edge resource        |

The edge resource is created with:

- `rdf:type sempkm:Edge`
- `sempkm:source` pointing to the source object
- `sempkm:target` pointing to the target object
- `sempkm:predicate` storing the relationship type IRI
- Any additional annotation properties

**Example -- link a Person to a Project:**

```json
{
  "command": "edge.create",
  "params": {
    "source": "https://example.org/data/Person/alice",
    "target": "https://example.org/data/Project/q1-planning",
    "predicate": "schema:memberOf",
    "properties": {
      "rdfs:label": "Team Lead",
      "schema:startDate": "2026-01-15"
    }
  }
}
```

> **Tip:** The `source`, `target`, and `predicate` of an edge are immutable after
> creation. To change a relationship's direction or type, delete the edge (undo
> the `edge.create` event) and create a new one.

---

### `edge.patch`

Updates annotation properties on an existing edge resource. Cannot modify the
source, target, or predicate -- those are immutable.

**Parameters:**

| Parameter    | Type   | Required | Description                                     |
|--------------|--------|----------|-------------------------------------------------|
| `iri`        | string | Yes      | The edge resource IRI                             |
| `properties` | object | Yes      | Annotation properties to update                   |

**Example:**

```json
{
  "command": "edge.patch",
  "params": {
    "iri": "https://example.org/data/Edge/550e8400-e29b-41d4-a716-446655440000",
    "properties": {
      "rdfs:label": "Project Lead"
    }
  }
}
```

---

## Response Format

A successful response (HTTP 200) returns a `CommandResponse` with three fields:

```json
{
  "results": [
    {
      "iri": "https://example.org/data/Note/standup-notes",
      "event_iri": "urn:sempkm:event:a1b2c3d4-...",
      "command": "object.create"
    }
  ],
  "event_iri": "urn:sempkm:event:a1b2c3d4-...",
  "timestamp": "2026-02-24T14:32:07.123456+00:00"
}
```

| Field       | Description                                                   |
|-------------|---------------------------------------------------------------|
| `results`   | Array with one entry per command: the affected IRI, event IRI, and command type |
| `event_iri` | The shared event graph IRI (same for all commands in a batch)  |
| `timestamp` | ISO 8601 UTC timestamp of the commit                           |

### Error Responses

| HTTP Status | Meaning                                                    |
|-------------|-----------------------------------------------------------|
| 400         | Invalid request body, malformed JSON, or bad command params |
| 401         | Not authenticated (missing or expired session)              |
| 403         | Insufficient role (requires `owner` or `member`)            |
| 500         | Internal error (transaction rolled back)                    |

Error bodies include an `error` field with a human-readable message:

```json
{
  "error": "Unknown command type: object.delete"
}
```

---

## Authentication

The Command API uses the same session cookie authentication as the rest of
SemPKM. Only users with the `owner` or `member` role can execute commands.

### Session Cookie

The session cookie is named `sempkm_session` and is set as an httpOnly cookie
after login. In a browser, this cookie is sent automatically with every request.

### Obtaining a Session for Scripting

To use the Command API from scripts or external tools, you need a session token.
The recommended approach:

1. **Request a magic link.** Send a POST to `/api/auth/magic-link`:

   ```bash
   curl -X POST http://localhost:8000/api/auth/magic-link \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com"}'
   ```

   If SMTP is not configured (typical for local instances), the response includes
   the token directly. Otherwise, check your email or the server terminal log.

2. **Verify the token.** Send a POST to `/api/auth/verify` with the token. The
   response sets the `sempkm_session` cookie:

   ```bash
   curl -X POST http://localhost:8000/api/auth/verify \
     -H "Content-Type: application/json" \
     -d '{"token": "the-magic-link-token"}' \
     -c cookies.txt
   ```

3. **Use the cookie in subsequent requests:**

   ```bash
   curl -X POST http://localhost:8000/api/commands \
     -H "Content-Type: application/json" \
     -b cookies.txt \
     -d '{
       "command": "object.create",
       "params": {
         "type": "Note",
         "slug": "scripted-note",
         "properties": {
           "rdfs:label": "Created via API"
         }
       }
     }'
   ```

> **Tip:** Sessions use a sliding window expiration. If you use the session
> regularly, it stays valid. The session is extended when it passes the midpoint
> of its configured lifetime.

---

## Example Workflows

### Create an Object and Set Its Body

Use a batch to create a Note and set its Markdown body in a single atomic
operation:

```bash
curl -X POST http://localhost:8000/api/commands \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[
    {
      "command": "object.create",
      "params": {
        "type": "Note",
        "slug": "weekly-review",
        "properties": {
          "rdfs:label": "Weekly Review",
          "schema:dateCreated": "2026-02-24"
        }
      }
    },
    {
      "command": "body.set",
      "params": {
        "iri": "https://example.org/data/Note/weekly-review",
        "body": "# Weekly Review\n\n## Accomplishments\n\n- Shipped v2.0\n\n## Next Week\n\n- Plan v2.1"
      }
    }
  ]'
```

### Create Two Objects and Link Them

Create a Person and a Project, then create an edge between them -- all in a
single transaction:

```bash
curl -X POST http://localhost:8000/api/commands \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[
    {
      "command": "object.create",
      "params": {
        "type": "Person",
        "slug": "bob",
        "properties": { "rdfs:label": "Bob Smith" }
      }
    },
    {
      "command": "object.create",
      "params": {
        "type": "Project",
        "slug": "website-redesign",
        "properties": { "rdfs:label": "Website Redesign" }
      }
    },
    {
      "command": "edge.create",
      "params": {
        "source": "https://example.org/data/Person/bob",
        "target": "https://example.org/data/Project/website-redesign",
        "predicate": "schema:memberOf"
      }
    }
  ]'
```

### Update a Property

Change the label of an existing Concept:

```bash
curl -X POST http://localhost:8000/api/commands \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "command": "object.patch",
    "params": {
      "iri": "https://example.org/data/Concept/event-sourcing",
      "properties": {
        "rdfs:label": "Event Sourcing (CQRS Pattern)"
      }
    }
  }'
```

---

## Next Steps

The Command API is for writing data. To read and query your data programmatically,
continue to [The SPARQL Endpoint](18-sparql-endpoint.md).
