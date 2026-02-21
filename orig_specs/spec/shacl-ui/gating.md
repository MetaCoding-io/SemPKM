# SHACL Gating Policy (v1)

This document defines how SHACL validation severities affect operations in SemPKM.

## Validation mode
- Validation is **asynchronous** (non-blocking).
- Validation results are persisted per commit (immutable reports) and indexed into a current diagnostics view.

## Severity handling
- **Violations**: treated as structural non-conformance
- **Warnings**: guidance; not blocking in v1
- **Info**: optional guidance; not blocking in v1

## Conformance-required operations (blocked by Violations)
If an object (or the relevant publish scope) has any SHACL **Violations**, SemPKM blocks operations that claim conformance, including:

- ActivityPub publish
- SOLID publish/export
- Any export/snapshot operation explicitly labeled as "conformant"

## Non-conformance-required operations (not blocked)
Violations do NOT block normal usage:
- editing properties or body
- viewing dashboards and views
- filesystem projection generation
- webhook notifications

## Future
v2+ may support per-user or per-workspace overrides, policy profiles, and more granular gating rules.