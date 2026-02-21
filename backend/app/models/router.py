"""API router for Mental Model management endpoints.

Provides endpoints for installing, removing, and listing Mental Models.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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

    result = await model_service.install(model_dir)
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail={"errors": result.errors},
        )

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
    model_service: ModelService = Depends(get_model_service),
) -> RemoveResponse:
    """Remove an installed Mental Model.

    Checks for user data before removal. If instances of model types
    exist in the current state graph, removal is blocked with 409 Conflict.
    """
    result = await model_service.remove(model_id)
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

    return RemoveResponse(
        model_id=result.model_id,
        message=f"Model '{result.model_id}' removed successfully",
    )


@router.get(
    "",
    response_model=ModelListResponse,
)
async def list_models(
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
