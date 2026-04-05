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
        """Load the real PPV dashboards file — 5 dashboards with names and blocks."""
        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")
        from app.models.manifest import parse_manifest
        manifest = parse_manifest(ppv_dir)
        result = load_tbox_dashboards(ppv_dir, manifest)
        assert result is not None
        assert len(result) >= 5
        names = [d["name"] for d in result]
        assert "Action Items" in names
        assert "Life Dashboard" in names
        assert "Projects Board" in names
        assert "Goals Overview" in names
        assert "Review Hub" in names
        for dash in result:
            assert "blocks" in dash
            assert len(dash["blocks"]) >= 1


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

    def test_real_ppv_workflows(self):
        """Load the real PPV workflows file — 5 workflows with dashboard_name refs."""
        ppv_dir = MODELS_DIR / "ppv"
        if not ppv_dir.exists():
            pytest.skip("ppv model not found")
        from app.models.manifest import parse_manifest
        manifest = parse_manifest(ppv_dir)
        result = load_tbox_workflows(ppv_dir, manifest)
        assert result is not None
        assert len(result) == 5
        names = [w["name"] for w in result]
        assert "Daily Check-in" in names
        assert "Weekly Review" in names
        assert "Monthly Review" in names
        assert "Quarterly Review" in names
        assert "Yearly Review" in names
        # Verify dashboard_name references exist in dashboard steps
        dashboard_steps = [
            step for wf in result for step in wf["steps"]
            if step["type"] == "dashboard"
        ]
        assert len(dashboard_steps) >= 5
        for step in dashboard_steps:
            assert "dashboard_name" in step["config"]


class TestResolveDashboardNames:
    """Tests for _resolve_dashboard_names helper."""

    def test_resolves_known_names(self):
        """Steps with dashboard_name get resolved to dashboard_id."""
        from app.services.models import _resolve_dashboard_names
        steps = [
            {"type": "dashboard", "label": "Review", "config": {"dashboard_name": "Action Items"}},
            {"type": "view", "label": "Table", "config": {"spec_iri": "urn:test"}},
        ]
        mapping = {"Action Items": "uuid-abc-123"}
        resolved = _resolve_dashboard_names(steps, mapping, "test-model")
        assert resolved[0]["config"]["dashboard_id"] == "uuid-abc-123"
        assert "dashboard_name" not in resolved[0]["config"]
        # view step unchanged
        assert resolved[1]["config"]["spec_iri"] == "urn:test"

    def test_unknown_name_leaves_unresolved(self):
        """Steps referencing unknown dashboard names are left as-is."""
        from app.services.models import _resolve_dashboard_names
        steps = [
            {"type": "dashboard", "label": "Missing", "config": {"dashboard_name": "No Such Dash"}},
        ]
        resolved = _resolve_dashboard_names(steps, {}, "test-model")
        assert resolved[0]["config"]["dashboard_name"] == "No Such Dash"
        assert "dashboard_id" not in resolved[0]["config"]

    def test_does_not_mutate_original(self):
        """Resolution returns copies, does not mutate original step dicts."""
        from app.services.models import _resolve_dashboard_names
        original_step = {"type": "dashboard", "label": "X", "config": {"dashboard_name": "Dash"}}
        steps = [original_step]
        mapping = {"Dash": "uuid-999"}
        resolved = _resolve_dashboard_names(steps, mapping, "test-model")
        # Original untouched
        assert "dashboard_name" in original_step["config"]
        assert "dashboard_id" not in original_step["config"]
        # Resolved has the new value
        assert resolved[0]["config"]["dashboard_id"] == "uuid-999"


class TestSeedWorkflows:
    """Verify seed.py SEED_WORKFLOWS after PPV migration to model-sourced workflows."""

    def test_seed_workflows_count(self):
        """SEED_WORKFLOWS has exactly 1 entry (Create & Review only)."""
        from app.dashboard.seed import SEED_WORKFLOWS
        assert len(SEED_WORKFLOWS) == 1
        assert SEED_WORKFLOWS[0]["name"] == "Create & Review"

    def test_seed_workflows_no_ppv_references(self):
        """SEED_WORKFLOWS has no PPV-specific references."""
        from app.dashboard.seed import SEED_WORKFLOWS
        ppv_ns = "urn:sempkm:model:ppv:"
        for wf in SEED_WORKFLOWS:
            for step in wf["steps"]:
                config = step.get("config", {})
                for value in config.values():
                    if isinstance(value, str):
                        assert ppv_ns not in value, f"PPV reference found in seed: {value}"
