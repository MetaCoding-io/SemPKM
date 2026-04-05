# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R001 — Non-object-contextual panels (inbox, collaboration) lazy-load on reveal rather than on page load — use hx-trigger="revealed" instead of hx-trigger="load"
- Class: non-functional
- Status: active
- Description: Non-object-contextual panels (inbox, collaboration) lazy-load on reveal rather than on page load — use hx-trigger="revealed" instead of hx-trigger="load"
- Why it matters: Inbox and collaboration panels fire HTTP requests on every page load even when collapsed, adding unnecessary server load and competing with object-tab requests for backend resources
- Source: M049
- Primary owning slice: M049/S03
- Supporting slices: M049/S01
- Validation: Browser Network tab shows no inbox/collaboration requests on page load. Requests fire only when panels are expanded.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | non-functional | active | M049/S03 | M049/S01 | Browser Network tab shows no inbox/collaboration requests on page load. Requests fire only when panels are expanded. |

## Coverage Summary

- Active requirements: 1
- Mapped to slices: 1
- Validated: 0
- Unmapped active requirements: 0
