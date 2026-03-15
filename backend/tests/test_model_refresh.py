"""Unit tests for ModelService.refresh_artifacts().

Validates that refresh clears exactly the 4 artifact graphs (ontology,
shapes, views, rules) and reloads them from disk — never touching the
seed graph or registry entry. Uses mock triplestore client.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from rdflib import Graph, URIRef, Literal

from app.models.loader import ModelArchive
from app.models.manifest import ManifestSchema
from app.models.registry import ModelGraphs
from app.services.models import ModelService, RefreshResult


MODEL_ID = "basic-pkm"
MODEL_DIR = Path(f"/app/models/{MODEL_ID}")
SEED_GRAPH_IRI = f"urn:sempkm:model:{MODEL_ID}:seed"


def _make_graph(triples: list[tuple] | None = None) -> Graph:
    """Create an rdflib Graph with optional triples."""
    g = Graph()
    if triples:
        for s, p, o in triples:
            g.add((URIRef(s), URIRef(p), Literal(o)))
    else:
        # Default: add one triple so graph is non-empty
        g.add((
            URIRef("urn:test:s"),
            URIRef("urn:test:p"),
            Literal("test-value"),
        ))
    return g


def _make_manifest() -> ManifestSchema:
    """Create a minimal ManifestSchema mock."""
    manifest = MagicMock(spec=ManifestSchema)
    manifest.modelId = MODEL_ID
    manifest.name = "Basic PKM"
    manifest.version = "1.0.0"
    manifest.description = "Test model"
    manifest.namespace = f"urn:sempkm:model:{MODEL_ID}:"
    return manifest


_SENTINEL = object()


def _make_archive(
    *,
    ontology: Graph | None | object = _SENTINEL,
    shapes: Graph | None | object = _SENTINEL,
    views: Graph | None | object = _SENTINEL,
    rules: Graph | None | object = _SENTINEL,
    seed: Graph | None | object = _SENTINEL,
) -> ModelArchive:
    """Create a ModelArchive with customizable graphs.

    Uses a sentinel to distinguish 'not provided' from explicit None/empty Graph.
    """
    return ModelArchive(
        manifest=_make_manifest(),
        ontology=_make_graph() if ontology is _SENTINEL else ontology,
        shapes=_make_graph() if shapes is _SENTINEL else shapes,
        views=_make_graph() if views is _SENTINEL else views,
        rules=_make_graph() if rules is _SENTINEL else rules,
        seed=_make_graph() if seed is _SENTINEL else seed,
    )


@pytest.fixture
def mock_client():
    """Mock TriplestoreClient with transaction support."""
    client = AsyncMock()
    client.begin_transaction = AsyncMock(return_value="http://localhost/txn/1")
    client.transaction_update = AsyncMock(return_value=None)
    client.commit_transaction = AsyncMock(return_value=None)
    client.rollback_transaction = AsyncMock(return_value=None)
    client.query = AsyncMock(return_value={"boolean": True})
    return client


@pytest.fixture
def mock_event_store():
    return AsyncMock()


@pytest.fixture
def mock_prefix_registry():
    return MagicMock()


@pytest.fixture
def service(mock_client, mock_event_store, mock_prefix_registry):
    return ModelService(mock_client, mock_event_store, mock_prefix_registry)


# ---- Happy Path ----


class TestRefreshHappyPath:
    @pytest.mark.asyncio
    async def test_success_returns_true(self, service, mock_client):
        """Installed model with dir on disk → RefreshResult.success=True."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is True
        assert result.model_id == MODEL_ID
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_four_graphs_refreshed(self, service, mock_client):
        """All 4 artifact graph names appear in graphs_refreshed."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert set(result.graphs_refreshed) == {"ontology", "shapes", "views", "rules"}

    @pytest.mark.asyncio
    async def test_clears_four_artifact_graphs(self, service, mock_client):
        """CLEAR SILENT issued for exactly 4 artifact graph IRIs."""
        graphs = ModelGraphs(MODEL_ID)
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            await service.refresh_artifacts(MODEL_ID)

        # Extract all CLEAR calls from transaction_update
        clear_calls = [
            call.args[1]
            for call in mock_client.transaction_update.call_args_list
            if "CLEAR SILENT" in call.args[1]
        ]

        assert len(clear_calls) == 4
        expected_iris = {graphs.ontology, graphs.shapes, graphs.views, graphs.rules}
        actual_iris = set()
        for sparql in clear_calls:
            # Extract IRI from "CLEAR SILENT GRAPH <iri>"
            iri = sparql.split("<")[1].split(">")[0]
            actual_iris.add(iri)
        assert actual_iris == expected_iris

    @pytest.mark.asyncio
    async def test_insert_data_for_non_empty_graphs(self, service, mock_client):
        """INSERT DATA issued for each non-empty artifact graph."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            await service.refresh_artifacts(MODEL_ID)

        insert_calls = [
            call.args[1]
            for call in mock_client.transaction_update.call_args_list
            if "INSERT DATA" in call.args[1]
        ]
        # 4 non-empty graphs → 4 INSERT DATA calls
        assert len(insert_calls) == 4

    @pytest.mark.asyncio
    async def test_transaction_committed(self, service, mock_client):
        """Transaction is committed after successful refresh."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            await service.refresh_artifacts(MODEL_ID)

        mock_client.begin_transaction.assert_awaited_once()
        mock_client.commit_transaction.assert_awaited_once_with("http://localhost/txn/1")
        mock_client.rollback_transaction.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_rules_graph_skipped(self, service, mock_client):
        """Rules graph with 0 triples → still cleared but no INSERT DATA issued."""
        archive = _make_archive(rules=Graph())  # Empty rules
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=archive),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert "rules" not in result.graphs_refreshed
        # 3 INSERT DATA (ontology, shapes, views) + 4 CLEAR = 7 total
        assert mock_client.transaction_update.await_count == 7

    @pytest.mark.asyncio
    async def test_none_rules_graph_skipped(self, service, mock_client):
        """Rules=None → still cleared but no INSERT DATA issued."""
        archive = _make_archive(rules=None)
        # ModelArchive.rules can be None per loader.py
        archive.rules = None
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=archive),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert "rules" not in result.graphs_refreshed


# ---- Seed Exclusion ----


class TestSeedExclusion:
    @pytest.mark.asyncio
    async def test_seed_graph_never_cleared(self, service, mock_client):
        """Seed graph IRI must NEVER appear in any CLEAR call."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            await service.refresh_artifacts(MODEL_ID)

        all_sparql = [
            call.args[1]
            for call in mock_client.transaction_update.call_args_list
        ]
        for sparql in all_sparql:
            assert SEED_GRAPH_IRI not in sparql, (
                f"Seed graph IRI found in SPARQL call: {sparql[:100]}"
            )

    @pytest.mark.asyncio
    async def test_seed_graph_never_inserted(self, service, mock_client):
        """Seed graph IRI must NEVER appear in any INSERT DATA call."""
        archive = _make_archive(seed=_make_graph([
            ("urn:seed:s1", "urn:seed:p1", "seed-value"),
        ]))
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=archive),
            patch.object(Path, "exists", return_value=True),
        ):
            await service.refresh_artifacts(MODEL_ID)

        insert_calls = [
            call.args[1]
            for call in mock_client.transaction_update.call_args_list
            if "INSERT DATA" in call.args[1]
        ]
        for sparql in insert_calls:
            assert SEED_GRAPH_IRI not in sparql, (
                f"Seed graph IRI found in INSERT DATA call: {sparql[:100]}"
            )

    @pytest.mark.asyncio
    async def test_registry_graph_never_touched(self, service, mock_client):
        """Registry graph (urn:sempkm:models) must not appear in any call."""
        from app.models.registry import MODELS_GRAPH

        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            await service.refresh_artifacts(MODEL_ID)

        all_sparql = [
            call.args[1]
            for call in mock_client.transaction_update.call_args_list
        ]
        for sparql in all_sparql:
            assert MODELS_GRAPH not in sparql, (
                f"Registry graph IRI found in SPARQL call: {sparql[:100]}"
            )


# ---- Error: Model Not Installed ----


class TestModelNotInstalled:
    @pytest.mark.asyncio
    async def test_returns_failure(self, service):
        """Model not in registry → success=False with error message."""
        with patch("app.services.models.is_model_installed", return_value=False):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        assert result.model_id == MODEL_ID
        assert any("not installed" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_no_transaction_started(self, service, mock_client):
        """Model not installed → no transaction opened."""
        with patch("app.services.models.is_model_installed", return_value=False):
            await service.refresh_artifacts(MODEL_ID)

        mock_client.begin_transaction.assert_not_awaited()


# ---- Error: Model Dir Missing From Disk ----


class TestModelDirMissing:
    @pytest.mark.asyncio
    async def test_returns_failure(self, service):
        """Model dir not on disk → success=False with error message."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch.object(Path, "exists", return_value=False),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        assert result.model_id == MODEL_ID
        assert any("not found on disk" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_no_transaction_started(self, service, mock_client):
        """Model dir missing → no transaction opened."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch.object(Path, "exists", return_value=False),
        ):
            await service.refresh_artifacts(MODEL_ID)

        mock_client.begin_transaction.assert_not_awaited()


# ---- Error: Transaction Rollback on Failure ----


class TestTransactionRollback:
    @pytest.mark.asyncio
    async def test_rollback_on_insert_failure(self, service, mock_client):
        """INSERT DATA failure → transaction rolled back, success=False."""
        call_count = 0

        async def fail_on_third_insert(txn_url, sparql):
            nonlocal call_count
            if "INSERT DATA" in sparql:
                call_count += 1
                if call_count >= 2:
                    raise Exception("Simulated SPARQL insert failure")

        mock_client.transaction_update = AsyncMock(side_effect=fail_on_third_insert)

        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        assert result.model_id == MODEL_ID
        assert any("Transaction error" in e for e in result.errors)
        mock_client.rollback_transaction.assert_awaited_once_with("http://localhost/txn/1")

    @pytest.mark.asyncio
    async def test_rollback_on_clear_failure(self, service, mock_client):
        """CLEAR SILENT failure → transaction rolled back, success=False."""
        async def fail_on_clear(txn_url, sparql):
            if "CLEAR SILENT" in sparql:
                raise Exception("Simulated clear failure")

        mock_client.transaction_update = AsyncMock(side_effect=fail_on_clear)

        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        mock_client.rollback_transaction.assert_awaited_once()
        mock_client.commit_transaction.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rollback_failure_still_returns_error(self, service, mock_client):
        """Even if rollback fails, result is still error (best-effort rollback)."""
        mock_client.transaction_update = AsyncMock(
            side_effect=Exception("INSERT failed")
        )
        mock_client.rollback_transaction = AsyncMock(
            side_effect=Exception("Rollback also failed")
        )

        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", return_value=_make_archive()),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        assert any("Transaction error" in e for e in result.errors)


# ---- Error: Manifest / Archive Loading Failures ----


class TestLoadingErrors:
    @pytest.mark.asyncio
    async def test_manifest_parse_error(self, service):
        """Manifest parse error → success=False, no transaction."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", side_effect=ValueError("bad yaml")),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        assert any("Manifest error" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_archive_load_error(self, service):
        """Archive load error → success=False, no transaction."""
        with (
            patch("app.services.models.is_model_installed", return_value=True),
            patch("app.services.models.parse_manifest", return_value=_make_manifest()),
            patch("app.services.models.load_archive", side_effect=FileNotFoundError("missing ontology.jsonld")),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await service.refresh_artifacts(MODEL_ID)

        assert result.success is False
        assert any("Archive loading error" in e for e in result.errors)


# ---- RefreshResult Dataclass ----


class TestRefreshResultDataclass:
    def test_defaults(self):
        """Default fields are empty lists."""
        r = RefreshResult(success=True, model_id="test")
        assert r.graphs_refreshed == []
        assert r.errors == []

    def test_fields_set(self):
        """All fields can be set explicitly."""
        r = RefreshResult(
            success=False,
            model_id="test",
            graphs_refreshed=["ontology", "shapes"],
            errors=["something broke"],
        )
        assert r.success is False
        assert r.model_id == "test"
        assert len(r.graphs_refreshed) == 2
        assert len(r.errors) == 1
