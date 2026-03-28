"""Jinja2 template helpers for asset URL resolution.

In production (Docker build): manifest.json maps logical names to content-hashed filenames.
In development (volume mounts): no manifest exists, paths return original dev locations.

Decision D270: JSON manifest + Jinja2 filter
Decision D275: manifest file presence is the dev/prod signal
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Search paths for the asset manifest (checked in order):
# 1. ASSET_MANIFEST_PATH env var (explicit override, e.g. for tests)
# 2. /app/frontend_assets/manifest.json (Docker shared volume between frontend→api)
# 3. /usr/share/nginx/html/assets/manifest.json (same-container, won't exist for API)
_MANIFEST_SEARCH_PATHS = [
    "/app/frontend_assets/manifest.json",
    "/usr/share/nginx/html/assets/manifest.json",
]
_MANIFEST_PATH_OVERRIDE = os.environ.get("ASSET_MANIFEST_PATH")

_manifest: dict[str, str] | None = None
_manifest_loaded: bool = False


def _load_manifest() -> dict[str, str] | None:
    """Load the asset manifest from disk.

    Checks ASSET_MANIFEST_PATH env var first (if set), then searches
    _MANIFEST_SEARCH_PATHS in order. Returns the first valid manifest found.
    Sets _manifest_loaded to True regardless of outcome to avoid repeated reads.
    """
    global _manifest, _manifest_loaded

    if _manifest_loaded:
        return _manifest

    _manifest_loaded = True

    # Build candidate list: env var override first, then search paths
    candidates = []
    if _MANIFEST_PATH_OVERRIDE:
        candidates.append(_MANIFEST_PATH_OVERRIDE)
    candidates.extend(_MANIFEST_SEARCH_PATHS)

    for candidate_path in candidates:
        manifest_path = Path(candidate_path)
        try:
            data = manifest_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning(
                "Could not read asset manifest at %s: %s", candidate_path, exc
            )
            continue

        try:
            parsed = json.loads(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Invalid JSON in asset manifest at %s: %s", candidate_path, exc
            )
            continue

        if not isinstance(parsed, dict):
            logger.warning(
                "Asset manifest at %s is not a JSON object (got %s)",
                candidate_path,
                type(parsed).__name__,
            )
            continue

        _manifest = parsed
        logger.info(
            "Loaded asset manifest from %s (%d entries)",
            candidate_path,
            len(_manifest),
        )
        return _manifest

    logger.info(
        "Asset manifest not found at any search path — running in dev mode"
    )
    _manifest = None
    return None


def asset_url(name: str) -> str:
    """Resolve a logical asset name to a URL path.

    With manifest (production): returns /assets/<hashed-filename>
    Without manifest (dev):     returns /js/<name>, /css/<name>, or /<name>
    """
    global _manifest, _manifest_loaded

    if not name:
        return ""

    # Lazy retry: if manifest wasn't found at startup, check once more on
    # first template render.  Handles the race where the frontend container
    # populates the shared volume after the API has already started.
    if _manifest is None and _manifest_loaded:
        _manifest_loaded = False          # allow one re-check
        _load_manifest()

    # Production mode: manifest available and contains this key
    if _manifest is not None and name in _manifest:
        return f"/assets/{_manifest[name]}"

    # Dev mode fallback: route by extension
    if name.endswith(".js"):
        return f"/js/{name}"
    if name.endswith(".css"):
        return f"/css/{name}"

    return f"/{name}"


def is_asset_manifest_available() -> bool:
    """Return True if a valid asset manifest was loaded."""
    return _manifest is not None


def init_template_helpers(app) -> None:
    """Register asset helpers on the app's Jinja2 environment.

    Call after templates are configured on app.state.templates.
    """
    _load_manifest()

    env = app.state.templates.env
    env.filters["asset_url"] = asset_url
    env.globals["asset_manifest_available"] = is_asset_manifest_available()

    mode = "production" if _manifest is not None else "development"
    logger.info("Asset template helpers registered (mode=%s)", mode)
