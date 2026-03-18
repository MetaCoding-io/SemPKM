"""
App manifest schema — validates manifest.yaml for SemPKM applications.

Follows the same conventions as the Mental Model ManifestSchema:
- camelCase field names (matching YAML keys)
- Strict validation with regex patterns and length constraints
- Custom validators for cross-field consistency
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Nested models ──


class AppAuthor(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str | None = None


class AppModelDependency(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=64)
    version: str  # semver range, validated below
    optional: bool = False

    @field_validator("version")
    @classmethod
    def validate_version_range(cls, v: str) -> str:
        from packaging.specifiers import InvalidSpecifier, SpecifierSet

        try:
            SpecifierSet(v)
        except InvalidSpecifier:
            raise ValueError(f"Invalid semver range: {v}")
        return v


class AppDependencies(BaseModel):
    models: list[AppModelDependency] = []
    platform: str = ">=0.1.0"

    @field_validator("platform")
    @classmethod
    def validate_platform_range(cls, v: str) -> str:
        from packaging.specifiers import InvalidSpecifier, SpecifierSet

        try:
            SpecifierSet(v)
        except InvalidSpecifier:
            raise ValueError(f"Invalid platform version range: {v}")
        return v


class AppPermissionsSparql(BaseModel):
    read: bool = False


class AppPermissions(BaseModel):
    commands: list[str] = []
    sparql: AppPermissionsSparql = AppPermissionsSparql()
    network: list[str] = []
    backgroundTasks: bool = False
    settings: bool = False


class AppBackend(BaseModel):
    entrypoint: str = Field(
        min_length=1,
        description="Python module:class path, e.g. 'backend.app:RSSReaderApp'",
    )
    requirements: str = "requirements.txt"


class AppTaskRetryPolicy(BaseModel):
    maxRetries: int = Field(default=3, ge=0, le=10)
    backoffMultiplier: int = Field(default=2, ge=1, le=10)
    maxBackoff: str = "5m"


class AppTask(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=64)
    description: str = Field(min_length=1, max_length=500)
    interval: str  # validated below
    configurable: bool = False
    retryPolicy: AppTaskRetryPolicy = AppTaskRetryPolicy()

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        """Accept shorthand (30s, 5m, 1h, 6h, 1d) or ISO 8601 duration."""
        shorthand = re.match(r"^(\d+)(s|m|h|d)$", v)
        if shorthand:
            amount, unit = int(shorthand.group(1)), shorthand.group(2)
            seconds = amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
            if seconds < 30:
                raise ValueError("Minimum interval is 30 seconds")
            if seconds > 86400:
                raise ValueError("Maximum interval is 24 hours")
            return v
        iso = re.match(r"^PT(\d+[HMS])+$", v)
        if iso:
            return v
        raise ValueError(
            f"Invalid interval: {v}. Use shorthand (5m) or ISO 8601 (PT5M)"
        )


class AppFrontend(BaseModel):
    staticDir: str = "frontend/static"
    css: list[str] = []
    js: list[str] = []


class AppPage(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", min_length=2, max_length=64)
    path: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=64)
    nav: str | None = "apps"
    fragment: str = Field(min_length=1)


class AppRightPaneContribution(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=64)
    fragment: str = Field(min_length=1)
    context: str = "object"  # "object" | "view" | "always"
    targetTypes: list[str] = ["*"]
    priority: int = Field(default=50, ge=0, le=100)


class AppViewContribution(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=100)
    icon: str = Field(min_length=1, max_length=64)
    fragment: str = Field(min_length=1)


class AppCommandPaletteEntry(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    label: str = Field(min_length=1, max_length=100)
    keywords: list[str] = []
    actionType: str  # "dialog" | "post" | "navigate"
    fragment: str | None = None
    endpoint: str | None = None
    path: str | None = None

    @model_validator(mode="after")
    def validate_action_target(self) -> "AppCommandPaletteEntry":
        if self.actionType == "dialog" and not self.fragment:
            raise ValueError("dialog action requires fragment")
        if self.actionType == "post" and not self.endpoint:
            raise ValueError("post action requires endpoint")
        if self.actionType == "navigate" and not self.path:
            raise ValueError("navigate action requires path")
        return self


class AppObjectRendererModes(BaseModel):
    read: str | None = None
    edit: str | None = None

    @model_validator(mode="after")
    def at_least_one_mode(self) -> "AppObjectRendererModes":
        if not self.read and not self.edit:
            raise ValueError("At least one mode (read or edit) must be specified")
        return self


class AppObjectRenderer(BaseModel):
    type: str = Field(min_length=1, description="RDF type IRI or prefixed name")
    modes: AppObjectRendererModes


class AppContributions(BaseModel):
    rightPane: list[AppRightPaneContribution] = []
    views: list[AppViewContribution] = []
    commandPalette: list[AppCommandPaletteEntry] = []


class AppUI(BaseModel):
    pages: list[AppPage] = []
    contributions: AppContributions = AppContributions()
    objectRenderers: list[AppObjectRenderer] = []


class AppSettingDef(BaseModel):
    key: str = Field(
        pattern=r"^[a-zA-Z][a-zA-Z0-9]*$", min_length=1, max_length=64
    )
    label: str = Field(min_length=1, max_length=200)
    description: str = ""
    inputType: str  # "text" | "password" | "toggle" | "select" | "number"
    options: list[str] | None = None
    default: Any = ""

    @model_validator(mode="after")
    def validate_options(self) -> "AppSettingDef":
        if self.inputType == "select" and not self.options:
            raise ValueError("select inputType requires options list")
        return self


# ── Root schema ──


class AppManifestSchema(BaseModel):
    """Root manifest schema for SemPKM applications."""

    # Identity
    appId: str = Field(
        pattern=r"^[a-z][a-z0-9-]*$",
        min_length=2,
        max_length=64,
    )
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    author: AppAuthor | None = None
    license: str = Field(default="", max_length=64)

    # Dependencies
    dependencies: AppDependencies = AppDependencies()

    # Permissions
    permissions: AppPermissions = AppPermissions()

    # Backend
    backend: AppBackend

    # Tasks
    tasks: list[AppTask] = []

    # Frontend
    frontend: AppFrontend = AppFrontend()

    # UI
    ui: AppUI = AppUI()

    # Settings
    settings: list[AppSettingDef] = []

    # ── Validators ──

    @model_validator(mode="after")
    def validate_task_references(self) -> "AppManifestSchema":
        """Ensure backgroundTasks permission is set if tasks are declared."""
        if self.tasks and not self.permissions.backgroundTasks:
            raise ValueError(
                "App declares tasks but permissions.backgroundTasks is false"
            )
        return self

    @model_validator(mode="after")
    def validate_settings_permission(self) -> "AppManifestSchema":
        """Ensure settings permission is set if settings are declared."""
        if self.settings and not self.permissions.settings:
            raise ValueError(
                "App declares settings but permissions.settings is false"
            )
        return self


def parse_app_manifest(manifest_path: str) -> AppManifestSchema:
    """Load and validate an app manifest from a YAML file.

    Args:
        manifest_path: Path to the manifest.yaml file.

    Returns:
        Validated AppManifestSchema instance.

    Raises:
        ValueError: If the file is missing or fails validation.
    """
    import yaml
    from pathlib import Path

    path = Path(manifest_path)
    if not path.exists():
        raise ValueError(f"Manifest not found: {manifest_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Manifest must be a YAML mapping")

    return AppManifestSchema(**data)
