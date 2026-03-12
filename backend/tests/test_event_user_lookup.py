"""Tests for batched event log user lookup.

Verifies that ``resolve_user_names`` correctly batch-resolves
``urn:sempkm:user:{uuid}`` IRIs to display names via a single
SQL ``WHERE id IN (...)`` query.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.models import User
from app.browser.events import resolve_user_names
from app.db.base import Base


@pytest_asyncio.fixture
async def async_session():
    """Provide an in-memory SQLite async session with User table created."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


class TestResolveUserNamesEmpty:
    """Empty input returns empty dict with no SQL query."""

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_dict(self, async_session: AsyncSession):
        result = await resolve_user_names(async_session, [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_list_executes_no_query(self, async_session: AsyncSession):
        """Verify that no SQL statement is executed for empty input."""
        queries: list[str] = []

        # Listen on the underlying sync engine for SQL statements
        sync_engine = async_session.get_bind()
        event.listen(
            sync_engine, "before_cursor_execute",
            lambda conn, cursor, stmt, params, context, executemany: queries.append(stmt),
        )

        await resolve_user_names(async_session, [])
        assert len(queries) == 0


class TestResolveUserNamesInvalid:
    """Invalid URIs are skipped without raising exceptions."""

    @pytest.mark.asyncio
    async def test_non_matching_uri_skipped(self, async_session: AsyncSession):
        result = await resolve_user_names(async_session, [
            "http://example.org/not-a-user",
            "urn:other:scheme:123",
        ])
        assert result == {}

    @pytest.mark.asyncio
    async def test_invalid_uuid_skipped(self, async_session: AsyncSession):
        result = await resolve_user_names(async_session, [
            "urn:sempkm:user:not-a-valid-uuid",
        ])
        assert result == {}

    @pytest.mark.asyncio
    async def test_mixed_invalid_no_exception(self, async_session: AsyncSession):
        """Mix of bad patterns and bad UUIDs — no exception, empty result."""
        result = await resolve_user_names(async_session, [
            "garbage",
            "urn:sempkm:user:zzz",
            "",
        ])
        assert result == {}


class TestResolveUserNamesValid:
    """Valid URIs resolve to the correct display name or email."""

    @pytest.mark.asyncio
    async def test_single_user_with_display_name(self, async_session: AsyncSession):
        uid = uuid.uuid4()
        user = User(id=uid, email="alice@example.com", display_name="Alice")
        async_session.add(user)
        await async_session.flush()

        iri = f"urn:sempkm:user:{uid}"
        result = await resolve_user_names(async_session, [iri])
        assert result == {iri: "Alice"}

    @pytest.mark.asyncio
    async def test_user_without_display_name_falls_back_to_email(self, async_session: AsyncSession):
        uid = uuid.uuid4()
        user = User(id=uid, email="bob@example.com", display_name=None)
        async_session.add(user)
        await async_session.flush()

        iri = f"urn:sempkm:user:{uid}"
        result = await resolve_user_names(async_session, [iri])
        assert result == {iri: "bob@example.com"}

    @pytest.mark.asyncio
    async def test_multiple_users_batched(self, async_session: AsyncSession):
        uid1, uid2 = uuid.uuid4(), uuid.uuid4()
        async_session.add(User(id=uid1, email="a@x.com", display_name="Alpha"))
        async_session.add(User(id=uid2, email="b@x.com", display_name="Beta"))
        await async_session.flush()

        iri1 = f"urn:sempkm:user:{uid1}"
        iri2 = f"urn:sempkm:user:{uid2}"
        result = await resolve_user_names(async_session, [iri1, iri2])
        assert result == {iri1: "Alpha", iri2: "Beta"}

    @pytest.mark.asyncio
    async def test_unknown_uuid_omitted_from_result(self, async_session: AsyncSession):
        """A valid UUID that has no matching User row is simply absent."""
        missing_uid = uuid.uuid4()
        iri = f"urn:sempkm:user:{missing_uid}"
        result = await resolve_user_names(async_session, [iri])
        assert result == {}

    @pytest.mark.asyncio
    async def test_mix_of_valid_and_invalid(self, async_session: AsyncSession):
        uid = uuid.uuid4()
        async_session.add(User(id=uid, email="c@x.com", display_name="Charlie"))
        await async_session.flush()

        valid_iri = f"urn:sempkm:user:{uid}"
        result = await resolve_user_names(async_session, [
            valid_iri,
            "urn:sempkm:user:not-a-uuid",
            "http://example.org/other",
        ])
        assert result == {valid_iri: "Charlie"}

    @pytest.mark.asyncio
    async def test_single_query_executed(self, async_session: AsyncSession):
        """Verify only one SELECT query is issued for multiple users."""
        uid1, uid2 = uuid.uuid4(), uuid.uuid4()
        async_session.add(User(id=uid1, email="d@x.com", display_name="Delta"))
        async_session.add(User(id=uid2, email="e@x.com", display_name="Echo"))
        await async_session.flush()

        queries: list[str] = []
        sync_engine = async_session.get_bind()
        event.listen(
            sync_engine, "before_cursor_execute",
            lambda conn, cursor, stmt, params, context, executemany: queries.append(stmt),
        )

        iri1 = f"urn:sempkm:user:{uid1}"
        iri2 = f"urn:sempkm:user:{uid2}"
        await resolve_user_names(async_session, [iri1, iri2])

        # Should be exactly one SELECT ... WHERE ... IN query
        select_queries = [q for q in queries if "SELECT" in q.upper()]
        assert len(select_queries) == 1
        assert "IN" in select_queries[0].upper()
