# M048: Critical Bug Fixes

## Vision
Fix the showstopper bugs that make core features non-functional: broken view rendering, phantom save events, missing delete UI, absent creation timestamps, and Docker volume permission issues. After this milestone, the full CRUD cycle (create → edit → save → delete) works correctly with clean event logs, views render all objects, and Docker deploys succeed on fresh volumes.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Fix Table & Cards Views + Creation Timestamps | high | — | ✅ | Open Table View from explorer → objects listed with label, type, created, modified. Open Cards View → cards render. Create a new object → dcterms:created appears in the table. |
| S02 | Diff-Based Save — No Phantom Events | medium | — | ✅ | Open an object, change one property field, save. Check the event log — only the changed property appears. Change nothing and save — no event is created. |
| S03 | Object Delete UI | low | S01 | ✅ | Click delete button on object toolbar → confirmation dialog → object removed from explorer tree, views, and SPARQL. Also accessible via command palette 'Delete Object' command. |
| S04 | Docker Permissions + Model Loading Diagnosis | low | — | ⬜ | docker compose down -v && docker compose up --build -d succeeds on fresh volume. Install business-planning model → SPARQL query confirms all 33 NodeShapes loaded. |
