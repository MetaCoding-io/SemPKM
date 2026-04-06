"""Marketplace registry service — fetch, cache, download, verify, install.

Fetches a remote ``registry.json`` catalog, caches it with a configurable
TTL, downloads model archives, verifies SHA-256 hashes, extracts safely
via the tar validator, and installs through ``ModelService.install()``.

Usage:
    from app.services.marketplace import MarketplaceRegistryService

    svc = MarketplaceRegistryService(
        registry_url="https://models.example.com/registry.json",
        models_data_dir=Path("/app/data/models"),
    )
    catalog = await svc.fetch_catalog()
    result = await svc.download_and_install("basic-pkm", model_service, user_id)
"""

import hashlib
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from app.models.registry import InstalledModel

from app.security.ssrf import validate_outbound_url
from app.security.tar_validator import safe_extract

logger = logging.getLogger(__name__)

# Cache TTL in seconds — 1 hour.
_CATALOG_TTL_SECONDS = 3600

# HTTP timeouts
_REGISTRY_FETCH_TIMEOUT = 5.0
_ARCHIVE_DOWNLOAD_TIMEOUT = 30.0


class MarketplaceRegistryService:
    """Fetches, caches, and installs models from a remote registry."""

    def __init__(self, registry_url: str, models_data_dir: Path) -> None:
        self._registry_url = registry_url.strip()
        self._models_data_dir = models_data_dir
        self._cached_catalog: list[dict] | None = None
        self._cache_timestamp: float = 0.0

    @property
    def enabled(self) -> bool:
        """Whether the marketplace is configured (non-empty URL)."""
        return bool(self._registry_url)

    async def fetch_catalog(self) -> list[dict]:
        """Fetch the model catalog from the remote registry.

        Returns a cached copy if within TTL.  On any network error,
        logs a warning and returns an empty list — never crashes.

        Returns:
            List of model dicts from ``registry.json["models"]``.
        """
        if not self.enabled:
            return []

        # Return cached catalog if within TTL
        now = time.monotonic()
        if (
            self._cached_catalog is not None
            and (now - self._cache_timestamp) < _CATALOG_TTL_SECONDS
        ):
            return self._cached_catalog

        t0 = time.monotonic()
        try:
            validate_outbound_url(self._registry_url)
        except ValueError as exc:
            logger.warning(
                "registry.fetch blocked by SSRF guard: url=%s reason=%s",
                self._registry_url,
                exc,
            )
            return []

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._registry_url,
                    timeout=_REGISTRY_FETCH_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
            duration_ms = (time.monotonic() - t0) * 1000
            logger.warning(
                "registry.fetch failed: url=%s error=%s duration_ms=%.0f",
                self._registry_url,
                exc,
                duration_ms,
            )
            return []

        models = data.get("models", [])
        if not isinstance(models, list):
            logger.warning(
                "registry.fetch malformed: 'models' is not a list, url=%s",
                self._registry_url,
            )
            return []

        self._cached_catalog = models
        self._cache_timestamp = time.monotonic()

        duration_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "registry.fetch ok: url=%s model_count=%d duration_ms=%.0f",
            self._registry_url,
            len(models),
            duration_ms,
        )
        return models

    async def download_and_install(
        self,
        model_id: str,
        model_service,
        user_id,
    ) -> dict:
        """Download, verify, extract, and install a marketplace model.

        Args:
            model_id: The model identifier from the catalog.
            model_service: A ``ModelService`` instance (with ``.install()``).
            user_id: User ID for install attribution.

        Returns:
            Install result dict from ``model_service.install()``.

        Raises:
            ValueError: If the model is not found in the catalog,
                SHA-256 mismatch, SSRF block, or archive validation failure.
        """
        catalog = await self.fetch_catalog()
        entry = next((m for m in catalog if m.get("id") == model_id), None)
        if entry is None:
            raise ValueError(f"Model '{model_id}' not found in marketplace catalog")

        archive_url = entry.get("archive_url", "")
        expected_sha = entry.get("sha256", "")

        if not archive_url:
            raise ValueError(f"Model '{model_id}' has no archive_url in catalog")

        # SSRF check on the archive URL
        validate_outbound_url(archive_url)

        tmpdir = None
        try:
            tmpdir = Path(tempfile.mkdtemp(prefix="sempkm-marketplace-"))
            archive_path = tmpdir / f"{model_id}.tar.gz"

            # --- Download ---
            t0 = time.monotonic()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    archive_url,
                    timeout=_ARCHIVE_DOWNLOAD_TIMEOUT,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                archive_bytes = resp.content

            download_ms = (time.monotonic() - t0) * 1000

            # --- SHA-256 verification ---
            actual_sha = hashlib.sha256(archive_bytes).hexdigest()
            if expected_sha and actual_sha != expected_sha:
                logger.warning(
                    "registry.download sha256_mismatch: model=%s "
                    "expected=%s actual=%s",
                    model_id,
                    expected_sha,
                    actual_sha,
                )
                raise ValueError(
                    f"SHA-256 mismatch for '{model_id}': "
                    f"expected {expected_sha}, got {actual_sha}"
                )

            logger.info(
                "registry.download ok: model=%s size=%d sha256=%s "
                "duration_ms=%.0f",
                model_id,
                len(archive_bytes),
                actual_sha,
                download_ms,
            )

            # --- Write and extract ---
            archive_path.write_bytes(archive_bytes)
            extract_dir = tmpdir / "extracted"
            safe_extract(archive_path, extract_dir)

            # Find the model directory inside the extracted tree.
            # Tar archives may have a single top-level directory or
            # put files directly in the root.
            manifest_candidates = list(extract_dir.rglob("manifest.yaml"))
            if not manifest_candidates:
                raise ValueError(
                    f"Extracted archive for '{model_id}' contains no manifest.yaml"
                )

            # Use the first manifest found, take its parent as model dir
            model_dir = manifest_candidates[0].parent

            # --- Install via ModelService ---
            result = await model_service.install(model_dir, user_id)

            # --- Persist to models_data_dir ---
            dest = self._models_data_dir / model_id
            if dest.exists():
                shutil.rmtree(dest)
            self._models_data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(model_dir, dest)

            return result

        finally:
            # Always clean up tmpdir
            if tmpdir and tmpdir.exists():
                shutil.rmtree(tmpdir, ignore_errors=True)

    async def check_updates(
        self,
        installed_models: list["InstalledModel"],
    ) -> dict[str, dict]:
        """Compare installed model versions against the marketplace catalog.

        Args:
            installed_models: List of currently installed models.

        Returns:
            Dict mapping model_id → {"installed_version": str,
            "latest_version": str, "has_update": bool}.
            Models not found in catalog or with malformed versions are omitted.
        """
        if not self.enabled:
            return {}

        catalog = await self.fetch_catalog()
        if not catalog:
            return {}

        # Build lookup: catalog model_id → entry
        catalog_map: dict[str, dict] = {}
        for entry in catalog:
            mid = entry.get("id")
            if mid:
                catalog_map[mid] = entry

        result: dict[str, dict] = {}
        for model in installed_models:
            cat_entry = catalog_map.get(model.model_id)
            if cat_entry is None:
                continue

            installed_ver_str = model.version
            latest_ver_str = cat_entry.get("version", "")

            try:
                installed_ver = Version(installed_ver_str)
                latest_ver = Version(latest_ver_str)
            except InvalidVersion:
                logger.warning(
                    "registry.check_updates skipped model=%s: "
                    "malformed version installed=%r catalog=%r",
                    model.model_id,
                    installed_ver_str,
                    latest_ver_str,
                )
                continue

            result[model.model_id] = {
                "installed_version": str(installed_ver),
                "latest_version": str(latest_ver),
                "has_update": latest_ver > installed_ver,
            }

        return result
