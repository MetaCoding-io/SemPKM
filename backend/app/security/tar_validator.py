"""Tar archive protection for marketplace model installs.

Validates tar.gz archives before extraction to reject path traversal,
symlinks, hardlinks, oversized archives, and excessive file counts.

Uses Python 3.12's ``tarfile.data_filter`` for safe extraction semantics.
"""

import logging
import os
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_tar_contents(
    tar_path: Path,
    *,
    max_uncompressed_mb: int = 2048,
    max_files: int = 50_000,
    max_ratio: int = 100,
) -> None:
    """Validate a tar archive's contents before extraction.

    Iterates members via ``getmembers()`` without extracting any files.
    Checks six criteria:

    1. No member may have an absolute path (starts with ``/``).
    2. No member may contain ``..`` path components (traversal).
    3. No symlinks (``issym()``) or hardlinks (``islnk()``) are allowed.
    4. Total file count must not exceed ``max_files``.
    5. Total uncompressed size must not exceed ``max_uncompressed_mb`` MB.
    6. Heuristic compression ratio (total uncompressed / archive size)
       must not exceed ``max_ratio``:1.

    Args:
        tar_path: Path to the tar (or tar.gz/tar.bz2/tar.xz) file on disk.
        max_uncompressed_mb: Maximum total uncompressed size in megabytes.
        max_files: Maximum number of entries in the archive.
        max_ratio: Maximum allowed heuristic compression ratio.

    Raises:
        ValueError: If any check fails, with a human-readable message.
            Also raised if the archive is corrupt or unreadable.
    """
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
    except tarfile.ReadError as exc:
        raise ValueError(
            f"Corrupt or unreadable tar archive: {tar_path.name} — {exc}"
        ) from exc

    archive_size = tar_path.stat().st_size
    file_count = len(members)
    total_uncompressed = 0

    # --- file count check ---
    if file_count > max_files:
        raise ValueError(
            f"Tar archive contains {file_count} entries, "
            f"exceeding limit of {max_files}"
        )

    for member in members:
        name = member.name

        # --- absolute path check ---
        if os.path.isabs(name):
            raise ValueError(
                f"Tar archive contains absolute path: {name}"
            )

        # --- path traversal check ---
        parts = name.replace("\\", "/").split("/")
        if ".." in parts:
            raise ValueError(
                f"Tar archive contains path traversal: {name}"
            )

        # --- symlink check ---
        if member.issym():
            raise ValueError(
                f"Tar archive contains symlink: {name} → {member.linkname}"
            )

        # --- hardlink check ---
        if member.islnk():
            raise ValueError(
                f"Tar archive contains hardlink: {name} → {member.linkname}"
            )

        # Accumulate size for regular files and directories
        if member.size > 0:
            total_uncompressed += member.size

    # --- total uncompressed size check ---
    max_bytes = max_uncompressed_mb * 1024 * 1024
    if total_uncompressed > max_bytes:
        size_mb = total_uncompressed / (1024 * 1024)
        raise ValueError(
            f"Tar archive uncompressed size ({size_mb:.1f} MB) "
            f"exceeds limit ({max_uncompressed_mb} MB)"
        )

    # --- heuristic compression ratio check ---
    # Tar doesn't expose per-entry compressed size, so use archive-level ratio.
    if archive_size > 0 and total_uncompressed > 0:
        ratio = total_uncompressed / archive_size
        if ratio > max_ratio:
            raise ValueError(
                f"Suspicious compression ratio ({ratio:.0f}:1) "
                f"in {tar_path.name}"
            )
        if ratio > 50:
            logger.warning(
                "High compression ratio (%.0f:1) in %s",
                ratio,
                tar_path.name,
            )


def safe_extract(
    tar_path: Path,
    dest_dir: Path,
    *,
    max_uncompressed_mb: int = 2048,
    max_files: int = 50_000,
    max_ratio: int = 100,
) -> None:
    """Validate and safely extract a tar archive.

    Runs ``validate_tar_contents()`` first, then extracts using
    ``tarfile.data_filter`` for Python 3.12+ safe extraction semantics
    (rejects absolute paths, traversal, and device files at the
    extraction layer as a defense-in-depth measure).

    Args:
        tar_path: Path to the tar archive.
        dest_dir: Directory to extract into (created if it doesn't exist).
        max_uncompressed_mb: Passed to ``validate_tar_contents()``.
        max_files: Passed to ``validate_tar_contents()``.
        max_ratio: Passed to ``validate_tar_contents()``.

    Raises:
        ValueError: If validation fails.
        tarfile.ReadError: If the archive is corrupt (after validation).
    """
    validate_tar_contents(
        tar_path,
        max_uncompressed_mb=max_uncompressed_mb,
        max_files=max_files,
        max_ratio=max_ratio,
    )

    dest_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_path, "r:*") as tf:
        tf.extractall(path=dest_dir, filter="data")
