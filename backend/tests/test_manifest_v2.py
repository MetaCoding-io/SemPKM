"""Tests for manifest v2 schema parsing and backward compatibility.

Verifies:
- All existing model directories parse without error
- v1 manifests (no manifest_version) parse with manifest_version=None
- v2 manifests parse with new fields (dashboards, workflows entrypoints)
- {modelId} placeholder resolution in entrypoint paths
- Optional fields in v2 manifests
"""

from pathlib import Path

import pytest

from app.models.manifest import ManifestSchema, ManifestEntrypoints, parse_manifest


# All model directories in the models/ folder
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_DIRS = sorted(p for p in MODELS_DIR.iterdir() if p.is_dir() and (p / "manifest.yaml").exists())


class TestV1BackwardCompat:
    """All existing v1 models must parse unchanged."""

    @pytest.mark.parametrize(
        "model_dir",
        MODEL_DIRS,
        ids=[d.name for d in MODEL_DIRS],
    )
    def test_existing_model_parses(self, model_dir: Path):
        """Every model with a manifest.yaml should parse without error."""
        manifest = parse_manifest(model_dir)
        assert manifest.modelId == model_dir.name or manifest.modelId  # sanity check
        assert manifest.name  # non-empty name
        assert manifest.version  # semver string

    def test_v1_manifest_has_no_manifest_version(self):
        """V1 manifests (e.g. basic-pkm) parse with manifest_version=None."""
        # basic-pkm is a v1 manifest — no manifest_version field
        basic_pkm = MODELS_DIR / "basic-pkm"
        if not basic_pkm.exists():
            pytest.skip("basic-pkm model not found")
        manifest = parse_manifest(basic_pkm)
        assert manifest.manifest_version is None

    def test_v1_manifest_has_no_dashboards(self):
        """V1 manifests have dashboards=None and workflows=None."""
        basic_pkm = MODELS_DIR / "basic-pkm"
        if not basic_pkm.exists():
            pytest.skip("basic-pkm model not found")
        manifest = parse_manifest(basic_pkm)
        assert manifest.entrypoints.dashboards is None
        assert manifest.entrypoints.workflows is None


class TestV2ManifestParsing:
    """V2 manifest with new fields parses correctly."""

    def test_ppv_v2_manifest_parses(self):
        """PPV model has manifest_version='2.0' and dashboards entrypoint."""
        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")
        manifest = parse_manifest(ppv_dir)
        assert manifest.manifest_version == "2.0"
        assert manifest.entrypoints.dashboards is not None
        assert "ppv" in manifest.entrypoints.dashboards  # resolved placeholder

    def test_v2_manifest_placeholder_resolution(self):
        """The {modelId} placeholder in entrypoint paths is resolved."""
        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")
        manifest = parse_manifest(ppv_dir)
        # dashboards entrypoint was "dashboards/{modelId}.json" or similar
        assert "{modelId}" not in (manifest.entrypoints.dashboards or "")
        assert "{modelId}" not in manifest.entrypoints.ontology
        assert "{modelId}" not in manifest.entrypoints.shapes

    def test_v2_manifest_without_dashboards(self):
        """A v2 manifest with manifest_version but no dashboards/workflows is valid."""
        # Construct a minimal v2 schema without optional entrypoints
        schema = ManifestSchema(
            manifest_version="2.0",
            modelId="test-model",
            version="1.0.0",
            name="Test Model",
            namespace="urn:sempkm:model:test-model:",
        )
        assert schema.manifest_version == "2.0"
        assert schema.entrypoints.dashboards is None
        assert schema.entrypoints.workflows is None

    def test_v2_manifest_with_both_entrypoints(self):
        """A v2 manifest can declare both dashboards and workflows entrypoints."""
        schema = ManifestSchema(
            manifest_version="2.0",
            modelId="test-model",
            version="1.0.0",
            name="Test Model",
            namespace="urn:sempkm:model:test-model:",
            entrypoints=ManifestEntrypoints(
                dashboards="dashboards/{modelId}.json",
                workflows="workflows/{modelId}.json",
            ),
        )
        # Placeholders should be resolved by the model_validator
        assert schema.entrypoints.dashboards == "dashboards/test-model.json"
        assert schema.entrypoints.workflows == "workflows/test-model.json"


class TestManifestEntrypoints:
    """Entrypoints model edge cases."""

    def test_default_entrypoints_have_no_dashboards(self):
        """Default ManifestEntrypoints has dashboards=None and workflows=None."""
        ep = ManifestEntrypoints()
        assert ep.dashboards is None
        assert ep.workflows is None

    def test_default_entrypoints_have_standard_paths(self):
        """Default entrypoints use {modelId} placeholder pattern."""
        ep = ManifestEntrypoints()
        assert "{modelId}" in ep.ontology
        assert "{modelId}" in ep.shapes
        assert "{modelId}" in ep.views
