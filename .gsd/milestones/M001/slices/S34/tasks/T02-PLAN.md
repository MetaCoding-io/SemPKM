# T02: 34-e2e-test-coverage 02

**Slice:** S34 — **Milestone:** M001

## Description

Write new Playwright E2E tests covering v2.3 user-visible features: fuzzy FTS toggle, carousel view switching, named workspace layout save/restore, and dockview panel management assertions.

Purpose: Ensure v2.3 features have regression coverage so future changes don't break fuzzy search, carousel views, named layouts, or dockview panel operations without detection.
Output: Three new test files covering TEST-04 requirements including dockview panel management.

## Must-Haves

- [ ] "Fuzzy FTS toggle test verifies the toggle command exists, persists state to localStorage, and sends fuzzy=true in search requests"
- [ ] "Carousel view test verifies the tab bar renders for multi-view types, clicking switches the view body, and active view persists to localStorage"
- [ ] "Named layout test verifies save/list/restore/remove lifecycle works via window.SemPKMLayouts API"
- [ ] "Dockview panel management is verified: window._dockview is available, openObjectTab/openViewTab helpers work, and getTabCount returns correct counts"

## Files

- `e2e/tests/08-search/fuzzy-toggle.spec.ts`
- `e2e/tests/03-navigation/named-layouts.spec.ts`
- `e2e/tests/02-views/carousel-views.spec.ts`
