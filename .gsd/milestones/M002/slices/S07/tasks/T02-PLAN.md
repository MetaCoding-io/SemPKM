---
estimated_steps: 5
estimated_files: 2
---

# T02: Import Ideaverse vault and verify wiki-links and frontmatter

**Slice:** S07 — Obsidian Ideaverse Import
**Milestone:** M002

## Description

User-driven validation of the full Obsidian import pipeline with the real Ideaverse Pro 2.5 vault (905 notes). This is the integration proof for OBSI-08, OBSI-09, and OBSI-10. The agent drives the import wizard UI, maps type groups and frontmatter, executes the import, then verifies that wiki-links became edges and frontmatter became properties in the workspace. Any bugs discovered during import are fixed inline.

Per D006: this is a manual user-driven import, not an automated E2E test. The agent performs the import and records results. The user confirms results in UAT sign-off.

## Steps

1. Ensure Docker stack is running with T01 bug fixes applied (rebuild backend if needed: `docker compose up -d --build backend`).
2. Navigate to the import wizard at `/browser/import`. Upload `Ideaverse Pro 2.5.zip`. Wait for scan to complete. Verify scan results show ~905 markdown files (minus 3 empty-stem files = ~902), ~30+ type groups from folder-based detection, and `__MACOSX` entries are NOT counted.
3. Map type groups to SHACL types in the wizard UI. Most folder groups → Note or Concept. Person-related groups → Person. Project-related → Project. Small groups (1-3 files) can be skipped. Map frontmatter keys: `created` → `dcterms:created`, `tags` → leave as-is (already handled by executor as `schema:keywords`). `up` and `related` contain wiki-links stored as literals — map or skip per available properties.
4. Execute the import. Monitor SSE progress. Wait for completion. Check `import_result.json` for: `created` count (expect ~800-900), `edges_created` (expect ~300-400 from resolvable body wiki-links), `unresolved_links` count (expect ~400-500), `duration_seconds`.
5. Verify in workspace: (a) Open the nav tree — imported objects appear grouped by type. (b) Open one imported note with known body wiki-links — Relations panel shows `dcterms:references` edges. (c) Open one imported note with known frontmatter — properties panel shows mapped frontmatter values. (d) If any step fails, diagnose and fix the bug, then re-verify.

## Must-Haves

- [ ] Ideaverse vault uploads and scans without errors (OBSI-08)
- [ ] Type mapping and property mapping complete in wizard UI (OBSI-08)
- [ ] Import executes to completion with objects and edges created (OBSI-08)
- [ ] At least one imported note shows `dcterms:references` edges in Relations panel (OBSI-09)
- [ ] At least one imported note shows mapped frontmatter properties (OBSI-10)
- [ ] Import result recorded (created count, edges, unresolved links, duration)

## Verification

- Import wizard completes all steps without error
- `import_result.json` shows `created > 0`, `edges_created > 0`, no fatal errors
- Workspace UI shows imported objects with edges and properties
- UAT sign-off by user confirming wiki-links and frontmatter mapping quality

## Observability Impact

- Signals added/changed: None (existing SSE progress and import_result.json)
- How a future agent inspects this: Read `import_result.json` from the import directory; check scan result warnings; browse imported objects in workspace
- Failure state exposed: `import_error` SSE event with message; `errors` list in import result; scan `warnings` list

## Inputs

- T01 bug fixes in `scanner.py` and `executor.py` (must be applied before import)
- `Ideaverse Pro 2.5.zip` vault file (in project root or accessible path)
- Running Docker stack with backend, frontend, RDF4J triplestore
- S07-RESEARCH.md vault analysis: 905 .md files, ~30 folder-based type groups, 2484 body wiki-links, 855 files with `up:` frontmatter

## Expected Output

- ~800-900 imported objects in the triplestore with type, properties, body, and tags
- ~300-400 `dcterms:references` edges from resolved body wiki-links
- `import_result.json` with full import statistics
- S07-UAT.md with import results and user verification notes
- Any bug fixes committed if issues found during import
