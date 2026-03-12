# S07: Obsidian Ideaverse Import

**Goal:** Import the Ideaverse Pro 2.5 vault (905 notes) through the existing import wizard, verify wiki-links resolve to edges and frontmatter maps to properties, fix any bugs found during the process.
**Demo:** User has imported the Ideaverse vault. In the workspace, opening an imported note shows frontmatter-mapped properties and the Relations panel shows `dcterms:references` edges from resolved wiki-links.

## Must-Haves

- `__MACOSX` resource fork directories are filtered from vault root detection and file walking in both scanner.py and executor.py
- Empty-stem `.md` files (e.g. `Books/.md`) are skipped during import rather than creating title-less colliding objects
- Unit tests cover the `__MACOSX` filtering and empty-stem handling
- Ideaverse Pro 2.5 vault (905 notes) uploads, scans, maps, and imports without errors through the existing wizard UI
- Body wiki-links in imported notes resolve to `dcterms:references` edges visible in the Relations panel
- Frontmatter keys mapped during the wizard appear as RDF properties on imported objects

## Proof Level

- This slice proves: integration (real vault through real import pipeline)
- Real runtime required: yes (Docker stack with RDF4J triplestore)
- Human/UAT required: yes (user maps type groups and frontmatter keys in wizard, verifies results in workspace)

## Verification

- `docker exec sempkm-backend pytest tests/test_obsidian_scanner.py -v` — unit tests pass for `__MACOSX` filtering, empty-stem skipping, and vault root detection
- Manual: Ideaverse Pro 2.5 vault imports through wizard UI with ~905 objects created (minus skipped empty-stem files)
- Manual: Opening an imported note shows mapped frontmatter properties in the object properties panel
- Manual: Relations panel for a note with body wiki-links shows `dcterms:references` edges to other imported notes

## Observability / Diagnostics

- Runtime signals: Import executor logs warnings for skipped files (empty-stem, parse errors) via `logger.warning`; SSE events broadcast progress (`import_progress`, `import_complete`, `import_error`)
- Inspection surfaces: `import_result.json` persisted in import directory contains `created`, `skipped_errors`, `edges_created`, `unresolved_links`, `duration_seconds`; scan result JSON in import directory shows type groups and warnings
- Failure visibility: SSE `import_error` event with message; `errors` list in import result with `(file_path, error_message)` tuples; scanner `warnings` list with categories (`malformed_frontmatter`, `empty_note`, `broken_link`)
- Redaction constraints: none (no secrets in import pipeline)

## Integration Closure

- Upstream surfaces consumed: `backend/app/obsidian/` (scanner, executor, router, models, broadcast), `backend/app/commands/handlers/` (object_create, edge_create, body_set), `backend/app/templates/obsidian/` (wizard UI)
- New wiring introduced in this slice: none (bug fixes only, existing wiring unchanged)
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice of M002

## Tasks

- [x] **T01: Fix __MACOSX filtering and empty-stem handling with unit tests** `est:45m`
  - Why: The `_detect_vault_root()` function in both scanner.py and executor.py doesn't exclude `__MACOSX` directories, causing macOS-created ZIPs to scan 2481 garbage entries. Empty-stem `.md` files cause title-less objects with colliding wiki-link keys. These are blocking bugs for the Ideaverse import.
  - Files: `backend/app/obsidian/scanner.py`, `backend/app/obsidian/executor.py`, `backend/tests/test_obsidian_scanner.py`
  - Do: (1) Add `__MACOSX` to exclusion filter in `_detect_vault_root()` visible entries and in `os.walk()` dirnames pruning in both scanner.py and executor.py. (2) Skip `.md` files with empty stems in scanner's md_files list and executor's md_files list. (3) Create unit tests covering: vault root detection with `__MACOSX` present, `os.walk` exclusion, empty-stem file skipping. Tests use temp directories with mock vault structure — no Docker required.
  - Verify: `cd backend && python -m pytest tests/test_obsidian_scanner.py -v` passes all tests
  - Done when: All unit tests pass, `__MACOSX` is excluded from both vault root detection and file walking, empty-stem files are skipped

- [x] **T02: Import Ideaverse vault and verify wiki-links and frontmatter** `est:1h`
  - Why: This is the core validation task — per D006, user-driven import of the real 905-note vault to prove OBSI-08, OBSI-09, and OBSI-10. The bug fixes from T01 must be in place for the import to succeed.
  - Files: `backend/app/obsidian/scanner.py`, `backend/app/obsidian/executor.py` (already fixed in T01 — verify fixes work at scale)
  - Do: (1) Ensure Docker stack is running with T01 fixes. (2) Upload `Ideaverse Pro 2.5.zip` through the import wizard at `/browser/import`. (3) Verify scan shows ~905 markdown files with ~30 type groups by folder. (4) Map type groups to available SHACL types (Note, Concept, Person, Project, or skip). (5) Map frontmatter keys (up, related, created, tags) to RDF properties. (6) Execute import and wait for completion. (7) Verify in workspace: open an imported note, confirm frontmatter properties appear, confirm Relations panel shows edges. (8) Fix any bugs discovered during import. (9) Record import results (created count, edge count, unresolved links) in UAT.
  - Verify: Import completes without errors; at least one note shows mapped frontmatter properties; at least one note shows `dcterms:references` edges in Relations panel
  - Done when: Ideaverse vault is imported, wiki-links resolve to edges, frontmatter maps to properties, user confirms results in UAT

## Files Likely Touched

- `backend/app/obsidian/scanner.py`
- `backend/app/obsidian/executor.py`
- `backend/tests/test_obsidian_scanner.py`
