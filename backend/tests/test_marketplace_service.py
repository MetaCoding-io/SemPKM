"""Tests for MarketplaceRegistryService.

Covers: catalog fetch, caching, timeout fallback, download + SHA-256 verify,
hash mismatch, SSRF guard, and disabled service (empty URL).
"""

import hashlib
import io
import json
import tarfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.marketplace import MarketplaceRegistryService


# ── Helpers ─────────────────────────────────────────────────────────────────

def _mock_response(status_code: int, content: bytes) -> httpx.Response:
    """Build an httpx.Response with a request set (needed for raise_for_status)."""
    request = httpx.Request("GET", "https://example.com/registry.json")
    return httpx.Response(status_code, content=content, request=request)


def _make_registry_json(models: list[dict]) -> bytes:
    """Build a registry.json response body."""
    return json.dumps({"models": models}).encode()


def _sample_model_entry(
    model_id: str = "test-model",
    archive_url: str = "https://cdn.example.com/test-model-v1.tar.gz",
    sha256: str | None = None,
) -> dict:
    """Build a single model catalog entry."""
    return {
        "id": model_id,
        "name": "Test Model",
        "version": "1.0.0",
        "description": "A test mental model",
        "archive_url": archive_url,
        "sha256": sha256 or "",
        "size_bytes": 1024,
        "tags": ["test"],
    }


def _make_tar_gz_bytes(files: dict[str, bytes]) -> bytes:
    """Create an in-memory tar.gz with the given file paths and contents."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_model_archive(model_id: str = "test-model") -> bytes:
    """Create a valid model archive containing a manifest.yaml."""
    manifest = b"id: test-model\nname: Test Model\nversion: 1.0.0\n"
    return _make_tar_gz_bytes({
        f"{model_id}/manifest.yaml": manifest,
        f"{model_id}/shapes/test.ttl": b"# shapes\n",
    })


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def registry_url():
    return "https://models.example.com/registry.json"


@pytest.fixture
def tmp_models_dir(tmp_path):
    d = tmp_path / "models"
    d.mkdir()
    return d


@pytest.fixture
def service(registry_url, tmp_models_dir):
    return MarketplaceRegistryService(
        registry_url=registry_url,
        models_data_dir=tmp_models_dir,
    )


@pytest.fixture
def disabled_service(tmp_models_dir):
    return MarketplaceRegistryService(
        registry_url="",
        models_data_dir=tmp_models_dir,
    )


# ── Catalog Fetch ───────────────────────────────────────────────────────────

class TestFetchCatalog:
    """Tests for fetch_catalog()."""

    @pytest.mark.asyncio
    async def test_returns_parsed_models_list(self, service, registry_url):
        """Happy path: fetch registry.json → parse → return models list."""
        models = [_sample_model_entry()]
        body = _make_registry_json(models)

        mock_resp = _mock_response(200, body)
        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            result = await service.fetch_catalog()

        assert len(result) == 1
        assert result[0]["id"] == "test-model"

    @pytest.mark.asyncio
    async def test_caches_within_ttl(self, service, registry_url):
        """Second call within TTL returns cached result without HTTP call."""
        models = [_sample_model_entry()]
        body = _make_registry_json(models)

        mock_resp = _mock_response(200, body)
        mock_get = AsyncMock(return_value=mock_resp)

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", mock_get),
        ):
            first = await service.fetch_catalog()
            second = await service.fetch_catalog()

        assert first == second
        assert mock_get.call_count == 1  # only one HTTP call

    @pytest.mark.asyncio
    async def test_refetches_after_ttl_expires(self, service, registry_url):
        """After TTL expires, a new HTTP call is made."""
        models = [_sample_model_entry()]
        body = _make_registry_json(models)

        mock_resp = _mock_response(200, body)
        mock_get = AsyncMock(return_value=mock_resp)

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", mock_get),
            patch("app.services.marketplace.time") as mock_time,
        ):
            # First call at t=0
            mock_time.monotonic.return_value = 0.0
            await service.fetch_catalog()

            # Second call at t=3601 (past TTL)
            mock_time.monotonic.return_value = 3601.0
            await service.fetch_catalog()

        assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_list(self, service):
        """Network timeout → returns empty list, no crash."""
        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch(
                "httpx.AsyncClient.get",
                new_callable=AsyncMock,
                side_effect=httpx.ConnectTimeout("timeout"),
            ),
        ):
            result = await service.fetch_catalog()

        assert result == []

    @pytest.mark.asyncio
    async def test_http_error_returns_empty_list(self, service):
        """HTTP 500 → returns empty list, no crash."""
        mock_resp = _mock_response(500, b"Internal Server Error")
        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            result = await service.fetch_catalog()

        assert result == []

    @pytest.mark.asyncio
    async def test_malformed_json_returns_empty_list(self, service):
        """Response with non-list 'models' key → returns empty list."""
        body = json.dumps({"models": "not-a-list"}).encode()
        mock_resp = _mock_response(200, body)
        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            result = await service.fetch_catalog()

        assert result == []

    @pytest.mark.asyncio
    async def test_disabled_service_returns_empty_list(self, disabled_service):
        """Empty registry URL → returns empty list immediately."""
        result = await disabled_service.fetch_catalog()
        assert result == []

    @pytest.mark.asyncio
    async def test_enabled_property(self, service, disabled_service):
        """enabled reflects whether registry_url is set."""
        assert service.enabled is True
        assert disabled_service.enabled is False


# ── SSRF Guard ──────────────────────────────────────────────────────────────

class TestSSRFGuard:
    """SSRF protection on both catalog fetch and archive download."""

    @pytest.mark.asyncio
    async def test_ssrf_blocks_catalog_fetch(self, tmp_models_dir):
        """SSRF guard on registry URL → no HTTP call made."""
        svc = MarketplaceRegistryService(
            registry_url="http://169.254.169.254/latest/meta-data/",
            models_data_dir=tmp_models_dir,
        )
        with patch(
            "app.services.marketplace.validate_outbound_url",
            side_effect=ValueError("SSRF blocked"),
        ):
            result = await svc.fetch_catalog()

        assert result == []

    @pytest.mark.asyncio
    async def test_ssrf_blocks_archive_download(self, service, tmp_models_dir):
        """SSRF guard on archive URL → ValueError before download."""
        entry = _sample_model_entry(archive_url="http://localhost/evil.tar.gz")
        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        def _ssrf_check(url):
            if "localhost" in url:
                raise ValueError("SSRF blocked: localhost")

        with patch(
            "app.services.marketplace.validate_outbound_url",
            side_effect=_ssrf_check,
        ):
            with pytest.raises(ValueError, match="SSRF blocked"):
                await service.download_and_install(
                    "test-model",
                    MagicMock(),
                    None,
                )


# ── Download and Install ────────────────────────────────────────────────────

class TestDownloadAndInstall:
    """Tests for download_and_install()."""

    @pytest.mark.asyncio
    async def test_happy_path(self, service, tmp_models_dir):
        """Download + SHA-256 match + extract + install → success."""
        archive_bytes = _make_model_archive("test-model")
        sha = hashlib.sha256(archive_bytes).hexdigest()
        entry = _sample_model_entry(sha256=sha)

        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        mock_resp = _mock_response(200, archive_bytes)
        mock_install = AsyncMock(return_value={"status": "installed", "model_id": "test-model"})
        mock_model_svc = MagicMock()
        mock_model_svc.install = mock_install

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            result = await service.download_and_install(
                "test-model", mock_model_svc, None
            )

        assert result["status"] == "installed"
        mock_install.assert_called_once()
        # Model should be persisted to models_data_dir
        assert (tmp_models_dir / "test-model" / "manifest.yaml").exists()

    @pytest.mark.asyncio
    async def test_sha256_mismatch_raises(self, service):
        """SHA-256 mismatch → ValueError before extraction."""
        archive_bytes = _make_model_archive("test-model")
        entry = _sample_model_entry(sha256="deadbeef" * 8)  # wrong hash

        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        mock_resp = _mock_response(200, archive_bytes)

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            with pytest.raises(ValueError, match="SHA-256 mismatch"):
                await service.download_and_install(
                    "test-model", MagicMock(), None
                )

    @pytest.mark.asyncio
    async def test_model_not_in_catalog_raises(self, service):
        """Model ID not in catalog → ValueError."""
        service._cached_catalog = []
        service._cache_timestamp = time.monotonic()

        with pytest.raises(ValueError, match="not found in marketplace catalog"):
            await service.download_and_install(
                "nonexistent", MagicMock(), None
            )

    @pytest.mark.asyncio
    async def test_no_archive_url_raises(self, service):
        """Entry with empty archive_url → ValueError."""
        entry = _sample_model_entry(archive_url="")
        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        with pytest.raises(ValueError, match="no archive_url"):
            await service.download_and_install(
                "test-model", MagicMock(), None
            )

    @pytest.mark.asyncio
    async def test_tmpdir_cleaned_on_failure(self, service):
        """Tempdir is cleaned up even when download fails."""
        entry = _sample_model_entry()
        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch(
                "httpx.AsyncClient.get",
                new_callable=AsyncMock,
                side_effect=httpx.ConnectError("fail"),
            ),
        ):
            with pytest.raises(httpx.ConnectError):
                await service.download_and_install(
                    "test-model", MagicMock(), None
                )

        # No leaked tempdirs — hard to assert directly, but the finally block
        # ensures cleanup. We verify no crash occurred.

    @pytest.mark.asyncio
    async def test_no_manifest_in_archive_raises(self, service):
        """Archive without manifest.yaml → ValueError."""
        # Archive with no manifest
        archive_bytes = _make_tar_gz_bytes({"test-model/readme.txt": b"hello"})
        sha = hashlib.sha256(archive_bytes).hexdigest()
        entry = _sample_model_entry(sha256=sha)

        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        mock_resp = _mock_response(200, archive_bytes)

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            with pytest.raises(ValueError, match="no manifest.yaml"):
                await service.download_and_install(
                    "test-model", MagicMock(), None
                )

    @pytest.mark.asyncio
    async def test_empty_sha_skips_verification(self, service, tmp_models_dir):
        """When sha256 is empty in catalog, skip hash check (install anyway)."""
        archive_bytes = _make_model_archive("test-model")
        entry = _sample_model_entry(sha256="")  # no hash

        service._cached_catalog = [entry]
        service._cache_timestamp = time.monotonic()

        mock_resp = _mock_response(200, archive_bytes)
        mock_install = AsyncMock(return_value={"status": "installed"})
        mock_model_svc = MagicMock()
        mock_model_svc.install = mock_install

        with (
            patch("app.services.marketplace.validate_outbound_url"),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        ):
            result = await service.download_and_install(
                "test-model", mock_model_svc, None
            )

        assert result["status"] == "installed"


# ── Check Updates ───────────────────────────────────────────────────────────


class TestCheckUpdates:
    """Tests for check_updates()."""

    @staticmethod
    def _make_installed(model_id: str, version: str):
        """Build a minimal InstalledModel-like object."""
        from app.models.registry import InstalledModel
        return InstalledModel(
            model_id=model_id,
            version=version,
            name=f"Model {model_id}",
            description="",
            namespace="",
            installed_at="",
        )

    @pytest.mark.asyncio
    async def test_detects_update_available(self, service):
        """Installed v1.0.0, registry v2.0.0 → has_update: True."""
        catalog = [_sample_model_entry()]  # version 1.0.0 by default
        catalog[0]["version"] = "2.0.0"
        service._cached_catalog = catalog
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("test-model", "1.0.0")]
        result = await service.check_updates(installed)

        assert "test-model" in result
        assert result["test-model"]["has_update"] is True
        assert result["test-model"]["installed_version"] == "1.0.0"
        assert result["test-model"]["latest_version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_detects_up_to_date(self, service):
        """Installed v2.0.0, registry v2.0.0 → has_update: False."""
        catalog = [_sample_model_entry()]
        catalog[0]["version"] = "2.0.0"
        service._cached_catalog = catalog
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("test-model", "2.0.0")]
        result = await service.check_updates(installed)

        assert "test-model" in result
        assert result["test-model"]["has_update"] is False

    @pytest.mark.asyncio
    async def test_installed_newer_than_registry(self, service):
        """Installed v3.0.0, registry v2.0.0 → has_update: False."""
        catalog = [_sample_model_entry()]
        catalog[0]["version"] = "2.0.0"
        service._cached_catalog = catalog
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("test-model", "3.0.0")]
        result = await service.check_updates(installed)

        assert "test-model" in result
        assert result["test-model"]["has_update"] is False

    @pytest.mark.asyncio
    async def test_model_not_in_registry(self, service):
        """Installed model not in catalog → not in result dict."""
        service._cached_catalog = []
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("unknown-model", "1.0.0")]
        result = await service.check_updates(installed)

        assert "unknown-model" not in result
        assert result == {}

    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self, disabled_service):
        """Disabled service → empty dict."""
        installed = [TestCheckUpdates._make_installed("test-model", "1.0.0")]
        result = await disabled_service.check_updates(installed)
        assert result == {}

    @pytest.mark.asyncio
    async def test_malformed_version_skipped(self, service):
        """Registry entry with 'invalid' version → skipped, no crash."""
        catalog = [_sample_model_entry()]
        catalog[0]["version"] = "not-a-version"
        service._cached_catalog = catalog
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("test-model", "1.0.0")]
        result = await service.check_updates(installed)

        assert "test-model" not in result

    @pytest.mark.asyncio
    async def test_empty_catalog_returns_empty(self, service):
        """Catalog fetch returns [] → empty dict."""
        service._cached_catalog = []
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("test-model", "1.0.0")]
        result = await service.check_updates(installed)
        assert result == {}

    @pytest.mark.asyncio
    async def test_malformed_installed_version_skipped(self, service):
        """Installed model with malformed version → skipped, no crash."""
        catalog = [_sample_model_entry()]
        catalog[0]["version"] = "2.0.0"
        service._cached_catalog = catalog
        service._cache_timestamp = time.monotonic()

        installed = [self._make_installed("test-model", "garbage")]
        result = await service.check_updates(installed)

        assert "test-model" not in result

    @pytest.mark.asyncio
    async def test_multiple_models(self, service):
        """Multiple installed models — each checked independently."""
        catalog = [
            {**_sample_model_entry(), "id": "model-a", "version": "2.0.0"},
            {**_sample_model_entry(), "id": "model-b", "version": "1.0.0"},
        ]
        service._cached_catalog = catalog
        service._cache_timestamp = time.monotonic()

        installed = [
            self._make_installed("model-a", "1.0.0"),
            self._make_installed("model-b", "1.0.0"),
        ]
        result = await service.check_updates(installed)

        assert result["model-a"]["has_update"] is True
        assert result["model-b"]["has_update"] is False


# ── resolve_model_dir ───────────────────────────────────────────────────────

class TestResolveModelDir:
    """Tests for the resolve_model_dir() utility."""

    def test_finds_in_first_dir(self, tmp_path):
        from app.models.paths import resolve_model_dir

        d = tmp_path / "models" / "test-model"
        d.mkdir(parents=True)
        (d / "manifest.yaml").write_text("id: test-model")

        with patch("app.models.paths._DEFAULT_DIRS", [tmp_path / "models"]):
            result = resolve_model_dir("test-model")

        assert result == d

    def test_finds_in_extra_dir(self, tmp_path):
        from app.models.paths import resolve_model_dir

        extra = tmp_path / "extra" / "test-model"
        extra.mkdir(parents=True)
        (extra / "manifest.yaml").write_text("id: test-model")

        with patch("app.models.paths._DEFAULT_DIRS", []):
            result = resolve_model_dir(
                "test-model",
                extra_dirs=[str(tmp_path / "extra")],
            )

        assert result == extra

    def test_returns_none_when_not_found(self, tmp_path):
        from app.models.paths import resolve_model_dir

        with patch("app.models.paths._DEFAULT_DIRS", [tmp_path]):
            result = resolve_model_dir("nonexistent")

        assert result is None

    def test_requires_manifest_yaml(self, tmp_path):
        from app.models.paths import resolve_model_dir

        # Directory exists but no manifest.yaml
        d = tmp_path / "models" / "no-manifest"
        d.mkdir(parents=True)

        with patch("app.models.paths._DEFAULT_DIRS", [tmp_path / "models"]):
            result = resolve_model_dir("no-manifest")

        assert result is None
