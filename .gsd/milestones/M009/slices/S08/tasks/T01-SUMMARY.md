---
id: T01
parent: S08
milestone: M009
provides:
  - Chapter 29 documentation page for the App Platform
key_files:
  - docs/guide/29-app-platform.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - none (static documentation)
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Write Chapter 29 — App Platform guide page

**Wrote 293-line Chapter 29 covering app management from the admin portal and app development with the SDK, using test-app as the canonical reference.**

## What Happened

Read all source material in parallel: test-app manifest and app.py for accurate examples, SDK App class and AppContext for API surface, admin templates for workflow descriptions, and chapter 28 for style conventions.

Wrote `docs/guide/29-app-platform.md` with two main H2 sections:

- **Managing Apps** — covers the Applications admin page, install form, status badges (running/stopped/error/installing), start/stop/restart controls, crash recovery, task monitoring with configuration and history, uninstalling, and permissions display.
- **Building Apps with the SDK** — covers directory structure, manifest.yaml (condensed test-app manifest as inline example), App class with all 6 decorators (on_install, on_startup, on_shutdown, on_uninstall, route, task), AppContext with 5 client properties (commands, graph, state, settings, http) plus render_template, fragment routes, task handlers, three frontend integration levels (L1 standalone pages, L2 workspace contributions, L3 object renderer overrides), and the permissions sandbox model.

Initial draft was 375 lines — trimmed redundant code examples and verbose sections to reach 293 lines (within the 150-300 target). Footer navigation points to ch. 28 (previous) and Appendix A (next).

## Verification

All task-level checks pass:
- File exists at `docs/guide/29-app-platform.md`
- H1 is "Chapter 29: App Platform"
- `## Managing Apps` present (count: 1)
- `## Building Apps` present (count: 1)
- `manifest.yaml` referenced 4 times
- `AppContext` referenced 12 times
- 3 Python code blocks showing App class, decorators, and fragment routes
- Footer navigation line present
- Line count: 293 (within 150-300 range)

Slice-level checks: 5/12 pass (the T01-owned checks). The remaining 7 (glossary entries, README TOC, ch28 footer update) are T02's responsibility.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/29-app-platform.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "## Managing Apps" docs/guide/29-app-platform.md` | 0 (1) | ✅ pass | <1s |
| 3 | `grep -c "## Building Apps" docs/guide/29-app-platform.md` | 0 (1) | ✅ pass | <1s |
| 4 | `grep "manifest.yaml" docs/guide/29-app-platform.md` | 0 | ✅ pass | <1s |
| 5 | `grep "AppContext" docs/guide/29-app-platform.md` | 0 | ✅ pass | <1s |
| 6 | `wc -l docs/guide/29-app-platform.md` | 0 (293) | ✅ pass | <1s |
| 7 | `grep "Appendix A" docs/guide/29-app-platform.md` | 0 | ✅ pass | <1s |
| 8 | `find docs/guide/ -name "29-app-platform.md" -empty \| wc -l` | 0 (0) | ✅ pass | <1s |

## Diagnostics

Static markdown file — `cat docs/guide/29-app-platform.md` to inspect. No runtime signals. Broken internal links can be checked with:
```
for f in $(grep -oP '\]\(\K[^)]+\.md' docs/guide/29-app-platform.md); do test -f "docs/guide/$f" || echo "BROKEN: $f"; done
```

## Deviations

- Line count target was 200-250; actual is 293. The manifest inline example and comprehensive decorator/client tables push the length up but the content is practical and non-redundant. Within the plan's 150-300 verification range.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/29-app-platform.md` — new Chapter 29 covering app management and SDK development
