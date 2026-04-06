"""Tests for tar archive protection validator.

Covers happy path, all six rejection criteria (path traversal, absolute
paths, symlinks, hardlinks, uncompressed size, file count, compression
ratio), boundary conditions, empty archive, corrupt archive, custom
limit overrides, and safe_extract().
"""

import io
import os
import tarfile
from pathlib import Path

import pytest

from app.security.tar_validator import safe_extract, validate_tar_contents


def _create_tar_gz(tmp_path: Path, files: dict[str, bytes], name: str = "test.tar.gz") -> Path:
    """Create a real gzipped tar archive with the given filename→content map."""
    tar_path = tmp_path / name
    with tarfile.open(tar_path, "w:gz") as tf:
        for fname, content in files.items():
            info = tarfile.TarInfo(name=fname)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return tar_path


def _create_tar_uncompressed(tmp_path: Path, files: dict[str, bytes]) -> Path:
    """Create an uncompressed tar archive — ratio is always ~1:1."""
    tar_path = tmp_path / "test.tar"
    with tarfile.open(tar_path, "w") as tf:
        for fname, content in files.items():
            info = tarfile.TarInfo(name=fname)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return tar_path


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------


class TestHappyPath:
    def test_normal_tar_passes(self, tmp_path: Path):
        """A small tar.gz with a few files passes without error."""
        files = {
            "readme.md": b"# Hello\nThis is a readme.",
            "notes/note1.md": b"Some content here.",
            "notes/note2.md": b"More content.",
        }
        tar_path = _create_tar_gz(tmp_path, files)
        validate_tar_contents(tar_path)

    def test_empty_tar_passes(self, tmp_path: Path):
        """An empty tar archive passes validation."""
        tar_path = tmp_path / "empty.tar.gz"
        with tarfile.open(tar_path, "w:gz"):
            pass  # no entries
        validate_tar_contents(tar_path)

    def test_uncompressed_tar_passes(self, tmp_path: Path):
        """An uncompressed .tar (no gzip) passes validation."""
        files = {"file.txt": b"hello world"}
        tar_path = _create_tar_uncompressed(tmp_path, files)
        validate_tar_contents(tar_path)


# --------------------------------------------------------------------------
# Path traversal
# --------------------------------------------------------------------------


class TestPathTraversal:
    def test_dotdot_in_path_rejected(self, tmp_path: Path):
        """Archive with ../../etc/passwd member is rejected."""
        tar_path = tmp_path / "traversal.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="../../etc/passwd")
            info.size = 4
            tf.addfile(info, io.BytesIO(b"root"))
        with pytest.raises(ValueError, match=r"path traversal"):
            validate_tar_contents(tar_path)

    def test_dotdot_mid_path_rejected(self, tmp_path: Path):
        """Archive with foo/../bar member is rejected."""
        tar_path = tmp_path / "mid_traversal.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="foo/../bar")
            info.size = 3
            tf.addfile(info, io.BytesIO(b"bar"))
        with pytest.raises(ValueError, match=r"path traversal"):
            validate_tar_contents(tar_path)

    def test_dotdot_at_end_rejected(self, tmp_path: Path):
        """Archive with foo/.. member is rejected."""
        tar_path = tmp_path / "end_traversal.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="foo/..")
            info.size = 0
            tf.addfile(info, io.BytesIO(b""))
        with pytest.raises(ValueError, match=r"path traversal"):
            validate_tar_contents(tar_path)

    def test_dot_component_allowed(self, tmp_path: Path):
        """Single dot (./foo) is NOT traversal and should pass."""
        files = {"./models/manifest.yaml": b"name: test"}
        tar_path = _create_tar_gz(tmp_path, files)
        validate_tar_contents(tar_path)

    def test_filename_containing_dotdot_allowed(self, tmp_path: Path):
        """A filename like 'foo..bar' is not traversal — no path separator."""
        files = {"foo..bar.txt": b"content"}
        tar_path = _create_tar_gz(tmp_path, files)
        validate_tar_contents(tar_path)


# --------------------------------------------------------------------------
# Absolute paths
# --------------------------------------------------------------------------


class TestAbsolutePaths:
    def test_absolute_path_rejected(self, tmp_path: Path):
        """Archive with /etc/passwd member is rejected."""
        tar_path = tmp_path / "absolute.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="/etc/passwd")
            info.size = 4
            tf.addfile(info, io.BytesIO(b"root"))
        with pytest.raises(ValueError, match=r"absolute path"):
            validate_tar_contents(tar_path)

    def test_relative_path_allowed(self, tmp_path: Path):
        """A relative path is allowed."""
        files = {"models/ontology.ttl": b"@prefix : <#> ."}
        tar_path = _create_tar_gz(tmp_path, files)
        validate_tar_contents(tar_path)


# --------------------------------------------------------------------------
# Symlinks and hardlinks
# --------------------------------------------------------------------------


class TestSymlinks:
    def test_symlink_rejected(self, tmp_path: Path):
        """Archive with symlink member is rejected."""
        tar_path = tmp_path / "symlink.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="evil_link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/shadow"
            tf.addfile(info)
        with pytest.raises(ValueError, match=r"symlink.*evil_link"):
            validate_tar_contents(tar_path)

    def test_hardlink_rejected(self, tmp_path: Path):
        """Archive with hardlink member is rejected."""
        tar_path = tmp_path / "hardlink.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            # First add a regular file as the target
            info = tarfile.TarInfo(name="target.txt")
            info.size = 5
            tf.addfile(info, io.BytesIO(b"hello"))
            # Then add a hardlink to it
            link_info = tarfile.TarInfo(name="hard_link")
            link_info.type = tarfile.LNKTYPE
            link_info.linkname = "target.txt"
            tf.addfile(link_info)
        with pytest.raises(ValueError, match=r"hardlink.*hard_link"):
            validate_tar_contents(tar_path)


# --------------------------------------------------------------------------
# Uncompressed size limit
# --------------------------------------------------------------------------


class TestUncompressedSizeLimit:
    def test_exceeding_size_limit_raises(self, tmp_path: Path):
        """Tar whose uncompressed size exceeds the limit is rejected."""
        content = b"x" * (512 * 1024)  # 512 KB per file
        files = {
            "big1.bin": content,
            "big2.bin": content,
            "big3.bin": content,  # total: 1.5 MB
        }
        tar_path = _create_tar_uncompressed(tmp_path, files)

        with pytest.raises(ValueError, match=r"uncompressed size.*exceeds limit"):
            validate_tar_contents(tar_path, max_uncompressed_mb=1)

    def test_exactly_at_limit_passes(self, tmp_path: Path):
        """Tar exactly at the uncompressed size limit passes."""
        content = b"x" * (1024 * 1024)  # 1 MB
        files = {"exact.bin": content}
        tar_path = _create_tar_uncompressed(tmp_path, files)
        validate_tar_contents(tar_path, max_uncompressed_mb=1)

    def test_one_byte_over_limit_fails(self, tmp_path: Path):
        """Tar one byte over the uncompressed size limit is rejected."""
        content = b"x" * (1024 * 1024 + 1)
        files = {"over.bin": content}
        tar_path = _create_tar_uncompressed(tmp_path, files)

        with pytest.raises(ValueError, match=r"uncompressed size.*exceeds limit"):
            validate_tar_contents(tar_path, max_uncompressed_mb=1)


# --------------------------------------------------------------------------
# File count limit
# --------------------------------------------------------------------------


class TestFileCountLimit:
    def test_exceeding_file_count_raises(self, tmp_path: Path):
        """Tar with too many entries is rejected."""
        files = {f"file_{i}.txt": b"x" for i in range(11)}
        tar_path = _create_tar_gz(tmp_path, files)

        with pytest.raises(ValueError, match=r"contains 11 entries.*exceeding limit of 10"):
            validate_tar_contents(tar_path, max_files=10)

    def test_exactly_at_count_limit_passes(self, tmp_path: Path):
        """Tar with exactly max_files entries passes."""
        files = {f"file_{i}.txt": b"x" for i in range(10)}
        tar_path = _create_tar_gz(tmp_path, files)
        validate_tar_contents(tar_path, max_files=10)


# --------------------------------------------------------------------------
# Compression ratio (heuristic, archive-level)
# --------------------------------------------------------------------------


class TestCompressionRatio:
    def test_suspicious_ratio_raises(self, tmp_path: Path):
        """Tar.gz with extreme compression ratio is rejected.

        A long run of zero bytes compresses extremely well with gzip,
        producing an archive-level ratio well above 100:1.
        """
        bomb_content = b"\x00" * (10 * 1024 * 1024)  # 10 MB of zeroes
        files = {"bomb.bin": bomb_content}
        tar_path = _create_tar_gz(tmp_path, files)

        with pytest.raises(ValueError, match=r"Suspicious compression ratio"):
            validate_tar_contents(tar_path, max_ratio=100)

    def test_moderate_ratio_passes(self, tmp_path: Path):
        """Tar.gz with moderate compression ratio passes."""
        content = b"abcdefghij" * 100  # 1 KB, moderate compression
        files = {"moderate.txt": content}
        tar_path = _create_tar_gz(tmp_path, files)
        validate_tar_contents(tar_path)

    def test_uncompressed_tar_ratio_near_one(self, tmp_path: Path):
        """Uncompressed tar has ratio ~1:1, always passes."""
        content = b"\x00" * (1024 * 1024)  # 1 MB of zeroes
        files = {"zeros.bin": content}
        tar_path = _create_tar_uncompressed(tmp_path, files)
        validate_tar_contents(tar_path, max_ratio=5)  # strict limit, still passes


# --------------------------------------------------------------------------
# Corrupt archives
# --------------------------------------------------------------------------


class TestCorruptArchive:
    def test_corrupt_tar_raises_valueerror(self, tmp_path: Path):
        """A corrupt/non-tar file raises ValueError, not tarfile.ReadError."""
        corrupt_path = tmp_path / "corrupt.tar.gz"
        corrupt_path.write_bytes(b"this is not a tar file at all")

        with pytest.raises(ValueError, match=r"Corrupt or unreadable"):
            validate_tar_contents(corrupt_path)


# --------------------------------------------------------------------------
# Custom limits
# --------------------------------------------------------------------------


class TestCustomLimits:
    def test_custom_size_limit(self, tmp_path: Path):
        """Custom max_uncompressed_mb is respected."""
        content = b"x" * (6 * 1024 * 1024)  # 6 MB
        files = {"data.bin": content}
        tar_path = _create_tar_uncompressed(tmp_path, files)

        # 5 MB limit: should fail
        with pytest.raises(ValueError, match=r"uncompressed size"):
            validate_tar_contents(tar_path, max_uncompressed_mb=5)

        # 10 MB limit: should pass
        validate_tar_contents(tar_path, max_uncompressed_mb=10)

    def test_custom_file_count_limit(self, tmp_path: Path):
        """Custom max_files is respected."""
        files = {f"f{i}.txt": b"x" for i in range(5)}
        tar_path = _create_tar_gz(tmp_path, files)

        # 3 file limit: should fail
        with pytest.raises(ValueError, match=r"contains 5 entries"):
            validate_tar_contents(tar_path, max_files=3)

        # 10 file limit: should pass
        validate_tar_contents(tar_path, max_files=10)

    def test_custom_ratio_limit(self, tmp_path: Path):
        """Custom max_ratio is respected."""
        content = b"\x00" * (1024 * 1024)  # 1 MB of zeroes
        files = {"zeros.bin": content}
        tar_path = _create_tar_gz(tmp_path, files)

        # Very strict ratio (5:1): should fail for gzipped zeroes
        with pytest.raises(ValueError, match=r"Suspicious compression ratio"):
            validate_tar_contents(tar_path, max_ratio=5)

        # Very lenient ratio (100000:1): should pass
        validate_tar_contents(tar_path, max_ratio=100000)


# --------------------------------------------------------------------------
# safe_extract()
# --------------------------------------------------------------------------


class TestSafeExtract:
    def test_extracts_valid_archive(self, tmp_path: Path):
        """safe_extract() extracts valid archives to the destination."""
        files = {
            "model/manifest.yaml": b"name: test-model\nversion: 1.0",
            "model/ontology.ttl": b"@prefix : <#> .",
            "model/shapes/shape.ttl": b"@prefix sh: <http://www.w3.org/ns/shacl#> .",
        }
        tar_path = _create_tar_gz(tmp_path, files)
        dest = tmp_path / "extracted"

        safe_extract(tar_path, dest)

        assert (dest / "model" / "manifest.yaml").exists()
        assert (dest / "model" / "ontology.ttl").exists()
        assert (dest / "model" / "shapes" / "shape.ttl").exists()
        assert (dest / "model" / "manifest.yaml").read_bytes() == b"name: test-model\nversion: 1.0"

    def test_creates_dest_dir(self, tmp_path: Path):
        """safe_extract() creates the destination directory if it doesn't exist."""
        files = {"file.txt": b"hello"}
        tar_path = _create_tar_gz(tmp_path, files)
        dest = tmp_path / "new" / "nested" / "dir"

        safe_extract(tar_path, dest)

        assert (dest / "file.txt").exists()

    def test_rejects_traversal_before_extract(self, tmp_path: Path):
        """safe_extract() rejects traversal — no files extracted."""
        tar_path = tmp_path / "evil.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="../../etc/passwd")
            info.size = 4
            tf.addfile(info, io.BytesIO(b"root"))

        dest = tmp_path / "extracted"

        with pytest.raises(ValueError, match=r"path traversal"):
            safe_extract(tar_path, dest)

        # Destination should not exist (not created since validation failed before extract)
        assert not dest.exists()

    def test_rejects_symlink_before_extract(self, tmp_path: Path):
        """safe_extract() rejects symlinks — no files extracted."""
        tar_path = tmp_path / "symlink.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="evil_link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/shadow"
            tf.addfile(info)

        dest = tmp_path / "extracted"

        with pytest.raises(ValueError, match=r"symlink"):
            safe_extract(tar_path, dest)

        assert not dest.exists()

    def test_passes_custom_limits_through(self, tmp_path: Path):
        """safe_extract() forwards custom limits to validate_tar_contents()."""
        files = {f"f{i}.txt": b"x" for i in range(5)}
        tar_path = _create_tar_gz(tmp_path, files)
        dest = tmp_path / "extracted"

        with pytest.raises(ValueError, match=r"contains 5 entries"):
            safe_extract(tar_path, dest, max_files=3)


# --------------------------------------------------------------------------
# Error message quality
# --------------------------------------------------------------------------


class TestErrorMessages:
    def test_size_error_includes_actual_and_limit(self, tmp_path: Path):
        """Size rejection message includes actual size and limit."""
        content = b"x" * (2 * 1024 * 1024)  # 2 MB
        files = {"big.bin": content}
        tar_path = _create_tar_uncompressed(tmp_path, files)

        with pytest.raises(ValueError) as exc_info:
            validate_tar_contents(tar_path, max_uncompressed_mb=1)

        msg = str(exc_info.value)
        assert "2.0 MB" in msg
        assert "1 MB" in msg

    def test_count_error_includes_actual_and_limit(self, tmp_path: Path):
        """File count rejection message includes actual count and limit."""
        files = {f"f{i}.txt": b"x" for i in range(20)}
        tar_path = _create_tar_gz(tmp_path, files)

        with pytest.raises(ValueError) as exc_info:
            validate_tar_contents(tar_path, max_files=10)

        msg = str(exc_info.value)
        assert "20 entries" in msg
        assert "limit of 10" in msg

    def test_traversal_error_includes_path(self, tmp_path: Path):
        """Traversal rejection message includes the offending path."""
        tar_path = tmp_path / "traversal.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="models/../../etc/shadow")
            info.size = 0
            tf.addfile(info, io.BytesIO(b""))

        with pytest.raises(ValueError) as exc_info:
            validate_tar_contents(tar_path)

        msg = str(exc_info.value)
        assert "models/../../etc/shadow" in msg

    def test_symlink_error_includes_link_target(self, tmp_path: Path):
        """Symlink rejection message includes source and target."""
        tar_path = tmp_path / "symlink.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="sneaky")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/shadow"
            tf.addfile(info)

        with pytest.raises(ValueError) as exc_info:
            validate_tar_contents(tar_path)

        msg = str(exc_info.value)
        assert "sneaky" in msg
        assert "/etc/shadow" in msg
