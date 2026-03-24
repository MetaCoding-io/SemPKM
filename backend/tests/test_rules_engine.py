"""Tests for RulesEngine — evaluation logic and CRUD operations.

Uses the same in-memory SQLite pattern as test_context_service.py.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User  # noqa: F401 — registers 'users' table in metadata
from app.context.rules_models import ContextRule
from app.context.rules_engine import RulesEngine
from app.db.base import Base


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def other_user_id():
    return uuid.uuid4()


@pytest.fixture
def rules_engine(session_factory):
    return RulesEngine(session_factory)


PERSONA_A = str(uuid.uuid4())
PERSONA_B = str(uuid.uuid4())
PERSONA_C = str(uuid.uuid4())


# ── Evaluate Tests ───────────────────────────────────────────────


class TestRulesEngineEvaluate:
    """Rule evaluation: priority ordering, AND conditions, edge cases."""

    @pytest.mark.asyncio
    async def test_single_rule_match(self, rules_engine, user_id):
        """Single matching rule returns its persona_id."""
        await rules_engine.create_rule(
            user_id, "Office", {"location_zone": "office"}, PERSONA_A
        )
        result = await rules_engine.evaluate(user_id, {"location_zone": "office"})
        assert result == PERSONA_A

    @pytest.mark.asyncio
    async def test_priority_ordering(self, rules_engine, user_id):
        """Higher priority rule wins over lower when both match."""
        await rules_engine.create_rule(
            user_id, "Low", {"location_zone": "office"}, PERSONA_A, priority=1
        )
        await rules_engine.create_rule(
            user_id, "High", {"location_zone": "office"}, PERSONA_B, priority=10
        )
        result = await rules_engine.evaluate(user_id, {"location_zone": "office"})
        assert result == PERSONA_B

    @pytest.mark.asyncio
    async def test_and_conditions_all_must_match(self, rules_engine, user_id):
        """Rule with multiple conditions only matches when ALL are satisfied."""
        await rules_engine.create_rule(
            user_id,
            "Office Work",
            {"location_zone": "office", "time_period": "work_hours"},
            PERSONA_A,
        )
        # Only one condition matches — should not fire.
        result = await rules_engine.evaluate(
            user_id, {"location_zone": "office", "time_period": "evening"}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_and_conditions_full_match(self, rules_engine, user_id):
        """Rule with multiple conditions matches when all are present and equal."""
        await rules_engine.create_rule(
            user_id,
            "Office Work",
            {"location_zone": "office", "time_period": "work_hours"},
            PERSONA_A,
        )
        result = await rules_engine.evaluate(
            user_id, {"location_zone": "office", "time_period": "work_hours"}
        )
        assert result == PERSONA_A

    @pytest.mark.asyncio
    async def test_partial_context_no_match(self, rules_engine, user_id):
        """Context with fewer fields than conditions → no match."""
        await rules_engine.create_rule(
            user_id,
            "Office Work",
            {"location_zone": "office", "time_period": "work_hours"},
            PERSONA_A,
        )
        # Context only has location_zone, not time_period.
        result = await rules_engine.evaluate(user_id, {"location_zone": "office"})
        assert result is None

    @pytest.mark.asyncio
    async def test_disabled_rules_skipped(self, rules_engine, user_id):
        """Disabled rules are not evaluated."""
        await rules_engine.create_rule(
            user_id,
            "Office",
            {"location_zone": "office"},
            PERSONA_A,
            enabled=False,
        )
        result = await rules_engine.evaluate(user_id, {"location_zone": "office"})
        assert result is None

    @pytest.mark.asyncio
    async def test_no_rules_returns_none(self, rules_engine, user_id):
        """No rules at all → None."""
        result = await rules_engine.evaluate(user_id, {"location_zone": "office"})
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_conditions_always_matches(self, rules_engine, user_id):
        """Rule with empty conditions dict matches any context."""
        await rules_engine.create_rule(
            user_id, "Catch-all", {}, PERSONA_C
        )
        result = await rules_engine.evaluate(user_id, {"location_zone": "anywhere"})
        assert result == PERSONA_C

    @pytest.mark.asyncio
    async def test_null_condition_value_ignored(self, rules_engine, user_id):
        """Condition entries with None value act as wildcards."""
        await rules_engine.create_rule(
            user_id,
            "Wildcard time",
            {"location_zone": "office", "time_period": None},
            PERSONA_A,
        )
        result = await rules_engine.evaluate(
            user_id, {"location_zone": "office", "time_period": "evening"}
        )
        assert result == PERSONA_A

    @pytest.mark.asyncio
    async def test_first_matching_rule_wins(self, rules_engine, user_id):
        """With same priority, earlier-created rule wins (created_at ASC)."""
        await rules_engine.create_rule(
            user_id, "First", {"location_zone": "office"}, PERSONA_A, priority=5
        )
        await rules_engine.create_rule(
            user_id, "Second", {"location_zone": "office"}, PERSONA_B, priority=5
        )
        result = await rules_engine.evaluate(user_id, {"location_zone": "office"})
        assert result == PERSONA_A


# ── CRUD Tests ───────────────────────────────────────────────────


class TestRulesEngineCRUD:
    """Create, list, get, update, delete operations."""

    @pytest.mark.asyncio
    async def test_create_and_get(self, rules_engine, user_id):
        rule = await rules_engine.create_rule(
            user_id, "Test Rule", {"location_zone": "home"}, PERSONA_A, priority=3
        )
        assert rule.name == "Test Rule"
        assert rule.conditions == {"location_zone": "home"}
        assert rule.persona_id == PERSONA_A
        assert rule.priority == 3
        assert rule.enabled is True

        fetched = await rules_engine.get_rule(rule.id, user_id)
        assert fetched is not None
        assert fetched.id == rule.id

    @pytest.mark.asyncio
    async def test_list_ordered_by_priority(self, rules_engine, user_id):
        await rules_engine.create_rule(user_id, "Low", {}, PERSONA_A, priority=1)
        await rules_engine.create_rule(user_id, "High", {}, PERSONA_B, priority=10)
        await rules_engine.create_rule(user_id, "Mid", {}, PERSONA_C, priority=5)

        rules = await rules_engine.list_rules(user_id)
        assert len(rules) == 3
        assert rules[0].name == "High"
        assert rules[1].name == "Mid"
        assert rules[2].name == "Low"

    @pytest.mark.asyncio
    async def test_update_rule(self, rules_engine, user_id):
        rule = await rules_engine.create_rule(
            user_id, "Original", {"location_zone": "home"}, PERSONA_A
        )
        updated = await rules_engine.update_rule(
            rule.id, user_id, name="Updated", priority=99
        )
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.priority == 99
        # Unchanged fields preserved
        assert updated.conditions == {"location_zone": "home"}

    @pytest.mark.asyncio
    async def test_delete_rule(self, rules_engine, user_id):
        rule = await rules_engine.create_rule(
            user_id, "Deleteme", {}, PERSONA_A
        )
        result = await rules_engine.delete_rule(rule.id, user_id)
        assert result is True

        fetched = await rules_engine.get_rule(rule.id, user_id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, rules_engine, user_id):
        result = await rules_engine.delete_rule(uuid.uuid4(), user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, rules_engine, user_id):
        result = await rules_engine.get_rule(uuid.uuid4(), user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_wrong_user_get_returns_none(self, rules_engine, user_id, other_user_id):
        """Cannot read another user's rule."""
        rule = await rules_engine.create_rule(
            user_id, "Private", {}, PERSONA_A
        )
        result = await rules_engine.get_rule(rule.id, other_user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_wrong_user_update_returns_none(self, rules_engine, user_id, other_user_id):
        """Cannot update another user's rule."""
        rule = await rules_engine.create_rule(
            user_id, "Private", {}, PERSONA_A
        )
        result = await rules_engine.update_rule(rule.id, other_user_id, name="Hacked")
        assert result is None

    @pytest.mark.asyncio
    async def test_wrong_user_delete_returns_false(self, rules_engine, user_id, other_user_id):
        """Cannot delete another user's rule."""
        rule = await rules_engine.create_rule(
            user_id, "Private", {}, PERSONA_A
        )
        result = await rules_engine.delete_rule(rule.id, other_user_id)
        assert result is False

        # Still exists for the original user.
        fetched = await rules_engine.get_rule(rule.id, user_id)
        assert fetched is not None
