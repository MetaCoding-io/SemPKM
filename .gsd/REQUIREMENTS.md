# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R002 — Tarfile extraction must validate all member paths are relative and within expected structure — no path traversal
- Class: security
- Status: active
- Description: Tarfile extraction must validate all member paths are relative and within expected structure — no path traversal
- Why it matters: Prevents path traversal attacks (../../etc/passwd) via malicious model archives
- Source: M053
- Primary owning slice: M053/S02
- Validation: Tarfile extraction validates every member name: rejects absolute paths, rejects '..', rejects symlinks. Unit test proves path traversal is blocked.

### R003 — Duplicate model install prevented for marketplace installs (same as filesystem installs)
- Class: functional
- Status: active
- Description: Duplicate model install prevented for marketplace installs (same as filesystem installs)
- Why it matters: ModelService.install() already rejects duplicates — verify this works for the marketplace install path too
- Source: M053
- Primary owning slice: M053/S02
- Validation: Clicking Install on an already-installed model shows appropriate error message. No duplicate data written.

### R004 — Registry HTTP fetches must use validate_outbound_url() SSRF guard before making requests
- Class: security
- Status: active
- Description: Registry HTTP fetches must use validate_outbound_url() SSRF guard before making requests
- Why it matters: Prevents SSRF attacks via crafted registry URLs pointing to internal services
- Source: M053
- Primary owning slice: M053/S02
- Validation: All httpx calls to registry/archive URLs preceded by validate_outbound_url(). Verified by grep.

### R005 — Archive downloads verified by SHA-256 hash against registry manifest before extraction
- Class: security
- Status: active
- Description: Archive downloads verified by SHA-256 hash against registry manifest before extraction
- Why it matters: Prevents installation of tampered or corrupted model archives
- Source: M053
- Primary owning slice: M053/S02
- Validation: Download flow computes SHA-256 of downloaded archive and compares to registry.json value. Hash mismatch raises error before extraction.

### R006 — Application must function normally when the model registry is unreachable — no crashes, no blocking waits
- Class: operational
- Status: active
- Description: Application must function normally when the model registry is unreachable — no crashes, no blocking waits
- Why it matters: Network failures and offline environments should not break existing functionality
- Source: M053
- Primary owning slice: M053/S02
- Supporting slices: M053/S03
- Validation: Registry fetch timeout (5s) with graceful fallback to empty catalog. UI shows informative error, not crash. Existing model management continues working.

### R007 — Install progress visible in admin UI during marketplace model download and installation
- Class: functional
- Status: active
- Description: Install progress visible in admin UI during marketplace model download and installation
- Why it matters: Archive downloads may take seconds — user needs visual feedback that something is happening, not a frozen button
- Source: M053
- Primary owning slice: M053/S02
- Validation: Install button shows loading spinner during download+install. Success/error message displayed after completion.

### R008 — Duplicate model install prevented for marketplace installs (same as filesystem installs)
- Class: functional
- Status: active
- Description: Duplicate model install prevented for marketplace installs (same as filesystem installs)
- Why it matters: ModelService.install() already rejects duplicates — verify this works for the marketplace install path too
- Source: M053
- Primary owning slice: M053/S02
- Validation: Clicking Install on an already-installed model shows appropriate error message. No duplicate data written.

## Validated

### R001 — Non-object-contextual panels (inbox, collaboration) lazy-load on reveal rather than on page load — use hx-trigger="revealed" instead of hx-trigger="load"
- Class: non-functional
- Status: validated
- Description: Non-object-contextual panels (inbox, collaboration) lazy-load on reveal rather than on page load — use hx-trigger="revealed" instead of hx-trigger="load"
- Why it matters: Inbox and collaboration panels fire HTTP requests on every page load even when collapsed, adding unnecessary server load and competing with object-tab requests for backend resources
- Source: M049
- Primary owning slice: M049/S03
- Supporting slices: M049/S01
- Validation: Both inbox_panel.html and collaboration_panel.html changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms no load triggers remain in either file. HTTP requests fire only when panels enter viewport via IntersectionObserver. Validated in M049/S03/T03.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | non-functional | validated | M049/S03 | M049/S01 | Both inbox_panel.html and collaboration_panel.html changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms no load triggers remain in either file. HTTP requests fire only when panels enter viewport via IntersectionObserver. Validated in M049/S03/T03. |
| R002 | security | active | M053/S02 | none | Tarfile extraction validates every member name: rejects absolute paths, rejects '..', rejects symlinks. Unit test proves path traversal is blocked. |
| R003 | functional | active | M053/S02 | none | Clicking Install on an already-installed model shows appropriate error message. No duplicate data written. |
| R004 | security | active | M053/S02 | none | All httpx calls to registry/archive URLs preceded by validate_outbound_url(). Verified by grep. |
| R005 | security | active | M053/S02 | none | Download flow computes SHA-256 of downloaded archive and compares to registry.json value. Hash mismatch raises error before extraction. |
| R006 | operational | active | M053/S02 | M053/S03 | Registry fetch timeout (5s) with graceful fallback to empty catalog. UI shows informative error, not crash. Existing model management continues working. |
| R007 | functional | active | M053/S02 | none | Install button shows loading spinner during download+install. Success/error message displayed after completion. |
| R008 | functional | active | M053/S02 | none | Clicking Install on an already-installed model shows appropriate error message. No duplicate data written. |

## Coverage Summary

- Active requirements: 7
- Mapped to slices: 7
- Validated: 1 (R001)
- Unmapped active requirements: 0
