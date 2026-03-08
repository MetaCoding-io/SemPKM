"""Canvas persistence service backed by user_settings entries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import uuid

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserSetting

_SESSIONS_INDEX_KEY = "canvas.sessions.index"
_ACTIVE_SESSION_KEY = "canvas.active_session"


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

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def list_sessions(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> list[dict]:
        """Return the list of saved canvas sessions for this user."""
        row = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == _SESSIONS_INDEX_KEY,
            )
        )
        setting = row.scalar_one_or_none()
        if not setting or not setting.value:
            return []
        try:
            parsed = json.loads(setting.value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    async def save_session_as(
        self,
        user_id: uuid.UUID,
        name: str,
        document: dict,
        db: AsyncSession,
    ) -> str:
        """Create a new named session, persist its document, and return the session id."""
        session_id = str(uuid.uuid4())[:8]
        updated_at = datetime.now(tz=timezone.utc).isoformat()

        # Persist document + meta without intermediate commit
        doc_value = json.dumps(document)
        meta_value = json.dumps({"updated_at": updated_at})
        await self._upsert_setting(db, user_id, self._doc_key(session_id), doc_value)
        await self._upsert_setting(db, user_id, self._meta_key(session_id), meta_value)

        # Update sessions index
        sessions = await self.list_sessions(user_id, db)
        sessions.append({"id": session_id, "name": name, "updated_at": updated_at})
        await self._upsert_setting(db, user_id, _SESSIONS_INDEX_KEY, json.dumps(sessions))

        # Set as active session
        await self._upsert_setting(db, user_id, _ACTIVE_SESSION_KEY, session_id)

        await db.commit()
        return session_id

    async def get_active_session_id(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> str | None:
        """Return the id of the user's active canvas session, or None."""
        row = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == _ACTIVE_SESSION_KEY,
            )
        )
        setting = row.scalar_one_or_none()
        return setting.value if setting and setting.value else None

    async def set_active_session(
        self, user_id: uuid.UUID, session_id: str, db: AsyncSession
    ) -> None:
        """Set the active canvas session for the user."""
        await self._upsert_setting(db, user_id, _ACTIVE_SESSION_KEY, session_id)
        await db.commit()

    async def delete_session(
        self, user_id: uuid.UUID, session_id: str, db: AsyncSession
    ) -> bool:
        """Delete a named session and its data. Returns False if not found."""
        sessions = await self.list_sessions(user_id, db)
        found = [s for s in sessions if s.get("id") == session_id]
        if not found:
            return False

        # Remove from index
        sessions = [s for s in sessions if s.get("id") != session_id]
        await self._upsert_setting(db, user_id, _SESSIONS_INDEX_KEY, json.dumps(sessions))

        # Delete document and meta rows
        for key in (self._doc_key(session_id), self._meta_key(session_id)):
            await db.execute(
                sa_delete(UserSetting).where(
                    UserSetting.user_id == user_id,
                    UserSetting.key == key,
                )
            )

        # If active session was deleted, switch to another or clear
        active = await self.get_active_session_id(user_id, db)
        if active == session_id:
            new_active = sessions[0]["id"] if sessions else ""
            await self._upsert_setting(db, user_id, _ACTIVE_SESSION_KEY, new_active)

        await db.commit()
        return True

    async def migrate_default_canvas(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> str | None:
        """One-time migration: move 'default' canvas to a named session."""
        # Already migrated?
        sessions = await self.list_sessions(user_id, db)
        if sessions:
            return None

        # Check for existing default canvas
        row = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == self._doc_key("default"),
            )
        )
        doc_setting = row.scalar_one_or_none()
        if not doc_setting or not doc_setting.value:
            return None

        try:
            document = json.loads(doc_setting.value)
            if not isinstance(document, dict):
                return None
            # Only migrate if there's actual content
            nodes = document.get("nodes", [])
            if not nodes:
                return None
        except Exception:
            return None

        return await self.save_session_as(user_id, "My Canvas", document, db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
