# Projection Refresh Semantics (v1)

This document defines when and how SemPKM updates the virtual filesystem projection.

## Scope (v1)
- Projection is **read-only** from the perspective of external tools.
- SemPKM updates the projection as a **derived artifact** from the event log + current projections.

## Update strategy (v1 default)
- **Push-based**: SemPKM writes/updates files on commit.
- **Asynchronous**: projection updates run in a background worker after the commit is accepted (non-blocking).

## Consistency contract
- Projections are **eventually consistent** with the canonical event log.
- Target: updates should appear within a few seconds under normal operation.
- SemPKM may expose UI indicators such as:
  - last projected time per object
  - last projected commitId/version

## Granularity and churn minimization
On each commit, SemPKM updates only the minimum set of files required:

- If an object's body changes:
  - Update `X.md` (body)
  - Update `X.meta.json` (generatedAt / projection metadata)
- If object properties change:
  - Update `X.meta.json`
- If edges are created/updated/deleted:
  - Update `X.edges.json` for the focus object
  - Update corresponding other endpoint’s `Y.edges.json` if direction=in/out lists include both ends

No global indices are generated in v1.

## File write behavior
- Updates are atomic per file where possible (write temp + rename).
- SemPKM should avoid rewriting unchanged content to reduce filesystem watcher noise (e.g., Obsidian).