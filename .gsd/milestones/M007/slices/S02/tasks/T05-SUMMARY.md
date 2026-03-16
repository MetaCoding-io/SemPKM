---
id: T05
parent: S02
milestone: M007
provides:
  - Unit tests for VFS slug generation edge cases (15 tests) and file map collision dedup (11 tests)
  - Path contract documentation in docs/guide/23-vfs.md covering forward/reverse mapping, collision dedup, and filename instability
key_files:
  - backend/tests/test_vfs_path_contract.py
  - docs/guide/23-vfs.md
key_decisions:
  - No extraction needed — _slugify and _build_file_map_from_bindings are already module-level functions, directly importable for testing
  - Plan assumed sequential numeric dedup (-2, -3); actual implementation uses IRI SHA-256 hash prefix (--{hash[:6]}) — tests written against actual behavior
patterns_established:
  - Test helper _make_binding() for constructing SPARQL binding dicts in VFS tests
observability_surfaces:
  - none — documentation and tests only, no runtime changes
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T05: Path contract documentation and slug/dedup tests

**Wrote 26 unit tests for `_slugify` and `_build_file_map_from_bindings`, and documented the VFS path contract (forward/reverse mapping, collision dedup via IRI hash, filename instability caveat) in `docs/guide/23-vfs.md`.**

## What Happened

Identified the two key functions in `mount_collections.py`:
- `_slugify(text)` — lowercases, replaces non-`[a-z0-9]` with hyphens, collapses consecutive hyphens, strips leading/trailing hyphens, falls back to `"untitled"` for empty input
- `_build_file_map_from_bindings(bindings)` — builds filename→{iri, label, type_iri} map, deduplicating collisions by appending `--{sha256(iri)[:6]}` suffix to all colliding filenames

Both were already module-level (not buried in class methods), so no extraction was needed.

Wrote `test_vfs_path_contract.py` with two test classes:
- **TestSlugify** (15 tests): normal, lowercase, mixed case, unicode, special chars, empty string, only-special-chars, only-whitespace, leading/trailing hyphens, consecutive hyphens, idempotent, numbers, long labels, single char, numeric-only
- **TestBuildFileMap** (11 tests): single object, no collision, 2-way collision with hash suffix, 3-way collision, collision isolation (non-colliding unaffected), type_iri preservation, missing type_iri default, empty bindings, .md extension always, reverse lookup, unicode label preservation

Added "Path Contract" section to `docs/guide/23-vfs.md` covering forward mapping (label→slug→filename), collision dedup (IRI hash suffix), reverse mapping (per-request file_map, no persistent index), and filename instability caveat.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_vfs_path_contract.py -v` — **26/26 passed** (0.13s)
- `cd backend && .venv/bin/python -m pytest tests/test_vfs_scope.py -v` — **21/21 passed** (slice-level check)
- `docs/guide/23-vfs.md` contains "Path Contract" section with forward/reverse mapping examples and instability caveat
- `savedQueryId` only appears in migration script (grep confirmed)

### Slice-level verification status (T05 is final task):
- ✅ `test_vfs_scope.py` — 21/21 passed
- ✅ `test_vfs_path_contract.py` — 26/26 passed
- ⬜ Manual/browser: mount form type multi-select, preview with saved query — not verifiable without running containers
- ✅ Grep: zero `savedQueryId` in Python/template/JS (except migration script)
- ⬜ Diagnostic: build_scope_filter with invalid IRI type_filter — requires running triplestore
- ⬜ Diagnostic: preview endpoint 404 on missing scope_query — requires running containers

## Diagnostics

- **Test diagnostic:** `cd backend && .venv/bin/python -m pytest tests/test_vfs_path_contract.py -v` — runs slug/dedup contract tests
- **No runtime changes** — this task adds documentation and tests only

## Deviations

- Plan assumed collision dedup uses sequential numbering (`-2`, `-3`). Actual implementation uses IRI SHA-256 hash prefix (`--{hash[:6]}`). Documentation and tests written against the actual behavior.
- Plan step 4 (extract slug function) was unnecessary — both functions are already module-level and directly importable.

## Known Issues

- `_slugify` does not truncate long labels (300+ chars produce 300+ char filenames). Documented in test (`test_long_label_not_truncated`) as current behavior. Could hit filesystem path length limits on deeply nested mounts.
- Unicode handling strips all non-ASCII to hyphens (e.g., `"Über"` → `"ber"`). This is lossy but safe for filesystem compatibility.

## Files Created/Modified

- `backend/tests/test_vfs_path_contract.py` — new: 26 unit tests for slug generation and collision dedup
- `docs/guide/23-vfs.md` — added Path Contract section (forward/reverse mapping, dedup, instability caveat)
- `.gsd/milestones/M007/slices/S02/tasks/T05-PLAN.md` — added Observability Impact section
