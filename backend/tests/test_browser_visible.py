"""Tests for browserVisible field and type filtering.

Covers:
- ManifestIconDef.browserVisible defaults and parsing
- get_hidden_type_iris() IRI resolution from manifest prefixes
- ShapesService.get_types() exclude_iris filtering
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from app.models.manifest import ManifestIconDef, ManifestSchema
from app.services.models import get_hidden_type_iris, _expand_prefix
from app.services.shapes import ShapesService


# ---------------------------------------------------------------------------
# ManifestIconDef.browserVisible field
# ---------------------------------------------------------------------------


class TestManifestIconDefBrowserVisible:
    """Tests for the browserVisible field on ManifestIconDef."""

    def test_default_is_true(self):
        """browserVisible defaults to True for backward compatibility."""
        icon_def = ManifestIconDef(type="bpkm:Note")
        assert icon_def.browserVisible is True

    def test_explicit_true(self):
        """Explicit True is accepted."""
        icon_def = ManifestIconDef(type="bpkm:Note", browserVisible=True)
        assert icon_def.browserVisible is True

    def test_explicit_false(self):
        """browserVisible=False parses correctly."""
        icon_def = ManifestIconDef(type="bpkm:ReadActivity", browserVisible=False)
        assert icon_def.browserVisible is False

    def test_manifest_schema_with_hidden_icons(self):
        """A full manifest with browserVisible=false on an icon entry parses."""
        manifest = ManifestSchema(
            modelId="test-model",
            version="1.0.0",
            name="Test Model",
            namespace="urn:sempkm:model:test-model:",
            prefixes={"tm": "urn:sempkm:model:test-model:"},
            icons=[
                ManifestIconDef(type="tm:Visible", icon="eye"),
                ManifestIconDef(
                    type="tm:Hidden", icon="eye-off", browserVisible=False
                ),
            ],
        )
        assert manifest.icons[0].browserVisible is True
        assert manifest.icons[1].browserVisible is False


# ---------------------------------------------------------------------------
# _expand_prefix helper
# ---------------------------------------------------------------------------


class TestExpandPrefix:
    """Tests for prefix expansion."""

    def test_expand_known_prefix(self):
        prefixes = {"bpkm": "urn:sempkm:model:basic-pkm:"}
        assert _expand_prefix("bpkm:Note", prefixes) == "urn:sempkm:model:basic-pkm:Note"

    def test_unknown_prefix_returns_original(self):
        prefixes = {"bpkm": "urn:sempkm:model:basic-pkm:"}
        assert _expand_prefix("unknown:Foo", prefixes) == "unknown:Foo"

    def test_http_iri_passthrough(self):
        assert _expand_prefix("http://example.org/Type", {}) == "http://example.org/Type"

    def test_urn_iri_passthrough(self):
        assert _expand_prefix("urn:sempkm:model:x:Type", {}) == "urn:sempkm:model:x:Type"

    def test_no_colon_passthrough(self):
        assert _expand_prefix("NoColon", {}) == "NoColon"


# ---------------------------------------------------------------------------
# get_hidden_type_iris()
# ---------------------------------------------------------------------------


def _write_manifest(tmpdir: Path, model_id: str, icons: list[dict],
                    prefixes: dict[str, str] | None = None) -> Path:
    """Write a minimal manifest.yaml to a model subdirectory and return the path."""
    if prefixes is None:
        prefixes = {model_id: f"urn:sempkm:model:{model_id}:"}
    model_dir = tmpdir / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "modelId": model_id,
        "version": "1.0.0",
        "name": f"Test {model_id}",
        "namespace": f"urn:sempkm:model:{model_id}:",
        "prefixes": prefixes,
        "icons": icons,
        "entrypoints": {
            "ontology": "ontology/test.jsonld",
            "shapes": "shapes/test.jsonld",
            "views": "views/test.jsonld",
            "seed": None,
        },
    }
    with open(model_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)
    return model_dir


class TestGetHiddenTypeIris:
    """Tests for get_hidden_type_iris()."""

    def test_none_models_dir_returns_empty(self):
        assert get_hidden_type_iris(None) == set()

    def test_nonexistent_dir_returns_empty(self):
        assert get_hidden_type_iris("/nonexistent/path/xyz") == set()

    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert get_hidden_type_iris(tmpdir) == set()

    def test_all_visible_returns_empty(self):
        """When all icons have browserVisible=True (default), returns empty set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_manifest(
                Path(tmpdir), "test-model",
                icons=[
                    {"type": "test-model:Note", "icon": "file-text"},
                    {"type": "test-model:Task", "icon": "check-square"},
                ],
            )
            result = get_hidden_type_iris(tmpdir)
            assert result == set()

    def test_hidden_types_resolved(self):
        """Hidden icons have their prefixed type expanded to full IRI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_manifest(
                Path(tmpdir), "test-model",
                icons=[
                    {"type": "test-model:Note", "icon": "file-text"},
                    {"type": "test-model:ReadActivity", "icon": "eye",
                     "browserVisible": False},
                    {"type": "test-model:SyncCursor", "icon": "refresh-cw",
                     "browserVisible": False},
                ],
            )
            result = get_hidden_type_iris(tmpdir)
            assert result == {
                "urn:sempkm:model:test-model:ReadActivity",
                "urn:sempkm:model:test-model:SyncCursor",
            }

    def test_multiple_models(self):
        """Hidden types from multiple model directories are combined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_manifest(
                Path(tmpdir), "model-a",
                icons=[
                    {"type": "model-a:Hidden", "icon": "x", "browserVisible": False},
                ],
            )
            _write_manifest(
                Path(tmpdir), "model-b",
                icons=[
                    {"type": "model-b:AlsoHidden", "icon": "x", "browserVisible": False},
                    {"type": "model-b:Visible", "icon": "eye"},
                ],
            )
            result = get_hidden_type_iris(tmpdir)
            assert result == {
                "urn:sempkm:model:model-a:Hidden",
                "urn:sempkm:model:model-b:AlsoHidden",
            }

    def test_bad_manifest_skipped(self):
        """A model with an invalid manifest.yaml is silently skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = Path(tmpdir) / "bad-model"
            bad_dir.mkdir()
            (bad_dir / "manifest.yaml").write_text("not: valid: yaml: {{{{")
            _write_manifest(
                Path(tmpdir), "good-model",
                icons=[
                    {"type": "good-model:Hidden", "icon": "x", "browserVisible": False},
                ],
            )
            result = get_hidden_type_iris(tmpdir)
            assert "urn:sempkm:model:good-model:Hidden" in result


# ---------------------------------------------------------------------------
# ShapesService.get_types() with exclude_iris
# ---------------------------------------------------------------------------


class TestGetTypesFiltering:
    """Tests for ShapesService.get_types() exclude_iris parameter."""

    @pytest.fixture
    def shapes_service(self):
        """Create a ShapesService with a mocked triplestore client."""
        mock_client = AsyncMock()
        return ShapesService(mock_client)

    @pytest.fixture
    def mock_node_shapes(self):
        """Return a list of mock NodeShapeForm objects."""
        from app.services.shapes import NodeShapeForm
        return [
            NodeShapeForm(
                shape_iri="urn:shape:note",
                target_class="urn:sempkm:model:basic-pkm:Note",
                label="Note",
            ),
            NodeShapeForm(
                shape_iri="urn:shape:task",
                target_class="urn:sempkm:model:basic-pkm:Task",
                label="Task",
            ),
            NodeShapeForm(
                shape_iri="urn:shape:activity",
                target_class="urn:sempkm:model:basic-pkm:ReadActivity",
                label="Read Activity",
            ),
        ]

    @pytest.mark.asyncio
    async def test_no_exclude_returns_all(self, shapes_service, mock_node_shapes):
        """Without exclude_iris, all types are returned (backward compat)."""
        with patch.object(shapes_service, "get_node_shapes", return_value=mock_node_shapes):
            result = await shapes_service.get_types()
            assert len(result) == 3
            iris = {t["iri"] for t in result}
            assert "urn:sempkm:model:basic-pkm:ReadActivity" in iris

    @pytest.mark.asyncio
    async def test_exclude_none_returns_all(self, shapes_service, mock_node_shapes):
        """Passing exclude_iris=None returns all types."""
        with patch.object(shapes_service, "get_node_shapes", return_value=mock_node_shapes):
            result = await shapes_service.get_types(exclude_iris=None)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_exclude_empty_set_returns_all(self, shapes_service, mock_node_shapes):
        """Passing an empty set returns all types."""
        with patch.object(shapes_service, "get_node_shapes", return_value=mock_node_shapes):
            result = await shapes_service.get_types(exclude_iris=set())
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_exclude_filters_hidden(self, shapes_service, mock_node_shapes):
        """Types in exclude_iris are removed from the result."""
        hidden = {"urn:sempkm:model:basic-pkm:ReadActivity"}
        with patch.object(shapes_service, "get_node_shapes", return_value=mock_node_shapes):
            result = await shapes_service.get_types(exclude_iris=hidden)
            assert len(result) == 2
            iris = {t["iri"] for t in result}
            assert "urn:sempkm:model:basic-pkm:ReadActivity" not in iris
            assert "urn:sempkm:model:basic-pkm:Note" in iris
            assert "urn:sempkm:model:basic-pkm:Task" in iris

    @pytest.mark.asyncio
    async def test_exclude_multiple(self, shapes_service, mock_node_shapes):
        """Multiple types can be excluded."""
        hidden = {
            "urn:sempkm:model:basic-pkm:ReadActivity",
            "urn:sempkm:model:basic-pkm:Task",
        }
        with patch.object(shapes_service, "get_node_shapes", return_value=mock_node_shapes):
            result = await shapes_service.get_types(exclude_iris=hidden)
            assert len(result) == 1
            assert result[0]["iri"] == "urn:sempkm:model:basic-pkm:Note"

    @pytest.mark.asyncio
    async def test_exclude_nonexistent_iri(self, shapes_service, mock_node_shapes):
        """Excluding an IRI that doesn't exist in shapes has no effect."""
        hidden = {"urn:nonexistent:Type"}
        with patch.object(shapes_service, "get_node_shapes", return_value=mock_node_shapes):
            result = await shapes_service.get_types(exclude_iris=hidden)
            assert len(result) == 3
