"""Tests for UserFavorite model CRUD operations.

Uses an in-memory SQLite database to verify create, duplicate rejection,
delete, per-user list filtering, and toggle (insert-if-absent /
delete-if-present) logic.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.models import User
from app.db.base import Base
from app.favorites.models import UserFavorite


@pytest.fixture
async def db_session():
    """Provide a fresh async SQLite session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def user_alice(db_session: AsyncSession) -> User:
    """Create and return a test user 'alice'."""
    user = User(id=uuid.uuid4(), email="alice@example.com", display_name="Alice")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_bob(db_session: AsyncSession) -> User:
    """Create and return a test user 'bob'."""
    user = User(id=uuid.uuid4(), email="bob@example.com", display_name="Bob")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestUserFavoriteCreate:
    async def test_create_and_read_back(self, db_session: AsyncSession, user_alice: User):
        """Create a UserFavorite and verify it can be read back."""
        iri = "http://example.org/resource/1"
        fav = UserFavorite(user_id=user_alice.id, object_iri=iri)
        db_session.add(fav)
        await db_session.commit()

        result = await db_session.execute(
            select(UserFavorite).where(UserFavorite.id == fav.id)
        )
        row = result.scalar_one()
        assert row.user_id == user_alice.id
        assert row.object_iri == iri
        assert row.created_at is not None

    async def test_unique_constraint_rejects_duplicate(
        self, db_session: AsyncSession, user_alice: User
    ):
        """Duplicate (user_id, object_iri) raises IntegrityError."""
        iri = "http://example.org/resource/dup"
        fav1 = UserFavorite(user_id=user_alice.id, object_iri=iri)
        db_session.add(fav1)
        await db_session.commit()

        fav2 = UserFavorite(user_id=user_alice.id, object_iri=iri)
        db_session.add(fav2)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()


class TestUserFavoriteDelete:
    async def test_delete_removes_row(self, db_session: AsyncSession, user_alice: User):
        """Deleting a favorite removes it from the database."""
        iri = "http://example.org/resource/del"
        fav = UserFavorite(user_id=user_alice.id, object_iri=iri)
        db_session.add(fav)
        await db_session.commit()

        await db_session.delete(fav)
        await db_session.commit()

        result = await db_session.execute(
            select(UserFavorite).where(UserFavorite.user_id == user_alice.id)
        )
        assert result.scalars().all() == []


class TestUserFavoriteList:
    async def test_list_returns_only_users_favorites(
        self, db_session: AsyncSession, user_alice: User, user_bob: User
    ):
        """Listing favorites for one user does not include another's."""
        alice_iri = "http://example.org/resource/alice-fav"
        bob_iri = "http://example.org/resource/bob-fav"
        db_session.add(UserFavorite(user_id=user_alice.id, object_iri=alice_iri))
        db_session.add(UserFavorite(user_id=user_bob.id, object_iri=bob_iri))
        await db_session.commit()

        result = await db_session.execute(
            select(UserFavorite).where(UserFavorite.user_id == user_alice.id)
        )
        alice_favs = result.scalars().all()
        assert len(alice_favs) == 1
        assert alice_favs[0].object_iri == alice_iri


class TestUserFavoriteToggle:
    async def test_toggle_adds_if_not_exists(
        self, db_session: AsyncSession, user_alice: User
    ):
        """Toggle on a non-existent favorite creates it."""
        iri = "http://example.org/resource/toggle"

        # Check not present
        result = await db_session.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == user_alice.id,
                UserFavorite.object_iri == iri,
            )
        )
        existing = result.scalar_one_or_none()
        assert existing is None

        # Toggle: insert since absent
        fav = UserFavorite(user_id=user_alice.id, object_iri=iri)
        db_session.add(fav)
        await db_session.commit()

        result = await db_session.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == user_alice.id,
                UserFavorite.object_iri == iri,
            )
        )
        assert result.scalar_one_or_none() is not None

    async def test_toggle_removes_if_exists(
        self, db_session: AsyncSession, user_alice: User
    ):
        """Toggle on an existing favorite deletes it."""
        iri = "http://example.org/resource/toggle-remove"

        # Create first
        fav = UserFavorite(user_id=user_alice.id, object_iri=iri)
        db_session.add(fav)
        await db_session.commit()

        # Toggle: delete since present
        result = await db_session.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == user_alice.id,
                UserFavorite.object_iri == iri,
            )
        )
        existing = result.scalar_one_or_none()
        assert existing is not None
        await db_session.delete(existing)
        await db_session.commit()

        # Verify gone
        result = await db_session.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == user_alice.id,
                UserFavorite.object_iri == iri,
            )
        )
        assert result.scalar_one_or_none() is None
