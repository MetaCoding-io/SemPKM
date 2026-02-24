"""Settings service for layered resolution of application settings.

Implements a three-layer resolution order:
  1. System defaults (defined in code)
  2. Model manifest defaults (contributed by installed Mental Models)
  3. User DB overrides (stored in user_settings table)
"""

from dataclasses import dataclass, field
from typing import Any
import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import UserSetting


@dataclass
class SettingDefinition:
    """Definition of a single setting with metadata and default value."""

    key: str           # e.g. "core.theme", "basic-pkm.defaultNoteType"
    label: str
    description: str = ""
    input_type: str = "text"   # "toggle" | "select" | "text" | "color"
    options: list[str] | None = None
    default: str = ""
    category: str = "General"
    model_id: str | None = None  # None for core settings


class SettingsService:
    """Service for resolving layered settings: system < model manifest < user DB."""

    # System defaults (only core.theme in Phase 15)
    SYSTEM_SETTINGS: dict[str, SettingDefinition] = {
        "core.theme": SettingDefinition(
            key="core.theme",
            label="Theme",
            description="Color theme for the workspace",
            input_type="select",
            options=["light", "dark", "system"],
            default="system",
            category="General",
            model_id=None,
        )
    }

    def __init__(self, installed_models_dir: str | None = None):
        """Initialize with optional models directory for manifest scanning.

        Args:
            installed_models_dir: Path to models/ directory. When provided,
                manifests are scanned for contributed settings definitions.
        """
        self._models_dir = installed_models_dir

    async def get_all_settings(self) -> list[SettingDefinition]:
        """Return system settings plus model-contributed settings from all installed manifests."""
        settings = list(self.SYSTEM_SETTINGS.values())

        if self._models_dir:
            import os
            import yaml
            from ..models.manifest import ManifestSchema

            try:
                model_ids = os.listdir(self._models_dir)
            except OSError:
                model_ids = []

            for model_id in model_ids:
                manifest_path = os.path.join(self._models_dir, model_id, "manifest.yaml")
                if not os.path.exists(manifest_path):
                    continue
                try:
                    with open(manifest_path) as f:
                        raw = yaml.safe_load(f)
                    manifest = ManifestSchema.model_validate(raw)
                    for s in (manifest.settings or []):
                        full_key = f"{model_id}.{s.key}"
                        settings.append(SettingDefinition(
                            key=full_key,
                            label=s.label,
                            description=s.description,
                            input_type=s.input_type,
                            options=s.options,
                            default=s.default,
                            category=model_id,
                            model_id=model_id,
                        ))
                except Exception:
                    continue

        return settings

    async def get_user_overrides(self, user_id: uuid.UUID, db: AsyncSession) -> dict[str, str]:
        """Return all user_settings rows for this user as {key: value}."""
        result = await db.execute(
            select(UserSetting).where(UserSetting.user_id == user_id)
        )
        return {row.key: row.value for row in result.scalars()}

    async def resolve(self, user_id: uuid.UUID, db: AsyncSession) -> dict[str, str]:
        """Return fully merged settings: system defaults + model defaults + user overrides."""
        all_defs = await self.get_all_settings()
        resolved = {d.key: d.default for d in all_defs}
        overrides = await self.get_user_overrides(user_id, db)
        resolved.update(overrides)
        return resolved

    async def set_override(
        self, user_id: uuid.UUID, key: str, value: str, db: AsyncSession
    ) -> None:
        """Upsert a user_settings row."""
        existing = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id, UserSetting.key == key
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(UserSetting(user_id=user_id, key=key, value=value))
        await db.commit()

    async def reset_override(
        self, user_id: uuid.UUID, key: str, db: AsyncSession
    ) -> None:
        """Delete a user override (reverts to system/manifest default)."""
        await db.execute(
            delete(UserSetting).where(
                UserSetting.user_id == user_id, UserSetting.key == key
            )
        )
        await db.commit()

    async def remove_model_overrides(
        self, user_id: uuid.UUID, model_id: str, db: AsyncSession
    ) -> None:
        """Remove all user overrides for keys contributed by a given model."""
        await db.execute(
            delete(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key.like(f"{model_id}.%"),
            )
        )
        await db.commit()
