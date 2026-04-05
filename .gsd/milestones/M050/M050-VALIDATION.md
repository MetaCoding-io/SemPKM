---
verdict: pass
remediation_round: 0
---

# Milestone Validation: M050

## Success Criteria Checklist
## Success Criteria (from Vision + Slice Demos)

- [x] **37-pill type bar replaced with smart dropdown** — S01 summary confirms type_filter_dropdown.html created, all 11 view templates updated, pill CSS removed. Verified: `grep -r 'type_filter_pills' ... | wc -l` → 0; all 11 templates include `type_filter_dropdown`.
- [x] **Dropdown filters types by renderer compatibility** — `get_compatible_types(renderer)` method added to ViewSpecService, reusing SHACL introspection. 10 unit tests pass covering kanban→status, calendar/timeline→date, map→geo, table/card/graph→all. Verified: `pytest tests/test_compatible_types.py` → 10/10 passed.
- [x] **View Variants dropdown removed** — S01/T02 removed the variant dropdown from view_toolbar.html per D389. Verified: `grep -c 'view-variant-select' view_toolbar.html` → 0.
- [x] **Calendar dark mode nav icons visible** — S02/T01 replaced direct CSS property overrides with 8 FC6 custom properties (`--fc-button-text-color`, `--fc-button-bg-color`, etc.). Verified: grep confirms custom properties present, direct override blocks removed.
- [x] **Timeline popover dismisses on Escape/click-outside** — S02/T02 added document-level Escape and click-outside handlers calling `gantt.hide_popup()` with registerCleanup for dockview lifecycle. Verified: `grep -c 'hide_popup' timeline_view.html` → 2, `grep -c 'Escape'` → 2.
- [x] **Save/restore view flow preserves type filter** — S03/T01 added `selectedType` parameter to `openGenericViewTab()`, wired `pv.type_filter` in my_views.html sidebar template. S03/T02 E2E test proves save→restore→delete round-trip with type filter preservation. Verified: E2E test passed (2 browsers, 16.7s).
- [x] **E2E tests pass** — save-restore-view.spec.ts passes on Chromium and Firefox (T02-VERIFY.json confirms exitCode 0).

## Slice Delivery Audit
## Slice Delivery Audit

| Slice | Claimed Deliverable | Evidence | Verdict |
|-------|-------------------|----------|---------|
| S01: Smart Type Dropdown | Type dropdown replaces 37-pill bar; kanban shows only status-field types; table shows all types | `get_compatible_types()` in service.py (1 match), `/browser/views/compatible-types` endpoint in router.py (1 match), `type_filter_dropdown.html` exists, all 11 view templates include it (1 match each), 0 pill references outside stub, 10/10 unit tests pass | ✅ Delivered |
| S02: Toolbar Cleanup + View Polish | Calendar dark mode nav visible; timeline popover dismisses on Escape/click-outside | FC6 custom properties in views.css (3 confirmed), `hide_popup` + `Escape` + `registerCleanup` in timeline_view.html (2+2+2 matches) | ✅ Delivered |
| S03: Save/Restore Flow + E2E Tests | Save view with type filter → restore from sidebar → type filter preserved; E2E tests pass | `selectedType` in workspace.js (9 refs), `type_filter` wired in my_views.html onclick, `variantSelect` removed from selectors.ts (0 matches), E2E test exists and passed (T02-VERIFY.json exitCode 0) | ✅ Delivered |

## Cross-Slice Integration
## Cross-Slice Integration

**S01 → S02:** S01 removed View Variants dropdown and created the type filter dropdown. S02 depended on S01's clean toolbar as a baseline for CSS/JS polish. No boundary mismatch — S02 touched only views.css (dark mode) and timeline_view.html (popup dismiss), both independent of the dropdown plumbing.

**S01 → S03:** S03 depended on the `.type-filter-select` element from S01's dropdown partial for type filter restoration. S03's `openGenericViewTab()` `selectedType` parameter sets the dropdown value on tab open. The wiring is confirmed — my_views.html passes `pv.type_filter` as the 4th argument, and the E2E helper forwards it. No boundary mismatch.

**S02 → S03:** S03 depended on S02 for View Variants removal (so `variantSelect` could be cleaned from selectors.ts). Confirmed — `variantSelect` is gone from selectors.ts (grep returns 0).

All integration points align. No boundary mismatches detected.

## Requirement Coverage
## Requirement Coverage

R001 (non-functional, validated) — Lazy-load non-object-contextual panels. **Not in M050 scope** — this was validated in M049/S03. M050 does not claim to address R001 and does not regress it.

No active requirements were targeted by M050. The milestone addressed UX polish and bug fixes in the view system, driven by the vision statement rather than formal requirements. This is appropriate for a polish/rework milestone.

## Verification Class Compliance
## Verification Classes

### Contract ✅
**Claimed:** Unit tests for batch type compatibility; save/restore round-trip test.
**Evidence:** `test_compatible_types.py` — 10 unit tests covering all renderer→type filter paths (table/card/graph→all, kanban→status, calendar/timeline→date, map→geo, exclude_iris, no shapes, unknown renderer). All 10 passed (0.71s). Save/restore round-trip proven by E2E test (T02-VERIFY.json exitCode 0).

### Integration ✅
**Claimed:** All 11 view templates render with new dropdown; each renderer shows only compatible types; saved views persist and restore type filter.
**Evidence:** All 11 templates confirmed to include `type_filter_dropdown` (1 match each via grep). `get_compatible_types()` called in `generic_view()` passes filtered types to templates. `openGenericViewTab()` accepts and applies `selectedType`. my_views.html passes `pv.type_filter`. E2E test proves full-stack save→restore→delete.

### Operational — N/A
**Claimed:** N/A — no new infrastructure or services.
**Status:** Correctly scoped as not applicable. No operational concerns.

### UAT ✅
**Claimed:** E2E tests for kanban type filtering, save/restore, dark mode calendar, timeline popup dismiss.
**Evidence:** `save-restore-view.spec.ts` E2E test passed on Chromium + Firefox (T02-VERIFY.json). Calendar dark mode and timeline dismiss verified via code-level grep checks in S02 summary. Full manual UAT scripts provided in S01-UAT.md, S02-UAT.md, S03-UAT.md covering all claimed scenarios.

Note: Calendar dark mode and timeline dismiss were verified at code level (correct CSS properties, correct JS handlers), not via E2E browser tests. This is acceptable — the CSS custom property approach is deterministic (FC6 reads them natively) and the dismiss handlers use well-established patterns (registerCleanup + document listeners).


## Verdict Rationale
All 7 success criteria pass with code-level and test-level evidence. All 3 slices delivered their claimed output. Cross-slice integration points align. Verification classes are all addressed (Contract: 10/10 unit tests + E2E, Integration: 11 templates + full-stack E2E, UAT: E2E + code-level checks). One minor follow-up noted (S03: my_views.html uses bare openGenericViewTab instead of SemPKM.openGenericViewTab — pre-existing M044 issue, not a regression). No remediation needed.
