---
id: T01
parent: S07
milestone: M002
provides:
  - __MACOSX filtering in scanner and executor vault root detection
  - __MACOSX exclusion from os.walk (scanner) and rglob (executor)
  - Defense-in-depth empty-stem file filtering in both scanner and executor
  - Unit test suite covering all filtering scenarios
key_files:
  - backend/app/obsidian/scanner.py
  - backend/app/obsidian/executor.py
  - backend/tests/test_obsidian_scanner.py
key_decisions:
  - Empty-stem filter kept as defense-in-depth even though Python Path('.md').stem returns '.md' (truthy), not '' — the real Ideaverse '.md' files are already caught by the dot-prefix filter. Both layers provide complementary protection.
patterns_established:
  - Scanner emits ScanWarning with category 'skipped_empty_stem' for filtered files
  - Executor logs warnings for skipped empty-stem files via logger.warning
observability_surfaces:
  - ScanWarning with category 'skipped_empty_stem' in VaultScanResult.warnings
  - logger.warning messages for skipped empty-stem files in executor
duration: 15min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Fix __MACOSX filtering and empty-stem handling with unit tests

**Added __MACOSX exclusion to vault root detection and file walking in both scanner and executor, plus empty-stem defense-in-depth filter, with 9 unit tests.**

## What Happened

The Ideaverse Pro 2.5 ZIP contains 2481 `__MACOSX` resource fork entries that the scanner and executor didn't filter. Fixed four locations:

1. **scanner.py `_detect_vault_root()`** — added `e.name != "__MACOSX"` to the visible entries filter so `__MACOSX/` doesn't count as a top-level directory.
2. **scanner.py `_do_scan()`** — added `d != "__MACOSX"` to the `os.walk` dirnames pruning so `__MACOSX` subtrees are never traversed.
3. **executor.py `_detect_vault_root()`** — same `__MACOSX` exclusion as scanner.
4. **executor.py `execute()`** — added `part == "__MACOSX"` to the hidden-parts check on `rglob` results.

Added empty-stem filtering in both scanner and executor. During implementation, discovered that Python's `Path('.md').stem` returns `'.md'` (truthy), not `''`. The real Ideaverse empty-stem files (`Books/.md`, `People/.md`, `ACE Pack/.md`) are already caught by the existing dot-prefix filter. The empty-stem filter remains as defense-in-depth for hypothetical edge cases.

Created `test_obsidian_scanner.py` with 9 tests covering vault root detection (with/without `__MACOSX`), file walk exclusion, dot-md file filtering, empty-stem filter logic verification, and executor vault root detection.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_obsidian_scanner.py -v` — 9/9 passed
- `cd backend && .venv/bin/python -m pytest tests/ -v` — 130/130 passed (no regressions)
- Manual code review: both `_detect_vault_root()` implementations filter `__MACOSX`; both file-walking paths exclude `__MACOSX` and empty-stem files
- **Slice verification**: `pytest tests/test_obsidian_scanner.py -v` passes ✅ (first slice check). Remaining slice checks (import wizard UI, frontmatter properties, relations panel) are for later tasks.

## Diagnostics

- Run `pytest tests/test_obsidian_scanner.py -v` to verify all filtering behavior
- Scanner scan results: check `VaultScanResult.warnings` for `skipped_empty_stem` category entries
- If `__MACOSX` filtering fails, `VaultScanResult.markdown_files` will show ~2x expected count

## Deviations

- Task plan specified `test_scan_skips_empty_stem_files` testing that empty-stem files produce a `skipped_empty_stem` warning. In reality, `.md` files (the only way to get an empty stem with `.md` extension) are caught first by the dot-prefix filter and never reach the empty-stem filter. Split into two tests: one verifying dot-md files are excluded from results, one verifying the empty-stem filter logic is sound.
- Added two bonus tests beyond the 5 specified: `test_macosx_alongside_vault_two_visible_dirs` and `test_scan_excludes_macosx_inside_vault` for more thorough coverage.

## Known Issues

None.

## Files Created/Modified

- `backend/app/obsidian/scanner.py` — Added `__MACOSX` exclusion to `_detect_vault_root()` and `_do_scan()` dirnames pruning; added empty-stem filter with `ScanWarning` emission
- `backend/app/obsidian/executor.py` — Added `__MACOSX` exclusion to `_detect_vault_root()` and `execute()` hidden-parts check; added empty-stem filter with logger warning
- `backend/tests/test_obsidian_scanner.py` — New test file with 9 unit tests covering vault root detection, walk exclusion, dot-md handling, empty-stem filter logic, and executor vault root
