---
id: T03
parent: S05
milestone: M014
provides:
  - Complete user guide chapter for the browser extension (Chapter 32)
  - Updated README TOC, glossary entries, and navigation chain
key_files:
  - docs/guide/32-browser-extension.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/31-api-surface.md
key_decisions:
  - Documented context menu as declared capability rather than detailed workflow since the permission is declared but no handler is implemented in the service worker
  - Included schema.org type mapping table directly from the actual TYPE_MAP in schema-mapper.js for accuracy
patterns_established:
  - Guide chapter structure: Overview → Installation (Chrome/Firefox) → API Key → Config → Workflow → Auto-population → Schema.org → Context Menu → Relationship Picker → Keyboard Shortcut → Troubleshooting
observability_surfaces:
  - none — documentation-only task; verify via file existence and content grep checks
duration: ~10 min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: User guide chapter + glossary + README TOC

**Wrote Chapter 32 (Browser Extension) with 12 sections covering installation, configuration, capture workflow, auto-population, schema.org mapping, relationship picker, keyboard shortcuts, and troubleshooting; updated README TOC, glossary, and navigation chain.**

## What Happened

Wrote `docs/guide/32-browser-extension.md` as a comprehensive user guide chapter for the browser extension. Cross-referenced the actual extension source code (manifest.json, options.html, extractor.js, schema-mapper.js, reference-picker.js) to ensure the documentation accurately reflects implemented features.

The chapter covers 12 sections: Overview, Installation (Chrome), Installation (Firefox), Generating an API Key, Configuration, Capturing Objects, Auto-population, Schema.org JSON-LD Mapping, Context Menu, Relationship Picker, Keyboard Shortcut, and Troubleshooting. The schema.org type mapping table was extracted directly from `extension/shared/schema-mapper.js` to ensure accuracy.

Updated three existing files: README.md (added Ch 32 to TOC), appendix-d-glossary.md (added "API Token" and "Browser Extension" entries in alphabetical order), and 31-api-surface.md (changed Next link from Appendix A to Chapter 32). The navigation chain now reads: Ch 31 → Ch 32 → Appendix A.

## Verification

All 8 plan-defined verification checks pass:
- File exists at `docs/guide/32-browser-extension.md`
- 25 `##` section headings (well above the 11 minimum)
- README TOC contains `32. [Browser Extension](32-browser-extension.md)`
- Glossary contains both "API Token" and "Browser Extension" entries
- Ch 31 Next link points to Ch 32
- Ch 32 Previous link points to Ch 31
- Ch 32 Next link points to Appendix A

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/32-browser-extension.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^##" docs/guide/32-browser-extension.md` (25 ≥ 11) | 0 | ✅ pass | <1s |
| 3 | `grep "32.*Browser Extension" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 4 | `grep "API Token" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 5 | `grep "Browser Extension" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 6 | `grep "32-browser-extension" docs/guide/31-api-surface.md` | 0 | ✅ pass | <1s |
| 7 | `grep "31-api-surface" docs/guide/32-browser-extension.md` | 0 | ✅ pass | <1s |
| 8 | `grep "appendix-a" docs/guide/32-browser-extension.md` | 0 | ✅ pass | <1s |

## Diagnostics

Documentation-only task. Verify by:
- `test -f docs/guide/32-browser-extension.md` — confirms chapter exists
- `grep -c "^##" docs/guide/32-browser-extension.md` — confirms section count
- Check navigation chain: grep prev/next links in Ch 31, Ch 32, and glossary

## Deviations

- Plan listed 11 sections; wrote 12 (split subsections within Troubleshooting into individual H3s for scanability)
- Context menu section is lighter than planned because the `contextMenus` permission is declared in both manifests but no `chrome.contextMenus.create()` handler exists in the service worker — documented as a declared capability rather than fabricating a workflow that doesn't exist

## Known Issues

- Context menu permission (`contextMenus`) is declared in both manifests but no handler is implemented — the feature is not yet functional
- Firefox temporary add-on limitation means the extension must be re-loaded after every browser restart; this is documented in the Troubleshooting section

## Files Created/Modified

- `docs/guide/32-browser-extension.md` — New: complete user guide chapter with 12 sections
- `docs/guide/README.md` — Updated: added Chapter 32 to TOC after Chapter 31
- `docs/guide/appendix-d-glossary.md` — Updated: added "API Token" and "Browser Extension" glossary entries
- `docs/guide/31-api-surface.md` — Updated: changed Next link from Appendix A to Chapter 32
- `.gsd/milestones/M014/slices/S05/tasks/T03-PLAN.md` — Updated: added Observability Impact section
