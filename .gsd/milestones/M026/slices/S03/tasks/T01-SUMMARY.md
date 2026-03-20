---
id: T01
parent: S03
milestone: M026
provides:
  - Fixed internal links (8 broken guide references → working guide/index.html)
  - Absolute og:image on all 4 docs pages
  - JSON-LD structured data (Organization + WebSite schema) on all 4 docs pages
key_files:
  - docs/index.html
  - docs/from-obsidian.html
  - docs/from-notion.html
  - docs/fresh-start.html
key_decisions: []
patterns_established: []
observability_surfaces:
  - "grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html → expect 4"
  - "grep -c 'application/ld+json' docs/*.html → expect 4"
  - "grep -rn 'guide/20-production-deployment' docs/*.html → expect 0 results"
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Fix broken links and add missing SEO tags

**Fixed 8 broken guide links, added absolute og:image to all 4 pages, and added JSON-LD structured data (Organization + WebSite) to all 4 docs pages.**

## What Happened

Four changes applied across `docs/index.html`, `docs/from-obsidian.html`, `docs/from-notion.html`, and `docs/fresh-start.html`:

1. Replaced `guide/20-production-deployment.html` with `guide/index.html` — 2 occurrences per file (hero CTA + bottom CTA), 8 total.
2. Changed homepage `og:image` from relative path (`screenshots/01-workspace-overview-dark.png`) to absolute URL (`https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png`).
3. Added `og:image` meta tag with absolute URL to the 3 persona pages (placed after `og:url`, before `twitter:card`).
4. Added `<script type="application/ld+json">` block with Organization + WebSite `@graph` to all 4 pages (placed after last `<meta>` tag, before first `<link>` tag).

## Verification

- Python link checker: zero broken internal links across all 4 files.
- HTMLParser: all 4 files parse without error.
- `grep -l 'og:image.*https://sempkm.metacoding.io'` returns all 4 files.
- `grep -l 'application/ld+json'` returns all 4 files.
- `grep -rn 'guide/20-production-deployment.html'` returns no results (exit code 1).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 link_checker (inline)` | 0 | ✅ pass | <1s |
| 2 | `python3 HTMLParser well-formedness` | 0 | ✅ pass | <1s |
| 3 | `grep -l 'og:image.*https://sempkm.metacoding.io' docs/*.html \| wc -l` → 4 | 0 | ✅ pass | <1s |
| 4 | `grep -l 'application/ld+json' docs/*.html \| wc -l` → 4 | 0 | ✅ pass | <1s |
| 5 | `grep -rn 'guide/20-production-deployment.html' docs/*.html` | 1 | ✅ pass (no matches) | <1s |

### Slice-Level Verification (partial — T01 is intermediate)

| # | Check | Status |
|---|-------|--------|
| 1 | Zero `guide/20-production-deployment.html` results | ✅ pass |
| 2 | og:image with absolute URL on all 4 pages | ✅ pass |
| 3 | JSON-LD on all 4 pages | ✅ pass |
| 4 | Python link checker: zero broken links | ✅ pass |
| 5 | HTML well-formedness: all 4 pages | ✅ pass |
| 6 | Fresh screenshots in docs/screenshots/ | ⬜ T02 |
| 7 | Lighthouse mobile ≥ 0.9 | ⬜ T02 |
| 8 | Browser rendering at 375px, 768px, 1200px | ⬜ T02 |

## Diagnostics

Static HTML changes only. Inspect with grep one-liners listed in observability_surfaces. No runtime, no logs, no server-side state.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/index.html` — fixed 2 guide links, absolute og:image, JSON-LD added
- `docs/from-obsidian.html` — fixed 2 guide links, og:image added, JSON-LD added
- `docs/from-notion.html` — fixed 2 guide links, og:image added, JSON-LD added
- `docs/fresh-start.html` — fixed 2 guide links, og:image added, JSON-LD added
