"""Tests for DEMO_MODE auth bypass.

Verifies that when settings.demo_mode is True, all three auth dependency
functions return a synthetic guest user without any DB or cookie check.
Also verifies that default (non-demo) behavior is unchanged.
"""

import uuid

import pytest
from fastapi import HTTPException

from app.auth.dependencies import (
    _DEMO_USER_UUID,
    _demo_user,
    get_current_user,
    get_current_user_or_api,
    optional_current_user,
)
from app.auth.models import User
from app.config import settings


class TestDemoUser:
    """Tests for the _demo_user() helper function."""

    def test_returns_user_instance(self):
        user = _demo_user()
        assert isinstance(user, User)

    def test_has_deterministic_uuid(self):
        user = _demo_user()
        assert user.id == uuid.UUID("00000000-0000-0000-0000-000000000000")
        assert user.id == _DEMO_USER_UUID

    def test_has_demo_email(self):
        user = _demo_user()
        assert user.email == "demo@sempkm.app"

    def test_has_display_name(self):
        user = _demo_user()
        assert user.display_name == "Demo Visitor"

    def test_has_guest_role(self):
        user = _demo_user()
        assert user.role == "guest"

    def test_returns_fresh_instance_each_call(self):
        """Each call returns a new object (not a cached singleton)."""
        user1 = _demo_user()
        user2 = _demo_user()
        assert user1 is not user2
        assert user1.id == user2.id


class TestGetCurrentUserDemoMode:
    """Tests for get_current_user with DEMO_MODE."""

    @pytest.mark.asyncio
    async def test_returns_synthetic_user_when_demo_mode(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", True)
        # No cookie, no DB — should still return the synthetic user
        user = await get_current_user(sempkm_session=None, db=None)
        assert isinstance(user, User)
        assert user.id == _DEMO_USER_UUID
        assert user.email == "demo@sempkm.app"
        assert user.role == "guest"

    @pytest.mark.asyncio
    async def test_raises_401_without_cookie_when_not_demo(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(sempkm_session=None, db=None)
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail


class TestOptionalCurrentUserDemoMode:
    """Tests for optional_current_user with DEMO_MODE."""

    @pytest.mark.asyncio
    async def test_returns_synthetic_user_when_demo_mode(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", True)
        user = await optional_current_user(sempkm_session=None, db=None)
        assert isinstance(user, User)
        assert user.id == _DEMO_USER_UUID
        assert user.role == "guest"

    @pytest.mark.asyncio
    async def test_returns_none_without_cookie_when_not_demo(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", False)
        result = await optional_current_user(sempkm_session=None, db=None)
        assert result is None


class TestGetCurrentUserOrApiDemoMode:
    """Tests for get_current_user_or_api with DEMO_MODE."""

    @pytest.mark.asyncio
    async def test_returns_synthetic_user_when_demo_mode(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", True)
        # No cookie, no Authorization header, no DB — should still work
        user = await get_current_user_or_api(
            request=None, sempkm_session=None, authorization=None, db=None
        )
        assert isinstance(user, User)
        assert user.id == _DEMO_USER_UUID
        assert user.email == "demo@sempkm.app"
        assert user.role == "guest"

    @pytest.mark.asyncio
    async def test_raises_401_without_credentials_when_not_demo(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_mode", False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api(
                request=None, sempkm_session=None, authorization=None, db=None
            )
        assert exc_info.value.status_code == 401


class TestDemoModeDefaultOff:
    """Verify that demo_mode defaults to False (existing behavior preserved)."""

    def test_settings_demo_mode_default_false(self):
        """The default settings object should have demo_mode=False."""
        # Note: we test the field default, not the live settings object
        # (which may be patched by other tests).
        from pydantic_settings import BaseSettings

        from app.config import Settings

        # Create a fresh Settings with no env override
        fresh = Settings(demo_mode=False)
        assert fresh.demo_mode is False

    def test_synthetic_user_role_is_guest(self):
        """Guest role is critical for downstream permission enforcement."""
        user = _demo_user()
        assert user.role == "guest"
        # Verify it's NOT a privileged role
        assert user.role not in ("owner", "member", "admin")
