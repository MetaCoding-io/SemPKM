---
estimated_steps: 34
estimated_files: 2
skills_used: []
---

# T01: Implement tarfile validator with bomb and traversal protection

Create `backend/app/security/tar_validator.py` adapting the existing `validate_zip_contents()` pattern for tar.gz archives. Must reject: path traversal (absolute paths, `..` components), symlinks, tar bombs (oversized archives, excessive file count, suspicious compression ratios). Use Python 3.12's `tarfile.data_filter` for safe extraction semantics.

Also create comprehensive unit tests at `backend/tests/test_tar_validator.py` following the pattern of `test_zip_validator.py`.

## Steps

1. Read `backend/app/security/zip_validator.py` for the pattern — adapt the three-check structure (total size, file count, per-entry ratio) plus add tarfile-specific checks (path traversal, symlinks, absolute paths)
2. Create `backend/app/security/tar_validator.py` with `validate_tar_contents(tar_path, *, max_uncompressed_mb=2048, max_files=50000, max_ratio=100) -> None` that raises `ValueError` on any failure. Also add `safe_extract(tar_path, dest_dir)` that validates then extracts using `tarfile.data_filter`
3. Checks to implement:
   - Total uncompressed size (sum of member.size) vs max_uncompressed_mb
   - File count vs max_files
   - Per-entry compression ratio (member.size / tar file size * member count approximation) — tar doesn't have per-entry compressed size like zip, so use total archive size / member count as heuristic
   - Reject members with absolute paths (`member.name.startswith('/')`)
   - Reject members with `..` path components (`'..' in member.name.split('/')`)
   - Reject symlinks (`member.issym()`) and hardlinks (`member.islnk()`)
4. Create `backend/tests/test_tar_validator.py` with tests for: valid archive passes, path traversal rejected, absolute paths rejected, symlinks rejected, oversized archive rejected, too many files rejected, empty archive passes, custom limits
5. Run tests to confirm all pass

## Must-Haves

- [x] `validate_tar_contents()` rejects path traversal via `..` components
- [x] `validate_tar_contents()` rejects absolute paths
- [x] `validate_tar_contents()` rejects symlinks and hardlinks
- [x] `validate_tar_contents()` rejects tar bombs (size, count)
- [x] `safe_extract()` uses `tarfile.data_filter` for Python 3.12+ safe extraction
- [x] Unit tests cover all rejection criteria and happy path

## Verification

- `cd backend && python -m pytest tests/test_tar_validator.py -v` — all tests pass

## Negative Tests

- Path traversal: archive with `../../etc/passwd` member → ValueError
- Absolute path: archive with `/etc/passwd` member → ValueError
- Symlink: archive with symlink member → ValueError
- Oversized: archive exceeding max_uncompressed_mb → ValueError
- Too many files: archive exceeding max_files → ValueError
- Empty archive: passes validation (zero files is valid)

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Filesystem (tar file) | ValueError with descriptive message | N/A | ValueError — corrupt tar raises tarfile.ReadError, caught and re-raised as ValueError |

## Inputs

- `backend/app/security/zip_validator.py`
- `backend/tests/test_zip_validator.py`

## Expected Output

- `backend/app/security/tar_validator.py`
- `backend/tests/test_tar_validator.py`

## Verification

cd backend && python -m pytest tests/test_tar_validator.py -v
