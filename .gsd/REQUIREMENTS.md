# Requirements

This file is the explicit capability and coverage contract for the project.

## Validated

### R001 — Non-object-contextual panels (inbox, collaboration) lazy-load on reveal rather than on page load — use hx-trigger="revealed" instead of hx-trigger="load"
- Class: non-functional
- Status: validated
- Description: Non-object-contextual panels (inbox, collaboration) lazy-load on reveal rather than on page load — use hx-trigger="revealed" instead of hx-trigger="load"
- Why it matters: Inbox and collaboration panels fire HTTP requests on every page load even when collapsed, adding unnecessary server load and competing with object-tab requests for backend resources
- Source: M049
- Primary owning slice: M049/S03
- Supporting slices: M049/S01
- Validation: Both inbox_panel.html and collaboration_panel.html changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms no load triggers remain in either file. HTTP requests fire only when panels enter viewport via IntersectionObserver. Validated in M049/S03/T03.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | non-functional | validated | M049/S03 | M049/S01 | Both inbox_panel.html and collaboration_panel.html changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms no load triggers remain in either file. HTTP requests fire only when panels enter viewport via IntersectionObserver. Validated in M049/S03/T03. |

## Coverage Summary

- Active requirements: 0
- Mapped to slices: 0
- Validated: 1 (R001)
- Unmapped active requirements: 0
