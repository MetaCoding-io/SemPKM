# M027: Notion Import Wizard — Research

**Date:** 2026-03-20

## Summary

The Notion import wizard mirrors the proven Obsidian import pattern (scanner → mapping UI → preview → execute) but with structurally different data: Notion exports databases as CSV files (not frontmatter), relations as title strings in CSV columns (not wiki-links), and property types are inferrable from CSV values (not guesswork from frontmatter strings). The existing `.planning/notion-import-research.md` provides an extensive design covering all aspects. This research validates that design against the current codebase and identifies what to build, reuse, and prove first.

The Obsidian importer (`backend/app/obsidian/`) is a clean 5-file module (scanner.py, executor.py, router.py, models.py, broadcast.py) with 10 template partials. The Notion importer should follow the same structure with a parallel `backend/app/notion/` module. Key shared infrastructure (broadcast SSE, TypeMapping/PropertyMapping models, step bar template) can be extracted to a shared `backend/app/imports/` module, but this is optional — copying and adapting is equally valid and lower risk for a milestone-scoped effort.

The biggest technical risk is **relation resolution by title matching** — Notion CSV exports store relations as page title strings, not IDs. When two rows in a target database share the same title, resolution is ambiguous. This must be proven early with a real Notion export. The research doc's "Classify" step (structured/content/dashboard/skip) adds wizard complexity beyond Obsidian's flow — the roadmap should evaluate whether to ship this in v1 or defer classification to auto-heuristics.

## Recommendation

**Follow the Obsidian pattern closely. Build in this order:**

1. **Scanner first** — CSV parsing, Notion ID stripping, column type inference, cross-database relation detection. This is the novel code. Prove it works against a real Notion export ZIP before building UI.
2. **Wizard UI second** — Adapt Obsidian templates. Upload → Scan Results → Type Mapping → Property Mapping → Relation Mapping → Preview → Import. Drop the "Classify" step from the research doc for v1 — auto-classify databases as structured and standalone pages as content. Users can skip individual items in the type mapping step.
3. **Executor third** — Two-pass import (objects first, relations second) via Command API with SSE progress. Adapt from Obsidian executor.
4. **E2E + docs last** — Standard trailing slices.

**Defer to future work:** Dashboard/rollup/formula preservation (DashboardSpec from research doc §8), Notion API live connection (Option B), Classify step as a separate wizard page, Comments import, Bookmark extraction.

## Implementation Landscape

### Key Files

- `backend/app/obsidian/scanner.py` — VaultScanner (250 lines). Reference for scan pattern: asyncio.to_thread wrapping sync logic, ScanBroadcast SSE progress, file-by-file parsing loop. Notion scanner replaces frontmatter parsing with CSV parsing.
- `backend/app/obsidian/executor.py` — ImportExecutor. Reference for two-pass import: Pass 1 creates objects via Command API, Pass 2 resolves links as edges. Notion executor replaces wiki-link resolution with CSV relation column resolution.
- `backend/app/obsidian/router.py` — FastAPI routes for wizard steps. Upload, scan trigger, scan results polling, type/property mapping POST, preview, execute. All htmx-driven with SSE for long operations.
- `backend/app/obsidian/models.py` — VaultScanResult, MappingConfig, TypeMapping, PropertyMapping, ImportResult dataclasses with to_dict/from_dict serialization. Notion models parallel these with CSV-specific fields.
- `backend/app/obsidian/broadcast.py` — ScanBroadcast SSE helper. Reusable as-is or trivially copyable.
- `backend/app/templates/obsidian/` — 10 template partials. Notion needs adapted versions of most, plus a new `relation_mapping.html` partial.
- `backend/app/main.py` — Router inclusion point. Notion router included alongside obsidian router.
- `frontend/static/js/workspace.js` — Command palette and sidebar navigation. Needs "Import > Notion" entry.

### Notion ZIP Structure (from research doc, critical for scanner design)

```
Workspace Name/
├── Standalone Page abc123.md           ← standalone content page
├── Database Name def456/
│   ├── Database Name def456.csv        ← schema + all row properties
│   ├── Row Title 111aaa.md             ← body content of row
│   └── Row Title 222bbb.md
```

Key scanner behaviors:
- **Database detection:** Presence of a `.csv` file in a folder marks it as a database. CSV headers = property schema, rows = instances.
- **Notion ID stripping:** Every filename/folder has ` [0-9a-f]{32}` appended. Regex `r'\s+[0-9a-f]{32}$'` strips it from stem.
- **Column type inference from CSV values:** Select (≤20 unique values), Date (ISO patterns), Checkbox (Yes/No), URL (http prefix), Number (parseable float), Relation (values matching titles in other DBs), Multi-select (comma-separated with few unique components).
- **Cross-DB relation detection:** After parsing all CSVs, check if column values are a subset (>80%) of another database's row titles.
- **Standalone pages:** .md files NOT inside a database folder.

### Build Order

1. **S01: Notion ZIP Scanner** — Parse CSV files, strip Notion IDs, infer column types, detect cross-DB relations. Unit tests with fixture data (small synthetic Notion export). This is the riskiest slice — novel parsing logic. Prove CSV parsing and relation detection work before building UI.
2. **S02: Upload + Scan Results UI** — Upload ZIP endpoint (reuse Obsidian pattern), scan trigger, scan results display (databases with column summaries, standalone pages, detected relations). htmx-driven.
3. **S03: Type + Property + Relation Mapping** — Three mapping steps. Type mapping (database → RDF type, same as Obsidian). Property mapping (CSV column → RDF property, per mapped type). Relation mapping (relation column → RDF predicate, new step unique to Notion). Auto-suggest based on name matching against installed model shapes.
4. **S04: Preview + Import Executor** — Preview shows sample mapped objects with properties and edges. Two-pass executor: Pass 1 creates objects from CSV rows + standalone pages as Notes, Pass 2 resolves relation columns as edges by title matching. SSE progress throughout. Import summary with stats.
5. **S05: E2E Tests + User Guide** — Playwright E2E test with a small fixture Notion export. User guide chapter.

### Verification Approach

- **Unit tests:** Scanner CSV parsing, ID stripping, column type inference, relation detection — all pure functions testable without Docker.
- **Integration test:** Upload a real (small) Notion export ZIP, verify scan results, map types/properties/relations, preview, execute import, verify objects and edges in triplestore via SPARQL.
- **E2E Playwright:** Full wizard flow against Docker test stack.

## Constraints

- **No `python-frontmatter` for Notion** — CSV parsing uses stdlib `csv` module. Markdown body files use plain `Path.read_text()` since they have no frontmatter.
- **Relation resolution is title-based** — CSV exports contain page titles, not Notion page IDs. Ambiguous titles (duplicates in target DB) require heuristic handling (warn user, pick first match).
- **No Notion API in v1** — ZIP-only. The research doc's Option B (API connection) is explicitly out of scope per CONTEXT.md.
- **DashboardSpec preservation deferred** — The research doc proposes creating DashboardSpec objects for dashboard pages. This is valuable but adds scope. Defer to v2 or a follow-up slice. Dashboard pages classified as "skip" for v1.
- **Rollup/Formula columns** — In CSV export, these are just computed values with no type metadata. Treat as plain text properties for v1. The research doc's heuristic detection is useful but not critical for MVP.

## Common Pitfalls

- **Notion ID in filenames is 32 hex chars, not 20** — The regex must match exactly 32 hex chars preceded by a space. Shorter hex sequences in user-chosen filenames should NOT be stripped.
- **CSV encoding** — Notion exports CSVs in UTF-8 with BOM. Use `encoding='utf-8-sig'` when opening CSV files.
- **Empty CSV cells** — Notion exports empty properties as empty strings, not missing columns. Column type inference must handle high empty-cell ratios gracefully.
- **Multi-select comma splitting** — A cell value like `"Tag1, Tag2"` looks like plain text. The heuristic (few unique components across all rows) must be conservative to avoid splitting actual text values.
- **Nested databases** — Notion allows databases inside pages inside databases. The ZIP flattens this somewhat but folders can nest arbitrarily. Scanner must walk the full tree.
- **Date format variation** — Notion exports dates in locale-dependent formats. Use `dateutil.parser.parse()` for robust parsing, with fallback to string storage.

## Open Risks

- **No real Notion export to test against during development** — Need to create a synthetic fixture that accurately represents Notion's export format. If the real format differs from the research doc's description, the scanner may need adjustment. Mitigated by keeping the scanner well-tested with fixture data and making format assumptions explicit.
- **Large export performance** — CONTEXT says "500+ page export completes without timeout". The Obsidian importer handles 895 objects in ~30s. CSV parsing is faster than frontmatter parsing, so this should be fine, but the two-pass relation resolution adds a title-lookup phase that could be O(n²) without indexing. Build a title→IRI lookup dict after Pass 1.
- **Relation ambiguity** — If 5-10% of relation values can't be resolved (duplicate titles, typos, missing targets), the user experience degrades. The preview step must clearly show unresolvable relations with counts.

## Scope Simplification vs Research Doc

The research doc (`notion-import-research.md`) is comprehensive but proposes features beyond the M027 CONTEXT scope. Here's what to include and defer:

| Feature | Research Doc Section | M027 Status | Rationale |
|---------|---------------------|-------------|-----------|
| ZIP upload + scan | §2 Option A, §4 | ✅ In scope | Core functionality |
| Database → type mapping | §3 Step 4 | ✅ In scope | Same as Obsidian |
| Property mapping with type inference | §3 Step 5 | ✅ In scope | CSV column types |
| Relation → edge mapping | §3 Step 6 | ✅ In scope | Notion-specific, high value |
| Preview + two-pass import | §3 Steps 7-8 | ✅ In scope | Same as Obsidian |
| Classify step (5 classifications) | §3 Step 3 | ⏭️ Simplify | Auto-classify: DB=structured, page=content. Skip toggle per item in type mapping. |
| DashboardSpec preservation | §8 | ⏭️ Defer | Adds RDF vocabulary + executor complexity for a non-critical feature |
| Rollup/Formula heuristic detection | §4, §8 | ⏭️ Defer | Treat as plain text columns for v1 |
| Comments import | §7 Tier 2 | ⏭️ Defer | Optional, low priority |
| Bookmark extraction | §7 Tier 2 | ⏭️ Defer | Low priority |
| Shared imports/ module extraction | §6 | ⏭️ Optional | Copy-and-adapt is lower risk than refactoring Obsidian |
| Notion API (Option B) | §2, §10 | ❌ Out of scope | Explicitly deferred in CONTEXT |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CSV parsing | Python stdlib `csv` module | Handles quoting, escaping, UTF-8 BOM |
| Date parsing from varied formats | `python-dateutil` (already in deps) | Notion exports dates in locale-dependent formats |
| ZIP extraction | Python stdlib `zipfile` | Already used by Obsidian importer |
| SSE broadcasting | `backend/app/obsidian/broadcast.py` | Proven pattern, copy or import |

## Sources

- `.planning/notion-import-research.md` — Comprehensive feasibility research covering all aspects of Notion import
- `backend/app/obsidian/` — Reference implementation (scanner, executor, router, models, broadcast)
- M027 CONTEXT.md — Scope definition and acceptance criteria
