---
estimated_steps: 30
estimated_files: 7
skills_used: []
---

# T01: Manifest v2 schema, Alembic migration, and service extensions

Add manifest_version field and optional dashboards/workflows entrypoints to ManifestSchema. Create Alembic migration adding nullable source_model column to dashboard_specs and workflow_specs. Extend DashboardService and WorkflowService with methods for model-sourced CRUD (create_for_model, delete_by_model, list_by_model). Add a TBox loader module that reads JSON dashboard/workflow files from model archives.

## Steps

1. Edit `backend/app/models/manifest.py`:
   - Add `manifest_version: str | None = None` field to ManifestSchema (Optional, default None)
   - Add `dashboards: str | None = None` and `workflows: str | None = None` to ManifestEntrypoints
   - Add {modelId} placeholder resolution for the new entrypoint fields in the model_validator

2. Create Alembic migration `backend/migrations/versions/025_add_source_model.py`:
   - Revision 025, revises 024
   - `op.add_column('dashboard_specs', sa.Column('source_model', sa.String(64), nullable=True))`
   - `op.add_column('workflow_specs', sa.Column('source_model', sa.String(64), nullable=True))`
   - Add index on source_model for both tables (efficient delete-by-model)
   - downgrade: drop columns

3. Edit `backend/app/dashboard/models.py`:
   - Add `source_model: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, index=True)` to DashboardSpec

4. Edit `backend/app/workflow/models.py`:
   - Add `source_model: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, index=True)` to WorkflowSpec

5. Extend `backend/app/dashboard/service.py`:
   - Add `source_model` param to `create()` method (Optional[str] = None), pass to DashboardSpec constructor
   - Add `source_model` field to DashboardData dataclass, populate in `_to_data()`
   - Add `async def delete_by_model(self, model_id: str) -> int` — DELETE WHERE source_model = model_id, returns rowcount
   - Add `async def list_by_model(self, model_id: str) -> list[DashboardData]` — SELECT WHERE source_model = model_id

6. Extend `backend/app/workflow/service.py`:
   - Same 3 additions as dashboard: source_model param on create, delete_by_model, list_by_model
   - Add `source_model` field to WorkflowData dataclass

7. Create `backend/app/models/tbox_loader.py`:
   - `load_tbox_dashboards(model_dir: Path, manifest: ManifestSchema) -> list[dict] | None` — loads JSON file at entrypoints.dashboards path, returns list of dashboard dicts, or None if no entrypoint
   - `load_tbox_workflows(model_dir: Path, manifest: ManifestSchema) -> list[dict] | None` — same for workflows
   - JSON format: `{"dashboards": [...]}` where each item has name, description, layout, blocks (matching DashboardService.create params)
   - Validation: check each dashboard has required 'name' field, each workflow has required 'name' and 'steps' fields
   - Raise ValueError with clear message on malformed JSON

## Inputs

- `backend/app/models/manifest.py`
- `backend/app/dashboard/models.py`
- `backend/app/workflow/models.py`
- `backend/app/dashboard/service.py`
- `backend/app/workflow/service.py`
- `backend/migrations/versions/024_add_security_audit_log.py`

## Expected Output

- `backend/app/models/manifest.py`
- `backend/migrations/versions/025_add_source_model.py`
- `backend/app/dashboard/models.py`
- `backend/app/workflow/models.py`
- `backend/app/dashboard/service.py`
- `backend/app/workflow/service.py`
- `backend/app/models/tbox_loader.py`

## Verification

cd backend && .venv/bin/python -c "from app.models.manifest import ManifestSchema; m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:', manifest_version='2.0', entrypoints={'dashboards': 'dashboards/test.json'}); print('v2 OK:', m.manifest_version, m.entrypoints.dashboards)" && .venv/bin/python -c "from app.models.manifest import ManifestSchema; m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:'); print('v1 OK:', m.manifest_version is None, m.entrypoints.dashboards is None)" && .venv/bin/python -c "from app.models.tbox_loader import load_tbox_dashboards; print('loader imported OK')"
