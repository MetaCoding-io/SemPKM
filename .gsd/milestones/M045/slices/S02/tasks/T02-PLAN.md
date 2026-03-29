---
estimated_steps: 36
estimated_files: 4
skills_used: []
---

# T02: ZIP bomb protection for Obsidian and Notion importers

Create a shared ZIP validation utility and wire it into both importers to reject oversized or suspicious archives before extraction.

## Steps

1. Create `backend/app/security/zip_validator.py`:
   - Function `validate_zip_contents(zip_path: Path, max_uncompressed_mb: int = 2048, max_files: int = 50000) -> None`
   - Uses `zipfile.ZipFile(zip_path).infolist()` to sum `file_size` and count entries BEFORE calling extractall
   - Raises `ValueError('ZIP archive uncompressed size ({size_mb:.1f} MB) exceeds limit ({max_uncompressed_mb} MB)')` if total `file_size` exceeds limit
   - Raises `ValueError('ZIP archive contains {count} files, exceeding limit of {max_files}')` if file count exceeds limit
   - Check compression ratio: if any single entry has `compress_size > 0` and `file_size / compress_size > 100`, raise `ValueError('Suspicious compression ratio ({ratio:.0f}:1) detected in {entry.filename}')`
   - Log warnings at `logger.warning` for suspicious but passing archives (ratio > 50)

2. Edit `backend/app/obsidian/router.py`:
   - Import `validate_zip_contents` from `app.security.zip_validator`
   - In `_write_and_extract()`, after writing the ZIP to disk and before `zf.extractall()`, call `validate_zip_contents(zip_path)`
   - Catch `ValueError` from validation, clean up files, return 400 HTML error with the validation message

3. Edit `backend/app/notion/router.py`:
   - Same changes as obsidian router — import, validate before extract, catch ValueError

4. Create `backend/tests/test_zip_validator.py`:
   - Test: normal ZIP passes validation
   - Test: ZIP exceeding uncompressed size limit raises ValueError
   - Test: ZIP exceeding file count limit raises ValueError
   - Test: ZIP with suspicious compression ratio raises ValueError
   - Test: empty ZIP passes validation
   - Test: custom limits are respected
   - Use `zipfile.ZipFile` to create test fixtures in-memory or tmpdir

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| zipfile.ZipFile.infolist() | Re-raise as ValueError with context | N/A (local I/O) | Caught by existing BadZipFile handler |

## Negative Tests

- Malformed inputs: corrupt ZIP file (caught by existing BadZipFile handler, not this code)
- Error paths: ZIP with zero-byte compressed entries (ratio calculation division by zero — guard with `compress_size > 0`)
- Boundary conditions: ZIP exactly at limit passes, ZIP 1 byte over limit fails

## Must-Haves

- [ ] `validate_zip_contents()` checks uncompressed size, file count, and compression ratio
- [ ] Both Obsidian and Notion importers call validator before extractall
- [ ] ValueError from validator returns 400 with descriptive error message
- [ ] Unit tests cover all three rejection criteria plus happy path

## Inputs

- ``backend/app/security/__init__.py` — existing security package from S01`
- ``backend/app/obsidian/router.py` — lines 140-170, _write_and_extract with bare extractall`
- ``backend/app/notion/router.py` — lines 168-198, identical _write_and_extract pattern`

## Expected Output

- ``backend/app/security/zip_validator.py` — ZIP validation utility with size, count, ratio checks`
- ``backend/app/obsidian/router.py` — calls validate_zip_contents before extractall`
- ``backend/app/notion/router.py` — calls validate_zip_contents before extractall`
- ``backend/tests/test_zip_validator.py` — unit tests for all validation paths`

## Verification

cd backend && python -m pytest tests/test_zip_validator.py -v
