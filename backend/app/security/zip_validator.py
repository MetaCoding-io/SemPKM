"""ZIP bomb protection for import endpoints.

Validates ZIP archives before extraction to reject oversized,
file-count-excessive, or suspiciously compressed archives.
"""

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_zip_contents(
    zip_path: Path,
    *,
    max_uncompressed_mb: int = 2048,
    max_files: int = 50_000,
    max_ratio: int = 100,
) -> None:
    """Validate a ZIP archive's contents before extraction.

    Inspects the ZIP central directory (via infolist()) without extracting
    any files. Checks three criteria:

    1. Total uncompressed size must not exceed ``max_uncompressed_mb`` MB.
    2. Total file count must not exceed ``max_files``.
    3. No single entry may have a compression ratio above ``max_ratio``:1.

    Args:
        zip_path: Path to the ZIP file on disk.
        max_uncompressed_mb: Maximum total uncompressed size in megabytes.
        max_files: Maximum number of entries in the archive.
        max_ratio: Maximum allowed compression ratio for any single entry.

    Raises:
        ValueError: If any check fails, with a human-readable message.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        entries = zf.infolist()

    total_uncompressed = 0
    file_count = len(entries)

    # --- file count check ---
    if file_count > max_files:
        raise ValueError(
            f"ZIP archive contains {file_count} files, "
            f"exceeding limit of {max_files}"
        )

    for entry in entries:
        total_uncompressed += entry.file_size

        # --- per-entry compression ratio check ---
        if entry.compress_size > 0:
            ratio = entry.file_size / entry.compress_size
            if ratio > max_ratio:
                raise ValueError(
                    f"Suspicious compression ratio ({ratio:.0f}:1) "
                    f"detected in {entry.filename}"
                )
            if ratio > 50:
                logger.warning(
                    "High compression ratio (%.0f:1) in %s of %s",
                    ratio,
                    entry.filename,
                    zip_path.name,
                )

    # --- total uncompressed size check ---
    max_bytes = max_uncompressed_mb * 1024 * 1024
    if total_uncompressed > max_bytes:
        size_mb = total_uncompressed / (1024 * 1024)
        raise ValueError(
            f"ZIP archive uncompressed size ({size_mb:.1f} MB) "
            f"exceeds limit ({max_uncompressed_mb} MB)"
        )
