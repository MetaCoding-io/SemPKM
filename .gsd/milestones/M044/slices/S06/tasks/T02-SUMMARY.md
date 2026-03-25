---
id: T02
parent: S06
milestone: M044
key_files:
  - docs/FRONTEND-CONVENTIONS.md
key_decisions:
  - Included Lucide Icons and File Serving sections beyond the planned 6 — both are documented pitfalls in CLAUDE.md/KNOWLEDGE.md that belong in the definitive frontend guide
duration: ""
verification_result: passed
completed_at: 2026-03-25T22:18:29.839Z
blocker_discovered: false
---

# T02: Create docs/FRONTEND-CONVENTIONS.md covering htmx patterns, JS module structure, CSS theme system, debug logging, fetch conventions, event cleanup, Lucide icons, and file serving

**Create docs/FRONTEND-CONVENTIONS.md covering htmx patterns, JS module structure, CSS theme system, debug logging, fetch conventions, event cleanup, Lucide icons, and file serving**

## What Happened

Created `docs/FRONTEND-CONVENTIONS.md` — the definitive developer-facing reference for SemPKM's frontend architecture. Before writing, read the actual codebase to ground every claim: `api-fetch.js` for namespace/fetch/debug patterns, `theme.css` for the full token system, `cleanup.js` for the cleanup registry, decisions D369/D370/D371, and grepped the template directory for real htmx usage counts.

The document covers 8 sections:

1. **htmx Patterns** — swap modes with actual usage counts (innerHTML ~170, outerHTML ~20, none ~10), trigger patterns with examples, hx-boost strategy, htmx event listeners used in JS (afterSwap, afterSettle, configRequest, responseError, pushedIntoHistory, beforeCleanupElement), and jinja2-fragments partial rendering pattern.

2. **JavaScript Module Structure** — IIFE pattern (24/29 files), the 5 exceptions and why, SemPKM namespace bootstrap in api-fetch.js, export conventions, cross-IIFE guard flag pattern.

3. **CSS Theme System** — two-tier architecture (primitives vs semantics), color rules (no standalone hex/rgba outside theme.css), color-mix() for transparency, two breakpoints only (600px mobile, 768px tablet), dark mode via data-theme attribute, crossfade transitions on specific elements.

4. **Debug Logging** — SemPKM.debug() API, enable/disable via localStorage, severity guide (debug/warn/error), rule against direct console.log().

5. **Fetch Conventions** — SemPKM.apiFetch() behavior table (success, network error, 401, 403, 5xx, AbortError, silent mode), the auth.js exemption and why.

6. **Event Cleanup** — registerCleanup/runCleanup API, automatic cleanup via htmx:beforeCleanupElement, manual cleanup for dockview panels.

7. **Lucide Icons** — CSS sizing rule (flex-shrink:0), stroke inheritance, re-initialization after htmx swap. Included because CLAUDE.md documents this as a recurring pitfall.

8. **File Serving** — nginx path mapping (no /static/ prefix). Included because this has caused bugs multiple times (see KNOWLEDGE.md entry about nginx serving /js/ and /css/ but NOT /static/).

## Verification

Ran `test -f docs/FRONTEND-CONVENTIONS.md && grep -c '^## ' docs/FRONTEND-CONVENTIONS.md` — returned 8, exceeding the ≥6 requirement. Verified all 6 planned sections present plus 2 bonus sections grounded in documented pitfalls. Confirmed document references real usage counts and patterns from the actual codebase.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/FRONTEND-CONVENTIONS.md && grep -c '^## ' docs/FRONTEND-CONVENTIONS.md` | 0 | ✅ pass (8 sections, ≥6 required) | 80ms |


## Deviations

Added two sections beyond the planned six: Lucide Icons (documented in CLAUDE.md as a recurring pitfall with flex containers) and File Serving (documented in KNOWLEDGE.md as a source of bugs). Both are important frontend conventions that belong in the definitive guide.

## Known Issues

None.

## Files Created/Modified

- `docs/FRONTEND-CONVENTIONS.md`
