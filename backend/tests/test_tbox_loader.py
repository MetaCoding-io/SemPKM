"""Tests for TBox loader — dashboard/workflow JSON file loading.

Verifies:
- Valid JSON files load correctly
- None entrypoint returns None (no dashboards/workflows declared)
- Missing file raises ValueError
- Malformed JSON raises ValueError
- Missing required fields raise ValueError
- Real PPV dashboards file loads
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.models.manifest import ManifestSchema, ManifestEntrypoints
from app.models.tbox_loader import load_tbox_dashboards, load_tbox_workflows


MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def _make_manifest(model_id: str = "test-model", dashboards: str | None = None, workflows: str | None = None) -> ManifestSchema:
    """Create a minimal ManifestSchema with specified entrypoints."""
    return ManifestSchema(
        manifest_version="2.0",
        modelId=model_id,
        version="1.0.0",
        name="Test Model",
        namespace=f"urn:sempkm:model:{model_id}:",
        entrypoints=ManifestEntrypoints(
            dashboards=dashboards,
            workflows=workflows,
        ),
    )


class TestLoadTboxDashboards:
    """Tests for load_tbox_dashboards."""

    def test_valid_json_returns_list(self, tmp_path: Path):
        """Valid dashboards JSON returns list of dashboard dicts."""
        dash_file = tmp_path / "dashboards" / "test.json"
        dash_file.parent.mkdir(parents=True)
        dash_file.write_text(json.dumps({
            "dashboards": [
                {"name": "Dashboard 1", "layout": "single", "blocks": []},
                {"name": "Dashboard 2", "description": "Test"},
            ]
        }))
        manifest = _make_manifest(dashboards="dashboards/test.json")
        result = load_tbox_dashboards(tmp_path, manifest)
        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "Dashboard 1"
        assert result[1]["name"] == "Dashboard 2"

    def test_none_entrypoint_returns_none(self, tmp_path: Path):
        """When manifest has no dashboards entrypoint, returns None."""
        manifest = _make_manifest(dashboards=None)
        result = load_tbox_dashboards(tmp_path, manifest)
        assert result is None

    def test_missing_file_raises_valueerror(self, tmp_path: Path):
        """When the declared file doesn't exist, raises ValueError."""
        manifest = _make_manifest(dashboards="dashboards/nonexistent.json")
        with pytest.raises(ValueError, match="not found"):
            load_tbox_dashboards(tmp_path, manifest)

    def test_malformed_json_raises_valueerror(self, tmp_path: Path):
        """Malformed JSON in dashboards file raises ValueError."""
        bad_file = tmp_path / "dashboards" / "bad.json"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text("{not valid json!!!")
        manifest = _make_manifest(dashboards="dashboards/bad.json")
        with pytest.raises(ValueError, match="Malformed JSON"):
            load_tbox_dashboards(tmp_path, manifest)

    def test_missing_name_raises_valueerror(self, tmp_path: Path):
        """Dashboard entry without 'name' raises ValueError."""
        dash_file = tmp_path / "dashboards" / "test.json"
        dash_file.parent.mkdir(parents=True)
        dash_file.write_text(json.dumps({
            "dashboards": [{"layout": "single"}]  # missing 'name'
        }))
        manifest = _make_manifest(dashboards="dashboards/test.json")
        with pytest.raises(ValueError, match="missing required 'name'"):
            load_tbox_dashboards(tmp_path, manifest)

    def test_missing_dashboards_key_raises_valueerror(self, tmp_path: Path):
        """JSON without top-level 'dashboards' key raises ValueError."""
        dash_file = tmp_path / "dashboards" / "test.json"
        dash_file.parent.mkdir(parents=True)
        dash_file.write_text(json.dumps({"items": []}))
        manifest = _make_manifest(dashboards="dashboards/test.json")
        with pytest.raises(ValueError, match="top-level 'dashboards' array"):
            load_tbox_dashboards(tmp_path, manifest)

    def test_real_ppv_dashboards(self):
        """Load the real PPV dashboards file."""
        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")
        from app.models.manifest import parse_manifest
        manifest = parse_manifest(ppv_dir)
        result = load_tbox_dashboards(ppv_dir, manifest)
        assert result is not None
        assert len(result) >= 1
        assert result[0]["name"]  # has a name


class TestLoadTboxWorkflows:
    """Tests for load_tbox_workflows."""

    def test_valid_json_returns_list(self, tmp_path: Path):
        """Valid workflows JSON returns list of workflow dicts."""
        wf_file = tmp_path / "workflows" / "test.json"
        wf_file.parent.mkdir(parents=True)
        wf_file.write_text(json.dumps({
            "workflows": [
                {"name": "Workflow 1", "steps": [{"type": "form"}]},
            ]
        }))
        manifest = _make_manifest(workflows="workflows/test.json")
        result = load_tbox_workflows(tmp_path, manifest)
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "Workflow 1"

    def test_none_entrypoint_returns_none(self, tmp_path: Path):
        """When manifest has no workflows entrypoint, returns None."""
        manifest = _make_manifest(workflows=None)
        result = load_tbox_workflows(tmp_path, manifest)
        assert result is None

    def test_missing_file_raises_valueerror(self, tmp_path: Path):
        """When the declared file doesn't exist, raises ValueError."""
        manifest = _make_manifest(workflows="workflows/nonexistent.json")
        with pytest.raises(ValueError, match="not found"):
            load_tbox_workflows(tmp_path, manifest)

    def test_malformed_json_raises_valueerror(self, tmp_path: Path):
        """Malformed JSON in workflows file raises ValueError."""
        bad_file = tmp_path / "workflows" / "bad.json"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text("{not valid json!!!")
        manifest = _make_manifest(workflows="workflows/bad.json")
        with pytest.raises(ValueError, match="Malformed JSON"):
            load_tbox_workflows(tmp_path, manifest)

    def test_missing_name_raises_valueerror(self, tmp_path: Path):
        """Workflow entry without 'name' raises ValueError."""
        wf_file = tmp_path / "workflows" / "test.json"
        wf_file.parent.mkdir(parents=True)
        wf_file.write_text(json.dumps({
            "workflows": [{"steps": [{"type": "form"}]}]  # missing 'name'
        }))
        manifest = _make_manifest(workflows="workflows/test.json")
        with pytest.raises(ValueError, match="missing required 'name'"):
            load_tbox_workflows(tmp_path, manifest)

    def test_missing_steps_raises_valueerror(self, tmp_path: Path):
        """Workflow entry without 'steps' raises ValueError."""
        wf_file = tmp_path / "workflows" / "test.json"
        wf_file.parent.mkdir(parents=True)
        wf_file.write_text(json.dumps({
            "workflows": [{"name": "No Steps"}]
        }))
        manifest = _make_manifest(workflows="workflows/test.json")
        with pytest.raises(ValueError, match="missing required 'steps'"):
            load_tbox_workflows(tmp_path, manifest)

    def test_missing_workflows_key_raises_valueerror(self, tmp_path: Path):
        """JSON without top-level 'workflows' key raises ValueError."""
        wf_file = tmp_path / "workflows" / "test.json"
        wf_file.parent.mkdir(parents=True)
        wf_file.write_text(json.dumps({"items": []}))
        manifest = _make_manifest(workflows="workflows/test.json")
        with pytest.raises(ValueError, match="top-level 'workflows' array"):
            load_tbox_workflows(tmp_path, manifest)
