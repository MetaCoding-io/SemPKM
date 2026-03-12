# S07: Obsidian Ideaverse Import — Research

**Date:** 2026-03-12

## Summary

S07 is a user-driven validation slice: import the Ideaverse Pro 2.5 vault (905 `.md` files, 35 MB ZIP) through the existing import wizard UI and verify that wiki-links resolve to edges and frontmatter maps to properties. The import infrastructure already exists (1917 LOC across 5 Python files, 998 LOC of templates, full E2E test suite with a small fixture vault).

Research identified **one critical bug** that will block the import: the `_detect_vault_root()` function fails on macOS-created ZIPs because `__MACOSX/` resource fork directories aren't filtered. The Ideaverse ZIP contains 2481 `__MACOSX` entries (including 905 `.md` binary resource forks) that would be scanned and produce garbage results. Additionally, the `+` folder name and 3 empty-stem `.md` files are edge cases that need verification or defensive handling.

The vault's structure is heavily folder-based (Atlas/Dots, Atlas/Sources, Efforts/Works, etc.) with zero `type`/`category` frontmatter fields — meaning all 905 notes will be classified by parent folder signal, producing ~30+ type groups for the user to map. The vault has rich frontmatter (855 files with `up:`, 851 with `related:`, 851 with `created:`) where `up` and `related` contain wiki-links (`[[target]]`). These frontmatter wiki-links are stored as literal strings during import, NOT resolved to edges — only body wiki-links (2484 across 366 files) become `dcterms:references` edges. This is an acceptable limitation for initial validation but worth noting.

## Recommendation

Fix the `__MACOSX` bug, then do the manual import through the UI. The existing import wizard is well-built and handles the full pipeline. The fix is small (exclude `__MACOSX` from both `_detect_vault_root` and `os.walk` in both scanner and executor). After the fix, run the import wizard manually:

1. Upload `Ideaverse Pro 2.5.zip`
2. Scan (expect ~905 notes, ~30 type groups by folder)
3. Map type groups to available SHACL types (Note, Concept, Project, Person, or skip)
4. Map frontmatter keys (up, related, created, tags, etc.) to RDF properties
5. Preview and execute import
6. Verify in workspace: wiki-links appear as edges in Relations panel, frontmatter appears as properties

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Vault scanning | `backend/app/obsidian/scanner.py` (VaultScanner) | Already handles multi-signal type detection, frontmatter parsing, wiki-link extraction, tag extraction |
| Object creation | `backend/app/commands/handlers/object_create.py` | Standard command handler, already used by executor |
| Edge creation | `backend/app/commands/handlers/edge_create.py` | Standard command handler for `dcterms:references` edges |
| SSE progress | `backend/app/obsidian/broadcast.py` (ScanBroadcast) | Thread-safe fan-out broadcaster already wired to UI |
| Frontmatter parsing | `python-frontmatter` library | Already a dependency, handles YAML frontmatter extraction |

## Existing Code and Patterns

- `backend/app/obsidian/scanner.py` — VaultScanner: auto-detects vault root, parses frontmatter, extracts wiki-links/tags, multi-signal type detection (frontmatter → folder → tag → uncategorized). **Bug: `_detect_vault_root` doesn't exclude `__MACOSX`**.
- `backend/app/obsidian/executor.py` — ImportExecutor: two-pass import (Pass 1: create objects with properties/body/tags, Pass 2: resolve body wiki-links to `dcterms:references` edges). Batches edges 10-at-a-time. Has same `_detect_vault_root` bug.
- `backend/app/obsidian/router.py` — Full wizard flow: upload → scan → type mapping → property mapping → preview → execute → summary. Auto-save endpoints for mapping configuration.
- `backend/app/obsidian/models.py` — Dataclasses for scan results, mapping config, import results. JSON serialization for persistence.
- `backend/app/obsidian/broadcast.py` — Thread-safe SSE broadcast with keepalive and terminal event detection.
- `backend/app/templates/obsidian/` — 12 template files for the wizard UI flow.
- `e2e/tests/14-obsidian-import/` — 3 E2E test files covering upload, scan, and full batch import with a 6-note fixture.
- `frontend/nginx.conf` — Already has `client_max_body_size 0` for `/browser/import/upload` and 300s proxy timeouts.

## Constraints

- **Available types are limited:** basic-pkm provides Note, Concept, Person, Project. PPV adds review types. The vault has ~30 folder-based type groups — most will map to Note or Concept, some will be skipped.
- **Object creation is not batched:** Each object+body is a separate EventStore.commit() = separate RDF4J transaction. 905 objects means ~905 transactions. At ~50ms each, expect ~45 seconds for Pass 1. Not a problem, but sets expectations.
- **Edge batching is 10-at-a-time:** Pass 2 (wiki-links) commits 10 edges per transaction. With ~2484 body links (386 resolvable), that's ~39 batch commits for edges. Fast.
- **Wiki-links in frontmatter are NOT resolved to edges:** The `up` and `related` fields (present in 855/851 files) contain wiki-links like `[[Communicate]]`. These are stored as literal string property values, not resolved. Only body wiki-links become edges. This is by design — the executor only extracts wiki-links from body content.
- **445 out of 831 unique wiki-link targets are unresolvable:** These reference notes outside the vault or notes that don't exist. The executor logs these as `unresolved_links` in the import result.
- **Docker volume:** Extracted vault goes to `/app/data/imports/{user_id}/{timestamp}/vault/`. The 35MB ZIP extracts to ~50MB. Volume must have space.
- **No type/category frontmatter:** Zero Ideaverse files use `type:`, `category:`, or `class:` fields. All type detection falls through to Signal 2 (parent folder name).

## Common Pitfalls

- **`__MACOSX` resource fork directory in macOS ZIPs** — The Ideaverse ZIP contains 2481 `__MACOSX` entries including 905 binary `.md` resource forks. The current `_detect_vault_root()` doesn't filter `__MACOSX`, causing it to fall back to `extract_path` (which includes `__MACOSX`). Fix: exclude `__MACOSX` from visible entries in `_detect_vault_root()` AND from `dirnames` in `os.walk()` in both scanner.py and executor.py.
- **3 empty-stem `.md` files** — `Books/.md`, `People/.md`, `ACE Pack/.md` have empty filenames (stem = ""). The executor uses `md_file.stem` as `dcterms:title` and `stem_name.lower()` as the wiki-link key. Empty stems mean: (a) title is empty string, (b) all three collide in `filename_to_iri` map. These should be skipped or given a generated title.
- **7 completely empty files** — Zero bytes. `frontmatter.load()` will produce empty metadata and empty body. They'll get created as empty objects. Low impact but noisy.
- **Tags with emoji** — Frontmatter tags like `output/youtube☑️` and `#output/youtube◻️` contain Unicode emoji. The body `TAG_RE` regex only matches `[a-zA-Z][a-zA-Z0-9_/-]*`, so emoji tags extracted from body would be truncated. Frontmatter tags are extracted as raw strings so they're fine. Minor inconsistency.
- **Very long filenames** — 7 files have names >100 chars (up to 192 chars). These become `dcterms:title` values. No issue for RDF (Literal strings are unbounded) but may display oddly in the UI.
- **Deeply nested folders** — 738 files are >3 levels deep. Type detection uses the immediate parent folder, so `Calendar/Records/Meetings/file.md` gets type `Meetings`, not `Calendar`. This is correct behavior for the Ideaverse structure.

## Open Risks

- **Import duration with 905 notes:** Estimated ~45-90 seconds for Pass 1 (objects), plus ~5 seconds for Pass 2 (edges). The SSE progress UI should handle this fine, but if RDF4J becomes slow under sustained transaction load, it could take longer. The 300s nginx proxy timeout provides ample headroom.
- **Mapping effort:** With ~30 type groups, the user needs to map each one in the wizard. Some groups are small (1-3 files) and can be skipped. This is expected manual effort per D006 (manual user-driven import).
- **Frontmatter wiki-links as strings:** The `up` field in 855 files contains hierarchical navigation links. Storing `[[Communicate]]` as a literal string instead of resolving it to an edge means the hierarchical structure of the vault is partially lost. This could be enhanced in a future slice but is out of scope for S07 validation.
- **Duplicate wiki-link targets:** If two notes have the same stem (case-insensitive), the executor's `filename_to_iri` map keeps the last one. There's only 1 duplicate stem case (3 empty-stem files) which should be filtered anyway.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Obsidian markdown | `kepano/obsidian-skills@obsidian-markdown` (5.5K installs) | available — not needed (server-side import, not Obsidian plugin dev) |
| python-frontmatter | n/a | none found — already well understood in codebase |
| RDF/SPARQL | n/a | none found — codebase has mature patterns |

No skills need to be installed. This is a bug-fix-and-validate slice, not new technology integration.

## Sources

- Vault analysis: `Ideaverse Pro 2.5.zip` — 905 .md files, 4963 total entries, 2481 `__MACOSX` entries, folder structure: Atlas (459), Efforts (226), x (102), Calendar (95), + (20), root (3)
- Import code: `backend/app/obsidian/` — 1917 LOC across scanner.py, executor.py, router.py, models.py, broadcast.py
- Templates: `backend/app/templates/obsidian/` — 998 LOC across 12 HTML files
- E2E tests: `e2e/tests/14-obsidian-import/` — 315 LOC across 3 spec files using 6-note fixture vault
- Available SHACL types: basic-pkm (Note, Concept, Person, Project), PPV (PillarGroup, Pillar, ValueGoal, GoalOutcome, Project, ActionItem, WeeklyReview, MonthlyReview, QuarterlyReview, YearlyReview)
