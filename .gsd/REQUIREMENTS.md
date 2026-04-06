# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R003 — Duplicate model install prevented for marketplace installs (same as filesystem installs)
- Class: functional
- Status: active
- Description: Duplicate model install prevented for marketplace installs (same as filesystem installs)
- Why it matters: ModelService.install() already rejects duplicates — verify this works for the marketplace install path too
- Source: M053
- Primary owning slice: M053/S02
- Validation: Clicking Install on an already-installed model shows appropriate error message. No duplicate data written.

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

### R009 — Explorer tree displays clean type labels without raw model IDs or ' Shape' suffixes
- Class: functional
- Status: active
- Description: Explorer tree displays clean type labels without raw model IDs or ' Shape' suffixes
- Why it matters: Current by-type mode shows raw model IDs like 'basic-pkm (by-type)' in the dropdown and ' Shape' suffixes on type nodes — confusing for non-technical users
- Source: M054
- Primary owning slice: M054/S01
- Validation: Explorer tree type nodes show human-readable labels (e.g. 'Task', 'Contact', 'Note') without suffixes. ShapesService.get_types() already strips suffixes — verify it's used in all tree rendering paths.

### R010 — Explorer configurations support composable filter (by type), group-by (by property/type/tag), and sort (label/date/property) layers producing correct SPARQL queries
- Class: functional
- Status: active
- Description: Explorer configurations support composable filter (by type), group-by (by property/type/tag), and sort (label/date/property) layers producing correct SPARQL queries
- Why it matters: The current explorer has a flat dropdown with three hardcoded modes — users can't filter to specific types, group by arbitrary properties, or sort within groups. Composable layers are the core value of M054.
- Source: M054
- Primary owning slice: M054/S01
- Validation: Create config with filter=Tasks, group=Status, sort=Due Date → explorer tree shows type-filtered objects grouped by status values with correct sort order. Unit tests prove SPARQL generation for multi-level configs.

### R011 — Explorer configurations persist server-side and survive browser restart — users can create, name, update, and delete saved configs
- Class: functional
- Status: active
- Description: Explorer configurations persist server-side and survive browser restart — users can create, name, update, and delete saved configs
- Why it matters: localStorage-only storage loses configs on browser clear and isn't portable across devices. Server-side persistence follows the DashboardSpec pattern.
- Source: M054
- Primary owning slice: M054/S02
- Supporting slices: M054/S01
- Validation: Save a named config → close browser → reopen → config available in selector and renders correct tree. CRUD API returns proper responses.

### R012 — Multiple OBJECTS explorer sections can be open simultaneously with different configurations
- Class: functional
- Status: active
- Description: Multiple OBJECTS explorer sections can be open simultaneously with different configurations
- Why it matters: Users need to compare objects across different views — e.g. Tasks by Status alongside Contacts by Company — without switching back and forth
- Source: M054
- Primary owning slice: M054/S02
- Validation: Click Duplicate on OBJECTS section → second section appears with independent config → changing one doesn't affect the other. Both trees render correctly.

### R013 — Existing explorer modes (by-type, hierarchy, by-tag) remain accessible as built-in presets after the composable config system replaces the mode dropdown
- Class: functional
- Status: active
- Description: Existing explorer modes (by-type, hierarchy, by-tag) remain accessible as built-in presets after the composable config system replaces the mode dropdown
- Why it matters: Backward compatibility — users who rely on the current modes shouldn't lose them. Presets also serve as examples for custom configs.
- Source: M054
- Primary owning slice: M054/S02
- Validation: Config selector shows By Type, Hierarchy, By Tag as preset options. Selecting each produces the same tree as the current mode dropdown.

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

### R002 — Tarfile extraction must validate all member paths are relative and within expected structure — no path traversal
- Class: security
- Status: validated
- Description: Tarfile extraction must validate all member paths are relative and within expected structure — no path traversal
- Why it matters: Prevents path traversal attacks (../../etc/passwd) via malicious model archives
- Source: M053
- Primary owning slice: M053/S02
- Validation: 33 unit tests in test_tar_validator.py prove path traversal, absolute paths, symlinks, hardlinks all rejected with ValueError. safe_extract() uses Python 3.12 data_filter for defense-in-depth. Validated in M053/S02/T01.

### R004 — Registry HTTP fetches must use validate_outbound_url() SSRF guard before making requests
- Class: security
- Status: validated
- Description: Registry HTTP fetches must use validate_outbound_url() SSRF guard before making requests
- Why it matters: Prevents SSRF attacks via crafted registry URLs pointing to internal services
- Source: M053
- Primary owning slice: M053/S02
- Validation: validate_outbound_url() called on both registry URL (catalog fetch) and archive URL (download) in marketplace.py. SSRF guard unit tests confirm blocking behavior. Validated in M053/S02/T02.

### R005 — Archive downloads verified by SHA-256 hash against registry manifest before extraction
- Class: security
- Status: validated
- Description: Archive downloads verified by SHA-256 hash against registry manifest before extraction
- Why it matters: Prevents installation of tampered or corrupted model archives
- Source: M053
- Primary owning slice: M053/S02
- Validation: SHA-256 computed on downloaded bytes and compared to registry manifest value. test_sha256_mismatch_raises proves hash mismatch blocks extraction. Validated in M053/S02/T02.

### R006 — Application must function normally when the model registry is unreachable — no crashes, no blocking waits
- Class: operational
- Status: validated
- Description: Application must function normally when the model registry is unreachable — no crashes, no blocking waits
- Why it matters: Network failures and offline environments should not break existing functionality
- Source: M053
- Primary owning slice: M053/S02
- Supporting slices: M053/S03
- Validation: 5s httpx timeout with empty-list fallback. test_timeout_returns_empty_list and test_http_error_returns_empty_list prove graceful degradation. S03 check_updates() returns empty dict when disabled/unreachable. Validated in M053/S02/T02 + M053/S03/T01.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | non-functional | validated | M049/S03 | M049/S01 | Both inbox_panel.html and collaboration_panel.html changed from hx-trigger="load" to hx-trigger="revealed". Grep confirms no load triggers remain in either file. HTTP requests fire only when panels enter viewport via IntersectionObserver. Validated in M049/S03/T03. |
| R002 | security | validated | M053/S02 | none | 33 unit tests in test_tar_validator.py prove path traversal, absolute paths, symlinks, hardlinks all rejected with ValueError. safe_extract() uses Python 3.12 data_filter for defense-in-depth. Validated in M053/S02/T01. |
| R003 | functional | active | M053/S02 | none | Clicking Install on an already-installed model shows appropriate error message. No duplicate data written. |
| R004 | security | validated | M053/S02 | none | validate_outbound_url() called on both registry URL (catalog fetch) and archive URL (download) in marketplace.py. SSRF guard unit tests confirm blocking behavior. Validated in M053/S02/T02. |
| R005 | security | validated | M053/S02 | none | SHA-256 computed on downloaded bytes and compared to registry manifest value. test_sha256_mismatch_raises proves hash mismatch blocks extraction. Validated in M053/S02/T02. |
| R006 | operational | validated | M053/S02 | M053/S03 | 5s httpx timeout with empty-list fallback. test_timeout_returns_empty_list and test_http_error_returns_empty_list prove graceful degradation. S03 check_updates() returns empty dict when disabled/unreachable. Validated in M053/S02/T02 + M053/S03/T01. |
| R007 | functional | active | M053/S02 | none | Install button shows loading spinner during download+install. Success/error message displayed after completion. |
| R008 | functional | active | M053/S02 | none | Clicking Install on an already-installed model shows appropriate error message. No duplicate data written. |
| R009 | functional | active | M054/S01 | none | Explorer tree type nodes show human-readable labels (e.g. 'Task', 'Contact', 'Note') without suffixes. ShapesService.get_types() already strips suffixes — verify it's used in all tree rendering paths. |
| R010 | functional | active | M054/S01 | none | Create config with filter=Tasks, group=Status, sort=Due Date → explorer tree shows type-filtered objects grouped by status values with correct sort order. Unit tests prove SPARQL generation for multi-level configs. |
| R011 | functional | active | M054/S02 | M054/S01 | Save a named config → close browser → reopen → config available in selector and renders correct tree. CRUD API returns proper responses. |
| R012 | functional | active | M054/S02 | none | Click Duplicate on OBJECTS section → second section appears with independent config → changing one doesn't affect the other. Both trees render correctly. |
| R013 | functional | active | M054/S02 | none | Config selector shows By Type, Hierarchy, By Tag as preset options. Selecting each produces the same tree as the current mode dropdown. |

## Coverage Summary

- Active requirements: 8
- Mapped to slices: 8
- Validated: 5 (R001, R002, R004, R005, R006)
- Unmapped active requirements: 0
