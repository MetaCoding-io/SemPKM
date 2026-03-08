"""IndieAuth service: authorization code, token issuance, introspection, revocation."""

import base64
import hashlib
import ipaddress
import logging
import secrets
import socket
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.indieauth.models import IndieAuthCode, IndieAuthToken
from app.indieauth.schemas import ClientInfo, IntrospectionResponse

logger = logging.getLogger(__name__)

# Token lifetimes
ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)
AUTH_CODE_TTL = timedelta(seconds=60)


def _sha256_hex(value: str) -> str:
    """SHA-256 hash a string, return hex digest."""
    return hashlib.sha256(value.encode("ascii")).hexdigest()


class IndieAuthService:
    """Core business logic for IndieAuth authorization code flow with PKCE."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Static helpers ──────────────────────────────────────────────

    @staticmethod
    def verify_pkce_s256(code_verifier: str, code_challenge: str) -> bool:
        """Verify PKCE S256 challenge against verifier (RFC 7636).

        Computes: BASE64URL(SHA256(code_verifier)) == code_challenge
        """
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return computed == code_challenge

    @staticmethod
    def validate_client_id(client_id: str) -> bool:
        """Validate client_id per IndieAuth spec Section 3.2.

        Requirements: http(s) scheme, path present, no fragment,
        no userinfo, no single/double dot path segments.
        """
        try:
            parsed = urlparse(client_id)
        except Exception:
            return False

        # Must be http or https
        if parsed.scheme not in ("http", "https"):
            return False

        # Must have a host
        if not parsed.hostname:
            return False

        # No fragment
        if parsed.fragment:
            return False

        # No userinfo (username/password in URL)
        if parsed.username or parsed.password:
            return False

        # Path must not be empty (at minimum "/")
        if not parsed.path:
            return False

        # No single-dot or double-dot path segments
        segments = parsed.path.split("/")
        for seg in segments:
            if seg in (".", ".."):
                return False

        return True

    @staticmethod
    async def fetch_client_info(client_id: str) -> ClientInfo:
        """Fetch client application metadata from client_id URL.

        Parses h-app microformat. Falls back to <title> or hostname.
        Guards against SSRF by rejecting loopback addresses.
        """
        # SSRF guard: reject loopback
        try:
            parsed = urlparse(client_id)
            hostname = parsed.hostname or ""
            # Resolve hostname to check for loopback
            for info in socket.getaddrinfo(hostname, None):
                addr = info[4][0]
                ip = ipaddress.ip_address(addr)
                if ip.is_loopback:
                    logger.warning("SSRF blocked: %s resolves to loopback", client_id)
                    return ClientInfo(name=client_id, url=client_id)
        except (socket.gaierror, ValueError):
            return ClientInfo(name=client_id, url=client_id)

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as http:
                resp = await http.get(client_id)
                resp.raise_for_status()

            import mf2py  # lazy import -- only needed here

            parsed_mf2 = mf2py.parse(resp.text, url=client_id)

            # Look for h-app microformat
            for item in parsed_mf2.get("items", []):
                if "h-app" in item.get("type", []):
                    props = item.get("properties", {})
                    name = props.get("name", [client_id])[0]
                    url = props.get("url", [client_id])[0]
                    logo_list = props.get("logo", [])
                    logo = logo_list[0] if logo_list else None
                    return ClientInfo(name=name, url=url, logo=logo)

            # Fallback: extract <title>
            import re

            title_match = re.search(r"<title[^>]*>([^<]+)</title>", resp.text, re.IGNORECASE)
            if title_match:
                return ClientInfo(name=title_match.group(1).strip(), url=client_id)

            # Final fallback: hostname
            return ClientInfo(name=urlparse(client_id).hostname or client_id, url=client_id)

        except Exception:
            logger.debug("Failed to fetch client info for %s", client_id, exc_info=True)
            return ClientInfo(name=client_id, url=client_id)

    # ── Authorization code ──────────────────────────────────────────

    async def create_authorization_code(
        self,
        user_id: UUID,
        client_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str,
        state: str | None,
    ) -> str:
        """Generate a single-use authorization code (60s TTL).

        Returns the plaintext code (given to client once). Only the hash is stored.
        """
        code = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        row = IndieAuthCode(
            code_hash=_sha256_hex(code),
            user_id=user_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            expires_at=now + AUTH_CODE_TTL,
        )
        self.db.add(row)
        await self.db.flush()
        return code

    # ── Token exchange ──────────────────────────────────────────────

    async def exchange_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> tuple[IndieAuthToken, str, str | None]:
        """Exchange authorization code for access + refresh tokens.

        Returns (token_row, access_token_plaintext, refresh_token_plaintext).
        Raises ValueError on any validation failure.
        """
        code_hash = _sha256_hex(code)
        result = await self.db.execute(
            select(IndieAuthCode).where(IndieAuthCode.code_hash == code_hash)
        )
        auth_code = result.scalar_one_or_none()

        if auth_code is None:
            raise ValueError("Invalid authorization code")

        now = datetime.now(timezone.utc)
        if auth_code.expires_at.replace(tzinfo=timezone.utc) < now:
            await self.db.delete(auth_code)
            await self.db.flush()
            raise ValueError("Authorization code has expired")

        if auth_code.client_id != client_id:
            raise ValueError("client_id mismatch")

        if auth_code.redirect_uri != redirect_uri:
            raise ValueError("redirect_uri mismatch")

        # PKCE verification
        if not self.verify_pkce_s256(code_verifier, auth_code.code_challenge):
            raise ValueError("PKCE verification failed")

        # Capture values before deleting
        scope = auth_code.scope
        user_id = auth_code.user_id

        # Delete code (single-use)
        await self.db.delete(auth_code)

        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        token_row = IndieAuthToken(
            token_hash=_sha256_hex(access_token),
            refresh_token_hash=_sha256_hex(refresh_token),
            user_id=user_id,
            client_id=client_id,
            scope=scope,
            expires_at=now + ACCESS_TOKEN_TTL,
            refresh_expires_at=now + REFRESH_TOKEN_TTL,
        )
        self.db.add(token_row)
        await self.db.flush()

        return token_row, access_token, refresh_token

    # ── Token refresh ───────────────────────────────────────────────

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[IndieAuthToken, str, str | None]:
        """Rotate refresh token and issue new access token.

        Returns (new_token_row, new_access_token, new_refresh_token).
        Raises ValueError on invalid/expired refresh token.
        """
        rt_hash = _sha256_hex(refresh_token)
        result = await self.db.execute(
            select(IndieAuthToken).where(IndieAuthToken.refresh_token_hash == rt_hash)
        )
        old_token = result.scalar_one_or_none()

        if old_token is None:
            raise ValueError("Invalid refresh token")

        now = datetime.now(timezone.utc)
        if (
            old_token.refresh_expires_at
            and old_token.refresh_expires_at.replace(tzinfo=timezone.utc) < now
        ):
            await self.db.delete(old_token)
            await self.db.flush()
            raise ValueError("Refresh token has expired")

        # Capture values, delete old
        user_id = old_token.user_id
        client_id = old_token.client_id
        scope = old_token.scope
        client_name = old_token.client_name
        await self.db.delete(old_token)

        # Issue new pair (rotation)
        new_access = secrets.token_urlsafe(32)
        new_refresh = secrets.token_urlsafe(32)

        new_token = IndieAuthToken(
            token_hash=_sha256_hex(new_access),
            refresh_token_hash=_sha256_hex(new_refresh),
            user_id=user_id,
            client_id=client_id,
            scope=scope,
            client_name=client_name,
            expires_at=now + ACCESS_TOKEN_TTL,
            refresh_expires_at=now + REFRESH_TOKEN_TTL,
        )
        self.db.add(new_token)
        await self.db.flush()

        return new_token, new_access, new_refresh

    # ── Introspection ───────────────────────────────────────────────

    async def introspect_token(self, token: str) -> IntrospectionResponse:
        """Introspect an access token (RFC 7662).

        Returns active=False for unknown/expired tokens.
        """
        t_hash = _sha256_hex(token)
        result = await self.db.execute(
            select(IndieAuthToken).where(IndieAuthToken.token_hash == t_hash)
        )
        token_row = result.scalar_one_or_none()

        if token_row is None:
            return IntrospectionResponse(active=False)

        now = datetime.now(timezone.utc)
        if token_row.expires_at.replace(tzinfo=timezone.utc) < now:
            return IntrospectionResponse(active=False)

        # Build me URL from user
        from app.auth.models import User

        user_result = await self.db.execute(
            select(User).where(User.id == token_row.user_id)
        )
        user = user_result.scalar_one_or_none()

        me = None
        if user and user.username:
            from app.webid.service import build_profile_url

            # Use a sensible default base URL; actual base comes from request context
            me = build_profile_url(user.username, "")

        return IntrospectionResponse(
            active=True,
            me=me,
            client_id=token_row.client_id,
            scope=token_row.scope,
            exp=int(token_row.expires_at.replace(tzinfo=timezone.utc).timestamp()),
            iat=int(token_row.created_at.replace(tzinfo=timezone.utc).timestamp()),
        )

    # ── Revocation ──────────────────────────────────────────────────

    async def revoke_token(self, token_hash: str) -> bool:
        """Revoke a token by its hash. Returns True if found and deleted."""
        result = await self.db.execute(
            select(IndieAuthToken).where(IndieAuthToken.token_hash == token_hash)
        )
        token_row = result.scalar_one_or_none()
        if token_row is None:
            return False
        await self.db.delete(token_row)
        await self.db.flush()
        return True

    # ── Listing ─────────────────────────────────────────────────────

    async def list_authorized_apps(self, user_id: UUID) -> list[IndieAuthToken]:
        """Return all non-expired tokens for a user, newest first."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(IndieAuthToken)
            .where(
                IndieAuthToken.user_id == user_id,
                IndieAuthToken.expires_at > now,
            )
            .order_by(IndieAuthToken.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Cleanup ─────────────────────────────────────────────────────

    async def cleanup_expired(self) -> None:
        """Delete all expired codes and tokens."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            delete(IndieAuthCode).where(IndieAuthCode.expires_at < now)
        )
        await self.db.execute(
            delete(IndieAuthToken).where(IndieAuthToken.expires_at < now)
        )
        await self.db.flush()
