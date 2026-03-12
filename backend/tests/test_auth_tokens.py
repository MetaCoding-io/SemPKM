"""Tests for auth token lifecycle: magic link, invitation, and setup tokens.

Covers create/verify roundtrips, expiry, tamper resistance, cross-salt
resistance, and setup token file idempotency/deletion.
"""

import time

import pytest

from app.auth.tokens import (
    create_invitation_token,
    create_magic_link_token,
    delete_setup_token,
    load_or_create_setup_token,
    verify_invitation_token,
    verify_magic_link_token,
)


# --- Magic link tokens ---


class TestMagicLinkTokens:
    def test_create_returns_nonempty_string(self):
        token = create_magic_link_token("user@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_roundtrip_verify_recovers_email(self):
        email = "alice@example.com"
        token = create_magic_link_token(email)
        result = verify_magic_link_token(token)
        assert result == email

    def test_expired_token_returns_none(self):
        token = create_magic_link_token("user@example.com")
        time.sleep(1)  # itsdangerous needs age > max_age, not >=
        result = verify_magic_link_token(token, max_age_seconds=0)
        assert result is None

    def test_tampered_token_returns_none(self):
        token = create_magic_link_token("user@example.com")
        tampered = token[:-4] + "XXXX"
        result = verify_magic_link_token(tampered)
        assert result is None

    def test_wrong_salt_returns_none(self):
        """Magic link token cannot be verified as invitation token."""
        token = create_magic_link_token("user@example.com")
        result = verify_invitation_token(token)
        assert result is None


# --- Invitation tokens ---


class TestInvitationTokens:
    def test_create_returns_nonempty_string(self):
        token = create_invitation_token("user@example.com", "member")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_roundtrip_verify_recovers_email_and_role(self):
        email = "bob@example.com"
        role = "guest"
        token = create_invitation_token(email, role)
        result = verify_invitation_token(token)
        assert result == {"email": email, "role": role}

    def test_expired_token_returns_none(self):
        token = create_invitation_token("user@example.com", "member")
        time.sleep(1)  # itsdangerous needs age > max_age, not >=
        result = verify_invitation_token(token, max_age_seconds=0)
        assert result is None

    def test_tampered_token_returns_none(self):
        token = create_invitation_token("user@example.com", "member")
        tampered = token[:-4] + "XXXX"
        result = verify_invitation_token(tampered)
        assert result is None

    def test_wrong_salt_returns_none(self):
        """Invitation token cannot be verified as magic link token."""
        token = create_invitation_token("user@example.com", "member")
        result = verify_magic_link_token(token)
        assert result is None


# --- Setup tokens (file-based) ---


class TestSetupTokens:
    def test_creates_file_and_returns_token(self, tmp_path):
        path = str(tmp_path / "setup.token")
        token = load_or_create_setup_token(path)
        assert isinstance(token, str)
        assert len(token) > 0
        assert (tmp_path / "setup.token").exists()

    def test_idempotent_returns_same_token(self, tmp_path):
        path = str(tmp_path / "setup.token")
        token1 = load_or_create_setup_token(path)
        token2 = load_or_create_setup_token(path)
        assert token1 == token2

    def test_delete_removes_file(self, tmp_path):
        path = str(tmp_path / "setup.token")
        load_or_create_setup_token(path)
        delete_setup_token(path)
        assert not (tmp_path / "setup.token").exists()

    def test_recreate_after_delete_gives_new_token(self, tmp_path):
        path = str(tmp_path / "setup.token")
        token1 = load_or_create_setup_token(path)
        delete_setup_token(path)
        token2 = load_or_create_setup_token(path)
        assert token2 != token1

    def test_delete_nonexistent_does_not_raise(self, tmp_path):
        path = str(tmp_path / "nonexistent.token")
        delete_setup_token(path)  # should not raise
