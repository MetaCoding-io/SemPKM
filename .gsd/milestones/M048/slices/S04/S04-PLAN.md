# S04: Docker Permissions + Model Loading Diagnosis

**Goal:** Add backend Docker entrypoint script that fixes volume permissions idempotently, and diagnose/fix the model loading issue where not all shapes load.
**Demo:** After this: docker compose down -v && docker compose up --build -d succeeds on fresh volume. Install business-planning model → SPARQL query confirms all 33 NodeShapes loaded.

## Tasks
