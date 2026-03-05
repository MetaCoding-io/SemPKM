"""Canvas persistence service backed by user_settings entries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserSetting


class CanvasService:
    """Persist and load user-scoped canvas documents via user_settings."""

    @staticmethod
    def _doc_key(canvas_id: str) -> str:
        return f"canvas.{canvas_id}.document"

    @staticmethod
    def _meta_key(canvas_id: str) -> str:
        return f"canvas.{canvas_id}.meta"

    async def load_document(
        self,
        user_id: uuid.UUID,
        canvas_id: str,
        db: AsyncSession,
    ) -> tuple[dict, str | None]:
        """Load a canvas document and updated timestamp for a user."""
        doc_row = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == self._doc_key(canvas_id),
            )
        )
        doc_setting = doc_row.scalar_one_or_none()

        meta_row = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == self._meta_key(canvas_id),
            )
        )
        meta_setting = meta_row.scalar_one_or_none()

        document: dict = {
            "nodes": [],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
        updated_at: str | None = None

        if doc_setting and doc_setting.value:
            try:
                parsed = json.loads(doc_setting.value)
                if isinstance(parsed, dict):
                    document = parsed
            except Exception:
                pass

        if meta_setting and meta_setting.value:
            try:
                parsed_meta = json.loads(meta_setting.value)
                if isinstance(parsed_meta, dict):
                    updated_at = parsed_meta.get("updated_at")
            except Exception:
                pass

        return document, updated_at

    async def save_document(
        self,
        user_id: uuid.UUID,
        canvas_id: str,
        document: dict,
        db: AsyncSession,
    ) -> str:
        """Upsert canvas document + metadata and return updated_at ISO timestamp."""
        updated_at = datetime.now(tz=timezone.utc).isoformat()
        doc_value = json.dumps(document)
        meta_value = json.dumps({"updated_at": updated_at})

        await self._upsert_setting(db, user_id, self._doc_key(canvas_id), doc_value)
        await self._upsert_setting(db, user_id, self._meta_key(canvas_id), meta_value)
        await db.commit()
        return updated_at

    async def _upsert_setting(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        key: str,
        value: str,
    ) -> None:
        row = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == key,
            )
        )
        existing = row.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(UserSetting(user_id=user_id, key=key, value=value))
