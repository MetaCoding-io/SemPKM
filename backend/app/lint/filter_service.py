"""LintFilterService — CRUD for lint suppressions, dismissals, and presets.

Provides async methods for creating, listing, deleting, and managing
lint filter state stored in SQLite. Follows the PersonaService pattern
with session_factory injection and dataclass read models.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.lint.filter_models import LintDismissal, LintPreset, LintSuppression

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Read models (dataclasses)
# ---------------------------------------------------------------------------


@dataclass
class SuppressionData:
    """Lightweight read model for a lint suppression."""

    id: str
    user_id: str
    rule_source_iri: str
    created_at: str


@dataclass
class DismissalData:
    """Lightweight read model for a lint dismissal."""

    id: str
    user_id: str
    object_iri: str
    rule_source_iri: str
    created_at: str


@dataclass
class PresetData:
    """Lightweight read model for a lint preset."""

    id: str
    user_id: str
    name: str
    suppressed_rules: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class LintFilterService:
    """Service for lint filter CRUD operations."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    # ── Suppressions ──────────────────────────────────────────────────────

    async def add_suppression(
        self, user_id: uuid.UUID, rule_source_iri: str
    ) -> SuppressionData:
        """Add a rule suppression. Returns existing if duplicate."""
        if not rule_source_iri or not rule_source_iri.strip():
            raise ValueError("rule_source_iri must not be empty")

        suppression = LintSuppression(
            id=uuid.uuid4(),
            user_id=user_id,
            rule_source_iri=rule_source_iri,
        )
        async with self._session_factory() as session:
            try:
                session.add(suppression)
                await session.commit()
                await session.refresh(suppression)
                logger.info(
                    "Suppression added: rule=%s (user=%s)",
                    rule_source_iri,
                    user_id,
                )
                return self._suppression_to_data(suppression)
            except IntegrityError:
                await session.rollback()
                # Return existing suppression
                result = await session.execute(
                    select(LintSuppression).where(
                        LintSuppression.user_id == user_id,
                        LintSuppression.rule_source_iri == rule_source_iri,
                    )
                )
                existing = result.scalar_one()
                return self._suppression_to_data(existing)

    async def list_suppressions(
        self, user_id: uuid.UUID
    ) -> list[SuppressionData]:
        """List all suppressions for a user, ordered by creation time."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintSuppression)
                .where(LintSuppression.user_id == user_id)
                .order_by(LintSuppression.created_at)
            )
            return [self._suppression_to_data(s) for s in result.scalars().all()]

    async def delete_suppression(
        self, suppression_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a suppression by ID. Returns True if deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintSuppression).where(
                    LintSuppression.id == suppression_id,
                    LintSuppression.user_id == user_id,
                )
            )
            suppression = result.scalar_one_or_none()
            if not suppression:
                return False
            await session.delete(suppression)
            await session.commit()
            logger.info(
                "Suppression deleted: id=%s (user=%s)", suppression_id, user_id
            )
            return True

    async def clear_suppressions(self, user_id: uuid.UUID) -> int:
        """Delete all suppressions for a user. Returns count deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(LintSuppression).where(
                    LintSuppression.user_id == user_id
                )
            )
            await session.commit()
            count = result.rowcount
            logger.info(
                "Suppressions cleared: count=%d (user=%s)", count, user_id
            )
            return count

    # ── Dismissals ────────────────────────────────────────────────────────

    async def add_dismissal(
        self, user_id: uuid.UUID, object_iri: str, rule_source_iri: str
    ) -> DismissalData:
        """Add a result dismissal. Returns existing if duplicate."""
        if not object_iri or not object_iri.strip():
            raise ValueError("object_iri must not be empty")
        if not rule_source_iri or not rule_source_iri.strip():
            raise ValueError("rule_source_iri must not be empty")

        dismissal = LintDismissal(
            id=uuid.uuid4(),
            user_id=user_id,
            object_iri=object_iri,
            rule_source_iri=rule_source_iri,
        )
        async with self._session_factory() as session:
            try:
                session.add(dismissal)
                await session.commit()
                await session.refresh(dismissal)
                logger.info(
                    "Dismissal added: object=%s rule=%s (user=%s)",
                    object_iri,
                    rule_source_iri,
                    user_id,
                )
                return self._dismissal_to_data(dismissal)
            except IntegrityError:
                await session.rollback()
                result = await session.execute(
                    select(LintDismissal).where(
                        LintDismissal.user_id == user_id,
                        LintDismissal.object_iri == object_iri,
                        LintDismissal.rule_source_iri == rule_source_iri,
                    )
                )
                existing = result.scalar_one()
                return self._dismissal_to_data(existing)

    async def list_dismissals(
        self, user_id: uuid.UUID
    ) -> list[DismissalData]:
        """List all dismissals for a user, ordered by creation time."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintDismissal)
                .where(LintDismissal.user_id == user_id)
                .order_by(LintDismissal.created_at)
            )
            return [self._dismissal_to_data(d) for d in result.scalars().all()]

    async def delete_dismissal(
        self, dismissal_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a dismissal by ID. Returns True if deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintDismissal).where(
                    LintDismissal.id == dismissal_id,
                    LintDismissal.user_id == user_id,
                )
            )
            dismissal = result.scalar_one_or_none()
            if not dismissal:
                return False
            await session.delete(dismissal)
            await session.commit()
            logger.info(
                "Dismissal deleted: id=%s (user=%s)", dismissal_id, user_id
            )
            return True

    async def clear_dismissals(self, user_id: uuid.UUID) -> int:
        """Delete all dismissals for a user. Returns count deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(LintDismissal).where(
                    LintDismissal.user_id == user_id
                )
            )
            await session.commit()
            count = result.rowcount
            logger.info(
                "Dismissals cleared: count=%d (user=%s)", count, user_id
            )
            return count

    # ── Presets ────────────────────────────────────────────────────────────

    async def create_preset(
        self, user_id: uuid.UUID, name: str, suppressed_rules: list[str]
    ) -> PresetData:
        """Create a named preset. Raises ValueError on duplicate name."""
        if not name or not name.strip():
            raise ValueError("preset name must not be empty")

        preset = LintPreset(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            suppressed_rules_json=json.dumps(suppressed_rules),
        )
        async with self._session_factory() as session:
            try:
                session.add(preset)
                await session.commit()
                await session.refresh(preset)
                logger.info(
                    "Preset created: name=%s rules=%d (user=%s)",
                    name,
                    len(suppressed_rules),
                    user_id,
                )
                return self._preset_to_data(preset)
            except IntegrityError:
                await session.rollback()
                raise ValueError(
                    f"Preset with name '{name}' already exists for this user"
                )

    async def list_presets(self, user_id: uuid.UUID) -> list[PresetData]:
        """List all presets for a user, ordered by name."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintPreset)
                .where(LintPreset.user_id == user_id)
                .order_by(LintPreset.name)
            )
            return [self._preset_to_data(p) for p in result.scalars().all()]

    async def update_preset(
        self,
        preset_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        suppressed_rules: list[str] | None = None,
    ) -> PresetData | None:
        """Update a preset's name and/or rules. Returns None if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintPreset).where(
                    LintPreset.id == preset_id,
                    LintPreset.user_id == user_id,
                )
            )
            preset = result.scalar_one_or_none()
            if not preset:
                return None

            if name is not None:
                preset.name = name
            if suppressed_rules is not None:
                preset.suppressed_rules_json = json.dumps(suppressed_rules)

            await session.commit()
            await session.refresh(preset)
            logger.info("Preset updated: id=%s (user=%s)", preset_id, user_id)
            return self._preset_to_data(preset)

    async def delete_preset(
        self, preset_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a preset by ID. Returns True if deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(LintPreset).where(
                    LintPreset.id == preset_id,
                    LintPreset.user_id == user_id,
                )
            )
            preset = result.scalar_one_or_none()
            if not preset:
                return False
            await session.delete(preset)
            await session.commit()
            logger.info("Preset deleted: id=%s (user=%s)", preset_id, user_id)
            return True

    async def apply_preset(
        self, preset_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Apply a preset: replace all user's suppressions with the preset's rules.

        Per D280 (additive suppression model), this clears existing suppressions
        and creates new ones from the preset's rule list.

        Returns True if applied, False if preset not found.
        """
        async with self._session_factory() as session:
            # Fetch the preset
            result = await session.execute(
                select(LintPreset).where(
                    LintPreset.id == preset_id,
                    LintPreset.user_id == user_id,
                )
            )
            preset = result.scalar_one_or_none()
            if not preset:
                return False

            rules = json.loads(preset.suppressed_rules_json)

            # Clear existing suppressions
            await session.execute(
                delete(LintSuppression).where(
                    LintSuppression.user_id == user_id
                )
            )

            # Create new suppressions from preset rules
            for rule_iri in rules:
                session.add(
                    LintSuppression(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        rule_source_iri=rule_iri,
                    )
                )

            await session.commit()
            logger.info(
                "Preset applied: name=%s rules=%d (user=%s)",
                preset.name,
                len(rules),
                user_id,
            )
            return True

    # ── Convenience ───────────────────────────────────────────────────────

    async def get_user_filters(
        self, user_id: uuid.UUID
    ) -> tuple[set[str], set[tuple[str, str]]]:
        """Get user's active filter state for passing to LintService.

        Returns:
            Tuple of (suppressed_rule_iris, dismissed_object_rule_pairs)
        """
        async with self._session_factory() as session:
            # Suppressed rule IRIs
            supp_result = await session.execute(
                select(LintSuppression.rule_source_iri).where(
                    LintSuppression.user_id == user_id
                )
            )
            suppressed = {row[0] for row in supp_result.all()}

            # Dismissed (object, rule) pairs
            dism_result = await session.execute(
                select(
                    LintDismissal.object_iri, LintDismissal.rule_source_iri
                ).where(LintDismissal.user_id == user_id)
            )
            dismissed = {(row[0], row[1]) for row in dism_result.all()}

            return suppressed, dismissed

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _suppression_to_data(s: LintSuppression) -> SuppressionData:
        return SuppressionData(
            id=str(s.id),
            user_id=str(s.user_id),
            rule_source_iri=s.rule_source_iri,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )

    @staticmethod
    def _dismissal_to_data(d: LintDismissal) -> DismissalData:
        return DismissalData(
            id=str(d.id),
            user_id=str(d.user_id),
            object_iri=d.object_iri,
            rule_source_iri=d.rule_source_iri,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )

    @staticmethod
    def _preset_to_data(p: LintPreset) -> PresetData:
        return PresetData(
            id=str(p.id),
            user_id=str(p.user_id),
            name=p.name,
            suppressed_rules=json.loads(p.suppressed_rules_json or "[]"),
            created_at=p.created_at.isoformat() if p.created_at else "",
            updated_at=p.updated_at.isoformat() if p.updated_at else "",
        )
