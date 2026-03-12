---
estimated_steps: 5
estimated_files: 3
---

# T01: Fix __MACOSX filtering and empty-stem handling with unit tests

**Slice:** S07 — Obsidian Ideaverse Import
**Milestone:** M002

## Description

The Ideaverse Pro 2.5 ZIP contains 2481 `__MACOSX` resource fork entries (including 905 binary `.md` files) that the current vault scanner and executor don't filter. The `_detect_vault_root()` function only excludes dot-prefixed entries, so `__MACOSX/` passes through and corrupts scan results. Additionally, 3 `.md` files in the vault have empty stems (e.g. `Books/.md`), which would create title-less objects that collide in the wiki-link resolution map.

This task fixes both issues in scanner.py and executor.py, then adds unit tests to prevent regression. Tests use temporary directory structures — no Docker or triplestore required.

## Steps

1. In `scanner.py` `_detect_vault_root()`: add `__MACOSX` to the visible entries filter (exclude entries where `e.name == "__MACOSX"`). In `_do_scan()` `os.walk()` dirnames pruning: add `__MACOSX` alongside the existing dot-prefix filter (`dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__MACOSX"]`).
2. In `executor.py` `_detect_vault_root()`: same `__MACOSX` exclusion. In `execute()` md_files filtering: add `__MACOSX` to the hidden-parts check (`any(part.startswith(".") or part == "__MACOSX" for part in ...)`).
3. In `scanner.py` `_do_scan()`: after collecting `md_files`, filter out entries with empty stems (`md_files = [f for f in md_files if f.stem]`). In `executor.py` `execute()`: same empty-stem filter after collecting md_files.
4. Create `backend/tests/test_obsidian_scanner.py` with unit tests:
   - `test_detect_vault_root_excludes_macosx`: create temp dir with `__MACOSX/` and `VaultName/` and `.obsidian/` — assert vault root is `VaultName/`, not `extract_path`
   - `test_detect_vault_root_single_dir_no_macosx`: create temp dir with just `VaultName/.obsidian/` — assert vault root is `VaultName/`
   - `test_scan_excludes_macosx_files`: create temp dir with `VaultName/.obsidian/`, `VaultName/note.md`, `__MACOSX/VaultName/._note.md` — run scan, assert only 1 markdown file found
   - `test_scan_skips_empty_stem_files`: create temp dir with `VaultName/.obsidian/`, `VaultName/Notes/good.md`, `VaultName/Notes/.md` — run scan, assert only `good.md` is counted
   - `test_executor_detect_vault_root_excludes_macosx`: same as scanner test but using executor's `_detect_vault_root()`
5. Run tests to verify all pass.

## Must-Haves

- [ ] `__MACOSX` excluded from `_detect_vault_root()` visible entries in both scanner.py and executor.py
- [ ] `__MACOSX` excluded from `os.walk()` dirnames in scanner.py `_do_scan()`
- [ ] `__MACOSX` excluded from `rglob` results in executor.py `execute()`
- [ ] Empty-stem `.md` files filtered in both scanner and executor
- [ ] Unit tests cover all four scenarios (vault root detection, walk exclusion, empty-stem skip, executor vault root)

## Verification

- `cd backend && python -m pytest tests/test_obsidian_scanner.py -v` — all tests pass
- Manual code review: both `_detect_vault_root()` implementations filter `__MACOSX`; both file-walking loops exclude `__MACOSX` and empty-stem files

## Observability Impact

- Signals added/changed: Scanner now emits a `ScanWarning` with category `skipped_empty_stem` for skipped empty-stem files, so the user sees them in scan results
- How a future agent inspects this: Run the unit test file; check scan warnings in scan result JSON
- Failure state exposed: If `__MACOSX` filtering fails, scan results will show ~2x the expected file count (visible in `VaultScanResult.markdown_files`)

## Inputs

- `backend/app/obsidian/scanner.py` — current `_detect_vault_root()` and `_do_scan()` implementations with the `__MACOSX` bug
- `backend/app/obsidian/executor.py` — current `_detect_vault_root()` and `execute()` implementations with the same bug
- `backend/tests/conftest.py` — existing test infrastructure (SECRET_KEY env var setup, serializer reset fixture)
- S07-RESEARCH.md — analysis of 2481 `__MACOSX` entries and 3 empty-stem files in the Ideaverse vault

## Expected Output

- `backend/app/obsidian/scanner.py` — `_detect_vault_root()` excludes `__MACOSX`; `_do_scan()` prunes `__MACOSX` from dirnames and filters empty-stem files
- `backend/app/obsidian/executor.py` — `_detect_vault_root()` excludes `__MACOSX`; `execute()` filters `__MACOSX` parts and empty-stem files
- `backend/tests/test_obsidian_scanner.py` — 5+ unit tests covering vault root detection, walk exclusion, empty-stem handling
