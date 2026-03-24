---
estimated_steps: 5
estimated_files: 15
skills_used:
  - review
  - best-practices
---

# T02: Document A06 (Vulnerable Components) and A08 (Data Integrity) findings, assemble severity summary

**Slice:** S02 — Configuration, Infrastructure & Supply Chain Findings (A05, A06, A08, A09)
**Milestone:** M042

## Description

Add A06 (Vulnerable and Outdated Components) and A08 (Software and Data Integrity Failures) findings to S02-FINDINGS.md, then append the severity summary table covering all S02 findings. A06 requires building a complete CDN dependency inventory table from template and JS file analysis. A08 covers ZIP handling, federation patch integrity, and RDF import validation. Continue finding numbers from where T01 left off.

## Steps

1. Read `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` (T01's output) to determine the last finding number used
2. Read the S02 research file for A06/A08 analysis: `.gsd/milestones/M042/slices/S02/S02-RESEARCH.md`
3. Build the A06 CDN dependency inventory by reading template files and JS sources:
   - Read `backend/app/templates/base.html` — count CDN script/link tags, check for `integrity=` attributes, note version pins
   - Read `backend/app/templates/base_embed.html` — same checks
   - Read `backend/app/templates/browser/calendar_view.html`, `map_view.html`, `timeline_view.html`, `workspace.html`, `admin/model_detail.html`, `admin/sparql.html` — check for CDN loads
   - Read `frontend/static/js/workspace.js`, `calendar.js`, `theme.js` — check for dynamic CDN loads (lazy `import()` or `document.createElement('script')`)
   - Read `frontend/build.js` — identify which deps are vendored vs always-CDN
   - Read `backend/pyproject.toml` and `frontend/package.json` — assess pin strategy
   - Confirm: zero `integrity=` attributes across all CDN loads (the research claims this)
   - Identify unpinned CDN deps (marked, marked-highlight, dompurify, gridstack@10, chart.js@4.4)
4. Write A06 findings (F-0XX through F-0XX): SRI absence across all CDN deps, unpinned CDN deps resolving to latest, vendor pipeline gaps (always-CDN in production), absent CVE scanning pipeline. Include the full CDN inventory table within the SRI finding.
5. Verify A08 findings against source:
   - Read `backend/app/obsidian/router.py` line ~126 for `zf.extractall()` — confirm no zip-bomb guard (no size/count check before extraction)
   - Read `backend/app/notion/router.py` line ~153 for `zf.extractall()` — same
   - Read `backend/app/federation/router.py` around `export_patches()` and `sync_shared_graph()` — confirm patches are not cryptographically signed
   - Search for RDF import validation: `rg 'rdf_import' backend/app/` to find the import module and confirm no content filtering beyond parsing
6. Write A08 findings (F-0XX through F-0XX): ZIP extraction without zip-bomb protection (note Python 3.12 path traversal mitigation), unsigned federation patches, unvalidated RDF import content
7. Append the `## Summary — Findings by Severity` table covering all S02 findings (F-021 through the last finding), matching S01's summary table format

## Must-Haves

- [ ] A06 section includes a complete CDN dependency inventory table: library, version pin, SRI status, template file, dev-only vs always
- [ ] A06 findings cover: zero SRI on all CDN loads, unpinned deps, vendor pipeline gaps, absent CVE scanning
- [ ] A08 findings cover: ZIP extraction without zip-bomb guard, unsigned federation patches, unvalidated RDF import
- [ ] All CDN URLs and file locations confirmed against actual template source (not just copied from research)
- [ ] Severity summary table covers all S02 findings with counts by severity level
- [ ] Finding numbers continue sequentially from T01's last finding
- [ ] No source code files modified

## Verification

- `grep -c '^### F-' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md` >= 12 (total across T01 + T02)
- `grep -q '## A06:' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md`
- `grep -q '## A08:' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md`
- `grep -q '## Summary' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md`
- `grep -q 'CDN' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md` — CDN inventory present

## Inputs

- `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` — T01's output (A05 + A09 sections, last finding number)
- `.gsd/milestones/M042/slices/S02/S02-RESEARCH.md` — pre-analyzed findings for A06 and A08
- `backend/app/templates/base.html` — main CDN dependency loads
- `backend/app/templates/base_embed.html` — embed page CDN loads
- `backend/app/templates/browser/calendar_view.html` — FullCalendar CDN lazy-load
- `backend/app/templates/browser/map_view.html` — Leaflet CDN lazy-load
- `backend/app/templates/browser/timeline_view.html` — timeline view CDN loads
- `backend/app/templates/browser/workspace.html` — dockview CDN load
- `frontend/static/js/workspace.js` — Chart.js CDN lazy-load
- `frontend/static/js/calendar.js` — FullCalendar CDN lazy-load
- `frontend/static/js/theme.js` — highlight.js theme CDN swap
- `frontend/build.js` — vendor pipeline (which deps are vendored)
- `backend/pyproject.toml` — Python dependency pins
- `frontend/package.json` — JS dependency pins
- `backend/app/obsidian/router.py` — ZIP extractall
- `backend/app/notion/router.py` — ZIP extractall
- `backend/app/federation/router.py` — unsigned patch export/sync

## Expected Output

- `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` — complete document with all four OWASP sections (A05, A06, A08, A09) and severity summary table
