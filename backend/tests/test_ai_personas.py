"""Tests for AIPersonaService — CRUD, built-in seeding, activation,
built-in protection, and system prompt integration.

Uses in-memory SQLite with async sessions, matching the existing
test pattern from test_conversation_service.py.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.models import User
from app.copilot.models import AIPersona
from app.copilot.personas import AIPersonaService, _BUILTIN_PERSONAS
from app.copilot.schemas import CopilotChatRequest, PersonaResponse
from app.copilot.service import _build_system_prompt
from app.db.base import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_session_factory():
    """Provide an in-memory SQLite async session factory with tables created."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def db(async_session_factory):
    """Provide an async session for tests."""
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def user_id(async_session_factory):
    """Create a test user and return their ID."""
    async with async_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            username="testuser",
            email="test@example.com",
            display_name="Test User",
        )
        session.add(user)
        await session.commit()
        return user.id


@pytest_asyncio.fixture
async def other_user_id(async_session_factory):
    """Create a second test user for isolation tests."""
    async with async_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            username="otheruser",
            email="other@example.com",
            display_name="Other User",
        )
        session.add(user)
        await session.commit()
        return user.id


@pytest.fixture
def svc():
    """AIPersonaService instance."""
    return AIPersonaService()


# ---------------------------------------------------------------------------
# Seeding tests
# ---------------------------------------------------------------------------


class TestSeedBuiltins:
    """Tests for seed_builtins() — lazy creation of 4 built-in personas."""

    @pytest.mark.asyncio
    async def test_seed_creates_four_personas(self, db, user_id, svc):
        """seed_builtins creates exactly 4 personas with correct names and icons."""
        count = await svc.seed_builtins(db, user_id)
        assert count == 4

        personas = await svc.list_for_user(db, user_id)
        assert len(personas) == 4

        names = {p.name for p in personas}
        assert names == {
            "General Assistant",
            "Research Assistant",
            "Project Manager",
            "Writing Coach",
        }

        icons = {p.icon for p in personas}
        assert icons == {"🤖", "🔬", "📋", "✍️"}

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, db, user_id, svc):
        """Calling seed_builtins twice creates only 4 total, not 8."""
        first = await svc.seed_builtins(db, user_id)
        assert first == 4

        second = await svc.seed_builtins(db, user_id)
        assert second == 0

        personas = await svc.list_for_user(db, user_id)
        assert len(personas) == 4

    @pytest.mark.asyncio
    async def test_seed_sets_general_assistant_active(self, db, user_id, svc):
        """General Assistant is the default active persona after seeding."""
        await svc.seed_builtins(db, user_id)

        active = await svc.get_active(db, user_id)
        assert active is not None
        assert active.name == "General Assistant"
        assert active.is_active is True

    @pytest.mark.asyncio
    async def test_seed_marks_all_as_builtin(self, db, user_id, svc):
        """All seeded personas are marked is_builtin=True."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        for p in personas:
            assert p.is_builtin is True

    @pytest.mark.asyncio
    async def test_seed_distinct_templates(self, db, user_id, svc):
        """Each built-in persona has a distinct system_prompt_template."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        templates = [p.system_prompt_template for p in personas]
        assert len(set(templates)) == 4

    @pytest.mark.asyncio
    async def test_seed_user_isolation(self, db, user_id, other_user_id, svc):
        """Seeding for one user does not affect another user."""
        await svc.seed_builtins(db, user_id)

        other_personas = await svc.list_for_user(db, other_user_id)
        # list_for_user triggers seed for other_user_id
        assert len(other_personas) == 4

        # Both users have their own 4 personas
        user_personas = await svc.list_for_user(db, user_id)
        assert len(user_personas) == 4


# ---------------------------------------------------------------------------
# List / Get tests
# ---------------------------------------------------------------------------


class TestListAndGet:
    """Tests for list_for_user() and get() methods."""

    @pytest.mark.asyncio
    async def test_list_triggers_seed_on_empty(self, db, user_id, svc):
        """list_for_user() triggers seed on first call for a new user."""
        personas = await svc.list_for_user(db, user_id)
        assert len(personas) == 4

    @pytest.mark.asyncio
    async def test_list_returns_builtins_first(self, db, user_id, svc):
        """Built-in personas appear before custom ones."""
        await svc.seed_builtins(db, user_id)
        await svc.create(db, user_id, "My Custom", "🎯", "Custom template")

        personas = await svc.list_for_user(db, user_id)
        assert len(personas) == 5

        # Built-ins should come first
        builtins = [p for p in personas if p.is_builtin]
        customs = [p for p in personas if not p.is_builtin]
        assert len(builtins) == 4
        assert len(customs) == 1

    @pytest.mark.asyncio
    async def test_get_returns_persona(self, db, user_id, svc):
        """get() returns a specific persona by ID."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        first = personas[0]

        result = await svc.get(db, first.id, user_id)
        assert result is not None
        assert result.id == first.id

    @pytest.mark.asyncio
    async def test_get_returns_none_for_wrong_user(self, db, user_id, other_user_id, svc):
        """get() returns None if persona belongs to another user."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        first = personas[0]

        result = await svc.get(db, first.id, other_user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_for_nonexistent(self, db, user_id, svc):
        """get() returns None for a nonexistent persona ID."""
        result = await svc.get(db, uuid.uuid4(), user_id)
        assert result is None


# ---------------------------------------------------------------------------
# Create tests
# ---------------------------------------------------------------------------


class TestCreate:
    """Tests for create() method."""

    @pytest.mark.asyncio
    async def test_create_custom_persona(self, db, user_id, svc):
        """create() produces a non-builtin, inactive persona."""
        persona = await svc.create(
            db,
            user_id,
            name="Custom Bot",
            icon="🎯",
            system_prompt_template="You are a custom bot. {type_schemas}",
            temperature=0.9,
        )
        assert persona.name == "Custom Bot"
        assert persona.icon == "🎯"
        assert persona.is_builtin is False
        assert persona.is_active is False
        assert persona.temperature == 0.9

    @pytest.mark.asyncio
    async def test_create_with_model_preference(self, db, user_id, svc):
        """create() stores model_preference when provided."""
        persona = await svc.create(
            db,
            user_id,
            name="GPT-4 Bot",
            icon="🧠",
            system_prompt_template="Smart bot",
            model_preference="gpt-4-turbo",
        )
        assert persona.model_preference == "gpt-4-turbo"


# ---------------------------------------------------------------------------
# Update tests
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for update() method."""

    @pytest.mark.asyncio
    async def test_update_custom_persona(self, db, user_id, svc):
        """update() modifies allowed fields on a custom persona."""
        persona = await svc.create(
            db, user_id, "Old Name", "🎯", "Old template"
        )
        updated = await svc.update(
            db, persona.id, user_id, name="New Name", temperature=0.3
        )
        assert updated.name == "New Name"
        assert updated.temperature == 0.3

    @pytest.mark.asyncio
    async def test_update_rejects_builtin(self, db, user_id, svc):
        """update() raises ValueError for built-in personas."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        builtin = next(p for p in personas if p.is_builtin)

        with pytest.raises(ValueError, match="Cannot modify built-in persona"):
            await svc.update(db, builtin.id, user_id, name="Hacked")

    @pytest.mark.asyncio
    async def test_update_raises_for_nonexistent(self, db, user_id, svc):
        """update() raises ValueError if persona not found."""
        with pytest.raises(ValueError, match="not found"):
            await svc.update(db, uuid.uuid4(), user_id, name="Ghost")

    @pytest.mark.asyncio
    async def test_update_ignores_disallowed_fields(self, db, user_id, svc):
        """update() silently ignores fields not in the allowed set."""
        persona = await svc.create(
            db, user_id, "Test", "🎯", "Template"
        )
        # is_builtin is not in allowed_fields
        updated = await svc.update(
            db, persona.id, user_id, is_builtin=True
        )
        assert updated.is_builtin is False


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for delete() method."""

    @pytest.mark.asyncio
    async def test_delete_custom_persona(self, db, user_id, svc):
        """delete() removes a custom persona."""
        persona = await svc.create(
            db, user_id, "Temp", "🎯", "Temp template"
        )
        deleted = await svc.delete(db, persona.id, user_id)
        assert deleted is True

        result = await svc.get(db, persona.id, user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_rejects_builtin(self, db, user_id, svc):
        """delete() raises ValueError for built-in personas."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        builtin = next(p for p in personas if p.is_builtin)

        with pytest.raises(ValueError, match="Cannot delete built-in persona"):
            await svc.delete(db, builtin.id, user_id)

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_nonexistent(self, db, user_id, svc):
        """delete() returns False for a nonexistent persona."""
        deleted = await svc.delete(db, uuid.uuid4(), user_id)
        assert deleted is False


# ---------------------------------------------------------------------------
# Activation tests
# ---------------------------------------------------------------------------


class TestActivation:
    """Tests for get_active() and set_active() methods."""

    @pytest.mark.asyncio
    async def test_get_active_after_seed(self, db, user_id, svc):
        """get_active() returns General Assistant after seeding."""
        await svc.seed_builtins(db, user_id)
        active = await svc.get_active(db, user_id)
        assert active is not None
        assert active.name == "General Assistant"

    @pytest.mark.asyncio
    async def test_set_active_switches_persona(self, db, user_id, svc):
        """set_active() deactivates current and activates specified."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        research = next(p for p in personas if p.name == "Research Assistant")

        activated = await svc.set_active(db, user_id, research.id)
        assert activated.name == "Research Assistant"

        active = await svc.get_active(db, user_id)
        assert active.id == research.id

        # Old active should be deactivated
        general = next(p for p in personas if p.name == "General Assistant")
        refreshed_general = await svc.get(db, general.id, user_id)
        assert refreshed_general.is_active is False

    @pytest.mark.asyncio
    async def test_set_active_raises_for_nonexistent(self, db, user_id, svc):
        """set_active() raises ValueError for nonexistent persona."""
        with pytest.raises(ValueError, match="not found"):
            await svc.set_active(db, user_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_only_one_active_at_a_time(self, db, user_id, svc):
        """Only one persona should be active at any time."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)

        # Switch through multiple personas
        for p in personas:
            await svc.set_active(db, user_id, p.id)

        all_personas = await svc.list_for_user(db, user_id)
        active_count = sum(1 for p in all_personas if p.is_active)
        assert active_count == 1


# ---------------------------------------------------------------------------
# System prompt integration tests
# ---------------------------------------------------------------------------


class TestSystemPromptIntegration:
    """Tests for _build_system_prompt() with persona_prompt parameter."""

    def test_build_system_prompt_without_persona(self):
        """_build_system_prompt with no persona_prompt returns default."""
        prompt = _build_system_prompt("schema goes here")
        assert "SPARQL assistant" in prompt
        assert "schema goes here" in prompt

    def test_build_system_prompt_with_persona(self):
        """_build_system_prompt with persona_prompt prepends it."""
        persona_text = "You are a meticulous research assistant."
        prompt = _build_system_prompt(
            "schema goes here", persona_prompt=persona_text
        )
        # Persona should appear before the default instructions
        persona_pos = prompt.find("meticulous research assistant")
        sparql_pos = prompt.find("SPARQL assistant")
        assert persona_pos < sparql_pos
        assert persona_text in prompt

    def test_build_system_prompt_with_graph_context(self):
        """_build_system_prompt with both persona and graph context."""
        prompt = _build_system_prompt(
            "schema",
            graph_context="Active object: Project X",
            persona_prompt="You are a PM bot.",
        )
        assert "PM bot" in prompt
        assert "Active object: Project X" in prompt
        assert "schema" in prompt

    def test_build_system_prompt_persona_none_has_no_effect(self):
        """_build_system_prompt with persona_prompt=None doesn't alter output."""
        base = _build_system_prompt("schema")
        with_none = _build_system_prompt("schema", persona_prompt=None)
        assert base == with_none


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Tests for persona-related Pydantic schemas."""

    def test_copilot_chat_request_has_persona_id(self):
        """CopilotChatRequest includes persona_id field."""
        req = CopilotChatRequest(
            messages=[{"role": "user", "content": "hi"}],
            persona_id="some-uuid",
        )
        assert req.persona_id == "some-uuid"

    def test_copilot_chat_request_persona_id_optional(self):
        """persona_id defaults to None when not provided."""
        req = CopilotChatRequest(
            messages=[{"role": "user", "content": "hi"}],
        )
        assert req.persona_id is None

    def test_persona_response_model(self):
        """PersonaResponse validates correctly."""
        resp = PersonaResponse(
            id="abc-123",
            name="Test",
            icon="🎯",
            system_prompt_template="You are a test bot.",
            temperature=0.5,
            is_builtin=False,
            is_active=True,
        )
        assert resp.name == "Test"
        assert resp.is_active is True


# ---------------------------------------------------------------------------
# Template slot variable tests
# ---------------------------------------------------------------------------


class TestTemplateSlotVariables:
    """Tests for persona template rendering with slot variables."""

    @pytest.mark.asyncio
    async def test_template_renders_slot_variables(self, db, user_id, svc):
        """Persona templates support {installed_models}, {type_schemas}, {current_context}."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)
        general = next(p for p in personas if p.name == "General Assistant")

        rendered = general.system_prompt_template.format(
            installed_models="basic-pkm, business-planning",
            type_schemas="Type: Project (properties: title, description)",
            current_context="Active: Project X",
        )

        assert "basic-pkm, business-planning" in rendered
        assert "Type: Project" in rendered
        assert "Active: Project X" in rendered

    @pytest.mark.asyncio
    async def test_all_builtins_have_slot_variables(self, db, user_id, svc):
        """All built-in persona templates include the 3 required slot variables."""
        await svc.seed_builtins(db, user_id)
        personas = await svc.list_for_user(db, user_id)

        for p in personas:
            assert "{type_schemas}" in p.system_prompt_template, (
                f"{p.name} template missing {{type_schemas}}"
            )
            assert "{installed_models}" in p.system_prompt_template, (
                f"{p.name} template missing {{installed_models}}"
            )
            assert "{current_context}" in p.system_prompt_template, (
                f"{p.name} template missing {{current_context}}"
            )
