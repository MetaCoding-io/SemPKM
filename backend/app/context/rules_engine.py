"""RulesEngine — evaluate context-to-persona mapping rules.

Loads per-user enabled rules sorted by priority (desc), created_at (asc).
The first rule whose AND-conditions all match the supplied context wins.
Also provides CRUD operations for managing rules.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.rules_models import ContextRule

logger = logging.getLogger(__name__)

# Fields callers may update on a rule.
_UPDATABLE_FIELDS = frozenset({"name", "priority", "conditions", "persona_id", "enabled"})


class RulesEngine:
    """Context rule evaluator and manager."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    # ── Evaluation ───────────────────────────────────────────────

    async def evaluate(self, user_id: uuid.UUID, context_data: dict) -> str | None:
        """Return the persona_id of the first matching rule, or None.

        Rules are evaluated in priority-descending, created_at-ascending
        order. A rule matches when every non-null condition value equals
        the corresponding value in *context_data*. An empty conditions
        dict matches unconditionally.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextRule)
                .where(ContextRule.user_id == user_id, ContextRule.enabled.is_(True))
                .order_by(ContextRule.priority.desc(), ContextRule.created_at.asc())
            )
            rules = result.scalars().all()

        for rule in rules:
            conditions = rule.conditions or {}
            matched = True
            for key, expected in conditions.items():
                if expected is None:
                    # Null condition values are ignored (wildcard).
                    continue
                if context_data.get(key) != expected:
                    matched = False
                    break

            if matched:
                logger.info(
                    "context.rule_matched user_id=%s rule_name=%s persona_id=%s",
                    user_id,
                    rule.name,
                    rule.persona_id,
                )
                return rule.persona_id

        logger.info("context.no_rule_matched user_id=%s", user_id)
        return None

    # ── CRUD ─────────────────────────────────────────────────────

    async def create_rule(
        self,
        user_id: uuid.UUID,
        name: str,
        conditions: dict,
        persona_id: str,
        priority: int = 0,
        enabled: bool = True,
    ) -> ContextRule:
        """Create a new context rule for *user_id*."""
        rule = ContextRule(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            conditions=conditions,
            persona_id=persona_id,
            priority=priority,
            enabled=enabled,
        )
        async with self._session_factory() as session:
            session.add(rule)
            await session.commit()
            await session.refresh(rule)
            logger.info(
                "context.rule_created user_id=%s rule_id=%s name=%s",
                user_id,
                rule.id,
                name,
            )
            return rule

    async def list_rules(self, user_id: uuid.UUID) -> list[ContextRule]:
        """Return all rules for *user_id*, ordered by priority desc."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextRule)
                .where(ContextRule.user_id == user_id)
                .order_by(ContextRule.priority.desc(), ContextRule.created_at.asc())
            )
            return list(result.scalars().all())

    async def get_rule(
        self, rule_id: uuid.UUID, user_id: uuid.UUID
    ) -> ContextRule | None:
        """Return a single rule, or None if not found / wrong user."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextRule).where(
                    ContextRule.id == rule_id, ContextRule.user_id == user_id
                )
            )
            return result.scalar_one_or_none()

    async def update_rule(
        self, rule_id: uuid.UUID, user_id: uuid.UUID, **updates
    ) -> ContextRule | None:
        """Update a rule. Returns the updated rule, or None if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextRule).where(
                    ContextRule.id == rule_id, ContextRule.user_id == user_id
                )
            )
            rule = result.scalar_one_or_none()
            if rule is None:
                return None

            for key, value in updates.items():
                if key in _UPDATABLE_FIELDS:
                    setattr(rule, key, value)

            await session.commit()
            await session.refresh(rule)
            logger.info(
                "context.rule_updated user_id=%s rule_id=%s fields=%s",
                user_id,
                rule_id,
                list(updates.keys()),
            )
            return rule

    async def delete_rule(self, rule_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a rule. Returns True if deleted, False if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextRule).where(
                    ContextRule.id == rule_id, ContextRule.user_id == user_id
                )
            )
            rule = result.scalar_one_or_none()
            if rule is None:
                return False

            await session.delete(rule)
            await session.commit()
            logger.info(
                "context.rule_deleted user_id=%s rule_id=%s", user_id, rule_id
            )
            return True
