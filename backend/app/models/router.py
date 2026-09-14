"""API router for Mental Model management endpoints.

Provides endpoints for installing, removing, and listing Mental Models.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.dependencies import get_model_service
from app.services.models import ModelService

router = APIRouter(prefix="/api/models", tags=["models"])


class InstallRequest(BaseModel):
    """Request body for model installation."""

    path: str = Field(
        ...,
        description="Absolute path to the model archive directory",
    )


class InstallResponse(BaseModel):
    """Response for successful model installation."""

    model_id: str
    message: str
    warnings: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Response for failed operations."""

    errors: list[str]


class RemoveResponse(BaseModel):
    """Response for successful model removal."""

    model_id: str
    message: str


class ModelInfo(BaseModel):
    """Model information for list responses."""

    model_id: str
    version: str
    name: str
    description: str
    installed_at: str


class ModelListResponse(BaseModel):
    """Response for listing installed models."""

    models: list[ModelInfo]
    count: int


@router.post(
    "/install",
    response_model=InstallResponse,
    status_code=201,
    responses={400: {"model": ErrorResponse}},
)
async def install_model(
    body: InstallRequest,
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
) -> InstallResponse:
    """Install a Mental Model from a directory path.

    Validates the manifest, loads and validates the archive, writes all
    artifacts to the triplestore, and registers the model.
    """
    model_dir = Path(body.path)
    if not model_dir.exists():
        raise HTTPException(
            status_code=400,
            detail={"errors": [f"Directory does not exist: {body.path}"]},
        )

    result = await model_service.install(model_dir, user_id=user.id)
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail={"errors": result.errors},
        )

    # Invalidate ViewSpec cache after successful model install
    request.app.state.view_spec_service.invalidate_cache()

    return InstallResponse(
        model_id=result.model_id,
        message=f"Model '{result.model_id}' installed successfully",
        warnings=result.warnings,
    )


@router.delete(
    "/{model_id}",
    response_model=RemoveResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def remove_model(
    model_id: str,
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
) -> RemoveResponse:
    """Remove an installed Mental Model.

    Checks for user data before removal. If instances of model types
    exist in the current state graph, removal is blocked with 409 Conflict.
    """
    result = await model_service.remove(model_id, user_id=user.id)
    if not result.success:
        # Determine appropriate status code
        error_text = " ".join(result.errors)
        if "not installed" in error_text:
            raise HTTPException(
                status_code=404,
                detail={"errors": result.errors},
            )
        elif "user data exists" in error_text:
            raise HTTPException(
                status_code=409,
                detail={"errors": result.errors},
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={"errors": result.errors},
            )

    # Invalidate ViewSpec cache after successful model removal
    request.app.state.view_spec_service.invalidate_cache()

    return RemoveResponse(
        model_id=result.model_id,
        message=f"Model '{result.model_id}' removed successfully",
    )


@router.get(
    "",
    response_model=ModelListResponse,
)
async def list_models(
    user: User = Depends(get_current_user),
    model_service: ModelService = Depends(get_model_service),
) -> ModelListResponse:
    """List all installed Mental Models.

    Returns model metadata including model_id, version, name,
    description, and installation timestamp.
    """
    models = await model_service.list_models()
    return ModelListResponse(
        models=[
            ModelInfo(
                model_id=m.model_id,
                version=m.version,
                name=m.name,
                description=m.description,
                installed_at=m.installed_at,
            )
            for m in models
        ],
        count=len(models),
    )


@router.get(
    "/{model_id}/docs",
    response_class=PlainTextResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_model_docs(
    model_id: str,
    user: User = Depends(get_current_user),
    model_service: ModelService = Depends(get_model_service),
) -> PlainTextResponse:
    """Return the Markdown documentation bundled with an installed model.

    Serves the file declared as ``entrypoints.docs`` in the model manifest
    (or the archive's root ``README.md``) as ``text/markdown``. Returns 404
    when the model is not installed or ships no documentation.
    """
    models = await model_service.list_models()
    if not any(m.model_id == model_id for m in models):
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' is not installed")
    docs = model_service.get_model_docs(model_id)
    if docs is None:
        raise HTTPException(
            status_code=404, detail=f"Model '{model_id}' ships no documentation"
        )
    return PlainTextResponse(docs, media_type="text/markdown; charset=utf-8")


class MigrationStepPreview(BaseModel):
    """One step's contribution to an upgrade plan."""

    id: str
    kind: str
    label: str
    deletes: int
    inserts: int
    samples: dict[str, list[str]]


class MigrationPreview(BaseModel):
    """One migration's contribution to an upgrade plan."""

    version: str
    description: str
    delete_count: int
    insert_count: int
    already_applied: bool
    steps: list[MigrationStepPreview] = Field(default_factory=list)


class UpgradePlanResponse(BaseModel):
    """Read-only preview of what upgrading a model would change."""

    model_id: str
    from_version: str
    to_version: str
    delete_count: int
    insert_count: int
    migrations: list[MigrationPreview]
    warnings: list[str] = Field(default_factory=list)


class UpgradeResponse(BaseModel):
    """Result of an in-place model upgrade."""

    model_id: str
    from_version: str
    to_version: str
    migrations_applied: list[str]
    migrations_skipped: list[str]
    triples_deleted: int
    triples_inserted: int
    warnings: list[str] = Field(default_factory=list)


@router.get(
    "/{model_id}/upgrade-plan",
    response_model=UpgradePlanResponse,
    responses={400: {"model": ErrorResponse}},
)
async def get_upgrade_plan(
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
) -> UpgradePlanResponse:
    """Preview an upgrade without applying it.

    Compiles each pending migration into the exact triples it would remove
    and add. Issues only SELECT queries, so it is safe to call at any time.
    """
    plan = await model_service.plan_upgrade(model_id)
    if not plan.success:
        raise HTTPException(status_code=400, detail={"errors": plan.errors})

    return UpgradePlanResponse(
        model_id=plan.model_id,
        from_version=plan.from_version,
        to_version=plan.to_version,
        delete_count=plan.delete_count,
        insert_count=plan.insert_count,
        warnings=plan.warnings,
        migrations=[
            MigrationPreview(
                version=m.version,
                description=m.description,
                delete_count=m.delete_count,
                insert_count=m.insert_count,
                already_applied=m.already_applied,
                steps=[MigrationStepPreview(**step) for step in m.steps],
            )
            for m in plan.migrations
        ],
    )


@router.post(
    "/{model_id}/upgrade",
    response_model=UpgradeResponse,
    responses={400: {"model": ErrorResponse}},
)
async def upgrade_model(
    model_id: str,
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
) -> UpgradeResponse:
    """Upgrade an installed model in place, migrating its instance data.

    Refreshes the model's schema artifacts from the on-disk archive, then
    applies each pending migration as one atomic event. Never deletes user
    data, so unlike remove-then-reinstall it is not blocked when instances of
    the model's types exist.
    """
    result = await model_service.upgrade(model_id, user_id=user.id)
    if not result.success:
        raise HTTPException(status_code=400, detail={"errors": result.errors})

    request.app.state.view_spec_service.invalidate_cache()

    return UpgradeResponse(
        model_id=result.model_id,
        from_version=result.from_version,
        to_version=result.to_version,
        migrations_applied=result.migrations_applied,
        migrations_skipped=result.migrations_skipped,
        triples_deleted=result.triples_deleted,
        triples_inserted=result.triples_inserted,
        warnings=result.warnings,
    )


class MigrationLedgerItem(BaseModel):
    """One migration recorded against an installed model."""

    version: str
    removed_count: int
    added_count: int
    reversible: bool
    is_latest: bool


class MigrationLedgerResponse(BaseModel):
    """The migrations applied to a model, newest first."""

    model_id: str
    migrations: list[MigrationLedgerItem]


class RollbackResponse(BaseModel):
    """Result of reversing one applied migration."""

    model_id: str
    version: str
    triples_restored: int
    triples_removed: int


@router.get(
    "/{model_id}/migrations",
    response_model=MigrationLedgerResponse,
    responses={404: {"model": ErrorResponse}},
)
async def list_model_migrations(
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
) -> MigrationLedgerResponse:
    """List the migrations applied to an installed model, newest first."""
    models = await model_service.list_models()
    if not any(m.model_id == model_id for m in models):
        raise HTTPException(
            status_code=404, detail=f"Model '{model_id}' is not installed"
        )
    entries = await model_service.list_applied_migrations(model_id)
    return MigrationLedgerResponse(
        model_id=model_id,
        migrations=[
            MigrationLedgerItem(
                version=e.version,
                removed_count=e.removed_count,
                added_count=e.added_count,
                reversible=e.reversible,
                is_latest=e.is_latest,
            )
            for e in entries
        ],
    )


@router.post(
    "/{model_id}/migrations/{version}/rollback",
    response_model=RollbackResponse,
    responses={400: {"model": ErrorResponse}},
)
async def rollback_model_migration(
    model_id: str,
    version: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
) -> RollbackResponse:
    """Reverse one applied migration from its journal.

    Only the most recently applied migration can be reversed: a later
    migration may have rewritten the same triples an earlier journal refers
    to. Rollback restores instance data only, leaving the model's schema
    artifacts and recorded version as they are.
    """
    result = await model_service.rollback_migration(model_id, version, user.id)
    if not result.success:
        raise HTTPException(status_code=400, detail={"errors": result.errors})

    return RollbackResponse(
        model_id=result.model_id,
        version=result.version,
        triples_restored=result.triples_restored,
        triples_removed=result.triples_removed,
    )
