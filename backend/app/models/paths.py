"""Model directory resolution across bundled and downloaded locations.

Usage:
    from app.models.paths import resolve_model_dir

    path = resolve_model_dir("basic-pkm")
    # → Path("/app/models/basic-pkm") if it exists there, else
    # → Path("/app/data/models/basic-pkm") if it exists there, else None
"""

from pathlib import Path


# Default search directories — bundled first, then downloaded.
_DEFAULT_DIRS = [
    Path("/app/models"),
    Path("/app/data/models"),
]


def resolve_model_dir(
    model_id: str,
    extra_dirs: list[str] | None = None,
) -> Path | None:
    """Find a model directory by ID across known locations.

    Searches the default directories (``/app/models/``, then
    ``/app/data/models/``) plus any ``extra_dirs`` for a subdirectory
    named ``model_id`` that contains a ``manifest.yaml`` file.

    Args:
        model_id: The model identifier (directory name).
        extra_dirs: Additional directories to search after defaults.

    Returns:
        The first matching directory path, or ``None`` if not found.
    """
    search_dirs = list(_DEFAULT_DIRS)
    if extra_dirs:
        search_dirs.extend(Path(d) for d in extra_dirs)

    for base in search_dirs:
        candidate = base / model_id
        if (candidate / "manifest.yaml").is_file():
            return candidate

    return None
