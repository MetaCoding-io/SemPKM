# S06 Research: Miscellaneous Failures & Full Suite Verification

## Summary

S06 is the mop-up slice — run the full suite after S01–S05, fix every remaining failure, verify 0 failures. A partial test run (chromium, tests 1–118 of 948) identified 14 unique failing tests. Two additional failures are confirmed from S04 forward-intelligence. The full suite was not completed (900s timeout) — T01 must finish the catalog.

## Recommendation

Split into 3 tasks:
1. **T01 — Run full suite, catalog all failures with error messages** (~30min). Run per-directory to avoid timeout.
2. **T02 — Fix all identified failures** — batch by root cause category.
3. **T03 — Full suite green-light verification run.**

## Implementation Landscape

### Confirmed Failures (partial run, chromium, tests 1–118)

| # | File | Test | Pattern |
|---|------|------|---------|
| 1 | `00-setup/02-magic-link-login.spec.ts:147` | new user gets member role | Consistent — invite/role issue |
| 2 | `01-objects/create-edge.spec.ts:38` | edge appears in relations panel | 28s timeout |
| 3 | `01-objects/create-object.spec.ts:17` | type picker shows 4 types | 17s timeout |
| 4 | `01-objects/create-object.spec.ts:227` | create with full type IRI | Flaky 14s |
| 5 | `01-objects/edit-object-ui.spec.ts:113` | no TypeError from closest() | Flaky |
| 6 | `01-objects/edit-object-ui.spec.ts:246` | multi-value ref persist | Consistent |
| 7 | `01-objects/markdown-rendering.spec.ts:38` | markdown + XSS + API | Consistent |
| 8 | `01-objects/object-view-redesign.spec.ts:88` | properties badge count | Flaky |
| 9 | `01-objects/object-view-redesign.spec.ts:128` | localStorage persist | Flaky |
| 10 | `02-views/table-pagination.spec.ts:13` | pagination | Consistent ~4s (assertion, not timeout) |
| 11 | `02-views/timeline.spec.ts:89` | renders task bars | Consistent 25s timeout |
| 12 | `02-views/timeline.spec.ts:124` | dependency arrows | Consistent 27s timeout |
| 13 | `02-views/timeline.spec.ts:170` | zoom no crash | Consistent 26s timeout |
| 14 | `03-navigation/keyboard-shortcuts.spec.ts:34` | Alt+N type picker | 13s timeout |

### Known Failures from S04 Forward-Intelligence

| # | File | Issue |
|---|------|-------|
| 15 | `22-ontology/ontology-viewer.spec.ts` RBox test | Template `data-testid="{{ testid }}-{{ source }}"` produces `rbox-object-table-gist`. Test expects `[data-testid="rbox-object-table"]` without suffix. Fix: use bare `{{ testid }}` or prefix-match selector. |
| 16 | `23-class-creation/class-creation.spec.ts` | Waits for `.success-message`. Backend returns it correctly. Likely form submission fails (parent_iri not populated, or JS error). |

### Failure Categories

**A: Timeline view broken (3 tests)** — All timeout ~25s. Frappe Gantt CDN dependency or bare-global missed in M044 namespace migration. Check `timeline_view.html` and any `timeline.js`.

**B: Type picker / keyboard shortcuts (2+ tests)** — `create-object:17` and `keyboard-shortcuts:34` both wait for type picker. Possibly same root cause — broken open function or command palette wiring.

**C: Object view flakiness (4–5 tests)** — Timing-sensitive dockview + htmx races. May need increased waits or robust selectors.

**D: Table pagination (1 test)** — Fast failure (~4s) = assertion error, not timeout. Changed API or seed data count.

**E: Magic-link member role (1 test)** — Creates new user via magic-link (different from S01's invite fix).

**F: Markdown rendering (1 test)** — Consistent. Missing JS or template issue.

**G: Ontology RBox + class creation (2 tests)** — Confirmed structural mismatches.

### Key Files

| File | Role |
|------|------|
| `e2e/tests/02-views/timeline.spec.ts` | 3 failing timeline tests |
| `backend/app/templates/browser/timeline_view.html` | Timeline template with Frappe Gantt CDN |
| `backend/app/templates/browser/ontology/rbox_legend.html` | RBox template with dynamic testid |
| `e2e/tests/01-objects/create-object.spec.ts` | Type picker failures |
| `e2e/tests/01-objects/markdown-rendering.spec.ts` | Markdown rendering |
| `e2e/tests/02-views/table-pagination.spec.ts` | Pagination |
| `e2e/tests/03-navigation/keyboard-shortcuts.spec.ts` | Keyboard shortcut |
| `e2e/helpers/selectors.ts` | Central selector definitions |

### INCOMPLETE COVERAGE WARNING

Partial run covered ~118/948 tests (chromium only, dirs 00–03). The executor's T01 MUST run the full suite to discover failures in dirs 04-validation through 99-rate-limiting, all firefox tests, and all sync app tests. Many later tests may pass or auto-skip, but the failure list above is known-incomplete.

### Constraints

- Full suite takes 15+ min for 948 runs (chromium + firefox, 122 files)
- Sequential execution (1 worker, shared Docker state)
- Docker test stack must have all services healthy
- Demo/rate-limiting/screenshot tests auto-skip when prerequisites absent
- Timeline depends on CDN Frappe Gantt — if unreachable, all 3 fail
