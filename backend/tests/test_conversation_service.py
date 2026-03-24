"""Tests for ConversationService CRUD operations.

Uses in-memory SQLite with async sessions, matching the existing
test pattern from test_dashboard.py.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.models import User
from app.copilot.conversation import ConversationService
from app.copilot.models import CopilotConversation, CopilotMessage
from app.db.base import Base


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
    """Provide a ConversationService instance."""
    return ConversationService()


class TestCreateConversation:
    """Test conversation creation."""

    @pytest.mark.asyncio
    async def test_create_with_default_title(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        assert conv.title == "New Chat"
        assert conv.user_id == user_id
        assert conv.id is not None

    @pytest.mark.asyncio
    async def test_create_with_custom_title(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id, title="My Project Chat")
        assert conv.title == "My Project Chat"

    @pytest.mark.asyncio
    async def test_create_with_none_title_defaults(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id, title=None)
        assert conv.title == "New Chat"


class TestListConversations:
    """Test conversation listing."""

    @pytest.mark.asyncio
    async def test_list_empty(self, svc, db, user_id):
        convs = await svc.list_conversations(db, user_id)
        assert convs == []

    @pytest.mark.asyncio
    async def test_list_returns_user_conversations(self, svc, db, user_id):
        await svc.create_conversation(db, user_id, title="First")
        await svc.create_conversation(db, user_id, title="Second")
        await db.commit()

        convs = await svc.list_conversations(db, user_id)
        assert len(convs) == 2
        titles = [c.title for c in convs]
        assert "First" in titles
        assert "Second" in titles

    @pytest.mark.asyncio
    async def test_list_isolates_users(self, svc, db, user_id, other_user_id):
        await svc.create_conversation(db, user_id, title="User1 Chat")
        await svc.create_conversation(db, other_user_id, title="User2 Chat")
        await db.commit()

        convs = await svc.list_conversations(db, user_id)
        assert len(convs) == 1
        assert convs[0].title == "User1 Chat"


class TestGetConversation:
    """Test conversation retrieval with messages."""

    @pytest.mark.asyncio
    async def test_get_returns_conversation_with_messages(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id, title="Test")
        await svc.add_message(db, conv.id, "user", "Hello")
        await svc.add_message(db, conv.id, "assistant", "Hi there!")
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        assert result["title"] == "Test"
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"
        assert result["messages"][1]["role"] == "assistant"
        assert result["messages"][1]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_get_raises_for_wrong_user(self, svc, db, user_id, other_user_id):
        conv = await svc.create_conversation(db, user_id, title="Private")
        await db.commit()

        with pytest.raises(ValueError, match="not found"):
            await svc.get_conversation(db, conv.id, other_user_id)

    @pytest.mark.asyncio
    async def test_get_raises_for_nonexistent(self, svc, db, user_id):
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await svc.get_conversation(db, fake_id, user_id)

    @pytest.mark.asyncio
    async def test_get_messages_ordered_by_creation(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        await svc.add_message(db, conv.id, "user", "First")
        await svc.add_message(db, conv.id, "assistant", "Second")
        await svc.add_message(db, conv.id, "user", "Third")
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        contents = [m["content"] for m in result["messages"]]
        assert contents == ["First", "Second", "Third"]


class TestDeleteConversation:
    """Test conversation deletion."""

    @pytest.mark.asyncio
    async def test_delete_existing(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id, title="ToDelete")
        await svc.add_message(db, conv.id, "user", "Bye")
        await db.commit()

        deleted = await svc.delete_conversation(db, conv.id, user_id)
        assert deleted is True

        # Verify it's gone
        convs = await svc.list_conversations(db, user_id)
        assert len(convs) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, svc, db, user_id):
        deleted = await svc.delete_conversation(db, uuid.uuid4(), user_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_wrong_user_returns_false(self, svc, db, user_id, other_user_id):
        conv = await svc.create_conversation(db, user_id, title="Private")
        await db.commit()

        deleted = await svc.delete_conversation(db, conv.id, other_user_id)
        assert deleted is False

        # Original user's conversation still exists
        convs = await svc.list_conversations(db, user_id)
        assert len(convs) == 1


class TestAddMessage:
    """Test message creation and auto-title."""

    @pytest.mark.asyncio
    async def test_add_message(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        msg = await svc.add_message(db, conv.id, "user", "Hello world")
        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.conversation_id == conv.id

    @pytest.mark.asyncio
    async def test_add_message_auto_titles_on_first_user_message(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        assert conv.title == "New Chat"

        await svc.add_message(db, conv.id, "user", "Tell me about my projects")
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        assert result["title"] == "Tell me about my projects"

    @pytest.mark.asyncio
    async def test_auto_title_truncates_at_50_chars(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        long_msg = "A" * 60
        await svc.add_message(db, conv.id, "user", long_msg)
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        assert len(result["title"]) <= 51  # 50 chars + "…"
        assert result["title"].endswith("…")

    @pytest.mark.asyncio
    async def test_auto_title_skips_when_already_titled(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id, title="Custom Title")
        await svc.add_message(db, conv.id, "user", "This should not become the title")
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        assert result["title"] == "Custom Title"

    @pytest.mark.asyncio
    async def test_auto_title_only_on_first_user_message(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        # Add first message to trigger auto-title
        await svc.add_message(db, conv.id, "user", "First message")
        await db.commit()

        # Manually reset title to test second message doesn't re-title
        await svc.update_title(db, conv.id, "New Chat")
        await db.commit()

        # The second user message should still trigger auto-title since
        # title is back to "New Chat" — but there are now 2 user messages
        # so it should NOT auto-title
        await svc.add_message(db, conv.id, "user", "Second message")
        await db.commit()

        # Title stays as "New Chat" because there's already a user message
        result = await svc.get_conversation(db, conv.id, user_id)
        # After the first auto-title + manual reset + second message,
        # the second message finds existing user messages, so no auto-title
        assert result["title"] == "New Chat"

    @pytest.mark.asyncio
    async def test_assistant_message_does_not_auto_title(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id)
        await svc.add_message(db, conv.id, "assistant", "How can I help?")
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        assert result["title"] == "New Chat"


class TestUpdateTitle:
    """Test title updates."""

    @pytest.mark.asyncio
    async def test_update_title(self, svc, db, user_id):
        conv = await svc.create_conversation(db, user_id, title="Old")
        await svc.update_title(db, conv.id, "New Title")
        await db.commit()

        result = await svc.get_conversation(db, conv.id, user_id)
        assert result["title"] == "New Title"


class TestConversationIntegration:
    """Integration-style tests for full conversation lifecycle."""

    @pytest.mark.asyncio
    async def test_full_chat_lifecycle(self, svc, db, user_id):
        """Simulate: create → chat → save → reload → continue → delete."""
        # Create
        conv = await svc.create_conversation(db, user_id)
        cid = conv.id

        # First exchange
        await svc.add_message(db, cid, "user", "What is RDF?")
        await svc.add_message(db, cid, "assistant", "RDF is a framework for representing information.")
        await db.commit()

        # Verify auto-title from first user message
        result = await svc.get_conversation(db, cid, user_id)
        assert result["title"] == "What is RDF?"
        assert len(result["messages"]) == 2

        # Second exchange
        await svc.add_message(db, cid, "user", "Give me an example")
        await svc.add_message(db, cid, "assistant", "A triple: subject predicate object.")
        await db.commit()

        # Reload and verify all messages present
        result = await svc.get_conversation(db, cid, user_id)
        assert len(result["messages"]) == 4

        # Delete
        deleted = await svc.delete_conversation(db, cid, user_id)
        assert deleted is True
        await db.commit()

        # Verify deleted
        with pytest.raises(ValueError):
            await svc.get_conversation(db, cid, user_id)

    @pytest.mark.asyncio
    async def test_multiple_conversations_per_user(self, svc, db, user_id):
        """Verify multiple independent conversations."""
        c1 = await svc.create_conversation(db, user_id, title="Chat 1")
        c2 = await svc.create_conversation(db, user_id, title="Chat 2")

        await svc.add_message(db, c1.id, "user", "Message in chat 1")
        await svc.add_message(db, c2.id, "user", "Message in chat 2")
        await db.commit()

        r1 = await svc.get_conversation(db, c1.id, user_id)
        r2 = await svc.get_conversation(db, c2.id, user_id)

        assert len(r1["messages"]) == 1
        assert len(r2["messages"]) == 1
        assert r1["messages"][0]["content"] == "Message in chat 1"
        assert r2["messages"][0]["content"] == "Message in chat 2"
