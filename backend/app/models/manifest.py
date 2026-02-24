"""Manifest schema validation for Mental Model archives.

Defines a Pydantic model for manifest.yaml files and a parser
that reads and validates manifest files from model directories.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ManifestSettingDef(BaseModel):
    """Setting definition contributed by a Mental Model manifest."""

    key: str               # short key, e.g. "defaultNoteType" -- prefixed by modelId at service layer
    label: str
    description: str = ""
    input_type: str = "text"   # "toggle" | "select" | "text" | "color"
    options: list[str] | None = None
    default: str = ""


class ManifestIconContextDef(BaseModel):
    """Per-context icon/color/size override for a type."""

    icon: str
    color: str
    size: int | None = None


class ManifestIconDef(BaseModel):
    """Icon definition for a node type contributed by a Mental Model manifest."""

    type: str                                        # e.g. "bpkm:Note" -- expanded against manifest prefixes
    icon: str | None = None                          # fallback icon for all contexts
    color: str | None = None                         # fallback color for all contexts
    tree: ManifestIconContextDef | None = None
    graph: ManifestIconContextDef | None = None
    tab: ManifestIconContextDef | None = None


class ManifestEntrypoints(BaseModel):
    """Entrypoint file paths relative to model root.

    Paths support {modelId} placeholder which is resolved
    after the full manifest is parsed.
    """

    ontology: str = "ontology/{modelId}.jsonld"
    shapes: str = "shapes/{modelId}.jsonld"
    views: str = "views/{modelId}.jsonld"
    seed: str | None = "seed/{modelId}.jsonld"


class ManifestSchema(BaseModel):
    """manifest.yaml schema for Mental Model archives.

    Validates all required fields including modelId format,
    semver version, namespace pattern, and entrypoint paths.
    """

    modelId: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9-]*$",
        min_length=2,
        max_length=64,
    )
    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )
    description: str = Field(
        default="",
        max_length=2000,
    )
    namespace: str = Field(...)
    prefixes: dict[str, str] = Field(default_factory=dict)
    entrypoints: ManifestEntrypoints = Field(default_factory=ManifestEntrypoints)
    settings: list[ManifestSettingDef] = Field(default_factory=list)
    icons: list[ManifestIconDef] = Field(default_factory=list)

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str, info) -> str:
        """Namespace must follow the urn:sempkm:model:{modelId}: pattern."""
        model_id = info.data.get("modelId", "")
        expected = f"urn:sempkm:model:{model_id}:"
        if v != expected:
            raise ValueError(f"namespace must be '{expected}', got '{v}'")
        return v

    @model_validator(mode="after")
    def resolve_entrypoint_placeholders(self) -> "ManifestSchema":
        """Replace {modelId} placeholders in entrypoint paths."""
        ep = self.entrypoints
        ep.ontology = ep.ontology.replace("{modelId}", self.modelId)
        ep.shapes = ep.shapes.replace("{modelId}", self.modelId)
        ep.views = ep.views.replace("{modelId}", self.modelId)
        if ep.seed is not None:
            ep.seed = ep.seed.replace("{modelId}", self.modelId)
        return self


def parse_manifest(model_dir: Path) -> ManifestSchema:
    """Parse and validate manifest.yaml from a model directory.

    Args:
        model_dir: Path to the model archive directory.

    Returns:
        Validated ManifestSchema instance.

    Raises:
        ValueError: If manifest.yaml is missing or fails validation.
    """
    manifest_path = model_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise ValueError(
            f"manifest.yaml not found in model directory: {model_dir}"
        )
    try:
        with open(manifest_path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse manifest.yaml: {e}") from e

    if raw is None:
        raise ValueError(f"manifest.yaml is empty: {manifest_path}")

    return ManifestSchema.model_validate(raw)
