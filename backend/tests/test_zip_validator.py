"""Tests for ZIP bomb protection validator.

Covers happy path, all three rejection criteria (uncompressed size,
file count, compression ratio), boundary conditions, empty ZIP,
and custom limit overrides.
"""

import zipfile
from pathlib import Path

import pytest

from app.security.zip_validator import validate_zip_contents


def _create_zip(tmp_path: Path, files: dict[str, bytes]) -> Path:
    """Create a real ZIP archive in tmp_path with the given filename→content map."""
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zip_path


def _create_stored_zip(tmp_path: Path, files: dict[str, bytes]) -> Path:
    """Create a ZIP with ZIP_STORED (no compression) — ratio is always ~1:1."""
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zip_path


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------


class TestHappyPath:
    def test_normal_zip_passes(self, tmp_path: Path):
        """A small ZIP with a few files passes without error."""
        files = {
            "readme.md": b"# Hello\nThis is a readme.",
            "notes/note1.md": b"Some content here.",
            "notes/note2.md": b"More content.",
        }
        zip_path = _create_zip(tmp_path, files)
        # Should not raise
        validate_zip_contents(zip_path)

    def test_empty_zip_passes(self, tmp_path: Path):
        """An empty ZIP archive passes validation."""
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w"):
            pass  # no entries
        validate_zip_contents(zip_path)


# --------------------------------------------------------------------------
# Uncompressed size limit
# --------------------------------------------------------------------------


class TestUncompressedSizeLimit:
    def test_exceeding_size_limit_raises(self, tmp_path: Path):
        """ZIP whose uncompressed size exceeds the limit is rejected."""
        # Use a small custom limit (1 MB) and create content over that
        content = b"x" * (512 * 1024)  # 512 KB per file
        files = {
            "big1.bin": content,
            "big2.bin": content,
            "big3.bin": content,  # total: 1.5 MB
        }
        zip_path = _create_stored_zip(tmp_path, files)

        with pytest.raises(ValueError, match=r"uncompressed size.*exceeds limit"):
            validate_zip_contents(zip_path, max_uncompressed_mb=1)

    def test_exactly_at_limit_passes(self, tmp_path: Path):
        """ZIP exactly at the uncompressed size limit passes."""
        # 1 MB limit, content exactly 1 MB
        content = b"x" * (1024 * 1024)
        files = {"exact.bin": content}
        zip_path = _create_stored_zip(tmp_path, files)
        # Should not raise
        validate_zip_contents(zip_path, max_uncompressed_mb=1)

    def test_one_byte_over_limit_fails(self, tmp_path: Path):
        """ZIP one byte over the uncompressed size limit is rejected."""
        content = b"x" * (1024 * 1024 + 1)
        files = {"over.bin": content}
        zip_path = _create_stored_zip(tmp_path, files)

        with pytest.raises(ValueError, match=r"uncompressed size.*exceeds limit"):
            validate_zip_contents(zip_path, max_uncompressed_mb=1)


# --------------------------------------------------------------------------
# File count limit
# --------------------------------------------------------------------------


class TestFileCountLimit:
    def test_exceeding_file_count_raises(self, tmp_path: Path):
        """ZIP with too many entries is rejected."""
        files = {f"file_{i}.txt": b"x" for i in range(11)}
        zip_path = _create_zip(tmp_path, files)

        with pytest.raises(ValueError, match=r"contains 11 files.*exceeding limit of 10"):
            validate_zip_contents(zip_path, max_files=10)

    def test_exactly_at_count_limit_passes(self, tmp_path: Path):
        """ZIP with exactly max_files entries passes."""
        files = {f"file_{i}.txt": b"x" for i in range(10)}
        zip_path = _create_zip(tmp_path, files)
        # Should not raise
        validate_zip_contents(zip_path, max_files=10)


# --------------------------------------------------------------------------
# Compression ratio
# --------------------------------------------------------------------------


class TestCompressionRatio:
    def test_suspicious_ratio_raises(self, tmp_path: Path):
        """ZIP entry with extreme compression ratio is rejected.

        A long run of identical bytes compresses extremely well with DEFLATE,
        producing a ratio well above 100:1.
        """
        # 10 MB of zeroes compresses to ~10 KB with DEFLATE → ratio ~1000:1
        bomb_content = b"\x00" * (10 * 1024 * 1024)
        files = {"bomb.bin": bomb_content}
        zip_path = _create_zip(tmp_path, files)

        with pytest.raises(ValueError, match=r"Suspicious compression ratio"):
            validate_zip_contents(zip_path, max_ratio=100)

    def test_moderate_ratio_passes(self, tmp_path: Path):
        """ZIP entry with moderate compression ratio passes."""
        # Repetitive but not extreme content
        content = (b"abcdefghij" * 100)  # 1 KB, compresses ~10:1
        files = {"moderate.txt": content}
        zip_path = _create_zip(tmp_path, files)
        # Should not raise with default ratio limit
        validate_zip_contents(zip_path)

    def test_zero_compress_size_skipped(self, tmp_path: Path):
        """Entries with compress_size == 0 (e.g. directories) don't trigger division by zero."""
        # Directories in ZIP have compress_size=0 and file_size=0
        zip_path = tmp_path / "dirs.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add a directory entry
            zf.mkdir("empty_dir/")
            zf.writestr("file.txt", "hello")
        validate_zip_contents(zip_path)


# --------------------------------------------------------------------------
# Custom limits
# --------------------------------------------------------------------------


class TestCustomLimits:
    def test_custom_size_limit(self, tmp_path: Path):
        """Custom max_uncompressed_mb is respected."""
        content = b"x" * (6 * 1024 * 1024)  # 6 MB
        files = {"data.bin": content}
        zip_path = _create_stored_zip(tmp_path, files)

        # 5 MB limit: should fail
        with pytest.raises(ValueError, match=r"uncompressed size"):
            validate_zip_contents(zip_path, max_uncompressed_mb=5)

        # 10 MB limit: should pass
        validate_zip_contents(zip_path, max_uncompressed_mb=10)

    def test_custom_file_count_limit(self, tmp_path: Path):
        """Custom max_files is respected."""
        files = {f"f{i}.txt": b"x" for i in range(5)}
        zip_path = _create_zip(tmp_path, files)

        # 3 file limit: should fail
        with pytest.raises(ValueError, match=r"contains 5 files"):
            validate_zip_contents(zip_path, max_files=3)

        # 10 file limit: should pass
        validate_zip_contents(zip_path, max_files=10)

    def test_custom_ratio_limit(self, tmp_path: Path):
        """Custom max_ratio is respected."""
        # Highly compressible content
        content = b"\x00" * (1024 * 1024)  # 1 MB of zeroes
        files = {"zeros.bin": content}
        zip_path = _create_zip(tmp_path, files)

        # Very strict ratio (5:1): should fail
        with pytest.raises(ValueError, match=r"Suspicious compression ratio"):
            validate_zip_contents(zip_path, max_ratio=5)

        # Very lenient ratio (10000:1): should pass
        validate_zip_contents(zip_path, max_ratio=10000)


# --------------------------------------------------------------------------
# Error message quality
# --------------------------------------------------------------------------


class TestErrorMessages:
    def test_size_error_includes_actual_and_limit(self, tmp_path: Path):
        """Size rejection message includes actual size and limit."""
        content = b"x" * (2 * 1024 * 1024)  # 2 MB
        files = {"big.bin": content}
        zip_path = _create_stored_zip(tmp_path, files)

        with pytest.raises(ValueError) as exc_info:
            validate_zip_contents(zip_path, max_uncompressed_mb=1)

        msg = str(exc_info.value)
        assert "2.0 MB" in msg
        assert "1 MB" in msg

    def test_count_error_includes_actual_and_limit(self, tmp_path: Path):
        """File count rejection message includes actual count and limit."""
        files = {f"f{i}.txt": b"x" for i in range(20)}
        zip_path = _create_zip(tmp_path, files)

        with pytest.raises(ValueError) as exc_info:
            validate_zip_contents(zip_path, max_files=10)

        msg = str(exc_info.value)
        assert "20 files" in msg
        assert "limit of 10" in msg

    def test_ratio_error_includes_filename(self, tmp_path: Path):
        """Ratio rejection message includes the offending filename."""
        content = b"\x00" * (10 * 1024 * 1024)
        files = {"evil/nested/bomb.bin": content}
        zip_path = _create_zip(tmp_path, files)

        with pytest.raises(ValueError) as exc_info:
            validate_zip_contents(zip_path, max_ratio=100)

        msg = str(exc_info.value)
        assert "evil/nested/bomb.bin" in msg
