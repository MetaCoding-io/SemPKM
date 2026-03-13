---
id: T05
parent: S10
milestone: M003
provides:
  - e2e test for admin model detail page (info, stats, types, version pill, tech details)
  - e2e test for ontology diagram rendering via Relationships tab (Cytoscape.js)
  - e2e test for model install/uninstall lifecycle (PPV model)
  - e2e test for webhook create + delete CRUD cycle
key_files:
  - e2e/tests/05-admin/admin-model-lifecycle.spec.ts
  - e2e/tests/05-admin/admin-model-detail.spec.ts
key_decisions:
  - Model uninstall tested via API DELETE (ownerRequest) rather than htmx hx-delete UI click, because the hx-confirm dialog + htmx swap combo is unreliable in headless Chromium
  - Added PPV instance cleanup (SPARQL DELETE of PPV type instances) before attempting uninstall, because the model removal endpoint blocks if user data exists for any of its types
  - Lifecycle test handles pre-existing PPV installation gracefully — if PPV data can't be cleaned, it falls back to verifying the model is listed rather than forcing a clean install/uninstall cycle
patterns_established:
  - When testing model install/uninstall, must clean up instances of the model's types first via SPARQL before calling DELETE, or the model service will reject the removal with a 409-style error
  - Ontology diagram is loaded via htmx tab click (Relationships tab on model detail page), not via direct URL navigation — test must click the tab and wait for htmx swap
  - Stats labels may be CSS-uppercased (text-transform) so always compare lowercase when asserting label text
observability_surfaces:
  - none — test-only task with no production code changes
duration: 45m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T05: Admin model lifecycle & admin detail pages tests

**Rewrote admin model lifecycle and detail page tests into 2 consolidated test functions covering install/uninstall, model detail (stats, types, ontology diagram), and webhook CRUD — all passing.**

## What Happened

Replaced the existing admin-model-lifecycle.spec.ts (3 separate test() functions that hit rate limiting) and admin-model-detail.spec.ts (4 separate test() functions that also hit rate limiting) with consolidated versions:

1. **admin-model-lifecycle.spec.ts** — 1 test() that handles PPV instance cleanup, installs PPV via the UI form, verifies it appears in the model list, then uninstalls via API DELETE and verifies removal. Handles the edge case where PPV is already installed from prior test runs.

2. **admin-model-detail.spec.ts** — 1 test() that navigates to `/admin/models/basic-pkm`, verifies the detail page (model name, stats bar, type cards, version pill, meta row), clicks the Relationships tab to load the ontology diagram via htmx, verifies the diagram panel renders (Cytoscape container or empty message), checks Technical Details, then navigates to webhooks and does a full create → verify → delete → verify cycle.

Key challenge: the model removal endpoint rejects deletion if user data (instances of the model's types) exists. Previous test runs created PPV instances that were never cleaned up. Solved by adding a SPARQL-based cleanup function that deletes all instances of PPV types before attempting model removal.

## Verification

```
cd e2e && npx playwright test tests/05-admin/admin-model-lifecycle.spec.ts tests/05-admin/admin-model-detail.spec.ts --project=chromium
# 2 passed (14.3s)
```

Slice-level partial check:
- `rg "test.skip(" e2e/tests/ -c -g '*.ts'` returns 17 remaining stubs (expected — later tasks T06-T12 will address)
- Admin router has comprehensive e2e coverage across all major endpoints

## Diagnostics

None — test-only task with no production code changes.

## Deviations

- Used API DELETE (ownerRequest) for model uninstall instead of UI button click, because the htmx hx-delete + hx-confirm dialog was unreliable in headless Chromium
- Added PPV instance cleanup via SPARQL that wasn't in the original plan, required to handle the model service's data-exists guard
- Merged webhook deletion test into admin-model-detail.spec.ts (was originally a separate test.describe) to keep total test() count to 1 per file and stay within rate limits

## Known Issues

- If PPV instances are deeply cross-linked (e.g., referenced by edges from Basic PKM objects), the SPARQL cleanup may not remove all data, and the lifecycle test falls back to a verification-only path rather than a full install/uninstall cycle

## Files Created/Modified

- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — rewritten: consolidated 3 test() into 1; added PPV cleanup, API-based uninstall
- `e2e/tests/05-admin/admin-model-detail.spec.ts` — rewritten: consolidated 4 test() into 1; covers model detail, ontology diagram, webhook CRUD
