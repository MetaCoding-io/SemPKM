# Event Types (v1) — Minimal Taxonomy

SemPKM emits events internally for projections, validation, UI refresh, and optional webhooks.

v1 webhooks are intentionally simple and best-effort. This taxonomy is meant to keep payloads stable and automations consistent.

## Required fields (all events)
Each event includes:
- `id` (unique)
- `type` (one of the types below)
- `time` (timestamp)
- `commitId` (the commit/event-batch that caused it)
- `subject` (primary IRI affected, when applicable)
- `data` (event-specific payload)

## Minimal event types (v1)
- `object.changed`
  - emitted on object create/update/delete (tombstone)
- `body.changed`
  - emitted when an object's markdown body version changes
- `edge.changed`
  - emitted when an edge resource is created/updated/deleted
- `validation.completed`
  - emitted when async validation completes for a commit
- `publish.completed`
  - emitted when a publish/export job completes successfully
- `publish.failed`
  - emitted when a publish/export job fails

## Suggested v1 payload shape
- `object.changed`:
  - `action`: `created|updated|deleted`
  - `types` (optional)
  - `changedPredicates` (optional list)
- `body.changed`:
  - `bodyVersionId` (optional)
- `edge.changed`:
  - `action`: `created|updated|deleted`
  - `edgeId`
  - `subjectIri` / `predicateIri` / `objectIri` (optional convenience)
- `validation.completed`:
  - `conforms` (boolean)
  - `violationCount`, `warningCount` (optional summaries)
  - `reportGraphId` (optional pointer)
- `publish.*`:
  - `target`: `activitypub|solid|export`
  - `status` / `error` (for failed)

## Notes
- Delivery semantics for webhooks remain best-effort in v1.
- Advanced delivery, signing, DLQ, and strict ordering are deferred to v3.